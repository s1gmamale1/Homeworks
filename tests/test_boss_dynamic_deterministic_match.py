"""Hotfix 2026-05-14 — deterministic pre-check in check_boss_answer.

Bug context:
    Boss grading on origin/server was 100% LLM-judged. Students typing
    the exact canonical from the rubric (e.g. "headache and cold") sometimes
    still saw the LLM mark them wrong. Plan-4's regular-phase grading
    already does deterministic-first → AI-fallback; the boss path skipped
    that protection.

Fix:
    Normalize student_answer + canonical + accepted_variants and compare
    verbatim BEFORE calling the LLM. On match → instant correct verdict,
    no LLM call. No match → fall through to the existing LLM path.

This file pins the contract.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from server.services import boss_dynamic
from server.services.boss_dynamic import (
    BossAnswerVerdict,
    _deterministic_correct_check,
    _normalize_for_match,
    _accepted_normalized_answers,
)


# ---------------------------------------------------------------------------
# _normalize_for_match — the canonical form for comparison
# ---------------------------------------------------------------------------


def test_normalize_lowercases_and_strips():
    assert _normalize_for_match("  Headache And Cold  ") == "headache and cold"


def test_normalize_collapses_internal_whitespace():
    assert _normalize_for_match("3.33   %") == "3.33 %"
    assert _normalize_for_match("hello\tworld\n\nfoo") == "hello world foo"


def test_normalize_strips_trailing_terminal_punctuation():
    assert _normalize_for_match("Yes.") == "yes"
    assert _normalize_for_match("Headache and cold!") == "headache and cold"
    assert _normalize_for_match("3.33%;") == "3.33%"


def test_normalize_handles_none_and_non_str():
    assert _normalize_for_match(None) == ""
    assert _normalize_for_match(42) == ""
    assert _normalize_for_match({"q": "x"}) == ""


def test_normalize_preserves_internal_punctuation():
    """Internal decimal points, percent signs, currency etc. must survive —
    only TRAILING terminal marks are stripped."""
    assert _normalize_for_match("$3.33") == "$3.33"
    assert _normalize_for_match("3.33%") == "3.33%"
    assert _normalize_for_match("e.g., x and y") == "e.g., x and y"


# ---------------------------------------------------------------------------
# _accepted_normalized_answers — single source of truth for accepted set
# ---------------------------------------------------------------------------


def test_accepted_combines_canonical_and_variants():
    expected = {
        "canonical": "Headache and Cold",
        "accepted_variants": ["headache + cold", "head ache and cold"],
    }
    accepted = _accepted_normalized_answers(expected)
    assert "headache and cold" in accepted
    assert "headache + cold" in accepted
    assert "head ache and cold" in accepted


def test_accepted_drops_empty_entries():
    expected = {
        "canonical": "",
        "accepted_variants": ["", "  ", "real answer"],
    }
    accepted = _accepted_normalized_answers(expected)
    assert accepted == ["real answer"]


def test_accepted_handles_missing_keys():
    assert _accepted_normalized_answers({}) == []
    assert _accepted_normalized_answers({"canonical": "x"}) == ["x"]


# ---------------------------------------------------------------------------
# _deterministic_correct_check — the pre-check used by check_boss_answer
# ---------------------------------------------------------------------------


def _expected(canonical: str, variants: list[str] | None = None) -> dict:
    return {
        "canonical": canonical,
        "accepted_variants": variants or [],
        "notes": "",
    }


def test_exact_canonical_match_returns_correct_verdict():
    """The exact bug from the screenshot: canonical 'headache and cold',
    student types 'headache and cold' → must mark correct without LLM."""
    v = _deterministic_correct_check("headache and cold", _expected("headache and cold"))
    assert v is not None
    assert v.is_correct is True
    assert v.score == 1.0
    assert v.confidence == 1.0
    assert v.damage_multiplier == 1.0
    assert v.ai_unavailable is False  # NOT a fallback — this is the happy path


def test_exact_variant_match_returns_correct_verdict():
    """Student types a value listed in accepted_variants → correct."""
    v = _deterministic_correct_check(
        "3.33",
        _expected("3.33%", variants=["3.33", "3.33 foiz"]),
    )
    assert v is not None
    assert v.is_correct is True


def test_case_insensitive_match():
    v = _deterministic_correct_check("HEADACHE AND COLD", _expected("headache and cold"))
    assert v is not None and v.is_correct is True


def test_whitespace_variation_match():
    """Extra spaces, tabs, leading/trailing — all normalized to the same form."""
    v = _deterministic_correct_check(
        "  headache  and  cold  ",
        _expected("headache and cold"),
    )
    assert v is not None and v.is_correct is True


def test_trailing_punctuation_match():
    """Period, exclamation, etc. at the end shouldn't block a match."""
    for student in ("headache and cold.", "headache and cold!", "headache and cold;"):
        v = _deterministic_correct_check(student, _expected("headache and cold"))
        assert v is not None, f"Trailing punctuation in {student!r} should match"
        assert v.is_correct is True


def test_empty_student_answer_falls_through_to_llm():
    """Empty input → return None so the LLM path can produce a 'try again'
    response instead of a fake correct verdict."""
    v = _deterministic_correct_check("", _expected("headache and cold"))
    assert v is None


def test_empty_canonical_and_variants_falls_through():
    """No rubric anchor → can't pre-check. Must defer to LLM."""
    v = _deterministic_correct_check("anything", _expected("", variants=[]))
    assert v is None


def test_partial_match_falls_through_to_llm():
    """'headache' alone isn't 'headache and cold' — let the LLM decide
    whether it deserves partial credit. The pre-check is EXACT match only."""
    v = _deterministic_correct_check("headache", _expected("headache and cold"))
    assert v is None


def test_paraphrase_falls_through_to_llm():
    """Semantic equivalents must NOT short-circuit — that's the LLM's job."""
    v = _deterministic_correct_check(
        "a head pain and a cold virus",
        _expected("headache and cold"),
    )
    assert v is None


def test_non_match_falls_through_to_llm():
    """Outright wrong answer → return None. The LLM marks it incorrect and
    explains why. Pre-check is correct-only (one-way gate)."""
    v = _deterministic_correct_check(
        "completely different answer",
        _expected("headache and cold"),
    )
    assert v is None


# ---------------------------------------------------------------------------
# Integration — check_boss_answer wires the pre-check correctly
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_boss_answer_short_circuits_on_exact_match():
    """When the student types the canonical answer, ai_gateway.generate_structured
    MUST NOT be called. This is the cost + correctness win — no LLM round
    trip needed for unambiguous matches."""
    with patch(
        "server.services.boss_dynamic.ai_gateway.generate_structured",
        new_callable=AsyncMock,
    ) as mock_llm:
        verdict = await boss_dynamic.check_boss_answer(
            question_text="What is the medical condition?",
            expected_answer={
                "canonical": "headache and cold",
                "accepted_variants": [],
                "notes": "",
            },
            rubric={"full_credit": ["headache and cold"]},
            student_answer="headache and cold",
            target_skill="diagnosis",
            difficulty="medium",
        )
    assert verdict.is_correct is True
    assert verdict.score == 1.0
    assert mock_llm.call_count == 0, (
        "LLM must NOT be called when deterministic pre-check matches — "
        "wastes tokens and risks the LLM disagreeing with the exact match"
    )


@pytest.mark.asyncio
async def test_check_boss_answer_calls_llm_on_paraphrase():
    """Inverse: when the student answer doesn't match the canonical
    verbatim, the LLM path MUST fire — semantic judgment is still needed
    for paraphrases and partial credit."""
    from server.schemas.ai_contracts import BossAnswerCheckResult

    fake_llm_result = BossAnswerCheckResult(
        is_correct=False,
        score=0.3,
        confidence=0.7,
        feedback="Not quite — be more specific.",
        misconception_tags=["meaning_in_context"],
        damage_multiplier=1.0,
        difficulty_recommendation="stay",
        should_retry_same_skill=True,
    )
    with patch(
        "server.services.boss_dynamic.ai_gateway.generate_structured",
        new_callable=AsyncMock,
        return_value=fake_llm_result,
    ) as mock_llm:
        verdict = await boss_dynamic.check_boss_answer(
            question_text="What is the medical condition?",
            expected_answer={
                "canonical": "headache and cold",
                "accepted_variants": [],
                "notes": "",
            },
            rubric={"full_credit": ["headache and cold"]},
            student_answer="just a headache",
            target_skill="diagnosis",
            difficulty="medium",
        )
    assert mock_llm.call_count == 1, "LLM must be called when no exact match"
    assert verdict.is_correct is False
    assert verdict.score == 0.3


@pytest.mark.asyncio
async def test_check_boss_answer_pre_check_works_on_case_and_whitespace():
    """Realistic typing — student capitalizes or adds extra spaces. Pre-check
    must still hit and skip the LLM."""
    with patch(
        "server.services.boss_dynamic.ai_gateway.generate_structured",
        new_callable=AsyncMock,
    ) as mock_llm:
        verdict = await boss_dynamic.check_boss_answer(
            question_text="?",
            expected_answer={"canonical": "headache and cold", "accepted_variants": [], "notes": ""},
            rubric={},
            student_answer="  Headache And Cold!  ",
            target_skill="diagnosis",
            difficulty="medium",
        )
    assert verdict.is_correct is True
    assert mock_llm.call_count == 0
