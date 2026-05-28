"""Integration tests for src/phoenix_ops.py.

These hit live Arize Phoenix read-only (the seeded `smart-home-commands` dataset
and its baseline/current experiments). They are written to the FROZEN CONTRACT:

    DATASET = "smart-home-commands"
    BASELINE_EXPERIMENT_ID = "RXhwZXJpbWVudDo5"     # 100% all categories
    CURRENT_EXPERIMENT_ID  = "RXhwZXJpbWVudDoxMA=="  # 80% overall, climate 0%

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

Assertions are deliberately tolerant (ranges, not exact floats) so the suite
stays green across minor seed/eval noise.

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


BASELINE_ID = phoenix_ops.BASELINE_EXPERIMENT_ID
CURRENT_ID = phoenix_ops.CURRENT_EXPERIMENT_ID


def test_contract_constants():
    assert phoenix_ops.DATASET == "smart-home-commands"
    assert phoenix_ops.BASELINE_EXPERIMENT_ID == "RXhwZXJpbWVudDo5"
    assert phoenix_ops.CURRENT_EXPERIMENT_ID == "RXhwZXJpbWVudDoxMA=="


def _assert_scores_shape(scores):
    assert isinstance(scores, dict)
    assert "overall" in scores
    assert "per_category" in scores
    assert "examples" in scores
    assert isinstance(scores["per_category"], dict)
    assert isinstance(scores["examples"], list)
    for ex in scores["examples"]:
        assert {"text", "expected", "predicted", "correct"} <= set(ex.keys())


def test_baseline_scores_all_perfect():
    scores = phoenix_ops.experiment_scores(BASELINE_ID)
    _assert_scores_shape(scores)
    # Baseline is seeded at 100% across the board.
    assert scores["overall"] >= 99.0, scores["overall"]
    assert scores["per_category"].get("climate") == pytest.approx(100, abs=0.5)


def test_current_scores_climate_regressed():
    scores = phoenix_ops.experiment_scores(CURRENT_ID)
    _assert_scores_shape(scores)
    # Current run: ~80% overall, climate dropped to 0, others still 100.
    assert 72.0 <= scores["overall"] <= 88.0, scores["overall"]
    per_cat = scores["per_category"]
    assert per_cat.get("climate") == pytest.approx(0, abs=0.5)
    for cat in ("lights", "media", "security", "other"):
        assert per_cat.get(cat) == pytest.approx(100, abs=0.5), (cat, per_cat.get(cat))


def test_compare_flags_climate_regression():
    result = phoenix_ops.compare(BASELINE_ID, CURRENT_ID)
    assert isinstance(result, dict)
    assert {"overall_delta", "regressed_categories", "baseline", "current"} <= set(
        result.keys()
    )
    # Climate went 100 -> 0, so it must show up as regressed.
    assert "climate" in result["regressed_categories"]
    # Overall dropped ~20 points; delta should be clearly negative.
    assert result["overall_delta"] < 0
    assert -30.0 <= result["overall_delta"] <= -12.0, result["overall_delta"]
