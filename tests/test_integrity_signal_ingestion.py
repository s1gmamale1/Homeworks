"""Anti-cheat signal ingestion — ADVISORY-ONLY proof + clamp guard.

These tests guard the wiring agent's core invariant: the optional
``client_time_ms`` / ``paste_detected`` signals are recorded (into
``phase_attempts.time_ms`` and a ``integrity:paste`` session event) but
NEVER change the grade. A regression that let a signal flip ``is_correct`` /
``score`` would be a fairness + correctness violation, so each test asserts
the grade is byte-identical with vs. without the signals.

We submit through the real ``POST /api/ai/runtime/submit-answer`` endpoint with
a DETERMINISTIC ``answer_spec`` (text_exact) so no AI backend is needed.
"""
from __future__ import annotations

import asyncio
import os

import aiosqlite


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_hw(client, *, hint: str) -> str:
    """A homework whose practice phase has one deterministically-gradeable item."""
    payload = {
        "title": f"Integrity ingestion HW ({hint})",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
        "family": "aniq-fanlar",
        "content_json": {
            "title": f"Integrity ingestion HW ({hint})",
            "subject": "math-algebra",
            "grade": 8,
            "practice": {
                "items": [
                    {
                        "id": "q1",
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


def _submit(client, hw_id, session_id, *, answer="4", **extra):
    body = {
        "session_id": session_id,
        "homework_id": hw_id,
        "phase": "practice",
        "question_id": "q1",
        "answer_type": "text",
        "student_answer": answer,
    }
    body.update(extra)
    return client.post("/api/ai/runtime/submit-answer", json=body)


def _query_time_ms(session_id: str, hw_id: str):
    db_path = os.environ.get("NETS_DB_PATH")

    async def _do():
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT time_ms FROM phase_attempts "
                "WHERE session_id = ? AND hw_id = ? ORDER BY id DESC LIMIT 1",
                (session_id, hw_id),
            )
            row = await cur.fetchone()
            return row["time_ms"] if row else None

    return _run(_do())


def _count_paste_events(session_id: str, hw_id: str) -> int:
    db_path = os.environ.get("NETS_DB_PATH")

    async def _do():
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT COUNT(*) AS n FROM session_events "
                "WHERE session_id = ? AND hw_id = ? AND event_type = 'integrity:paste'",
                (session_id, hw_id),
            )
            row = await cur.fetchone()
            return int(row["n"]) if row else 0

    return _run(_do())


def _run(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_client_time_ms_populates_phase_attempt_time_ms(client):
    hw_id = _make_hw(client, hint="time")
    sess = "integ-time-0001"
    resp = _submit(client, hw_id, sess, client_time_ms=4200)
    assert resp.status_code == 200, resp.text
    assert _query_time_ms(sess, hw_id) == 4200


def test_paste_detected_records_integrity_paste_event(client):
    hw_id = _make_hw(client, hint="paste")
    sess = "integ-paste-0001"
    resp = _submit(client, hw_id, sess, paste_detected=True)
    assert resp.status_code == 200, resp.text
    assert _count_paste_events(sess, hw_id) == 1


def test_no_paste_event_when_flag_absent(client):
    hw_id = _make_hw(client, hint="nopaste")
    sess = "integ-nopaste-0001"
    resp = _submit(client, hw_id, sess)  # no paste_detected
    assert resp.status_code == 200, resp.text
    assert _count_paste_events(sess, hw_id) == 0


def test_signals_are_advisory_only_grade_identical_with_and_without(client):
    """The load-bearing fairness proof: the SAME answer graded with vs. without
    the anti-cheat signals must yield an identical score / is_correct."""
    hw_id = _make_hw(client, hint="advisory")

    plain = _submit(client, hw_id, "integ-adv-plain-001").json()
    signaled = _submit(
        client,
        hw_id,
        "integ-adv-signal-01",
        client_time_ms=10,  # very fast — would trip too_fast IF policy opted in
        paste_detected=True,
    ).json()

    assert plain["is_correct"] == signaled["is_correct"] is True
    assert plain["score"] == signaled["score"] == 1.0
    assert plain["confidence"] == signaled["confidence"]
    # An incorrect submit must also be unaffected by the signals.
    wrong_plain = _submit(client, hw_id, "integ-adv-wp-001", answer="5").json()
    wrong_signal = _submit(
        client, hw_id, "integ-adv-ws-001", answer="5",
        client_time_ms=5, paste_detected=True,
    ).json()
    assert wrong_plain["is_correct"] == wrong_signal["is_correct"] is False
    assert wrong_plain["score"] == wrong_signal["score"] == 0.0


def test_client_time_ms_clamped_negative_and_huge_become_null(client):
    """A negative / absurd / zero time is garbage → time_ms stored as NULL, and
    the grade is still unaffected."""
    hw_id = _make_hw(client, hint="clamp")

    # Negative.
    s1 = "integ-clamp-neg-01"
    r1 = _submit(client, hw_id, s1, client_time_ms=-5)
    assert r1.status_code == 200, r1.text
    assert _query_time_ms(s1, hw_id) is None

    # Absurdly large (>= 24h in ms).
    s2 = "integ-clamp-big-01"
    r2 = _submit(client, hw_id, s2, client_time_ms=999_999_999)
    assert r2.status_code == 200, r2.text
    assert _query_time_ms(s2, hw_id) is None

    # Zero is not a valid measured time either.
    s3 = "integ-clamp-zero-1"
    r3 = _submit(client, hw_id, s3, client_time_ms=0)
    assert r3.status_code == 200, r3.text
    assert _query_time_ms(s3, hw_id) is None

    # And the grade is intact in every clamp case.
    assert r1.json()["is_correct"] is True
    assert r2.json()["is_correct"] is True
    assert r3.json()["is_correct"] is True


def test_clamp_unit_rejects_bool_and_float():
    """Direct unit coverage of the clamp helper's type discipline."""
    from server.services.integrity_wiring import clamp_client_time_ms

    assert clamp_client_time_ms(4200) == 4200
    assert clamp_client_time_ms(None) is None
    assert clamp_client_time_ms(0) is None
    assert clamp_client_time_ms(-1) is None
    assert clamp_client_time_ms(86_400_000) is None  # boundary excluded
    assert clamp_client_time_ms(True) is None  # bool must not pass as 1ms
    assert clamp_client_time_ms(12.5) is None
    assert clamp_client_time_ms("4200") is None
