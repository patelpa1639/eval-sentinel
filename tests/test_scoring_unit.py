"""Fast, network-free UNIT tests for the scoring logic in src/phoenix_ops.py.

Unlike test_phoenix_ops.py (live Phoenix integration, skipped without creds),
these exercise the PURE reduction/comparison functions directly with synthetic
inputs and monkeypatched fakes. No network, fully deterministic, run under the
default `make test` (no `slow` marker).

Covered:
  * _score_runs  — per-category %, overall %, example correctness flags
  * compare      — regression detection (drop > threshold), overall_delta, passthrough
  * _resolve_experiment — no-match RuntimeError, happy path, most-recent-wins
"""

import pytest

# Import the contract module. It imports cleanly (constructs a Phoenix client
# from .env) but we never let the tests touch the network — every Phoenix call
# is monkeypatched out below.
import src.phoenix_ops as phoenix_ops

# Read categories from the module rather than hardcoding (smart-home set today,
# but the contract says CATEGORIES is module-owned).
CATEGORIES = phoenix_ops.CATEGORIES
THRESHOLD = phoenix_ops._REGRESSION_DELTA_THRESHOLD


# ── helpers ──────────────────────────────────────────────────────────────────
def _truth(pairs):
    """Build {example_id: {'text', 'expected'}} from [(text, expected), ...].

    example ids are the 0-based index as a string.
    """
    return {
        str(i): {"text": text, "expected": expected}
        for i, (text, expected) in enumerate(pairs)
    }


def _runs(predictions):
    """Build [{'dataset_example_id', 'output'}, ...] from [predicted, ...]."""
    return [
        {"dataset_example_id": str(i), "output": predicted}
        for i, predicted in enumerate(predictions)
    ]


def _zero_per_cat():
    return {c: 0.0 for c in CATEGORIES}


# ── _score_runs math ─────────────────────────────────────────────────────────
def test_score_runs_all_correct_is_100():
    # Two examples in each of the first two categories, all predicted correctly.
    c0, c1 = CATEGORIES[0], CATEGORIES[1]
    pairs = [("a", c0), ("b", c0), ("c", c1), ("d", c1)]
    truth = _truth(pairs)
    runs = _runs([c0, c0, c1, c1])

    out = phoenix_ops._score_runs(runs, truth)

    assert out["overall"] == 100.0
    assert out["per_category"][c0] == 100.0
    assert out["per_category"][c1] == 100.0
    # Categories with no examples score 0.0 (no division by zero).
    for c in CATEGORIES[2:]:
        assert out["per_category"][c] == 0.0
    assert len(out["examples"]) == 4
    assert all(ex["correct"] is True for ex in out["examples"])
    # Example shape matches the frozen contract.
    for ex in out["examples"]:
        assert set(ex.keys()) == {"text", "expected", "predicted", "correct"}


def test_score_runs_one_category_fully_wrong_is_0():
    # c0 examples are all misrouted to c1; c1 examples all correct.
    c0, c1 = CATEGORIES[0], CATEGORIES[1]
    pairs = [("a", c0), ("b", c0), ("c", c1), ("d", c1)]
    truth = _truth(pairs)
    runs = _runs([c1, c1, c1, c1])

    out = phoenix_ops._score_runs(runs, truth)

    assert out["per_category"][c0] == 0.0
    assert out["per_category"][c1] == 100.0
    # 2 of 4 correct overall.
    assert out["overall"] == 50.0
    correct_flags = {ex["text"]: ex["correct"] for ex in out["examples"]}
    assert correct_flags == {"a": False, "b": False, "c": True, "d": True}


def test_score_runs_mixed_partial_percentages():
    # c0: 3 examples, 2 correct -> 66.7%. c1: 1 example, correct -> 100%.
    c0, c1 = CATEGORIES[0], CATEGORIES[1]
    pairs = [("a", c0), ("b", c0), ("c", c0), ("d", c1)]
    truth = _truth(pairs)
    runs = _runs([c0, c0, c1, c1])  # third c0 mislabeled

    out = phoenix_ops._score_runs(runs, truth)

    assert out["per_category"][c0] == pytest.approx(66.7)
    assert out["per_category"][c1] == 100.0
    # 3 of 4 correct overall = 75.0
    assert out["overall"] == 75.0


def test_score_runs_normalizes_case_and_whitespace():
    # predicted is uppercased / padded but should still match expected.
    c0 = CATEGORIES[0]
    truth = _truth([("a", c0)])
    runs = [{"dataset_example_id": "0", "output": f"  {c0.upper()} "}]

    out = phoenix_ops._score_runs(runs, truth)

    assert out["per_category"][c0] == 100.0
    assert out["overall"] == 100.0
    assert out["examples"][0]["predicted"] == c0  # normalized to lowercase, stripped


def test_score_runs_handles_none_output_and_unknown_ids():
    # None prediction counts as wrong; a run with an unknown example id is skipped.
    c0 = CATEGORIES[0]
    truth = _truth([("a", c0)])
    runs = [
        {"dataset_example_id": "0", "output": None},      # wrong
        {"dataset_example_id": "999", "output": c0},       # no truth -> skipped
    ]

    out = phoenix_ops._score_runs(runs, truth)

    assert len(out["examples"]) == 1
    assert out["examples"][0]["correct"] is False
    assert out["per_category"][c0] == 0.0
    assert out["overall"] == 0.0


def test_score_runs_empty_is_zero_not_crash():
    out = phoenix_ops._score_runs([], {})
    assert out["overall"] == 0.0
    assert out["examples"] == []
    assert out["per_category"] == _zero_per_cat()


# ── compare regression detection ─────────────────────────────────────────────
def _scores(overall, per_category):
    """Minimal experiment_scores-shaped dict for compare()."""
    full = _zero_per_cat()
    full.update(per_category)
    return {"overall": overall, "per_category": full, "examples": []}


def test_compare_flags_only_dropped_category(monkeypatch):
    c0, c1 = CATEGORIES[0], CATEGORIES[1]
    baseline = _scores(100.0, {c: 100.0 for c in CATEGORIES})
    # c1 collapses to 0; everything else holds at 100.
    current_cats = {c: 100.0 for c in CATEGORIES}
    current_cats[c1] = 0.0
    current = _scores(80.0, current_cats)

    def fake_scores(experiment_id):
        return {"BASE": baseline, "CUR": current}[experiment_id]

    monkeypatch.setattr(phoenix_ops, "experiment_scores", fake_scores)

    result = phoenix_ops.compare("BASE", "CUR")

    assert result["regressed_categories"] == [c1]
    assert result["overall_delta"] == -20.0
    assert result["baseline"] is baseline
    assert result["current"] is current
    assert {"overall_delta", "regressed_categories", "baseline", "current"} <= set(
        result.keys()
    )


def test_compare_no_regression_within_threshold(monkeypatch):
    # A drop equal to / just under the threshold must NOT count as regressed.
    c0 = CATEGORIES[0]
    baseline = _scores(100.0, {c: 100.0 for c in CATEGORIES})
    small_drop = {c: 100.0 for c in CATEGORIES}
    small_drop[c0] = 100.0 - THRESHOLD  # exactly threshold drop -> not > threshold
    current = _scores(98.0, small_drop)

    monkeypatch.setattr(
        phoenix_ops,
        "experiment_scores",
        lambda eid: {"B": baseline, "C": current}[eid],
    )

    result = phoenix_ops.compare("B", "C")

    assert result["regressed_categories"] == []
    assert result["overall_delta"] == -2.0


def test_compare_improvement_gives_positive_delta_no_regression(monkeypatch):
    baseline = _scores(80.0, {c: 80.0 for c in CATEGORIES})
    current = _scores(95.0, {c: 95.0 for c in CATEGORIES})

    monkeypatch.setattr(
        phoenix_ops,
        "experiment_scores",
        lambda eid: {"B": baseline, "C": current}[eid],
    )

    result = phoenix_ops.compare("B", "C")

    assert result["regressed_categories"] == []
    assert result["overall_delta"] == 15.0


def test_compare_multiple_regressions(monkeypatch):
    # Two categories collapse; both must be flagged, order follows CATEGORIES.
    if len(CATEGORIES) < 2:
        pytest.skip("needs >=2 categories")
    c0, c1 = CATEGORIES[0], CATEGORIES[1]
    baseline = _scores(100.0, {c: 100.0 for c in CATEGORIES})
    cur_cats = {c: 100.0 for c in CATEGORIES}
    cur_cats[c0] = 0.0
    cur_cats[c1] = 50.0  # 50-point drop, > threshold
    current = _scores(60.0, cur_cats)

    monkeypatch.setattr(
        phoenix_ops,
        "experiment_scores",
        lambda eid: {"B": baseline, "C": current}[eid],
    )

    result = phoenix_ops.compare("B", "C")

    assert set(result["regressed_categories"]) == {c0, c1}
    # Flagged in CATEGORIES order.
    assert result["regressed_categories"] == [
        c for c in CATEGORIES if c in (c0, c1)
    ]


# ── _resolve_experiment ──────────────────────────────────────────────────────
class _FakeDataset:
    id = "ds-fake-id"


def _patch_resolver(monkeypatch, experiments):
    """Wire _dataset + _PHX.experiments.list to canned data; clear the cache."""
    monkeypatch.setattr(phoenix_ops, "_dataset", lambda: _FakeDataset())

    class _FakeExperiments:
        def list(self, dataset_id=None):
            assert dataset_id == _FakeDataset.id
            return experiments

    class _FakePHX:
        experiments = _FakeExperiments()

    monkeypatch.setattr(phoenix_ops, "_PHX", _FakePHX())
    # _resolve_experiment memoizes in module-level dict; isolate each test.
    monkeypatch.setattr(phoenix_ops, "_resolved_ids", {})


def test_resolve_experiment_no_match_raises_with_seed_hint(monkeypatch):
    # Experiments exist but none carry the requested tag in prompt_version.
    experiments = [
        {"id": "e1", "metadata": {"prompt_version": "v1-baseline"}, "created_at": "2026-01-01"},
        {"id": "e2", "metadata": {"prompt_version": "v2-current"}, "created_at": "2026-01-02"},
    ]
    _patch_resolver(monkeypatch, experiments)

    with pytest.raises(RuntimeError) as exc:
        phoenix_ops._resolve_experiment("nonexistent-tag")

    msg = str(exc.value)
    assert "python -m src.seed" in msg


def test_resolve_experiment_happy_path_returns_id(monkeypatch):
    experiments = [
        {"id": "base-id", "metadata": {"prompt_version": "v1-baseline"}, "created_at": "2026-01-01"},
        {"id": "cur-id", "metadata": {"prompt_version": "v2-current"}, "created_at": "2026-01-02"},
    ]
    _patch_resolver(monkeypatch, experiments)

    assert phoenix_ops._resolve_experiment("baseline") == "base-id"
    assert phoenix_ops._resolve_experiment("current") == "cur-id"


def test_resolve_experiment_most_recent_wins(monkeypatch):
    # Two experiments share the tag; the one with the later created_at wins.
    experiments = [
        {"id": "old", "metadata": {"prompt_version": "v2-current"}, "created_at": "2026-01-01T00:00:00"},
        {"id": "new", "metadata": {"prompt_version": "v2-current"}, "created_at": "2026-03-15T00:00:00"},
    ]
    _patch_resolver(monkeypatch, experiments)

    assert phoenix_ops._resolve_experiment("current") == "new"


def test_resolve_experiment_accepts_object_experiments(monkeypatch):
    # experiments.list may yield objects (not dicts); resolver reads __dict__.
    class _ExpObj:
        def __init__(self, _id, version, created):
            self.id = _id
            self.metadata = {"prompt_version": version}
            self.created_at = created

    experiments = [
        _ExpObj("obj-base", "v1-baseline", "2026-01-01"),
        _ExpObj("obj-cur", "v2-current", "2026-01-02"),
    ]
    _patch_resolver(monkeypatch, experiments)

    assert phoenix_ops._resolve_experiment("baseline") == "obj-base"
    assert phoenix_ops._resolve_experiment("current") == "obj-cur"
