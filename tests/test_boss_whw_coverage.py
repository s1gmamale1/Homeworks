"""Boss-Arena Why→How→What coverage grading + damage + grade-band HP.

Guards the Boss-Arena spec §6 rework of boss_dynamic:
  (a) accuracy_tier boundary table
  (b) coverage_mean over partial/missing axes
  (c) calculate_damage with coverage vs the legacy score-fallback
  (d) the is_correct -> damage > 0 floor invariant
  (e) hint_penalty mapping
  (f) combo +20% after 3 full-accuracy answers, reset on wrong/hint
  (g) grade-band starting_hp_for (50/100/150 + override + default)

These are pure-logic tests — no DB, no AI, no HTTP.
"""
from __future__ import annotations

import pytest

from server.services import boss_dynamic
from server.services.boss_dynamic import (
    accuracy_tier,
    calculate_damage,
    coverage_mean,
    hint_penalty,
    starting_hp_for,
    BASE_DAMAGE,
    _CORRECT_SCORE_FLOOR,
    _verdict_from_gateway,
)
from server.routes.ai_plan5 import _combo_bonus_for
from server.schemas.ai_contracts import BossAnswerCheckResult


# ---------------------------------------------------------------------------
# (a) accuracy_tier boundary table (spec §6)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value,expected",
    [
        (1.00, 1.0),
        (0.85, 1.0),   # boundary — inclusive
        (0.8499, 0.7),
        (0.55, 0.7),   # boundary — inclusive
        (0.5499, 0.5),
        (0.30, 0.5),   # boundary — inclusive
        (0.2999, 0.0),
        (0.0, 0.0),
        (-0.5, 0.0),   # clamp below 0
        (1.5, 1.0),    # clamp above 1
    ],
)
def test_accuracy_tier_boundaries(value, expected):
    assert accuracy_tier(value) == expected


# ---------------------------------------------------------------------------
# (b) coverage_mean — partial / missing axes
# ---------------------------------------------------------------------------


def test_coverage_mean_all_three_axes():
    assert coverage_mean({"why": 0.6, "how": 0.6, "what": 0.6}) == pytest.approx(0.6)


def test_coverage_mean_partial_axes_only_averages_present():
    # Only why + what present -> mean of those two, NOT divided by 3.
    assert coverage_mean({"why": 0.8, "what": 0.6}) == pytest.approx(0.7)


def test_coverage_mean_none_and_empty_return_none():
    assert coverage_mean(None) is None
    assert coverage_mean({}) is None


def test_coverage_mean_ignores_non_numeric_and_bool():
    # bool is an int subclass; must be skipped. Non-numeric ignored.
    assert coverage_mean({"why": True, "how": "x", "what": 0.5}) == pytest.approx(0.5)
    # All non-usable -> None.
    assert coverage_mean({"why": True, "how": None}) is None


def test_coverage_mean_clamps_axis_values():
    assert coverage_mean({"why": 1.5, "how": -0.2}) == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# (c) calculate_damage — coverage vs legacy score-fallback tiers
# ---------------------------------------------------------------------------


def test_calculate_damage_uses_coverage_when_present():
    # coverage mean = 0.9 -> tier 1.0 -> medium base 20 * 1.0 = 20.
    dmg = calculate_damage(
        score=0.0,  # score is ignored when coverage present
        difficulty="medium",
        coverage={"why": 0.9, "how": 0.9, "what": 0.9},
    )
    assert dmg == 20


def test_calculate_damage_coverage_mid_tier():
    # coverage mean = 0.6 -> tier 0.7 -> hard base 30 * 0.7 = 21.
    dmg = calculate_damage(
        score=1.0, difficulty="hard",
        coverage={"why": 0.6, "how": 0.6, "what": 0.6},
    )
    assert dmg == round(30 * 0.7)


def test_calculate_damage_legacy_score_fallback_when_no_coverage():
    # No coverage -> falls back to score. score 0.95 -> tier 1.0 -> easy 10.
    assert calculate_damage(0.95, "easy") == 10
    # score 0.6 -> tier 0.7 -> medium 20 * 0.7 = 14.
    assert calculate_damage(0.6, "medium") == round(20 * 0.7)
    # score 0.2 -> tier 0.0 -> 0.
    assert calculate_damage(0.2, "hard") == 0


def test_calculate_damage_empty_coverage_dict_falls_back_to_score():
    # coverage={} is falsy -> score fallback path.
    assert calculate_damage(0.95, "medium", coverage={}) == 20


def test_calculate_damage_base_table_is_spec_section_6():
    assert BASE_DAMAGE == {"easy": 10, "medium": 20, "hard": 30}


# ---------------------------------------------------------------------------
# (d) is_correct -> damage > 0 floor invariant
# ---------------------------------------------------------------------------


def _result(**kw) -> BossAnswerCheckResult:
    base = dict(
        is_correct=True, score=0.95, confidence=0.85, feedback="To'g'ri",
        misconception_tags=[], damage_multiplier=1.0,
        difficulty_recommendation="stay", should_retry_same_skill=False,
        coverage={},
    )
    base.update(kw)
    return BossAnswerCheckResult(**base)


def test_correct_but_weak_coverage_still_deals_positive_damage():
    # "correct but weak": coverage mean in [0.30, 0.85). Verdict floors lift it
    # so accuracy tier is never 0.0 -> damage > 0 on every difficulty.
    for difficulty in ("easy", "medium", "hard"):
        verdict = _verdict_from_gateway(_result(
            is_correct=True, score=0.5,
            coverage={"why": 0.4, "how": 0.4, "what": 0.4},  # mean 0.4 < floor
        ))
        dmg = calculate_damage(
            verdict.score, difficulty,
            multiplier=verdict.damage_multiplier,
            coverage=verdict.coverage or None,
        )
        assert dmg > 0, f"correct-but-weak must deal >0 on {difficulty}; got {dmg}"


def test_correct_with_zero_coverage_is_lifted_to_positive_damage():
    # Contradictory all-zero coverage on a correct verdict -> floored so the
    # student never sees "-0 HP".
    verdict = _verdict_from_gateway(_result(
        is_correct=True, score=0.9,
        coverage={"why": 0.0, "how": 0.0, "what": 0.0},
    ))
    dmg = calculate_damage(
        verdict.score, "medium",
        multiplier=verdict.damage_multiplier,
        coverage=verdict.coverage or None,
    )
    assert dmg > 0


def test_wrong_answer_with_low_coverage_deals_zero_damage():
    # is_correct=False -> no floor. coverage mean 0.1 -> tier 0.0 -> 0 damage.
    verdict = _verdict_from_gateway(_result(
        is_correct=False, score=0.1, feedback="Try again.",
        coverage={"why": 0.1, "how": 0.1, "what": 0.1},
    ))
    dmg = calculate_damage(
        verdict.score, "hard",
        multiplier=verdict.damage_multiplier,
        coverage=verdict.coverage or None,
    )
    assert dmg == 0


def test_verdict_does_not_floor_coverage_when_incorrect():
    verdict = _verdict_from_gateway(_result(
        is_correct=False, score=0.2, feedback="No.",
        coverage={"why": 0.1, "how": 0.1, "what": 0.1},
    ))
    # Coverage left intact (low) on a wrong answer.
    assert coverage_mean(verdict.coverage) == pytest.approx(0.1)


# ---------------------------------------------------------------------------
# (e) hint_penalty mapping (spec §6)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "hints,expected",
    [(0, 1.0), (1, 0.8), (2, 0.6), (3, 0.3), (5, 0.3)],
)
def test_hint_penalty_mapping(hints, expected):
    assert hint_penalty(hints) == expected


def test_hint_penalty_reduces_damage_in_calculate_damage():
    # 2 hints -> 0.6 multiplier. medium base 20 * 1.0 tier * 0.6 = 12.
    dmg = calculate_damage(0.95, "medium", hints_used=2)
    assert dmg == round(20 * 1.0 * 0.6)


# ---------------------------------------------------------------------------
# (f) combo +20% after 3 full-accuracy answers; reset on wrong / hint
# ---------------------------------------------------------------------------


def _attempt(correct: int, score: float) -> dict:
    return {"correct": correct, "score": score}


def test_combo_bonus_applies_after_three_full_accuracy():
    prior = [_attempt(1, 0.9), _attempt(1, 0.95), _attempt(1, 1.0)]
    assert _combo_bonus_for(prior, hints_used=0) == boss_dynamic.COMBO_BONUS_FACTOR


def test_combo_bonus_not_applied_below_threshold():
    prior = [_attempt(1, 0.9), _attempt(1, 0.95)]  # only 2
    assert _combo_bonus_for(prior, hints_used=0) == 1.0


def test_combo_bonus_resets_on_wrong_answer():
    # The most-recent attempt is wrong -> tail streak is 0.
    prior = [_attempt(1, 0.9), _attempt(1, 0.95), _attempt(1, 1.0), _attempt(0, 0.1)]
    assert _combo_bonus_for(prior, hints_used=0) == 1.0


def test_combo_bonus_resets_on_low_score_correct_answer():
    # A correct-but-not-full-accuracy answer (score < 0.85) breaks the combo.
    prior = [_attempt(1, 0.9), _attempt(1, 0.95), _attempt(1, 1.0), _attempt(1, 0.6)]
    assert _combo_bonus_for(prior, hints_used=0) == 1.0


def test_combo_bonus_suppressed_when_hints_used():
    prior = [_attempt(1, 0.9), _attempt(1, 0.95), _attempt(1, 1.0)]
    assert _combo_bonus_for(prior, hints_used=1) == 1.0


def test_combo_bonus_multiplies_damage():
    # Full streak + 0 hints -> 1.2x. medium base 20 * 1.0 tier * 1.2 = 24.
    dmg = calculate_damage(0.95, "medium", combo_bonus=boss_dynamic.COMBO_BONUS_FACTOR)
    assert dmg == round(20 * 1.0 * 1.2)


# ---------------------------------------------------------------------------
# (g) grade-band starting_hp_for (50 / 100 / 150 + override + default)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "band,expected",
    [
        ("G1-4", 50),
        ("G5-8", 100),
        ("G9-11", 150),
        # schema GradeBand literals
        ("g1_4", 50),
        ("g5", 100),
        ("g6_8", 100),
        ("g9_11", 150),
        # raw numeric grade
        (3, 50),
        (8, 100),
        (10, 150),
        ("8", 100),
    ],
)
def test_starting_hp_for_band_mapping(band, expected):
    assert starting_hp_for(band, None) == expected


def test_starting_hp_for_override_wins():
    # A valid override beats the band HP.
    assert starting_hp_for("G1-4", 250) == 250
    assert starting_hp_for(None, 75) == 75


def test_starting_hp_for_override_below_floor_ignored():
    # Override < 10 is invalid -> fall back to band, then default.
    assert starting_hp_for("G5-8", 5) == 100
    assert starting_hp_for(None, 5) == 100  # default


def test_starting_hp_for_unknown_band_defaults_to_100():
    assert starting_hp_for(None, None) == 100
    assert starting_hp_for("nonsense", None) == 100
    assert starting_hp_for(0, None) == 100  # grade 0 is out of band range
