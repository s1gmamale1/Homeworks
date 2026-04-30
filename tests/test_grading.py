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


def test_amr_phases_are_real_life_boss_and_reading_checkpoint():
    """Per GRADING.md §4 / §6, the 2-axis rubric is anchored on Phase 4 +
    Phase 6 — Real-Life Challenge + Final Boss. Reading checkpoints
    (Til Fanlar / Adabiyot) also collect axes when graded by the LMR
    AI grader, so they participate in the axis-mean pool. All three
    are flagged as 'amr' in PHASE_METHOD.
    """
    amr_phases = {p for p, m in PHASE_METHOD.items() if m == "amr"}
    assert amr_phases == {"real-life", "final-boss", "reading-checkpoint"}


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

    # Axes shape — `name` was added so the renderer can show the right
    # axis label per rubric (AMR: Concept Identification / Process Integrity;
    # LMR v2: Grammatical Accuracy / Lexical Quality).
    for axis in ("axis_1", "axis_2"):
        assert set(out["axes"][axis].keys()) == {"mean", "perf_class", "tag", "name"}
        assert isinstance(out["axes"][axis]["name"], str) and out["axes"][axis]["name"]

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


# ── LMR v2: language-subject rubric routing ────────────────────────────────

def test_lmr_axis_labels_for_language_subject():
    """English / Ona Tili / Rus Tili must use LMR v2 axis names —
    Grammatical Accuracy + Lexical Quality. Anything else falls through
    to AMR (Concept Identification + Process Integrity)."""
    items = [{"phase": "real-life", "id": "Q1", "correct": True, "score": 1.0,
              "axis_1": 4, "axis_2": 4}]
    eng = aggregate(items, subject="english")
    assert eng["rubric"] == "lmr"
    assert eng["axes"]["axis_1"]["name"] == "Grammatical Accuracy"
    assert eng["axes"]["axis_2"]["name"] == "Lexical Quality"


def test_lmr_axis_labels_for_uzbek_and_russian():
    """ona-tili and rus-tili (and their grade-band aliases) also use LMR v2."""
    items = [{"phase": "real-life", "id": "Q1", "correct": True, "score": 1.0,
              "axis_1": 3, "axis_2": 3}]
    for subject in ("ona-tili", "rus-tili", "ingliz-tili-g1-11", "ona-tili-g1-11"):
        out = aggregate(items, subject=subject)
        assert out["rubric"] == "lmr", subject
        assert out["axes"]["axis_1"]["name"] == "Grammatical Accuracy", subject
        assert out["axes"]["axis_2"]["name"] == "Lexical Quality", subject


def test_amr_axis_labels_for_non_language_subjects():
    """Math / science / social subjects keep AMR's axis names regardless
    of LMR addition. Adding LMR must not regress AMR labelling."""
    items = [{"phase": "real-life", "id": "Q1", "correct": True, "score": 1.0,
              "axis_1": 4, "axis_2": 4}]
    for subject in ("math-algebra", "math-geometry", "geometriya-g7-11",
                    "biologiya", "tarix", None, ""):
        out = aggregate(items, subject=subject)
        assert out["rubric"] == "amr", subject
        assert out["axes"]["axis_1"]["name"] == "Concept Identification", subject
        assert out["axes"]["axis_2"]["name"] == "Process Integrity", subject


def test_lmr_score_formula_identical_to_amr():
    """LMR v2 reuses AMR's ((a1+a2)/2)*25 formula and band thresholds.
    Same axis values must produce identical pct + band regardless of subject."""
    items = [{"phase": "real-life", "id": "Q1", "correct": True, "score": 1.0,
              "axis_1": 3, "axis_2": 4}]  # → ((3+4)/2)*25 = 87.5 → 88, mastered
    eng = aggregate(items, subject="english")
    math = aggregate(items, subject="math-algebra")
    assert eng["overall_pct"] == math["overall_pct"] == 88
    assert eng["band"] == math["band"]
    # Both rubrics must collect the same band even though axis labels differ
    assert eng["band"]["key"] == "mastered"


def test_lmr_floor_25_pct_same_as_amr():
    """The LMR v2 floor for a 'correct' answer (gate passed but axes 1/1)
    must equal AMR's floor — both are 25%."""
    items = [{"phase": "real-life", "id": "Q1", "correct": True, "score": 1.0,
              "axis_1": 1, "axis_2": 1}]
    eng = aggregate(items, subject="english")
    math = aggregate(items, subject="math-algebra")
    assert eng["overall_pct"] == math["overall_pct"] == 25


# ── Skipped-question penalty (expected_open_count padding) ──────────────

def test_one_perfect_answer_with_others_skipped_does_not_score_100():
    """User-flagged: a student who solves one Real-Life question with full
    rubric (axis 4/4) and dismisses the other 9 open questions used to
    score 100% because the mean was taken over answered items only.
    With expected_open_count=10 the missing 9 are padded to floor (1/1)
    and the score reflects partial completion."""
    items = [{"phase": "real-life", "id": "Q1", "correct": True, "score": 1.0,
              "axis_1": 4, "axis_2": 4}]
    out = aggregate(items, subject="english", expected_open_count=10)
    # ((4 + 9*1) / 10) on each axis = 1.3 → ((1.3 + 1.3)/2) * 25 = 32.5 → 32 or 33
    assert out["overall_pct"] < 50, (
        f"one-of-ten perfect answer must NOT score >= 50%, got {out['overall_pct']}"
    )
    assert out["overall_pct"] >= 25, (
        f"answered floor must hold; one perfect answer should still beat pure 25%"
    )
    assert round(out["overall_axis_1"], 1) == 1.3
    assert round(out["overall_axis_2"], 1) == 1.3


def test_full_completion_unchanged_by_padding():
    """When the student answers all expected_open_count items, padding
    must be a no-op — the mean of 10 perfect items stays at 4.0/4.0."""
    items = [
        {"phase": "real-life", "id": f"rl-{i}", "correct": True, "score": 1.0,
         "axis_1": 4, "axis_2": 4} for i in range(5)
    ] + [
        {"phase": "final-boss", "id": f"boss-{i}", "correct": True, "score": 1.0,
         "axis_1": 4, "axis_2": 4} for i in range(5)
    ]
    out = aggregate(items, subject="english", expected_open_count=10)
    assert out["overall_pct"] == 100
    assert out["overall_axis_1"] == 4.0
    assert out["overall_axis_2"] == 4.0


def test_partial_completion_scales_proportionally():
    """Half the questions answered perfectly, half skipped:
    mean = (5*4 + 5*1) / 10 = 2.5 on each axis →
    ((2.5+2.5)/2) * 25 = 62.5% → 62 (banker's rounding).
    A student who does half the work crosses the 60% finish threshold;
    below half they retry. That's the intended difficulty curve."""
    items = [
        {"phase": "real-life", "id": f"rl-{i}", "correct": True, "score": 1.0,
         "axis_1": 4, "axis_2": 4} for i in range(5)
    ]
    out = aggregate(items, subject="english", expected_open_count=10)
    assert round(out["overall_axis_1"], 2) == 2.5
    assert round(out["overall_axis_2"], 2) == 2.5
    assert out["overall_pct"] == 62
    # Just at the proficient/apprentice border (axis avg 2.5 = proficient floor)
    assert out["band"]["key"] in ("apprentice", "proficient")


def test_skipped_padding_works_for_amr_too():
    """The bug also affects math/science (AMR) when answers go through
    AI grading. Same fix, same test pattern."""
    items = [{"phase": "real-life", "id": "Q1", "correct": True, "score": 1.0,
              "axis_1": 4, "axis_2": 4}]
    eng = aggregate(items, subject="english",     expected_open_count=10)
    math = aggregate(items, subject="math-algebra", expected_open_count=10)
    # Same numerical scoring regardless of rubric — only labels differ
    assert eng["overall_pct"] == math["overall_pct"]
    assert eng["overall_pct"] < 50


def test_no_padding_when_expected_count_omitted_legacy_behaviour():
    """Backwards compatibility: callers that don't pass expected_open_count
    get the unchanged behaviour (mean over answered only, partial
    inflation possible). The runtime template DOES pass the count after
    this fix, but legacy tests / callers must not break."""
    items = [{"phase": "real-life", "id": "Q1", "correct": True, "score": 1.0,
              "axis_1": 4, "axis_2": 4}]
    out = aggregate(items, subject="english")  # no expected_open_count
    assert out["overall_pct"] == 100  # legacy behaviour: one item averages to 4/4


def test_padding_handles_count_smaller_than_actual():
    """Defensive: if the runtime sends an expected_open_count that's
    SMALLER than the actual answered count (shouldn't happen but
    possible if RL_SCENARIO is undefined and only BOSS counts),
    no padding is added — just average over actual."""
    items = [
        {"phase": "real-life", "id": f"rl-{i}", "correct": True, "score": 1.0,
         "axis_1": 4, "axis_2": 4} for i in range(10)
    ]
    out = aggregate(items, subject="english", expected_open_count=5)
    # 10 actual > 5 expected → no padding, simple average over 10
    assert out["overall_axis_1"] == 4.0
    assert out["overall_axis_2"] == 4.0
    assert out["overall_pct"] == 100


def test_zero_answered_with_expected_count_pure_floor():
    """Edge case: student dismissed everything (zero items, but expected
    10). All 10 padded to floor → 25%."""
    out = aggregate([], subject="english", expected_open_count=10)
    # Zero answered → all 10 padded to (1, 1) → mean 1.0/1.0 → 25%
    assert out["overall_axis_1"] == 1.0
    assert out["overall_axis_2"] == 1.0
    assert out["overall_pct"] == 25
    assert out["band"]["key"] == "novice"
