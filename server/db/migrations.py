from .connection import connect, apply_pragmas


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

CREATE TABLE IF NOT EXISTS taskboard_users (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  name        TEXT NOT NULL,
  position    INTEGER NOT NULL DEFAULT 0,
  created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  archived_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_tb_users_position ON taskboard_users(position);

CREATE TABLE IF NOT EXISTS taskboard_tasks (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  title       TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  assignee_id INTEGER REFERENCES taskboard_users(id) ON DELETE SET NULL,
  position    INTEGER NOT NULL DEFAULT 0,
  status      TEXT NOT NULL DEFAULT 'open',
  created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  archived_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_tb_tasks_assignee ON taskboard_tasks(assignee_id);
CREATE INDEX IF NOT EXISTS idx_tb_tasks_position ON taskboard_tasks(position);
"""


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
