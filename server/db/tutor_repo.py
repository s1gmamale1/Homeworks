from typing import Optional

from .connection import connect, _now


# ---------------------------------------------------------------------------
# Wave F1 — tutor_conversations helpers
# ---------------------------------------------------------------------------
#
# The `tutor_conversations` table is owned by the tutor lane. Each row is a
# single chat turn (user|assistant|system) scoped to a (session_id, hw_id).
# We never modify rows after insertion — chat history is append-only.


async def add_tutor_turn(
    session_id: str,
    hw_id: str,
    phase: str,
    question_id: Optional[str],
    role: str,
    content: str,
) -> int:
    """Append a chat turn. Returns the new row id."""
    db = await connect()
    try:
        cursor = await db.execute(
            "INSERT INTO tutor_conversations "
            "(session_id, hw_id, phase, question_id, role, content, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (session_id, hw_id, phase, question_id, role, content, _now()),
        )
        await db.commit()
        return cursor.lastrowid or 0
    finally:
        await db.close()


async def list_tutor_turns(
    session_id: str,
    hw_id: str,
    limit: int = 50,
    *,
    most_recent: bool = False,
) -> list[dict]:
    """Turns for a (session_id, hw_id), capped at `limit`.

    Default order is chronological (oldest first) — the shape `/api/ai/tutor/history`
    returns to the client. When `most_recent=True`, fetch the *last* N turns
    (newest first in SQL, then reversed to chronological) — used by the chat
    prompt builder to grab the recent-history window without scanning the full
    session up to the cap.
    """
    db = await connect()
    try:
        if most_recent:
            cursor = await db.execute(
                "SELECT id, session_id, hw_id, phase, question_id, role, content, created_at "
                "FROM tutor_conversations "
                "WHERE session_id = ? AND hw_id = ? "
                "ORDER BY created_at DESC, id DESC LIMIT ?",
                (session_id, hw_id, limit),
            )
            rows = await cursor.fetchall()
            return list(reversed([dict(r) for r in rows]))
        cursor = await db.execute(
            "SELECT id, session_id, hw_id, phase, question_id, role, content, created_at "
            "FROM tutor_conversations "
            "WHERE session_id = ? AND hw_id = ? "
            "ORDER BY created_at ASC, id ASC LIMIT ?",
            (session_id, hw_id, limit),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def count_session_messages(session_id: str, hw_id: str) -> int:
    """Total tutor turns for one (session_id, hw_id). Used for the 60-message cap."""
    db = await connect()
    try:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM tutor_conversations "
            "WHERE session_id = ? AND hw_id = ?",
            (session_id, hw_id),
        )
        row = await cursor.fetchone()
        return int(row[0]) if row else 0
    finally:
        await db.close()


async def build_session_profile(session_id: str, hw_id: str) -> str:
    """Concatenate the last 20 user+assistant turns into a compact profile string.

    No AI summarization in v1 — just a chronological dump (oldest first), each
    line prefixed with the role, truncated to ~1500 chars to keep the boss-plan
    prompt context tight.
    """
    db = await connect()
    try:
        cursor = await db.execute(
            "SELECT role, content FROM tutor_conversations "
            "WHERE session_id = ? AND hw_id = ? AND role IN ('user', 'assistant') "
            "ORDER BY created_at DESC, id DESC LIMIT 20",
            (session_id, hw_id),
        )
        rows = await cursor.fetchall()
    finally:
        await db.close()
    # Reverse so output reads chronologically.
    rows = list(reversed(rows))
    lines = [f"{r['role']}: {r['content']}" for r in rows]
    profile = "\n".join(lines)
    if len(profile) > 1500:
        profile = profile[-1500:]
    return profile


# ---------------------------------------------------------------------------
# Wave J — tutor_warnings helpers
# ---------------------------------------------------------------------------
#
# Records every warning event cross-session per hw_id. Counters never reset
# when the student reopens the homework — that's by design (troll-deterrence).


async def add_warning(
    *,
    session_id: str,
    hw_id: str,
    severity: str,
    category: str,
    matched_term: Optional[str],
    warning_level: int,
    deduction_pct: int,
    is_big_warning: bool,
    is_fail: bool,
) -> int:
    """Append a warning event. Returns the new row id."""
    db = await connect()
    try:
        cursor = await db.execute(
            "INSERT INTO tutor_warnings "
            "(session_id, hw_id, severity, category, matched_term, "
            "warning_level, deduction_pct, is_big_warning, is_fail, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                session_id,
                hw_id,
                severity,
                category,
                matched_term,
                warning_level,
                deduction_pct,
                1 if is_big_warning else 0,
                1 if is_fail else 0,
                _now(),
            ),
        )
        await db.commit()
        return cursor.lastrowid or 0
    finally:
        await db.close()


async def count_warnings_for_hw(hw_id: str) -> int:
    """Total warning events ever recorded for this hw_id across all sessions."""
    db = await connect()
    try:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM tutor_warnings WHERE hw_id = ?",
            (hw_id,),
        )
        row = await cursor.fetchone()
        return int(row[0]) if row else 0
    finally:
        await db.close()


async def count_warnings_for_session(session_id: str, hw_id: str) -> int:
    """Warning events for a specific (session_id, hw_id) pair."""
    db = await connect()
    try:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM tutor_warnings WHERE session_id = ? AND hw_id = ?",
            (session_id, hw_id),
        )
        row = await cursor.fetchone()
        return int(row[0]) if row else 0
    finally:
        await db.close()


async def list_recent_warnings(hw_id: str, limit: int = 5) -> list[dict]:
    """Newest-first; used for the 'mild repeated 3x in last 5 turns' rule."""
    db = await connect()
    try:
        cursor = await db.execute(
            "SELECT id, session_id, hw_id, severity, category, matched_term, "
            "warning_level, deduction_pct, is_big_warning, is_fail, created_at "
            "FROM tutor_warnings "
            "WHERE hw_id = ? "
            "ORDER BY created_at DESC, id DESC LIMIT ?",
            (hw_id, limit),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def sum_deductions(hw_id: str) -> int:
    """Sum of all deduction_pct rows for an hw_id (idempotent across sessions)."""
    db = await connect()
    try:
        cursor = await db.execute(
            "SELECT COALESCE(SUM(deduction_pct), 0) FROM tutor_warnings WHERE hw_id = ?",
            (hw_id,),
        )
        row = await cursor.fetchone()
        return int(row[0]) if row else 0
    finally:
        await db.close()


async def summary_for_tutor(hw_id: str) -> str:
    """Compact one-line summary for prompt injection.

    Returns '' if no prior warnings.
    Otherwise: 'earlier this hw: 2 profanity_strong, 1 insult_mild'
    (counts by severity, no quoted terms — keeps slurs out of the LLM context).
    """
    db = await connect()
    try:
        cursor = await db.execute(
            "SELECT severity, COUNT(*) as cnt FROM tutor_warnings "
            "WHERE hw_id = ? GROUP BY severity ORDER BY cnt DESC",
            (hw_id,),
        )
        rows = await cursor.fetchall()
    finally:
        await db.close()

    if not rows:
        return ""

    parts = [f"{row['cnt']} {row['severity']}" for row in rows]
    return "earlier this hw: " + ", ".join(parts)
