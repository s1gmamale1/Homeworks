"""Soft-friction nudge — strong flag surfaces a nudge but NEVER gates progress.

Guards the wiring agent's nudge contract on BOTH submit surfaces:
  - process_runtime_answer (the /runtime/submit-answer path)
  - the ai_plan5 boss submit-answer path

A ``sudden_mastery`` (strong) scenario must:
  - set ``integrity_nudge`` to an {type, message} dict (no reason_code /
    thresholds leaked), AND
  - leave ``is_correct`` / ``score`` (and, for boss, ``hp`` / ``boss_status``)
    exactly as the grader produced them.

A normal scenario must leave ``integrity_nudge`` as ``None``.

The runtime path uses a DETERMINISTIC ``answer_spec`` on an assessment phase
(``consolidation`` is not in the AI-use policy table → fail-closed
assessment=True), so no AI backend is needed. The boss path mocks the LLM.
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import patch

from server.db import attempts_repo, session_metrics_repo
from server.schemas.ai_contracts import (
    BossQuestionGenerated,
    BossExpectedAnswer,
    BossRubric,
    BossAnswerCheckResult,
)


def _run(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


# ---------------------------------------------------------------------------
# process_runtime_answer path
# ---------------------------------------------------------------------------


def _make_assessment_hw(client, *, hint: str) -> str:
    """Homework whose 'consolidation' phase has a deterministically-gradeable
    item. 'consolidation' is absent from AI_USE_POLICY → SAFE_DEFAULT →
    assessment=True, so its attempts feed the sudden-mastery detector."""
    payload = {
        "title": f"Soft-friction HW ({hint})",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
        "family": "aniq-fanlar",
        "content_json": {
            "title": f"Soft-friction HW ({hint})",
            "subject": "math-algebra",
            "grade": 8,
            "consolidation": {
                "items": [
                    {
                        "id": "c1",
                        "text": "What is 2+2?",
                        "expected_answers": ["4"],
                        "answer_spec": {"type": "text_exact", "expected": "4"},
                    }
                ]
            },
        },
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _seed_low_mastery_and_assessment(session_id: str, hw_id: str, *, n_correct: int) -> None:
    """Seed low mastery + n correct ASSESSMENT (consolidation) attempts."""

    async def go():
        # Low-mastery anchor: enough wrong practice attempts that the OVERALL
        # mastery_score lands at/under the sudden-mastery pre-ceiling (0.40)
        # even though the assessment-phase rate is perfect. (mastery is computed
        # over ALL attempts, so the correct assessment rows raise it; we
        # outweigh them with non-assessment wrong rows.)
        for i in range(12):
            await attempts_repo.add_phase_attempt(
                session_id=session_id, hw_id=hw_id,
                phase="practice", subphase="sentence-fill",
                question_id=f"w{i}", checker_source="ai_judge",
                correct=0, score=0.1, confidence=0.9,
            )
        # Correct assessment attempts (consolidation = assessment).
        for i in range(n_correct):
            await attempts_repo.add_phase_attempt(
                session_id=session_id, hw_id=hw_id,
                phase="consolidation", question_id=f"a{i}",
                checker_source="deterministic",
                correct=1, score=1.0, confidence=1.0,
            )
        await session_metrics_repo.recompute_session_metrics(session_id, hw_id)

    _run(go())


def _submit_consolidation(client, hw_id, sess, *, answer="4"):
    return client.post("/api/ai/runtime/submit-answer", json={
        "session_id": sess,
        "homework_id": hw_id,
        "phase": "consolidation",
        "question_id": "c1",
        "answer_type": "text",
        "student_answer": answer,
    })


def test_runtime_sudden_mastery_sets_nudge_without_changing_grade(client):
    hw_id = _make_assessment_hw(client, hint="rt-strong")
    sess = "sf-rt-strong-001"
    # 3 prior correct assessment attempts already seeded; this submit is the
    # 4th correct → correct_rate stays 1.0 over >= 3 items, pre-mastery low.
    _seed_low_mastery_and_assessment(sess, hw_id, n_correct=3)

    resp = _submit_consolidation(client, hw_id, sess)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Grade is the normal deterministic correct verdict.
    assert body["is_correct"] is True
    assert body["score"] == 1.0
    assert body["grading_method"] == "deterministic"

    # Strong flag → nudge present, shaped, and leak-free.
    nudge = body["integrity_nudge"]
    assert isinstance(nudge, dict)
    assert nudge["type"] == "explain_reasoning"
    assert isinstance(nudge["message"], str) and nudge["message"]
    assert "reason_code" not in nudge
    assert "sudden_mastery" not in json.dumps(nudge)


def test_runtime_normal_scenario_has_no_nudge(client):
    hw_id = _make_assessment_hw(client, hint="rt-normal")
    sess = "sf-rt-normal-001"
    # No low-mastery anchor + no prior assessment attempts → sudden_mastery
    # cannot fire (pre-mastery unknown / item count below floor).
    resp = _submit_consolidation(client, hw_id, sess)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_correct"] is True
    assert body["score"] == 1.0
    assert body["integrity_nudge"] is None


# ---------------------------------------------------------------------------
# boss (ai_plan5) path
# ---------------------------------------------------------------------------


def _make_boss_hw(client, *, hint: str) -> str:
    payload = {
        "title": f"Soft-friction boss HW ({hint})",
        "subject": "english",
        "grade": 8,
        "mode": "hard",
        "family": "til-fanlar",
        "content_json": {
            "title": f"Soft-friction boss HW ({hint})",
            "subject": "english",
            "grade": 8,
            "language": "en",
            "preview": {"text": "according to means as stated by"},
        },
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _seed_low_mastery(session_id: str, hw_id: str) -> None:
    async def go():
        for i in range(3):
            await attempts_repo.add_phase_attempt(
                session_id=session_id, hw_id=hw_id,
                phase="practice", subphase="sentence-fill",
                question_id=f"q{i}", checker_source="ai_judge",
                correct=0, score=0.1, confidence=0.9,
            )
        await session_metrics_repo.recompute_session_metrics(session_id, hw_id)

    _run(go())


_Q = {"n": 0}


def _boss_question():
    _Q["n"] += 1
    n = _Q["n"]
    return BossQuestionGenerated(
        question_text=f"Soft-friction boss q {n}: explain 'according to' {n}.",
        expected_answer=BossExpectedAnswer(canonical="the source"),
        rubric=BossRubric(full_credit=["the source"]),
        target_skill="according_to",
        difficulty="medium",
        source_phase_ids=["preview"],
        why_this_question="weak topic",
    )


def _correct_verdict():
    return BossAnswerCheckResult(
        is_correct=True, score=1.0, confidence=0.95,
        feedback="Correct.", misconception_tags=[],
        damage_multiplier=1.0, difficulty_recommendation="increase",
        should_retry_same_skill=False,
    )


def test_boss_sudden_mastery_sets_nudge_without_changing_grade(client):
    hw_id = _make_boss_hw(client, hint="boss-strong")
    sess = "sf-boss-strong-1"
    _seed_low_mastery(sess, hw_id)

    started = client.post("/api/ai/boss/start", json={
        "session_id": sess, "homework_id": hw_id, "trials_left": 10,
    }).json()
    bsid = started["boss_session_id"]

    last = None
    with patch("server.services.boss_dynamic.ai_gateway.generate_structured") as mock_gen:
        for _ in range(3):
            mock_gen.return_value = _boss_question()
            g = client.post("/api/ai/boss/generate-question",
                            json={"boss_session_id": bsid}).json()
            mock_gen.return_value = _correct_verdict()
            r = client.post("/api/ai/boss/submit-answer", json={
                "boss_session_id": bsid, "question_id": g["question_id"],
                "student_answer": "the source",
            })
            assert r.status_code == 200, r.text
            last = r.json()

    # The third correct submit (correct_rate 1.0 over 3 items) trips
    # sudden_mastery → nudge present; grade + boss state untouched.
    assert last["is_correct"] is True
    assert last["score"] == 1.0
    assert last["hp"] >= 0  # HP is final + server-authoritative
    assert last["boss_status"] in ("active", "won", "failed")
    nudge = last["integrity_nudge"]
    assert isinstance(nudge, dict)
    assert nudge["type"] == "explain_reasoning"
    assert "reason_code" not in nudge


def test_boss_normal_scenario_has_no_nudge(client):
    hw_id = _make_boss_hw(client, hint="boss-normal")
    sess = "sf-boss-normal-1"
    _seed_low_mastery(sess, hw_id)

    started = client.post("/api/ai/boss/start", json={
        "session_id": sess, "homework_id": hw_id, "trials_left": 10,
    }).json()
    bsid = started["boss_session_id"]

    with patch("server.services.boss_dynamic.ai_gateway.generate_structured") as mock_gen:
        # A single correct answer: item_count == 1 < the min-items floor (3),
        # so sudden_mastery cannot fire → no nudge.
        mock_gen.return_value = _boss_question()
        g = client.post("/api/ai/boss/generate-question",
                        json={"boss_session_id": bsid}).json()
        mock_gen.return_value = _correct_verdict()
        r = client.post("/api/ai/boss/submit-answer", json={
            "boss_session_id": bsid, "question_id": g["question_id"],
            "student_answer": "the source",
        })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["is_correct"] is True
    assert body["integrity_nudge"] is None
