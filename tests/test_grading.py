"""Unit tests for server.services.grading.

The grading service is the single source of truth for the session
rubric (GRADING.md). These tests pin down:
  - Which phases use which method (PHASE_METHOD)
  - The score formula `((axis_1 + axis_2) / 2) * 25`
  - Hard rubric anchors (bare-result = 25%, full-Mastered = 100%)
  - Closed-form items don't poison axis means
  - Conditional-button rule (>= 60% Tugatish vs < 60% Qayta bajarish)
  - Phase-level row (Tile Match) is treated as pass/fail
  - Output schema is what the runtime template expects
"""

import pytest

from server.services.grading import (
    BAND_THRESHOLDS,
    FINISH_THRESHOLD_PCT,
    PHASE_DISPLAY_ORDER,
    PHASE_METHOD,
    aggregate,
)


# ── PHASE_METHOD invariants ────────────────────────────────────────────────

def test_phase_method_covers_every_known_phase():
    """All 13 known phases must be mapped — no silent drop-throughs."""
    expected = {
        "theme-preview", "flash-cards",
        "memory-sprint", "story-mode",
        "adaptive-quiz", "sentence-fill", "tile-match",
        "mystery-box", "puzzle-lock",
        "real-life",
        "consolidation",
        "final-boss",
        "reflection",
    }
    assert expected.issubset(set(PHASE_METHOD.keys())), \
        "PHASE_METHOD missing one of the canonical phases"


def test_phase_method_values_are_valid():
    """Every phase maps to one of the three valid methods."""
    valid = {"closed", "amr", "ungraded"}
    for phase, method in PHASE_METHOD.items():
        assert method in valid, f"{phase} has invalid method {method!r}"


def test_only_real_life_and_final_boss_are_amr():
    """Per GRADING.md §4 / §6, the 2-axis rubric is exactly Phase 4 + Phase 6."""
    amr_phases = {p for p, m in PHASE_METHOD.items() if m == "amr"}
    assert amr_phases == {"real-life", "final-boss"}


def test_sentence_fill_is_closed_not_amr():
    """SF is in Phase 3 Game Breaks → closed accuracy. Was previously bug
    where SF inflated AMR axis means; this pins the corrected behavior."""
    assert PHASE_METHOD["sentence-fill"] == "closed"


def test_consolidation_and_reflection_are_ungraded():
    """Per GRADING.md §5 / §7, neither contributes to the score."""
    assert PHASE_METHOD["consolidation"] == "ungraded"
    assert PHASE_METHOD["reflection"]    == "ungraded"


# ── Score formula + rubric anchors ─────────────────────────────────────────

def test_bare_result_is_floor():
    """GRADING.md anchor: 'the right numerical answer alone earns 25%.'
    A single Real-Life item with axis_1=1, axis_2=1 must produce
    overall 25% with band Novice."""
    out = aggregate([
        {"phase": "real-life", "id": "Q1", "correct": True, "score": 1,
         "axis_1": 1, "axis_2": 1},
    ])
    assert out["overall_pct"] == 25
    assert out["overall_axis_1"] == 1.0
    assert out["overall_axis_2"] == 1.0
    assert out["band"]["key"] == "novice"
    assert out["perf_class"] == "perf-bad"


def test_full_mastered_is_ceiling():
    """A1=4, A2=4 on a single Real-Life item → 100% Mastered."""
    out = aggregate([
        {"phase": "real-life", "id": "Q1", "correct": True, "score": 1,
         "axis_1": 4, "axis_2": 4},
    ])
    assert out["overall_pct"] == 100
    assert out["band"]["key"] == "mastered"
    assert out["perf_class"] == "perf-good"


def test_score_formula_holds():
    """`((axis_1_mean + axis_2_mean) / 2) * 25` exactly. We mix AMR items
    with closed items to confirm closed items don't pollute axis_1_mean
    or axis_2_mean."""
    items = [
        # Two AMR items: means → A1=3, A2=3.5
        {"phase": "real-life",  "id": "Q1", "correct": True, "score": 1, "axis_1": 4, "axis_2": 4},
        {"phase": "real-life",  "id": "Q2", "correct": True, "score": 1, "axis_1": 2, "axis_2": 3},
        # Closed items — must NOT contribute to axes
        {"phase": "memory-sprint", "id": "ms-1", "correct": True,  "closed": True},
        {"phase": "memory-sprint", "id": "ms-2", "correct": False, "closed": True},
    ]
    out = aggregate(items)
    assert out["overall_axis_1"] == 3.0
    assert out["overall_axis_2"] == 3.5
    # ((3 + 3.5) / 2) * 25 = 81.25 → rounds to 81
    assert out["overall_pct"] == 81
    assert out["band"]["key"] in ("proficient", "mastered")  # at the boundary


def test_closed_items_do_not_poison_axis_means():
    """Per GRADING.md, closed-form correct answers count toward donut +
    per-phase row but must NOT contribute axis_1 / axis_2.

    Earlier bug: rl correct items pushed `axis_1: 4, axis_2: 4` which
    fabricated Mastered grades for bare numerics. This pins the fix."""
    out = aggregate([
        {"phase": "real-life", "id": "Q1", "correct": True, "score": 1,
         "axis_1": 1, "axis_2": 1},  # honest AMR floor
        {"phase": "real-life", "id": "Q2", "correct": True, "score": 1,
         "closed": True},  # closed match, no axes
        {"phase": "real-life", "id": "Q3", "correct": True, "score": 1,
         "closed": True},  # closed match, no axes
    ])
    # Axes mean must be 1.0 (only the AMR item contributes), not bumped
    # by the closed items.
    assert out["overall_axis_1"] == 1.0
    assert out["overall_axis_2"] == 1.0
    # Donut counts ALL three (3/3 correct in real-life phase)
    rl_row = next(p for p in out["phases"] if p["key"] == "real-life")
    assert rl_row["correct"] == 3
    assert rl_row["total"]   == 3


# ── Conditional button (the > = 60% rule) ──────────────────────────────────

def test_high_score_renders_finish_button():
    """>= 60% → Tugatish (is-finish)."""
    out = aggregate([
        {"phase": "real-life", "id": "Q1", "correct": True, "score": 1, "axis_1": 4, "axis_2": 4},
        {"phase": "real-life", "id": "Q2", "correct": True, "score": 1, "axis_1": 4, "axis_2": 4},
    ])
    assert out["overall_pct"] >= FINISH_THRESHOLD_PCT
    assert out["action"]["kind"]   == "finish"
    assert out["action"]["label"]  == "Tugatish"
    assert out["action"]["perf_class"] == "is-finish"


def test_low_score_renders_redo_button():
    """< 60% → Qayta bajarish (is-redo)."""
    out = aggregate([
        {"phase": "real-life", "id": "Q1", "correct": True, "score": 1, "axis_1": 1, "axis_2": 1},
    ])
    assert out["overall_pct"] < FINISH_THRESHOLD_PCT
    assert out["action"]["kind"]   == "redo"
    assert out["action"]["label"]  == "Qayta bajarish"
    assert out["action"]["perf_class"] == "is-redo"


def test_finish_threshold_is_60():
    """Pin the threshold to GRADING.md / the spec."""
    assert FINISH_THRESHOLD_PCT == 60


# ── Per-phase rows ─────────────────────────────────────────────────────────

def test_tile_match_is_pass_fail():
    """Tile Match is the one phase-level row — pass/fail, not X/N."""
    out_pass = aggregate([{"phase": "tile-match", "id": "tm-all", "correct": True, "closed": True}])
    out_fail = aggregate([{"phase": "tile-match", "id": "tm-all", "correct": False, "closed": True}])

    pass_row = next(p for p in out_pass["phases"] if p["key"] == "tile-match")
    fail_row = next(p for p in out_fail["phases"] if p["key"] == "tile-match")

    assert pass_row["is_phase_level"] is True
    assert pass_row["score_text"]    == "Bajarildi"
    assert pass_row["perf_class"]    == "perf-good"

    assert fail_row["is_phase_level"] is True
    assert fail_row["score_text"]    == "—"
    assert fail_row["perf_class"]    == "perf-bad"


def test_phase_row_score_text_is_x_over_n():
    """Non-phase-level rows render as 'correct/total'."""
    out = aggregate([
        {"phase": "memory-sprint", "id": "ms-1", "correct": True,  "closed": True},
        {"phase": "memory-sprint", "id": "ms-2", "correct": True,  "closed": True},
        {"phase": "memory-sprint", "id": "ms-3", "correct": False, "closed": True},
    ])
    ms = next(p for p in out["phases"] if p["key"] == "memory-sprint")
    assert ms["score_text"] == "2/3"
    assert ms["correct"]    == 2
    assert ms["total"]      == 3
    assert ms["perf_class"] == "perf-mid"  # 67% → yellow band


def test_per_phase_axis_means_only_count_axed_items():
    """Axes for a given phase row only include items that explicitly
    carry numeric axis_1 / axis_2. Closed-form items in the same phase
    must be ignored for the axis mean (but counted in correct/total)."""
    out = aggregate([
        {"phase": "real-life", "id": "Q1", "correct": True, "score": 1, "axis_1": 4, "axis_2": 4},
        {"phase": "real-life", "id": "Q2", "correct": True, "score": 1, "closed": True},
    ])
    rl = next(p for p in out["phases"] if p["key"] == "real-life")
    assert rl["axis_1_mean"] == 4.0
    assert rl["axis_2_mean"] == 4.0
    assert rl["correct"]     == 2
    assert rl["total"]       == 2


# ── Edge cases ─────────────────────────────────────────────────────────────

def test_empty_log_returns_zero_state():
    out = aggregate([])
    assert out["overall_pct"] == 0
    assert out["has_axes"] is False
    assert out["totals"]["items"] == 0
    assert out["action"]["kind"]  == "redo"  # 0% < 60% → redo


def test_ungraded_phases_dropped():
    """Items in ungraded phases (consolidation, reflection, theme-preview,
    flash-cards) are dropped — they shouldn't even appear in totals."""
    out = aggregate([
        {"phase": "consolidation", "id": "c1", "correct": True},
        {"phase": "reflection",    "id": "r1", "correct": True},
        {"phase": "theme-preview", "id": "t1", "correct": True},
        {"phase": "flash-cards",   "id": "f1", "correct": True},
        # Plus one real graded item so totals isn't zero
        {"phase": "memory-sprint", "id": "ms-1", "correct": True, "closed": True},
    ])
    # Only the memory-sprint item should contribute
    assert out["totals"]["items"]   == 1
    assert out["totals"]["correct"] == 1


def test_unknown_phase_ignored_safely():
    """An unrecognized phase shouldn't crash — it should just be skipped
    silently (defensive — the rubric is supposed to be exhaustive)."""
    out = aggregate([
        {"phase": "does-not-exist", "id": "x", "correct": True},
        {"phase": "memory-sprint",  "id": "ms-1", "correct": True, "closed": True},
    ])
    assert out["totals"]["items"] == 1


def test_closed_only_session_still_gets_band():
    """If a session has no AMR items at all (closed-only run), the band
    is derived from the percentage so the scorecard still has a label."""
    out = aggregate([
        {"phase": "memory-sprint", "id": f"ms-{i}", "correct": True, "closed": True}
        for i in range(7)
    ])
    assert out["has_axes"] is False
    # 7/7 correct → 100% → band should be Mastered when projected onto 1-4.
    assert out["band"]["key"] == "mastered"
    assert out["overall_pct"] == 100


# ── Output schema invariants ───────────────────────────────────────────────

def test_aggregate_output_shape_matches_template_contract():
    """The runtime template's renderer expects this exact shape. If we
    rename a field here, the template breaks — pin the contract."""
    out = aggregate([
        {"phase": "real-life", "id": "Q1", "correct": True, "score": 1, "axis_1": 3, "axis_2": 4},
    ])
    # Top-level keys
    expected_keys = {
        "overall_pct", "overall_score",
        "overall_axis_1", "overall_axis_2",
        "band", "perf_class", "has_axes",
        "phases", "axes",
        "totals", "coaching_tip", "action",
    }
    assert expected_keys.issubset(set(out.keys())), \
        f"missing top-level keys: {expected_keys - set(out.keys())}"

    # Band shape
    assert set(out["band"].keys()) == {"key", "name"}

    # Axes shape
    for axis in ("axis_1", "axis_2"):
        assert set(out["axes"][axis].keys()) == {"mean", "perf_class", "tag"}

    # Totals shape
    assert set(out["totals"].keys()) == {"correct", "items"}

    # Action shape
    assert set(out["action"].keys()) == {"kind", "label", "perf_class"}


def test_phase_display_order_is_consistent_with_method_dict():
    """Every key in PHASE_DISPLAY_ORDER must exist in PHASE_METHOD —
    otherwise the renderer would show a row for a phase the rubric
    doesn't know how to grade."""
    for spec in PHASE_DISPLAY_ORDER:
        assert spec["key"] in PHASE_METHOD, \
            f"{spec['key']} appears in display order but not in PHASE_METHOD"


def test_band_thresholds_cover_full_range():
    """The four band thresholds must cover the entire 0-4 axis-mean
    range with no gaps. The lowest must accept anything (0.0 floor)."""
    floors = sorted(t[0] for t in BAND_THRESHOLDS)
    assert floors[0] == 0.0  # Novice catches everything

    # Every band has a unique key
    keys = [t[1] for t in BAND_THRESHOLDS]
    assert len(set(keys)) == len(keys)


# ── Coaching-tip pertinence ────────────────────────────────────────────────

def test_coaching_tip_changes_with_band():
    """The coaching tip should be band-keyed so the student gets the
    right nudge — not a generic message."""
    mastered = aggregate([{"phase": "real-life", "id": "Q1", "correct": True, "score": 1, "axis_1": 4, "axis_2": 4}])
    novice   = aggregate([{"phase": "real-life", "id": "Q1", "correct": True, "score": 1, "axis_1": 1, "axis_2": 1}])
    assert mastered["coaching_tip"] != novice["coaching_tip"]
    assert mastered["coaching_tip"]  # not empty
    assert novice["coaching_tip"]    # not empty
