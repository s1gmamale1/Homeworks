# 01 — Repo Audit and AI Failure Diagnosis

This document verifies the current architecture of the `Homeworks` AI runtime and maps the observed problems to exact files/functions. No code edits are performed here.

---

## 1. Verified Current AI Surface

## 1.1 Backend endpoints

Observed in `server/routes/ai.py`:

| Endpoint | Current role | Issue |
|---|---|---|
| `POST /api/ai/check-answer` | Generic and phase-dispatched answer grading. | Generic fallback accepts weak payloads. Phase-specific branches need `homework_id` + item IDs. |
| `POST /api/ai/boss-turn` | Grades one provided boss question. | Does not generate next question. Does not use session history. |
| `POST /api/ai/tutor` | Older generic tutor helper. | Uses simple payload: phase, question, student_input, context. Not enough for live screen awareness. |
| `POST /api/ai/tutor/chat` | Newer live tutor chat with history. | Still depends on optional frontend context fields. |
| `POST /api/ai/tutor/boss-plan` | Builds personalized order/framing for boss questions. | Reorders existing fixed `boss_questions`; no inventions allowed. |
| `GET /api/ai/tutor/history` | Returns tutor chat turns. | Useful, should stay. |

---

## 1.2 Frontend runtime bridge

Observed in `server/template/runtime.js`:

| Function | Current payload | Issue |
|---|---|---|
| `checkAnswer(opts)` | `question`, `student_answer`, `expected_answers`, `subject`, `grade`, `tier`, `context` | Missing `homework_id`, `phase`, `subphase`, `question_id`, `answer_spec`, UI state, session ID. |
| `bossTurn(opts)` | `boss_question`, `student_answer`, `expected_answers`, `damage_value`, `hp_remaining`, `attempt_number`, subject/grade | Frontend supplies expected answers. Boss is not server-generated. No session state. |
| `tutor(opts)` | `phase`, `question`, `student_input`, subject/grade/context | Legacy generic helper, not screen-aware. |
| `tutorChat(opts)` | `session_id`, `hw_id`, `phase`, `message`; optional `question_id`, `screen_context`, `student_work_text`, `subphase` | Better, but context fields are optional and not guaranteed. |
| `bossPlan(opts)` | `session_id`, `hw_id` | Builds only a plan over fixed boss questions. |
| `nets:submit` event bridge | Calls generic functions by kind. | `kind: 'answer'` still uses weak `checkAnswer`. |

---

## 1.3 Existing DB state

Observed in `server/db/migrations.py`:

### Existing tables that matter

| Table | Current usefulness | Missing pieces |
|---|---|---|
| `homeworks` | Stores `content_json`. | Good source of stable homework content. |
| `sessions` | Has `homework_id`, `student_name`, `overall_score`, `phase_scores`. | Missing current phase, status, metrics, tutor summary, boss state. |
| `responses` | Stores phase, question_id, answer, correct, time_ms. | Too thin for AI-grade analytics. No feedback, score, confidence, checker source, misconception tags. |
| `tutor_conversations` | Append-only chat history. | Good. Needs integration with context builder and Boss. |
| `answer_cache` | Caches AI answer checks. | Good, but cache keys must include full answer spec and homework context. |
| `review_queue` | Stores low-confidence AI reviews. | Good but should be tied to session/phase/attempt. |
| `tutor_warnings` | Tracks behavior warnings. | Useful as extra context, not core performance. |
| `notebook_captures` | Stores handwriting/photo grading. | Potential future evidence source. |

### Tables not currently present but needed

| New table | Purpose |
|---|---|
| `session_events` | Append-only audit stream of every student/tutor/system event. |
| `phase_attempts` | Rich answer attempts, checker source, score, feedback, misconceptions. |
| `session_metrics` | Aggregated live performance metrics. |
| `boss_state` or `sessions.boss_state_json` | HP, trials, difficulty, generated question IDs, used topics. |
| `generated_boss_questions` | Store hidden generated question, rubric, expected answer, topic tags. |

---

## 2. Confirmed Root Causes

## 2.1 Live Tutor context starvation

### Existing behavior

`TutorChatRequest` has optional fields:

```text
question_id?: string
screen_context?: string
student_work_text?: string
subphase?: string
```

`tutor_chat` only extracts `question_text` when `question_id` exists and `hw_meta.question` is a dict. If no active question is provided, the model may get no exact question stem.

### Why this breaks the example

Student asks:

```text
"according to" nima degani?
```

If `SCREEN_CONTEXT` and `QUESTION_TEXT` are empty, the model cannot know that `according to` appears in the current homework sentence. The model treats it as a generic phrase or even as a malformed greeting.

### Required fix

- Frontend must always send active screen text and active question metadata.
- Backend must fallback to session current question if `question_id` is missing.
- Prompt must explicitly handle direct phrase-definition questions from visible content.

---

## 2.2 Sanitizer destroys useful context

### Existing behavior

`_sanitize_screen_context` drops entire lines containing markers like:

```text
data-correct=true
class="correct"
class="is-correct"
answer-key
data-expected
data-answer
```

### Why this is dangerous

If the frontend sends DOM-derived HTML where a full exercise block is one large line and one attribute contains `class="correct"`, the whole line may be dropped. This can remove the sentence the student is asking about.

### Required fix

Replace line deletion with a structured frontend extractor:

```text
visible_text
active_question_text
student_visible_options
student_current_input
redacted_answer_metadata=false
```

Then backend sanitizer redacts answer-bearing attributes/values without deleting surrounding educational text.

---

## 2.3 Boss is static by design

### Existing behavior

`boss_plan` receives `BOSS_QUESTIONS` and prompt rule says:

```text
Include every input question_id exactly once. No omissions, no inventions.
```

`boss_turn` receives a single `boss_question`, checks `student_answer` against supplied `expected_answers`, and generates only a one-line boss response.

### Required fix

Add new dynamic Boss loop:

```text
boss/start
boss/next-question
boss/answer
boss/finalize
```

Do not remove old fixed boss path immediately. Keep it as compatibility fallback until dynamic Boss passes evals.

---

## 2.4 Boss has no turn memory

### Existing behavior

`boss-tutor.md` says to scan `CHAT_HISTORY` and `recent_assistant_phrases`, but `boss_turn` payload does not include them.

### Required fix

Boss answer generation must receive:

```text
boss_turn_history
recent_boss_phrases
used_question_topics
current_boss_state
```

This should come from backend state, not frontend memory.

---

## 2.5 Answer submission payload mismatch

### Existing behavior

`runtime.js` generic `checkAnswer` does not send `homework_id`, `phase`, `subphase`, `question_id`, or `answer_spec`.

`routes/ai.py` contains phase-specific fields for:

- sentence-fill
- tile-match
- real-life-challenge
- final-boss
- tic-tac-toe
- memory-palace

But generic `checkAnswer` cannot reliably trigger those branches without the required fields.

### Required fix

Create one canonical `AnswerSubmissionEnvelope` and make each phase adapter populate it.

---

## 2.6 Hard confidence gate makes AI look dumb

### Existing behavior

In `tutor.check_answer`, AI fallback is accepted only when confidence is `>= 0.90`. Below that, non-boss mode marks incorrect or generic unsure and sends review.

### Required fix

Replace with action tiers:

| Confidence | Action |
|---:|---|
| `>= 0.90` | Accept AI result. |
| `0.70–0.89` | Show partial/uncertain feedback, allow retry, log review candidate. |
| `0.45–0.69` | Ask for clarification or require more work. |
| `<0.45` | Safe fallback and review queue. |

Do not make `0.89` behave like total failure.

---

## 2.7 Model routing defaults are not K2.6

### Existing behavior

`server/services/ai_providers/kimi.py` defaults:

```text
KIMI_MODEL_FAST → moonshot-v1-32k
KIMI_MODEL_PRO → moonshot-v1-128k
KIMI_MODEL_VISION → kimi-k2.6
```

`server/services/gemini.py` maps internal `FAST_MODEL` and `PRO_MODEL` to Kimi provider fast/pro models when Kimi is active.

### Required fix

Set text models explicitly in env and status reporting:

```env
AI_BACKEND_PREFERENCE=kimi,vertex,gemini_api
KIMI_MODEL_FAST=kimi-k2.6
KIMI_MODEL_PRO=kimi-k2.6
```

Then update K2.6 JSON handling, because current Kimi code has special handling that avoids `response_format` for some K2 vision calls, but normal text JSON calls still use JSON mode.

---

## 3. Claims From Gemini: Verdict

| Claim | Verdict | Reason |
|---|---:|---|
| Boss is static | Confirmed | `boss_plan` uses fixed `boss_questions`; prompt forbids inventions. |
| Boss has no chat history | Confirmed | `boss_turn` payload does not include history, despite prompt mentioning it. |
| Live Tutor missing context causes hallucination | Confirmed | `question_id`, `screen_context`, `student_work_text` are optional. |
| Sanitizer may delete useful screen context | Confirmed risk | Drops whole lines with answer markers. |
| `0.90` confidence gate creates dumb fallback | Confirmed | Low confidence path can mark incorrect/unsure. |
| K2.6 unused for normal text by default | Confirmed by defaults | K2.6 is default only for vision model. |
| Live Tutor has no memory | Partially wrong | `tutor_chat` uses `tutor_conversations` recent history. |
| Prompt is the main problem | Mostly wrong | Prompt has many good rules; context feeding is the bigger issue. |

---

## 4. Immediate Diagnostic Tasks

## Task A — Add debug metadata for Tutor Chat

**Where:** `server/routes/ai.py`, `server/services/tutor.py`

Log:

```json
{
  "session_id_present": true,
  "hw_id_present": true,
  "phase": "practice",
  "subphase": "sentence-fill",
  "question_id_present": true,
  "question_found": true,
  "question_text_len": 143,
  "screen_context_raw_len": 1200,
  "screen_context_clean_len": 820,
  "student_work_text_len": 17,
  "chat_history_count": 6,
  "model": "kimi-k2.6"
}
```

## Task B — Add debug metadata for Answer Check

**Where:** `server/routes/ai.py`, `server/services/tutor.py`

Log:

```json
{
  "phase": "sentence-fill",
  "homework_id_present": true,
  "question_id": "...",
  "item_id": "...",
  "answer_spec_type": "semantic",
  "checker_path": "deterministic|ai_judge|phase_adapter",
  "confidence": 0.84,
  "result_action": "partial_retry"
}
```

## Task C — Add debug metadata for Boss

**Where:** `server/routes/ai.py`, `server/services/tutor.py`

Log:

```json
{
  "mode": "fixed_boss|dynamic_boss",
  "session_id_present": true,
  "history_count": 0,
  "boss_questions_count": 5,
  "question_source": "content_json|generated",
  "hp_before": 70,
  "hp_after": 55,
  "difficulty": "medium"
}
```

---

## 5. Non-Code Investigation Checklist

Before editing logic, reproduce these flows and capture logs:

1. English homework: ask `"according to" nima degani?` while phrase is visible.
2. Ask `"manabu joyga tushunmadim"` with no active question ID.
3. Submit sentence-fill answer with and without `homework_id`.
4. Submit boss answer and inspect whether expected answers came from frontend.
5. Hit `/api/ai/status` and confirm resolved provider/model.
6. Trigger an AI fallback answer with confidence around `0.80–0.89`.
7. Compare raw vs sanitized screen context lengths.

---

## 6. Conclusion

The current system is not broken because it lacks AI. It is broken because the AI runtime contract is too loose.

The immediate engineering move is:

```text
optional context fields → mandatory structured context packet
fixed boss list → dynamic boss question generator backed by stored state
generic answer bridge → phase-aware answer envelope
JSON prompt parsing → schema validation + retry
manual vibes → eval suite
```

