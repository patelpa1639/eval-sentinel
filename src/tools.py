"""Eval Sentinel — ADK FunctionTools over the Phoenix ops layer.

These are the eval-domain analogue of RHODES' tool registry: thin, typed
wrappers the agent calls during its detect -> root-cause -> verify loop.
Each returns plain JSON-serializable dicts so the agent can reason over them.

  detect_regression()        -> RHODES anomaly detection (compare baseline/current)
  get_failing_examples(cat)  -> RHODES RCAAnalyzer evidence (failing rows)
  verify_fix(candidate)      -> RHODES "is the host healthy after the heal?"
                                (re-runs the real eval, confirms recovery)

Reads (detect / get_failing_examples) flow through the Phoenix MCP server via
the phoenix_ops layer; only verify_fix performs an SDK write (run a new
experiment), since MCP is read-only.
"""

import threading

from google.adk.tools import FunctionTool

from . import phoenix_ops as po

# HARD cap on how many REAL verification experiments this process may run, to
# bound cost and runaway agent loops. Each verify_fix() runs the full dataset
# through the model, so we cap it. Thread-safe counter.
_MAX_VERIFY_RUNS = 3
_verify_runs = 0
_verify_lock = threading.Lock()


def detect_regression() -> dict:
    """Detect an eval regression on the smart-home command router by comparing
    the locked BASELINE experiment against the CURRENT (production) experiment.

    Returns a dict with:
      - overall_delta: change in overall accuracy (negative = regression)
      - regressed_categories: list of category names that collapsed
      - baseline: {overall, per_category, examples}
      - current:  {overall, per_category, examples}
    Use this FIRST to confirm a regression exists and which categories fell.
    """
    return po.compare(po.baseline_experiment_id(), po.current_experiment_id())


def get_failing_examples(category: str) -> dict:
    """Return the CURRENT experiment's failing rows for a given category, so you
    can root-cause *why* it regressed (which wrong label it collapsed into).

    Args:
      category: one of lights | climate | media | security | other

    Returns:
      {
        'category': str,
        'failing': [{'text','expected','predicted'}],
        'misclassified_as': {wrong_label: count},  # where the failures went
        'current_prompt': str,                      # the prompt under test
      }
    """
    current_id = po.current_experiment_id()
    current = po.experiment_scores(current_id)
    failing = [
        {"text": e["text"], "expected": e["expected"], "predicted": e["predicted"]}
        for e in current["examples"]
        if e["expected"] == category and not e["correct"]
    ]
    misclassified_as: dict = {}
    for f in failing:
        misclassified_as[f["predicted"]] = misclassified_as.get(f["predicted"], 0) + 1

    # Prompt metadata is fetched over the Phoenix MCP server (get-experiment-by-id).
    meta = po.experiment_metadata(current_id)
    return {
        "category": category,
        "failing": failing,
        "misclassified_as": misclassified_as,
        "current_prompt": meta.get("prompt", ""),
    }


def verify_fix(candidate_prompt: str) -> dict:
    """Verify a proposed corrected prompt by RUNNING A REAL NEW EXPERIMENT on the
    dataset and re-scoring it — the eval-domain equivalent of confirming a host
    is healthy after a heal. Call this AFTER you have proposed a corrected prompt.

    The candidate is run with the SAME strong baseline model (the regression is a
    prompt issue, so the fix is a prompt revert, re-evaluated on the same model).

    A HARD cap of 3 real verification runs per process bounds cost / runaway
    loops; beyond that this returns an error dict instead of running.

    Args:
      candidate_prompt: the full corrected classifier prompt to test.

    Returns experiment scores for the candidate plus 'experiment_id':
      {'overall', 'per_category', 'examples', 'experiment_id'}
    Compare these recovered scores against detect_regression()'s baseline to
    confirm the fix restored the regressed categories.
    """
    global _verify_runs
    with _verify_lock:
        if _verify_runs >= _MAX_VERIFY_RUNS:
            return {
                "error": (
                    f"verify_fix run limit reached ({_MAX_VERIFY_RUNS} real "
                    "verification experiments per process). Refusing to run "
                    "another experiment to bound cost and avoid runaway loops. "
                    "Settle on a candidate prompt and report your conclusion."
                ),
                "runs_used": _verify_runs,
                "max_runs": _MAX_VERIFY_RUNS,
            }
        _verify_runs += 1

    return po.run_candidate(candidate_prompt, name="classifier-fix")


detect_regression_tool = FunctionTool(detect_regression)
get_failing_examples_tool = FunctionTool(get_failing_examples)
verify_fix_tool = FunctionTool(verify_fix)

EVAL_SENTINEL_TOOLS = [
    detect_regression_tool,
    get_failing_examples_tool,
    verify_fix_tool,
]
