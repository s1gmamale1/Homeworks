# 07 — Prompt Rewrite and Contract Plan

**Goal:** rewrite prompts so they match the repaired architecture. Prompts should consume structured context packets, return strict contracts, and stop asking the model to use fields that backend does not provide.

---

## 1. Verified current prompt files

| Prompt | Existing role | Current issue |
|---|---|---|
| `tutor-assistant.md` | Live tutor response | Good foundation, but depends on optional context and needs stricter output/action contract. |
| `boss-tutor.md` | Boss persona response | Mentions `CHAT_HISTORY`, but backend `boss_turn` does not provide it. Also not responsible for correctness. |
| `tutor-boss-plan.md` | Boss plan/order | Static by design: uses input `BOSS_QUESTIONS`; no new inventions. |
| `answer-checker-language.md` | AI answer checker | Needs splitting by task type and schema consistency. |

---

## 2. Prompt design principles for this project

### Rule 1 — prompts consume backend-owned facts

Never make the model infer current phase from user phrasing alone. Feed:

```text
session_state
homework_summary
current_phase
current_question
performance_snapshot
recent_history
student_message
```

### Rule 2 — user text is untrusted

Wrap student message in delimiters:

```xml
<UNTRUSTED_STUDENT_MESSAGE>
...
</UNTRUSTED_STUDENT_MESSAGE>
```

### Rule 3 — prompt must match available fields

If the prompt says “use CHAT_HISTORY,” backend must include `CHAT_HISTORY`. No ghost variables.

### Rule 4 — output contracts are separate from personality

For grading and Boss state, JSON first. Persona text is a field inside JSON, not the whole response.

---

## 3. New shared context format

### New file

`server/prompts/runtime/_shared_context_contract.md`

### Content

```md
# Shared Context Contract

The backend provides these sections:

<SESSION_STATE>
- session_id
- homework_id
- current_phase_index
- current_phase_title
- current_question_id
- mode
</SESSION_STATE>

<HOMEWORK_SUMMARY>
Stable homework title, subject, grade, learning goals, and total phases.
</HOMEWORK_SUMMARY>

<CURRENT_PHASE_CONTEXT>
Trusted server-side phase title, instructions, visible content summary, and current question.
</CURRENT_PHASE_CONTEXT>

<PERFORMANCE_SNAPSHOT>
Accuracy, attempts, hints, weak topics, strong topics, phase summaries.
</PERFORMANCE_SNAPSHOT>

<RECENT_HISTORY>
Recent conversation turns or compressed summary.
</RECENT_HISTORY>

<UNTRUSTED_STUDENT_MESSAGE>
The student's newest message.
</UNTRUSTED_STUDENT_MESSAGE>
```

Use this as a human-readable prompt convention. Actual payload can be JSON.

---

## 4. Live Tutor prompt rewrite

### File to modify

`server/prompts/runtime/tutor-assistant.md`

### Keep

- answer in student language
- short guided teaching
- do not leak answer unless policy allows
- ask clarifying question when context is truly missing

### Add

Explicit behavior for vocabulary/context questions:

```md
If the student asks what a word/phrase means, and the phrase exists in CURRENT_PHASE_CONTEXT or CURRENT_QUESTION, explain the phrase directly in the student's language. Do not greet the phrase as if it were a person.

Bad:
"Hey according to, how can I help?"

Good:
"'according to' degani '...ga ko'ra' yoki '...bo'yicha'. Masalan: according to the text = matnga ko'ra."
```

### Required output contract

```json
{
  "reply": "...",
  "action": "explain | hint | ask_clarifying | encourage | answer_context_question | redirect | refuse",
  "used_context": {
    "phase": true,
    "question": true,
    "screen": false,
    "history": true
  },
  "detected_confusion": ["vocabulary_meaning"],
  "needs_backend_action": null,
  "confidence": 0.86
}
```

---

## 5. Answer checker prompt split

### Existing file

`server/prompts/runtime/answer-checker-language.md`

### Replace with three prompts

```text
answer-checker-language.md
answer-checker-math.md
answer-checker-general-rubric.md
```

### Language answer checker contract

```json
{
  "is_correct": true,
  "score": 0.85,
  "confidence": 0.88,
  "feedback": "...",
  "accepted_meaning": "...",
  "missing_parts": [],
  "misconception_tags": [],
  "student_language": "uzbek"
}
```

### Math answer checker contract

```json
{
  "is_correct": false,
  "final_answer_correct": false,
  "method_correct": true,
  "score": 0.55,
  "confidence": 0.91,
  "feedback": "Formula is correct, substitution has a sign error.",
  "math_error_type": "sign_error",
  "misconception_tags": ["sign_error"]
}
```

---

## 6. Boss prompts

### Deprecate as default

`server/prompts/runtime/tutor-boss-plan.md`

Keep only as fallback for old fixed Boss mode.

### New prompt

`server/prompts/runtime/boss-question-generator.md`

Purpose: generate one question at a time.

### New prompt

`server/prompts/runtime/boss-answer-checker.md`

Purpose: judge student answer to generated Boss question.

### Modify existing

`server/prompts/runtime/boss-tutor.md`

Purpose becomes **persona response only** after correctness is known.

It should no longer mention unavailable `CHAT_HISTORY` unless backend provides `RECENT_BOSS_HISTORY`.

New variables:

```text
BOSS_STATE
CURRENT_BOSS_QUESTION
ANSWER_RESULT
RECENT_BOSS_HISTORY
PERSONA_TRAITS
```

---

## 7. Final report prompt

### New prompt

`server/prompts/runtime/final-homework-report.md`

### Input

```json
{
  "homework_summary": {...},
  "phase_summaries": [...],
  "attempt_metrics": {...},
  "boss_results": {...},
  "tutor_observations": [...]
}
```

### Output

```json
{
  "overall_score": 78,
  "mastery_level": "developing",
  "strengths": ["..."],
  "weaknesses": ["..."],
  "student_feedback": "...",
  "teacher_feedback": "...",
  "recommended_practice": ["..."],
  "next_homework_difficulty": "medium-hard"
}
```

---

## 8. Prompt versioning

### New table or constants

Every prompt should have a version string:

```text
tutor-assistant:v2
answer-checker-language:v2
boss-question-generator:v1
boss-answer-checker:v1
boss-tutor:v2
final-homework-report:v1
```

### Log it

`ai_call_logs.prompt_version` should record it.

### Why

When prompt behavior changes, you need to know which version generated which output.

---

## 9. Prompt testing fixture examples

Create:

```text
tests/fixtures/ai_prompt_cases/
  tutor_vocab_according_to.json
  tutor_missing_context.json
  answer_language_partial.json
  boss_generate_weak_topic.json
  boss_no_repetition.json
```

Example case:

```json
{
  "name": "tutor explains according to",
  "context": {
    "current_phase_context": {
      "visible_text": "According to the text, Tom was late."
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

## 10. Acceptance tests

### Test 1 — ghost variable check

Every prompt variable must be provided by the backend builder. If prompt references `CHAT_HISTORY`, builder must pass it or test fails.

### Test 2 — strict output contract

Every AI task output validates against Pydantic schema.

### Test 3 — vocabulary behavior

Tutor directly explains vocabulary when phrase is in current context.

### Test 4 — no answer leakage

Tutor gives hints unless the mode allows direct explanation.

### Test 5 — Boss generator output

Generated Boss question includes expected answer and rubric.

---

## 11. Done definition

This chunk is complete when:

- prompts match actual backend context fields
- task-specific prompts exist
- tutor prompt handles vocabulary/context questions correctly
- Boss question generation and answer checking prompts exist
- all prompts return structured contracts where needed
- prompt versions are logged

