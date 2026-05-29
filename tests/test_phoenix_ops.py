"""Integration tests for src/phoenix_ops.py.

These hit live Arize Phoenix READ-ONLY through the Phoenix MCP server (the
sensing/investigation path) against the seeded `smart-home-commands` dataset and
its baseline/current experiments. They are written to the FROZEN CONTRACT:

    DATASET = "smart-home-commands"
    # Experiment ids are resolved dynamically by metadata `prompt_version` tag
    # ('baseline' / 'current') — NOT hardcoded — so the suite is reproducible.

    experiment_scores(experiment_id) -> {
        'overall': float,
        'per_category': {cat: float},
        'examples': [{'text','expected','predicted','correct'}],
    }
    compare(baseline_id, current_id) -> {
        'overall_delta': float,
        'regressed_categories': [...],
        'baseline': {...},
        'current': {...},
    }

The seeded regression is a SUBTLE, plausible prompt "cleanup" (same model) that
narrows `media` to entertainment-only and adds an over-broad "any question/status
check is other" rule. Empirically this sinks the media + security categories
(each ~60%) for an overall ~84%, while lights/climate/other stay ~100%.

Assertions are deliberately tolerant (ranges, not exact floats) so the suite
stays green across minor eval noise.

If src/phoenix_ops.py does not yet exist (it is being written in parallel),
`pytest.importorskip` skips this module rather than hard-crashing collection.
"""

import os

import pytest
from dotenv import load_dotenv

load_dotenv()

# Skip the whole module cleanly if the contract code is not written yet.
phoenix_ops = pytest.importorskip(
    "src.phoenix_ops",
    reason="src/phoenix_ops.py not implemented yet (contract code in progress)",
)

# Require live Phoenix credentials; otherwise skip (these are integration tests).
if not os.environ.get("PHOENIX_API_KEY"):
    pytest.skip(
        "PHOENIX_API_KEY not set; skipping live Phoenix integration tests",
        allow_module_level=True,
    )


BASELINE_ID = phoenix_ops.baseline_experiment_id()
CURRENT_ID = phoenix_ops.current_experiment_id()


def test_contract_constants():
    # Dataset is fixed; experiment ids are resolved dynamically by tag (no
    # hardcoded ids), so just assert they resolve to distinct, non-empty ids.
    assert phoenix_ops.DATASET == "smart-home-commands"
    assert isinstance(BASELINE_ID, str) and BASELINE_ID
    assert isinstance(CURRENT_ID, str) and CURRENT_ID
    assert BASELINE_ID != CURRENT_ID


def _assert_scores_shape(scores):
    assert isinstance(scores, dict)
    assert "overall" in scores
    assert "per_category" in scores
    assert "examples" in scores
    assert isinstance(scores["per_category"], dict)
    assert isinstance(scores["examples"], list)
    for ex in scores["examples"]:
        assert {"text", "expected", "predicted", "correct"} <= set(ex.keys())


def test_baseline_scores_all_strong():
    scores = phoenix_ops.experiment_scores(BASELINE_ID)
    _assert_scores_shape(scores)
    # Baseline (well-scoped prompt, strong model) is seeded near-perfect.
    assert scores["overall"] >= 96.0, scores["overall"]
    for cat in ("lights", "climate", "media", "security", "other"):
        assert scores["per_category"].get(cat) >= 90.0, (cat, scores["per_category"].get(cat))


def test_current_scores_media_and_security_regressed():
    scores = phoenix_ops.experiment_scores(CURRENT_ID)
    _assert_scores_shape(scores)
    # Current run: ~84% overall; the subtle prompt cleanup sinks media + security
    # while lights/climate/other stay strong.
    assert 72.0 <= scores["overall"] <= 90.0, scores["overall"]
    per_cat = scores["per_category"]
    assert per_cat.get("media") <= 80.0, per_cat.get("media")
    assert per_cat.get("security") <= 80.0, per_cat.get("security")
    for cat in ("lights", "climate", "other"):
        assert per_cat.get(cat) >= 90.0, (cat, per_cat.get(cat))


def test_compare_flags_media_security_regression():
    result = phoenix_ops.compare(BASELINE_ID, CURRENT_ID)
    assert isinstance(result, dict)
    assert {"overall_delta", "regressed_categories", "baseline", "current"} <= set(
        result.keys()
    )
    # Media and security both dropped well past the threshold.
    assert "media" in result["regressed_categories"]
    assert "security" in result["regressed_categories"]
    # Lights/climate/other should NOT be flagged.
    for cat in ("lights", "climate", "other"):
        assert cat not in result["regressed_categories"], cat
    # Overall dropped clearly; delta should be solidly negative.
    assert result["overall_delta"] < 0
    assert -30.0 <= result["overall_delta"] <= -8.0, result["overall_delta"]


def test_resolve_tolerates_experiment_metadata_key():
    # _meta_prompt_version must read prompt_version from BOTH the SDK `metadata`
    # shape and the MCP/REST `experiment_metadata` shape (and nested forms).
    f = phoenix_ops._meta_prompt_version
    assert f({"prompt_version": "v2-current"}) == "v2-current"
    assert f({"metadata": {"prompt_version": "v1-baseline"}}) == "v1-baseline"
    assert f({"experiment_metadata": {"prompt_version": "v9-x"}}) == "v9-x"
    assert f({}) == ""


def test_verify_fix_run_cap():
    # The hard cap on real verification runs must be enforced by tools.verify_fix.
    from src import tools

    assert tools._MAX_VERIFY_RUNS >= 1
    # Simulate exhausting the budget without running real experiments.
    saved = tools._verify_runs
    try:
        tools._verify_runs = tools._MAX_VERIFY_RUNS
        out = tools.verify_fix("any prompt")
        assert isinstance(out, dict)
        assert "error" in out
        assert out.get("max_runs") == tools._MAX_VERIFY_RUNS
    finally:
        tools._verify_runs = saved
