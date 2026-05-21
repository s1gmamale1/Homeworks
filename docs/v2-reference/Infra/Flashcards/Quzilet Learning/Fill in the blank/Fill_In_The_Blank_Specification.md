# Fill in the Blank — Game Mechanic Specification

**New game. No predecessor spec.**
**Type:** Game (position in flow determined by homework design, not by this spec)
**Audience:** Production team creating homework prompts and content.

---

## 1. What Fill in the Blank Is

Fill in the Blank is a targeted production game. The student is shown content with one to three specific words, numbers, or symbols missing — marked with `_____` — and must type the missing content.

Unlike Multiple Choice (which is recognition), Fill in the Blank forces **production**. The student doesn't pick from options; they retrieve from memory. That makes Fill in the Blank a Level 3 event under the interactivity standard (Corrective when the student gets it wrong and the system shows the answer; Generative at its strongest because the student is actively constructing the missing piece).

The blank is the learning target. Not a function word, not a connector, not a punctuation mark — the blank is the **concept-bearing word**. If you blank out "the" instead of "photosynthesis," you've built a typing test, not a learning event.

Fill in the Blank pairs well with concepts where exact production matters: vocabulary, formulas, conjugations, dates, key terms, specific operations. It's less useful for open conceptual understanding (Short Answer fits better there).

---

## 2. When Fill in the Blank Fires

Fill in the Blank is deployable wherever the homework flow places it. The spec does not pin it to a specific phase.

What Fill in the Blank requires to function:

- The concept being tested must have appeared at least once earlier in the session in **complete form**. Without exposure to the unblanked version, the student is guessing.
- An accepted-variations list per task. Without this, the AI will reject valid answers with minor formatting differences.

This rules out Fill in the Blank as a first-exposure mechanic.

Fill in the Blank can run as a single task or in a streak (3-5 questions targeting one concept cluster). It works well after a teaching moment or as a coverage check after Flashcards / Memory Check.

---

## 3. The Student Experience (Flow)

Each Fill in the Blank task goes through this loop:

```
1. System presents the content with blank(s) marked as _____
2. Student types into the blank(s)
3. Student submits
4. AI normalizes the input (case, whitespace, diacritics per task config) and evaluates against expected + accepted variations
5. If correct → strong feedback, score awarded
6. If wrong → one hint offered (the hint tells the type/shape of the answer, not the answer)
7. Student retries (one retry only)
8. If still wrong → system reveals correct answer, reduced score
9. Optional WHY prompt (mandatory for math/science where the blank tests a concept, not just spelling): "Why does this word/number/symbol fit?"
10. Task ends, telemetry recorded
```

The student commits to a typed answer before the system reveals anything. No auto-reveal until after the second wrong attempt.

---

## 4. The Three Subject Patterns

Fill in the Blank in v1 covers three patterns. Each has the same loop shape but different blank-design rules.

### Pattern A — Math (numerical / formula blank)

The blank is a number, variable, or operator inside a worked equation. The surrounding equation is shown so the student can see the structure.

**Example (Grade 7, linear equation):**

```
Solve: 3x + 5 = 20

Step 1: 3x = 20 - _____
Step 2: 3x = 15
Step 3: x = _____
```

Blanks: `5` and `5`. (Yes, both are 5 — but at different positions in the reasoning. The first is the constant being moved across the equals sign; the second is the division result.)

Acceptable variations: `5`, `5.0`. Reject anything else.

WHY enabled (mandatory for math): "Why does 5 appear in both blanks?" → expected reasoning: "the constant 5 is subtracted from both sides; then 15 ÷ 3 happens to also equal 5."

### Pattern B — Grammar / Text (word in a sentence)

The blank is a specific word (verb form, preposition, vocabulary item) inside a complete sentence. The sentence context must be sufficient to determine the right word.

**Example (English, Grade 6, past simple):**

```
She _____ to Tashkent last summer.
```

Blank: `went` (past simple of "go").

Acceptable variations: `went`, `Went`. Reject `goes`, `gone`, `going`.

WHY optional for grammar mechanical fill — usually skip.

For vocabulary cards specifically, the blank is the target word and the sentence shows it in context:

```
The process plants use to make food using sunlight is called _____.
```

Blank: `photosynthesis`. Acceptable variations: `photosynthesis`, `Photosynthesis`. Reject misspellings (the point of the blank is exact spelling).

### Pattern C — Sciences (term in a mechanism description)

The blank is a key term inside a sentence describing a process or mechanism. Surrounding context defines the concept; the blank is the term that names it.

**Example (Biology, Grade 8, cellular respiration):**

```
The _____ release energy in the form of ATP through cellular respiration.
```

Blank: `mitochondria`. Acceptable variations: `mitochondria`, `Mitochondria`, `mitochondrion` (singular form acceptable in some contexts — production team decides).

WHY enabled (mandatory for science): "Why are mitochondria the right answer here?" → expected reasoning: "they are the site of cellular respiration and produce ATP."

---

## 5. Adaptation Logic

Fill in the Blank adapts at the **task selection** level.

Before launching a task, the system checks upstream session telemetry:

- Which concepts has the student been shaky on this session?
- Which key terms has the student seen in complete form earlier?

The system selects a Fill in the Blank task from the pool that:

1. Tests one of the student's currently-shaky concepts (when possible)
2. Targets a term/number/form that appeared upstream in correct context
3. Matches the student's current grade band

If the student got concept X wrong in an earlier task (any game), and a Fill in the Blank task on concept X exists in the pool, prioritize it. Production-typing is one of the strongest repair mechanics.

There is no within-task branching. Every student sees the same task content for the same task ID.

---

## 6. Difficulty by Grade Band

Same task shape across all grades. Difficulty comes from blank specificity, surrounding context, and number of blanks.

| Grade Band | Number of Blanks per Task | Context Length | Time Target |
|---|---|---|---|
| G1–4 | 1 | Short sentence | 60 seconds |
| G5–8 | 1–2 | Sentence with 1-2 supporting lines | 90 seconds |
| G9–11 | 1–3 | Paragraph or multi-step equation | 2 minutes |

The blanks must always test the **same concept cluster** — don't blank a math term, a grammar term, and a date in the same task.

---

## 7. Scoring

Fill in the Blank uses a 100-point scoring model.

| Criterion | Max Points (no WHY) | Max Points (with WHY) | What It Measures |
|---|---|---|---|
| **Production accuracy** | 100 | 75 | Is the typed answer substantively right? |
| **Reasoning (WHY prompt)** | — | 25 | Does the explanation connect to the underlying concept? |
| **Total** | **100** | **100** | |

For multi-blank tasks: production accuracy is averaged across blanks. A 2-blank task with one right and one wrong = 50 production accuracy.

### Penalties and modifiers

| Event | Effect |
|---|---|
| Near-miss (edit distance 1, e.g., spelling error) | Counts as wrong but offers a retry without hint penalty |
| Hint used | Production accuracy × 0.7 |
| Reveal triggered (still wrong after hint + retry) | Production accuracy = 0, partial credit for WHY if attempted |
| WHY explanation generic | WHY = 0 |

Near-miss handling matters: a student who types "photosythesis" knows the concept and made a typo. Letting them fix it without full penalty preserves the learning signal.

### Pass tiers

| Score | Rating | Feedback Framing |
|---|---|---|
| 85-100 | Sharp Production | "Aniq yozdingiz va sababini ham tushundingiz." |
| 65-84 | Good Recall | "To'g'ri javob, kichik tuzatish yoki tushuntirish kerak edi." |
| 40-64 | Half Production | "Tushunchani bildingiz, lekin aniq yoza olmadingiz." |
| Below 40 | Hali emas | "Hali emas. To'g'ri javob: [X]. Sababi: [...]" |

---

## 8. Hint Behavior

One hint allowed per task. The hint follows the same rule as Error Detection and Boss: **never reveals the answer**.

The hint tells the student about the **shape** of the answer — what type of word, what category, what form — without giving the word itself.

**Math example (blank wrong):**
> Hint: "Look at the equation `3x + 5 = 20`. To isolate `3x`, you need to remove the 5. What operation undoes addition?"

**Grammar example (blank wrong):**
> Hint: "The action happened last year and is finished. What tense does English use for completed past actions?"

**Science example (blank wrong):**
> Hint: "This organelle is found in animal cells and converts glucose to energy. Think about which organelle is famous for ATP."

Hint cost: production accuracy × 0.7. Hints do not reset the blank or change the task.

---

## 9. Mistake Repair Signal

If the student got concept X wrong earlier in the session (in any game) and successfully produces the correct answer on a Fill in the Blank task involving concept X, that counts as a **mistake repair** event.

Fill in the Blank produces **strong repair signal** because production beats recognition. A student who can type the right answer has retrieved it from memory, not picked it from a list.

Production team should leverage this when authoring tasks: the blank should target exactly the concept the student commonly gets wrong, with surrounding context that nudges toward the right answer without giving it.

Repair signal feeds downstream session components for adaptation and Reflection narrative.

---

## 10. What the Production Team Outputs Per Task

Each Fill in the Blank task in the homework JSON should include:

```json
{
  "task_id": "fitb_bio_g8_004",
  "pattern": "science_term",
  "concept_tag": "mitochondria_cellular_respiration",
  "grade_band": "G5-8",
  "difficulty": "medium",
  "content": "The _____ release energy in the form of ATP through cellular respiration.",
  "blanks": [
    {
      "id": "b1",
      "expected_answer": "mitochondria",
      "accepted_variations": ["Mitochondria", "mitochondrion"],
      "case_sensitive": false,
      "diacritic_sensitive": false,
      "near_miss_tolerance": 1
    }
  ],
  "common_mistake_pattern": "Students confuse with chloroplasts (plant cells) or ribosomes (protein synthesis)",
  "hint": "This organelle is found in animal cells and converts glucose to energy. Think about which is famous for ATP.",
  "why_prompt": "Why are mitochondria the correct answer here?",
  "expected_reasoning_keywords": ["cellular respiration", "ATP", "energy", "glucose"],
  "correct_feedback": "To'g'ri. Mitokondriylar — hujayralarning energiya ishlab chiqarish markazlari.",
  "wrong_feedback_template": "Hali emas. To'g'ri javob: 'mitochondria'. Sabab: bu organella hujayra nafas olishi orqali energiya hosil qiladi.",
  "supports_visual": false
}
```

For Pattern A math with worked equations, include `"supports_visual": true` and add a `equation_svg` field showing the work with the blank highlighted. For Pattern C sciences with diagrams, optionally include `diagram_svg`.

The minimum pool size is **10 tasks per concept tag per grade band**. Higher than Error Detection because Fill in the Blank tasks are smaller and reused; adaptation needs variants.

---

## 11. What NOT to Do

These are forbidden in Fill in the Blank:

- **First-exposure tasks.** If the concept has not appeared in correct form earlier in the session, Fill in the Blank cannot run.
- **Blanking function words.** `_____ photosynthesis is the process plants use` (blanking "Photosynthesis," "is," "the," or "process" produces a typing test, not a learning event). Blank the concept-bearing word: `The process plants use to make food is called _____.`
- **Ambiguous blanks.** If the surrounding context allows two or more correct fills, the task is broken. `She _____ to Tashkent` could be `went`, `flew`, `drove`, `traveled`. Either constrain context (`She _____ to Tashkent last summer by train`) or specify all acceptable variations.
- **Exact-character match without normalization.** Reject `mitochondria` because the student wrote `Mitochondria` is failure. Use case-insensitive matching, whitespace normalization, and diacritic handling unless those are explicitly the target.
- **Treating edit-distance-1 as fully wrong.** A student who typed `photosythesis` knows the concept. Offer a retry without hint penalty.
- **Any-string-accepted blanks.** The opposite failure. The AI must check substantive correctness, not just non-empty input.
- **Speed multipliers.** Production is reasoning, not speed.
- **Multiple blanks targeting different concepts.** Don't blank a vocabulary word and a math number in the same task — adapt logic gets muddled.
- **More than 3 blanks per task in v1.** Cognitive overload. Multi-blank tasks are powerful but should stay focused.
- **Reveal of answer before hint + retry.** The student gets: one attempt → hint → one retry → then reveal. No earlier shortcut.
- **WHY prompt skipped for math/science where the blank tests a concept.** Mandatory per the interactivity standard. Optional only for pure spelling/vocabulary blanks.

---

## 12. Success Criteria

Fill in the Blank is working correctly when:

- Every task blanks a concept-bearing word, number, or symbol — never a function word
- The Strip Test passes — remove the subject content and the task is just "type something into an underscore"
- AI normalization handles case, whitespace, diacritics, and near-misses correctly
- Acceptable variations cover legitimate alternative forms without over-broadening
- WHY prompt fires for math/science conceptual blanks
- Mistake repair signal from Fill in the Blank is treated as strong (production beats recognition)
- Tasks selected by adaptation logic match the student's currently-shaky concepts where possible
- No two Fill in the Blank tasks on the same concept use identical surrounding context

If any of these fail, the task pool or evaluation logic needs review before that homework ships.
