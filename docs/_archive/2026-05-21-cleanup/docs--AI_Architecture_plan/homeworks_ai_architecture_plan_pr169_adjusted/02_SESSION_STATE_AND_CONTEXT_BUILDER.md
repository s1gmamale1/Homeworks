# 02 — Session State and Context Builder Plan

This file defines the backend state model required for homework-specific tutoring, live progress tracking, adaptive Boss behavior, and final AI analysis.

---

## 1. Current Repo Reality

Observed current database schema includes:

```text
homeworks
sessions
responses
homework_versions
answer_cache
review_queue
tutor_conversations
tutor_warnings
notebook_captures
```

Important existing facts:

- `homeworks.content_json` is the stable homework source.
- `sessions` exists but has only broad fields.
- `responses` exists but is too thin for AI analytics.
- `tutor_conversations` already stores chat turns per `(session_id, hw_id)`.
- `build_session_profile(session_id, hw_id)` exists but is only a raw truncated chat dump.

Therefore, do **not** create an entirely separate duplicate session system without checking migrations. Extend the existing structure where sensible.

---

## 2. Target State Model

## 2.1 Extend `sessions`

**Where:** `server/db/migrations.py`

Add nullable columns to existing `sessions` table:

```sql
ALTER TABLE sessions ADD COLUMN status TEXT DEFAULT 'active';
ALTER TABLE sessions ADD COLUMN current_phase TEXT;
ALTER TABLE sessions ADD COLUMN current_subphase TEXT;
ALTER TABLE sessions ADD COLUMN current_question_id TEXT;
ALTER TABLE sessions ADD COLUMN tutor_summary_json TEXT;
ALTER TABLE sessions ADD COLUMN performance_summary_json TEXT;
ALTER TABLE sessions ADD COLUMN boss_state_json TEXT;
ALTER TABLE sessions ADD COLUMN updated_at TEXT;
```

### Why extend instead of replace

`sessions` already exists and references `homework_id`. Extending it avoids inventing a parallel table that the rest of the app does not know about.

---

## 2.2 Create `session_events`

**Where:** `server/db/migrations.py`

```sql
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
```

### Event examples

```text
session_started
phase_started
screen_context_updated
tutor_message_sent
tutor_message_received
answer_submitted
answer_checked
phase_completed
boss_started
boss_question_generated
boss_answer_submitted
boss_hp_updated
boss_completed
final_report_generated
```

### Why append-only

Append-only events let you replay student behavior, debug AI failures, and generate eval cases later. This follows the same production principle as support-chat systems that mine failure transcripts into evaluation scenarios.

---

## 2.3 Create `phase_attempts`

**Where:** `server/db/migrations.py`

```sql
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
```

### Checker source enum

```text
deterministic
ai_judge
ai_unsure
phase_adapter
manual_review
boss_judge
```

---

## 2.4 Create `session_metrics`

**Where:** `server/db/migrations.py`

```sql
CREATE TABLE IF NOT EXISTS session_metrics (
  session_id TEXT NOT NULL,
  hw_id TEXT NOT NULL,
  metrics_json TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (session_id, hw_id)
);
```

### Example `metrics_json`

```json
{
  "accuracy": 0.72,
  "correct_count": 18,
  "incorrect_count": 7,
  "partial_count": 3,
  "hint_count": 4,
  "avg_attempts": 1.8,
  "avg_time_ms": 42000,
  "weak_topics": ["sign_errors", "word_meaning", "factoring"],
  "strong_topics": ["basic_substitution", "main_idea"],
  "language_confusion_terms": ["according to", "concerning"],
  "mastery_score": 0.68,
  "boss_readiness_score": 0.61
}
```

---

## 2.5 Create `generated_boss_questions`

**Where:** `server/db/migrations.py`

```sql
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
```

### Security rule

Never send `expected_answer_json` to the frontend. The frontend only receives:

```json
{
  "question_id": "generated_boss_q_001",
  "question_text": "...",
  "difficulty": "medium",
  "topic_tags": ["factoring"],
  "boss_line": "..."
}
```

---

## 3. New DB Repo Helpers

## 3.1 Create `server/db/session_events_repo.py`

Functions:

```python
async def add_session_event(session_id, hw_id, event_type, payload, phase=None, subphase=None, question_id=None) -> int
async def list_session_events(session_id, hw_id, limit=100, event_types=None) -> list[dict]
async def latest_event(session_id, hw_id, event_type) -> Optional[dict]
```

## 3.2 Create `server/db/attempts_repo.py`

Functions:

```python
async def add_phase_attempt(...) -> int
async def list_phase_attempts(session_id, hw_id, phase=None, limit=100) -> list[dict]
async def attempts_for_question(session_id, hw_id, question_id) -> list[dict]
```

## 3.3 Create `server/db/session_metrics_repo.py`

Functions:

```python
async def recompute_session_metrics(session_id, hw_id) -> dict
async def get_session_metrics(session_id, hw_id) -> dict
async def upsert_session_metrics(session_id, hw_id, metrics) -> None
```

## 3.4 Create `server/db/boss_repo.py`

Functions:

```python
async def create_generated_boss_question(...)
async def get_generated_boss_question(question_id, session_id, hw_id)
async def mark_boss_question_used(question_id, session_id, hw_id)
async def list_used_boss_topics(session_id, hw_id)
```

---

## 4. Context Builder

## 4.1 New file

```text
server/services/ai_context.py
```

## 4.2 Purpose

The Context Builder becomes the single backend authority for what the AI receives.

Every AI call should stop manually assembling random payloads in route handlers or tutor service functions.

---

## 4.3 Context packet shape

```python
@dataclass
class TutorContextPacket:
    session_id: str
    hw_id: str
    phase: str
    subphase: str | None
    current_question_id: str | None
    subject: str
    grade: int
    homework_title: str
    homework_summary: str
    current_phase_content: dict
    current_question_text: str
    current_question_context: dict
    visible_screen_text: str
    student_work_text: str
    recent_chat_history: list[dict]
    recent_attempts: list[dict]
    metrics: dict
    warnings_summary: str
    missing_context_flags: list[str]
```

---

## 4.4 Main builder function

```python
async def build_tutor_context(
    *,
    session_id: str,
    hw_id: str,
    phase: str | None,
    subphase: str | None,
    question_id: str | None,
    screen_context: str | None,
    student_work_text: str | None,
) -> TutorContextPacket:
    ...
```

### Resolution order

1. Validate `session_id`.
2. Load homework by `hw_id` using existing `db.get_homework`.
3. Load session row.
4. Determine phase:
   - request phase if present and valid
   - else `sessions.current_phase`
   - else fallback `preview`
5. Determine question ID:
   - request `question_id`
   - else `sessions.current_question_id`
   - else `None`
6. Find question inside `content_json` using existing `_find_question_in_content` logic moved out of route.
7. Build safe question context using `_redact_question_for_tutor` logic moved into context builder.
8. Clean screen context.
9. Attach recent attempts and metrics.
10. Return typed packet.

---

## 4.5 Missing context flags

The builder should not silently proceed when context is weak. It should set flags:

```text
missing_hw
missing_session
missing_phase
missing_question_id
question_not_found
empty_screen_context
empty_student_work
empty_metrics
```

The tutor prompt should receive these flags. The model should then either answer based on known content or ask a precise clarification.

---

## 4.6 Current phase content slicing

Do not pass all `content_json` into every AI call.

Create content slicing helpers:

```python
def extract_phase_content(content_json: dict, subphase: str | None) -> dict

def summarize_homework_content(content_json: dict) -> dict
```

### Example slices

| Subphase | Include |
|---|---|
| `preview` | current panel/page text, related title, lesson goals. |
| `memory-sprint` | current flashcard/question stem/options without answer. |
| `sentence-fill` | current sentence/passages, blank index, visible choices without answer. |
| `tile-match` | visible left/right tiles without matched answer key. |
| `real-life-challenge` | current scenario step, prompt, visible options. |
| `final-boss` | boss state, generated/current question, no hidden expected answer. |
| `reflection` | session summary and performance metrics. |

---

## 5. Context Compression Rules

## 5.1 Feed full detail only for current item

Give the AI:

```text
current phase full visible content
current question full visible content
current draft answer
```

Do not give:

```text
all 9 phases full JSON
every previous raw transcript
all expected answers
full DOM HTML
```

## 5.2 Summarize previous phases

After each phase, generate/store:

```json
{
  "phase": "sentence-fill",
  "score": 0.72,
  "attempts": 5,
  "hints_used": 2,
  "weak_topics": ["collocation", "word order"],
  "strong_topics": ["meaning recognition"],
  "tutor_note": "Student understands meaning but struggles with target grammar form."
}
```

This can be deterministic at first. AI summarization can be added later.

---

## 6. Backend State Update Flow

## 6.1 When homework starts

Endpoint to add:

```text
POST /api/homeworks/{hw_id}/start-session
```

Actions:

1. Create or validate `sessions` row.
2. Set status `active`.
3. Set current phase/subphase.
4. Add `session_started` event.
5. Initialize metrics.

## 6.2 When phase changes

Endpoint to add or standardize:

```text
POST /api/homeworks/{hw_id}/sessions/{session_id}/phase
```

Payload:

```json
{
  "phase": "practice",
  "subphase": "sentence-fill",
  "question_id": "sf_1"
}
```

Actions:

1. Update `sessions.current_phase`, `current_subphase`, `current_question_id`.
2. Add `phase_started` or `active_question_changed` event.

## 6.3 When answer is checked

Actions:

1. Add `answer_submitted` event.
2. Run checker.
3. Add `phase_attempts` row.
4. Add `answer_checked` event.
5. Recompute metrics.
6. Update session summary fields.

## 6.4 When tutor replies

Actions:

1. Existing `tutor_conversations` still stores chat turns.
2. Also add `tutor_message_sent` and `tutor_message_received` session events.
3. Optionally update `tutor_summary_json` every N turns.

---

## 7. Session Metrics Formula

## 7.1 Initial formula

```text
mastery_score =
  accuracy_score * 0.45
+ independence_score * 0.20
+ improvement_score * 0.20
+ speed_score * 0.05
+ boss_readiness_modifier * 0.10
```

### Components

```text
accuracy_score = correct + partial credit average
independence_score = lower hints + lower retries
improvement_score = later attempts better than earlier attempts
speed_score = reasonable time, not speedrun punishment
boss_readiness_modifier = recent phase performance on core goals
```

## 7.2 Weak topic extraction

Use source priority:

1. `misconception_tags_json` from AI judge.
2. `answer_spec.tags` if present.
3. question tags from content JSON.
4. fallback topic by subphase.

---

## 8. Integration Points

## 8.1 `routes/ai.py`

Move repeated homework/question extraction logic into `ai_context.py`.

Current helpers to relocate or reuse:

```text
_find_question_in_content
_extract_boss_questions
```

## 8.2 `services/tutor.py`

Change functions to accept context packets instead of loose fields:

```python
async def tutor_chat(context: TutorContextPacket, message: str) -> dict
async def generate_boss_question(context: TutorContextPacket) -> dict
async def grade_boss_answer(context: TutorContextPacket, answer: str) -> dict
```

Keep old signatures temporarily as wrappers for backward compatibility.

## 8.3 `runtime.js`

Send structured context envelope instead of loose optional fields.

---

## 9. Success Criteria

The Context Builder phase is complete when:

- Every tutor AI call includes `context_packet_version`.
- Logs show current phase/subphase/question resolution.
- Tutor can answer visible-content questions.
- Boss can access performance metrics.
- Final analyst can read phase summaries and attempts.
- No endpoint directly builds large ad-hoc prompt payloads without using context builder.

---

## 10. Migration Safety

Do migrations additively.

Do not drop current tables:

```text
sessions
responses
tutor_conversations
review_queue
answer_cache
```

Keep old endpoints temporarily:

```text
/api/ai/check-answer
/api/ai/boss-turn
/api/ai/tutor/chat
```

But route new runtime calls through v2 payloads.

Suggested compatibility period:

```text
v1 endpoints remain for old generated homework HTML
v2 endpoints used by new runtime bridge
add deprecation logs when v1 payload lacks required context
```

