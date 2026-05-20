# Homeworks AI Architecture Repair Master Plan

**Project:** `https://github.com/s1gmamale1/Homeworks.git`  
**Branch inspected:** `server`  
**Goal:** rebuild the AI layer so the Live Tutor and AI Boss become homework-aware, phase-aware, adaptive, logged, measurable, and safe.  
**Constraint honored:** this plan does **not** assume missing modules exist. Each recommendation is mapped either to an observed file/function or explicitly marked as a new file/table/endpoint to create.

---

> **PR #169 adjustment:** After inspection of PR #169, provider references must be updated from `server/services/ai_orchestrator.py` to `server/services/ai_orchestrator.py`. PR #169 already adds prompt-bloat read-time sanitization, write-time inline-base64 validation, and synthetic AI-unavailable fallbacks. See [`10_PR169_DELTA_AND_PLAN_ADJUSTMENTS.md`](./10_PR169_DELTA_AND_PLAN_ADJUSTMENTS.md).


## 0. Source Basis

### Repo files verified

| Area | Existing file verified | Why it matters |
|---|---|---|
| Runtime tutor service | `server/services/tutor.py` | Current `check_answer`, `tutor_chat`, `boss_turn`, `boss_plan`, sanitizer, model routing. |
| AI routes | `server/routes/ai.py` | Current request models and endpoints: `/ai/check-answer`, `/ai/boss-turn`, `/ai/tutor/chat`, `/ai/tutor/boss-plan`. |
| Runtime frontend bridge | `server/template/runtime.js` | Current `NETS_AI.checkAnswer`, `bossTurn`, `tutorChat`, event bridge. |
| Provider shim/orchestrator | `server/services/ai_orchestrator.py` | Current Kimi provider facade, fallback walking, input bloat sanitization, model constants, JSON parsing. |
| Kimi provider | `server/services/ai_providers/kimi.py` | Current Kimi defaults and K2.X behavior. |
| DB schema | `server/db/migrations.py` | Current tables: `homeworks`, `sessions`, `responses`, `tutor_conversations`, `review_queue`, `answer_cache`, warnings, notebook captures. |
| Tutor repo | `server/db/tutor_repo.py` | Existing append-only `tutor_conversations` and `build_session_profile`. |
| Prompts | `server/prompts/runtime/*.md` | Current tutor, boss, boss-plan, answer-checker prompts. |

### Research patterns selected for this project

This project should copy the **DoorDash style** more than the Klarna style:

- Use a structured intermediate state instead of stuffing raw logs into the model.
- Run deterministic/cheap checks before LLM calls.
- Build a simulation/evaluation flywheel for multi-turn tutoring and Boss behavior.
- Treat prompts as versioned infra, not random text.
- Track quality, not just automation.

This directly matches the homework use case because your AI is not a generic customer-support bot. It is a **session-specific tutoring agent** with live UI state, student attempts, phase progression, performance metrics, and adaptive assessment.

---

## 1. Current Root Problem

The current AI failures are not mainly because the model is “dumb.” The system is giving the AI an incomplete, inconsistent, sometimes sanitized-to-death context packet.

Current failure mode:

```text
Student screen has homework content
        ↓
Frontend may or may not send question_id / screen_context / student_work_text
        ↓
Backend only resolves question_text if question_id matches content_json
        ↓
Sanitizer may strip useful screen context
        ↓
Tutor receives weak context
        ↓
Tutor replies generically or hallucinates
```

Boss failure mode:

```text
content_json.boss_questions fixed list
        ↓
Boss-plan only reorders/preframes existing questions
        ↓
Boss-turn only grades one fixed question
        ↓
No boss chat history / no adaptive question generation
        ↓
Boss feels static
```

---

## 2. Target Architecture

```text
Student UI
  ↓
Runtime Context Collector
  ↓
Backend AI Runtime API
  ↓
Session State Service
  ├── existing sessions table, extended
  ├── new session_events table
  ├── new phase_attempts table
  └── new session_metrics table
  ↓
Context Builder
  ├── Homework content slice
  ├── Current phase + subphase
  ├── Current active question
  ├── Student current draft/answer
  ├── Previous phase summaries
  ├── Performance metrics
  └── Recent conversation summary
  ↓
AI Gateway / Model Router
  ├── deterministic checker first
  ├── Kimi K2.6 for tutor/boss reasoning
  ├── fallback providers
  └── structured output validation
  ↓
Tutor / Boss / Judge / Final Analyst prompts
  ↓
Response validator
  ↓
State update + event log
  ↓
Frontend UI update
```

---

## 3. Execution Sequence

## Phase 0 — Freeze and Instrument Current Behavior

**Purpose:** prove the exact missing-context path before rewriting.

**Files to touch later:**

- `server/routes/ai.py`
- `server/services/tutor.py`
- `server/template/runtime.js`

**What to add:**

- Debug logging around every AI request.
- `context_debug` object returned only when `AI_DEBUG_CONTEXT=true`.
- Log lengths, not full sensitive content.

**Must capture:**

```text
session_id present?
hw_id present?
phase/subphase present?
question_id present?
question found in content_json?
question_text length
screen_context raw length
screen_context sanitized length
student_work_text length
chat_history count
selected provider/model
response parse status
```

**Success gate:**

You can reproduce the English example failure and see exactly whether `QUESTION_TEXT`, `SCREEN_CONTEXT`, or `STUDENT_ATTEMPT` is empty.

Detailed plan: [`01_REPO_AUDIT_AND_DIAGNOSIS.md`](./01_REPO_AUDIT_AND_DIAGNOSIS.md)

---

## Phase 1 — Build the Session State Foundation

**Purpose:** make the backend own the truth. The AI must never own progress, HP, phase, trials, or correctness.

**Current repo reality:**

- `sessions` table exists but is too thin.
- `responses` table exists but is too thin.
- `tutor_conversations` exists and is useful.
- No dedicated `session_events`, `phase_attempts`, or `session_metrics` table exists.

**What to create:**

- Extend `sessions` or create `homework_session_state`.
- Create append-only `session_events`.
- Create `phase_attempts`.
- Create `session_metrics`.
- Add DB repo helpers.

**Success gate:**

Every student action can be replayed from event logs, and every AI call can be built from current backend state.

Detailed plan: [`02_SESSION_STATE_AND_CONTEXT_BUILDER.md`](./02_SESSION_STATE_AND_CONTEXT_BUILDER.md)

---

## Phase 2 — Build the Context Builder

**Purpose:** replace “random optional payload fields” with one canonical context packet.

**New file recommended:**

```text
server/services/ai_context.py
```

**Responsibilities:**

- Resolve homework by `hw_id`.
- Resolve current phase from backend session state.
- Resolve active question by `question_id` or session state fallback.
- Generate safe question context.
- Attach recent attempts and metrics.
- Attach recent tutor history.
- Produce a compact, typed packet.

**Success gate:**

`tutor_chat`, `boss_question_generate`, `boss_answer`, `final_report` all consume the same context builder style.

Detailed plan: [`02_SESSION_STATE_AND_CONTEXT_BUILDER.md`](./02_SESSION_STATE_AND_CONTEXT_BUILDER.md)

---

## Phase 3 — Repair Live Tutor

**Purpose:** make the tutor know what phase/screen/question the student is talking about.

**Files to update:**

- `server/template/runtime.js`
- `server/routes/ai.py`
- `server/services/tutor.py`
- `server/prompts/runtime/tutor-assistant.md`

**Core changes:**

1. Frontend must always send structured context from the active UI.
2. Backend must reject or recover from missing context.
3. Sanitizer must stop deleting entire content lines when one answer marker appears.
4. Tutor prompt should be shortened and made contract-based.
5. Tutor must answer direct word-definition questions from visible content.

**Success gate:**

If student asks:

```text
"according to" nima degani?
"shu gapga tushunmadim"
"manabu joy nima deyapti?"
```

Tutor references the current visible sentence or asks a precise clarification. It must not reply “Hey according to, how can I help?”

Detailed plan: [`03_LIVE_TUTOR_REPAIR_PLAN.md`](./03_LIVE_TUTOR_REPAIR_PLAN.md)

---

## Phase 4 — Repair Answer Submission and Grading

**Purpose:** make answer handling deterministic, phase-aware, and traceable.

**Files to update:**

- `server/template/runtime.js`
- `server/routes/ai.py`
- `server/services/tutor.py`
- `server/services/answer_checker.py`
- `server/prompts/runtime/answer-checker*.md`

**Core changes:**

1. Replace the generic weak `checkAnswer` payload with a full `AnswerSubmissionEnvelope`.
2. Route phase-specific checkers by phase + required IDs.
3. Deterministic check first.
4. AI judge second only when required.
5. Store every attempt in `phase_attempts` and `session_events`.
6. Replace hard `0.90` confidence logic with action tiers.

**Success gate:**

Every answer submission logs:

```text
phase
subphase
question_id/item_id/step_id
checker_used
correct/score/confidence
feedback
stored event_id
```

Detailed plan: [`04_ANSWER_SUBMISSION_AND_GRADING_PLAN.md`](./04_ANSWER_SUBMISSION_AND_GRADING_PLAN.md)

---

## Phase 5 — Rebuild Boss as a Dynamic Adaptive System

**Purpose:** make Boss AI generate questions live from performance state, not only reorder `content_json.boss_questions`.

**Files to update/create:**

- `server/routes/ai.py`
- `server/services/tutor.py`
- `server/services/ai_context.py` new
- `server/prompts/runtime/boss-question-generator.md` new
- `server/prompts/runtime/boss-answer-judge.md` new or refactor `boss-tutor.md`
- `server/template/runtime.js`

**Current repo reality:**

- `boss_plan` consumes fixed `boss_questions` and requires every ID exactly once.
- `boss_turn` grades a supplied fixed question.
- `boss_turn` does not receive Boss history.

**Target flow:**

```text
POST /api/ai/boss/start
  → backend creates boss_state

POST /api/ai/boss/next-question
  → Context Builder creates performance profile
  → LLM generates new question + rubric + hidden expected answer
  → backend stores generated question

POST /api/ai/boss/answer
  → deterministic/AI judge grades answer
  → backend updates HP/trials/difficulty
  → boss response generated
```

**Success gate:**

Boss asks different questions based on weak topics, avoids repetition, adapts difficulty, and continues until HP/trials/give-up condition is reached.

Detailed plan: [`05_DYNAMIC_BOSS_AI_PLAN.md`](./05_DYNAMIC_BOSS_AI_PLAN.md)

---

## Phase 6 — Repair AI Gateway, Model Routing, and JSON Reliability

**Purpose:** stop silent quality loss from wrong model routing and weak JSON enforcement.

**Files to update:**

- `server/services/ai_orchestrator.py`
- `server/services/ai_providers/kimi.py`
- `server/routes/ai.py`
- `.env.example` if present, otherwise create/update deployment docs

**Current repo reality:**

- `FAST_MODEL` and `PRO_MODEL` are Gemini names in the shim.
- Kimi provider maps them to `KIMI_MODEL_FAST` and `KIMI_MODEL_PRO`.
- Kimi defaults are `moonshot-v1-32k` and `moonshot-v1-128k`.
- `kimi-k2.6` is only the default vision model.
- Kimi K2.X path has special temperature/JSON quirks.
- `generate_json` still depends on JSON mode + cleanup parsing.

**Target:**

- Use K2.6 for Live Tutor, Boss generator, Boss judge, and final analysis.
- Keep cheap models only for simple classification or fallback.
- Add response validator + retry wrapper for providers without native JSON schema.
- Prefer native structured outputs when provider supports it.

**Success gate:**

`/api/ai/status` clearly shows active provider and resolved model IDs. Every JSON call has schema validation and either returns valid typed output or fails visibly.

Detailed plan: [`06_MODEL_GATEWAY_AND_STRUCTURED_OUTPUTS.md`](./06_MODEL_GATEWAY_AND_STRUCTURED_OUTPUTS.md)

---

## Phase 7 — Prompt Rewrite and Prompt Versioning

**Purpose:** prompts must become shorter, modular, versioned, and tied to explicit context contracts.

**Files to update/create:**

- `server/prompts/runtime/tutor-assistant.md`
- `server/prompts/runtime/answer-checker.md`
- `server/prompts/runtime/answer-checker-language.md`
- `server/prompts/runtime/boss-tutor.md`
- `server/prompts/runtime/boss-question-generator.md` new
- `server/prompts/runtime/final-homework-analyst.md` new
- `server/prompts/runtime/*.vX.md` or prompt manifest new

**Success gate:**

Every prompt declares:

```text
role
allowed inputs
trust boundaries
what to do when context is missing
output schema
failure behavior
```

Detailed plan: [`07_PROMPT_REWRITE_AND_CONTRACTS.md`](./07_PROMPT_REWRITE_AND_CONTRACTS.md)

---

## Phase 8 — Add Evaluation, Simulation, and Rollout Gates

**Purpose:** prevent “fixed one bug, broke three flows” chaos.

**Files to create:**

```text
server/tests/ai_eval_cases/
server/tests/ai_eval_runner.py
server/tests/simulated_tutor_conversations.py
```

**Test categories:**

- Tutor context awareness.
- English word-definition questions.
- Uzbek casual speech.
- Missing context fallback.
- Answer grading correctness.
- Boss adaptive question generation.
- Boss no-repeat behavior.
- Prompt injection attempts.

**Success gate:**

No prompt/model/router change ships unless eval pass rate clears threshold.

Detailed plan: [`08_EVALUATION_LOGGING_AND_ROLLOUT.md`](./08_EVALUATION_LOGGING_AND_ROLLOUT.md)

---

## 4. Recommended Implementation Order

| Order | Chunk | Why first/next |
|---:|---|---|
| 1 | Instrumentation | You need proof before cutting wires. |
| 2 | Session state + events | Everything else depends on stable state. |
| 3 | Context Builder | Tutor/Boss both depend on clean context. |
| 4 | Frontend context collector | Backend cannot infer invisible UI without payloads. |
| 5 | Live Tutor repair | Highest user-visible pain. |
| 6 | Answer submission repair | Required for trustworthy metrics. |
| 7 | Model routing + JSON reliability | Prevents quality/parser chaos. |
| 8 | Dynamic Boss | Needs metrics + context + grading first. |
| 9 | Final analyst/report | Needs complete session data. |
| 10 | Eval simulator | Locks quality before bigger experiments. |

---

## 5. Non-Negotiable Rules

1. **Backend owns state.** AI never owns phase, score, HP, trials, correctness, or completion.
2. **Context Builder owns prompt inputs.** No endpoint should hand-roll random prompt payloads after this refactor.
3. **Frontend sends visible state.** `question_id`, `phase`, `subphase`, visible text, active input, and UI state must become normal payload fields.
4. **Deterministic first, AI second.** Do not pay LLMs to compare exact strings or numeric values.
5. **Boss questions are generated/stored server-side.** Do not trust frontend for hidden expected answers.
6. **Structured output is mandatory.** If provider lacks native schema enforcement, validate + retry + fail loud.
7. **Logs before vibes.** Every AI call gets enough metadata to debug.
8. **Eval before deploy.** Prompt changes must pass scripted conversations.

---

## 6. Final Target Behavior

### Live Tutor

- Knows current homework, phase, subphase, active question, visible text, and student draft.
- Answers language/word meaning questions from current screen.
- Asks precise clarification only when context is truly missing.
- Uses performance data to adapt hints.
- Does not leak answers in practice/boss mode.

### Answer Checker

- Handles exact, numeric, multiple choice, semantic, and language-subject answers through clear routing.
- Stores every attempt.
- Produces metrics for weakness detection.

### Boss AI

- Starts after phase completion.
- Reads compressed performance profile.
- Generates adaptive questions live.
- Stores each generated question and hidden rubric server-side.
- Updates HP/trials/difficulty.
- Produces final mastery result.

### Final Report

- Summarizes all phase performance, misconceptions, hint dependence, improvement trend, Boss result, and next recommended practice.

---

## 7. Deliverable Map

1. [`00_MASTER_PLAN.md`](./00_MASTER_PLAN.md) — this index and execution order.
2. [`01_REPO_AUDIT_AND_DIAGNOSIS.md`](./01_REPO_AUDIT_AND_DIAGNOSIS.md) — verified current repo behavior and root causes.
3. [`02_SESSION_STATE_AND_CONTEXT_BUILDER.md`](./02_SESSION_STATE_AND_CONTEXT_BUILDER.md) — state tables, event logs, context packets.
4. [`03_LIVE_TUTOR_REPAIR_PLAN.md`](./03_LIVE_TUTOR_REPAIR_PLAN.md) — frontend/backend/prompt fixes for tutor.
5. [`04_ANSWER_SUBMISSION_AND_GRADING_PLAN.md`](./04_ANSWER_SUBMISSION_AND_GRADING_PLAN.md) — answer flow repair.
6. [`05_DYNAMIC_BOSS_AI_PLAN.md`](./05_DYNAMIC_BOSS_AI_PLAN.md) — real-time adaptive Boss architecture.
7. [`06_MODEL_GATEWAY_AND_STRUCTURED_OUTPUTS.md`](./06_MODEL_GATEWAY_AND_STRUCTURED_OUTPUTS.md) — model routing and JSON reliability.
8. [`07_PROMPT_REWRITE_AND_CONTRACTS.md`](./07_PROMPT_REWRITE_AND_CONTRACTS.md) — prompt contracts and templates.
9. [`08_EVALUATION_LOGGING_AND_ROLLOUT.md`](./08_EVALUATION_LOGGING_AND_ROLLOUT.md) — evals, simulation, rollout.
10. [`09_REFERENCES_AND_REPO_MAP.md`](./09_REFERENCES_AND_REPO_MAP.md) — verified repo map and research pattern references.

