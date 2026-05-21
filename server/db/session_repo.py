import json
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


async def update_session_boss_xp(session_id: str, xp: int) -> None:
    """Persist `outcome_xp` to sessions.boss_xp_earned at boss defeat.

    Boss is once-per-session per spec, but no DB constraint enforces it —
    last-write-wins if a duplicate defeat fires (e.g., retry path). Column
    defaults to 0 and is overwritten with the integer XP value computed by
    the boss outcome helper (legacy `_boss_outcome_for` or Plan-5
    `boss_dynamic.compute_boss_outcome`).
    """
    db = await connect()
    try:
        await db.execute(
            "UPDATE sessions SET boss_xp_earned = ? WHERE id = ?",
            (int(xp), session_id),
        )
        await db.commit()
    finally:
        await db.close()