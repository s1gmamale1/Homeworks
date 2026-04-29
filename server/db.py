import json
import sqlite3
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

from .config import get_db_path


_SCHEMA = """
CREATE TABLE IF NOT EXISTS homeworks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    subject TEXT NOT NULL,
    grade INTEGER NOT NULL,
    mode TEXT NOT NULL,
    family TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'uz',
    status TEXT NOT NULL DEFAULT 'draft',
    content_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    homework_id TEXT NOT NULL,
    student_name TEXT,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    overall_score REAL,
    phase_scores TEXT,
    FOREIGN KEY (homework_id) REFERENCES homeworks(id)
);

CREATE TABLE IF NOT EXISTS responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    phase TEXT NOT NULL,
    question_id TEXT,
    answer TEXT,
    correct INTEGER,
    time_ms INTEGER,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS homework_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    homework_id TEXT NOT NULL,
    content_json TEXT NOT NULL,
    title TEXT,
    saved_at TEXT NOT NULL,
    FOREIGN KEY (homework_id) REFERENCES homeworks(id)
);

CREATE TABLE IF NOT EXISTS answer_cache (
    key TEXT PRIMARY KEY,
    response_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS review_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id TEXT NOT NULL,
    student_answer TEXT NOT NULL,
    answer_spec_json TEXT NOT NULL,
    ai_response_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    decision_json TEXT NULL,
    resolved_at TEXT NULL
);

CREATE INDEX IF NOT EXISTS idx_versions_hw_saved
    ON homework_versions(homework_id, saved_at DESC);

CREATE INDEX IF NOT EXISTS idx_review_pending
    ON review_queue(question_id, student_answer) WHERE status='pending';

CREATE TABLE IF NOT EXISTS tutor_conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    hw_id TEXT NOT NULL,
    phase TEXT NOT NULL,
    question_id TEXT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tutor_session
    ON tutor_conversations(session_id, hw_id, created_at);

CREATE TABLE IF NOT EXISTS tutor_warnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    hw_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    category TEXT NOT NULL,
    matched_term TEXT,
    warning_level INTEGER NOT NULL,
    deduction_pct INTEGER DEFAULT 0,
    is_big_warning INTEGER DEFAULT 0,
    is_fail INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_warnings_hw ON tutor_warnings(hw_id, created_at);
CREATE INDEX IF NOT EXISTS idx_warnings_session ON tutor_warnings(session_id, hw_id, created_at);

CREATE TABLE IF NOT EXISTS notebook_captures (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    hw_id           TEXT NOT NULL,
    question_id     TEXT NOT NULL,
    photo_id        TEXT,
    status          TEXT NOT NULL,
    rejection_reason TEXT,
    transcribed_text TEXT,
    confidence      REAL,
    score_1_to_4    INTEGER,
    axis_1_concept_id INTEGER,
    axis_2_process_integrity INTEGER,
    correct         INTEGER,
    feedback        TEXT,
    grade_json      TEXT,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_captures_session ON notebook_captures(session_id, hw_id, created_at);
CREATE INDEX IF NOT EXISTS idx_captures_question ON notebook_captures(hw_id, question_id);
"""


# Pragmas that are per-connection and must be set every time a connection opens.
# WAL/synchronous are persistent on the DB file itself but are cheap to re-assert.
# foreign_keys and busy_timeout are strictly per-connection.
_DURABILITY_PRAGMAS = (
    "PRAGMA journal_mode = WAL;",
    "PRAGMA synchronous = FULL;",
    "PRAGMA foreign_keys = ON;",
    "PRAGMA busy_timeout = 5000;",
    "PRAGMA wal_autocheckpoint = 100;",
)

# Snapshot thresholds
_SNAPSHOT_MIN_INTERVAL_SEC = 120
_SNAPSHOT_SIZE_DELTA_BYTES = 500


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


async def apply_pragmas(db: aiosqlite.Connection) -> None:
    for stmt in _DURABILITY_PRAGMAS:
        await db.execute(stmt)


async def connect() -> aiosqlite.Connection:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    await apply_pragmas(db)
    return db


async def init_db() -> None:
    db = await connect()
    try:
        # Pragmas already applied via connect; reassert for clarity on fresh DBs.
        await apply_pragmas(db)
        await db.executescript(_SCHEMA)
        # Migrate existing DBs that predate the `deleted_at` column.
        try:
            await db.execute("ALTER TABLE homeworks ADD COLUMN deleted_at TEXT NULL")
        except Exception:
            # Column already exists — safe to ignore.
            pass
        # Migrate existing DBs that predate Wave-D review_queue decision columns.
        for migration in (
            "ALTER TABLE review_queue ADD COLUMN decision_json TEXT NULL",
            "ALTER TABLE review_queue ADD COLUMN resolved_at TEXT NULL",
        ):
            try:
                await db.execute(migration)
            except Exception:
                # Column already exists — safe to ignore.
                pass
        await db.commit()
    finally:
        await db.close()


async def checkpoint() -> None:
    """Force a full WAL checkpoint. Call on graceful shutdown or periodically."""
    db_path = get_db_path()
    async with aiosqlite.connect(db_path) as db:
        await apply_pragmas(db)
        await db.execute("PRAGMA wal_checkpoint(FULL)")
        await db.commit()


def _row_to_homework(row: aiosqlite.Row) -> dict:
    d = dict(row)
    raw = d.get("content_json")
    d["content_json"] = json.loads(raw) if raw else None
    return d


async def list_homeworks(include_deleted: bool = False) -> list[dict]:
    db = await connect()
    try:
        if include_deleted:
            sql = (
                "SELECT id, title, subject, grade, mode, family, language, status, "
                "created_at, updated_at, deleted_at FROM homeworks "
                "ORDER BY created_at DESC"
            )
            cursor = await db.execute(sql)
        else:
            sql = (
                "SELECT id, title, subject, grade, mode, family, language, status, "
                "created_at, updated_at, deleted_at FROM homeworks "
                "WHERE deleted_at IS NULL ORDER BY created_at DESC"
            )
            cursor = await db.execute(sql)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def search_homeworks(
    q: Optional[str] = None,
    subject: Optional[str] = None,
    grade: Optional[int] = None,
    mode: Optional[str] = None,
    include_deleted: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Paginated + filtered homework list. Returns {items, total, limit, offset}."""
    conditions = []
    params: list = []

    if not include_deleted:
        conditions.append("deleted_at IS NULL")

    if q:
        like = f"%{q}%"
        conditions.append(
            "(title LIKE ? OR subject LIKE ? OR family LIKE ?)"
        )
        params.extend([like, like, like])

    if subject:
        conditions.append("subject = ?")
        params.append(subject)

    if grade is not None:
        conditions.append("grade = ?")
        params.append(grade)

    if mode:
        conditions.append("mode = ?")
        params.append(mode)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    cols = (
        "id, title, subject, grade, mode, family, language, status, "
        "created_at, updated_at, deleted_at"
    )
    count_sql = f"SELECT COUNT(*) FROM homeworks {where}"
    list_sql = (
        f"SELECT {cols} FROM homeworks {where} "
        f"ORDER BY created_at DESC LIMIT ? OFFSET ?"
    )

    db = await connect()
    try:
        count_cursor = await db.execute(count_sql, params)
        count_row = await count_cursor.fetchone()
        total = count_row[0] if count_row else 0

        list_cursor = await db.execute(list_sql, params + [limit, offset])
        rows = await list_cursor.fetchall()
        items = [dict(r) for r in rows]
    finally:
        await db.close()

    return {"items": items, "total": total, "limit": limit, "offset": offset}


async def list_trashed_homeworks() -> list[dict]:
    """Only soft-deleted rows — for the Trash view."""
    db = await connect()
    try:
        cursor = await db.execute(
            "SELECT id, title, subject, grade, mode, family, language, status, "
            "created_at, updated_at, deleted_at FROM homeworks "
            "WHERE deleted_at IS NOT NULL ORDER BY deleted_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def get_homework(id: str) -> Optional[dict]:
    """Returns the record even if soft-deleted — needed for restore + preview."""
    db = await connect()
    try:
        cursor = await db.execute("SELECT * FROM homeworks WHERE id = ?", (id,))
        row = await cursor.fetchone()
        return _row_to_homework(row) if row else None
    finally:
        await db.close()


async def _next_id(db: aiosqlite.Connection) -> str:
    stamp = _today_stamp()
    prefix = f"HW-{stamp}-"
    cursor = await db.execute(
        "SELECT id FROM homeworks WHERE id LIKE ? ORDER BY id DESC LIMIT 1",
        (prefix + "%",),
    )
    row = await cursor.fetchone()
    if row:
        last_seq = int(row[0].rsplit("-", 1)[1])
        seq = last_seq + 1
    else:
        seq = 1
    return f"{prefix}{seq:03d}"


async def create_homework(data: dict) -> dict:
    now = _now()
    content = data.get("content_json") or {}
    content_str = json.dumps(content, ensure_ascii=False)

    db = await connect()
    try:
        new_id = await _next_id(db)
        await db.execute(
            "INSERT INTO homeworks (id, title, subject, grade, mode, family, "
            "language, status, content_json, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                new_id,
                data["title"],
                data["subject"],
                data["grade"],
                data["mode"],
                data["family"],
                data.get("language", "uz"),
                data.get("status", "draft"),
                content_str,
                now,
                now,
            ),
        )
        await db.commit()
    finally:
        await db.close()

    record = await get_homework(new_id)
    assert record is not None
    return record


async def _get_latest_version(
    db: aiosqlite.Connection, homework_id: str
) -> Optional[aiosqlite.Row]:
    cursor = await db.execute(
        "SELECT id, content_json, title, saved_at FROM homework_versions "
        "WHERE homework_id = ? ORDER BY saved_at DESC LIMIT 1",
        (homework_id,),
    )
    return await cursor.fetchone()


def _should_snapshot(
    prior: Optional[aiosqlite.Row], new_content_str: str, now_iso: str
) -> bool:
    """Snapshot if:
      - no prior version exists, OR
      - prior snapshot is >= 120s old, OR
      - content size delta vs prior is >= 500 bytes.
    """
    if prior is None:
        return True

    prior_content = prior["content_json"] or ""
    size_delta = abs(len(new_content_str.encode("utf-8")) - len(prior_content.encode("utf-8")))
    if size_delta >= _SNAPSHOT_SIZE_DELTA_BYTES:
        return True

    try:
        prior_ts = datetime.fromisoformat(prior["saved_at"])
        now_ts = datetime.fromisoformat(now_iso)
        if (now_ts - prior_ts).total_seconds() >= _SNAPSHOT_MIN_INTERVAL_SEC:
            return True
    except (ValueError, TypeError):
        # Malformed timestamp — snapshot defensively.
        return True

    return False


async def update_homework(id: str, updates: dict) -> Optional[dict]:
    existing = await get_homework(id)
    if not existing:
        return None

    fields: list[str] = []
    values: list = []

    if "title" in updates:
        fields.append("title = ?")
        values.append(updates["title"])

    new_content_str: Optional[str] = None
    if "content_json" in updates:
        new_content_str = json.dumps(updates["content_json"], ensure_ascii=False)
        fields.append("content_json = ?")
        values.append(new_content_str)

    if not fields:
        return existing

    now_iso = _now()
    fields.append("updated_at = ?")
    values.append(now_iso)
    values.append(id)

    db = await connect()
    try:
        # Snapshot BEFORE the update when content is changing. This preserves the
        # prior state so even if the write is later corrupted we can roll back.
        if new_content_str is not None:
            prior = await _get_latest_version(db, id)
            # Use the existing row's current content as the snapshot payload —
            # that's the state we're about to overwrite.
            snapshot_payload = existing.get("content_json")
            snapshot_str = (
                json.dumps(snapshot_payload, ensure_ascii=False)
                if snapshot_payload is not None
                else ""
            )
            if _should_snapshot(prior, new_content_str, now_iso):
                await db.execute(
                    "INSERT INTO homework_versions "
                    "(homework_id, content_json, title, saved_at) "
                    "VALUES (?, ?, ?, ?)",
                    (id, snapshot_str, existing.get("title"), now_iso),
                )

        await db.execute(
            f"UPDATE homeworks SET {', '.join(fields)} WHERE id = ?", values
        )
        await db.commit()
    finally:
        await db.close()

    return await get_homework(id)


async def delete_homework(id: str) -> bool:
    """Soft delete — sets deleted_at timestamp. Still returns True on success."""
    db = await connect()
    try:
        cursor = await db.execute(
            "UPDATE homeworks SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL",
            (_now(), id),
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def hard_delete_homework(id: str) -> bool:
    """Permanent deletion. Only callable from an admin route."""
    db = await connect()
    try:
        # Clean up version history first to avoid orphaned rows.
        await db.execute(
            "DELETE FROM homework_versions WHERE homework_id = ?", (id,)
        )
        cursor = await db.execute("DELETE FROM homeworks WHERE id = ?", (id,))
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def restore_homework(id: str) -> bool:
    """Un-soft-delete — clears deleted_at."""
    db = await connect()
    try:
        cursor = await db.execute(
            "UPDATE homeworks SET deleted_at = NULL WHERE id = ? AND deleted_at IS NOT NULL",
            (id,),
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def list_versions(homework_id: str) -> list[dict]:
    db = await connect()
    try:
        cursor = await db.execute(
            "SELECT id, homework_id, title, saved_at, length(content_json) AS size_bytes "
            "FROM homework_versions WHERE homework_id = ? ORDER BY saved_at DESC",
            (homework_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def get_version(version_id: int) -> Optional[dict]:
    db = await connect()
    try:
        cursor = await db.execute(
            "SELECT id, homework_id, content_json, title, saved_at "
            "FROM homework_versions WHERE id = ?",
            (version_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        raw = d.get("content_json")
        d["content_json"] = json.loads(raw) if raw else None
        return d
    finally:
        await db.close()


async def restore_version(version_id: int) -> Optional[dict]:
    """Restore a specific version's content back onto the live homework.
    Creates a new snapshot of the current content before overwriting.
    """
    version = await get_version(version_id)
    if not version:
        return None
    hw_id = version["homework_id"]
    updates: dict = {"content_json": version["content_json"]}
    if version.get("title"):
        updates["title"] = version["title"]
    return await update_homework(hw_id, updates)


async def set_status(id: str, status: str) -> None:
    db = await connect()
    try:
        await db.execute(
            "UPDATE homeworks SET status = ?, updated_at = ? WHERE id = ?",
            (status, _now(), id),
        )
        await db.commit()
    finally:
        await db.close()

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
) -> bool:
    """Insert a pending review item.  Idempotent: if a row with the same
    ``question_id`` + ``student_answer`` already has ``status='pending'``,
    the insert is skipped and ``False`` is returned.  Returns ``True`` when a
    new row was actually inserted.
    """
    db = await connect()
    try:
        # Dedup check: skip insert when an identical pending row already exists.
        cursor = await db.execute(
            "SELECT id FROM review_queue "
            "WHERE question_id = ? AND student_answer = ? AND status = 'pending' "
            "LIMIT 1",
            (question_id, student_answer),
        )
        existing = await cursor.fetchone()
        if existing:
            return False
        await db.execute(
            "INSERT INTO review_queue "
            "(question_id, student_answer, answer_spec_json, ai_response_json, status, created_at) "
            "VALUES (?, ?, ?, ?, 'pending', ?)",
            (
                question_id,
                student_answer,
                json.dumps(answer_spec, ensure_ascii=False),
                json.dumps(ai_response, ensure_ascii=False),
                _now(),
            ),
        )
        await db.commit()
        return True
    finally:
        await db.close()

async def get_review_queue() -> list[dict]:
    db = await connect()
    try:
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
