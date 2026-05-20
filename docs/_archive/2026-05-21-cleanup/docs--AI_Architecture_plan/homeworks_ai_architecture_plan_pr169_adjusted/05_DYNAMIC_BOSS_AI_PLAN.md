# 05 — Dynamic AI Boss Repair Plan

**Goal:** replace the current static/pre-authored Boss flow with an adaptive Boss system that generates questions in real time from the student's homework performance, checks answers, updates HP/trials, and logs every turn.

---

## 1. Verified current state

### Existing prompt behavior

`server/prompts/runtime/tutor-boss-plan.md` currently receives `BOSS_QUESTIONS` and says:

```text
Include every input question_id exactly once. No omissions, no inventions.
```

That means current Boss planning is not dynamic question generation.

### Existing backend behavior

`server/services/tutor.py::boss_plan`:

- receives `boss_questions`
- sanitizes them
- asks LLM to order/plan them
- falls back to fixed plan if parsing fails

`server/services/tutor.py::boss_turn`:

- receives one `boss_question`
- receives `student_answer`
- receives `was_correct` calculated outside the LLM
- responds as the Boss persona
- does not receive chat history
- does not generate next question

### Existing frontend behavior

`server/template/runtime.js::NETS_AI.bossTurn` sends:

```json
{
  "boss_question": "...",
  "student_answer": "...",
  "expected_answers": [...],
  "was_correct": true,
  "damage": 15,
  "hp": 70,
  "attempt_number": 3
}
```

No `session_id`, no performance profile, no generated question contract.

---

## 2. Target Boss architecture

```text
Boss Start
  ↓
Build Boss Context from session metrics + phase summaries + weak topics
  ↓
Generate one adaptive Boss question
  ↓
Show question to student
  ↓
Student answers
  ↓
Resolve/check answer using boss answer checker
  ↓
Update HP/trials/difficulty
  ↓
Store boss turn event
  ↓
Generate next adaptive question
  ↓
Loop until win/fail/give-up
```

Boss AI should become a **state machine**, not a list renderer.

---

## 3. New Boss state model

### Add fields to `sessions` or create `boss_sessions`

Preferred: create a dedicated `boss_sessions` table.

### File to modify

`server/db/migrations.py`

### New table

```sql
CREATE TABLE IF NOT EXISTS boss_sessions (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    homework_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    hp INTEGER NOT NULL DEFAULT 100,
    max_hp INTEGER NOT NULL DEFAULT 100,
    trials_left INTEGER NOT NULL DEFAULT 7,
    current_difficulty TEXT NOT NULL DEFAULT 'medium',
    current_question_id TEXT,
    asked_question_ids_json TEXT NOT NULL DEFAULT '[]',
    weak_topics_json TEXT NOT NULL DEFAULT '[]',
    strong_topics_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

### New table: generated boss questions

```sql
CREATE TABLE IF NOT EXISTS generated_boss_questions (
    id TEXT PRIMARY KEY,
    boss_session_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    question_text TEXT NOT NULL,
    expected_answer_json TEXT NOT NULL,
    rubric_json TEXT NOT NULL,
    target_skill TEXT,
    difficulty TEXT NOT NULL,
    source_phase_ids_json TEXT NOT NULL DEFAULT '[]',
    generation_context_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
```

---

## 4. New endpoints

### File to modify

`server/routes/ai.py`

### Add endpoints

```text
POST /ai/boss/start
POST /ai/boss/generate-question
POST /ai/boss/submit-answer
POST /ai/boss/state
POST /ai/boss/give-up
```

### Endpoint responsibilities

| Endpoint | Responsibility |
|---|---|
| `/ai/boss/start` | Create boss session from finished homework session metrics. |
| `/ai/boss/generate-question` | Generate one new question from weak topics and current difficulty. |
| `/ai/boss/submit-answer` | Check answer, calculate damage, update HP/trials. |
| `/ai/boss/state` | Return current Boss state to frontend. |
| `/ai/boss/give-up` | End boss session as abandoned/failed. |

Keep old `/ai/boss-turn` temporarily as legacy.

---

## 5. Boss Context Builder

### New file to create

`server/services/boss_context_builder.py`

### Input

```python
build_boss_context(session_id: str) -> BossContext
```

### Output

```json
{
  "session_id": "s1",
  "homework_id": "hw1",
  "homework_title": "English Vocabulary Practice",
  "subject": "English",
  "grade": 8,
  "phase_summaries": [
    {
      "phase_index": 1,
      "title": "Vocabulary in context",
      "score": 0.62,
      "weak_topics": ["according_to", "meaning_in_context"],
      "strong_topics": ["basic_translation"]
    }
  ],
  "overall_metrics": {
    "mastery_score": 0.68,
    "accuracy": 0.71,
    "hint_dependency": "medium",
    "avg_attempts": 2.3
  },
  "boss_policy": {
    "target_weak_topics_first": true,
    "avoid_repetition": true,
    "max_question_length": 900,
    "language": "uzbek_or_student_language"
  }
}
```

### Do not include

- full raw transcript
- full 9-phase content
- frontend-provided answer keys
- unsanitized HTML

---

## 6. Boss question generation prompt

### New prompt file

`server/prompts/runtime/boss-question-generator.md`

### Prompt contract

```text
You are the Boss Question Generator for one homework session.
Generate exactly one question.
Use the student's weak topics first.
Do not repeat previous generated questions.
Question must be answerable from the completed homework content and phase summaries.
Return strict JSON only.
```

### Required JSON

```json
{
  "question_text": "...",
  "expected_answer": {
    "canonical": "...",
    "accepted_variants": ["..."],
    "notes": "..."
  },
  "rubric": {
    "full_credit": ["..."],
    "partial_credit": ["..."],
    "common_mistakes": ["..."]
  },
  "target_skill": "meaning_in_context",
  "difficulty": "medium",
  "source_phase_ids": ["phase_3"],
  "why_this_question": "Student struggled with according_to in phase 3."
}
```

### Required backend validation

Reject generated question if:

- missing expected answer
- no rubric
- repeats previous question too closely
- target skill not in homework content/performance summary
- too long
- asks about content not present in homework

---

## 7. Boss answer checker

### New prompt file

`server/prompts/runtime/boss-answer-checker.md`

### Why separate from normal checker?

Boss answers affect game state, HP, difficulty, and final assessment. It needs a stricter contract.

### Required JSON

```json
{
  "is_correct": true,
  "score": 0.92,
  "confidence": 0.88,
  "feedback_to_student": "Correct. You understood the phrase in context.",
  "misconception_tags": [],
  "damage_multiplier": 1.0,
  "difficulty_recommendation": "increase",
  "should_retry_same_skill": false
}
```

### Damage formula

Keep damage calculation in backend, not model.

```python
BASE_DAMAGE = {
    "easy": 10,
    "medium": 15,
    "hard": 25
}

def calculate_damage(score: float, difficulty: str) -> int:
    base = BASE_DAMAGE[difficulty]
    if score >= 0.90:
        return base
    if score >= 0.60:
        return int(base * 0.5)
    return 0
```

The model may recommend a multiplier, but backend must clamp it.

---

## 8. Boss difficulty policy

Backend owns difficulty.

```python
def next_difficulty(state, answer_result):
    if answer_result.score >= 0.90 and state.correct_streak >= 2:
        return "hard"
    if answer_result.score < 0.50 and state.wrong_streak >= 2:
        return "easy"
    return "medium"
```

### Rule

Boss should be challenging, not unfair. Difficulty tracks actual performance.

---

## 9. Frontend runtime changes

### File to modify

`server/template/runtime.js`

### Replace old Boss bridge usage

Current:

```js
NETS_AI.bossTurn(...)
```

Target:

```js
await NETS_AI.bossStart({ session_id, homework_id });
const q = await NETS_AI.bossGenerateQuestion({ boss_session_id });
const result = await NETS_AI.bossSubmitAnswer({ boss_session_id, question_id, student_answer });
```

### Frontend displays

```json
{
  "boss_hp": 70,
  "trials_left": 5,
  "current_question": "...",
  "feedback": "...",
  "damage": 15,
  "difficulty": "medium"
}
```

---

## 10. Boss history / anti-repetition

### Required context

Each generation call should receive:

```json
{
  "asked_questions": [
    {
      "question_id": "bq_1",
      "question_text": "...",
      "target_skill": "...",
      "student_score": 0.4
    }
  ],
  "recent_boss_phrases": ["..."]
}
```

This fixes current prompt-history mismatch.

---

## 11. Acceptance tests

### Test 1 — no static list dependency

A homework with no `content_json.boss_questions` but completed phase metrics should still start Boss and generate a question.

### Test 2 — generated question targets weakness

If weak topic is `according_to`, generated question should test that skill before unrelated skills.

### Test 3 — no repetition

After question 1 asks about `according to`, question 2 should not be a paraphrase of the same question unless previous answer was wrong and retry policy says retry.

### Test 4 — HP controlled by backend

Model cannot set HP directly. Backend calculates HP from score and difficulty.

### Test 5 — Boss state persists after refresh

Reload frontend during Boss mode; `/ai/boss/state` returns same HP, trials, current question.

---

## 12. Migration strategy

### Phase 1

Keep current pre-authored Boss as fallback.

### Phase 2

Add dynamic generated Boss only for homeworks with completed metrics.

### Phase 3

Make dynamic Boss default.

### Phase 4

Remove `tutor-boss-plan.md` dependency or keep it only as optional seed-question planner.

---

## 13. Done definition

Dynamic Boss is complete when:

- Boss starts from session metrics, not only `content_json.boss_questions`
- every Boss question is generated one at a time
- generated questions are stored
- answer checking updates HP/trials/difficulty
- Boss state survives page refresh
- Boss never repeats without policy reason
- final report includes Boss performance

