from typing import Optional

from .connection import connect, _now


# ---------------------------------------------------------------------------
# Wave K — notebook_captures helpers
# ---------------------------------------------------------------------------
#
# Persists each notebook formula capture attempt — both rejected (input/prefilter
# failures) and graded ones — so we can audit, show retry history, and rate-limit.


async def add_capture(
    *,
    session_id: str,
    hw_id: str,
    question_id: str,
    photo_id: Optional[str],
    status: str,
    rejection_reason: Optional[str] = None,
    transcribed_text: Optional[str] = None,
    confidence: Optional[float] = None,
    score_1_to_4: Optional[int] = None,
    axis_1_concept_id: Optional[int] = None,
    axis_2_process_integrity: Optional[int] = None,
    correct: Optional[int] = None,
    feedback: Optional[str] = None,
    grade_json: Optional[str] = None,
) -> int:
    """Append a capture event. Returns the new row id.

    `status` is 'graded' | 'rejected'. For rejections, only photo_id +
    rejection_reason + (optionally) confidence/transcribed_text are populated.
    """
    db = await connect()
    try:
        cursor = await db.execute(
            "INSERT INTO notebook_captures "
            "(session_id, hw_id, question_id, photo_id, status, rejection_reason, "
            "transcribed_text, confidence, score_1_to_4, axis_1_concept_id, "
            "axis_2_process_integrity, correct, feedback, grade_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                session_id,
                hw_id,
                question_id,
                photo_id,
                status,
                rejection_reason,
                transcribed_text,
                confidence,
                score_1_to_4,
                axis_1_concept_id,
                axis_2_process_integrity,
                correct,
                feedback,
                grade_json,
                _now(),
            ),
        )
        await db.commit()
        return cursor.lastrowid or 0
    finally:
        await db.close()


async def get_capture(capture_id: int) -> Optional[dict]:
    """Fetch a single capture row by id, or None if not found."""
    db = await connect()
    try:
        cursor = await db.execute(
            "SELECT * FROM notebook_captures WHERE id = ?",
            (capture_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def list_captures_for_session(session_id: str, hw_id: str) -> list[dict]:
    """All capture rows for a (session_id, hw_id) pair, newest-first."""
    db = await connect()
    try:
        cursor = await db.execute(
            "SELECT * FROM notebook_captures "
            "WHERE session_id = ? AND hw_id = ? "
            "ORDER BY created_at DESC, id DESC",
            (session_id, hw_id),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def count_captures_for_question(hw_id: str, question_id: str) -> int:
    """Total captures (graded + rejected) for one question across all sessions."""
    db = await connect()
    try:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM notebook_captures "
            "WHERE hw_id = ? AND question_id = ?",
            (hw_id, question_id),
        )
        row = await cursor.fetchone()
        return int(row[0]) if row else 0
    finally:
        await db.close()


async def latest_capture(
    session_id: str, hw_id: str, question_id: str
) -> Optional[dict]:
    """Most recent capture row for this (session, hw, question), or None."""
    db = await connect()
    try:
        cursor = await db.execute(
            "SELECT * FROM notebook_captures "
            "WHERE session_id = ? AND hw_id = ? AND question_id = ? "
            "ORDER BY created_at DESC, id DESC LIMIT 1",
            (session_id, hw_id, question_id),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()
