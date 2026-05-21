# Boss Arena — Game Mechanic Specification

**Replaces:** Final Boss (21), Why Chain (09), Adaptive Quiz (07)
**Type:** Game (position in flow determined by homework design, not by this spec)
**Audience:** Production team creating homework prompts and content.

---

## 1. What Boss Arena Is

Boss Arena is a high-stakes reasoning game. It is not a quiz with HP painted on it. It is a sequence of 4–6 reasoning questions where every question forces the student to explain **why** something works, **how** it works, and **what** the result means. The HP/damage system is the gamification skin on top of that real reasoning.

Boss Arena replaces three older games. Why Chain becomes the question *shape*. Adaptive Quiz becomes the delivery *logic*. Final Boss becomes the high-stakes *moment*. They are not separate games anymore — they are three components of one Boss Arena.

---

## 2. When Boss Fires

Boss Arena is deployable wherever the homework flow places it. The spec does not pin Boss to a specific phase.

What Boss requires to function:

- Some upstream learning activity in the same session that produces telemetry — earlier game results, weak skill flags, hint usage, first-failure events. Boss adapts based on this data, so it cannot run as the first activity in a session with no upstream context.
- A connected concept pool that matches the session's lesson content.

Boss runs once per session. There is no Sub/Big/Mythical hierarchy in this spec — that's deferred.

---

## 3. The Student Experience (Flow)

The student enters Boss Arena with a starting HP bar (50 / 100 / 150 depending on grade band). The boss "attacks" by presenting one question at a time. The student's job is to answer correctly enough, and explain well enough, to bring the boss's HP to zero before the question pool runs out.

Each question goes through this loop:

```
1. Boss presents Why → How → What question on screen
2. Student types or selects answer
3. System evaluates accuracy + reasoning quality
4. Damage is dealt based on the evaluation
5. Feedback appears (correct, partial, or "hali emas")
6. If wrong, student may request a hint (which reduces the next damage they can deal)
7. Next question loads, adapted based on what just happened
```

The session ends when boss HP reaches zero (victory), or when the question pool is exhausted (assessment based on total damage dealt vs HP remaining).

---

## 4. The Question Shape — Why → How → What

Every Boss question must include all three parts. Not one of them. Not two. Three.

| Part | What it asks | What it tests |
|---|---|---|
| **Why** | Why does this concept apply here? | Conceptual understanding |
| **How** | How do you use it to reach the answer? | Process / application |
| **What** | What does the result mean? | Interpretation / transfer |

A question that asks only "what is the answer" is a quiz question, not a Boss question. A question that asks "why does this matter" without "how do you do it" is a discussion question, not a Boss question. The full chain must fire.

### Example (Math, Grade 7)

> **Topic:** Pythagorean theorem
>
> A ladder leans against a wall. The base is 5 meters from the wall. The ladder is 13 meters long. How high up the wall does the ladder reach?
>
> - **Why** does the Pythagorean theorem apply to this situation?
> - **How** do you set up the equation to solve it?
> - **What** does the answer mean for whether the ladder is safe?

### Example (Biology, Grade 8)

> **Topic:** Photosynthesis
>
> A plant in a closed jar is placed in sunlight. After 6 hours, the oxygen level in the jar has risen.
>
> - **Why** did the oxygen level rise?
> - **How** does the plant produce this oxygen?
> - **What** would happen if you moved the jar into the dark for the next 6 hours?

The student does not have to answer all three in one paragraph. The system can split them into three short text fields, or one open-response field with three labeled prompts. Either way, the answer must address all three.

---

## 5. Adaptation Logic

Boss is adaptive in two ways at once.

**Difficulty adaptation.** After each answer:

- Correct and well-reasoned → next question is one tier harder
- Correct but weak reasoning → next question stays at same difficulty
- Wrong → next question is one tier easier OR stays same (targets the same concept, different angle)

**Weak-skill targeting.** Before each new question, the system checks upstream session telemetry:

- Which concepts did the student get wrong in earlier session activity?
- Which concepts did the student need hints for?
- Which skills are tagged as weak from anywhere earlier in the session?

The next Boss question is pulled from the pool that matches the **weakest unaddressed skill** at the current difficulty tier. Boss does not just hit random topics — it hunts the student's weak spots.

If all weak skills have been hit and the student is succeeding, Boss escalates difficulty regardless of skill targeting. If the student is struggling, Boss stays on the same weak skill across multiple questions with different framings until repair happens.

---

## 6. HP, Damage, and Scoring

| Grade Band | Starting HP | Question Count |
|---|---|---|
| G1–4 | 50 | 4 |
| G5–8 | 100 | 5 |
| G9–11 | 150 | 6 |

### Damage by question difficulty

| Difficulty | Base Damage | Cognitive Target |
|---|---|---|
| Easy | -10 HP | Apply (Bloom L3) |
| Medium | -20 HP | Analyze (Bloom L4) |
| Hard | -30 HP | Evaluate / Create (Bloom L5–6) |

### Damage modifiers

Final damage = Base Damage × Accuracy × Hint Multiplier

| Modifier | Values |
|---|---|
| Accuracy | Correct + strong reasoning = 1.0 / Correct + weak reasoning = 0.7 / Partial = 0.5 / Wrong = 0.0 |
| Hint usage | 0 hints = 1.0 / 1 hint = 0.8 / 2 hints = 0.6 / 3+ hints = 0.3 |

Combo (3 consecutive full-accuracy answers) adds +20% to the next damage roll. Combo resets on any wrong answer or hint use.

### Pass / fail

The student passes Boss when HP reaches zero before the question pool runs out. If the pool runs out with HP remaining:

- Boss HP ≤ 40% of start → Pass with reduced score
- Boss HP > 40% → Hali emas (not yet). Retry next session with different questions on the same concepts.

The 60% session pass threshold from the interactivity standard applies here too.

---

## 7. Hints

Hints follow Why Chain's rule, not the old Final Boss rule. The AI **never** states the answer. The hint is a smaller question that probes the student's thinking and points them toward what they're missing.

| Hint level | What the hint does |
|---|---|
| Hint 1 | Asks a clarifying question about the **Why** part. "What concept from this chapter applies when two sides of a triangle meet at a right angle?" |
| Hint 2 | Points to the **How** part. "What's the relationship between the three sides in that case?" |
| Hint 3 | Pushes toward synthesis. "If you square the two shorter sides and add them, what should that equal?" |

Hint 3 must never be the answer or a fill-in-the-blank skeleton of the answer. If the production team can't write a Hint 3 that follows this rule, the question itself is too narrow.

Hints cost the damage multiplier shown in Section 6. Hints do not cost HP.

---

## 8. Adaptation Targets the Mistake Repair Signal

If a student got concept X wrong earlier in the session and then gets a Boss question on concept X right (without seeing the answer between the two attempts), that counts as a **mistake repair**. Repair is the strongest signal of real learning that the session can produce.

Boss is the natural moment where repair happens, regardless of where Boss sits in the flow. Any session-level Reflection or Results component can read repair count from Boss outcomes. Production team should keep this in mind when writing Boss questions: every Boss question should connect to something the student could have stumbled on earlier in the session.

---

## 9. What the Production Team Outputs Per Question

Each Boss question in the homework JSON should include:

```
{
  "question_id": "boss_q1",
  "concept_tag": "pythagorean_theorem",
  "difficulty": "medium",
  "bloom": "L4",
  "pisa": "L4",
  "base_damage": 20,
  "prompt": {
    "scenario": "A ladder leans against a wall...",
    "why": "Why does the Pythagorean theorem apply here?",
    "how": "How do you set up the equation?",
    "what": "What does the answer mean for safety?"
  },
  "expected_concepts": ["right_triangle", "a^2+b^2=c^2", "real_world_interpretation"],
  "hints": [
    "What kind of triangle does the ladder form with the wall and ground?",
    "Which side of that triangle is the longest, and what does it represent?",
    "If you square the two shorter sides and add them, what does that equal?"
  ],
  "correct_feedback": "Strong reasoning. You named the rule, applied it cleanly, and interpreted the result.",
  "partial_feedback": "You got the number, but didn't explain why the theorem applies. Try the Why again.",
  "wrong_feedback": "Hali emas. The ladder, wall, and ground form a specific triangle — which one?"
}
```

The minimum question pool per topic is 15 questions across the three difficulty tiers (5 Easy / 5 Medium / 5 Hard) so adaptation has room to operate.

---

## 10. What NOT to Do

These are forbidden in Boss Arena:

- **MCQ-only Boss questions** (G6 and above). Boss is reasoning, not multiple choice. G5 may include up to 30% MCQ for scaffolding.
- **Questions that test only recall.** If the student can answer it from memory alone with no reasoning, it is a Memory Check question, not a Boss question.
- **Fixed question pools.** Boss must adapt. A pre-set sequence of 5 questions regardless of student performance defeats the design.
- **Hints that reveal the answer or its skeleton.** Hint 3 is a probing question, not a fill-in-the-blank.
- **HP damage without reasoning.** If the student just picks the right number and deals damage without explaining, the answer evaluation has failed.
- **Boss questions outside the current session's content.** Boss tests what the student practiced today, not last week.
- **Boss with no connection to upstream session telemetry.** If earlier-activity weak-skill data isn't being read, adaptation isn't happening, and the spec is being violated.

---

## 11. Success Criteria

Boss Arena is working correctly when:

- Every question has a complete Why → How → What chain
- The student cannot pass Boss by pattern-matching from earlier games
- Adaptation visibly targets weak skills from upstream session activity
- Hint 3 never leaks the answer
- Mistake repair count from Boss is consumable by any downstream session component
- A student who fails Boss retries on the same concepts but different questions, not the same questions

If any of these fail in a generated Boss, the question pool or adaptation logic needs review before that homework ships.
