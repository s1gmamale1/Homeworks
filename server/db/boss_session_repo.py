"""Boss-session persistence for Plan 5 (Dynamic Boss AI).

Plan 5 introduces a per-student-session boss state machine separate from the
legacy ``content_json.boss_questions`` flow. Each ``boss_sessions`` row tracks
HP, trials, current difficulty, the queue of asked question IDs, and a snapshot
of weak/strong topics at boss-start time.

The legacy ``/ai/boss-turn`` route and the ``content_json.boss_questions``
content path remain intact; this repo only governs the new dynamic boss layer.
"""
import json
from typing import Optional, Any
from datetime import datetime, timezone

from .connection import connect


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def create_boss_session(
    boss_session_id: str,
    session_id: str,
    homework_id: str,
    *,
    max_hp: int = 100,
    trials_left: int = 7,
    current_difficulty: str = "medium",
    weak_topics: Optional[list[str]] = None,
    strong_topics: Optional[list[str]] = None,
) -> dict:
    """Insert a new boss session row and return its hydrated dict form."""
    now = _utc_now_iso()
    weak_json = json.dumps(weak_topics or [])
    strong_json = json.dumps(strong_topics or [])
    db = await connect()
    try:
        await db.execute(
            """
            INSERT INTO boss_sessions (
                id, session_id, homework_id, status, hp, max_hp,
                trials_left, current_difficulty, current_question_id,
                asked_question_ids_json, weak_topics_json, strong_topics_json,
                created_at, updated_at
            )
            VALUES (?, ?, ?, 'active', ?, ?, ?, ?, NULL, '[]', ?, ?, ?, ?)
            """,
            (
                boss_session_id, session_id, homework_id,
                max_hp, max_hp, trials_left, current_difficulty,
                weak_json, strong_json, now, now,
            ),
        )
        await db.commit()
    finally:
        await db.close()

    return {
        "id": boss_session_id,
        "session_id": session_id,
        "homework_id": homework_id,
        "status": "active",
        "hp": max_hp,
        "max_hp": max_hp,
        "trials_left": trials_left,
        "current_difficulty": current_difficulty,
        "current_question_id": None,
        "asked_question_ids": [],
        "weak_topics": list(weak_topics or []),
        "strong_topics": list(strong_topics or []),
        "created_at": now,
        "updated_at": now,
    }


def _row_to_boss_session(row: Any) -> dict:
    d = dict(row)
    d["asked_question_ids"] = json.loads(d.get("asked_question_ids_json") or "[]")
    d["weak_topics"] = json.loads(d.get("weak_topics_json") or "[]")
    d["strong_topics"] = json.loads(d.get("strong_topics_json") or "[]")
    return d


async def get_boss_session(boss_session_id: str) -> Optional[dict]:
    db = await connect()
    try:
        async with db.execute(
            "SELECT * FROM boss_sessions WHERE id = ?",
            (boss_session_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return _row_to_boss_session(row) if row else None
    finally:
        await db.close()


async def get_active_boss_session_for(session_id: str, homework_id: str) -> Optional[dict]:
    """Return the most recent active boss session for this (session, hw)."""
    db = await connect()
    try:
        async with db.execute(
            """
            SELECT * FROM boss_sessions
            WHERE session_id = ? AND homework_id = ? AND status = 'active'
            ORDER BY created_at DESC LIMIT 1
            """,
            (session_id, homework_id),
        ) as cursor:
            row = await cursor.fetchone()
            return _row_to_boss_session(row) if row else None
    finally:
        await db.close()


async def update_boss_session(
    boss_session_id: str,
    *,
    hp: Optional[int] = None,
    trials_left: Optional[int] = None,
    current_difficulty: Optional[str] = None,
    current_question_id: Optional[str] = None,
    asked_question_ids: Optional[list[str]] = None,
    status: Optional[str] = None,
) -> Optional[dict]:
    """Patch any subset of mutable fields. Returns the updated row, or None if missing."""
    fields: list[str] = []
    values: list[Any] = []
    if hp is not None:
        fields.append("hp = ?")
        values.append(int(hp))
    if trials_left is not None:
        fields.append("trials_left = ?")
        values.append(int(trials_left))
    if current_difficulty is not None:
        fields.append("current_difficulty = ?")
        values.append(current_difficulty)
    if current_question_id is not None:
        fields.append("current_question_id = ?")
        values.append(current_question_id)
    if asked_question_ids is not None:
        fields.append("asked_question_ids_json = ?")
        values.append(json.dumps(list(asked_question_ids)))
    if status is not None:
        fields.append("status = ?")
        values.append(status)
    if not fields:
        return await get_boss_session(boss_session_id)

    fields.append("updated_at = ?")
    values.append(_utc_now_iso())
    values.append(boss_session_id)

    db = await connect()
    try:
        await db.execute(
            f"UPDATE boss_sessions SET {', '.join(fields)} WHERE id = ?",
            values,
        )
        await db.commit()
    finally:
        await db.close()
    return await get_boss_session(boss_session_id)


async def append_asked_question(boss_session_id: str, question_id: str) -> Optional[dict]:
    """Append ``question_id`` to the asked queue and bump current_question_id.

    Bug-Backend-#4 fix (2026-05-13 audit): the read-then-write sequence used
    to be split across two SQLite connections, racing with any concurrent
    /generate-question for the same boss session. Two parallel calls could
    both see asked_question_ids=[A], both append their B/C locally, and one
    write would overwrite the other (losing B or C from the queue, which
    then weakens anti-repetition for that lost question).

    Fix: hold a single connection across SELECT+UPDATE wrapped in
    BEGIN IMMEDIATE — SQLite acquires a RESERVED lock on the first write
    intent, blocking concurrent writers until COMMIT. Other readers proceed.
    """
    db = await connect()
    try:
        await db.execute("BEGIN IMMEDIATE")
        try:
            async with db.execute(
                "SELECT asked_question_ids_json FROM boss_sessions WHERE id = ?",
                (boss_session_id,),
            ) as cursor:
                row = await cursor.fetchone()
            if not row:
                await db.execute("ROLLBACK")
                return None
            asked = json.loads(row[0] or "[]")
            if question_id not in asked:
                asked.append(question_id)
            await db.execute(
                "UPDATE boss_sessions "
                "SET asked_question_ids_json = ?, current_question_id = ?, updated_at = ? "
                "WHERE id = ?",
                (json.dumps(asked), question_id, _utc_now_iso(), boss_session_id),
            )
            await db.commit()
        except Exception:
            await db.execute("ROLLBACK")
            raise
    finally:
        await db.close()
    return await get_boss_session(boss_session_id)
