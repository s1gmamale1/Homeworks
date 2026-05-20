# 09 — References and Repo Map

This file maps the plan to verified project files and selected research patterns.

> **Refresh status (2026-05-07):** Updated against `origin/server@38c50b9`. Plans 1, 2, 3, 4, 5, and 6 are merged; Plan 7 (prompt rewrite) and Plan 8 (eval + rollout) are still in flight and intentionally not relied on here. Symbol/file names below were grep-verified in the working tree at refresh time.

---

## 1. Repo files verified

### Backend AI service

```text
server/services/tutor.py
```

Verified responsibilities (post Plans 1–6):

- `_validate_session_id`
- `_fence_untrusted`
- `_sanitize_screen_context`
- `_strip_fence_tags`
- `_validate_phase`
- `_scrub_provider_error`
- `_was_correct_normalized`
- `_model_for_subject`
- `_load_runtime_prompt`
- `_normalize`
- `_is_boss`
- `check_answer`
- `boss_turn`
- `_boss_turn_ai_unavailable` (synthetic-fallback verdict introduced in PR #169)
- `reflection_feedback`
- `_redact_question_for_tutor`, `_format_history_for_prompt`, `_build_tutor_chat_prompt`
- `tutor_chat_v2` (Plan 3 / PR #174 — context-builder–driven path)
- `tutor_chat` (legacy path, retained for backward compatibility)
- `_default_boss_plan`, `_validate_boss_plan`, `boss_plan`
- `tutor_help`
- `process_runtime_answer` (Plan 4 / PR #175 — used by `/ai/runtime/submit-answer`)

Plan references:

- `01_REPO_AUDIT_AND_DIAGNOSIS.md`
- `03_LIVE_TUTOR_REPAIR_PLAN.md`
- `04_ANSWER_SUBMISSION_AND_GRADING_PLAN.md`
- `05_DYNAMIC_BOSS_AI_PLAN.md`

---

### AI routes

```text
server/routes/ai.py
```

Verified responsibilities:

- `GET  /ai/status` (Plan 6 / PR #179 — exposes provider + gateway status)
- `GET  /ai/review-queue`, `POST /ai/review-queue/{id}/decide`
- `POST /ai/answer-spec/preview`
- `POST /ai/runtime/submit-answer` (Plan 4 / PR #175 — canonical answer envelope)
- `POST /ai/check-answer`, `POST /ai/check-answer/finalize`
- `POST /ai/boss-turn`
- `POST /ai/reflection`
- `POST /ai/tutor`
- `POST /ai/tutor/chat` (routes to `tutor_chat_v2` when context-builder packet is available)
- `POST /ai/tutor/boss-plan`
- `GET  /ai/tutor/history`
- Phase-specific `_check_answer_*` handlers (sentence-fill, tile-match, real-life challenge, final-boss, ttt, memory-palace)
- Request models including `RuntimeAnswerSubmitRequest`, `CheckAnswerRequest`, `FinalizeCheckAnswerRequest`, `BossTurnRequest`, `ReflectionRequest`, `PreviewAnswerSpecRequest`, `TutorRequest`, `ReviewDecideRequest`, `TutorChatRequest`, `TutorChatResponse`, `BossPlanRequest`, `BossPlanResponse`
- Plan 1 debug attach helpers: `_attach_check_answer_debug`, `_attach_boss_turn_debug`, `_attach_tutor_chat_route_debug`

Plan references:

- runtime answer endpoint (live)
- new Boss endpoints (now in `ai_plan5.py`, see below)
- debug endpoints / instrumentation (live, see `services/ai_debug.py`)

---

### Boss AI routes (new in Plan 5)

```text
server/routes/ai_plan5.py
```

Verified responsibilities (PR #180):

- `POST /ai/boss/start` → `boss_start`
- `POST /ai/boss/generate-question` → `boss_generate_question`
- `POST /ai/boss/submit-answer` → `boss_submit_answer`
- `POST /ai/boss/state` → `boss_state`
- `POST /ai/boss/give-up` → `boss_give_up`
- Request/response models: `BossStartRequest/Response`, `BossGenerateQuestionRequest/Response`, `BossSubmitAnswerRequest/Response`, `BossStateRequest`, `BossGiveUpRequest`
- Helpers: `_boss_state_to_response`, `_load_asked_questions`, `_record_event`, `_streaks_from_recent_attempts`

Wired in `server/app.py` via `app.include_router(ai_plan5_router, prefix="/api")`.

Plan references:

- `05_DYNAMIC_BOSS_AI_PLAN.md`

---

### Frontend runtime bridge

```text
server/template/runtime.js
```

Verified responsibilities (`window.NETS_AI` surface):

- `checkAnswer`
- `bossTurn`
- `reflectionFeedback`
- `tutor`, `tutorChat`, `tutorHistory`
- `bossPlan`
- Plan 5 dynamic-boss methods: `bossStart`, `bossGenerateQuestion`, `bossSubmitAnswer`, `bossState`, `bossGiveUp`
- `isAvailable`, exposed `_ctx`
- `nets:submit` / `nets:result` event bridge with per-kind `FALLBACK` envelopes

Plan references:

- runtime context collector
- canonical answer envelope (`POST /ai/runtime/submit-answer`)
- new Boss state calls (live)

---

### Provider facade / orchestrator

```text
server/services/ai_orchestrator.py
```

> **Note:** PR #169 renamed the historical `server/services/gemini.py` to `ai_orchestrator.py` and deleted the Vertex / `gemini_api` provider modules. Current preference defaults to Kimi only.

Verified responsibilities:

- Provider order parsing (`_parse_preference`, `_preference_list`, `_active_backend`, `_iter_available_providers`, `_iter_vision_providers`)
- Fast / pro / vision model constants (`FAST_MODEL`, `PRO_MODEL`, `VISION_MODEL` — all sourced from `server/config.py` env defaults)
- Prompt-bloat hardening: `PromptTooLargeError`, `_strip_inline_media`, `_sanitize_payload`, `build_input_section`
- Generation entry points: `generate`, `generate_json`, `generate_vision`
- `health_check`

Plan references:

- `06_MODEL_GATEWAY_AND_STRUCTURED_OUTPUTS.md` (this orchestrator now sits behind the new gateway)

---

### AI Gateway (new in Plan 6)

```text
server/services/ai_gateway.py
server/schemas/ai_contracts.py
server/db/ai_call_logs_repo.py
server/prompts/runtime/input-guardrail.md
```

Verified responsibilities (PR #179):

- `services/ai_gateway.py`: `AITask` enum, `_resolve_model`, `_task_schema`, `_log_call`, `_active_provider_name`, `generate_text`, `generate_structured`, `run_guardrail`, `get_status`
- `schemas/ai_contracts.py` — Pydantic contracts: `TutorResponse`, `AnswerCheckResult`, `BossQuestionGenerated`, `BossAnswerCheckResult`, `FinalReportResult`, `GuardrailResult`, `SimulationJudgeResult`
- `db/ai_call_logs_repo.py` — `add_ai_call_log`, `list_ai_call_logs`
- `prompts/runtime/input-guardrail.md` — guardrail classifier prompt

Plan references:

- `06_MODEL_GATEWAY_AND_STRUCTURED_OUTPUTS.md`

---

### AI debug instrumentation (new in Plan 1)

```text
server/services/ai_debug.py
```

Verified responsibilities (PR #172):

- `enabled()` (env-gated)
- `present`, `text_len`, `_sanitize_value`, `sanitize`
- `with_context_debug` — attaches `__ai_debug` envelopes to selected route responses

Plan references:

- `01_REPO_AUDIT_AND_DIAGNOSIS.md`

---

### Context builder (new in Plan 2, used by Plan 3)

```text
server/services/ai_context.py
```

Verified responsibilities (PR #171, extended in PR #174):

- `TutorContextPacket` dataclass
- `extract_phase_content`
- `summarize_homework_content`
- `_find_question_in_content`
- `_redact_question_for_tutor` (mirrors the answer-leak guard in `tutor.py`)
- `sanitize_screen_context_v2`
- `build_tutor_context` — single async entry that assembles the packet from session + attempts + metrics

Plan references:

- `02_SESSION_STATE_AND_CONTEXT_BUILDER.md`
- `03_LIVE_TUTOR_REPAIR_PLAN.md`

---

### Runtime answer resolver (new in Plan 4)

```text
server/services/runtime_answer_resolver.py
```

Verified responsibilities (PR #175):

- `ResolvedAnswerTarget` Pydantic model
- `resolve_runtime_answer(request)` — locates the canonical question target inside `content_json` and returns `trusted_source_path` for downstream graders

Plan references:

- `04_ANSWER_SUBMISSION_AND_GRADING_PLAN.md`

---

### Dynamic Boss services (new in Plan 5)

```text
server/services/boss_dynamic.py
server/services/boss_context_builder.py
server/db/boss_session_repo.py
```

Verified responsibilities (PR #180):

- `services/boss_dynamic.py`:
  - `calculate_damage`
  - `BossStreaks`, `next_difficulty`
  - `_load_prompt`
  - `GeneratedBossQuestion`, `BossQuestionRejected`, `_validate_generated_question`, `generate_boss_question`
  - `BossAnswerVerdict`, `_verdict_from_raw`, `check_boss_answer`, `_synthetic_verdict`
- `services/boss_context_builder.py`:
  - `BossContext`, `_scrub_dict`, `_truncate`
  - `_phase_summary_from_attempts`, `_aggregate_topics`, `_default_policy`
  - `build_boss_context`
- `db/boss_session_repo.py`:
  - `create_boss_session`, `get_boss_session`, `get_active_boss_session_for`
  - `update_boss_session`, `append_asked_question`
  - row-mapping helper `_row_to_boss_session`

Plan references:

- `05_DYNAMIC_BOSS_AI_PLAN.md`

---

### Kimi provider

```text
server/services/ai_providers/kimi.py
```

Verified defaults (read from `server/config.py`):

```text
KIMI_MODEL_FAST=moonshot-v1-32k
KIMI_MODEL_PRO=moonshot-v1-128k
KIMI_MODEL_VISION=kimi-k2.6
```

`server/services/ai_providers/__init__.py` exposes the registry: `register`, `get_provider`, `select_provider`, `available_providers`.

Plan references:

- AI Gateway model policy (`AITask` → model resolution in `services/ai_gateway.py`)
- `.env` override for Kimi K2.6 vision
- provider capability flags

---

### DB schema

```text
server/db/migrations.py
```

Verified existing tables (post-Plan 6):

- `homeworks`
- `sessions`
- `responses`
- `homework_versions`
- `answer_cache`
- `review_queue`
- `tutor_conversations`
- `tutor_warnings`
- `notebook_captures`
- `taskboard_users`, `taskboard_tasks`
- `session_events` (Plan 2)
- `phase_attempts` (Plan 2)
- `session_metrics` (Plan 2)
- `generated_boss_questions` (Plan 5)
- `boss_sessions` (Plan 5)
- `ai_call_logs` (Plan 6)

Still outstanding (intentionally not yet created — Plan 8 territory):

- `ai_eval_runs`

Plan references:

- `02_SESSION_STATE_AND_CONTEXT_BUILDER.md`
- `05_DYNAMIC_BOSS_AI_PLAN.md`
- `06_MODEL_GATEWAY_AND_STRUCTURED_OUTPUTS.md`
- `08_EVALUATION_LOGGING_AND_ROLLOUT.md`

---

### Session / attempt / event repos (new in Plan 2)

```text
server/db/session_repo.py
server/db/attempts_repo.py
server/db/session_events_repo.py
server/db/session_metrics_repo.py
server/db/boss_repo.py
```

Verified responsibilities (PR #171):

- `session_repo.py`: `get_session`, `create_session`
- `attempts_repo.py`: `add_phase_attempt`, `list_phase_attempts`, `attempts_for_question`
- `session_events_repo.py`: `add_session_event`, `list_session_events`, `latest_event`
- `session_metrics_repo.py`: `upsert_session_metrics`, `get_session_metrics`, `recompute_session_metrics`
- `boss_repo.py`: `create_generated_boss_question`, `get_generated_boss_question`, `mark_boss_question_used`, `list_used_boss_topics`

Plan references:

- `02_SESSION_STATE_AND_CONTEXT_BUILDER.md`

---

### Tutor conversation repo

```text
server/db/tutor_repo.py
```

Verified responsibilities:

- `add_tutor_turn`, `list_tutor_turns`, `count_session_messages`
- `build_session_profile`
- Warning bookkeeping: `add_warning`, `count_warnings_for_hw`, `count_warnings_for_session`, `list_recent_warnings`, `sum_deductions`, `summary_for_tutor`

Plan references:

- re-used by Live Tutor history; event logs and aggregated metrics now live in `session_events_repo` / `session_metrics_repo` rather than duplicating raw chat storage.

---

### Prompts

```text
server/prompts/runtime/tutor-assistant.md
server/prompts/runtime/boss-tutor.md
server/prompts/runtime/tutor-boss-plan.md
server/prompts/runtime/answer-checker.md
server/prompts/runtime/answer-checker-language.md
server/prompts/runtime/answer-checker-math.md          # added by Plan 4 (PR #175)
server/prompts/runtime/answer-checker-boss.md         # added by Plan 4 (PR #175)
server/prompts/runtime/boss-question-generator.md     # added by Plan 5 (PR #180)
server/prompts/runtime/boss-answer-checker.md         # added by Plan 5 (PR #180)
server/prompts/runtime/input-guardrail.md             # added by Plan 6 (PR #179)
server/prompts/runtime/notebook-grader.md
server/prompts/runtime/real-life-challenge-grader.md
server/prompts/runtime/reflection-coach.md
```

Status of the original "verified issues":

- `tutor-assistant.md` — partially refreshed (Plan 3 / PR #174 introduced the Opus-4.7-tone block and Uzbek/Russian idiom locality rules); full schema/tone harmonisation still scheduled for Plan 7.
- `boss-tutor.md` — still requests history that the legacy `boss_turn` path does not provide; Plan 5 routes the new dynamic flow through `boss-question-generator.md` + `boss-answer-checker.md` instead, leaving `boss-tutor.md` for the legacy Boss path.
- `tutor-boss-plan.md` — outstanding (Plan 7 will rewrite to allow generated questions for the dynamic path).
- `answer-checker-language.md` — outstanding; Plan 4 split out `answer-checker-math.md` and `answer-checker-boss.md`, but the language prompt itself still mixes schema and task instructions.

Plan references:

- `07_PROMPT_REWRITE_AND_CONTRACTS.md` (in flight, not merged)

---

## 2. Research patterns used

### DoorDash: simulation + context engineering + guardrails

Pattern used:

```text
structured case state → conversational agent → guardrails → LLM judge → simulation flywheel → production feedback
```

Why it matches Homeworks:

- multi-turn AI behavior
- user can be confused or adversarial
- context must be structured, not raw dumped
- prompt changes need simulation before release

Used in:

- `02_SESSION_STATE_AND_CONTEXT_BUILDER.md` (live: `services/ai_context.py`)
- `03_LIVE_TUTOR_REPAIR_PLAN.md` (live: `tutor_chat_v2` in `services/tutor.py`)
- `08_EVALUATION_LOGGING_AND_ROLLOUT.md` (in flight)

---

### Uber GenAI Gateway: central AI routing

Pattern used:

```text
internal product code → AI gateway → provider adapters → selected model
```

Why it matches Homeworks:

- you need visibility into which model answered
- Kimi/Gemini/Vertex routing must be explicit
- cost/latency/failure logs matter

Used in:

- `06_MODEL_GATEWAY_AND_STRUCTURED_OUTPUTS.md` — live in `services/ai_gateway.py` (`AITask` routing) and persisted via `db/ai_call_logs_repo.py`. Note: Vertex / `gemini_api` adapters were deleted in PR #169; the only registered provider today is Kimi.

---

### Structured Outputs / schema validation

Pattern used:

```text
strict task schema → model response → validation → retry/fallback
```

Why it matches Homeworks:

- grading/Boss/final reports cannot depend on fragile free-form output
- schema validation catches broken outputs before they corrupt state

Used in:

- `04_ANSWER_SUBMISSION_AND_GRADING_PLAN.md` (live: `services/runtime_answer_resolver.py` + `process_runtime_answer`)
- `05_DYNAMIC_BOSS_AI_PLAN.md` (live: `_validate_generated_question`, `BossAnswerVerdict` in `services/boss_dynamic.py`)
- `06_MODEL_GATEWAY_AND_STRUCTURED_OUTPUTS.md` (live: `generate_structured` + `schemas/ai_contracts.py`)
- `07_PROMPT_REWRITE_AND_CONTRACTS.md` (in flight)

---

### Context engineering

Pattern used:

```text
backend-owned context packet > raw transcript dump
```

Why it matches Homeworks:

- current failure was context starvation
- current phase/question is now explicit (`TutorContextPacket`)
- previous phases are summarized via `session_metrics`, not dumped

Used in:

- every implementation chunk (lives in `services/ai_context.py` and `services/boss_context_builder.py`)

---

## 3. Sequence summary

```text
00 Master plan
01 Repo audit                        ✅ merged (#172)
02 Session state + context builder   ✅ merged (#171)
03 Live Tutor repair                 ✅ merged (#174)
04 Answer submission + grading       ✅ merged (#175)
05 Dynamic Boss AI                   ✅ merged (#180)
06 Model gateway + structured        ✅ merged (#179)
07 Prompt rewrite + contracts        ⏳ in flight (feature/prompt-rewrite-plan7)
08 Evaluation + rollout              ⏳ in flight (feat/ai-architecture-plan8)
09 References + repo map             ✅ this doc
```

---

## 4. What is intentionally not assumed

When this plan was originally written, none of the following existed. After Plans 1–6 merged, most have landed; the remaining `Status` column reflects the post-merge state at refresh time.

| Item | Status | Where it lives now |
|---|---|---|
| dedicated `homework_sessions` table | not created | sessions still tracked via `sessions` table; per-session AI state lives in `session_events` + `session_metrics` |
| `session_events` table | ✅ created | `server/db/migrations.py` |
| `phase_attempts` table | ✅ created | `server/db/migrations.py` |
| dynamic generated boss question table | ✅ created | `generated_boss_questions` + `boss_sessions` |
| centralized AI gateway | ✅ created | `server/services/ai_gateway.py` |
| strict JSON schema provider path | ✅ created | `generate_structured` + `server/schemas/ai_contracts.py` |
| final report endpoint | ⏳ pending Plan 8 | — |
| synthetic simulation runner | ⏳ pending Plan 8 | — |
| runtime context collector | ✅ created | `server/services/ai_context.py` (tutor) + `server/services/boss_context_builder.py` (boss) |
| `ai_call_logs` table | ✅ created (Plan 6) | `server/db/migrations.py` |
| `ai_eval_runs` table | ⏳ pending Plan 8 | — |
