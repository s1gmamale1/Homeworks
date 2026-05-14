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


# ---------------------------------------------------------------------------
# 2026-05-13 audit Bug #8 — hybrid token+SequenceMatcher skill matching
# ---------------------------------------------------------------------------


def test_match_skill_to_stem_token_overlap_beats_sequencematcher_for_short_tokens():
    """Bug #8 fix: SequenceMatcher.ratio() between a short skill token
    ('nisbiy xatolik', 14 chars) and a long haystack (300 chars) tanks the
    score. The new hybrid scoring takes max(token-overlap, seq-ratio) so
    legitimate short-target matches still clear the 0.40 threshold."""
    long_haystack_stem = _stem(
        "(750 ± 1) m o'lchovning nisbiy xatoligini foizda yaxlit ikki "
        "xonali toping. Nisbiy xatolik aniq fizik o'lchovlar bo'yicha "
        "o'lchov natijasining haqiqiy qiymatdan og'ish darajasini ifoda etadi. "
        "Bu masalada o'lchov 750 metrga teng va xato darajasi 1 metrdir.",
        "medium",
        tags="[Bloom: L3]",
    )
    matched = boss_dynamic._match_skill_to_stem("nisbiy xatolik", [long_haystack_stem])
    assert matched is not None, (
        "Hybrid scoring (token-overlap) must rescue short skill tokens "
        "against long haystacks where pure SequenceMatcher ratio would fail"
    )


def test_tokenize_skill_filters_noise_tokens():
    """Tokens shorter than _SKILL_TOKEN_MIN_LEN must be excluded so single-
    letter or two-letter fragments don't dominate the overlap fraction."""
    assert boss_dynamic._tokenize_skill("sign_error") == {"sign", "error"}
    # Single + double letter tokens are filtered ("a", "of"); "the" stays (3 chars).
    assert boss_dynamic._tokenize_skill("a of foo") == {"foo"}
    assert boss_dynamic._tokenize_skill("nisbiy xatolik") == {"nisbiy", "xatolik"}
    assert boss_dynamic._tokenize_skill("") == set()


# ---------------------------------------------------------------------------
# 2026-05-13 audit Bug #9 — language drift detection + retry
# ---------------------------------------------------------------------------


def test_detect_language_drift_flags_english_on_uzbek_homework():
    """Bug #9: when boss_policy.language='uz' and Kimi generates English
    text, the validator must reject with 'language_drift'. Threshold is
    3+ English function-word hits — guards against single-borrowed-word
    false positives (e.g. 'PISA', 'Bloom', 'error')."""
    # 5+ English indicators on a uz homework — must trip
    reason = boss_dynamic._detect_language_drift(
        question_text="A student measures the length of a school bench with a ruler.",
        target_skill="sign_error",
        expected_language="uz",
    )
    assert reason is not None
    assert "language_drift" in reason


def test_detect_language_drift_allows_borrowed_terminology():
    """Mixed Uzbek with one or two English technical terms must NOT trip."""
    reason = boss_dynamic._detect_language_drift(
        question_text="Buzan tomonidan taklif etilgan PISA standartiga muvofiq o'rganish",
        target_skill="nisbiy xatolik",
        expected_language="uz",
    )
    assert reason is None, (
        "Borrowed terminology ('PISA', 'Buzan') must not trip language_drift"
    )


def test_detect_language_drift_skipped_for_english_homework():
    """For English homeworks, English text is correct — must not trip."""
    reason = boss_dynamic._detect_language_drift(
        question_text="A student measures the length of a pencil with a ruler.",
        target_skill="measurement_error",
        expected_language="en",
    )
    assert reason is None


# ---------------------------------------------------------------------------
# Bug #3 follow-up (2026-05-14) — snake_case is an INPUT problem, not an
# OUTPUT validation problem.
#
# Pre-fix: _detect_language_drift flagged English snake_case in target_skill
# and triggered a hard reject on output. When the LLM persisted with English
# (because weak_topics[0] was already English snake_case in the input), the
# retry also produced snake_case → 502 → boss session ends mid-arc.
#
# Post-fix: snake_case is scrubbed at the INPUT side in
# boss_context_builder.build_boss_context — weak_topics like "sign_error"
# never reach the LLM, so it never echoes them. _detect_language_drift now
# only checks function-word density (the legitimate "wholesale drift to
# English" signal). Snake_case in target_skill is no longer a rejection.
# ---------------------------------------------------------------------------


def test_detect_language_drift_does_not_reject_snake_case_alone():
    """Bug #3 follow-up: snake_case-only target_skill on uz/ru lesson must
    NOT trip drift detection. We handle this via input scrubbing instead
    (see test_boss_context_authored_stems.py for the input-side coverage).
    Pre-fix produced 502s when the LLM persisted with English skill names."""
    reason = boss_dynamic._detect_language_drift(
        question_text="100 gramm dorida nisbiy xatolikni foizda toping.",
        target_skill="sign_error",
        expected_language="uz",
    )
    assert reason is None, (
        "Snake_case in target_skill alone must NOT trigger drift rejection; "
        "the question_text is clean Uzbek. Input-side scrubbing prevents the "
        "English echo cycle without producing 502s."
    )


def test_detect_language_drift_does_not_flag_uzbek_space_separated_target_skill():
    """A legitimate Uzbek target_skill ('nisbiy xatolik') has a SPACE, not an
    underscore — and the question_text is clean Uzbek. No drift."""
    reason = boss_dynamic._detect_language_drift(
        question_text="Nisbiy xatolikni hisoblang.",
        target_skill="nisbiy xatolik",
        expected_language="uz",
    )
    assert reason is None


def test_detect_language_drift_does_not_flag_single_token_target_skill():
    """A single ASCII token (e.g. 'measurement') with clean Uzbek question
    text must not trip — borrowed single English terms are tolerated."""
    reason = boss_dynamic._detect_language_drift(
        question_text="O'lchov xatoligini toping.",
        target_skill="measurement",
        expected_language="uz",
    )
    assert reason is None


def test_detect_language_drift_does_not_flag_snake_case_on_english_homework():
    """On an English homework, snake_case skill names are correct — guard
    short-circuits on non-uz/ru languages."""
    reason = boss_dynamic._detect_language_drift(
        question_text="Find the relative error of the measurement.",
        target_skill="sign_error",
        expected_language="en",
    )
    assert reason is None


def test_validate_generated_question_accepts_clean_uzbek_with_snake_case_skill():
    """Bug #3 follow-up regression: a Uzbek question_text with an English
    snake_case target_skill must validate cleanly. Pre-fix this raised
    BossQuestionRejected and produced 502s when the LLM retry also kept
    snake_case. Post-fix, input scrubbing is the only defense and snake_case
    on output is accepted (cosmetic metadata only)."""
    raw = {
        "question_text": "100 gramm dorida nisbiy xatolikni foizda toping.",
        "expected_answer": {"canonical": "5%"},
        "rubric": {"full_credit": ["5%"]},
        "target_skill": "format_error",
        "difficulty": "medium",
    }
    # Must NOT raise — only function-word density triggers a reject now.
    result = boss_dynamic._validate_generated_question(
        raw,
        asked_questions=[],
        stems=[],
        pool_max=None,
        expected_language="uz",
    )
    assert result.target_skill == "format_error"


def test_validate_generated_question_still_rejects_full_english_drift_on_uz_homework():
    """Defense against the OTHER drift mode — when the LLM goes fully English
    (function-word density >= 3 in question_text), the validator must still
    reject. This is the legitimate "wholesale language drift" we keep
    rejecting after the snake_case branch was removed."""
    raw = {
        "question_text": "A student measures the length of a school bench with a ruler.",
        "expected_answer": {"canonical": "0.5"},
        "rubric": {"full_credit": ["0.5"]},
        "target_skill": "measurement",
        "difficulty": "medium",
    }
    with pytest.raises(boss_dynamic.BossQuestionRejected) as exc:
        boss_dynamic._validate_generated_question(
            raw,
            asked_questions=[],
            stems=[],
            pool_max=None,
            expected_language="uz",
        )
    assert "language_drift" in str(exc.value)


# ---------------------------------------------------------------------------
# Bug A (2026-05-14) — _validate_generated_question strips HTML tags from
# LLM-generated question_text as defense in depth. Authored stems are
# stripped upstream in build_boss_context too; this is the safety net for
# anything the LLM injects on its own.
# ---------------------------------------------------------------------------


def test_validate_generated_question_strips_html_tags_from_question_text():
    """If the LLM echoes `<strong>...</strong>` from an authored stem (or
    invents inline markup), the validator must return clean text. Runtime
    renders via textContent so any surviving tag becomes a literal character
    on the student's screen."""
    raw = {
        "question_text": "<strong>Translate to English</strong>, using \"have to\".",
        "expected_answer": {"canonical": "ok"},
        "rubric": {"full_credit": ["ok"]},
        "target_skill": "translation",
        "difficulty": "medium",
    }
    result = boss_dynamic._validate_generated_question(
        raw,
        asked_questions=[],
        stems=[],
        pool_max=None,
        expected_language="en",
    )
    assert "<strong>" not in result.question_text
    assert "</strong>" not in result.question_text
    assert "Translate to English" in result.question_text


def test_validate_generated_question_length_check_uses_stripped_text():
    """A long question with HTML markup must be length-checked against the
    STRIPPED text. Otherwise a question that's actually within the cap could
    fail just because of `<strong>...</strong>` padding."""
    # 100 visible characters + 17 chars of HTML markup = 117 raw, 100 stripped
    visible = "x" * 100
    raw = {
        "question_text": f"<strong>{visible}</strong>",
        "expected_answer": {"canonical": "ok"},
        "rubric": {"full_credit": ["ok"]},
        "target_skill": "translation",
        "difficulty": "medium",
    }
    result = boss_dynamic._validate_generated_question(
        raw,
        asked_questions=[],
        stems=[],
        pool_max=None,
        max_question_length=110,  # would reject 117 raw, accept 100 stripped
        expected_language="en",
    )
    assert len(result.question_text) <= 110
    assert "<strong>" not in result.question_text


def test_validate_generated_question_rejects_english_on_uzbek_homework():
    """End-to-end: feed an English BossQuestionGenerated through the
    validator with expected_language='uz' and assert rejection."""
    english_raw = {
        "question_text": "A student measures the length of a school bench with a ruler.",
        "expected_answer": {"canonical": "0.5"},
        "rubric": {"full_credit": ["0.5"]},
        "target_skill": "sign_error",
        "difficulty": "medium",
    }
    with pytest.raises(boss_dynamic.BossQuestionRejected) as exc:
        boss_dynamic._validate_generated_question(
            english_raw,
            asked_questions=[],
            stems=[],
            pool_max=None,
            expected_language="uz",
        )
    assert "language_drift" in str(exc.value)


@pytest.mark.asyncio
async def test_language_drift_rejection_triggers_one_retry_with_emphasis():
    """Bug #9: when validator rejects with 'language_drift', generate_boss_question
    must retry once with explicit language emphasis. Pin the retry count
    (exactly 2) and verify the retry prompt contains the emphasis."""
    boss_context = {
        "session_id": "test-sess",
        "homework_id": "test-hw",
        "authored_question_stems": [{
            "question_text": "Nisbiy xatolikni toping",
            "tags": "",
            "hint": "",
            "authored_difficulty": "medium",
        }],
        "phase_summaries": [{"phase": "practice", "score": 0.5}],
        "authored_difficulty_floor": "medium",
        "asked_questions": [],
        "boss_policy": {"max_question_length": 900, "language": "uz"},
    }

    english_output = BossQuestionGenerated(
        question_text="A student measures the length of a school bench with a ruler.",
        expected_answer=BossExpectedAnswer(canonical="0.5"),
        rubric=BossRubric(full_credit=["0.5"]),
        target_skill="sign_error",
        difficulty="medium",
        source_phase_ids=["practice"],
        why_this_question="english drift",
    )
    uzbek_output = BossQuestionGenerated(
        question_text="O'lchov natijasi 750 m bo'lib, xato 1 m. Nisbiy xatolikni toping.",
        expected_answer=BossExpectedAnswer(canonical="0.13%"),
        rubric=BossRubric(full_credit=["0.13%"]),
        target_skill="nisbiy xatolik",
        difficulty="medium",
        source_phase_ids=["practice"],
        why_this_question="retry uzbek",
    )

    call_count = {"n": 0}
    captured_prompts: list[str] = []

    async def _fake(*args, **kwargs):
        call_count["n"] += 1
        captured_prompts.append(kwargs.get("prompt", ""))
        return english_output if call_count["n"] == 1 else uzbek_output

    with patch.object(boss_dynamic.ai_gateway, "generate_structured", side_effect=_fake):
        out = await boss_dynamic.generate_boss_question(boss_context, difficulty="medium")

    assert call_count["n"] == 2, f"Expected 2 calls (1 retry), got {call_count['n']}"
    assert out.target_skill == "nisbiy xatolik"
    assert "_language_emphasis" in captured_prompts[1] or "REJECTED" in captured_prompts[1]


# ---------------------------------------------------------------------------
# 2026-05-13 audit Bug #10 — PromptTooLargeError translation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prompt_too_large_translates_to_boss_question_rejected():
    """Bug #10: _build_boss_input_section can raise PromptTooLargeError
    (RuntimeError subclass from ai_orchestrator). Before this fix it surfaced
    as an unhandled 500. Now it must be caught and re-raised as
    BossQuestionRejected('prompt_too_large: size=N cap=M') so the route
    returns 502 with a specific reason."""
    boss_context = {
        "session_id": "test-sess",
        "homework_id": "test-hw",
        "authored_question_stems": [{
            "question_text": "test", "tags": "", "hint": "", "authored_difficulty": "medium",
        }],
        "phase_summaries": [{"phase": "practice", "score": 0.5}],
        "authored_difficulty_floor": "medium",
        "asked_questions": [],
        "boss_policy": {"max_question_length": 900},
    }

    def _explode_with_size(*args, **kwargs):
        raise boss_dynamic.ai_orchestrator.PromptTooLargeError(size=999_999, cap=500_000)

    with patch.object(boss_dynamic.ai_orchestrator, "build_input_section", side_effect=_explode_with_size):
        with pytest.raises(boss_dynamic.BossQuestionRejected) as exc:
            await boss_dynamic.generate_boss_question(boss_context, difficulty="medium")

    assert "prompt_too_large" in str(exc.value)
    assert "size=999999" in str(exc.value)
