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

The signatures below are a FROZEN CONTRACT — other agents code against them.
Do not change the names or return shapes.
"""

import os

from dotenv import load_dotenv

load_dotenv()

from phoenix.client import Client

# Reuse the seed helpers so the demo and the agent classify identically.
from .seed import CATEGORIES, classify, exact_match, make_task

# ── Frozen contract constants ───────────────────────────────────────────────
DATASET = "smart-home-commands"
# Seeded by src/seed.py: baseline (100% all categories) vs current (climate 0%).
BASELINE_EXPERIMENT_ID = "RXhwZXJpbWVudDo5"
CURRENT_EXPERIMENT_ID = "RXhwZXJpbWVudDoxMA=="

# A correctness floor: a category counts as "regressed" when its accuracy drops
# by more than this many points relative to baseline. Mirrors RHODES' anomaly
# thresholds — a small jitter shouldn't trip the gate, a collapse should.
_REGRESSION_DELTA_THRESHOLD = 10.0

_PHX = Client(base_url=os.environ["PHOENIX_COLLECTOR_ENDPOINT"])


# ── Private helpers ──────────────────────────────────────────────────────────
def _dataset():
    return _PHX.datasets.get_dataset(dataset=DATASET)


def _example_truth(ds) -> dict:
    """Map dataset_example_id -> {'text', 'expected'} for join with task_runs.

    Domain-agnostic: grabs the single input value (e.g. 'command' or 'ticket')
    without assuming a specific key name.
    """
    truth = {}
    for ex in ds.examples:
        inp = ex.get("input") or {}
        out = ex.get("output") or {}
        if isinstance(inp, dict):
            text = next(iter(inp.values()), "") if inp else ""
        else:
            text = str(inp)
        expected = out.get("label") if isinstance(out, dict) else str(out)
        truth[ex["id"]] = {"text": text, "expected": expected}
    return truth


def _score_runs(task_runs, truth) -> dict:
    """Reduce raw task_runs + ground truth into the experiment_scores shape."""
    examples = []
    per_cat_total: dict = {c: 0 for c in CATEGORIES}
    per_cat_correct: dict = {c: 0 for c in CATEGORIES}

    for run in task_runs:
        ex_id = run.get("dataset_example_id")
        t = truth.get(ex_id)
        if t is None:
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


# ── Frozen contract ──────────────────────────────────────────────────────────
def experiment_scores(experiment_id: str) -> dict:
    """Compute accuracy for an existing Phoenix experiment.

    Returns:
        {
          'overall': float (0-100),
          'per_category': {category: float},
          'examples': [{'ticket', 'expected', 'predicted', 'correct'}],
        }
    """
    exp = _PHX.experiments.get_experiment(experiment_id=experiment_id)
    truth = _example_truth(_dataset())
    return _score_runs(exp.get("task_runs", []), truth)


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


def run_candidate(prompt: str, name: str = "classifier-fix") -> dict:
    """Run a NEW Phoenix experiment on DATASET with the candidate `prompt`,
    then score it. This is the eval-domain analogue of RHODES verifying a host
    is healthy after a heal: we re-run the real eval and confirm recovery.

    Returns experiment_scores(...) shape plus 'experiment_id'.
    """
    ds = _dataset()
    exp = _PHX.experiments.run_experiment(
        dataset=ds,
        task=make_task(prompt),
        evaluators={"exact_match": exact_match},
        experiment_name=name,
        experiment_metadata={"prompt": prompt, "prompt_version": name},
    )

    experiment_id = _experiment_id_of(exp)
    if experiment_id:
        scores = experiment_scores(experiment_id)
        scores["experiment_id"] = experiment_id
        return scores

    # Fallback: score directly off the returned object if the id is unavailable.
    truth = _example_truth(ds)
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
