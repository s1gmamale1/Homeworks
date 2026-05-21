# Choose Correct Explanation — Game Mechanic Specification

**New game. No predecessor spec.**
**Type:** Game (position in flow determined by homework design, not by this spec)
**Audience:** Production team creating homework prompts and content.

---

## 1. What Choose Correct Explanation Is

Choose Correct Explanation is a deep-recognition game. The student is shown a statement, problem, or phenomenon and four **explanation options** — each a 1-2 sentence reasoning. Exactly one explanation is correct. The student picks it.

Unlike Multiple Choice (where options are short — a number, a word, a label), Choose Correct Explanation has **rich options**: each one tries to explain *why* something is the case. This shifts the cognitive event from "which answer matches" to "which reasoning chain is sound." That's Level 2 minimum, leaning toward Level 3 because the student must evaluate competing logic, not just match a label.

Choose Correct Explanation works because the distractors are not wrong answers — they are **flawed reasoning**. Each distractor reflects a real misconception or a partially-correct line of thinking. The student who has surface-learned the concept will be drawn to a distractor; the student who understands will pick the right reasoning.

This mechanic shines for "why" content: why a formula works, why a sentence is grammatical, why a process happens. It's weak for pure recall, vocabulary, or numeric answer questions — use MCQ or Fill in the Blank for those.

---

## 2. When Choose Correct Explanation Fires

Choose Correct Explanation is deployable wherever the homework flow places it. The spec does not pin it to a specific phase.

What Choose Correct Explanation requires to function:

- The underlying concept must have been **taught** earlier in the session (Case-Based Preview, Flashcards, prior task with reasoning shown). The student needs to have seen the correct reasoning chain at least once before being asked to recognize it among distractors.
- A distractor pool of plausible misconceptions for the concept. This is the hardest authoring task in any of the v1 games — distractors must be wrong but not stupid.

This rules out Choose Correct Explanation as a first-exposure mechanic. It also rules out concepts where the student has only seen the *fact*, not the *reasoning*.

Choose Correct Explanation runs as a single task per concept. Streaks of these are exhausting — the cognitive load per task is real. Use 2-4 per session at most, ideally on the most important "why" content of the lesson.

---

## 3. The Student Experience (Flow)

Each Choose Correct Explanation task goes through this loop:

```
1. System presents the statement/problem/phenomenon and 4 explanation options (each 1-2 sentences)
2. Student reads all four (the read time is part of the cognitive event — don't rush)
3. Student taps one option
4. System gives immediate feedback:
   - Correct → strong affirmation, brief reinforcement of what made the correct explanation correct
   - Wrong → "Hali emas." Reveal the correct explanation. Brief note on why the chosen distractor was flawed (the misconception it represents)
5. Optional WHY prompt (recommended for high-stakes tasks): "What part of the correct explanation matters most?"
6. AI evaluates the WHY response against expected key components
7. Task ends, telemetry recorded
```

The student commits to a choice before any reveal. No hint mechanism on the choice itself (same rationale as MCQ — there's nothing to hint without giving the answer).

---

## 4. The Three Subject Patterns

Choose Correct Explanation in v1 covers three patterns. Each has the same loop shape but different reasoning structure.

### Pattern A — Math (why a step or method works)

The student is shown an equation, a step, or a result, and asked to pick the explanation that justifies it.

**Example (Grade 7, equation solving):**

```
Statement: 3x + 5 = 20 simplifies to 3x = 15.

Which explanation is correct?

A) We multiplied both sides by 5.
B) We subtracted 5 from both sides to keep the equation balanced.
C) The 5 disappears because constants don't matter once we have x.
D) We moved the 5 to the right and changed its sign because that's the rule.
```

Correct: B. A is wrong operation. C is a common misconception ("constants don't matter"). D is the right procedure described with magical-thinking reasoning instead of the underlying balance principle — a classic "right answer, wrong understanding" distractor.

WHY prompt enabled: "What makes B the most accurate explanation?" → expected: "the balance principle — equations stay equal when the same operation is applied to both sides."

### Pattern B — Grammar / Text (why a sentence or form is correct)

The student is shown a sentence and asked to pick the explanation for why a particular form is used.

**Example (English, Grade 8, present perfect):**

```
Statement: "She has been to Tashkent three times."

Why is "has been" the correct form here?

A) Because it describes an action that happened in the past.
B) Because it describes a life experience without a specific finished time, and "three times" emphasizes the count, not when.
C) Because "three times" requires present tense in English.
D) Because all sentences with "three" use present perfect.
```

Correct: B. A is partially correct but missing the key — life experience + unfinished time. C and D are invented rules that don't exist in English grammar but sound plausible to a learner.

WHY optional for grammar — the explanation itself already required reasoning.

### Pattern C — Sciences (why a phenomenon happens)

The student is shown a phenomenon and asked to pick the explanation that fits.

**Example (Biology, Grade 8, photosynthesis):**

```
Statement: Plants in a dark room eventually wilt and die, even with water.

Why?

A) The plants need air, which is blocked in dark rooms.
B) Without sunlight, plants cannot perform photosynthesis to make glucose, so they lose energy supply.
C) Plants need warmth from the sun to survive; darkness is too cold.
D) Plants drink water through their leaves, which needs light to work.
```

Correct: B. A is wrong (air not blocked). C is partially related (some plants need warmth) but misses the energy/glucose mechanism. D is invented biology.

WHY enabled (mandatory for science): "What process is missing in the dark room?" → expected: "photosynthesis; plants need light to convert CO₂ and water into glucose for energy."

---

## 5. Adaptation Logic

Choose Correct Explanation adapts at the **task selection** level.

Before launching a task, the system checks upstream session telemetry:

- Which concepts has the student misunderstood (not just got wrong, but chose a flawed reasoning option in a prior task)?
- Which concepts has the student seen the full reasoning for, not just the surface answer?

The system selects a Choose Correct Explanation task from the pool that:

1. Tests one of the student's currently-shaky concepts at the **reasoning level**, not just the answer level
2. Uses a concept whose reasoning has been established upstream
3. Matches the student's current grade band

Choose Correct Explanation is particularly powerful for adapting to a student who consistently picks the right MCQ answer but for the wrong reason. The distractors here expose that.

There is no within-task branching. Every student sees the same task content for the same task ID.

---

## 6. Difficulty by Grade Band

Same task shape across all grades. Difficulty comes from how subtle the distractors are.

| Grade Band | Distractor Quality | Explanation Length | Time Target |
|---|---|---|---|
| G1–4 | One clearly correct, three clearly off | 1 sentence each | 60 seconds |
| G5–8 | One correct, three with common misconceptions | 1-2 sentences each | 90 seconds |
| G9–11 | One correct, distractors include partially-true reasoning | 2 sentences each, more nuanced | 2-3 minutes |

The four explanations should be of **similar length and style** across all grades. This is critical for anti-leak.

---

## 7. Scoring

Choose Correct Explanation uses a 100-point scoring model.

| Criterion | Max Points (no WHY) | Max Points (with WHY) | What It Measures |
|---|---|---|---|
| **Explanation accuracy** | 100 | 70 | Did the student pick the correct reasoning on the first try? |
| **Reasoning depth (WHY prompt)** | — | 30 | Does the explanation of the explanation connect to the core principle? |
| **Total** | **100** | **100** | |

### Penalties and modifiers

| Event | Effect |
|---|---|
| Wrong first choice | Explanation accuracy = 0. WHY (if prompted) can still earn partial credit for showing concept understanding even after wrong pick. |
| WHY answer generic ("because it's right") | WHY = 0 |

No retries. Choose Correct Explanation is one-shot like MCQ. The cognitive event is in the choice itself.

### Pass tiers

| Score | Rating | Feedback Framing |
|---|---|---|
| 85-100 | Deep Understanding | "Aniq tushuntirishni topdingiz va asosini ham bildingiz." |
| 65-84 | Sound Reasoning | "To'g'ri tushuntirish, asosini biroz aniqlash kerak edi." |
| 30-64 | Surface Reasoning | "Javob to'g'ri emas. Tanlagan tushuntirishingiz noto'g'ri tushunchadan kelib chiqadi." |
| Below 30 | Hali emas | "Hali emas. To'g'ri tushuntirish: [X]. Tanlagan variantingiz [misconception] ni aks ettiradi." |

---

## 8. Hint Behavior

**No hint on the choice itself.** Same rationale as MCQ — a hint that narrows four explanations is either useless or revealing.

If WHY is enabled and the student's explanation is thin, the system may offer one hint after evaluation:

> "Your explanation of why B is correct is incomplete. Hint: think about *why* the other options are wrong. That often reveals what makes the right one right."

Hint cost: WHY score × 0.7 if the student retries the explanation.

---

## 9. Mistake Repair Signal

If the student got concept X wrong earlier in the session (in any game) and correctly picks the right explanation on a Choose Correct Explanation task involving concept X, that counts as a **mistake repair** event.

Choose Correct Explanation produces **medium-to-strong repair signal**. Stronger than MCQ because the student had to evaluate competing reasoning chains. Weaker than Fill in the Blank or Error Detection because production beats recognition.

The strongest repair signal comes from a student who:
1. Got a previous task wrong because they picked a flawed-reasoning distractor here
2. Then on a later Choose Correct Explanation task on the same concept, picks the correct reasoning

That pattern shows the misconception was specifically dislodged, not bypassed.

Repair signal feeds downstream session components for adaptation and Reflection narrative.

---

## 10. What the Production Team Outputs Per Task

Each Choose Correct Explanation task in the homework JSON should include:

```json
{
  "task_id": "cce_bio_g8_002",
  "pattern": "science_phenomenon",
  "concept_tag": "photosynthesis_energy_dependency",
  "grade_band": "G5-8",
  "difficulty": "medium",
  "statement": "Plants in a dark room eventually wilt and die, even with water.",
  "question": "Why?",
  "options": [
    {
      "id": "A",
      "explanation": "The plants need air, which is blocked in dark rooms.",
      "is_correct": false,
      "misconception": "Conflates light with air"
    },
    {
      "id": "B",
      "explanation": "Without sunlight, plants cannot perform photosynthesis to make glucose, so they lose energy supply.",
      "is_correct": true
    },
    {
      "id": "C",
      "explanation": "Plants need warmth from the sun to survive; darkness is too cold.",
      "is_correct": false,
      "misconception": "Partial truth (warmth matters) but misses the actual photosynthesis mechanism"
    },
    {
      "id": "D",
      "explanation": "Plants drink water through their leaves, which needs light to work.",
      "is_correct": false,
      "misconception": "Invented biology that conflates roots/leaves and light/water"
    }
  ],
  "why_prompt_enabled": true,
  "why_prompt": "What process is missing in the dark room?",
  "expected_reasoning_keywords": ["photosynthesis", "glucose", "energy", "sunlight", "CO2"],
  "correct_feedback": "Aniq. Fotosintez yorug'lik energiyasidan foydalanib glyukoza hosil qiladi.",
  "wrong_feedback_template": "Hali emas. To'g'ri javob: B. Sizning tanlagan variantingiz {misconception} ni aks ettiradi.",
  "supports_visual": false
}
```

For Pattern A math, optionally include an `equation_svg` showing the step being explained. For Pattern C sciences, optionally include a `diagram_svg`.

The minimum pool size is **6 tasks per concept tag per grade band**. Lower than MCQ because Choose Correct Explanation tasks are dense and used less frequently per session.

---

## 11. What NOT to Do

These are forbidden in Choose Correct Explanation:

- **First-exposure tasks.** The reasoning must have been taught earlier in the session.
- **Distractors that are obviously wrong.** "Plants need air, which is blocked in dark rooms" works as a distractor because the conflation of light and air is a real misconception. "Plants are angry at the dark" doesn't work — no student is choosing that.
- **Distractors of different length / style than the correct option.** If the correct explanation is two sentences and the three distractors are one sentence, you've leaked the answer. All four must read in the same register and at similar length.
- **Distractors that are also correct.** "Plants need warmth from the sun" is technically true for some species, but it's not *the* answer to why dark-room plants die. Distractors should be wrong specifically for the question asked — not wrong in general, but not the right reasoning for this case.
- **More than 4 options.** Four is the locked standard. Cognitive load with rich-text options gets brutal beyond four.
- **Three or fewer options.** Three is too easy. The cognitive event needs the resistance of multiple plausible-looking explanations.
- **Pure-recall content.** "What is the formula for water?" doesn't belong here. Use MCQ. Choose Correct Explanation is for "why" content.
- **Speed multipliers.** Reading four explanations carefully is the work. Speed pressure pushes students into pattern-matching the keywords instead of evaluating reasoning.
- **WHY prompt disabled for science questions.** Recommended per the interactivity standard, mandatory for high-stakes Choose Correct Explanation tasks.
- **Vocabulary-flavored distractors.** Distractors must differ in the **reasoning**, not in the **terminology**. "Photosynthesis" vs "Glucose synthesis" vs "Photogeneration" is a vocabulary trick, not a reasoning test.

---

## 12. Success Criteria

Choose Correct Explanation is working correctly when:

- Every task has exactly one correct explanation and three flawed-reasoning distractors
- Each distractor reflects a real misconception, tagged in the JSON
- The Strip Test passes — remove the subject content and the task is just "pick one of four similar paragraphs"
- Anti-leak rules hold: all four options are similar in length, style, and register
- AI WHY evaluation is reading explanations and giving substantive feedback
- WHY prompt fires for science tasks and high-stakes math reasoning
- Mistake repair signal is treated as medium-to-strong
- Tasks selected by adaptation logic prioritize concepts where the student has shown surface-correct-but-reasoning-flawed behavior
- Distractors differ in reasoning logic, not in vocabulary

If any of these fail, the task pool or evaluation logic needs review before that homework ships.
