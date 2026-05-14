"""Regression — boss damage on correct answer must never be zero.

Bug context (2026-05-14):
    Student answered "3.33%" to a boss question whose canonical answer was
    "3.33". The LLM verdict was is_correct=true, but the damage shown on the
    runtime was "−0 HP" — boss took no damage despite the correct answer.

Root cause:
    server/services/boss_dynamic.py::calculate_damage maps score < 0.60 to
    raw=0 (wrong-answer branch). The LLM was returning is_correct=true with
    score < 0.60 — semantically inconsistent — and calculate_damage took the
    score at face value.

Defensive fix (this test file's contract):
    _verdict_from_gateway now floors score to 0.60 and damage_multiplier to
    1.0 when is_correct=true, so calculate_damage always returns >= half base
    damage on a correct answer. When is_correct=false, no floors apply.
"""
from __future__ import annotations

from server.services.boss_dynamic import (
    _verdict_from_gateway,
    calculate_damage,
    BASE_DAMAGE,
    _CORRECT_SCORE_FLOOR,
    _CORRECT_MULTIPLIER_FLOOR,
)
from server.schemas.ai_contracts import BossAnswerCheckResult


def _result(**kw) -> BossAnswerCheckResult:
    """BossAnswerCheckResult with sane defaults that tests can override."""
    base = dict(
        is_correct=True,
        score=0.95,
        confidence=0.85,
        feedback="To'g'ri",
        misconception_tags=[],
        damage_multiplier=1.0,
        difficulty_recommendation="stay",
        should_retry_same_skill=False,
    )
    base.update(kw)
    return BossAnswerCheckResult(**base)


def test_verdict_floors_score_when_is_correct_and_score_below_floor():
    """LLM returns is_correct=true + score=0.4 → verdict.score floored to 0.60.
    Without this, calculate_damage's score<0.60 branch returns raw=0 and the
    student sees '✓ To'g'ri! −0 HP'."""
    v = _verdict_from_gateway(_result(is_correct=True, score=0.4))
    assert v.is_correct is True
    assert v.score >= _CORRECT_SCORE_FLOOR, (
        f"correct answer score must be floored to {_CORRECT_SCORE_FLOOR}, "
        f"got {v.score}"
    )


def test_verdict_floors_multiplier_when_is_correct_and_multiplier_below_floor():
    """LLM returns is_correct=true + damage_multiplier=0.3 → floored to 1.0.
    Sub-1.0 modifier on a correct answer is semantically inconsistent with
    the binary correctness signal."""
    v = _verdict_from_gateway(_result(is_correct=True, damage_multiplier=0.3))
    assert v.damage_multiplier >= _CORRECT_MULTIPLIER_FLOOR


def test_verdict_does_not_alter_high_score_when_is_correct():
    """Floor must not accidentally clamp DOWN — only up. score=0.95 stays."""
    v = _verdict_from_gateway(_result(is_correct=True, score=0.95))
    assert v.score == 0.95


def test_verdict_does_not_alter_high_multiplier_when_is_correct():
    """A 1.3x multiplier (e.g. exemplary answer) must survive the floor."""
    v = _verdict_from_gateway(_result(is_correct=True, damage_multiplier=1.3))
    assert v.damage_multiplier == 1.3


def test_verdict_does_not_floor_when_is_correct_false():
    """Wrong answers must keep their low scores — that's how the route layer
    correctly skips damage. Flooring on is_correct=false would inflate
    wrong-answer signal."""
    v = _verdict_from_gateway(_result(
        is_correct=False, score=0.2, damage_multiplier=0.5,
        feedback="Not quite — try again.",
    ))
    assert v.is_correct is False
    assert v.score == 0.2  # NOT floored
    # Multiplier still clamped to the global [0.0, 1.5] range but NOT
    # raised by the is_correct floor.
    assert v.damage_multiplier == 0.5


def test_calculate_damage_after_floor_is_nonzero_for_every_difficulty():
    """End-to-end smoke: a correct answer that hits the floor must produce
    non-zero HP damage on EVERY difficulty tier. Hard regression for the
    '−0 HP on correct' bug."""
    for difficulty in ("easy", "medium", "hard"):
        verdict = _verdict_from_gateway(_result(
            is_correct=True, score=0.4, damage_multiplier=0.5,
        ))
        damage = calculate_damage(
            verdict.score, difficulty, multiplier=verdict.damage_multiplier
        )
        assert damage > 0, (
            f"correct answer must deal non-zero damage on {difficulty} "
            f"(got {damage}; verdict.score={verdict.score}, "
            f"verdict.multiplier={verdict.damage_multiplier})"
        )
        # Specifically: post-floor score=0.60 hits calculate_damage's
        # half-damage branch: raw = int(base * 0.5) (truncation, not
        # rounding — matches the implementation). Then damage =
        # int(round(raw * 1.0)) = raw.
        expected_raw = int(BASE_DAMAGE[difficulty] * 0.5)
        expected = int(round(expected_raw * _CORRECT_MULTIPLIER_FLOOR))
        assert damage == expected, (
            f"{difficulty}: expected {expected} HP damage (half base * floored "
            f"multiplier), got {damage}"
        )


def test_calculate_damage_still_returns_zero_on_genuine_wrong_answer():
    """Counterpart to the above — wrong answers must STILL deal zero damage.
    The fix is is_correct-gated; it doesn't change wrong-answer semantics."""
    verdict = _verdict_from_gateway(_result(
        is_correct=False, score=0.3, damage_multiplier=1.0,
        feedback="Wrong — try again.",
    ))
    damage = calculate_damage(
        verdict.score, "hard", multiplier=verdict.damage_multiplier
    )
    assert damage == 0, (
        "wrong answer must still deal 0 damage; floor only applies "
        "when is_correct=true"
    )
