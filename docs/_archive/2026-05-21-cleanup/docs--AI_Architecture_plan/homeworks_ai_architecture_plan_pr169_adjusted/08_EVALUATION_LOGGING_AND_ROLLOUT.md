# 08 — Evaluation, Logging, Simulation, and Rollout Plan

**Goal:** prevent the repaired AI system from becoming another shiny demo that fails in real student sessions. Build logging, diagnostics, regression tests, synthetic simulations, and safe rollout gates.

---

## 1. Why this is required

The current project has AI features, but the system does not yet have enough observability to answer these questions quickly:

```text
Which model answered?
What exact context did it receive?
Was the question_id present?
Did sanitizer remove the phase content?
Did grading use deterministic checker or LLM judge?
Why did confidence fall below threshold?
Did Boss repeat itself?
Did final feedback match actual attempt logs?
```

Without this, every bug becomes ghost hunting.

---

## 2. Verified current logging/storage

Existing DB tables include:

- `sessions`
- `responses`
- `answer_cache`
- `review_queue`
- `tutor_conversations`
- `tutor_warnings`
- `notebook_captures`

Existing `server/db/tutor_repo.py` stores tutor turns in `tutor_conversations`.

Missing dedicated structures:

- `session_events`
- `phase_attempts`
- `session_metrics`
- `ai_call_logs`
- `boss_sessions`
- `generated_boss_questions`
- prompt evaluation fixtures
- synthetic simulation runner

---

## 3. Logging layers

### Layer 1 — AI call logs

Defined in `06_MODEL_GATEWAY_AND_STRUCTURED_OUTPUTS.md`.

Captures:

```text
task_type
provider
model
prompt_version
latency
input/output size
success/failure
fallback_used
```

### Layer 2 — session events

Defined in `02_SESSION_STATE_AND_CONTEXT_BUILDER.md`.

Captures user/system lifecycle:

```text
session_started
phase_started
student_message_sent
tutor_response_sent
student_answer_submitted
answer_checked
phase_completed
boss_started
boss_question_generated
boss_answer_checked
session_completed
```

### Layer 3 — attempt metrics

Defined in `04_ANSWER_SUBMISSION_AND_GRADING_PLAN.md`.

Captures scoring and misconception data.

### Layer 4 — evaluation outcomes

New table:

```sql
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
    created_at TEXT NOT NULL
);
```

---

## 4. Debug endpoint plan

### File to modify

`server/routes/ai.py`

### Add admin/dev-only endpoints

```text
GET /ai/debug/session/{session_id}/context
GET /ai/debug/session/{session_id}/events
GET /ai/debug/session/{session_id}/ai-calls
GET /ai/debug/session/{session_id}/metrics
GET /ai/debug/boss/{boss_session_id}
```

### Security

These endpoints must be disabled or admin-only in production.

### Why

When tutor fails, developer should see:

```json
{
  "session_id": "s1",
  "current_phase": 3,
  "question_id": "q12",
  "question_text_length": 430,
  "screen_context_raw_length": 2300,
  "screen_context_sanitized_length": 120,
  "chat_history_count": 5,
  "model": "kimi-k2.6"
}
```

This immediately reveals blindfold bugs.

---

## 5. Evaluation fixture structure

### New directory

```text
tests/ai_eval_cases/
```

### Files

```text
live_tutor_context_questions.jsonl
answer_checking_language.jsonl
answer_checking_math.jsonl
boss_generation.jsonl
boss_answer_checking.jsonl
final_report.jsonl
```

### Example JSONL row

```json
{
  "id": "tutor_vocab_according_to_001",
  "task_type": "tutor_chat",
  "input": {
    "session_state": {"phase_index": 2, "question_id": "q4"},
    "current_phase_context": {
      "visible_text": "According to the passage, the boy was late."
    },
    "student_message": "according to nima degani?"
  },
  "expected": {
    "must_include_any": ["ga ko'ra", "bo'yicha"],
    "must_not_include": ["Hey according to"]
  }
}
```

---

## 6. Synthetic simulation runner

### Why

Single-turn evals are not enough. Your tutor and Boss are multi-turn flows. The research-selected DoorDash pattern uses simulation + LLM judge to catch multi-turn failures before users see them.

### New file

`server/services/ai_simulator.py`

### Simulation types

| Simulation | Purpose |
|---|---|
| `student_confused_vocab` | Student asks word/phrase meanings inside English homework. |
| `student_missing_context` | Student says “manabu joyga tushunmadim” and current UI context must carry the meaning. |
| `student_wrong_answer_then_hint` | Tutor should hint, not instantly solve. |
| `boss_adaptive_weak_topic` | Boss should target weak topics and update difficulty. |
| `boss_repetition_guard` | Boss should not repeat the same question. |
| `final_report_accuracy` | Report must match stored attempts. |

### Simulation loop

```text
Load fixture homework/session
  ↓
Simulated student sends message / answer
  ↓
Real backend context builder builds context
  ↓
Real AI gateway responds
  ↓
Judge checks response against rubric
  ↓
Store eval result
```

### Judge schema

```json
{
  "passed": true,
  "score": 0.91,
  "failure_type": null,
  "reason": "Tutor explained the phrase directly in Uzbek and used phase context."
}
```

---

## 7. Quality gates before rollout

### Gate 1 — unit tests

Must pass:

- context builder tests
- answer resolver tests
- grading contract tests
- boss state tests
- prompt variable availability tests

### Gate 2 — single-turn evals

Minimum pass rates:

| Eval set | Pass threshold |
|---|---:|
| Tutor context questions | 95% |
| Language answer checking | 90% |
| Math answer checking | 95% deterministic, 90% AI explanation grading |
| Boss generation | 90% |
| Boss answer checking | 90% |

### Gate 3 — multi-turn simulations

Minimum pass rates:

| Simulation | Pass threshold |
|---|---:|
| Tutor vocabulary help | 95% |
| Tutor wrong answer recovery | 90% |
| Boss adaptive loop | 90% |
| Boss no-repeat | 95% |
| Final report consistency | 95% |

### Gate 4 — canary rollout

Roll out by homework/template type:

```text
5% internal/dev homeworks
  ↓
10% simple English/math homeworks
  ↓
25% generated homeworks
  ↓
100% after no critical regressions
```

---

## 8. Regression dashboard metrics

Track daily/weekly:

```text
Tutor context missing rate
Question resolution failure rate
Screen context sanitized-to-empty rate
Average tutor confidence
Generic fallback rate
AI answer check confidence distribution
Review queue rate
Boss generated question rejection rate
Boss repetition rate
Final report generation failure rate
Average model latency
Provider fallback rate
```

### High-signal alerts

| Metric | Alert if |
|---|---:|
| `question_resolution_failure_rate` | > 3% |
| `screen_context_sanitized_to_empty_rate` | > 5% |
| `generic_fallback_rate` | > 7% |
| `boss_repetition_rate` | > 2% |
| `provider_failure_rate` | > 1% |
| `schema_validation_failure_rate` | > 2% |

---

## 9. Rollout sequence

### Stage 0 — instrumentation only

Add logs and debug endpoints without changing behavior.

### Stage 1 — context builder shadow mode

Build new context packets but keep old tutor behavior. Log differences.

### Stage 2 — new tutor context active

Route Live Tutor through context builder and structured response.

### Stage 3 — answer envelope active

Move runtime answer submission to `/ai/runtime/submit-answer`.

### Stage 4 — dynamic Boss beta

Enable `/ai/boss/start` → generated questions for selected homeworks.

### Stage 5 — final report active

Generate final reports from stored metrics.

### Stage 6 — cleanup legacy

Deprecate old generic runtime paths after all templates migrate.

---

## 10. Bug triage playbook

### If tutor says generic nonsense

Check:

```text
question_id present?
current_phase_context present?
sanitized screen context length?
model resolved?
prompt version?
```

### If answer does not submit

Check:

```text
runtime payload contains session_id/homework_id/phase/question_id?
resolver found trusted target?
which grading branch used?
frontend using old checkAnswer or new submitRuntimeAnswer?
```

### If Boss repeats

Check:

```text
asked_question_ids_json updated?
generation context includes asked questions?
similarity rejection active?
```

### If Boss asks unrelated question

Check:

```text
weak_topics_json correct?
source_phase_ids valid?
question validation rejected off-topic generation?
```

---

## 11. Done definition

This chunk is complete when:

- AI calls, session events, attempts, and Boss events are logged
- debug endpoints show context and resolved models
- single-turn and multi-turn eval fixtures exist
- simulation runner can reproduce the reported bugs
- rollout gates prevent broken prompts/context from reaching users

