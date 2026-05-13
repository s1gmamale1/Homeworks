"""Plan 5 + Plan 7 — Dynamic Boss AI regression tests.

Each test guards a specific Plan 5/7 contract that, if regressed, would
either silently break the boss flow or weaken the answer-leak / state-ownership
/ prompt-contract invariants. Test names describe the regression they guard,
not the happy path.
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import patch

import pytest

from server.services import boss_dynamic
from server.services.boss_context_builder import (
    build_boss_context,
    _scrub_dict,
)
from server.db import boss_session_repo, attempts_repo
from server.schemas.ai_contracts import (
    BossQuestionGenerated,
    BossAnswerCheckResult,
    BossExpectedAnswer,
    BossRubric,
)


# ---------------------------------------------------------------------------
# Pure logic — damage / difficulty (deterministic, no DB, no AI)
# ---------------------------------------------------------------------------


def test_calculate_damage_clamps_multiplier_so_model_cannot_one_shot_boss():
    # Even if the model reports damage_multiplier=99, the boss can never lose
    # >37 HP from one medium-difficulty correct answer (15 base * 1.5 cap).
    dmg = boss_dynamic.calculate_damage(score=1.0, difficulty="medium", multiplier=99.0)
    assert dmg <= 25, f"multiplier should be clamped <=1.5x base; got {dmg}"


def test_calculate_damage_zero_below_60_score_regardless_of_difficulty():
    for diff in ("easy", "medium", "hard"):
        assert boss_dynamic.calculate_damage(0.59, diff) == 0
        assert boss_dynamic.calculate_damage(0.0, diff) == 0


def test_calculate_damage_invalid_difficulty_falls_back_to_medium_not_zero():
    # Defensive: a typo in the runtime should not silently zero damage on
    # correct answers.
    dmg = boss_dynamic.calculate_damage(1.0, "ULTRA-HARD")
    assert dmg == 15, f"unknown difficulty must fall back to medium=15, got {dmg}"


def test_next_difficulty_requires_two_correct_streak_before_escalating():
    # Single 0.95 score with streak=1 stays put — prevents a lucky guess
    # ramping difficulty after one question.
    streaks = boss_dynamic.BossStreaks(correct_streak=1, wrong_streak=0)
    assert boss_dynamic.next_difficulty("medium", 0.95, streaks) == "medium"
    streaks2 = boss_dynamic.BossStreaks(correct_streak=2, wrong_streak=0)
    assert boss_dynamic.next_difficulty("medium", 0.95, streaks2) == "hard"


def test_next_difficulty_de_escalates_on_two_wrong_streak():
    streaks = boss_dynamic.BossStreaks(correct_streak=0, wrong_streak=2)
    assert boss_dynamic.next_difficulty("hard", 0.3, streaks) == "easy"


# ---------------------------------------------------------------------------
# Generated-question validation — guards the contract surface
# ---------------------------------------------------------------------------


def test_generated_question_rejected_when_missing_expected_answer():
    raw = {
        "question_text": "What is 2+2?",
        "expected_answer": {},  # empty — Pydantic will reject (canonical required)
        "rubric": {"full_credit": ["4"]},
        "target_skill": "addition",
        "difficulty": "easy",
    }
    with pytest.raises(boss_dynamic.BossQuestionRejected) as exc:
        boss_dynamic._validate_generated_question(raw, asked_questions=[])
    # Plan 7: Pydantic validation now catches this before the manual check.
    assert "pydantic_validation" in str(exc.value) or "missing_expected_answer" in str(exc.value)


def test_generated_question_rejected_when_paraphrase_of_previous():
    asked = [{"question_text": "Solve x + 2 = 5"}]
    raw = {
        "question_text": "  solve  X + 2 = 5  ",  # same after normalize
        "expected_answer": {"canonical": "3"},
        "rubric": {"full_credit": ["3"]},
        "target_skill": "linear_eq",
        "difficulty": "medium",
    }
    with pytest.raises(boss_dynamic.BossQuestionRejected) as exc:
        boss_dynamic._validate_generated_question(raw, asked_questions=asked)
    assert "repeats_previous" in str(exc.value)


def test_generated_question_rejected_when_near_duplicate_slips_past_strict_equality():
    # Regression for the 2026-05-13 bug: Kimi returned a question for Q2 that
    # differed from Q1 by only a punctuation/word tweak, which strict equality
    # (the pre-fix anti-repetition check) let through. SequenceMatcher.ratio
    # >= 0.85 must catch it. Fixture: trailing period + one-digit change — NOT
    # byte-equal after whitespace normalize, so the pre-fix code passed this
    # through; the new fuzzy check must reject it.
    asked = [{"question_text": "Find the absolute error of 12.345 meters"}]
    raw = {
        "question_text": "Find the absolute error of 12.346 meters.",
        "expected_answer": {"canonical": "0.001"},
        "rubric": {"full_credit": ["0.001"]},
        "target_skill": "absolyut_xatolik",
        "difficulty": "medium",
    }
    with pytest.raises(boss_dynamic.BossQuestionRejected) as exc:
        boss_dynamic._validate_generated_question(raw, asked_questions=asked)
    assert "repeats_previous" in str(exc.value)


def test_generated_question_passes_when_topically_related_but_substantively_different():
    # Counterpart to the near-duplicate test: two different questions on the
    # same topic must NOT trip the fuzzy similarity threshold. Without this
    # the generator could be blocked from asking multiple legitimate questions
    # about, e.g., absolute error in one boss session.
    asked = [{"question_text": "Find the absolute error of 12.345 meters"}]
    raw = {
        "question_text": "Round 0.084736 to two significant figures.",
        "expected_answer": {"canonical": "0.085"},
        "rubric": {"full_credit": ["0.085"]},
        "target_skill": "yaxlitlash",
        "difficulty": "medium",
    }
    boss_dynamic._validate_generated_question(raw, asked_questions=asked)


def test_generated_question_rejects_invalid_difficulty_token():
    raw = {
        "question_text": "What is the meaning of 'according to'?",
        "expected_answer": {"canonical": "as stated by"},
        "rubric": {"full_credit": ["as stated by"]},
        "target_skill": "meaning_in_context",
        "difficulty": "TRIVIAL",  # not in allowed — Pydantic Literal rejects
    }
    with pytest.raises(boss_dynamic.BossQuestionRejected) as exc:
        boss_dynamic._validate_generated_question(raw, asked_questions=[])
    # Plan 7: Pydantic Literal catches invalid enum values.
    assert "pydantic_validation" in str(exc.value) or "invalid_difficulty" in str(exc.value)


# ---------------------------------------------------------------------------
# Context builder — answer-leak invariant
# ---------------------------------------------------------------------------


def test_scrub_dict_removes_answer_leak_keys_recursively():
    payload = {
        "question_text": "x?",
        "expected": "5",
        "ans": ["5"],
        "nested": {
            "accepted_answers": ["5", "five"],
            "answer_spec": {"type": "numeric", "expected": 5.0},
            "ok_field": "keep me",
        },
    }
    cleaned = _scrub_dict(payload)
    assert "expected" not in cleaned
    assert "ans" not in cleaned
    assert "accepted_answers" not in cleaned["nested"]
    assert "answer_spec" not in cleaned["nested"]
    assert cleaned["nested"]["ok_field"] == "keep me"


# ---------------------------------------------------------------------------
# End-to-end via the FastAPI client (with mocked LLM)
# ---------------------------------------------------------------------------


def _make_homework(client, *, hw_id_hint: str = "plan5-hw") -> str:
    """Insert a homework with no `boss_questions` so we prove the dynamic
    flow does not depend on the legacy static list (Plan 5 acceptance test 1).
    """
    payload = {
        "title": f"Plan 5 dynamic boss test ({hw_id_hint})",
        "subject": "english",
        "grade": 8,
        "mode": "hard",
        "family": "til-fanlar",
        "content_json": {
            "title": f"Plan 5 dynamic boss test ({hw_id_hint})",
            "subject": "english",
            "grade": 8,
            "language": "en",
            "preview": {"text": "according to means as stated by"},
        },
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _seed_attempts(session_id: str, hw_id: str) -> None:
    """Insert phase_attempts so the context builder has weak-topic signal."""
    async def go():
        for i in range(2):
            await attempts_repo.add_phase_attempt(
                session_id=session_id, hw_id=hw_id,
                phase="practice", subphase="sentence-fill",
                question_id=f"q{i}", checker_source="ai_judge",
                correct=0, score=0.2, confidence=0.9,
                feedback="not quite",
                misconception_tags_json=json.dumps(["meaning_in_context", "according_to"]),
            )
        await attempts_repo.add_phase_attempt(
            session_id=session_id, hw_id=hw_id,
            phase="practice", subphase="sentence-fill",
            question_id="q_strong", checker_source="ai_judge",
            correct=1, score=1.0, confidence=0.95,
            feedback="great",
            misconception_tags_json=json.dumps(["basic_translation"]),
        )
    asyncio.run(go())


def _boss_question_factory(**overrides) -> BossQuestionGenerated:
    """Return a valid BossQuestionGenerated with optional overrides."""
    defaults = {
        "question_text": "What does 'according to' indicate in a sentence?",
        "expected_answer": BossExpectedAnswer(
            canonical="the source",
            accepted_variants=["the source", "as stated by"],
        ),
        "rubric": BossRubric(
            full_credit=["the source"],
            partial_credit=["source"],
            common_mistakes=[],
        ),
        "target_skill": "according_to",
        "difficulty": "medium",
        "source_phase_ids": ["preview"],
        "why_this_question": "Student missed two according_to items in practice",
    }
    defaults.update(overrides)
    return BossQuestionGenerated(**defaults)


def _boss_check_factory(**overrides) -> BossAnswerCheckResult:
    """Return a valid BossAnswerCheckResult with optional overrides."""
    defaults = {
        "is_correct": True,
        "score": 1.0,
        "confidence": 0.95,
        "feedback": "Correct.",
        "misconception_tags": [],
        "damage_multiplier": 1.0,
        "difficulty_recommendation": "increase",
        "should_retry_same_skill": False,
    }
    defaults.update(overrides)
    return BossAnswerCheckResult(**defaults)


@patch("server.services.boss_dynamic.ai_gateway.generate_structured")
def test_boss_starts_without_static_boss_questions(mock_gen, client):
    """Plan 5 acceptance test 1 — homework with no boss_questions but
    completed phase metrics must still start a boss session."""
    hw_id = _make_homework(client, hw_id_hint="t1")
    sess = "plan5sess0001"
    _seed_attempts(sess, hw_id)

    resp = client.post("/api/ai/boss/start", json={
        "session_id": sess,
        "homework_id": hw_id,
        "max_hp": 100,
        "trials_left": 5,
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["hp"] == 100
    assert body["max_hp"] == 100
    assert body["trials_left"] == 5
    assert body["current_difficulty"] == "medium"
    assert body["boss_session_id"].startswith("bs_")
    # Weak topics derived from seeded misconception tags.
    assert "according_to" in body["weak_topics"] or "meaning_in_context" in body["weak_topics"]
    # No LLM call on /start — generation happens only on demand.
    mock_gen.assert_not_called()


@patch("server.services.boss_dynamic.ai_gateway.generate_structured")
def test_boss_start_is_idempotent_for_session_refresh(mock_gen, client):
    """Plan 5 acceptance test 5 — refresh during boss should not spawn a
    new boss session; re-calling /start returns the existing one."""
    hw_id = _make_homework(client, hw_id_hint="t5")
    sess = "plan5sess0005"
    _seed_attempts(sess, hw_id)

    a = client.post("/api/ai/boss/start", json={
        "session_id": sess, "homework_id": hw_id,
    })
    b = client.post("/api/ai/boss/start", json={
        "session_id": sess, "homework_id": hw_id,
    })
    assert a.status_code == 200 and b.status_code == 200
    assert a.json()["boss_session_id"] == b.json()["boss_session_id"]


@patch("server.services.boss_dynamic.ai_gateway.generate_structured")
def test_boss_generate_question_targets_weak_topics_first(mock_gen, client):
    """Plan 5 acceptance test 2 — generated question should target a weak
    topic. We assert the LLM was given the weak-topic list, since the
    generator output itself comes from the (mocked) LLM."""
    hw_id = _make_homework(client, hw_id_hint="t2")
    sess = "plan5sess0002"
    _seed_attempts(sess, hw_id)

    mock_gen.return_value = _boss_question_factory()

    started = client.post("/api/ai/boss/start", json={
        "session_id": sess, "homework_id": hw_id,
    }).json()
    bsid = started["boss_session_id"]

    resp = client.post("/api/ai/boss/generate-question", json={"boss_session_id": bsid})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["question_id"].startswith("gbq_")
    assert body["target_skill"] == "according_to"
    assert body["difficulty"] == "medium"

    # The prompt sent to the LLM must include the student's weak topics.
    prompt_str = mock_gen.call_args[1]["prompt"]
    assert "weak_topics" in prompt_str
    assert "according_to" in prompt_str or "meaning_in_context" in prompt_str

    # Frontend-facing response must NOT carry the expected_answer / rubric.
    assert "expected_answer" not in body
    assert "rubric" not in body


@patch("server.services.boss_dynamic.ai_gateway.generate_structured")
def test_boss_generate_question_does_not_leak_prior_expected_answers_to_llm(mock_gen, client):
    """Anti-leak invariant — even after asking one question, the next
    generation prompt must NOT contain the prior question's expected_answer
    or rubric. This is the one mistake that would let a Plan 5 generator
    silently regress into answer leaking."""
    hw_id = _make_homework(client, hw_id_hint="t_leak")
    sess = "plan5leak0001"
    _seed_attempts(sess, hw_id)

    leak_canary = "ZQXLEAKCANARY"
    mock_gen.return_value = _boss_question_factory(
        question_text="What does 'concerning' mean?",
        expected_answer=BossExpectedAnswer(
            canonical=leak_canary, accepted_variants=[leak_canary]
        ),
        rubric=BossRubric(full_credit=[leak_canary]),
        target_skill="meaning_in_context",
        why_this_question="weak topic follow-up",
    )
    started = client.post("/api/ai/boss/start", json={
        "session_id": sess, "homework_id": hw_id,
    }).json()
    bsid = started["boss_session_id"]
    # First question.
    r1 = client.post("/api/ai/boss/generate-question", json={"boss_session_id": bsid})
    assert r1.status_code == 200, r1.text

    # Second generation — check the prompt does NOT contain the canary.
    mock_gen.return_value = _boss_question_factory(
        question_text="Use 'according to' in a sentence about sources.",
        expected_answer=BossExpectedAnswer(
            canonical="any sentence with according to", accepted_variants=[]
        ),
        rubric=BossRubric(full_credit=["uses according to citing source"]),
        target_skill="according_to",
        why_this_question="second item",
    )
    mock_gen.reset_mock()
    # Adjust return so the new question_text isn't a paraphrase.
    r2 = client.post("/api/ai/boss/generate-question", json={"boss_session_id": bsid})
    assert r2.status_code == 200, r2.text

    second_prompt = mock_gen.call_args[1]["prompt"]
    assert leak_canary not in second_prompt, (
        "prior expected_answer canary leaked into the generator prompt — "
        "asked_questions context must scrub answer keys"
    )


@patch("server.services.boss_dynamic.ai_gateway.generate_structured")
def test_boss_submit_answer_backend_owns_hp_not_model(mock_gen, client):
    """Plan 5 acceptance test 4 — the model cannot set HP. Even when the
    answer-checker returns a wild damage_multiplier, backend HP delta is
    bounded by the deterministic damage table and the multiplier clamp."""
    hw_id = _make_homework(client, hw_id_hint="t_hp")
    sess = "plan5hpgrd0001"
    _seed_attempts(sess, hw_id)

    started = client.post("/api/ai/boss/start", json={
        "session_id": sess, "homework_id": hw_id, "max_hp": 100,
    }).json()
    bsid = started["boss_session_id"]

    # Step 1: generate question
    mock_gen.return_value = _boss_question_factory(
        question_text="Define 'according to'.",
        expected_answer=BossExpectedAnswer(canonical="as stated by"),
        rubric=BossRubric(full_credit=["as stated by"]),
        target_skill="according_to",
        why_this_question="weak topic",
    )
    g = client.post("/api/ai/boss/generate-question", json={"boss_session_id": bsid}).json()
    qid = g["question_id"]

    # Step 2: submit — simulate model returning inflated damage_multiplier.
    # We bypass Pydantic validation here to test backend clamping as defense
    # in depth (Plan 5 §7). In production, the gateway schema prevents >1.5.
    class _FakeCheckResult:
        is_correct = True
        score = 1.0
        confidence = 0.95
        feedback = "Correct."
        misconception_tags = []
        damage_multiplier = 99.0  # absurd; backend must clamp
        difficulty_recommendation = "increase"
        should_retry_same_skill = False
    mock_gen.return_value = _FakeCheckResult()
    resp = client.post("/api/ai/boss/submit-answer", json={
        "boss_session_id": bsid,
        "question_id": qid,
        "student_answer": "as stated by",
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Medium base = 15, max multiplier = 1.5 → max damage = 22 or 23 (rounding).
    # HP must NOT be 100 - (15 * 99) = -1385.
    assert body["damage"] <= 25, f"damage not clamped: {body['damage']}"
    assert body["hp"] >= 75, f"hp not clamped: {body['hp']}"
    assert body["boss_status"] == "active"


@patch("server.services.boss_dynamic.ai_gateway.generate_structured")
def test_boss_state_persists_across_request_for_refresh(mock_gen, client):
    """Plan 5 acceptance test 5 — /state must return the same HP / trials
    as set by submit-answer. Guards the database round-trip."""
    hw_id = _make_homework(client, hw_id_hint="t_state")
    sess = "plan5state001"
    _seed_attempts(sess, hw_id)

    started = client.post("/api/ai/boss/start", json={
        "session_id": sess, "homework_id": hw_id, "max_hp": 100, "trials_left": 5,
    }).json()
    bsid = started["boss_session_id"]

    mock_gen.return_value = _boss_question_factory(
        question_text="Pick the synonym of 'concerning'.",
        expected_answer=BossExpectedAnswer(canonical="about", accepted_variants=["regarding"]),
        rubric=BossRubric(full_credit=["about"]),
        target_skill="meaning_in_context",
        why_this_question="weak topic",
    )
    q = client.post("/api/ai/boss/generate-question", json={"boss_session_id": bsid}).json()

    mock_gen.return_value = _boss_check_factory(
        is_correct=False, score=0.0, confidence=0.9,
        feedback="Try again.",
        misconception_tags=["meaning_in_context"],
        damage_multiplier=1.0, difficulty_recommendation="stay",
        should_retry_same_skill=True,
    )
    client.post("/api/ai/boss/submit-answer", json={
        "boss_session_id": bsid, "question_id": q["question_id"], "student_answer": "wrong",
    })

    state = client.post("/api/ai/boss/state", json={"boss_session_id": bsid}).json()
    assert state["hp"] == 100  # wrong answer = 0 damage
    assert state["trials_left"] == 4  # one attempt consumed
    assert state["boss_session_id"] == bsid


@patch("server.services.boss_dynamic.ai_gateway.generate_structured")
def test_boss_give_up_marks_abandoned_and_blocks_further_actions(mock_gen, client):
    hw_id = _make_homework(client, hw_id_hint="t_giveup")
    sess = "plan5give001"
    _seed_attempts(sess, hw_id)

    started = client.post("/api/ai/boss/start", json={
        "session_id": sess, "homework_id": hw_id,
    }).json()
    bsid = started["boss_session_id"]
    r = client.post("/api/ai/boss/give-up", json={"boss_session_id": bsid})
    assert r.status_code == 200
    assert r.json()["status"] == "abandoned"

    # Subsequent generate must be rejected.
    rg = client.post("/api/ai/boss/generate-question", json={"boss_session_id": bsid})
    assert rg.status_code == 409


@patch("server.services.boss_dynamic.ai_gateway.generate_structured")
def test_legacy_boss_turn_endpoint_still_intact(mock_gen, client):
    """Plan 5 §4 + CLAUDE.md — the legacy /ai/boss-turn route must keep
    working while Plan 5 ships, so old generated homework HTML keeps
    grading correctly. If this fails we have broken backward compat."""
    mock_gen.return_value = {
        "correct": True, "damage_dealt": 20, "boss_response": "Yaxshi!",
        "hint": None, "score": 1.0,
    }
    resp = client.post("/api/ai/boss-turn", json={
        "boss_question": "x²=25?",
        "student_answer": "±5",
        "expected_answers": ["±5"],
        "damage_value": 20,
        "hp_remaining": 80,
        "attempt_number": 1,
        "subject": "math-algebra",
        "grade": 8,
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["correct"] is True


# ---------------------------------------------------------------------------
# Plan 7 — Prompt contract + Pydantic validation
# ---------------------------------------------------------------------------


def test_pydantic_boss_question_output_validates_full_contract():
    """Plan 7 §10 Test 2 — BossQuestionOutput must enforce types, ranges, literals."""
    valid = {
        "question_text": "What is 2+2?",
        "expected_answer": {"canonical": "4", "accepted_variants": ["four"]},
        "rubric": {"full_credit": ["4"], "partial_credit": [], "common_mistakes": []},
        "target_skill": "addition",
        "difficulty": "easy",
        "source_phase_ids": ["preview"],
        "why_this_question": "Basic arithmetic check",
    }
    out = boss_dynamic.BossQuestionOutput.model_validate(valid)
    assert out.difficulty == "easy"
    assert out.expected_answer.canonical == "4"


def test_pydantic_boss_question_output_rejects_empty_question():
    """Plan 7 §10 Test 2 — empty question_text must fail Pydantic validation."""
    bad = {
        "question_text": "   ",
        "expected_answer": {"canonical": "4"},
        "rubric": {"full_credit": ["4"]},
        "target_skill": "addition",
        "difficulty": "easy",
    }
    with pytest.raises(Exception):
        boss_dynamic.BossQuestionOutput.model_validate(bad)


def test_pydantic_boss_question_output_rejects_too_long_question():
    """Plan 7 §10 Test 2 — question_text > 900 chars must fail."""
    bad = {
        "question_text": "x" * 901,
        "expected_answer": {"canonical": "x"},
        "rubric": {"full_credit": ["x"]},
        "target_skill": "overflow",
        "difficulty": "easy",
    }
    with pytest.raises(Exception):
        boss_dynamic.BossQuestionOutput.model_validate(bad)


def test_pydantic_boss_answer_verdict_output_clamps_multiplier():
    """Plan 7 §10 Test 2 — damage_multiplier outside [0, 1.5] must fail."""
    bad = {
        "is_correct": True,
        "score": 1.0,
        "confidence": 0.95,
        "feedback_to_student": "Nice!",
        "misconception_tags": [],
        "damage_multiplier": 99.0,
        "difficulty_recommendation": "increase",
        "should_retry_same_skill": False,
    }
    with pytest.raises(Exception):
        boss_dynamic.BossAnswerVerdictOutput.model_validate(bad)


def test_pydantic_boss_answer_verdict_output_accepts_valid():
    """Plan 7 §10 Test 2 — valid verdict parses correctly."""
    valid = {
        "is_correct": False,
        "score": 0.3,
        "confidence": 0.8,
        "feedback_to_student": "Try again.",
        "misconception_tags": ["sign_error"],
        "damage_multiplier": 1.0,
        "difficulty_recommendation": "stay",
        "should_retry_same_skill": True,
    }
    out = boss_dynamic.BossAnswerVerdictOutput.model_validate(valid)
    assert out.is_correct is False
    assert out.damage_multiplier == 1.0


def test_build_boss_input_section_wraps_student_answer_in_untrusted_delimiters():
    """Plan 7 Rule 2 — student_answer must be wrapped in <UNTRUSTED_STUDENT_MESSAGE>."""
    payload = {
        "question_text": "x?",
        "student_answer": "my answer",
        "target_skill": "test",
    }
    section = boss_dynamic._build_boss_input_section(payload)
    assert "<UNTRUSTED_STUDENT_MESSAGE>" in section
    assert "my answer" in section
    assert "</UNTRUSTED_STUDENT_MESSAGE>" in section


def test_build_boss_input_section_leaves_other_fields_intact():
    """Plan 7 Rule 2 — only student_answer gets wrapped; other fields stay plain."""
    payload = {
        "question_text": "plain",
        "student_answer": "untrusted",
    }
    section = boss_dynamic._build_boss_input_section(payload)
    assert section.count("<UNTRUSTED_STUDENT_MESSAGE>") == 1
    # The plain field should NOT be wrapped.
    assert "plain" in section


def test_boss_tutor_prompt_has_no_chat_history_ghost_variable():
    """Plan 7 §10 Test 1 — boss-tutor.md must not reference CHAT_HISTORY
    unless the backend provides it. After Plan 7 rewrite, it uses
    RECENT_BOSS_HISTORY instead."""
    from server.config import PROMPTS_DIR

    text = (PROMPTS_DIR / "runtime" / "boss-tutor.md").read_text(encoding="utf-8")
    # CHAT_HISTORY is a ghost variable in the old prompt; v2 removes it.
    assert "CHAT_HISTORY" not in text, (
        "boss-tutor.md still references CHAT_HISTORY — backend does not provide it. "
        "Use RECENT_BOSS_HISTORY instead (Plan 7 §6)."
    )
    # v2 should reference the new variable.
    assert "RECENT_BOSS_HISTORY" in text, (
        "boss-tutor.md v2 must reference RECENT_BOSS_HISTORY (Plan 7 §6)."
    )


def test_boss_tutor_prompt_uses_boss_state_and_answer_result():
    """Plan 7 §6 — boss-tutor.md v2 must consume BOSS_STATE, CURRENT_BOSS_QUESTION,
    ANSWER_RESULT, PERSONA_TRAITS."""
    from server.config import PROMPTS_DIR

    text = (PROMPTS_DIR / "runtime" / "boss-tutor.md").read_text(encoding="utf-8")
    for var in ("BOSS_STATE", "CURRENT_BOSS_QUESTION", "ANSWER_RESULT", "PERSONA_TRAITS"):
        assert var in text, f"boss-tutor.md v2 missing required variable: {var}"


def test_boss_question_generator_has_prompt_version_header():
    """Plan 7 §8 — every prompt file must carry a machine-readable version."""
    from server.config import PROMPTS_DIR

    text = (PROMPTS_DIR / "runtime" / "boss-question-generator.md").read_text(encoding="utf-8")
    assert "prompt-version:" in text or "prompt version" in text.lower(), (
        "boss-question-generator.md missing version header (Plan 7 §8)."
    )


def test_boss_answer_checker_has_prompt_version_header():
    """Plan 7 §8 — every prompt file must carry a machine-readable version."""
    from server.config import PROMPTS_DIR

    text = (PROMPTS_DIR / "runtime" / "boss-answer-checker.md").read_text(encoding="utf-8")
    assert "prompt-version:" in text or "prompt version" in text.lower(), (
        "boss-answer-checker.md missing version header (Plan 7 §8)."
    )


def test_prompt_version_constant_matches_files():
    """Plan 7 §8 — PROMPT_VERSION dict must declare versions for all boss prompts."""
    assert "boss-question-generator" in boss_dynamic.PROMPT_VERSION
    assert "boss-answer-checker" in boss_dynamic.PROMPT_VERSION
    assert "boss-tutor" in boss_dynamic.PROMPT_VERSION
    assert boss_dynamic.PROMPT_VERSION["boss-tutor"] == "v2"


def test_boss_answer_checker_prompt_json_example_validates_against_schema():
    """Plan 7 contract guard — the JSON example in boss-answer-checker.md must
    validate against BossAnswerCheckResult.

    Regression: PR #186 originally taught the model to emit the key
    `feedback_to_student`, but the schema field is `feedback`. The first
    model call would always fail Pydantic validation, wasting the gateway's
    one repair retry. This test fails on pre-fix code.
    """
    import re
    from server.config import PROMPTS_DIR

    text = (PROMPTS_DIR / "runtime" / "boss-answer-checker.md").read_text(encoding="utf-8")

    match = re.search(
        r"## Required JSON output\s*```json\s*(\{.*?\})\s*```",
        text,
        re.DOTALL,
    )
    assert match, "boss-answer-checker.md missing JSON example under '## Required JSON output'"

    parsed = json.loads(match.group(1))
    BossAnswerCheckResult(**parsed)


# ---------------------------------------------------------------------------
# Section F — recompute_session_metrics called on /boss/start
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Section G — empty-pool guard (no stems AND no phases → no_anchor_context)
# ---------------------------------------------------------------------------


@patch("server.services.boss_dynamic.ai_gateway.generate_structured")
def test_generate_question_rejects_when_both_pools_empty(mock_gen):
    """Plan Wave 2 §G — when the boss_context has neither authored stems nor
    phase summaries, generate_boss_question must bail with
    BossQuestionRejected("no_anchor_context") BEFORE paying the LLM call.
    Without this guard the generator hallucinates an off-topic skill from
    nothing.
    """
    boss_context = {
        "session_id": "sess-empty",
        "homework_id": "hw-empty",
        "authored_question_stems": [],
        "phase_summaries": [],
        "authored_difficulty_floor": None,
        "asked_questions": [],
        "boss_policy": {"max_question_length": 900},
    }
    with pytest.raises(boss_dynamic.BossQuestionRejected) as exc:
        asyncio.run(
            boss_dynamic.generate_boss_question(boss_context, difficulty="medium")
        )
    assert exc.value.reason == "no_anchor_context"
    # The empty-pool guard must short-circuit BEFORE the gateway is called.
    mock_gen.assert_not_called()


@patch("server.routes.ai_plan5.session_metrics_repo.recompute_session_metrics")
@patch("server.services.boss_dynamic.ai_gateway.generate_structured")
def test_recompute_session_metrics_called_on_boss_start(mock_gen, mock_recompute, client):
    """Section F regression — /boss/start must trigger recompute_session_metrics so
    that overall_metrics is fresh by the time /boss/generate-question fires.
    Before the fix, recompute_session_metrics was never called and
    overall_metrics was always {}, causing missing_context_flags=['empty_metrics'].
    This test fails on pre-fix code (where the call is absent).
    """
    import asyncio

    # Make the mock awaitable (recompute_session_metrics is async)
    async def _noop(*args, **kwargs):
        return {}

    mock_recompute.side_effect = _noop

    hw_id = _make_homework(client, hw_id_hint="t_recompute")
    sess = "plan5recompute01"
    _seed_attempts(sess, hw_id)

    resp = client.post("/api/ai/boss/start", json={
        "session_id": sess,
        "homework_id": hw_id,
        "max_hp": 100,
        "trials_left": 5,
    })
    assert resp.status_code == 200, resp.text

    # recompute_session_metrics must have been called exactly once with the
    # correct session_id and hw_id keyword arguments.
    mock_recompute.assert_called_once_with(
        session_id=sess,
        hw_id=hw_id,
    )


# ---------------------------------------------------------------------------
# 2026-05-13 audit Bug #7 — attempt_number increments per question_id
# ---------------------------------------------------------------------------


@patch("server.services.boss_dynamic.ai_gateway.generate_structured")
def test_attempt_number_increments_when_same_question_resubmitted(mock_gen, client):
    """Bug #7: attempt_number was hardcoded to 1 on every boss submit.
    Re-submitting the same question_id (retry path) created multiple rows
    with attempt_number=1, inflating _streaks_from_recent_attempts. After
    the fix, the second submit must record attempt_number=2."""
    import asyncio
    from server.db import attempts_repo

    hw_id = _make_homework(client, hw_id_hint="t_atn")
    sess = "plan5atn00001"
    _seed_attempts(sess, hw_id)

    started = client.post("/api/ai/boss/start", json={
        "session_id": sess, "homework_id": hw_id, "max_hp": 100,
    }).json()
    bsid = started["boss_session_id"]

    mock_gen.return_value = _boss_question_factory(
        question_text="Q for attempt-number test.",
        expected_answer=BossExpectedAnswer(canonical="x"),
        rubric=BossRubric(full_credit=["x"]),
        target_skill="topic1",
        why_this_question="test",
    )
    q = client.post("/api/ai/boss/generate-question", json={"boss_session_id": bsid}).json()
    qid = q["question_id"]

    mock_gen.return_value = _boss_check_factory(
        is_correct=False, score=0.0, confidence=0.9,
        feedback="wrong", misconception_tags=[],
        damage_multiplier=1.0, difficulty_recommendation="stay",
        should_retry_same_skill=True,
    )
    # First submit
    r1 = client.post("/api/ai/boss/submit-answer", json={
        "boss_session_id": bsid, "question_id": qid, "student_answer": "wrong1",
    })
    assert r1.status_code == 200, r1.text
    # Second submit on SAME question_id (retry path)
    r2 = client.post("/api/ai/boss/submit-answer", json={
        "boss_session_id": bsid, "question_id": qid, "student_answer": "wrong2",
    })
    assert r2.status_code == 200, r2.text

    # Verify DB has two rows for this question with attempt_number 1 and 2.
    rows = asyncio.run(attempts_repo.attempts_for_question(sess, hw_id, qid))
    nums = sorted(r.get("attempt_number") for r in rows)
    assert nums == [1, 2], (
        f"Expected attempt_number=[1, 2] for two submits, got {nums}. "
        f"Bug #7 regression — attempt_number must increment per question."
    )


# ---------------------------------------------------------------------------
# 2026-05-13 audit Backend Bug #4 — append_asked_question atomic on race
# ---------------------------------------------------------------------------


def test_append_asked_question_serializes_concurrent_writes(client):
    """Backend Bug #4: append_asked_question used to read-then-write in two
    separate connections, racing with concurrent /generate-question calls.
    After the BEGIN IMMEDIATE fix, concurrent appends to the same session
    must serialize — both question IDs end up in the array. Simulates the
    race with two threads calling append simultaneously."""
    import asyncio
    import threading
    from server.db import boss_session_repo

    hw_id = _make_homework(client, hw_id_hint="t_race")
    sess = "plan5race0001"
    _seed_attempts(sess, hw_id)

    started = client.post("/api/ai/boss/start", json={
        "session_id": sess, "homework_id": hw_id, "max_hp": 100,
    }).json()
    bsid = started["boss_session_id"]

    errors = []

    def _do_append(qid: str):
        try:
            asyncio.run(boss_session_repo.append_asked_question(bsid, qid))
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [
        threading.Thread(target=_do_append, args=(f"gbq_race_{i:02d}",))
        for i in range(8)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"concurrent appends raised: {errors}"

    # Final state must contain ALL 8 question IDs (no overwrites).
    final = asyncio.run(boss_session_repo.get_boss_session(bsid))
    asked = final["asked_question_ids"]
    expected = {f"gbq_race_{i:02d}" for i in range(8)}
    assert set(asked) >= expected, (
        f"concurrent appends lost some IDs (race condition still present): "
        f"expected ⊇ {expected}, got {set(asked)}"
    )
