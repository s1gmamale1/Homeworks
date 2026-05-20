# 06 — Model Gateway and Structured Outputs Plan

**Goal:** make model routing explicit, observable, configurable, and reliable. Stop hiding model choices behind vague `FAST_MODEL` / `PRO_MODEL` defaults, and stop relying on fragile JSON cleanup for production-critical AI outputs.

---

## 1. Verified current state

### Existing files

| File | Current role |
|---|---|
| `server/services/gemini.py` | Provider facade. Selects provider order and exposes `generate_text` / `generate_json`. |
| `server/services/ai_providers/kimi.py` | Kimi/Moonshot provider implementation. |
| `server/config.py` | Environment config source. |
| `server/services/tutor.py` | Calls `gemini.generate_json` / `gemini.generate_text` with `FAST_MODEL` or `PRO_MODEL`. |

### Current model defaults

`server/services/gemini.py` defaults:

```python
FAST_MODEL = "gemini-2.5-flash"
PRO_MODEL = "gemini-2.5-pro"
AI_PROVIDER_PREFERENCE = "kimi,vertex,gemini_api"
```

When Kimi is active, `gemini.py` maps Gemini fast/pro names into Kimi provider models.

`server/services/ai_providers/kimi.py` defaults:

```python
KIMI_MODEL_FAST = "moonshot-v1-32k"
KIMI_MODEL_PRO = "moonshot-v1-128k"
KIMI_MODEL_VISION = "kimi-k2.6"
```

So text tasks default to older Moonshot models unless `.env` overrides them.

---

## 2. Problem statement

The project currently has a provider shim, but not a real AI gateway.

Current issues:

- task type is not explicit enough
- resolved model name is not consistently logged
- text path can route to old models while user expects Kimi K2.6
- JSON reliability depends on prompt + cleanup, not strict schema
- model decisions are scattered across service code
- no central cost/latency/failure telemetry per AI call

---

## 3. Target design

Create a lightweight internal **AI Gateway** inside the backend.

```text
Tutor/Boss/Grading services
        ↓
server/services/ai_gateway.py
        ↓
Task policy + model router + schema enforcement + logging
        ↓
Provider adapters
        ↓
Kimi / Gemini / Vertex / future providers
```

This matches the enterprise gateway pattern in the research: one unified entrypoint controls provider choice, security checks, usage tracking, and model routing.

---

## 4. New file: `server/services/ai_gateway.py`

### Responsibilities

1. Accept a task type.
2. Resolve model based on task policy.
3. Call the provider adapter.
4. Enforce structured outputs where possible.
5. Log model, latency, token/cost estimate, status, and fallback.
6. Return normalized response.

### Task types

```python
class AITask(str, Enum):
    TUTOR_CHAT = "tutor_chat"
    ANSWER_CHECK = "answer_check"
    BOSS_QUESTION_GENERATE = "boss_question_generate"
    BOSS_ANSWER_CHECK = "boss_answer_check"
    BOSS_PERSONA_RESPONSE = "boss_persona_response"
    FINAL_REPORT = "final_report"
    SAFETY_GUARDRAIL = "safety_guardrail"
    SIMULATION_JUDGE = "simulation_judge"
```

### Model policy

```python
TASK_MODEL_POLICY = {
    AITask.TUTOR_CHAT: "pro",
    AITask.ANSWER_CHECK: "pro",
    AITask.BOSS_QUESTION_GENERATE: "pro",
    AITask.BOSS_ANSWER_CHECK: "pro",
    AITask.BOSS_PERSONA_RESPONSE: "fast",
    AITask.FINAL_REPORT: "pro",
    AITask.SAFETY_GUARDRAIL: "fast",
    AITask.SIMULATION_JUDGE: "pro",
}
```

For your current desired behavior, set both Kimi fast/pro to K2.6 if cost is acceptable:

```env
AI_PROVIDER_PREFERENCE=kimi,vertex,gemini_api
KIMI_MODEL_FAST=kimi-k2.6
KIMI_MODEL_PRO=kimi-k2.6
KIMI_MODEL_VISION=kimi-k2.6
```

But do not hardcode this in app logic. Keep it configurable.

---

## 5. Logging contract

### New table

`ai_call_logs`

### File to modify

`server/db/migrations.py`

```sql
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
    created_at TEXT NOT NULL
);
```

### Why

When the tutor acts dumb, first question should be:

```text
Which model answered? What context length? Did fallback happen? Was schema valid?
```

Right now this is not easily observable.

---

## 6. Structured output enforcement

### Current issue

`gemini.py::generate_json` appends a JSON instruction and then cleans/parses output. This is acceptable for prototype logic but fragile for production-critical grading/Boss contracts.

### Target

For providers that support JSON schema/strict structured output, use that directly. For providers that do not, keep parser fallback but validate with Pydantic and retry once.

### Gateway interface

```python
async def generate_structured(
    task: AITask,
    prompt: str,
    schema: type[BaseModel],
    session_id: str | None = None,
    homework_id: str | None = None,
    temperature: float = 0.2,
) -> BaseModel:
    ...
```

### Validation strategy

```text
Model output
  ↓
Parse JSON
  ↓
Pydantic validate
  ↓
If invalid: one repair retry with validation error
  ↓
If still invalid: structured fallback error
```

---

## 7. Provider adapter updates

### File to modify

`server/services/ai_providers/kimi.py`

### Current behavior

`generate_json` sends `response_format={"type": "json_object"}` for normal paths.

### Required behavior

Add provider capability flags:

```python
CAPABILITIES = {
    "json_object": True,
    "json_schema": False,  # set true only if verified for chosen endpoint/model
    "vision": True,
    "streaming": False
}
```

Then the gateway chooses:

```text
if provider supports strict schema:
    use strict schema
else:
    use json_object + Pydantic validation + repair retry
```

### Important K2.X behavior

The existing file already avoids `response_format` for K2.X vision. Do not break this. Keep vision behavior separate from text behavior.

---

## 8. Model choice matrix for Homeworks

| Task | Current likely model | Target default | Why |
|---|---|---|---|
| Live Tutor chat | Fast or subject-based Pro | Kimi K2.6 / Pro | Needs context reasoning and Uzbek/English mixed help. |
| Answer checking | Pro | Kimi K2.6 / Pro | Grading mistakes damage trust. |
| Boss question generation | Not present | Kimi K2.6 / Pro | Needs adaptive question design. |
| Boss answer check | Not separate | Kimi K2.6 / Pro | Affects HP and final metrics. |
| Boss persona response | Pro currently | Fast acceptable after grading | Style layer only if correctness already computed. |
| Final report | Not centralized | Pro | Needs synthesis from metrics. |
| Safety/guardrail | Not centralized | Fast | Classification task. |
| Simulation judge | Not present | Pro | Evaluates multi-turn quality. |

---

## 9. File-level implementation sequence

### Step 1

Create `server/services/ai_gateway.py`.

### Step 2

Create `server/schemas/ai_contracts.py` for structured outputs:

```text
TutorResponse
AnswerCheckResult
BossQuestionGenerated
BossAnswerCheckResult
FinalReportResult
GuardrailResult
```

### Step 3

Update `tutor.py` calls:

```text
gemini.generate_json(...) → ai_gateway.generate_structured(task=...)
gemini.generate_text(...) → ai_gateway.generate_text(task=...)
```

### Step 4

Add `ai_call_logs` repo helper.

### Step 5

Expose `/ai/status` with resolved effective models:

```json
{
  "provider_order": ["kimi", "vertex", "gemini_api"],
  "tasks": {
    "tutor_chat": {"provider": "kimi", "model": "kimi-k2.6"},
    "answer_check": {"provider": "kimi", "model": "kimi-k2.6"}
  }
}
```

---

## 10. Guardrails

Add a cheap preflight guardrail for:

- prompt injection attempts
- requests to reveal answers directly
- requests to reveal system prompt
- irrelevant/off-topic chat

Do not overbuild this first. Start with a fast classifier prompt + hardcoded rules.

### New prompt

`server/prompts/runtime/input-guardrail.md`

### Output

```json
{
  "allowed": true,
  "risk": "none | answer_leak | prompt_injection | off_topic",
  "action": "continue | refuse | redirect | ask_clarifying"
}
```

---

## 11. Acceptance tests

### Test 1 — model visibility

`/ai/status` must show actual resolved model names, not generic fast/pro labels.

### Test 2 — tutor call log

Every `/ai/tutor/chat` call creates an `ai_call_logs` row.

### Test 3 — schema invalid retry

If model returns invalid JSON, gateway retries once with validation errors.

### Test 4 — no silent fallback

If all providers fail, response includes:

```json
{
  "ok": false,
  "error_code": "AI_PROVIDER_FAILED"
}
```

### Test 5 — Kimi K2.6 config

With env:

```env
KIMI_MODEL_FAST=kimi-k2.6
KIMI_MODEL_PRO=kimi-k2.6
```

`/ai/status` confirms tutor and Boss tasks use K2.6.

---

## 12. Done definition

This chunk is complete when:

- all AI calls go through `ai_gateway.py`
- task type is explicit for every AI call
- effective provider/model is logged
- structured outputs are validated
- Kimi K2.6 can be forced by env without code edits
- frontend or logs can confirm which model answered

