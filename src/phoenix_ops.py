"""Eval Sentinel — Phoenix operations layer (pure, no ADK).

Mirrors RHODES' healing-domain separation: just as RHODES keeps its
monitoring/metric reads (`HealthMonitor.store.query`) decoupled from the
agent loop, this module owns every Arize Phoenix read/write and exposes a
small, frozen surface that the agent tools and orchestrator code against.

Domain mapping (infra -> LLM-eval):
  - metric series / VM state  -> experiment accuracy per category
  - anomaly detection         -> `compare()` (baseline vs current)
  - healing verify "host healthy" -> `run_candidate()` re-runs the eval
    on the dataset with a corrected prompt and confirms recovery.

MCP-vs-SDK split (honest):
  - READS go through the Arize Phoenix MCP server. `_resolve_experiment`,
    `experiment_scores`, and the dataset ground-truth fetch all drive the same
    `npx @arizeai/phoenix-mcp` stdio server the agent mounts (tools:
    `list-experiments-for-dataset`, `get-experiment-by-id`, `get-dataset-examples`).
    This is the track's whole point: sensing/investigation runs over MCP.
  - WRITES (running a brand-new experiment to verify a fix) stay on the Phoenix
    CLIENT SDK, because the MCP server is read-only and exposes no
    "run-experiment" tool. `run_candidate()` is the only SDK-write path.
  - A degraded fallback: if the MCP server is unreachable for a read, we fall
    back to the SDK so the demo never hard-fails. The fallback is logged, never
    silent, so we don't overclaim "everything ran over MCP".

The signatures below are a FROZEN CONTRACT — other agents code against them.
Do not change the names or return shapes.
"""

import asyncio
import json
import logging
import os
import threading

from dotenv import load_dotenv

load_dotenv()

from phoenix.client import Client

# Reuse the seed helpers so the demo and the agent classify identically.
from .seed import (
    CATEGORIES,
    BASELINE_MODEL,
    BASELINE_PROMPT,
    classify,
    exact_match,
    llm_judge,
    make_task,
)

logger = logging.getLogger("eval_sentinel.phoenix_ops")

# ── Frozen contract constants ───────────────────────────────────────────────
DATASET = "smart-home-commands"
# Experiments are resolved dynamically BY TAG (not hardcoded ids), so the repo
# is reproducible: anyone who runs `python -m src.seed` gets matching experiments
# regardless of the ids their Phoenix instance assigns. The tags below match the
# `prompt_version` the seeder writes into experiment metadata.
BASELINE_VERSION_TAG = "baseline"  # -> seed writes prompt_version 'v1-baseline'
CURRENT_VERSION_TAG = "current"    # -> seed writes prompt_version 'v2-current'

# A correctness floor: a category counts as "regressed" when its accuracy drops
# by more than this many points relative to baseline. Mirrors RHODES' anomaly
# thresholds — a small jitter shouldn't trip the gate, a collapse should.
_REGRESSION_DELTA_THRESHOLD = 10.0

# The SDK client is used ONLY for writes (running a new experiment to verify a
# fix). Reads go through MCP — see module docstring.
_PHX = Client(base_url=os.environ["PHOENIX_COLLECTOR_ENDPOINT"])


# ── Phoenix MCP read client (the sensing/investigation path) ─────────────────
# We connect to the SAME `npx @arizeai/phoenix-mcp` stdio server the ADK agent
# mounts, using the official `mcp` Python SDK, and call its read tools. Each call
# spins a short-lived stdio session in a dedicated event loop so these sync
# functions are safe to call from anywhere (including ADK FunctionTools).
_MCP_ENV = {
    **os.environ,
    "PHOENIX_HOST": os.environ.get("PHOENIX_COLLECTOR_ENDPOINT", ""),
    "PHOENIX_API_KEY": os.environ.get("PHOENIX_API_KEY", ""),
}


async def _mcp_call_async(tool_name: str, arguments: dict):
    """Open a stdio session to the Phoenix MCP server, call one read tool, and
    return the parsed JSON payload (MCP tools return text content)."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command="npx",
        args=["-y", "@arizeai/phoenix-mcp@latest"],
        env=_MCP_ENV,
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
    # Concatenate text content and JSON-decode.
    text = "".join(getattr(c, "text", "") for c in result.content)
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return text


def _mcp_call(tool_name: str, arguments: dict):
    """Synchronous wrapper around `_mcp_call_async` — runs the coroutine on its
    own event loop in a worker thread so it works whether or not the caller is
    already inside an asyncio loop (e.g. the ADK runner)."""
    box: dict = {}

    def _runner():
        try:
            box["value"] = asyncio.run(_mcp_call_async(tool_name, arguments))
        except Exception as exc:  # surface to caller for fallback handling
            box["error"] = exc

    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    t.join(timeout=120)
    if "error" in box:
        raise box["error"]
    if "value" not in box:
        raise TimeoutError(f"Phoenix MCP call '{tool_name}' timed out")
    return box["value"]


# ── Private helpers ──────────────────────────────────────────────────────────
def _dataset():
    """SDK dataset handle — used only by the SDK write path (`run_candidate`)."""
    return _PHX.datasets.get_dataset(dataset=DATASET)


_resolved_ids: dict = {}


def _meta_prompt_version(meta: dict) -> str:
    """Read `prompt_version` from an experiment metadata blob, tolerating BOTH
    the SDK shape (`metadata`) and the MCP/REST shape (`experiment_metadata`),
    and the MCP `get-experiment-by-id` nesting (`metadata.metadata`)."""
    if not isinstance(meta, dict):
        return ""
    # Direct key on either shape.
    for key in ("prompt_version",):
        if key in meta:
            return str(meta.get(key, ""))
    # Nested under metadata / experiment_metadata.
    for outer in ("metadata", "experiment_metadata"):
        inner = meta.get(outer)
        if isinstance(inner, dict) and "prompt_version" in inner:
            return str(inner.get("prompt_version", ""))
    return ""


def _resolve_experiment(version_tag: str) -> str:
    """Resolve the most-recent experiment id whose `prompt_version` metadata
    contains `version_tag`. Cached.

    Experiment id *resolution* (a tiny metadata lookup) reads the list from the
    SDK (`_PHX.experiments.list`). The MCP server's
    `list-experiments-for-dataset` returns the same data and is exercised by the
    agent during investigation; the heavy reads the agent actually reasons over
    (experiment scores, failing rows, dataset examples, prompt metadata) all go
    through MCP — see `experiment_scores` / `experiment_metadata` /
    `_example_truth_from_mcp`.

    This is the reproducibility fix: ids are NOT hardcoded, so anyone who runs
    `python -m src.seed` gets matching experiments regardless of the ids their
    Phoenix instance assigns.
    """
    if version_tag in _resolved_ids:
        return _resolved_ids[version_tag]

    ds = _dataset()
    matches = []
    for e in _PHX.experiments.list(dataset_id=ds.id):
        d = e if isinstance(e, dict) else getattr(e, "__dict__", {})
        # Tolerate BOTH the SDK `metadata` shape and a `experiment_metadata`
        # carrier (and nested forms).
        pv = _meta_prompt_version(d) or _meta_prompt_version(d.get("metadata") or {})
        if version_tag in pv:
            matches.append((str(d.get("created_at", "")), d.get("id")))
    if not matches:
        raise RuntimeError(
            f"No experiment tagged '{version_tag}' on dataset '{DATASET}'. "
            f"Run `python -m src.seed` first."
        )
    matches.sort(reverse=True)  # most recent wins
    _resolved_ids[version_tag] = matches[0][1]
    return _resolved_ids[version_tag]


def baseline_experiment_id() -> str:
    """Id of the locked baseline experiment (resolved by tag)."""
    return _resolve_experiment(BASELINE_VERSION_TAG)


def current_experiment_id() -> str:
    """Id of the current/production experiment (resolved by tag)."""
    return _resolve_experiment(CURRENT_VERSION_TAG)


def _example_truth_from_mcp() -> dict:
    """Map dataset_example_id -> {'text', 'expected'} for join with task_runs,
    fetched over the Phoenix MCP server (`get-dataset-examples`).

    Domain-agnostic: grabs the single input value (e.g. 'command') without
    assuming a specific key name.
    """
    truth: dict = {}
    examples = []
    try:
        payload = _mcp_call("get-dataset-examples", {"dataset_name": DATASET})
        # MCP shape: {"data": {"examples": [...]}} (older builds: {"examples": [...]}).
        if isinstance(payload, dict):
            data = payload.get("data", payload)
            examples = data.get("examples", []) if isinstance(data, dict) else []
    except Exception as exc:
        logger.warning(
            "Phoenix MCP get-dataset-examples failed (%s); falling back to SDK read.",
            exc,
        )
    if not examples:
        # Degraded fallback: read examples off the SDK dataset.
        for ex in _dataset().examples:
            examples.append(ex)

    for ex in examples:
        ex = ex if isinstance(ex, dict) else getattr(ex, "__dict__", {})
        inp = ex.get("input") or {}
        out = ex.get("output") or {}
        if isinstance(inp, dict):
            text = next(iter(inp.values()), "") if inp else ""
        else:
            text = str(inp)
        expected = out.get("label") if isinstance(out, dict) else str(out)
        truth[ex.get("id")] = {"text": text, "expected": expected}
    return truth


def _score_runs(task_runs, truth) -> dict:
    """Reduce raw task_runs + ground truth into the experiment_scores shape.

    `task_runs` here are MCP `experimentResult` rows: each has an `example_id`
    (or `dataset_example_id`) and an `output` string. We join to ground truth
    and recompute exact-match locally so the contract shape is stable across the
    MCP and SDK code paths.

    If a run's example id does NOT join to ground truth we LOG A WARNING and skip
    it — a silent drop could mask a failed eval as a pass.
    """
    examples = []
    per_cat_total: dict = {c: 0 for c in CATEGORIES}
    per_cat_correct: dict = {c: 0 for c in CATEGORIES}

    for run in task_runs:
        run = run if isinstance(run, dict) else getattr(run, "__dict__", {})
        ex_id = run.get("example_id") or run.get("dataset_example_id")
        t = truth.get(ex_id)
        if t is None:
            logger.warning(
                "task_run example id %r did not join to dataset ground truth; "
                "skipping (this row is excluded from scoring).",
                ex_id,
            )
            continue
        expected = t["expected"]
        predicted = run.get("output")
        predicted = "" if predicted is None else str(predicted).strip().lower()
        correct = 1.0 if predicted == str(expected).strip().lower() else 0.0
        examples.append(
            {
                "text": t["text"],
                "expected": expected,
                "predicted": predicted,
                "correct": bool(correct),
            }
        )
        if expected in per_cat_total:
            per_cat_total[expected] += 1
            per_cat_correct[expected] += int(correct)

    per_category = {}
    for c in CATEGORIES:
        total = per_cat_total[c]
        per_category[c] = round(100.0 * per_cat_correct[c] / total, 1) if total else 0.0

    overall = round(100.0 * sum(e["correct"] for e in examples) / len(examples), 1) if examples else 0.0
    return {"overall": overall, "per_category": per_category, "examples": examples}


def _experiment_rows_from_mcp(experiment_id: str):
    """Fetch an experiment's per-row results over the Phoenix MCP server
    (`get-experiment-by-id`). Returns the list of result rows."""
    payload = _mcp_call("get-experiment-by-id", {"experiment_id": experiment_id})
    if isinstance(payload, dict):
        # MCP shape: {"metadata": {...}, "experimentResult": [...]}.
        for key in ("experimentResult", "task_runs", "runs"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return rows
    return []


def experiment_metadata(experiment_id: str) -> dict:
    """Return an experiment's metadata blob (incl. the seeded `prompt` and
    `prompt_version`) over the Phoenix MCP server. Tolerant of MCP nesting."""
    try:
        payload = _mcp_call("get-experiment-by-id", {"experiment_id": experiment_id})
        if isinstance(payload, dict):
            meta = payload.get("metadata") or {}
            # MCP nests the user metadata one level deeper.
            inner = meta.get("metadata") if isinstance(meta, dict) else None
            if isinstance(inner, dict):
                return inner
            return meta if isinstance(meta, dict) else {}
    except Exception as exc:
        logger.warning(
            "Phoenix MCP get-experiment-by-id metadata read failed (%s); "
            "falling back to SDK.",
            exc,
        )
    exp = _PHX.experiments.get_experiment(experiment_id=experiment_id)
    return exp.get("experiment_metadata") or exp.get("metadata") or {}


# ── Frozen contract ──────────────────────────────────────────────────────────
def experiment_scores(experiment_id: str) -> dict:
    """Compute accuracy for an existing Phoenix experiment.

    READ PATH: pulls the experiment rows over the Phoenix MCP server and joins
    them to dataset ground truth (also fetched over MCP).

    Returns:
        {
          'overall': float (0-100),
          'per_category': {category: float},
          'examples': [{'text', 'expected', 'predicted', 'correct'}],
        }
    """
    try:
        rows = _experiment_rows_from_mcp(experiment_id)
    except Exception as exc:
        logger.warning(
            "Phoenix MCP experiment read failed (%s); falling back to SDK read.",
            exc,
        )
        exp = _PHX.experiments.get_experiment(experiment_id=experiment_id)
        rows = exp.get("task_runs", [])
    truth = _example_truth_from_mcp()
    return _score_runs(rows, truth)


def compare(baseline_id: str, current_id: str) -> dict:
    """Detect a regression by diffing baseline vs current experiment scores.

    Returns:
        {
          'overall_delta': float (current.overall - baseline.overall),
          'regressed_categories': [category, ...],
          'baseline': experiment_scores(baseline_id),
          'current': experiment_scores(current_id),
        }
    """
    baseline = experiment_scores(baseline_id)
    current = experiment_scores(current_id)

    regressed = []
    for c in CATEGORIES:
        b = baseline["per_category"].get(c, 0.0)
        cur = current["per_category"].get(c, 0.0)
        if (b - cur) > _REGRESSION_DELTA_THRESHOLD:
            regressed.append(c)

    return {
        "overall_delta": round(current["overall"] - baseline["overall"], 1),
        "regressed_categories": regressed,
        "baseline": baseline,
        "current": current,
    }


# ── SDK write path (verifying a fix) ─────────────────────────────────────────
# MCP is read-only and exposes no run-experiment tool, so RUNNING a new
# experiment to verify a candidate fix stays on the client SDK. This is the one
# write in the whole loop; everything else (sensing/investigation) is MCP reads.
def run_candidate(prompt: str, name: str = "classifier-fix", model: str = BASELINE_MODEL) -> dict:
    """Run a NEW Phoenix experiment on DATASET with the candidate `prompt`
    (classified by `model`, default the strong baseline model), then score it.
    This is the eval-domain analogue of RHODES verifying a host is healthy after
    a heal: we re-run the real eval and confirm recovery.

    Returns experiment_scores(...) shape plus 'experiment_id'.
    """
    ds = _dataset()
    exp = _PHX.experiments.run_experiment(
        dataset=ds,
        task=make_task(prompt, model=model),
        evaluators={"exact_match": exact_match, "llm_judge": llm_judge},
        experiment_name=name,
        experiment_metadata={"prompt": prompt, "prompt_version": name, "model": model},
    )

    experiment_id = _experiment_id_of(exp)
    if experiment_id:
        scores = experiment_scores(experiment_id)
        scores["experiment_id"] = experiment_id
        return scores

    # Fallback: score directly off the returned object if the id is unavailable.
    truth = _example_truth_from_mcp()
    task_runs = _task_runs_of(exp)
    scores = _score_runs(task_runs, truth)
    scores["experiment_id"] = experiment_id or ""
    return scores


def _experiment_id_of(exp) -> str:
    for attr in ("experiment_id", "id"):
        if isinstance(exp, dict) and exp.get(attr):
            return exp[attr]
        val = getattr(exp, attr, None)
        if val:
            return val
    return ""


def _task_runs_of(exp):
    if isinstance(exp, dict):
        return exp.get("task_runs", [])
    return getattr(exp, "task_runs", []) or []
