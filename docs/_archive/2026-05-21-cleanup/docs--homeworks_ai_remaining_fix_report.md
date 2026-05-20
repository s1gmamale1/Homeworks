# Homeworks AI Architecture Remaining Fix Report

## Scope
This report divides the remaining work into backend and frontend tasks needed to fully wire the AI architecture end-to-end after the plan merges. It focuses on live tutor context, runtime answer submission, AI gateway coverage, dynamic Boss integration, debug/eval rollout, and final expected behavior.

## Current Verified State

### Already present
- AI gateway exists with task-level model routing and logging intent.
- Tutor context collector exists in `runtime.js` and gathers active question DOM context when the DOM exposes the needed metadata.
- Dynamic Boss bridge functions exist in `runtime.js`: `bossStart`, `bossGenerateQuestion`, `bossSubmitAnswer`, `bossState`, `bossGiveUp`.
- Backend has the new runtime answer request model and `/api/ai/runtime/submit-answer` contract.
- Backend has debug instrumentation and canonical tutor context construction.

### Still not fully wired
- `submitRuntimeAnswer` is not exposed in `runtime.js`.
- Generic `nets:submit` event bridge still routes answer events to legacy `checkAnswer` and boss events to legacy `bossTurn`.
- `perfect_homework.html` still visibly contains old/static Final Boss UI text such as `Savol 1 / 10` and does not reference `bossGenerateQuestion`.
- Some AI paths in `tutor.py` still call `ai_orchestrator` directly instead of routing through `ai_gateway`.
- Full phase renderer metadata coverage is not proven: every active question must expose `data-question-id`, `data-subphase`, and active state.

---

# Backend Tasks

## BE-1 — Route Live Tutor through `ai_gateway.py`

### Problem
`tutor_chat_v2` still uses direct AI orchestration in `server/services/tutor.py` instead of the universal AI gateway.

### Files
- `server/services/tutor.py`
- `server/services/ai_gateway.py`
- `server/prompts/runtime/tutor-assistant.md`

### Fix
Replace direct `ai_orchestrator.generate(...)` usage in `tutor_chat_v2` with gateway call:

```python
await ai_gateway.generate_text(
    task=AITask.TUTOR_CHAT,
    prompt=prompt,
    input_payload=context_payload,
    prompt_version="tutor-assistant:v2"
)
```

If structured tutor response is desired, use `generate_structured(...)` with a Pydantic `TutorResponse` schema.

### Expected behavior
- Every tutor call records model, latency, provider, prompt version, success/failure.
- Tutor gets task-specific model routing.
- Provider failures are visible in `ai_call_logs` and metrics.
- Tutor is no longer a separate old-pipe AI path.

### Test
- Ask tutor a visible question.
- Check `/api/ai/debug/session/{session_id}/ai-calls`.
- Expected: `task_type=tutor_chat` exists.

---

## BE-2 — Route Runtime Answer AI Judge through `ai_gateway.py`

### Problem
`process_runtime_answer()` still uses direct `ai_orchestrator.generate_json(...)` when deterministic grading cannot decide.

### Files
- `server/services/tutor.py`
- `server/services/ai_gateway.py`
- `server/services/answer_checker.py`

### Fix
Create a strict Pydantic output model:

```python
class RuntimeAnswerJudgeResult(BaseModel):
    is_correct: bool
    score: float
    confidence: float
    feedback: str
    misconception_tags: list[str] = []
    requires_review: bool = False
```

Route AI judge through:

```python
await ai_gateway.generate_structured(
    task=AITask.ANSWER_CHECK,
    schema=RuntimeAnswerJudgeResult,
    prompt_version="runtime-answer-checker:v1",
    ...
)
```

### Expected behavior
- Deterministic checker runs first.
- AI judge runs only when needed.
- AI output is schema-validated.
- Low-confidence answers go to review/fallback, not random frontend behavior.
- Every judge call is logged.

### Test
Submit a messy written answer.
Expected: response includes `grading_method=ai_judge`, `confidence`, `feedback`, and an AI call log.

---

## BE-3 — Keep `/api/ai/runtime/submit-answer` as the Default Grading Path

### Problem
The new endpoint exists, but frontend is not fully using it yet.

### Files
- `server/routes/ai.py`
- `server/services/tutor.py`

### Fix
Make `/api/ai/runtime/submit-answer` the canonical backend endpoint for all new homework answer submissions.
Legacy `/api/ai/check-answer` stays only for old templates/fallback.

### Expected behavior
Every answer includes:

```json
{
  "session_id": "...",
  "homework_id": "...",
  "phase": "...",
  "subphase": "...",
  "question_id": "...",
  "item_id": "optional",
  "step_id": "optional",
  "student_answer": "...",
  "student_work_text": "...",
  "client_context": {}
}
```

### Test
Submit answers from adaptive quiz, sentence fill, tile match, and real-life challenge.
Expected: all go through `/api/ai/runtime/submit-answer`, not legacy `/check-answer`.

---

## BE-4 — Enforce Required Context Flags Server-side

### Problem
Frontend may still miss `question_id`, phase, subphase, or visible screen context.

### Files
- `server/services/ai_context.py`
- `server/routes/ai.py`

### Fix
For tutor and runtime answer calls, return structured debug warnings when context is incomplete:

```json
{
  "missing_context_flags": [
    "missing_question_id",
    "empty_screen_context"
  ]
}
```

For answer submission, fail hard if the missing field is required for trusted grading.
For tutor chat, allow response but tell the tutor to ask a precise clarification.

### Expected behavior
- Missing `question_id` becomes visible immediately.
- Tutor does not hallucinate when context is missing.
- Debug endpoints clearly show the frontend bug source.

### Test
Manually remove `question_id` from request.
Expected: debug context shows `missing_question_id`.

---

## BE-5 — Gate Legacy Boss vs Dynamic Boss

### Problem
The repo currently has two Boss systems:

- Legacy fixed Boss: `/api/ai/boss-turn`, `/api/ai/tutor/boss-plan`
- Dynamic Boss: `/api/ai/boss/start`, `/api/ai/boss/generate-question`, `/api/ai/boss/submit-answer`

### Files
- `server/routes/ai.py`
- `server/routes/ai_plan5.py`
- config/env files

### Fix
Add a backend flag:

```txt
AI_BOSS_MODE=dynamic
```

Routing rule:

- New runtime homework sessions → dynamic Boss only.
- Old rendered homework templates → legacy fallback only.

### Expected behavior
No mixed Boss mode. A student cannot start with dynamic question generation and submit answers to legacy `bossTurn`.

### Test
Start Boss from real homework UI.
Expected network sequence:

1. `/api/ai/boss/start`
2. `/api/ai/boss/generate-question`
3. `/api/ai/boss/submit-answer`

No `/api/ai/boss-turn` for new flow.

---

## BE-6 — Final Report Service Wiring

### Problem
Gateway has `final_report` as an AI task, but the end-of-homework report must consume the new metrics/session data consistently.

### Files
- `server/services/ai_gateway.py`
- final report route/service files
- session/metrics storage files

### Fix
Create or finish final-report pipeline:

```txt
phase summaries
attempt metrics
weak topics
strong topics
hint usage
boss result
time stats
misconception tags
↓
AI final report
↓
stored report + frontend summary
```

### Expected behavior
At session end, student and teacher receive clear feedback:

- overall score
- strengths
- weaknesses
- recommended practice
- next difficulty recommendation
- Boss performance

### Test
Complete a homework session and call final report endpoint.
Expected: report contains metrics from normal phases and Boss phase.

---

## BE-7 — Extend Regression Tests for Full Wiring

### Problem
Plan 8 eval scaffolding exists, but tests must catch incomplete frontend/backend wiring.

### Files
- `tests/`
- `tests/fixtures/ai_prompt_cases/`

### Fix
Add tests for:

- tutor gateway routing
- runtime answer gateway routing
- missing question ID detection
- empty screen context detection
- dynamic Boss no answer leak
- legacy Boss not used in dynamic mode
- final report from session metrics

### Expected behavior
Future PRs cannot silently break context delivery.

---

# Frontend Tasks

## FE-1 — Add `submitRuntimeAnswer` to `runtime.js`

### Problem
`runtime.js` has `collectRuntimeContext`, `tutorChat`, and dynamic Boss functions, but no exposed `submitRuntimeAnswer` bridge.

### File
- `server/template/runtime.js`

### Fix
Add:

```js
async function submitRuntimeAnswer(opts) {
  opts = opts || {};
  const ctxPacket = collectRuntimeContext(opts);
  return _post('/ai/runtime/submit-answer', {
    session_id: ctxPacket.session_id,
    homework_id: ctxPacket.hw_id,
    phase: ctxPacket.phase,
    subphase: ctxPacket.subphase,
    question_id: ctxPacket.question_id,
    item_id: opts.item_id || null,
    step_id: opts.step_id || null,
    answer_type: opts.answer_type || 'text',
    student_answer: opts.student_answer || '',
    student_work_text: ctxPacket.student_work_text || opts.student_work_text || '',
    client_context: ctxPacket.ui_state || {},
    attempt_number: opts.attempt_number || 1,
  });
}
```

Expose it:

```js
window.NETS_AI.submitRuntimeAnswer = submitRuntimeAnswer;
```

### Expected behavior
All new answer UI can call one standard endpoint.

---

## FE-2 — Change Generic `nets:submit` Event Bridge to Use New Endpoints

### Problem
The current generic event bridge still maps:

```js
kind === 'answer' → checkAnswer(payload)
kind === 'boss' → bossTurn(payload)
```

That keeps old routes alive in new gameplay.

### File
- `server/template/runtime.js`

### Fix
Change event bridge logic:

```js
if (kind === 'answer') result = await submitRuntimeAnswer(payload);
else if (kind === 'boss-answer') result = await bossSubmitAnswer(payload);
else if (kind === 'boss-generate') result = await bossGenerateQuestion(payload);
```

Keep legacy kinds as explicit fallback:

```js
kind === 'legacy-answer'
kind === 'legacy-boss'
```

### Expected behavior
New UI uses new AI architecture by default.
Legacy is visible and intentional, not accidental.

---

## FE-3 — Add Required DOM Metadata to Every Active Question

### Problem
`collectRuntimeContext()` can only deliver `question_id` if the active DOM node or `window.NETS_STATE` has it.

### Files
- `server/template/perfect_homework.html`
- phase renderer JS inside the template
- any generated runtime template chunks

### Fix
Every active question wrapper must include:

```html
<div
  data-nets-active="true"
  data-question-id="q_123"
  data-subphase="adaptive-quiz"
>
```

On phase/question transition:

```js
window.NETS_STATE = {
  phase: 'practice',
  subphase: 'adaptive-quiz',
  questionId: 'q_123'
};
```

Remove active marker from old question before setting it on the new one.

### Expected behavior
Tutor always knows the current question.

### Test
Open DevTools → run:

```js
document.querySelector('[data-nets-active="true"]')?.dataset
```

Expected:

```txt
questionId exists
subphase exists
```

---

## FE-4 — Ensure `screen_context` Contains Visible Question Text

### Problem
If active question root is wrong or too narrow, `screen_context` may be empty or irrelevant.

### Files
- `server/template/runtime.js`
- phase renderers

### Fix
Make active wrapper include all relevant visible text:

- question prompt
- passage/sentence
- visible answer options
- current instruction
- student input area

Do not include answer keys or expected answers.

### Expected behavior
When student asks “manabu joyga tushunmadim,” Tutor sees what “manabu joy” refers to.

### Test
In browser:

```js
NETS_AI._ctx
```

Then trigger tutor call and inspect request payload. `screen_context` should be non-empty and relevant.

---

## FE-5 — Fully Replace Static Boss UI Loop with Dynamic Boss Loop

### Problem
`perfect_homework.html` still shows old Final Boss UI text such as fixed question count and static Boss screen. The template does not visibly reference `bossGenerateQuestion`.

### Files
- `server/template/perfect_homework.html`
- runtime Boss JS code inside generated homework template
- possibly builder/injector code that emits Boss UI

### Fix
Boss frontend flow:

```txt
enter Boss phase
↓
NETS_AI.bossStart(...)
↓
NETS_AI.bossGenerateQuestion(...)
↓
render generated question
↓
student submits answer
↓
NETS_AI.bossSubmitAnswer(...)
↓
update HP, trials, difficulty, feedback
↓
loop until won/failed/give-up
```

### Expected behavior
- Boss questions are generated live.
- Boss targets weak topics.
- Boss HP changes from backend response.
- Trials decrease from backend response.
- No static `Savol 1 / 10` dependency unless it is merely visual count from dynamic state.

---

## FE-6 — Protect Against Answer Leakage in Boss UI

### Problem
Dynamic Boss backend should not return expected answer/rubric, but frontend should also never render these fields if accidentally present.

### Files
- Boss UI renderer

### Fix
Whitelist frontend render fields:

```js
const safeQuestion = {
  question_id: res.question_id,
  question_text: res.question_text,
  target_skill: res.target_skill,
  difficulty: res.difficulty,
  why_this_question: res.why_this_question,
};
```

Ignore:

```txt
expected_answer
rubric
canonical
full_credit
partial_credit
```

### Expected behavior
No answer key leaks into browser UI.

---

## FE-7 — Update Tutor Widget to Always Use `tutorChat`, Not Legacy `tutor`

### Problem
`runtime.js` still exposes old `tutor()` and generic event bridge still maps `kind === 'tutor'` to `tutor(payload)`, not `tutorChat(payload)`.

### File
- `server/template/runtime.js`

### Fix
For live homework tutor widget:

```js
kind === 'tutor-chat' → tutorChat(payload)
```

Keep legacy `tutor` only for older templates.

### Expected behavior
Tutor widget sends full context packet, not just generic question/input/context.

---

## FE-8 — Frontend Network Smoke Tests

### Required network sequence
During normal homework:

```txt
Tutor message → POST /api/ai/tutor/chat
Answer submit → POST /api/ai/runtime/submit-answer
Boss start → POST /api/ai/boss/start
Boss question → POST /api/ai/boss/generate-question
Boss answer → POST /api/ai/boss/submit-answer
```

### Routes that should disappear from new gameplay

```txt
POST /api/ai/check-answer
POST /api/ai/boss-turn
POST /api/ai/tutor/boss-plan
POST /api/ai/tutor
```

These can remain only for legacy fallback.

---

# Expected Behavior After Full Fix

## Live Tutor
- Knows homework, phase, subphase, current question, visible screen text, and student work.
- Answers phrase/context questions correctly.
- Does not greet random homework words as names.
- Uses recent attempts and chat history.
- If context is missing, asks a precise clarification.
- Logs all calls through AI gateway.

## Answer Submission
- Every answer goes through one envelope.
- Backend resolves trusted answer target.
- Deterministic checker runs first.
- AI judge runs only when needed.
- Attempt metrics update.
- Low confidence goes to review/fallback.

## Dynamic Boss
- Boss starts from session metrics.
- Generates questions live.
- Targets weak topics.
- Hidden answer/rubric stays server-side.
- HP/trials/difficulty update from backend state.
- No legacy fixed-question flow for new sessions.

## Final Report
- Uses all phase metrics and Boss results.
- Produces student-friendly and teacher/admin-friendly feedback.
- Stores final report against the session.

## Debug / Evaluation
- Debug endpoints reveal missing context fields.
- AI call logs show model, provider, task, latency, prompt version, success/failure.
- Regression dashboard catches sanitizer-empty, missing question ID, generic fallback, and schema failure spikes.

---

# Priority Order

## P0 — Must fix first
1. Add `submitRuntimeAnswer` frontend bridge.
2. Change answer UI to call `/api/ai/runtime/submit-answer`.
3. Ensure active question DOM has `data-question-id` and `data-nets-active`.
4. Switch actual Boss UI to dynamic endpoints.
5. Route Tutor and runtime answer AI judge through `ai_gateway`.

## P1 — Should fix next
6. Add dynamic-vs-legacy Boss feature flag.
7. Update generic `nets:submit` bridge to use new endpoints by default.
8. Add final report pipeline using session metrics.
9. Add tests proving no legacy routes are used in new runtime flow.

## P2 — Polish / hardening
10. Add frontend render whitelist for Boss fields.
11. Add more fixture/eval cases.
12. Add dashboard alert thresholds for production rollout.

---

# Short Version
Backend brain is mostly built. Frontend control flow is not fully plugged into it yet. The most important fix is to make the real homework UI use the new endpoints by default: `tutorChat`, `submitRuntimeAnswer`, and dynamic Boss start/generate/submit. Then route the remaining direct AI calls in `tutor.py` through `ai_gateway.py` so logging, model routing, prompt versions, and schema validation become universal.
