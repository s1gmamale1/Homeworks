import json
from datetime import datetime, timezone
from typing import Optional
from .connection import connect

async def get_session(session_id: str) -> Optional[dict]:
    db = await connect()
    try:
        async with db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            session = dict(row)
            if session.get('tutor_summary_json'):
                session['tutor_summary'] = json.loads(session['tutor_summary_json'])
            if session.get('performance_summary_json'):
                session['performance_summary'] = json.loads(session['performance_summary_json'])
            if session.get('boss_state_json'):
                session['boss_state'] = json.loads(session['boss_state_json'])
            return session
    finally:
        await db.close()

async def create_session(session_id: str, homework_id: str, student_name: str, started_at: str) -> None:
    db = await connect()
    try:
        await db.execute(
            """
            INSERT INTO sessions (id, homework_id, student_name, started_at, status)
            VALUES (?, ?, ?, ?, 'active')
            """,
            (session_id, homework_id, student_name, started_at)
        )
        await db.commit()
    finally:
        await db.close()


async def ensure_session(session_id: str, homework_id: str) -> dict:
    """Get-or-create the sessions row for (session_id, homework_id).

    The v2 React runtime generates session_ids client-side (localStorage) and
    writes attempts under them, but no production code path inserts into the
    parent `sessions` table — so `get_session` returns None for every real
    student, even though their phase_attempts exist. Endpoints that need the
    row (reflection finalize/redo, which call `_write_session_mark` to persist
    verdict + ended_at) must call this helper to materialize the row first.

    Idempotent: if the row already exists, returns it untouched. Otherwise
    inserts a minimal `active` row with `started_at = now` and returns it.
    """
    existing = await get_session(session_id)
    if existing is not None:
        return existing
    started_at = datetime.now(timezone.utc).isoformat()
    db = await connect()
    try:
        # INSERT OR IGNORE so a concurrent finalize from another tab doesn't
        # 500 on UNIQUE(id) — whichever request lands first wins, the other
        # silently no-ops and re-reads below.
        await db.execute(
            """
            INSERT OR IGNORE INTO sessions (id, homework_id, student_name, started_at, status)
            VALUES (?, ?, ?, ?, 'active')
            """,
            (session_id, homework_id, "anonymous", started_at),
        )
        await db.commit()
    finally:
        await db.close()
    # Re-read so callers see the same shape get_session returns (parsed JSON cols).
    row = await get_session(session_id)
    assert row is not None, "ensure_session: row missing after INSERT OR IGNORE"
    return row