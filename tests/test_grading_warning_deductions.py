"""Wave J — grading warning-deduction tests.

Tests that warning_deductions and homework_failed are correctly wired into
server/services/grading.aggregate().

Covers:
 1. warning_deductions=15 subtracts 15 from overall_pct
 2. homework_failed=True → action.kind == "failed"
 3. Negative protection — deduction can't push score below 0
 4. Zero deductions → raw_pct_pre_deductions == overall_pct (no change)
 5. Transparency fields present (raw_pct_pre_deductions, warning_deduction_pct)
"""

import pytest

from server.services.grading import aggregate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _amr_item(axis_1: float = 4.0, axis_2: float = 4.0) -> dict:
    return {
        "phase": "real-life",
        "id": "Q1",
        "correct": True,
        "score": 1,
        "axis_1": axis_1,
        "axis_2": axis_2,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_warning_deductions_subtracted_from_score():
    """aggregate(items, warning_deductions=15) → overall_pct = raw - 15."""
    # axis_1=4, axis_2=4 → raw = 100
    out = aggregate([_amr_item(4.0, 4.0)], warning_deductions=15)
    assert out["raw_pct_pre_deductions"] == 100
    assert out["overall_pct"] == 85
    assert out["warning_deduction_pct"] == 15


def test_homework_failed_action_kind():
    """aggregate(..., homework_failed=True) → action.kind == 'failed'."""
    out = aggregate([_amr_item(4.0, 4.0)], homework_failed=True)
    assert out["action"]["kind"] == "failed"
    assert out["action"]["label"] == "Failed"
    assert out["action"]["perf_class"] == "is-failed"
    assert out["homework_failed"] is True


def test_negative_protection():
    """Deduction cannot push score below 0."""
    # axis_1=1, axis_2=1 → raw = 25
    out = aggregate([_amr_item(1.0, 1.0)], warning_deductions=50)
    assert out["overall_pct"] == 0
    assert out["raw_pct_pre_deductions"] == 25
    assert out["warning_deduction_pct"] == 50


def test_zero_deductions_no_change():
    """No deductions → overall_pct equals raw_pct_pre_deductions."""
    out = aggregate([_amr_item(3.0, 3.0)])
    # ((3+3)/2) * 25 = 75
    assert out["overall_pct"] == 75
    assert out["raw_pct_pre_deductions"] == 75
    assert out["warning_deduction_pct"] == 0


def test_transparency_fields_always_present():
    """New fields are always present, even in the zero-deduction happy path."""
    out = aggregate([_amr_item()], warning_deductions=0, homework_failed=False)
    assert "raw_pct_pre_deductions" in out
    assert "warning_deduction_pct" in out
    assert "homework_failed" in out


def test_coaching_tip_includes_deduction_note():
    """When warning_deductions > 0, the coaching_tip mentions the deduction."""
    out = aggregate([_amr_item(4.0, 4.0)], warning_deductions=10)
    assert "10%" in out["coaching_tip"] or "ushlab" in out["coaching_tip"]


def test_finish_button_suppressed_when_score_drops_below_threshold():
    """If the score after deductions falls below FINISH_THRESHOLD_PCT (60),
    the action should be 'redo', not 'finish'."""
    from server.services.grading import FINISH_THRESHOLD_PCT

    # axis_1=3, axis_2=3 → raw = ((3+3)/2)*25 = 75 → after 20% deduction = 55
    out = aggregate([_amr_item(3.0, 3.0)], warning_deductions=20)
    assert out["overall_pct"] == 55
    assert 55 < FINISH_THRESHOLD_PCT
    assert out["action"]["kind"] == "redo"


def test_finish_button_present_when_score_stays_above_threshold():
    """Score after deduction still ≥ 60% → finish button."""
    # raw = 100, deduction = 30 → final = 70
    out = aggregate([_amr_item(4.0, 4.0)], warning_deductions=30)
    assert out["overall_pct"] == 70
    assert out["action"]["kind"] == "finish"


def test_existing_schema_fields_preserved():
    """The new fields must not replace or rename any existing contract fields."""
    out = aggregate([_amr_item(3.0, 4.0)], warning_deductions=5)
    existing_keys = {
        "overall_score", "overall_axis_1", "overall_axis_2",
        "band", "perf_class", "has_axes", "phases", "axes",
        "totals", "coaching_tip", "action",
    }
    assert existing_keys.issubset(set(out.keys())), (
        f"Missing expected keys: {existing_keys - set(out.keys())}"
    )
