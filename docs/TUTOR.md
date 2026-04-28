# Live AI Tutor — Architecture

The AI Tutor is a stateless runtime service that provides personalized guidance to students during homework playback. It orchestrates interaction between the frontend widget, the LLM provider (Vertex AI / Gemini / Kimi), and the session database to provide context-aware hints without leaking answers.

## Phase modes

| Phase    | Tutor Behavior                                | LLM gets `answer_spec`? | LOC Reference                  |
|----------|-----------------------------------------------|-------------------------|--------------------------------|
| preview  | Explains concepts and provides examples.      | Yes (full)              | `server/services/tutor.py:195` |
| practice | Scoped to specific questions; provides hints. | No (redacted)           | `server/services/tutor.py:190` |
| boss     | Strategic framing for the final challenge.    | No (redacted)           | `server/services/tutor.py:397` |

## Request flow

```
[ Browser ] -> POST /api/ai/tutor/chat            (server/routes/ai.py:342)
      |
      v
[ tutor.py::tutor_chat ]                          (server/services/tutor.py:284)
      |-- 1. db.add_tutor_turn (persist "user" message)
      |-- 2. check SESSION_MESSAGE_CAP (60 turns)
      |-- 3. build context (profile + attempts + redacted question)
      |-- 4. gemini.generate (server/services/gemini.py)
      |-- 5. db.add_tutor_turn (persist "assistant" response)
      v
[ Response JSON ] -> {"response": "...", "message_id": 123}
```

## Answer-leak guarantee

To prevent the LLM from accidentally revealing the correct answer during practice or boss phases, all question payloads are passed through a redactor. The keys `expected`, `ans`, `accepted_answers`, and `correct` are stripped at the top level and inside the `answer_spec` object (see `server/services/tutor.py:190`). This is strictly enforced for all phases except `preview`.

**Test guard:** `tests/test_tutor_chat.py::test_practice_no_answer_leak`

## Boss-plan flow

When a student reaches the boss phase, the runtime initializes a personalized challenge sequence:

1. `build_session_profile` (`server/db.py:512`) — Aggregates the last 20 chat turns into a text summary of student behavior.
2. `boss_plan()` (`server/services/tutor.py:382`) — Sends the profile, recent practice attempts, and sanitized boss questions to the LLM (using `PRO_MODEL`).
3. **Validation** (`server/services/tutor.py:343`) — Ensures the LLM returned every question ID exactly once and used valid persona traits.
4. **Fallback** (`server/services/tutor.py:330`) — If the LLM fails or validation fails, a `_default_boss_plan` is used (original order, neutral framing).

Question stems and `answer_spec` are never modified by the planner; it only generates the `framing_text` wrapper.

## DB tables we own vs read

- **Owned:** `tutor_conversations` (`server/db.py:84`) — Stores every chat turn (role, content, phase, question_id). Append-only history.
- **Read-only:** `tutor_attempts` (`server/db.py:539`) — Owned by the grading lane. We read the last 3 attempts on a question to provide context (e.g., "I see you've tried 42 twice already…"). Graceful fallback returns `[]` if the table is missing.

## Cache namespaces

- `answer_cache` — Managed by the grading lane to store deterministic and high-confidence AI verdicts.
- `tutor_cache` — *Deferred to Wave G.* Will handle budget tracking and repeated generic help queries.

## Adding a new tutor phase

1. **Backend:** Add the phase string to the redactor allow-list in `server/services/tutor.py:190` and update `server/prompts/runtime/tutor-assistant.md` instructions.
2. **Frontend:** The runtime must fire a `nets:phase-change` event to update the widget's internal state.

## Cost guards

- **Session cap:** Hard limit of 60 messages per `(session, homework)` pair (`server/services/tutor.py:25`).
- **LLM model:** Uses `FAST_MODEL` for chat and `PRO_MODEL` for the strategic boss plan.
- **Reliability:** The boss battle always defaults to a valid plan if the LLM hiccups, ensuring zero impact on playability.

## Future work

Detailed implementation plans for Phase 2 (streaming, summarization, proactive intervention) are located in `.claude/plans/flickering-rolling-robin.md` (gitignored — local only).
