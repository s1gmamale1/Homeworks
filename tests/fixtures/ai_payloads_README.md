# ai_payloads.json — Fixture Documentation

Each key in `ai_payloads.json` maps to one POST endpoint.
Fields are written in Uzbek (uz) to match production usage.

## check_answer
Maps to `POST /api/ai/check-answer`.
- `question` — question text shown to student
- `student_answer` — what the student typed
- `expected_answers` — array of accepted answers from the homework author
- `subject` / `grade` — context for the AI grader
- `tier` — difficulty: EASY | MEDIUM | HARD
- `context` — optional extra context (recent flashcard terms, etc.)

Expected response shape (from runtime.js `checkAnswer`):
```json
{ "correct": bool, "score": float, "feedback": str, "matched_expected": str|null }
```

## boss_turn
Maps to `POST /api/ai/boss-turn`.
- `boss_question` — the boss character's challenge question
- `student_answer` — student's typed response
- `expected_answers` — accepted correct answers
- `damage_value` — base HP damage if correct (0–50)
- `hp_remaining` — boss current HP
- `attempt_number` — 1 = first try; >= 2 = retry (triggers hint generation)

Expected response shape (from runtime.js `bossTurn`):
```json
{ "correct": bool, "damage_dealt": int, "boss_response": str, "hint": str|null, "score": float }
```

## reflection
Maps to `POST /api/ai/reflection`.
- `homework_title` / `homework_summary` — injected by backend via NETS_CTX
- `student_reflection` — free-text what the student typed in the reflection box
- `performance` — `{correct, total, time_minutes, weak_phase}` object

Expected response shape (from runtime.js `reflectionFeedback`):
```json
{ "feedback": str, "next_steps": [str, ...], "encouragement": str }
```

## tutor
Maps to `POST /api/ai/tutor`.
- `phase` — current homework phase name (e.g. "flashcards", "boss")
- `question` — the question the student is looking at
- `student_input` — what the student typed when asking for help
- `context` — optional extra context

Expected response shape (from runtime.js `tutor`):
```json
{ "response": str, "guidance_type": "hint"|"explanation"|"encouragement"|"correction" }
```
