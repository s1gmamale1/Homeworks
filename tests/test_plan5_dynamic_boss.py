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
    # more than base * 1.0(accuracy tier) * 1.5(multiplier cap) from one
    # medium-difficulty correct answer. spec §6: medium base = 20 → cap = 30.
    dmg = boss_dynamic.calculate_damage(score=1.0, difficulty="medium", multiplier=99.0)
    assert dmg <= 30, f"multiplier should be clamped <=1.5x base; got {dmg}"


def test_calculate_damage_zero_below_accuracy_floor_regardless_of_difficulty():
    # spec §6: the zero-damage accuracy tier is value < 0.30 (was < 0.60 under
    # the legacy two-tier table). 0.29 → 0 damage; 0.0 → 0 damage.
    for diff in ("easy", "medium", "hard"):
        assert boss_dynamic.calculate_damage(0.29, diff) == 0
        assert boss_dynamic.calculate_damage(0.0, diff) == 0


def test_calculate_damage_invalid_difficulty_falls_back_to_medium_not_zero():
    # Defensive: a typo in the runtime should not silently zero damage on
    # correct answers. spec §6: medium base = 20 → score 1.0 deals 20.
    dmg = boss_dynamic.calculate_damage(1.0, "ULTRA-HARD")
    assert dmg == 20, f"unknown difficulty must fall back to medium=20, got {dmg}"


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


def test_generated_question_allows_near_duplicate_at_threshold_1_point_0():
    # Design change (2026-05-21, prompt v5): the SequenceMatcher fuzzy threshold
    # was raised from 0.85 to 1.0 — only byte-identical duplicates (caught by
    # the `prev_text == norm_new` branch) are rejected post-gateway. Variation
    # responsibility moves to the prompt itself (Rule 3 in
    # boss-question-generator.md v5), which now spells out concrete variation
    # axes + a self-check directive. The narrow-topic-homework case (every
    # candidate scoring 0.93+ vs. a prior question) used to 502; now it passes
    # and we measure prompt quality empirically rather than letting the
    # hard-coded floor block legitimate runs.
    #
    # This fixture (one-digit change + trailing period — similarity ≈ 0.94)
    # used to fail under the 0.85 threshold; under 1.0 it must pass.
    asked = [{"question_text": "Find the absolute error of 12.345 meters"}]
    raw = {
        "question_text": "Find the absolute error of 12.346 meters.",
        "expected_answer": {"canonical": "0.001"},
        "rubric": {"full_credit": ["0.001"]},
        "target_skill": "absolyut_xatolik",
        "difficulty": "medium",
    }
    # No exception — the near-duplicate now flows through to the runtime.
    boss_dynamic._validate_generated_question(raw, asked_questions=asked)


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
    # spec §6: medium base = 20, accuracy tier 1.0, multiplier clamp 1.5 →
    # max damage = 30. Grade-8 homework derives max_hp = 100 (band G5-8), so
    # HP must NOT be 100 - (20 * 99) = -1880; it lands at exactly 70.
    assert body["damage"] <= 30, f"damage not clamped: {body['damage']}"
    assert body["hp"] >= 70, f"hp not clamped: {body['hp']}"
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


# ---------------------------------------------------------------------------
# 2026-05-13 audit — boss session staleness check on /boss/start
# ---------------------------------------------------------------------------


def test_boss_start_archives_stale_active_session_and_spawns_fresh(client):
    """When /boss/start finds an existing active session whose updated_at is
    older than the staleness threshold (30 minutes), it must mark that session
    as 'abandoned' and create a brand-new row with fresh trials_left and HP.

    Bug context (2026-05-14):
        Threshold was 6 hours originally. A real test on 2026-05-13 had a
        4h22m gap between two playthroughs of the same homework — well under
        the 6h window — so the second playthrough silently inherited a session
        whose trials_left was already depleted from the first. Student got
        2 questions instead of 5 and the session ended in 'failed' state.

        30 minutes is the new threshold: covers legitimate same-sitting
        breaks (snack, bathroom, doorbell) without spanning hour-long gaps
        that a student would mentally count as a separate attempt.
    """
    import asyncio
    from datetime import datetime, timezone, timedelta
    from server.db import boss_session_repo

    hw_id = _make_homework(client, hw_id_hint="t_stale")
    sess = "plan5stale001"
    _seed_attempts(sess, hw_id)

    # First /boss/start — creates a fresh session.
    first = client.post("/api/ai/boss/start", json={
        "session_id": sess, "homework_id": hw_id, "max_hp": 100, "trials_left": 7,
    }).json()
    first_bsid = first["boss_session_id"]

    # Forcibly age the session by writing a stale updated_at directly to DB.
    # 45 minutes ago — well past the 30-minute threshold.
    stale_ts = (datetime.now(timezone.utc) - timedelta(minutes=45)).isoformat()
    import sqlite3
    from server.config import DB_PATH
    con = sqlite3.connect(str(DB_PATH))
    con.execute(
        "UPDATE boss_sessions SET updated_at = ?, trials_left = 1 WHERE id = ?",
        (stale_ts, first_bsid),
    )
    con.commit()
    con.close()

    # Second /boss/start — same (session, hw). Must NOT reuse the stale row.
    second = client.post("/api/ai/boss/start", json={
        "session_id": sess, "homework_id": hw_id, "max_hp": 100, "trials_left": 7,
    }).json()
    second_bsid = second["boss_session_id"]

    assert second_bsid != first_bsid, (
        "Stale session was reused — staleness check failed. "
        "Expected a new boss_session_id."
    )
    # _make_homework doesn't author boss_questions, so trials_left falls
    # back to the default (5) per the 2026-05-13 pool-size-derived logic.
    assert second["trials_left"] == 5, (
        f"New session must start with fresh trials_left=5 (fallback default "
        f"since fixture has no authored boss_questions), got {second['trials_left']}"
    )
    assert second["hp"] == 100

    # Old session must be marked 'abandoned' (no longer active).
    old_state = asyncio.run(boss_session_repo.get_boss_session(first_bsid))
    assert old_state["status"] == "abandoned", (
        f"Stale session was not archived. Got status={old_state['status']!r}"
    )


def test_boss_start_reuses_recent_active_session(client):
    """Counterpart: a session whose updated_at is RECENT (< 30 min) must still
    be reused per the original idempotence rule (state survives refresh).
    Guards against accidentally making the staleness check fire too eagerly."""
    hw_id = _make_homework(client, hw_id_hint="t_fresh")
    sess = "plan5fresh001"
    _seed_attempts(sess, hw_id)

    first = client.post("/api/ai/boss/start", json={
        "session_id": sess, "homework_id": hw_id, "max_hp": 100, "trials_left": 7,
    }).json()
    first_bsid = first["boss_session_id"]

    # Immediately call /boss/start again — must reuse.
    second = client.post("/api/ai/boss/start", json={
        "session_id": sess, "homework_id": hw_id, "max_hp": 100, "trials_left": 7,
    }).json()

    assert second["boss_session_id"] == first_bsid, (
        "Recent session was NOT reused — staleness check is firing too eagerly. "
        "Idempotence (Plan 5 acceptance test 5) is broken."
    )


def test_boss_start_archives_session_aged_just_past_threshold(client):
    """Boundary test — a session aged 35 minutes (5 min past the 30-min
    threshold) MUST be archived. Was previously a 6h threshold; a session
    aged 35 min was incorrectly reused, leading to the 2026-05-13 trial-leak
    bug. This test guards against the threshold accidentally creeping back
    up via refactor."""
    import asyncio
    from datetime import datetime, timezone, timedelta
    from server.db import boss_session_repo

    hw_id = _make_homework(client, hw_id_hint="t_boundary")
    sess = "plan5boundary001"
    _seed_attempts(sess, hw_id)

    first = client.post("/api/ai/boss/start", json={
        "session_id": sess, "homework_id": hw_id, "max_hp": 100, "trials_left": 7,
    }).json()
    first_bsid = first["boss_session_id"]

    # 35 min stale — past the 30-min threshold but well short of the old 6h.
    stale_ts = (datetime.now(timezone.utc) - timedelta(minutes=35)).isoformat()
    import sqlite3
    from server.config import DB_PATH
    con = sqlite3.connect(str(DB_PATH))
    con.execute(
        "UPDATE boss_sessions SET updated_at = ? WHERE id = ?",
        (stale_ts, first_bsid),
    )
    con.commit()
    con.close()

    second = client.post("/api/ai/boss/start", json={
        "session_id": sess, "homework_id": hw_id, "max_hp": 100, "trials_left": 7,
    }).json()

    assert second["boss_session_id"] != first_bsid, (
        "Session aged 35 min (past 30-min threshold) was reused — would let "
        "the trial-leak bug regress."
    )

    old_state = asyncio.run(boss_session_repo.get_boss_session(first_bsid))
    assert old_state["status"] == "abandoned"


def test_boss_start_force_fresh_archives_active_session_regardless_of_age(client):
    """When the frontend sends `force_fresh=True` (e.g. student clicked an
    explicit 'Restart boss' / 'New attempt' button), /boss/start must archive
    any active row for this (session_id, homework_id) regardless of its age
    and spawn a fresh session. This is the explicit-intent path so the UI
    can offer a 'Resume or restart?' dialog without fighting the time-based
    staleness heuristic."""
    import asyncio
    from server.db import boss_session_repo

    hw_id = _make_homework(client, hw_id_hint="t_fforce")
    sess = "plan5force001"
    _seed_attempts(sess, hw_id)

    # First call creates a fresh, very-recent session.
    first = client.post("/api/ai/boss/start", json={
        "session_id": sess, "homework_id": hw_id,
    }).json()
    first_bsid = first["boss_session_id"]

    # Second call with force_fresh=True — must NOT reuse despite session
    # being seconds old (well within the 30-min staleness window).
    second = client.post("/api/ai/boss/start", json={
        "session_id": sess, "homework_id": hw_id, "force_fresh": True,
    }).json()
    second_bsid = second["boss_session_id"]

    assert second_bsid != first_bsid, (
        "force_fresh=True must archive any existing session and spawn fresh, "
        "even when the existing session is recent."
    )
    assert second["trials_left"] == 5
    assert second["hp"] == 100

    old_state = asyncio.run(boss_session_repo.get_boss_session(first_bsid))
    assert old_state["status"] == "abandoned"


def test_boss_start_force_fresh_works_when_no_existing_session(client):
    """force_fresh=True on a session that has no active boss row must still
    create a fresh row (not crash, not 404). The flag is a hint about intent,
    not a precondition."""
    hw_id = _make_homework(client, hw_id_hint="t_fnone")
    sess = "plan5fnone001"
    _seed_attempts(sess, hw_id)

    resp = client.post("/api/ai/boss/start", json={
        "session_id": sess, "homework_id": hw_id, "force_fresh": True,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["boss_session_id"].startswith("bs_")
    assert body["hp"] == 100
    assert body["trials_left"] == 5


# ---------------------------------------------------------------------------
# 2026-05-13 — trials_left derived from authored boss_questions pool size
# ---------------------------------------------------------------------------


def test_trials_left_matches_authored_boss_questions_count(client):
    """Design decision (2026-05-13): trials_left should equal the number of
    authored boss_questions in the homework. One Kimi-generated question per
    author-supplied anchor. The req.trials_left field becomes advisory; the
    server computes the effective value from content_json.boss_questions."""
    # Build a homework with exactly 3 boss_questions.
    payload = {
        "title": "trials count test 3",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
        "family": "aniq-fanlar",
        "content_json": {
            "title": "trials count test 3",
            "subject": "math-algebra",
            "grade": 8,
            "language": "uz",
            "boss_questions": [
                {"q": "Stem A", "dmg": 10},
                {"q": "Stem B", "dmg": 20},
                {"q": "Stem C", "dmg": 30},
            ],
        },
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, resp.text
    hw_id = resp.json()["id"]

    # Frontend passes the legacy default of 7; server must override to 3.
    started = client.post("/api/ai/boss/start", json={
        "session_id": "trials_test_3", "homework_id": hw_id,
        "max_hp": 100, "trials_left": 7,
    })
    assert started.status_code == 200, started.text
    assert started.json()["trials_left"] == 3, (
        f"Server must override trials_left to authored pool size "
        f"(3), got {started.json()['trials_left']}. "
        f"req.trials_left=7 was treated as advisory."
    )


def test_trials_left_falls_back_to_5_when_no_authored_boss_questions(client):
    """Counterpart: when content_json has no boss_questions[] (or empty),
    the server falls back to a default of 5 trials."""
    payload = {
        "title": "trials count test 0",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
        "family": "aniq-fanlar",
        "content_json": {
            "title": "trials count test 0",
            "subject": "math-algebra",
            "grade": 8,
            "language": "uz",
            # No boss_questions key at all.
        },
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, resp.text
    hw_id = resp.json()["id"]

    started = client.post("/api/ai/boss/start", json={
        "session_id": "trials_test_0", "homework_id": hw_id,
        "max_hp": 100, "trials_left": 7,
    })
    assert started.status_code == 200, started.text
    assert started.json()["trials_left"] == 5, (
        f"Expected fallback trials_left=5 when no authored boss_questions, "
        f"got {started.json()['trials_left']}"
    )
