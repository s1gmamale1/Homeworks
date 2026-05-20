# 10 — PR #169 Delta and Plan Adjustments

**PR inspected:** `https://github.com/s1gmamale1/Homeworks/pull/169`
**PR title:** `fix(ai): grading bloat hardening + Vertex/Gemini provider cleanup`
**PR state (as of refresh):** **MERGED** 2026-05-06 (commit `a1831fe`).
**Plan impact:** partial adjustment. The core architecture plan still stands, but the model/provider and prompt-bloat parts must be updated.

> **Refresh note (2026-05-07).** This document was first written while PR #169 was still open. Since then PR #169 itself merged (2026-05-06), and Plans **1 (#172), 2 (#171), 3 (#174), 4 (#175), 5 (#180), 6 (#179)** have all merged into `server`. **Plan 7 (Prompt Rewrite & Contracts)** is currently in-flight on the `feature/prompt-rewrite-plan7` branch and not yet merged. Each section below now carries an `[absorbed]` / `[superseded by Plan N]` / `[still valid]` tag reflecting the post-merge reality. A consolidated **State as of 2026-05-07** section appears at the bottom.

---

## 0. Status note

PR #169 has merged. The PR-branch state is now the new server baseline, and several follow-on plans have built on top of it.

---

## 1. What PR #169 changes

## 1.1 Provider cleanup  `[absorbed; verified on origin/server@38c50b9]`

### Changed

- Deletes old Vertex AI and Gemini API provider modules.
- Renames `server/services/gemini.py` to `server/services/ai_orchestrator.py`.
- Removes old `as gemini` aliases.
- Sets Kimi as the only configured provider in `.env.example`.
- Keeps `AI_BACKEND_PREFERENCE`, but effectively defaults to `kimi`.
- Updates docs from Gemini/Vertex wording to Kimi/Moonshot wording.

### Verification (2026-05-07)

- `server/services/ai_providers/` contains only `__init__.py`, `base.py`, `kimi.py`. `vertex.py` and `gemini_api.py` are gone.
- `server/services/gemini.py` no longer exists; the orchestrator file is `server/services/ai_orchestrator.py`.
- `.env.example` line 3: `AI_BACKEND_PREFERENCE=kimi`. Only `KIMI_*` env keys are configured.
- `server/config.py` defaults: `KIMI_MODEL_FAST=moonshot-v1-32k`, `KIMI_MODEL_PRO=moonshot-v1-128k`, `KIMI_MODEL_VISION=kimi-k2.6`.
- One legacy `as gemini` style alias survives at the module-level `__getattr__` in `ai_orchestrator.py` for `ACTIVE_BACKEND` lookup compatibility — intentional and harmless.

### Plan impact

The previous plan references `server/services/gemini.py`. That is outdated after this PR.

Replace all references:

```text
server/services/gemini.py
```

with:

```text
server/services/ai_orchestrator.py
```

Do **not** re-create `gemini.py`.

---

## 1.2 Prompt bloat read-time defense  `[absorbed by PR #169; reused by Plan 6 (#179)]`

### Changed

PR #169 adds a centralized helper:

```python
ai_orchestrator.build_input_section(payload, max_chars=50000)
```

It:

- strips inline `<img src="data:...">`
- strips full `<svg>...</svg>` blocks
- strips bare `data:*/*;base64,...` URLs
- truncates individual string fields
- caps serialized prompt payload size
- raises `PromptTooLargeError` when too large

### Verification (2026-05-07)

`build_input_section` lives in `server/services/ai_orchestrator.py:219`. Callers confirmed at:

- `server/services/tutor.py` (tutor + grading paths)
- `server/services/boss_dynamic.py` (Plan 5)
- `server/services/boss_context_builder.py` (Plan 5)
- `server/routes/ai.py` and `server/routes/ai_plan5.py` (boss endpoints)

### Plan impact (refreshed)

This partially completes the old plan's "prompt input sanitization / bloat guard" concern.

Do **not** duplicate this with a second sanitizer in `ai_gateway.py`. Plan 6 followed this rule — `ai_gateway.py` calls `ai_orchestrator.generate_*` and inherits the orchestrator-level sanitization.

Forward guidance unchanged:

- reuse `build_input_section` inside future gateway/context-builder calls
- keep it canonical inside `ai_orchestrator.py` (Plan 2's `ai_context.py` already calls into the orchestrator path rather than reimplementing it)
- add tests for legitimate web-dev/CSS lessons that mention data URIs, because the validator may false-positive on literal `data:image/png;base64,X` examples (still open work; not yet covered by Plans 1–6)

---

## 1.3 AI call fallback hardening  `[absorbed; extended by Plan 5]`

### Changed

PR #169 wraps several AI call sites so provider failure no longer causes browser-facing 500s. Some functions now return synthetic fallback objects:

- `check_answer`
- `boss_turn`
- `reflection_feedback`
- `tutor_help`
- `boss_plan`
- some route-level reasoning checks

### Verification (2026-05-07)

`ai_unavailable: true` markers are present in `server/routes/ai.py`, `server/routes/ai_plan5.py`, `server/services/boss_dynamic.py`. Plan 5 (#180) added a synthetic-fallback path to `check_boss_answer` mirroring this pattern.

### Plan impact

This improves reliability, but it does **not** solve intelligence/context problems.

Keep the master plan's instrumentation requirement, but adjust it:

- log when synthetic fallback is used  `[absorbed by Plan 1 (#172) — ai_debug.py + nets.ai.context channel]`
- include `ai_unavailable: true` in event logs  `[absorbed]`
- do not treat synthetic fallback as a successful AI answer in analytics  `[absorbed by Plan 6 (#179) — ai_call_logs_repo.add_ai_call_log records success/fallback flags]`

---

## 1.4 Write-time content bloat validator  `[absorbed; documentation follow-ups still open]`

### Changed

PR #169 adds `_check_no_inline_bloat` in `server/routes/homework.py`.

It rejects:

- string fields over 200KB
- inline base64 `data:*/*;base64,` URLs

It is wired into:

- POST `/api/homeworks`
- PUT `/api/homeworks/{id}`
- PATCH `/api/homeworks/{id}/content`

PATCH validates only the incoming patch, not the merged legacy content.

### Verification (2026-05-07)

`grep _check_no_inline_bloat server/` matches `server/routes/homework.py` only. Wiring intact.

### Plan impact (refreshed)

This is good and should stay.

Update the plan:

- remove "add write-time bloat validator" as future work  `[absorbed]`
- add "document validator error codes in `docs/API.md`" as a small follow-up  `[still open]`
- add "switch builder autosave from full PUT to PATCH" if legacy bloated rows still exist, because full PUT can now reject old bloated content  `[still open]`

---

## 1.5 Kimi timeout change  `[absorbed]`

### Changed

Kimi text timeout changed from 60 seconds to 15 seconds for faster failure and fallback.

### Plan impact

This is fine for interactive UX, but only if fallback is clearly logged.

Dynamic Boss generation may need different timeout policy:

```text
Tutor chat: 15s max
Answer check: 15s max
Boss persona line: 15s max
Boss question generation: 20-30s acceptable if async/pregenerated at boss-start
Final report: 30-60s acceptable if async
Vision/notebook grading: separate longer timeout
```

> **Plan 5 follow-through:** Plan 5 (#180) generates one boss question per turn server-side (no async pregeneration), so the 15s timeout currently bounds boss generation too. Async pregeneration remains an optimization to revisit; not a regression.

---

# 2. What PR #169 does NOT fix

## 2.1 It does not make Live Tutor phase-aware  `[superseded by Plan 3 (#174)]`

The tutor still depends on `question_id`, `screen_context`, `student_work_text`, `subphase`, and homework metadata being correctly supplied.

The context-starvation problem remains.

Keep these plan chunks unchanged:

- `02_SESSION_STATE_AND_CONTEXT_BUILDER.md`  `[absorbed by Plan 2 (#171) — sessions table extended, session_events / phase_attempts / session_metrics / generated_boss_questions tables added, ai_context.TutorContextPacket landed]`
- `03_LIVE_TUTOR_REPAIR_PLAN.md`  `[absorbed by Plan 3 (#174) — tutor_chat_v2 + build_tutor_context wired, runtime.js context collector added]`
- runtime context collector changes  `[absorbed by Plan 3 — collectRuntimeContext + extractVisibleText in runtime.js]`
- backend context packet contract  `[absorbed by Plan 2 + 3]`

The original "context starvation" concern is now structurally resolved at the data-flow level. Quality work (tightening which DOM elements are visible, ensuring screen_context lengths cap correctly) is ongoing in Plan 7.

---

## 2.2 It does not make Boss dynamic  `[superseded by Plan 5 (#180)]`

The original PR #169 description said:

```text
boss_plan → plan/order fixed boss_questions
boss_turn → grade/respond to one provided boss_question
```

PR #169 made Boss grading more reliable when the LLM fails, but did not create:

- dynamic question generation
- boss state
- generated hidden rubric storage
- adaptive difficulty
- no-repeat question memory
- performance-driven topic targeting

`05_DYNAMIC_BOSS_AI_PLAN.md` was the planned response — `[absorbed by Plan 5 (#180)]`. Net new in `server`:

- `boss_sessions` table (HP / trials / current_difficulty / asked queue / weak+strong topic snapshots)
- `server/services/boss_dynamic.py` — `calculate_damage`, `next_difficulty`, `generate_boss_question` + validator, `check_boss_answer`
- `server/services/boss_context_builder.py` — answer-key-scrubbed `BossContext`
- `server/routes/ai_plan5.py` — `/ai/boss/start`, `/generate-question`, `/submit-answer`, `/state`, `/give-up`
- 17 new tests in `tests/test_plan5_dynamic_boss.py`

The legacy `/api/ai/boss-turn` flow remains for older homework HTML.

---

## 2.3 It does not remove the 0.90 confidence cliff  `[superseded by Plan 4 (#175)]`

`check_answer` originally accepted AI output only if `confidence >= 0.90`. Below that, practice mode became `ai_unsure` / incorrect; boss had special handling.

Plan 4 (#175) introduced tiered fallbacks via `process_runtime_answer` in `tutor.py`:

```text
>= 0.90  → accept
0.75–0.89 → medium / partial credit
< 0.60   → review queue
```

The exact thresholds match the planned tiers approximately (medium tier is 0.75 not 0.70, review tier is 0.60 not 0.45). The structural shape is in place; tier-cutoff tuning is part of Plan 8 evaluation work.

---

## 2.4 It does not give real structured outputs  `[absorbed by Plan 6 (#179)]`

Pre-Plan-6 `ai_orchestrator.generate_json` still:

- appended schema text to the prompt
- asked for JSON mode
- parsed JSON
- stripped markdown fences if needed

Plan 6 (`06_MODEL_GATEWAY_AND_STRUCTURED_OUTPUTS.md`) shipped as PR #179. Concretely:

- `server/services/ai_gateway.py` — `AITask` enum + `TASK_MODEL_POLICY` + `generate_text` + `generate_structured` (Pydantic-validated, one repair retry) + `run_guardrail` + `get_status`.
- `server/schemas/ai_contracts.py` — `TutorResponse`, `AnswerCheckResult`, `BossQuestionGenerated`, `BossAnswerCheckResult`, `FinalReportResult`, `GuardrailResult`, `SimulationJudgeResult`.
- `server/db/ai_call_logs_repo.py` — append-only telemetry (model, latency, success, fallback, error code) wired into the gateway.
- `server/prompts/runtime/input-guardrail.md` — safety classifier prompt.
- 15 new tests in `tests/test_ai_gateway.py`.

The gateway sits **on top of** `ai_orchestrator.py` rather than replacing it, exactly as this delta document recommended.

---

## 2.5 It does not switch text tasks to Kimi K2.6  `[partial — vision switched, text still on moonshot-v1]`

PR #169 explicitly defaulted text tasks to:

```text
KIMI_MODEL_FAST=moonshot-v1-32k
KIMI_MODEL_PRO=moonshot-v1-128k
```

Post Plan 6, these are still the defaults in `server/config.py` and `.env.example`. Vision currently defaults to `KIMI_MODEL_VISION=kimi-k2.6` (verified at `server/config.py:26` and `server/services/ai_providers/kimi.py:53`).

⚠️ **Config drift from memory-locked invariant.** The user's [Always use Kimi K2.6 for vision] memory rule (2026-05-01) specifies the default should be the explicit preview model ID `kimi-k2.6-preview` (discoverable via `GET /v1/models`). The current code default `kimi-k2.6` does not include the `-preview` suffix — this is config drift, not an architectural decision. Resolution belongs in a separate config-fix PR; out of Plan 10's scope.

```env
KIMI_MODEL_FAST=kimi-k2.6              # not the default; override per .env
KIMI_MODEL_PRO=kimi-k2.6               # not the default; override per .env
KIMI_MODEL_VISION=kimi-k2.6            # current default — invariant says kimi-k2.6-preview
```

This is now an environment/config decision, not a legacy Gemini mapping issue. Switching text tasks to K2.6 remains a deferred env-config change with no code dependency.

---

# 3. Adjusted implementation sequence after PR #169

## Before PR #169

```text
1. Instrumentation
2. Session state/events
3. Context Builder
4. Tutor repair
5. Answer submission repair
6. Gateway/model routing cleanup
7. Dynamic Boss
8. Prompt contracts
9. Eval simulator
```

## After PR #169 (and post Plans 1–6)

```text
1. Merge/rebase plan references from gemini.py → ai_orchestrator.py    [absorbed]
2. Add AI-context instrumentation around the new bloat/fallback paths  [absorbed by Plan 1 (#172)]
3. Build session_events / phase_attempts / session_metrics             [absorbed by Plan 2 (#171)]
4. Build Context Builder using build_input_section as sanitizer/cap    [absorbed by Plan 2 (#171) + Plan 3 (#174)]
5. Fix frontend context collector and tutor_chat payload completeness  [absorbed by Plan 3 (#174)]
6. Repair Live Tutor prompt contract and missing-context behavior      [absorbed by Plan 3 (#174); contract polish in Plan 7 (in-flight)]
7. Repair answer submission envelope and confidence tiers              [absorbed by Plan 4 (#175)]
8. Add real task-based AI Gateway wrapper around ai_orchestrator.py    [absorbed by Plan 6 (#179)]
9. Configure K2.6 for tutor/boss tasks if desired                      [open — env config, no code change required]
10. Rebuild Dynamic Boss                                               [absorbed by Plan 5 (#180)]
11. Add final report analyst                                           [open — FinalReportResult schema exists, route/UI not yet wired]
12. Add synthetic eval/simulation suite                                [partial — SimulationJudgeResult schema in place; harness deferred]
```

---

# 4. File-specific plan edits

## 4.1 `00_MASTER_PLAN.md`  `[absorbed]`

### Change

Replace:

```text
Provider shim: server/services/gemini.py
```

with:

```text
Provider shim/orchestrator: server/services/ai_orchestrator.py
```

`00_MASTER_PLAN_PR169_ADJUSTED.md` already carries this edit.

### Add

PR #169 already provides:

- read-time bloat sanitizer
- write-time inline base64 validator
- synthetic fallback for LLM failures
- Kimi-only provider cleanup

---

## 4.2 `01_REPO_AUDIT_AND_DIAGNOSIS.md`  `[absorbed]`

### Update verified state (2026-05-07)

`gemini.py` is gone. The provider/orchestrator layer is now:

```text
server/services/ai_orchestrator.py     # provider facade + sanitizer
server/services/ai_gateway.py          # task-typed gateway (Plan 6)
server/services/ai_context.py          # tutor context packet (Plan 2 + 3)
server/services/ai_debug.py            # context_debug instrumentation (Plan 1)
server/services/ai_providers/__init__.py
server/services/ai_providers/base.py
server/services/ai_providers/kimi.py
```

### Keep root causes

Status, refreshed:

- tutor context starvation  `[absorbed by Plan 2 + 3]`
- sanitizer/context loss risk  `[mitigated — sanitize_screen_context_v2 in ai_context.py preserves answer-bearing content boundaries]`
- static Boss  `[absorbed by Plan 5]`
- Boss no history  `[absorbed by Plan 5 — boss_sessions.asked queue]`
- weak generic answer envelope  `[absorbed by Plan 4]`
- confidence cliff  `[absorbed by Plan 4 — tier thresholds 0.90 / 0.75 / 0.60]`
- K2.6 not default for text  `[still open — env-only change]`

---

## 4.3 `02_SESSION_STATE_AND_CONTEXT_BUILDER.md`  `[absorbed by Plan 2 (#171)]`

### No major change

Still needed at the design level; implementation has landed.

### Add integration point

Context Builder calls `ai_orchestrator.build_input_section` (or its sanitizer helpers) inside the prompt-assembly path rather than reinventing payload sanitization. Confirmed in `server/services/ai_context.py`.

---

## 4.4 `03_LIVE_TUTOR_REPAIR_PLAN.md`  `[absorbed by Plan 3 (#174)]`

### No major change

Implementation has landed: `tutor_chat_v2`, `build_tutor_context`, runtime context collector.

### Add condition

The 60K full-prompt cap in `tutor_chat` means the frontend context collector must send **structured compact visible text**, not raw DOM blobs. `extractVisibleText()` in `runtime.js` already strips answer-bearing elements; further trimming is part of Plan 7's prompt contract.

---

## 4.5 `04_ANSWER_SUBMISSION_AND_GRADING_PLAN.md`  `[absorbed by Plan 4 (#175)]`

### Keep

`AnswerSubmissionEnvelope` shape was needed. `RuntimeAnswerSubmitRequest` in `routes/ai.py` plus `runtime_answer_resolver.py` cover it. `process_runtime_answer` in `tutor.py` is the unified pipeline.

### Add (verified)

PR #169 removed legacy `question_id.startswith("boss")` behavior and now determines boss mode by explicit `phase == "boss"` (verified at `server/services/tutor.py:248`). This strengthens the plan: every phase adapter must send explicit `phase`. Plan 4 honours this in `RuntimeAnswerSubmitRequest`.

---

## 4.6 `05_DYNAMIC_BOSS_AI_PLAN.md`  `[absorbed by Plan 5 (#180)]`

### No major change

Dynamic Boss has shipped.

### Add (verified)

PR #169's security invariant — expected answers must never be sent to the Boss response/persona model — is preserved in `boss_context_builder.build_boss_context`, which scrubs `expected/ans/accepted_answers/answer_spec/correct/canonical` recursively before any prompt assembly. Server-side judge (`check_boss_answer`) decides correctness; the model only explains/hints based on safe rubric/context.

---

## 4.7 `06_MODEL_GATEWAY_AND_STRUCTURED_OUTPUTS.md`  `[absorbed by Plan 6 (#179)]`

### Major rewrite needed → done

The old plan said "create a gateway because gemini.py is weak."

Final shape, as shipped:

- `ai_orchestrator.py` is the provider facade.
- `ai_gateway.py` sits **above** it for task policy, logging, strict validation, retries, and task-level routing.
- Vertex/Gemini are not reintroduced.
- Kimi is the sole provider; `AI_BACKEND_PREFERENCE` is forward-compat only.

---

## 4.8 `07_PROMPT_REWRITE_AND_CONTRACTS.md`  `[in-flight on `feature/prompt-rewrite-plan7`]`

### Keep

Still needed.

### Branch state (2026-05-07)

Branch `feature/prompt-rewrite-plan7` exists at commit `acc4eb7` ("feat(ai): Plan 7 — Prompt Rewrite and Contracts for Dynamic Boss"). Touches:

- `server/prompts/runtime/_shared_context_contract.md` (new)
- `server/prompts/runtime/{boss-answer-checker,boss-question-generator,boss-tutor,input-guardrail,tutor-assistant}.md`
- `server/services/{ai_context,ai_gateway,ai_orchestrator,boss_dynamic,tutor}.py`
- `server/schemas/ai_contracts.py`
- `server/routes/ai.py`
- `server/template/runtime.js`
- 3 new test fixtures under `tests/fixtures/ai_prompt_cases/`

Plan 7 overlaps with `ai_orchestrator.py` and `ai_gateway.py` but does not undo Plan 6's structural decisions — it tightens prompt contracts that the gateway already validates. Plan 10 is documentation-only and does not collide.

### Add

Prompts should reference sanitized `INPUT` blocks generated by `build_input_section`, not hand-rolled JSON snippets. Plan 7's `_shared_context_contract.md` formalises this.

---

## 4.9 `08_EVALUATION_LOGGING_AND_ROLLOUT.md`  `[partially absorbed by Plan 6 (#179) telemetry; harness deferred]`

### Add PR-specific tests

Status:

- bloated base64 content does not crash tutor/Boss  `[absorbed — tests/test_prompt_sanitization.py covers this from PR #169 itself]`
- clean pedagogical `data:` mention is not wrongly stripped unless it is an actual inline base64 URL  `[still open — false-positive guard tests not yet added]`
- `ai_unavailable: true` fallback is counted as degraded, not successful  `[absorbed — ai_call_logs_repo records `success` + `fallback` separately]`
- `docs/API.md` includes new 422 error code docs  `[still open]`

The synthetic eval/simulation harness (Plan 8 §3) is **not** yet shipped. `SimulationJudgeResult` schema exists in `ai_contracts.py` as Plan 6 groundwork; the runner/loader is the open work.

---

# 5. Updated priority decision

The Priority list in the original delta doc is now mostly historical — Priorities 1–5 are absorbed by merged Plans. Refreshed priority for the next chunk of work:

## Priority 1 (current)  `[Plan 7, in-flight]`

**Prompt contract polish for tutor + boss + guardrail.** Tighten input/output contracts so the gateway's structured-output validation has clean data to enforce.

## Priority 2

**Final report analyst** — wire `FinalReportResult` schema into a `/ai/session/final-report` endpoint and a runtime UI surface.

## Priority 3

**Synthetic eval/simulation harness** — Plan 8 §3. Use `SimulationJudgeResult` to score multi-turn tutor + boss runs.

## Priority 4

**Confidence-tier tuning + answer-checker false-positive tests** — calibrate Plan 4's 0.90 / 0.75 / 0.60 cuts against logged data; add the data-URI false-positive regression suite.

## Priority 5

**K2.6 default for text tasks** — env-only flip; gated on cost/latency comparison after Priority 3 telemetry exists.

---

# 6. Final verdict (refreshed)

PR #169 was a good defensive patch. It prevented AI crashes from huge inline media and cleaned up provider naming.

It did **not** change the main architecture problem at the time:

```text
AI lacks a canonical, trustworthy, homework-specific live context packet.
```

That problem is now structurally resolved by Plans 1 → 6: instrumentation (#172), session state (#171), context builder + tutor repair (#171, #174), answer envelope + tier confidence (#175), dynamic boss (#180), and a typed model gateway with structured outputs and call logs (#179).

The revised, post-merge direction is:

```text
Reuse PR #169's sanitizer/fallback work everywhere.
Stop referencing gemini.py (done).
Stop duplicating provider cleanup (done).
Stop adding sanitizers — call build_input_section.
Stop adding gateway-side schema parsing — call ai_gateway.generate_structured.
Focus next on prompt-contract polish (Plan 7), final report, eval harness, and confidence-tier tuning.
```

---

# 7. State as of 2026-05-07

This snapshot reflects what is actually on `origin/server@38c50b9` after Plans 1–6 landed.

## Provider / orchestrator topology

| Layer | File | Role |
|---|---|---|
| Provider adapter | `server/services/ai_providers/kimi.py` | Concrete Kimi/Moonshot HTTP client |
| Provider registry | `server/services/ai_providers/__init__.py` + `base.py` | `register` / `get_provider` / `select_provider` |
| Orchestrator (facade) | `server/services/ai_orchestrator.py` | `generate`, `generate_json`, `generate_vision`, `build_input_section`, model constants `FAST_MODEL` / `PRO_MODEL` / `VISION_MODEL` |
| Gateway (task router) | `server/services/ai_gateway.py` | `AITask` enum, `TASK_MODEL_POLICY`, `generate_text`, `generate_structured`, `run_guardrail`, `get_status` |
| Context builder | `server/services/ai_context.py` | `TutorContextPacket`, `build_tutor_context`, `sanitize_screen_context_v2` |
| Boss context builder | `server/services/boss_context_builder.py` | `build_boss_context` (answer-key-scrubbed) |
| Boss state machine | `server/services/boss_dynamic.py` | `calculate_damage`, `next_difficulty`, `generate_boss_question`, `check_boss_answer` |
| Debug instrumentation | `server/services/ai_debug.py` | `context_debug` field (gated by `AI_DEBUG_CONTEXT`), metadata-only `nets.ai.context` log channel |
| Call telemetry | `server/db/ai_call_logs_repo.py` | append-only `ai_call_logs` table |

## Schemas

`server/schemas/ai_contracts.py` defines: `TutorResponse`, `AnswerCheckResult`, `BossQuestionGenerated`, `BossAnswerCheckResult`, `FinalReportResult`, `GuardrailResult`, `SimulationJudgeResult`.

## Prompts

`server/prompts/runtime/` includes `tutor-assistant.md`, `boss-tutor.md`, `boss-question-generator.md`, `boss-answer-checker.md`, `answer-checker{,-language,-math,-boss}.md`, `notebook-grader.md`, `real-life-challenge-grader.md`, `reflection-coach.md`, `tutor-boss-plan.md`, `input-guardrail.md`. Plan 7 (in-flight) introduces `_shared_context_contract.md` and tightens five existing prompts.

## Routes

| Endpoint | Source plan |
|---|---|
| `/api/ai/check-answer` | pre-existing, hardened by PR #169 |
| `/api/ai/boss-turn` | pre-existing legacy boss path |
| `/api/ai/tutor/chat` | repaired by Plan 3 |
| `/api/ai/tutor/boss-plan` | pre-existing |
| `/api/ai/runtime/submit-answer` | Plan 4 |
| `/api/ai/boss/start`, `/generate-question`, `/submit-answer`, `/state`, `/give-up` | Plan 5 |
| `/api/ai/status` | gateway-aware via Plan 6 |

## Env config (defaults from `server/config.py`)

```env
AI_BACKEND_PREFERENCE=kimi
KIMI_API_KEY=                     # required for live AI
KIMI_BASE_URL=https://api.moonshot.ai/v1
KIMI_MODEL_FAST=moonshot-v1-32k
KIMI_MODEL_PRO=moonshot-v1-128k
KIMI_MODEL_VISION=kimi-k2.6
AI_DEBUG_CONTEXT=                 # opt-in, gates context_debug response field
```

## Test baseline

`python -m pytest tests/ -q` → **2322 passed, 4 skipped** on `feat/ai-architecture-plan10` (off `origin/server@38c50b9`).

## Open work (post-Plan-6, pre-Plan-7-merge)

1. Plan 7 (`feature/prompt-rewrite-plan7`) — prompt contract tightening; in flight.
2. Final-report endpoint wiring `FinalReportResult` → `/ai/session/final-report`.
3. Synthetic eval / simulation harness for `SimulationJudgeResult`.
4. False-positive regression tests for `build_input_section` on legitimate `data:` mentions in code-lesson content.
5. `docs/API.md` 422 error-code documentation for `_check_no_inline_bloat`.
6. Builder autosave PUT → PATCH migration so legacy bloated rows can still be edited.
7. K2.6 default for text tasks (env-only flip; gated on telemetry comparison).
