"""Plan Wave 2 — per-skill difficulty floor regression tests.

Guards the contract that:
  * ``_match_skill_to_stem`` picks the closest authored stem for a generator's
    ``target_skill``, returning ``None`` when nothing clears the threshold.
  * ``_resolve_skill_floor`` prefers the matched stem's ``authored_difficulty``
    and falls back to ``pool_max`` only when no stem matches.
  * ``_validate_generated_question`` rejects generated questions whose
    ``difficulty`` drops more than one step below the resolved floor.
  * ``generate_boss_question`` hard-clamps the difficulty UP to the floor when
    the gateway's repair retry produced an output that still violates the
    floor (better UX than 502-ing the runtime).

Test names describe the regression each guard, not the happy path.
"""
from __future__ import annotations

import logging
from unittest.mock import patch

import pytest

from server.services import boss_dynamic
from server.schemas.ai_contracts import (
    BossQuestionGenerated,
    BossExpectedAnswer,
    BossRubric,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stem(question_text: str, authored_difficulty: str, *, tags: str = "") -> dict:
    return {
        "question_text": question_text,
        "tags": tags,
        "hint": "",
        "authored_difficulty": authored_difficulty,
    }


def _valid_raw(**overrides) -> dict:
    """Return a dict matching the BossQuestionOutput / BossQuestionGenerated
    Pydantic shape with optional overrides."""
    base = {
        "question_text": "Absolyut xatolikni hisoblang.",
        "expected_answer": {
            "canonical": "0.05",
            "accepted_variants": ["5%"],
            "notes": "",
        },
        "rubric": {
            "full_credit": ["0.05"],
            "partial_credit": [],
            "common_mistakes": [],
        },
        "target_skill": "absolyut xatolik",
        "difficulty": "medium",
        "source_phase_ids": ["practice"],
        "why_this_question": "test",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# _match_skill_to_stem
# ---------------------------------------------------------------------------


def test_match_skill_to_stem_returns_best_overlap():
    pool = [
        _stem("Absolyut xatolikni toping", "easy", tags="[Bloom: L2]"),
        _stem("Nisbiy xatolikni hisoblang", "hard", tags="[Bloom: L3]"),
    ]
    matched = boss_dynamic._match_skill_to_stem("absolyut xatolik", pool)
    assert matched is not None
    assert matched["question_text"] == "Absolyut xatolikni toping"


def test_match_skill_to_stem_returns_none_below_threshold():
    pool = [
        _stem("Absolyut xatolikni toping", "easy"),
        _stem("Nisbiy xatolikni hisoblang", "hard"),
    ]
    # Use a target whose character set has minimal overlap with the pool so
    # the SequenceMatcher score falls below the 0.40 threshold. Naive English
    # phrases like "completely unrelated topic" can coincidentally score
    # 0.40+ from shared characters (t/o/p/i overlap with "toping"), so we
    # use a deliberately disjoint glyph set here.
    matched = boss_dynamic._match_skill_to_stem("zzz qqq vvv www", pool)
    assert matched is None


def test_match_skill_to_stem_handles_empty_pool_and_empty_target():
    # Empty target, empty pool → None
    assert boss_dynamic._match_skill_to_stem("", []) is None
    # Non-empty target, empty pool → None
    assert boss_dynamic._match_skill_to_stem("foo", []) is None
    # Empty target, non-empty pool → None
    pool = [_stem("Absolyut xatolikni toping", "easy")]
    assert boss_dynamic._match_skill_to_stem("", pool) is None


# ---------------------------------------------------------------------------
# _resolve_skill_floor
# ---------------------------------------------------------------------------


def test_resolve_skill_floor_returns_matched_stem_difficulty():
    """Matched stem's authored_difficulty wins over pool_max."""
    pool = [
        _stem("Absolyut xatolikni toping", "hard", tags="[Bloom: L3]"),
        _stem("Boshqa savol", "easy"),
    ]
    floor = boss_dynamic._resolve_skill_floor(
        "absolyut xatolik", pool, pool_max="medium"
    )
    assert floor == "hard"


def test_resolve_skill_floor_falls_back_to_pool_max_when_no_match():
    pool = [
        _stem("Absolyut xatolikni toping", "easy"),
        _stem("Nisbiy xatolikni hisoblang", "medium"),
    ]
    # Glyph-disjoint target so neither stem matches via SequenceMatcher
    # (>=0.40 threshold). Confirms the pool_max fallback path.
    floor = boss_dynamic._resolve_skill_floor(
        "zzz qqq vvv www", pool, pool_max="hard"
    )
    assert floor == "hard"


def test_resolve_skill_floor_returns_none_when_pool_empty():
    floor = boss_dynamic._resolve_skill_floor("some skill", [], pool_max=None)
    assert floor is None


# ---------------------------------------------------------------------------
# _validate_generated_question — floor enforcement
# ---------------------------------------------------------------------------


def test_validate_generated_question_rejects_difficulty_below_skill_floor():
    """Stem floor=hard, generated difficulty=easy is two ranks below — must
    be rejected."""
    stem = _stem(
        "Absolyut xatolikni hisoblang",
        "hard",
        tags="[Bloom: L3]",
    )
    raw = _valid_raw(
        target_skill="absolyut xatolik",
        difficulty="easy",
    )
    with pytest.raises(boss_dynamic.BossQuestionRejected) as exc:
        boss_dynamic._validate_generated_question(
            raw,
            asked_questions=[],
            stems=[stem],
            pool_max="hard",
        )
    assert exc.value.reason.startswith("difficulty_below_skill_floor")


def test_validate_passes_when_difficulty_within_one_step_of_floor():
    """Stem floor=hard, generated difficulty=medium is exactly one rank below
    — must be accepted."""
    stem = _stem(
        "Absolyut xatolikni hisoblang",
        "hard",
        tags="[Bloom: L3]",
    )
    raw = _valid_raw(
        target_skill="absolyut xatolik",
        difficulty="medium",
    )
    out = boss_dynamic._validate_generated_question(
        raw,
        asked_questions=[],
        stems=[stem],
        pool_max="hard",
    )
    assert isinstance(out, boss_dynamic.GeneratedBossQuestion)
    assert out.difficulty == "medium"


def test_validate_passes_when_no_pool_and_no_match():
    """Empty stems + pool_max=None → floor check is skipped entirely."""
    raw = _valid_raw(
        target_skill="anything",
        difficulty="easy",
    )
    out = boss_dynamic._validate_generated_question(
        raw,
        asked_questions=[],
        stems=[],
        pool_max=None,
    )
    assert out.difficulty == "easy"


# ---------------------------------------------------------------------------
# generate_boss_question — hard clamp on persistent floor violation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hard_clamp_after_repair_failure_logs_warning_and_returns_clamped(
    caplog,
):
    """Integration: when the gateway's repair retry returns a question whose
    difficulty STILL falls below the matched stem's floor, generate_boss_question
    must hard-clamp the difficulty up to that floor and log a warning rather
    than re-raising. This guards against a 502 propagating to the runtime
    purely due to a stubborn LLM output."""
    stem = {
        "question_text": "Absolyut xatolikni hisoblang",
        "tags": "[Bloom: L3]",
        "hint": "",
        "authored_difficulty": "hard",
    }
    boss_context = {
        "session_id": "test-sess",
        "homework_id": "test-hw",
        "authored_question_stems": [stem],
        "phase_summaries": [],
        "authored_difficulty_floor": "hard",
        "asked_questions": [],
        "boss_policy": {"max_question_length": 900},
    }

    # Mock gateway returns an output that violates the floor
    # (target_skill matches stem; difficulty=easy; floor=hard → reject).
    # The clamp branch should then re-validate with difficulty="hard"
    # (the matched stem's floor itself).
    mock_result = BossQuestionGenerated(
        question_text="Absolyut xatolikni qisqa hisoblang.",
        expected_answer=BossExpectedAnswer(canonical="0.05"),
        rubric=BossRubric(full_credit=["0.05"]),
        target_skill="absolyut xatolik",
        difficulty="easy",
        source_phase_ids=["practice"],
        why_this_question="test",
    )

    async def _fake_generate_structured(*args, **kwargs):
        return mock_result

    with patch.object(
        boss_dynamic.ai_gateway,
        "generate_structured",
        side_effect=_fake_generate_structured,
    ):
        with caplog.at_level(logging.WARNING, logger="nets.boss_dynamic"):
            out = await boss_dynamic.generate_boss_question(
                boss_context, difficulty="medium"
            )

    # Clamped to the matched stem's floor (hard).
    assert out.difficulty == "hard"
    assert any(
        "boss_difficulty_clamped_after_repair_fail" in rec.message
        for rec in caplog.records
    ), f"warning not emitted; got: {[r.message for r in caplog.records]}"


# ---------------------------------------------------------------------------
# 2026-05-13 audit fix #3 — anti-repetition retry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_anti_repetition_rejection_triggers_one_retry_with_emphasis(caplog):
    """Bug #3 from 2026-05-13 audit: BossQuestionRejected('repeats_previous')
    used to surface as an immediate 502 because the gateway's repair retry
    only fires on Pydantic/JSON errors. The audit fix adds a single manual
    retry inside generate_boss_question that re-calls the LLM with an
    emphatic anti-repetition note injected into the payload. This test pins
    the retry behavior: first call returns a duplicate, second call returns
    a fresh question, end result is the fresh question."""
    asked = [{"question_text": "Absolyut xatolikni hisoblang: a=23, x=23.5"}]
    boss_context = {
        "session_id": "test-sess",
        "homework_id": "test-hw",
        "authored_question_stems": [{
            "question_text": "Absolyut xatolikni hisoblang",
            "tags": "",
            "hint": "",
            "authored_difficulty": "medium",
        }],
        "phase_summaries": [{"phase": "practice", "score": 0.5}],
        "authored_difficulty_floor": "medium",
        "asked_questions": asked,
        "boss_policy": {"max_question_length": 900, "language": "uz"},
    }

    duplicate_output = BossQuestionGenerated(
        question_text="Absolyut xatolikni hisoblang: a=23, x=23.5",  # exact dup
        expected_answer=BossExpectedAnswer(canonical="0.5"),
        rubric=BossRubric(full_credit=["0.5"]),
        target_skill="absolyut xatolik",
        difficulty="medium",
        source_phase_ids=["practice"],
        why_this_question="first attempt",
    )
    fresh_output = BossQuestionGenerated(
        question_text="Nisbiy xatolikni foizda toping: a=100, x=102.",
        expected_answer=BossExpectedAnswer(canonical="2%"),
        rubric=BossRubric(full_credit=["2%", "2"]),
        target_skill="nisbiy xatolik",
        difficulty="medium",
        source_phase_ids=["practice"],
        why_this_question="retry — varied surface form",
    )

    call_count = {"n": 0}
    captured_prompts: list[str] = []

    async def _fake_generate_structured(*args, **kwargs):
        call_count["n"] += 1
        captured_prompts.append(kwargs.get("prompt", ""))
        return duplicate_output if call_count["n"] == 1 else fresh_output

    with patch.object(
        boss_dynamic.ai_gateway,
        "generate_structured",
        side_effect=_fake_generate_structured,
    ):
        with caplog.at_level(logging.WARNING, logger="nets.boss_dynamic"):
            out = await boss_dynamic.generate_boss_question(
                boss_context, difficulty="medium"
            )

    # Retry must have fired exactly once.
    assert call_count["n"] == 2, (
        f"Expected one retry (2 total calls), got {call_count['n']}"
    )
    # Final output must be the fresh question, not the duplicate.
    assert out.question_text == fresh_output.question_text
    # The retry prompt must include the emphatic anti-repetition note.
    assert "_anti_repetition_emphasis" in captured_prompts[1] or "REJECTED" in captured_prompts[1], (
        "Second LLM call must include the anti-repetition emphasis injection"
    )
    assert any(
        "anti-repetition rejection on attempt 1" in rec.message
        for rec in caplog.records
    ), "Retry log line missing"


@pytest.mark.asyncio
async def test_anti_repetition_retry_does_not_loop_forever():
    """If the retry ALSO returns a duplicate, the rejection must propagate
    as BossQuestionRejected — no infinite retry loop, no third call."""
    asked = [{"question_text": "Solve 12 + 5 step by step."}]
    boss_context = {
        "session_id": "test-sess",
        "homework_id": "test-hw",
        "authored_question_stems": [{
            "question_text": "Solve 12 + 5",
            "tags": "",
            "hint": "",
            "authored_difficulty": "easy",
        }],
        "phase_summaries": [{"phase": "practice", "score": 0.5}],
        "authored_difficulty_floor": "easy",
        "asked_questions": asked,
        "boss_policy": {"max_question_length": 900, "language": "en"},
    }
    dup = BossQuestionGenerated(
        question_text="Solve 12 + 5 step by step.",
        expected_answer=BossExpectedAnswer(canonical="17"),
        rubric=BossRubric(full_credit=["17"]),
        target_skill="addition",
        difficulty="easy",
        source_phase_ids=["practice"],
        why_this_question="",
    )

    call_count = {"n": 0}

    async def _always_dup(*args, **kwargs):
        call_count["n"] += 1
        return dup

    with patch.object(
        boss_dynamic.ai_gateway,
        "generate_structured",
        side_effect=_always_dup,
    ):
        with pytest.raises(boss_dynamic.BossQuestionRejected) as exc_info:
            await boss_dynamic.generate_boss_question(boss_context, difficulty="easy")

    assert "repeats_previous" in str(exc_info.value)
    assert call_count["n"] == 2, (
        f"Expected exactly 2 LLM calls (initial + 1 retry), got {call_count['n']}"
    )
