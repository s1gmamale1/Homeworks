import json
from typing import Optional

from .connection import connect, _now


async def get_answer_cache(key: str) -> Optional[dict]:
    db = await connect()
    try:
        cursor = await db.execute(
            "SELECT response_json FROM answer_cache WHERE key = ?", (key,)
        )
        row = await cursor.fetchone()
        if row:
            return json.loads(row["response_json"])
        return None
    finally:
        await db.close()

async def set_answer_cache(key: str, response: dict) -> None:
    db = await connect()
    try:
        await db.execute(
            "INSERT OR REPLACE INTO answer_cache (key, response_json, created_at) VALUES (?, ?, ?)",
            (key, json.dumps(response, ensure_ascii=False), _now())
        )
        await db.commit()
    finally:
        await db.close()

async def add_to_review_queue(
    question_id: str,
    student_answer: str,
    answer_spec: dict,
    ai_response: dict,
    integrity_reason: Optional[str] = None,
    integrity_severity: Optional[str] = None,
    kind: str = "grading",
    session_id: Optional[str] = None,
) -> bool:
    """Insert a pending review item.  Idempotent.  Returns ``True`` when a new
    row was actually inserted, ``False`` when an equivalent pending row exists.

    Dedup keys depend on ``kind``:

      - ``kind='grading'`` (default, the legacy path) keys on
        ``question_id`` + ``student_answer`` — an identical pending grading row
        is never enrolled twice. Existing callers are unchanged.
      - ``kind='integrity'`` keys on ``question_id`` + ``integrity_reason`` +
        ``session_id`` (NOT student_answer — an integrity flag is about the
        interaction, not the literal answer, so the same flag for the same
        question in the same playthrough must not be re-enrolled on retry).

    Integrity rows are ADVISORY teacher intelligence; they never participate in
    grading and carry ``student_answer=""`` with the flag detail in
    ``ai_response``.
    """
    db = await connect()
    try:
        if kind == "integrity":
            # Integrity dedup: one row per (question, reason, playthrough).
            cursor = await db.execute(
                "SELECT id FROM review_queue "
                "WHERE kind = 'integrity' AND question_id = ? "
                "AND integrity_reason IS ? AND session_id IS ? "
                "AND status = 'pending' LIMIT 1",
                (question_id, integrity_reason, session_id),
            )
        else:
            # Grading dedup (unchanged): skip an identical pending grading row.
            cursor = await db.execute(
                "SELECT id FROM review_queue "
                "WHERE question_id = ? AND student_answer = ? "
                "AND kind = 'grading' AND status = 'pending' LIMIT 1",
                (question_id, student_answer),
            )
        existing = await cursor.fetchone()
        if existing:
            return False
        await db.execute(
            "INSERT INTO review_queue "
            "(question_id, student_answer, answer_spec_json, ai_response_json, "
            "status, created_at, integrity_reason, integrity_severity, kind, session_id) "
            "VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?)",
            (
                question_id,
                student_answer,
                json.dumps(answer_spec, ensure_ascii=False),
                json.dumps(ai_response, ensure_ascii=False),
                _now(),
                integrity_reason,
                integrity_severity,
                kind,
                session_id,
            ),
        )
        await db.commit()
        return True
    finally:
        await db.close()


async def add_integrity_flag(
    session_id: str,
    hw_id: str,
    question_id: str,
    flag,
) -> bool:
    """Enroll one advisory integrity flag into the review queue.

    Thin wrapper over ``add_to_review_queue(kind='integrity', ...)``. ``flag``
    is an ``integrity_signals.IntegrityFlag`` (reason_code / severity / detail).
    The flag's ``detail`` dict is stored in the ``ai_response_json`` blob (it is
    advisory evidence, never an AI grade); ``student_answer`` is ``""`` and
    ``answer_spec`` is empty because integrity rows are not gradeable.

    NEVER affects grading. The integration layer wraps this in try/except so a
    DB failure here can never break the student's graded response.
    """
    return await add_to_review_queue(
        question_id=question_id or "",
        student_answer="",
        answer_spec={},
        ai_response={
            "integrity": True,
            "reason_code": getattr(flag, "reason_code", None),
            "severity": getattr(flag, "severity", None),
            "detail": getattr(flag, "detail", {}) or {},
            "hw_id": hw_id,
        },
        integrity_reason=getattr(flag, "reason_code", None),
        integrity_severity=getattr(flag, "severity", None),
        kind="integrity",
        session_id=session_id,
    )


async def get_review_queue(kind: Optional[str] = None) -> list[dict]:
    db = await connect()
    try:
        if kind is not None:
            cursor = await db.execute(
                "SELECT * FROM review_queue "
                "WHERE status = 'pending' AND kind = ? ORDER BY created_at ASC",
                (kind,),
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM review_queue WHERE status = 'pending' ORDER BY created_at ASC"
            )
        rows = await cursor.fetchall()
        res = []
        for r in rows:
            d = dict(r)
            d["answer_spec"] = json.loads(d.pop("answer_spec_json"))
            d["ai_response"] = json.loads(d.pop("ai_response_json"))
            res.append(d)
        return res
    finally:
        await db.close()

async def resolve_review_item(id: int, decision: dict) -> bool:
    """Persist the teacher's decision and mark the review item resolved.

    `decision` is stored verbatim as JSON so the schema doesn't need to grow
    every time we add a new field (e.g. {correct, score, feedback, override_reason}).
    """
    db = await connect()
    try:
        cursor = await db.execute(
            "UPDATE review_queue "
            "SET status = 'resolved', decision_json = ?, resolved_at = ? "
            "WHERE id = ? AND status = 'pending'",
            (json.dumps(decision, ensure_ascii=False), _now(), id),
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()
