"""Authorship-affirmation repository (research §9.6).

An affirmation is a TEACHER record: "I reviewed this session and affirm (or
decline to affirm) that the student authored the work." It is human-in-the-loop
intelligence, never an automated grade input. The row optionally links to the
integrity review-queue items the teacher resolved when affirming, so the audit
trail is one hop from the affirmation to the signals it addressed.

Mirrors the connection/JSON pattern in ``review_queue_repo.py``: open → act →
close, JSON-encode list columns, return plain dicts with the list columns
decoded back.
"""
import json
from typing import Optional

from .connection import connect, _now


def _row_to_dict(row) -> dict:
    """Map an ``authorship_affirmations`` row to a plain dict.

    Decodes the two JSON list columns and normalizes ``affirmed`` to a bool so
    callers don't see SQLite's 0/1 integer.
    """
    d = dict(row)
    d["affirmed"] = bool(d.get("affirmed"))
    try:
        d["checkpoints"] = json.loads(d.pop("checkpoints_json") or "[]")
    except (TypeError, ValueError):
        d["checkpoints"] = []
    try:
        d["integrity_queue_ids"] = json.loads(d.pop("integrity_queue_ids_json") or "[]")
    except (TypeError, ValueError):
        d["integrity_queue_ids"] = []
    return d


async def create_affirmation(
    session_id: str,
    homework_id: str,
    *,
    teacher_id: Optional[str] = None,
    affirmed: bool = False,
    note: Optional[str] = None,
    checkpoints: Optional[list] = None,
    integrity_queue_ids: Optional[list] = None,
) -> dict:
    """Insert one affirmation row and return it (with its new ``id``)."""
    checkpoints_json = json.dumps(checkpoints or [], ensure_ascii=False)
    queue_ids_json = json.dumps(integrity_queue_ids or [], ensure_ascii=False)
    created_at = _now()
    db = await connect()
    try:
        cursor = await db.execute(
            "INSERT INTO authorship_affirmations "
            "(session_id, homework_id, teacher_id, affirmed, note, "
            " checkpoints_json, integrity_queue_ids_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                session_id,
                homework_id,
                teacher_id,
                1 if affirmed else 0,
                note,
                checkpoints_json,
                queue_ids_json,
                created_at,
            ),
        )
        await db.commit()
        new_id = cursor.lastrowid
    finally:
        await db.close()
    return {
        "id": new_id,
        "session_id": session_id,
        "homework_id": homework_id,
        "teacher_id": teacher_id,
        "affirmed": bool(affirmed),
        "note": note,
        "checkpoints": checkpoints or [],
        "integrity_queue_ids": integrity_queue_ids or [],
        "created_at": created_at,
    }


async def list_affirmations(
    session_id: Optional[str] = None,
    homework_id: Optional[str] = None,
) -> list[dict]:
    """List affirmations, optionally filtered by session and/or homework.

    Newest first. With neither filter, returns all rows (admin/audit view).
    """
    clauses: list[str] = []
    params: list = []
    if session_id is not None:
        clauses.append("session_id = ?")
        params.append(session_id)
    if homework_id is not None:
        clauses.append("homework_id = ?")
        params.append(homework_id)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    db = await connect()
    try:
        cursor = await db.execute(
            "SELECT * FROM authorship_affirmations"
            + where
            + " ORDER BY created_at DESC, id DESC",
            tuple(params),
        )
        rows = await cursor.fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        await db.close()
