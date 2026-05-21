# Multiple Choice — Game Mechanic Specification

**New game. No predecessor spec.**
**Type:** Game (position in flow determined by homework design, not by this spec)
**Audience:** Production team creating homework prompts and content.

---

## 1. What Multiple Choice Is

Multiple Choice (MCQ) is a recognition game. The student is shown a question and 4 options. Exactly one option is correct. The student picks the correct one.

Recognition is the lowest cognitive event the homework engine accepts as a real practice mechanic — Level 2 under the interactivity standard (Constructive: answer + feedback). At Level 2 alone, MCQ is a thin task. It earns its place by being **fast, low-friction, and high-coverage**: you can test many concepts in a short window, which makes MCQ the workhorse of session warm-up, mid-session coverage checks, and breadth-of-recall confirmation.

MCQ works because of distractor quality. A good MCQ is **not** "one obvious answer and three jokes." A good MCQ has three options that are plausibly tempting for a student who half-learned the material, and one option that is correct for a student who actually learned it. The cognitive event lives in resisting the wrong-but-tempting distractors.

When MCQ is paired with a mandatory WHY prompt ("Why did you choose this?"), it bumps to Level 3-4. Without WHY, it stays Level 2. The spec supports both modes.

---

## 2. When Multiple Choice Fires

MCQ is deployable wherever the homework flow places it. The spec does not pin it to a specific phase.

What MCQ requires to function:

- A concept pool from the lesson with at least one correct expression of each tested concept somewhere earlier in the session (Case-Based Preview, Flashcards, prior task) — same reference-point rule as Error Detection.
- A distractor pool: plausible wrong answers drawn from related concepts, common mistakes, or look-alike terms.

This rules out MCQ as a first-exposure mechanic. If the student has never seen the correct concept, MCQ becomes guessing.

MCQ can run multiple times per session — typically 3-8 questions in a row when used as a coverage check, or interspersed between deeper tasks for variety.

---

## 3. The Student Experience (Flow)

Each MCQ task goes through this loop:

```
1. System presents the question and 4 options
2. Student taps one option
3. System gives immediate feedback:
   - Correct → strong affirmation, brief explanation, score awarded
   - Wrong → "Hali emas." Reveal the correct option, brief explanation of why correct, why distractor was wrong
4. Optional WHY prompt (configurable per task): "Why is this the right answer?"
5. AI evaluates the WHY response against expected reasoning components
6. Task ends, telemetry recorded
```

If WHY is enabled, the student commits to their option before being asked to justify it. The system does not auto-reveal until after both the choice and (if WHY enabled) the justification are submitted.

No hint mechanism in standard MCQ — there's nothing meaningful for a hint to reveal that isn't the answer. Hints exist only on the WHY prompt if enabled (see §8).

---

## 4. The Three Subject Patterns

MCQ in v1 covers three patterns. Each has the same loop shape (Section 3) but different content structure.

### Pattern A — Math (numerical / formula)

The question asks for a numerical answer, a formula, or which step is correct. Options are short — numbers, expressions, or single equations.

**Example (Grade 6, fractions):**

```
What is 3/5 ÷ 3?

A) 9/5
B) 1/5
C) 3/15
D) 6/5
```

Correct: B. Distractor A is the result of multiplying instead of dividing (a common mistake). C is mechanically dividing both top and bottom by 3 wrongly. D is adding instead of dividing.

If WHY is enabled: "Why is B correct?" → expected reasoning: "dividing a fraction by a whole number multiplies the denominator."

### Pattern B — Grammar / Text (sentence / form)

The question asks which sentence is correct, which form fits the context, or which word is the right choice. Options are short sentences or single forms.

**Example (English, Grade 6, past simple vs present perfect):**

```
She _____ to Tashkent three times last year.

A) has been
B) have been
C) went
D) goes
```

Correct: C. A and B are present perfect (which doesn't combine with "last year"). D is present tense.

If WHY is optional for grammar mechanical fixes (matches Error Detection rule). If enabled: "Why is C the right form?" → expected: "completed action in a finished time period."

### Pattern C — Sciences (mechanism / classification)

The question asks which mechanism explains a phenomenon, which classification fits, or which prediction follows from a setup. Options are short phrases or mechanism names.

**Example (Biology, Grade 7, photosynthesis):**

```
Which organelle is the energy producer of the animal cell?

A) Chloroplast
B) Vacuole
C) Mitochondria
D) Ribosome
```

Correct: C. A is the energy producer of plant cells (specifically photosynthesis, not the same role). B is storage. D is protein synthesis.

WHY enabled for science (per interactivity standard): "Why is C correct?" → expected reasoning: "mitochondria release energy through cellular respiration."

---

## 5. Adaptation Logic

MCQ adapts at the **task selection** level, same as Error Detection.

Before launching a question, the system checks upstream session telemetry:

- Which concepts has the student been shaky on this session?
- Which concepts have appeared in correct form earlier so a recognition test is meaningful?

The system selects an MCQ task from the pool that:

1. Tests one of the student's currently-shaky concepts (when possible)
2. Uses a concept already established upstream in correct form
3. Matches the student's current grade band
4. Avoids repeating the exact same MCQ in the same session (rotate variants)

If a student got concept X wrong on an earlier MCQ, the next MCQ on concept X should use **different distractors** so the student isn't just memorizing the option position.

There is no within-task branching. Every student sees the same question content for the same task ID.

---

## 6. Difficulty by Grade Band

Same task shape across all grades. Difficulty comes from concept depth and distractor subtlety.

| Grade Band | Distractor Subtlety | Question Length | Time Target |
|---|---|---|---|
| G1–4 | Clear correct vs clear wrong | 1 line | 20 sec |
| G5–8 | Common-mistake distractors | 1-2 lines | 30 sec |
| G9–11 | Near-miss distractors, requires reasoning to resolve | 2-3 lines, may include short context | 45 sec |

Number of options stays at 4 across all grades. Three is too easy, five is option-overload.

---

## 7. Scoring

MCQ uses a 100-point scoring model.

| Criterion | Max Points (no WHY) | Max Points (with WHY) | What It Measures |
|---|---|---|---|
| **Choice accuracy** | 100 | 70 | Did the student pick the right option on the first try? |
| **Reasoning (WHY prompt)** | — | 30 | Does the explanation connect to the underlying concept? |
| **Total** | **100** | **100** | |

### Penalties and modifiers

| Event | Effect |
|---|---|
| Wrong first choice | Choice accuracy = 0; partial credit for WHY if the explanation shows the student knows the concept |
| WHY explanation generic ("because it's right") | WHY = 0, but doesn't penalize the choice score |

There is no retry on the choice itself — MCQ is one-shot. The student commits, sees the answer, learns from feedback. This is intentional: MCQ is high-coverage, low-depth. Retries belong to deeper mechanics.

### Pass tiers

| Score | Rating | Feedback Framing |
|---|---|---|
| 85-100 | Sharp | "To'g'ri javob, va sababini ham aniq tushuntirdingiz." |
| 65-84 | Good | "To'g'ri tanladingiz. Sababini biroz aniqroq tushuntirsa bo'lardi." |
| 30-64 | Half | "Javob to'g'ri emas, lekin tushunchangiz qisman ko'rinadi." |
| Below 30 | Hali emas | "Hali emas. To'g'ri javob: [X]. Sababi: [...]" |

---

## 8. Hint Behavior

**No hint on the choice itself.** MCQ is one-shot recognition. A hint that narrows the four options would either give the answer away or be useless.

If WHY is enabled and the student writes a poor explanation, the system may offer one hint **after** evaluation:

> "Your answer is correct, but your reasoning was thin. Hint: think about what makes the wrong options wrong, not just what makes the right option right."

Hint cost: WHY score × 0.7 if the student retries the explanation. The student is not required to retry — they can accept the partial WHY score and move on.

---

## 9. Mistake Repair Signal

If the student got concept X wrong earlier in the session (in any game) and answers an MCQ on concept X correctly, that counts as a **mistake repair** event — but with a caveat.

MCQ-based repair is **weaker signal** than Error Detection or Fill-in-the-Blank repair, because the student might have guessed correctly. To strengthen the signal:

- A correct MCQ + correct WHY explanation = strong repair signal
- A correct MCQ alone = weak repair signal (counted but flagged)
- Two consecutive correct MCQs on the same concept = stronger repair signal than one

Production team should not over-weight MCQ repair when designing session adaptation. Use MCQ to confirm understanding, not to certify mastery.

Repair signal feeds downstream session components for adaptation and Reflection narrative.

---

## 10. What the Production Team Outputs Per Task

Each MCQ task in the homework JSON should include:

```json
{
  "task_id": "mcq_math_g6_007",
  "pattern": "math_numerical",
  "concept_tag": "fraction_division_by_whole",
  "grade_band": "G5-8",
  "difficulty": "medium",
  "question": "What is 3/5 ÷ 3?",
  "options": [
    {"id": "A", "content": "9/5",  "is_correct": false, "distractor_reason": "multiplied instead of divided"},
    {"id": "B", "content": "1/5",  "is_correct": true},
    {"id": "C", "content": "3/15", "is_correct": false, "distractor_reason": "divided both top and bottom by 3"},
    {"id": "D", "content": "6/5",  "is_correct": false, "distractor_reason": "added instead of divided"}
  ],
  "why_prompt_enabled": true,
  "why_prompt": "Why is this the correct answer?",
  "expected_reasoning_keywords": ["denominator", "multiply", "whole number", "denominator increases"],
  "correct_feedback": "To'g'ri. 3/5 ÷ 3 = 3/(5·3) = 1/5. Kasrni butun songa bo'lganda maxraj ko'payadi.",
  "wrong_feedback_template": "Hali emas. To'g'ri javob: B (1/5). [distractor_reason] xato yo'l.",
  "supports_visual": false
}
```

For Pattern C (sciences) with a diagram, add a `diagram_svg` field. For Pattern A math with geometric figures, also add `diagram_svg`.

The minimum pool size is **12 MCQs per concept tag per grade band**. Higher than Error Detection because MCQ tasks are smaller and used more frequently — adaptation needs more variants to avoid repetition.

---

## 11. What NOT to Do

These are forbidden in MCQ:

- **First-exposure questions.** If the concept has not appeared in correct form earlier in the session, MCQ cannot run.
- **Joke distractors.** Three obviously-wrong options and one correct one fails the Strip Test — the cognitive event collapses to "pick the one that looks like a real answer." All three distractors must be plausible to a half-learned student.
- **Anti-leak violations.** The correct option must not be longer / shorter / more formal / differently formatted than the distractors. If only one option ends with a period, only one option is capitalized, or only one option uses formal register, you've leaked the answer through style.
- **Two correct options.** Exactly one correct answer per MCQ. "Pick all that apply" is a different mechanic and not in v1.
- **More or fewer than 4 options.** Three is too easy, five is overload. Four is the locked standard.
- **Retries.** MCQ is one-shot. Retry-on-MCQ would just teach the student to remember the option position.
- **Hint on the choice.** Hints have nothing meaningful to reveal without giving the answer.
- **Speed multipliers.** MCQ already favors speed over depth; a multiplier on top would push students into guessing.
- **Questions outside the lesson content.** Every MCQ must come from concepts established in the session.
- **Distractors that are real correct answers to a different but related question.** If "Mitochondria" is the right answer for "energy producer of animal cell" but also for "where ATP is made," using "ATP production" as a distractor is technically a correct answer in another framing. Avoid this — pick distractors that are unambiguously wrong for the specific question asked.
- **WHY prompt disabled for science questions.** Mandatory for science per the interactivity standard. Optional for math/grammar mechanical recognition.

---

## 12. Success Criteria

MCQ is working correctly when:

- Every task has exactly one correct option and three plausible distractors
- The Strip Test passes — distractors must be derived from real concept-space, not random
- Anti-leak rules hold: no option is identifiable as correct by formatting/length/register alone
- AI WHY evaluation is reading explanations and giving substantive feedback (not just keyword match)
- WHY prompt fires for science tasks
- Mistake repair counts from MCQ are flagged as weaker signal than corrective-mechanic repair
- Tasks selected by adaptation logic match the student's currently-shaky concepts where possible
- Repeated MCQs on the same concept use different distractor sets

If any of these fail, the task pool or evaluation logic needs review before that homework ships.
