"""Eval Sentinel — ADK FunctionTools over the Phoenix ops layer.

These are the eval-domain analogue of RHODES' tool registry: thin, typed
wrappers the agent calls during its detect -> root-cause -> verify loop.
Each returns plain JSON-serializable dicts so the agent can reason over them.

  detect_regression()        -> RHODES anomaly detection (compare baseline/current)
  get_failing_examples(cat)  -> RHODES RCAAnalyzer evidence (failing spans/rows)
  verify_fix(candidate)      -> RHODES "is the host healthy after the heal?"
                                (re-runs the real eval, confirms recovery)
"""

from google.adk.tools import FunctionTool

from . import phoenix_ops as po


def detect_regression() -> dict:
    """Detect an eval regression on the support-tickets classifier by comparing
    the locked BASELINE experiment against the CURRENT (production) experiment.

    Returns a dict with:
      - overall_delta: change in overall accuracy (negative = regression)
      - regressed_categories: list of category names that collapsed
      - baseline: {overall, per_category, examples}
      - current:  {overall, per_category, examples}
    Use this FIRST to confirm a regression exists and which categories fell.
    """
    return po.compare(po.BASELINE_EXPERIMENT_ID, po.CURRENT_EXPERIMENT_ID)


def get_failing_examples(category: str) -> dict:
    """Return the CURRENT experiment's failing rows for a given category, so you
    can root-cause *why* it regressed (which wrong label it collapsed into).

    Args:
      category: one of billing | account | technical | other

    Returns:
      {
        'category': str,
        'failing': [{'ticket','expected','predicted'}],
        'misclassified_as': {wrong_label: count},  # where the failures went
        'current_prompt': str,                      # the prompt under test
      }
    """
    current = po.experiment_scores(po.CURRENT_EXPERIMENT_ID)
    failing = [
        {"ticket": e["ticket"], "expected": e["expected"], "predicted": e["predicted"]}
        for e in current["examples"]
        if e["expected"] == category and not e["correct"]
    ]
    misclassified_as: dict = {}
    for f in failing:
        misclassified_as[f["predicted"]] = misclassified_as.get(f["predicted"], 0) + 1

    exp = po._PHX.experiments.get_experiment(experiment_id=po.CURRENT_EXPERIMENT_ID)
    meta = exp.get("experiment_metadata") or {}
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

    Args:
      candidate_prompt: the full corrected classifier prompt to test.

    Returns experiment scores for the candidate plus 'experiment_id':
      {'overall', 'per_category', 'examples', 'experiment_id'}
    Compare these recovered scores against detect_regression()'s baseline to
    confirm the fix restored the regressed categories.
    """
    return po.run_candidate(candidate_prompt, name="classifier-fix")


detect_regression_tool = FunctionTool(detect_regression)
get_failing_examples_tool = FunctionTool(get_failing_examples)
verify_fix_tool = FunctionTool(verify_fix)

EVAL_SENTINEL_TOOLS = [
    detect_regression_tool,
    get_failing_examples_tool,
    verify_fix_tool,
]
