# Prompt: Final Challenge (Boss) — Physics (Hard only)

You are building the Final Challenge for a Physics Hard mode session. HP boss fight. The student proves mastery.

## Input

- Textbook page + all previous phase outputs
- Grade: G7-11 (Fizika)

## Output

4-6 boss questions with HP damage tags. Mix of difficulty tiers.

---

## HP and Damage

| Grade | HP |
|-------|:--:|
| G7-8 | **100** |
| G9-11 | **150** |

| Difficulty | Damage | Distribution |
|-----------|:------:|:----------:|
| Easy | -10 HP | 40% |
| Medium | -20 HP | 40% |
| Hard | -30 HP | 20% |

For 5 questions: 2 Easy + 2 Medium + 1 Hard.

---

## Question Construction

Every question tagged: `[Bloom: LX | PISA: LX | Damage: -XX HP]`

**Must include:**
- ≥1 formula application (given values, find unknown)
- ≥1 diagram reading (force diagram, circuit, graph → answer question)
- G9-11: ≥1 interpretation ("Bu natija fizik jihatdan nimani bildiradi?")

**MC restriction:**
- G7: up to 30% MC
- G8+: **NO MC.** Open-ended with shown work.

**Difficulty scaling:**
- Easy (-10): direct formula substitution, one step
- Medium (-20): 2-3 steps, unit conversion may be needed
- Hard (-30): multi-step with context, setup + solve + interpret

---

## Hint Ladder

- **Hint 1: -5 HP.** Name the law/formula that applies — never the answer.
- **Hint 2: -5 HP.** Restate which quantities the problem gives you and which symbol stands for the unknown. Don't substitute values yet.
- **Hint 3: -5 HP.** Show the formula with units placed but the unknown still solved-for symbolically (e.g. `F = m · a → a = F / m`). Even at Hint 3, the literal numeric answer never appears.

**Anti-leak rules (apply at every level):**
- Hint must never quote the model answer (numeric value with units) verbatim or in any unit-converted equivalent (e.g. if the answer is `5 m/s`, no level can show `5 m/s`, `500 cm/s`, `18 km/h`, or any rounding of it).
- Hint must never collapse the work to a single substitution — "F = 10 · 2 = 20 N" gives both setup and answer.
- Hint must teach toward the answer (which law applies, which quantity is unknown, which units must align), not deliver it.
- Hint must never name the correct option for any sub-choice in a multi-part question.

**Hint format (single-string encoding):**
The injector splits the `hint` field by newline, `|`, or `•` into up to 3 ladder stages. Encode all three levels in one string, joined by ` | `:
> Hint 1 text | Hint 2 text | Hint 3 text

If fewer than 3 stages are supplied, the last one is duplicated to fill — meaning one answer-leaning line becomes EVERY level the student sees. Always supply exactly 3.

**BAD / GOOD (for "10 kg jismga 20 N kuch ta'sir qiladi. Tezlanishni toping."):**
- BAD Hint 1: "a = 2 m/s²" (literal answer)
- BAD Hint 2: "F = m·a → 20 = 10 · a → a = 2" (full substitution + answer)
- BAD Hint 3: "Tezlanish 2 m/s² ga teng" (paraphrased answer)
- GOOD: "Nyutonning ikkinchi qonuni — kuch, massa, tezlanish o'rtasidagi munosabat | Berilganlar: kuch va massa. Noma'lum: tezlanish. Birliklar: N, kg, m/s². | F = m · a tenglamasini a uchun yeching — qaysi miqdorni nimaga bo'lasiz, o'zingiz toping"

## Failure Response

"Hali emas!" — never "Noto'g'ri". Show WHY the correct answer is correct.

---

## Rules

- Numbering: questions are pre-numbered 1–6 by the system. Do not renumber mid-stream.
- 4-6 questions, 40/40/20 distribution
- THIS chapter content only
- Every question tagged Bloom + PISA + Damage
- G8+: no MC
- All answers require units
- Hints cost HP
- Language: Uzbek, "Siz" formal
- Visuals: Generate inline SVG for diagram-reading questions (force diagrams, circuits, graphs, data tables). Place SVG inside the question.


---

## OUTPUT REQUIREMENT

**Stored key: `content_json.boss_questions[]`.** `final_challenge` is only the
pipeline / builder phase name — there is no `final_challenge` key in
`content_json`. The builder writes this array to `content.boss_questions`, and
the renderer reads it as the `BOSS_QUESTIONS` JS constant. Paste the output into
the builder's "Yakuniy jang" (👾) editor; return the bare array, unwrapped.

Field routing — all five reach the screen:
- `q` -> the question body.
- `tags` -> parsed server-side into the Bloom/PISA header. Only the `Bloom:` and
  `PISA:` segments are read; the `Damage:` segment inside the tag string is
  inert — `dmg` is what actually sets damage. Keep the two in sync anyway.
- `ans` -> the server-only accepted-answer list. Stripped before the page is
  sent, so it never leaks to the student.
- `hint` -> split on newline, ` | ` or `•` into the 3-step hint ladder.
- `dmg` -> HP damage, and it also picks the tier badge (<=10 easy, <=20 medium,
  otherwise hard).

Return valid JSON matching this exact schema:
```json
[
  {
    "q": "string",
    "tags": "[Bloom: LX | PISA: LX | Damage: -XX HP]",
    "ans": ["string", "string"],
    "hint": "string",
    "dmg": 10
  }
]
```
