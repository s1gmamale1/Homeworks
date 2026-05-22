"""Anti-cheat security-review blockers (C2 / H2 / M2).

Each test guards a specific review finding on the integrity surface:

  C2 — a /api/ai/check-answer submit carrying a `nudge_response` (the student's
       reply to a soft-friction "explain in your own words" nudge) is recorded
       as an ADVISORY session event and EARLY-RETURNS {"advisory": true} BEFORE
       any grading. A nudge reply must never be scored.

  H2 — GET /api/integrity/affirmations with NO filter must 400, never dump the
       whole authorship_affirmations table (teacher notes) to an unauthenticated
       caller.

  M2 — POST /api/ai/review-queue/{id}/decide must refuse a normal grading
       decision against an ADVISORY kind='integrity' row.
"""
from __future__ import annotations

import asyncio
import os

import aiosqlite


def _run(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


# ---------------------------------------------------------------------------
# C2 — nudge_response early-returns advisory, never grades
# ---------------------------------------------------------------------------


def _count_nudge_events(session_id: str, hw_id: str) -> int:
    db_path = os.environ.get("NETS_DB_PATH")

    async def _do():
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT COUNT(*) AS n FROM session_events "
                "WHERE session_id = ? AND hw_id = ? "
                "AND event_type = 'integrity_nudge_response'",
                (session_id, hw_id),
            )
            row = await cur.fetchone()
            return int(row["n"]) if row else 0

    return _run(_do())


def test_check_answer_nudge_response_is_advisory_not_graded(client):
    """A submit with `nudge_response` returns {advisory: true} and records a
    session event — it is never scored (no `correct` / `score` / `passed`)."""
    sess = "blocker-nudge-001"
    hw_id = "hw-nudge-blocker"
    body = {
        "phase": "case_based_preview_reasoning",
        "homework_id": hw_id,
        "session_id": sess,
        "question_id": "cbp_reasoning_0",
        "nudge_response": "I solved it by balancing the forces with a free body diagram.",
    }
    resp = client.post("/api/ai/check-answer", json=body)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data == {"advisory": True}, data
    # Never scored.
    assert "correct" not in data and "score" not in data and "passed" not in data
    # The advisory event was recorded.
    assert _count_nudge_events(sess, hw_id) == 1


def test_check_answer_integrity_nudge_subphase_also_advisory(client):
    """subphase=='integrity-nudge' (with no explicit nudge_response) is also
    treated as the advisory follow-up and early-returns."""
    sess = "blocker-nudge-sub-1"
    hw_id = "hw-nudge-sub-blocker"
    body = {
        "phase": "case_based_preview_reasoning",
        "homework_id": hw_id,
        "session_id": sess,
        "subphase": "integrity-nudge",
        "question_id": "cbp_reasoning_0",
    }
    resp = client.post("/api/ai/check-answer", json=body)
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"advisory": True}
    assert _count_nudge_events(sess, hw_id) == 1


# ---------------------------------------------------------------------------
# H2 — affirmations listing requires at least one filter
# ---------------------------------------------------------------------------


def test_affirmations_unfiltered_is_rejected(client):
    """No filter → 400 (never a full-table dump of teacher notes)."""
    resp = client.get("/api/integrity/affirmations")
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "AFFIRM_FILTER_REQUIRED"


def test_affirmations_with_session_filter_is_allowed(client):
    """A scoped query (session_id present) still works — 200, list shape."""
    resp = client.get(
        "/api/integrity/affirmations", params={"session_id": "some-session"}
    )
    assert resp.status_code == 200, resp.text
    assert isinstance(resp.json(), list)


def test_affirmations_with_homework_filter_is_allowed(client):
    """homework_id alone also satisfies the filter requirement."""
    resp = client.get(
        "/api/integrity/affirmations", params={"homework_id": "some-hw"}
    )
    assert resp.status_code == 200, resp.text
    assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# M2 — decide route refuses a grading decision against an integrity row
# ---------------------------------------------------------------------------


def _seed_integrity_row(session_id: str) -> int:
    """Enroll one advisory integrity review row; return its id."""
    from server import db as _db
    from server.services.integrity_signals import IntegrityFlag

    async def go():
        await _db.add_integrity_flag(
            session_id,
            "hw-decide-blocker",
            "q-decide-1",
            IntegrityFlag(
                reason_code="sudden_mastery",
                severity="strong",
                detail={"pre_assessment_mastery": 0.1, "assessment_correct_rate": 1.0},
            ),
        )
        db_path = os.environ.get("NETS_DB_PATH")
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT id FROM review_queue "
                "WHERE kind = 'integrity' AND session_id = ? ORDER BY id DESC LIMIT 1",
                (session_id,),
            )
            row = await cur.fetchone()
            return int(row["id"])

    return _run(go())


def test_decide_rejects_grading_decision_on_integrity_row(client):
    """A normal {correct, score, feedback} decision against an integrity row →
    400 RQ_INTEGRITY_NOT_GRADEABLE (a flag is advisory, never a grade)."""
    rid = _seed_integrity_row("blocker-decide-001")
    resp = client.post(
        f"/api/ai/review-queue/{rid}/decide",
        json={"correct": True, "score": 1.0, "feedback": "looks fine"},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "RQ_INTEGRITY_NOT_GRADEABLE"


def test_decide_accepts_integrity_outcome_on_integrity_row(client):
    """The same integrity row CAN be resolved with an integrity_outcome."""
    rid = _seed_integrity_row("blocker-decide-002")
    resp = client.post(
        f"/api/ai/review-queue/{rid}/decide",
        json={
            "correct": False,
            "score": 0.0,
            "feedback": "",
            "integrity_outcome": "cleared",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "ok"


def test_decide_grading_decision_on_grading_row_still_works(client):
    """The legacy grading-review path is unchanged: a grading decision against a
    kind='grading' row resolves normally."""
    from server import db as _db

    async def seed():
        await _db.add_to_review_queue(
            question_id="grading-decide-q",
            student_answer="42",
            answer_spec={"type": "semantic", "expected": "x"},
            ai_response={"confidence": 0.4, "score": 0.5},
        )
        db_path = os.environ.get("NETS_DB_PATH")
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT id FROM review_queue "
                "WHERE kind = 'grading' AND question_id = 'grading-decide-q' "
                "ORDER BY id DESC LIMIT 1"
            )
            row = await cur.fetchone()
            return int(row["id"])

    rid = _run(seed())
    resp = client.post(
        f"/api/ai/review-queue/{rid}/decide",
        json={"correct": True, "score": 1.0, "feedback": "ok"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "ok"
