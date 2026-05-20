# 04 — Answer Submission and Grading Repair Plan

**Goal:** make answer submission deterministic, traceable, phase-aware, and safe. The AI should judge messy human answers only when deterministic grading cannot confidently decide.

---

## 1. Verified current state

### Existing frontend bridge

`server/template/runtime.js` currently exposes `NETS_AI.checkAnswer(payload)` and sends this body:

```json
{
  "question": "...",
  "student_answer": "...",
  "expected_answers": ["..."],
  "subject": "...",
  "grade": 8,
  "tier": "standard",
  "context": "..."
}
```

The bridge does **not** consistently include:

- `session_id`
- `homework_id` / `hw_id`
- `phase`
- `question_id`
- `item_id`
- `step_id`
- `answer_spec`
- `current_phase_state`
- `attempt_number`

### Existing backend route

`server/routes/ai.py` contains `/ai/check-answer`. It first tries phase-specific grading paths such as:

- sentence-fill
- sentence-correction
- tile-match
- real-life challenge
- scenario challenge
- generic fallback

Some phase-specific branches require identifiers like `homework_id`, `item_id`, `left_id`, `right_id`, or `step_id`.

### Existing checker logic

`server/services/tutor.py::check_answer` currently does:

1. deterministic local check
2. cache lookup
3. LLM answer checking fallback
4. confidence gate
5. review queue fallback for uncertain results

The current AI acceptance threshold is strict: `confidence >= 0.90`.

---

## 2. Problem statement

The answer path has two different systems wearing one trench coat:

1. **Generic answer checking** — works with question text + expected answers.
2. **Phase-specific checking** — needs homework/phase/item IDs.

The frontend generic bridge does not carry enough metadata for phase-specific logic. So the backend sometimes cannot know what kind of answer it is checking.

---

## 3. Target behavior

Every answer submission must include a canonical **Answer Submission Envelope**.

```json
{
  "session_id": "sess_123",
  "homework_id": "hw_456",
  "phase": "practice",
  "phase_index": 3,
  "question_id": "q_12",
  "item_id": null,
  "step_id": null,
  "answer_type": "text | numeric | multiple_choice | sentence_fill | tile_match | scenario | real_life | boss",
  "student_answer": "...",
  "student_work_text": "optional scratch/calc/explanation",
  "client_context": {
    "visible_prompt": "...",
    "selected_text": "...",
    "subphase": "..."
  },
  "attempt_number": 2,
  "submitted_at_client": "2026-05-07T00:00:00+05:00"
}
```

The backend enriches this with trusted content:

```json
{
  "trusted_question": "loaded from homework content_json",
  "expected_answer": "loaded server-side",
  "rubric": "loaded server-side",
  "phase_goal": "loaded server-side",
  "previous_attempts": [...],
  "metrics_snapshot": {...}
}
```

**Never trust expected answers from frontend for final grading.** Frontend may display something, but backend must load the answer key from `homeworks.content_json` or the normalized homework state.

---

## 4. Work chunk A — create a canonical request schema

### File to modify

`server/routes/ai.py`

### Current issue

`CheckAnswerRequest` is too generic for the runtime homework flow.

### Required change

Add a new request model, keeping the old one temporarily for compatibility:

```python
class RuntimeAnswerSubmitRequest(BaseModel):
    session_id: str
    homework_id: str
    phase: str | None = None
    phase_index: int | None = None
    question_id: str | None = None
    item_id: str | None = None
    step_id: str | None = None
    answer_type: str | None = None
    student_answer: Any
    student_work_text: str | None = None
    client_context: dict[str, Any] = {}
    attempt_number: int | None = None
```

### New endpoint

```text
POST /ai/runtime/submit-answer
```

### Why new endpoint instead of changing `/ai/check-answer` immediately?

Because `/ai/check-answer` may already be used by older generated templates. Keep it as a legacy compatibility endpoint, then migrate the runtime UI to the new endpoint.

---

## 5. Work chunk B — server-side resolver before grading

### New file to create

`server/services/runtime_answer_resolver.py`

### Purpose

Take the submitted envelope and resolve the authoritative grading target.

```python
class ResolvedAnswerTarget(BaseModel):
    session_id: str
    homework_id: str
    phase: str | None
    phase_index: int | None
    question_id: str | None
    answer_type: str
    question_text: str
    expected_answers: list[str]
    rubric: dict[str, Any]
    phase_context: dict[str, Any]
    trusted_source_path: str
```

### Resolver responsibilities

1. Load homework by `homework_id` from `homework_repo`.
2. Read `content_json`.
3. Locate the phase by `phase` or `phase_index`.
4. Locate the question/item/step by ID.
5. Extract answer key and rubric.
6. Return `ResolvedAnswerTarget`.
7. If no trusted target is found, return a structured error, not a silent fallback.

### Required errors

```json
{
  "ok": false,
  "error_code": "QUESTION_NOT_RESOLVED",
  "message": "Could not resolve question_id q_12 inside homework hw_456 phase 3."
}
```

---

## 6. Work chunk C — unify deterministic + AI grading result

### New internal result contract

```json
{
  "ok": true,
  "grading_method": "deterministic | ai_judge | review_queue",
  "is_correct": false,
  "score": 0.4,
  "confidence": 0.87,
  "feedback": "You used the right formula but substituted b incorrectly.",
  "misconception_tags": ["wrong_substitution"],
  "next_hint": "Check the coefficient of x.",
  "requires_review": false,
  "attempt_number": 2
}
```

### File to modify

`server/services/tutor.py`

### Method

Do not let every route branch return its own shape. Normalize all phase-specific checks into the contract above.

### Recommended grading ladder

```text
1. Deterministic exact/numeric/set checker
2. Specialized phase checker
3. AI judge with strict schema
4. Review queue fallback
```

### Confidence policy change

Current `0.90` threshold is too blunt. Replace with tiered confidence:

| Confidence | Action |
|---:|---|
| `>= 0.90` | accept result |
| `0.75 - 0.89` | accept with `requires_review=false` for low-stakes homework, but mark `confidence_band=medium` |
| `0.60 - 0.74` | return partial feedback + optionally ask one clarification |
| `< 0.60` | review queue / fallback |

For math/numeric correctness, keep stricter confidence. For language/translation/explanation answers, medium confidence is often enough if rubric evidence is clear.

---

## 7. Work chunk D — update frontend runtime bridge

### File to modify

`server/template/runtime.js`

### Current issue

`NETS_AI.checkAnswer` sends generic payload only.

### Required change

Add a new function:

```js
NETS_AI.submitRuntimeAnswer = async function(payload) {
  return request('/ai/runtime/submit-answer', {
    method: 'POST',
    body: JSON.stringify({
      session_id: getCurrentSessionId(),
      homework_id: getCurrentHomeworkId(),
      phase: getCurrentPhaseName(),
      phase_index: getCurrentPhaseIndex(),
      question_id: payload.question_id || getCurrentQuestionId(),
      item_id: payload.item_id || null,
      step_id: payload.step_id || null,
      answer_type: payload.answer_type || inferAnswerTypeFromDom(),
      student_answer: payload.student_answer,
      student_work_text: payload.student_work_text || collectScratchWork(),
      client_context: collectRuntimeContext({ includeAnswerKey: false }),
      attempt_number: getAttemptNumber(payload.question_id)
    })
  });
};
```

Keep the legacy `checkAnswer` but make new templates call `submitRuntimeAnswer`.

---

## 8. Work chunk E — store answer attempts

### Depends on

`02_SESSION_STATE_AND_CONTEXT_BUILDER.md`

### New table

`phase_attempts`

### File to modify

`server/db/migrations.py`

### New repo file

`server/db/phase_attempt_repo.py`

### Required events

Every answer submit must create:

```text
student_answer_submitted
answer_checked
metrics_updated
```

### Why

Without stored attempt rows, Boss AI cannot adapt to actual student weakness. It will stay cosmetic.

---

## 9. Work chunk F — AI judge prompt repair

### Existing file

`server/prompts/runtime/answer-checker-language.md`

### Required change

Split answer judging into separate prompt contracts:

```text
answer-checker-language.md
answer-checker-math.md
answer-checker-boss.md
```

### Why

Language answers and math answers need different grading logic.

### Language checker requirements

- Accept Uzbek/English mixed responses.
- Judge semantic correctness, not exact wording.
- Extract misconception tags.
- Return `score`, `confidence`, and `feedback`.

### Math checker requirements

- Prefer deterministic result when available.
- If checking explanation, verify method and final answer separately.
- Return `math_error_type`.

---

## 10. Acceptance tests

### Test 1 — missing question ID must not silently fallback

Input:

```json
{
  "session_id": "s1",
  "homework_id": "hw1",
  "phase_index": 3,
  "student_answer": "x=4"
}
```

Expected:

```json
{
  "ok": false,
  "error_code": "QUESTION_NOT_RESOLVED"
}
```

### Test 2 — English vocabulary answer

Homework text contains:

```text
according to = ga ko'ra / bo'yicha
```

Student asks/submits:

```text
according to nima degani?
```

Expected tutor/answer behavior:

```text
"according to" means "...ga ko'ra" or "...bo'yicha" in Uzbek.
```

Not:

```text
Hey according to, how can I help?
```

### Test 3 — confidence medium should still give useful feedback

AI judge confidence = `0.82`.

Expected:

- no generic “I did not understand” fallback
- useful feedback shown
- event tagged `medium_confidence`

---

## 11. Done definition

This chunk is complete when:

- runtime answer submissions always include session/homework/phase/question metadata
- backend resolves trusted answer keys server-side
- all grading paths return one normalized contract
- attempts are stored in `phase_attempts`
- confidence fallback is tiered
- frontend no longer relies on generic `NETS_AI.checkAnswer` for homework runtime phases

