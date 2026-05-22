"""Review-queue integrity routing — ADVISORY flags land in their own lane.

Guards the wiring agent's review-queue contract:
  - A strong (sudden_mastery) flag enrolls a ``kind='integrity'`` row carrying
    ``integrity_reason`` / ``integrity_severity``.
  - ``GET /ai/review-queue?kind=integrity`` returns it; pending grading rows are
    excluded from that lane (and vice-versa).
  - The student's submit response still shows the NORMAL grade — the flag is
    non-blocking (server stays authoritative).
  - Integrity dedup keys on (question_id + reason + session_id), so the same
    flag for the same playthrough is not enrolled twice.

We drive the strong flag through the BOSS submit path (the boss is always an
assessment): seed a low pre-boss mastery, then answer several boss questions
correctly so correct_rate >= 0.90 over >= 3 items → sudden_mastery fires.
"""
from __future__ import annotations

import asyncio
import json
import os
from unittest.mock import patch

import aiosqlite

from server.db import attempts_repo, session_metrics_repo
from server.schemas.ai_contracts import (
    BossQuestionGenerated,
    BossExpectedAnswer,
    BossRubric,
    BossAnswerCheckResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def _make_boss_hw(client, *, hint: str) -> str:
    payload = {
        "title": f"Integrity routing boss HW ({hint})",
        "subject": "english",
        "grade": 8,
        "mode": "hard",
        "family": "til-fanlar",
        "content_json": {
            "title": f"Integrity routing boss HW ({hint})",
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
    """Seed all-wrong practice attempts → low mastery_score (<= 0.40 ceiling)."""

    async def go():
        for i in range(3):
            await attempts_repo.add_phase_attempt(
                session_id=session_id, hw_id=hw_id,
                phase="practice", subphase="sentence-fill",
                question_id=f"q{i}", checker_source="ai_judge",
                correct=0, score=0.1, confidence=0.9,
                feedback="not quite",
                misconception_tags_json=json.dumps(["according_to"]),
            )
        await session_metrics_repo.recompute_session_metrics(session_id, hw_id)

    _run(go())


def _integrity_rows(session_id: str):
    db_path = os.environ.get("NETS_DB_PATH")

    async def _do():
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM review_queue "
                "WHERE kind = 'integrity' AND session_id = ?",
                (session_id,),
            )
            return [dict(r) for r in await cur.fetchall()]

    return _run(_do())


_Q_COUNTER = {"n": 0}


def _boss_question():
    """A UNIQUE question per call — the boss generator rejects paraphrases of
    prior questions (anti-repetition), so each generated stem must differ."""
    _Q_COUNTER["n"] += 1
    n = _Q_COUNTER["n"]
    return BossQuestionGenerated(
        question_text=f"Boss question number {n}: explain 'according to' usage {n}.",
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


def _drive_correct_boss_answers(client, hw_id, sess, *, n: int):
    """Start a boss and answer n questions correctly. Returns the last submit
    response body. HP damage is bounded so the boss stays active across n
    rounds (n small)."""
    started = client.post("/api/ai/boss/start", json={
        "session_id": sess, "homework_id": hw_id, "trials_left": 10,
    }).json()
    bsid = started["boss_session_id"]

    last = None
    with patch("server.services.boss_dynamic.ai_gateway.generate_structured") as mock_gen:
        for _ in range(n):
            mock_gen.return_value = _boss_question()
            g = client.post("/api/ai/boss/generate-question",
                            json={"boss_session_id": bsid}).json()
            mock_gen.return_value = _correct_verdict()
            r = client.post("/api/ai/boss/submit-answer", json={
                "boss_session_id": bsid,
                "question_id": g["question_id"],
                "student_answer": "the source",
            })
            assert r.status_code == 200, r.text
            last = r.json()
            if last["boss_status"] != "active":
                break
    return last


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_sudden_mastery_enrolls_integrity_row_with_reason(client):
    hw_id = _make_boss_hw(client, hint="enroll")
    sess = "introut-enroll-001"
    _seed_low_mastery(sess, hw_id)

    # 3 correct boss answers → correct_rate 1.0 over 3 items, low pre-mastery →
    # sudden_mastery (strong) must fire and enroll an integrity row.
    _drive_correct_boss_answers(client, hw_id, sess, n=3)

    rows = _integrity_rows(sess)
    assert rows, "a strong sudden_mastery flag must enroll a kind='integrity' row"
    reasons = {r["integrity_reason"] for r in rows}
    assert "sudden_mastery" in reasons
    sm = next(r for r in rows if r["integrity_reason"] == "sudden_mastery")
    assert sm["integrity_severity"] == "strong"
    assert sm["kind"] == "integrity"
    # Advisory: integrity rows carry no student answer.
    assert sm["student_answer"] == ""


def test_review_queue_kind_filter_separates_lanes(client):
    hw_id = _make_boss_hw(client, hint="lanes")
    sess = "introut-lanes-001"
    _seed_low_mastery(sess, hw_id)

    # Seed a pending GRADING row directly so the lanes have distinct content.
    async def seed_grading():
        from server import db as _db
        await _db.add_to_review_queue(
            question_id="grading-q-1",
            student_answer="some answer",
            answer_spec={"type": "semantic", "expected": "x"},
            ai_response={"confidence": 0.4, "score": 0.5},
        )
    _run(seed_grading())

    _drive_correct_boss_answers(client, hw_id, sess, n=3)

    # Integrity lane: only integrity rows, never the grading row.
    integ = client.get("/api/ai/review-queue?kind=integrity")
    assert integ.status_code == 200, integ.text
    integ_body = integ.json()
    assert integ_body, "integrity lane must contain the enrolled flag"
    assert all(r.get("kind") == "integrity" for r in integ_body)
    assert all(r.get("question_id") != "grading-q-1" for r in integ_body)

    # Grading lane: only grading rows, never the integrity flag.
    grading = client.get("/api/ai/review-queue?kind=grading")
    assert grading.status_code == 200, grading.text
    grading_body = grading.json()
    assert any(r.get("question_id") == "grading-q-1" for r in grading_body)
    assert all(r.get("kind") == "grading" for r in grading_body)

    # Unfiltered: returns both lanes (legacy behavior preserved).
    both = client.get("/api/ai/review-queue").json()
    kinds = {r.get("kind") for r in both}
    assert "integrity" in kinds and "grading" in kinds


def test_student_submit_grade_is_unaffected_by_flag(client):
    hw_id = _make_boss_hw(client, hint="nonblock")
    sess = "introut-nonblock-1"
    _seed_low_mastery(sess, hw_id)

    last = _drive_correct_boss_answers(client, hw_id, sess, n=3)
    # The flagged submit still reports the normal correct grade — non-blocking.
    assert last is not None
    assert last["is_correct"] is True
    assert last["score"] == 1.0
    # And it did fire the soft-friction nudge (strong flag), but the grade
    # fields above are independent of it.
    assert "integrity_nudge" in last


def test_integrity_dedup_does_not_double_enroll_same_flag(client):
    """The same sudden_mastery flag for the same (question, session) must enroll
    at most once per distinct question_id — repeated strong flags across rounds
    that re-use a question_id are deduped on (question_id + reason + session)."""
    hw_id = _make_boss_hw(client, hint="dedup")
    sess = "introut-dedup-001"
    _seed_low_mastery(sess, hw_id)

    started = client.post("/api/ai/boss/start", json={
        "session_id": sess, "homework_id": hw_id, "trials_left": 10,
    }).json()
    bsid = started["boss_session_id"]

    with patch("server.services.boss_dynamic.ai_gateway.generate_structured") as mock_gen:
        # First, climb to 3 correct so sudden_mastery is armed.
        for _ in range(3):
            mock_gen.return_value = _boss_question()
            g = client.post("/api/ai/boss/generate-question",
                            json={"boss_session_id": bsid}).json()
            mock_gen.return_value = _correct_verdict()
            client.post("/api/ai/boss/submit-answer", json={
                "boss_session_id": bsid, "question_id": g["question_id"],
                "student_answer": "the source",
            })
        # Now RESUBMIT the same question id twice more — the flag for THAT qid +
        # reason + session must dedup to a single row.
        mock_gen.return_value = _boss_question()
        g = client.post("/api/ai/boss/generate-question",
                        json={"boss_session_id": bsid}).json()
        qid = g["question_id"]
        mock_gen.return_value = _correct_verdict()
        for _ in range(2):
            client.post("/api/ai/boss/submit-answer", json={
                "boss_session_id": bsid, "question_id": qid,
                "student_answer": "the source",
            })

    rows = _integrity_rows(sess)
    # Group by (question_id, reason) — none should appear twice.
    seen = {}
    for r in rows:
        key = (r["question_id"], r["integrity_reason"])
        seen[key] = seen.get(key, 0) + 1
    assert all(c == 1 for c in seen.values()), f"duplicate integrity rows: {seen}"
