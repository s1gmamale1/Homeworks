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
  color       TEXT,
  created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  archived_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_tb_users_position ON taskboard_users(position);

CREATE TABLE IF NOT EXISTS taskboard_tasks (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  title            TEXT NOT NULL,
  description      TEXT NOT NULL DEFAULT '',
  assignee_id      INTEGER REFERENCES taskboard_users(id) ON DELETE SET NULL,
  position         INTEGER NOT NULL DEFAULT 0,
  status           TEXT NOT NULL DEFAULT 'open',
  task_type        TEXT NOT NULL DEFAULT 'general',
  subtask_total    INTEGER NOT NULL DEFAULT 0,
  subtask_done     INTEGER NOT NULL DEFAULT 0,
  attachment_count INTEGER NOT NULL DEFAULT 0,
  cover_url        TEXT,
  created_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  archived_at      TEXT
);
CREATE INDEX IF NOT EXISTS idx_tb_tasks_assignee ON taskboard_tasks(assignee_id);
CREATE INDEX IF NOT EXISTS idx_tb_tasks_position ON taskboard_tasks(position);

CREATE TABLE IF NOT EXISTS session_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  hw_id TEXT NOT NULL,
  phase TEXT,
  subphase TEXT,
  question_id TEXT,
  event_type TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_session_events_session
ON session_events(session_id, hw_id, created_at);

CREATE INDEX IF NOT EXISTS idx_session_events_type
ON session_events(session_id, hw_id, event_type, created_at);

CREATE TABLE IF NOT EXISTS phase_attempts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  hw_id TEXT NOT NULL,
  phase TEXT NOT NULL,
  subphase TEXT,
  question_id TEXT,
  item_id TEXT,
  step_id TEXT,
  attempt_number INTEGER NOT NULL DEFAULT 1,
  student_answer TEXT,
  normalized_answer TEXT,
  answer_spec_json TEXT,
  checker_source TEXT NOT NULL,
  correct INTEGER,
  score REAL,
  confidence REAL,
  feedback TEXT,
  misconception_tags_json TEXT,
  time_ms INTEGER,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_phase_attempts_session
ON phase_attempts(session_id, hw_id, phase, created_at);

CREATE INDEX IF NOT EXISTS idx_phase_attempts_question
ON phase_attempts(session_id, hw_id, question_id, created_at);

CREATE TABLE IF NOT EXISTS session_metrics (
  session_id TEXT NOT NULL,
  hw_id TEXT NOT NULL,
  metrics_json TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (session_id, hw_id)
);

CREATE TABLE IF NOT EXISTS final_reports (
  session_id TEXT NOT NULL,
  hw_id TEXT NOT NULL,
  report_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (session_id, hw_id)
);

CREATE TABLE IF NOT EXISTS generated_boss_questions (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  hw_id TEXT NOT NULL,
  difficulty TEXT NOT NULL,
  topic_tags_json TEXT NOT NULL,
  question_text TEXT NOT NULL,
  expected_answer_json TEXT NOT NULL,
  rubric_json TEXT NOT NULL,
  source_context_json TEXT NOT NULL,
  used INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_generated_boss_session
ON generated_boss_questions(session_id, hw_id, created_at);

CREATE TABLE IF NOT EXISTS boss_sessions (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  homework_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  hp INTEGER NOT NULL DEFAULT 100,
  max_hp INTEGER NOT NULL DEFAULT 100,
  trials_left INTEGER NOT NULL DEFAULT 7,
  current_difficulty TEXT NOT NULL DEFAULT 'medium',
  current_question_id TEXT,
  asked_question_ids_json TEXT NOT NULL DEFAULT '[]',
  weak_topics_json TEXT NOT NULL DEFAULT '[]',
  strong_topics_json TEXT NOT NULL DEFAULT '[]',
  hints_used INTEGER NOT NULL DEFAULT 0,
  correct_count INTEGER NOT NULL DEFAULT 0,
  total_attempts INTEGER NOT NULL DEFAULT 0,
  question_kind TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_boss_sessions_session
ON boss_sessions(session_id, homework_id, status);

CREATE TABLE IF NOT EXISTS ai_call_logs (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    homework_id TEXT,
    task_type TEXT NOT NULL,
    provider TEXT,
    model TEXT,
    prompt_version TEXT,
    input_chars INTEGER,
    output_chars INTEGER,
    latency_ms INTEGER,
    success INTEGER NOT NULL,
    error_code TEXT,
    fallback_used INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ai_calls_session ON ai_call_logs(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_ai_calls_task ON ai_call_logs(task_type, created_at);

CREATE TABLE IF NOT EXISTS ai_eval_runs (
    id TEXT PRIMARY KEY,
    eval_name TEXT NOT NULL,
    task_type TEXT NOT NULL,
    prompt_version TEXT,
    model TEXT,
    total_cases INTEGER NOT NULL,
    passed_cases INTEGER NOT NULL,
    failed_cases INTEGER NOT NULL,
    score REAL,
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ai_eval_runs_name ON ai_eval_runs(eval_name, created_at);
CREATE INDEX IF NOT EXISTS idx_ai_eval_runs_task ON ai_eval_runs(task_type, created_at);

CREATE TABLE IF NOT EXISTS authorship_affirmations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  homework_id TEXT NOT NULL,
  teacher_id TEXT,
  affirmed INTEGER NOT NULL DEFAULT 0,
  note TEXT,
  checkpoints_json TEXT NOT NULL DEFAULT '[]',
  integrity_queue_ids_json TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_affirmations_session
ON authorship_affirmations(session_id, homework_id, created_at);
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
            # Taskboard kanban polish — extra task metadata + per-user accent.
            "ALTER TABLE taskboard_users ADD COLUMN color TEXT",
            "ALTER TABLE taskboard_tasks ADD COLUMN task_type TEXT NOT NULL DEFAULT 'general'",
            "ALTER TABLE taskboard_tasks ADD COLUMN subtask_total INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE taskboard_tasks ADD COLUMN subtask_done INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE taskboard_tasks ADD COLUMN attachment_count INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE taskboard_tasks ADD COLUMN cover_url TEXT",
            "ALTER TABLE sessions ADD COLUMN status TEXT DEFAULT 'active'",
            "ALTER TABLE sessions ADD COLUMN current_phase TEXT",
            "ALTER TABLE sessions ADD COLUMN current_subphase TEXT",
            "ALTER TABLE sessions ADD COLUMN current_question_id TEXT",
            "ALTER TABLE sessions ADD COLUMN tutor_summary_json TEXT",
            "ALTER TABLE sessions ADD COLUMN performance_summary_json TEXT",
            "ALTER TABLE sessions ADD COLUMN boss_state_json TEXT",
            "ALTER TABLE sessions ADD COLUMN updated_at TEXT",
            # Boss-Arena (spec §6) — hint threading + per-session tallies +
            # question shape. Idempotent: re-running on a DB that already has
            # the column is swallowed by the try/except below.
            "ALTER TABLE boss_sessions ADD COLUMN hints_used INTEGER DEFAULT 0",
            "ALTER TABLE boss_sessions ADD COLUMN correct_count INTEGER DEFAULT 0",
            "ALTER TABLE boss_sessions ADD COLUMN total_attempts INTEGER DEFAULT 0",
            "ALTER TABLE boss_sessions ADD COLUMN question_kind TEXT",
        ):
            try:
                await db.execute(migration)
            except Exception:
                # Column already exists — safe to ignore.
                pass
        await db.commit()
    finally:
        await db.close()
