# Error Detection — Game Mechanic Specification

**New game. No predecessor spec.**
**Type:** Game (position in flow determined by homework design, not by this spec)
**Audience:** Production team creating homework prompts and content.

---

## 1. What Error Detection Is

Error Detection is a recognition-plus-construction game. The student is shown work that contains exactly one error — a broken equation step, a wrong word in a sentence, a mislabeled diagram — and must:

1. **Find** the broken piece
2. **Type** the correct version themselves

The system does **not** auto-reveal the correct answer when the student finds the error. The student must produce the correction. That's the load-bearing cognitive event.

Error Detection works because spotting a wrong path is half of learning, and producing the right path is the other half. Combined into one task, it's a Level 3-4 cognitive event under the interactivity standard — Corrective minimum, Generative when the correction requires real construction.

---

## 2. When Error Detection Fires

Error Detection is deployable wherever the homework flow places it. The spec does not pin it to a specific phase.

What Error Detection requires to function:

- The concept being tested must have appeared at least once earlier in the session in **correct form**. The student needs a reference point — otherwise they can't tell broken from intact.
- A connected concept pool that matches the session's lesson content.

This rules out Error Detection as a first-exposure game. It tests recognition of broken vs intact and the ability to produce the intact version. Different games (Case-Based Preview, Memory Check) build initial knowledge.

Error Detection can run once or multiple times in a session depending on flow design. Each run is one task.

---

## 3. The Student Experience (Flow)

Each Error Detection task goes through this loop:

```
1. System presents the work — equation, sentence, or diagram
2. Student taps the block / word / label they believe is wrong
3. System gives immediate spot feedback:
   - Correct spot → continue to step 4
   - Wrong spot → "That part is correct. Look again." Small score penalty. Try again.
4. System asks: "What should this be?" — student types the correction
5. AI evaluates the typed correction against expected content
6. If correct → strong feedback, score awarded
7. If wrong → one hint offered. Student retries.
8. If still wrong → system reveals correct version, reduced score
9. Optional WHY prompt (mandatory for math/science): "Why was the original wrong?"
10. Task ends, telemetry recorded
```

The student commits to a typed correction before the system reveals anything. No auto-reveal at any step until the second wrong attempt.

---

## 4. The Three Subject Patterns

Error Detection in v1 covers three patterns. Each pattern has the same loop shape (Section 3) but different content structure.

### Pattern A — Math (block-based equation)

The work is broken into blocks. Each block is one step of the equation. One block contains the error.

**Example (Grade 7, linear equation):**

```
Block 1:  3x + 5 = 11
Block 2:  3x = 11 - 5
Block 3:  3x = 16          ← broken
Block 4:  x = 16/3
```

Student taps Block 3.
System: "What should Block 3 be?"
Student types: `3x = 6`
System evaluates → correct → asks WHY → "Why was the original wrong?"
Student types: "11 - 5 is 6, not 16."

### Pattern B — Grammar / Text (block-based sentence)

The sentence is broken into semantic blocks (clauses, phrases). One block contains the error.

**Example (English, Grade 6):**

```
[She][have been][to Tashkent][three times][last year]
```

Student taps `[have been]`.
System: "What should this be?"
Student types: `went`
System evaluates → correct.
(WHY prompt is optional for grammar/text mechanical fixes.)

For English specifically, the error must be a grammar pattern the student has been taught — not a vocabulary trick, not an idiom they wouldn't know.

### Pattern C — Science Diagrams (mislabeled label)

A diagram is shown with all parts labeled. One label is wrong.

**Example (Biology, Grade 8 — plant cell):**

```
[Cell wall]   [Nucleus]   [Mitochondria → "Photosynthesis"]   [Vacuole]
```

Student taps `Mitochondria → "Photosynthesis"`.
System: "What does this organelle actually do?"
Student types: `Energy production / ATP`
System evaluates → correct → asks WHY → "Why is photosynthesis the wrong label here?"
Student types: "Photosynthesis happens in chloroplasts, not mitochondria."

---

## 5. Adaptation Logic

Error Detection adapts at the **task selection** level.

Before launching the game, the system checks upstream session telemetry:

- Which concepts has the student been shaky on this session?
- Which concept did the student just learn correctly upstream (so a broken version makes a productive recognition test)?

The system selects an Error Detection task from the pool that:

1. Tests one of the student's currently-shaky concepts (when possible)
2. Uses a concept that appeared upstream in correct form earlier in the session
3. Matches the student's current grade band

If no upstream telemetry exists, the system picks a task at the student's grade-band default difficulty.

There is no within-task branching. Every student sees the same task content for the same task ID.

---

## 6. Difficulty by Grade Band

Same task shape across all grades. Difficulty comes from the content, not from removing requirements.

| Grade Band | Equation Steps (Pattern A) | Sentence Blocks (Pattern B) | Diagram Labels (Pattern C) | Time Target |
|---|---|---|---|---|
| G1–4 | 3 blocks | 3–4 blocks | 4 labels | 90 seconds |
| G5–8 | 4–5 blocks | 4–5 blocks | 5–6 labels | 2 minutes |
| G9–11 | 5–6 blocks | 5–6 blocks | 6–8 labels | 2–3 minutes |

One error per task across all grades. The error is genuinely subtle, not obviously wrong on first glance.

---

## 7. Scoring

Error Detection uses a 100-point scoring model. Different shape from Real-Life Challenge because the cognitive event is narrower (one task, two student actions).

| Criterion | Max Points | What It Measures |
|---|---|---|
| **Spot accuracy** | 30 | Did the student tap the right block on the first try? |
| **Correction accuracy** | 50 | Is the typed correction substantively right? |
| **Reasoning (WHY prompt)** | 20 | For math/science: does the explanation connect to the underlying concept? |
| **Total** | **100** | |

For grammar/text without WHY prompt: the 20 reasoning points fold into Correction accuracy (60 max), keeping the 100 total.

### Penalties and modifiers

| Event | Effect |
|---|---|
| Wrong first spot | -5 points per wrong spot, max 3 wrong spots before forced reveal |
| Hint used on correction | Correction accuracy × 0.7 |
| Reveal triggered (still wrong after hint + retry) | Correction accuracy = 0, partial credit for WHY if attempted |

### Pass tiers

| Score | Rating | Feedback Framing |
|---|---|---|
| 85-100 | Sharp Eye | "Aniq topdingiz va to'g'rilashni o'zingiz qildingiz." |
| 65-84 | Good Detective | "Xatoni topdingiz, lekin to'g'rilashda biroz qiyinchilik bo'ldi." |
| 40-64 | Half-Found | "Xatoni topdingiz, ammo to'g'ri javobni mustaqil yoza olmadingiz." |
| Below 40 | Hali emas | "Hali emas. Bu kontseptsiyani qayta ko'rib chiqamiz." |

---

## 8. Hint Behavior

One hint allowed per task. The hint follows the same rule as Boss and Why Chain: **never reveals the answer**.

The hint is a smaller question that probes what the student is missing.

**Math example (correction wrong):**
> Hint: "Check the arithmetic. What is 11 minus 5?"

**Grammar example (correction wrong):**
> Hint: "The action happened last year — finished, not still going. What tense matches that?"

**Diagram example (correction wrong):**
> Hint: "Which organelle is the energy-producer of the cell?"

Hint cost: correction accuracy × 0.7. Hints do not reset the task or change the spot.

---

## 9. Mistake Repair Signal

If the student got concept X wrong earlier in the session (in any game) and successfully spots + corrects an Error Detection task involving concept X, that counts as a **mistake repair** event.

Error Detection is particularly good at producing repair events because the broken example often mirrors the kind of mistake the student themselves makes. Production team should keep this in mind when authoring tasks — the broken block should reflect a real, common student error, not an artificial nonsense error.

Repair signal feeds downstream session components for adaptation and Reflection narrative.

---

## 10. What the Production Team Outputs Per Task

Each Error Detection task in the homework JSON should include:

```
{
  "task_id": "err_math_g7_001",
  "pattern": "math_equation",
  "concept_tag": "linear_equation_subtraction",
  "grade_band": "G5-8",
  "difficulty": "medium",
  "blocks": [
    {"id": "b1", "content": "3x + 5 = 11", "is_error": false},
    {"id": "b2", "content": "3x = 11 - 5", "is_error": false},
    {"id": "b3", "content": "3x = 16",     "is_error": true},
    {"id": "b4", "content": "x = 16/3",    "is_error": false}
  ],
  "correct_answer_for_error_block": "3x = 6",
  "accepted_variants": ["3x=6", "3x = 6", "3 x = 6"],
  "common_mistake_source": "11 - 5 miscalculated as 16",
  "hint": "Check the arithmetic. What is 11 minus 5?",
  "why_prompt": "Why was the original wrong?",
  "expected_reasoning_keywords": ["11 - 5", "6", "arithmetic"],
  "correct_feedback": "Aniq! Xatoni topdingiz va to'g'rilashni mustaqil bajardingiz.",
  "wrong_correction_feedback": "Hali emas. Hintni ko'rishni xohlaysizmi?",
  "reveal_feedback": "To'g'ri javob: 3x = 6. Sabab: 11 - 5 = 6, 16 emas."
}
```

For Pattern B (grammar), `blocks` are sentence clauses and `pattern: "grammar_sentence"`. For Pattern C (diagram), `blocks` are labels with positions and `pattern: "science_diagram"` plus a `diagram_svg` field.

The minimum pool size is **8 tasks per concept tag per grade band**. Lower than Real-Life Challenge because tasks are smaller, easier to author, and adaptation needs choices to operate.

---

## 11. What NOT to Do

These are forbidden in Error Detection:

- **First-exposure tasks.** If the concept has not appeared in correct form earlier in the session, Error Detection cannot run. The student needs a reference point.
- **Auto-reveal after spotting.** The system must wait for the student to type a correction. Showing the correct version after the spot kills the cognitive event.
- **Any-string-accepted corrections.** The AI must check whether the typed correction is substantively right. Accepting any string the student types fails the Strip Test — the game collapses into clickable content.
- **Exact-match-only checking.** The opposite failure — rejecting `3x=6` because the student didn't write `3x = 6` with spaces. Production team must list accepted variants. AI handles minor formatting differences.
- **Artificial errors no student would make.** The broken block should reflect a real, common mistake. "3x = 999" as the wrong version of "3x = 6" is too obvious — every student spots it immediately. Use mistakes drawn from real student error patterns (or from the team's misconception data).
- **Multiple errors per task in v1.** One error per task, all grades. Multi-error is a future variant.
- **Speed multipliers.** Error Detection is reasoning, not speed. Even at lower grades, the cognitive event is recognition + construction, both of which suffer under time pressure.
- **Reveal of correct answer before the second wrong correction attempt.** The student gets: one spot attempt with retry → one correction attempt → one hint → one retry → then reveal. No earlier shortcut.
- **WHY prompt skipped for math/science.** Mandatory per the interactivity standard. Optional only for grammar/text mechanical fixes.

---

## 12. Success Criteria

Error Detection is working correctly when:

- Every task has exactly one error, in a real-mistake pattern
- The student cannot complete the task without producing the correction themselves
- The Strip Test passes — remove the subject content and the task is just "tap a block, type something"
- AI missing-part detection is reading typed corrections and giving substantive feedback (not string-match)
- WHY prompt is firing for math/science tasks
- Mistake repair count from Error Detection is consumable by downstream session components
- Tasks selected by adaptation logic match the student's currently-shaky concepts where possible

If any of these fail, the task pool or evaluation logic needs review before that homework ships.
