# Prompt: Final Challenge (Boss) — Math + Algebra (Hard only)

You are building the Final Challenge for a Math/Algebra Hard mode session. This is the boss fight — HP combat. The student proves mastery of everything taught in this session.

## Input

- Textbook page (image or text)
- All previous phase outputs
- Grade: G5-6 (Matematika) or G7-9 (Algebra)

## Output

4-6 boss questions with HP damage tags. Mix of difficulty tiers.

---

## HP and Damage

| Grade | HP | 
|-------|:--:|
| G5-6 (Matematika) | **80** |
| G7-9 (Algebra) | **100** |

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
- ≥1 word problem (real situation → set up formula → solve)
- ≥1 visual question (read a diagram, bar model, graph, or table and answer)
- G7-9: ≥1 interpretation question ("Javobingiz nimani bildiradi?" or "Bu natija mantiqiymi?")

**MC restriction:**
- G5-6: up to 30% MC allowed (max 1-2 questions)
- G6+: **NO MC.** All open-ended with written steps.

**Difficulty scaling:**
- Easy (-10): single-step, direct application of the formula
- Medium (-20): 2-3 steps, requires choosing the right approach
- Hard (-30): multi-step with context, requires setup + solve + interpret

---

## Example (§23 — multiplying by tens/hundreds)

> **Q1** [Bloom: L2 | PISA: L2 | Damage: -10 HP]
> 56 × 30 = ? Yechimni bosqichma-bosqich ko'rsating.
>
> **Q2** [Bloom: L3 | PISA: L2 | Damage: -10 HP]
> 245 × 400 ni hisoblang va chamalab tekshiring.
>
> **Q3** [Bloom: L3 | PISA: L3 | Damage: -20 HP]
> Zavod har kuni 38 ta detal ishlab chiqaradi. Har bir detal 200 gramm. 5 kunda jami qancha kilogramm detal ishlab chiqariladi?
>
> **Q4** [Bloom: L4 | PISA: L3 | Damage: -20 HP]
> [Jadval: 3 turdagi mahsulot, har birining soni va narxi berilgan] Jami xarajatni hisoblang. Qaysi mahsulot eng qimmatga tushdi?
>
> **Q5** [Bloom: L5 | PISA: L4 | Damage: -30 HP]
> Siz do'kon menejerisiz. 600 so'mlik mahsulotdan 125 ta va 400 so'mlik mahsulotdan 230 ta buyurtma qildingiz. Byudjet 170 000 so'm. Yetadimi? Agar yetmasa, qaysi buyurtmani qisqartirasiz va nima uchun?

---

## Hint Ladder

If student is stuck:
- **Hint 1: -5 HP.** Name the formula, theorem, or technique that applies — never the answer or any intermediate value.
- **Hint 2: -5 HP.** Show the substituted formula or the first transformation — never the solved equation.
- **Hint 3: -5 HP.** Show the setup frame with the student-facing operation still missing (e.g. `x² + ?x + ? = 0 → (x + p)(x + q) = 0; find p, q`). Even at Hint 3, the literal numeric or symbolic answer never appears.

**Anti-leak rules (apply at every level):**
- Hint must never quote the model answer (numeric value, expression, or final form) verbatim or in any algebraically-equivalent reduced form.
- Hint must never collapse the work to a single substitution — for "Yeching: x² = 64" the hint cannot be "x = ±8" or "√64 = 8".
- Hint must teach toward the answer (formula, identity, technique, Vieta pair, factoring frame) — not deliver it.
- Hint must never name the correct option for any sub-choice in a multi-part question.

**Hint format (single-string encoding):**
The injector splits the `hint` field by newline, `|`, or `•` into up to 3 ladder stages. Encode all three levels in one string, joined by ` | `:
> Hint 1 text | Hint 2 text | Hint 3 text

If you provide fewer than 3 stages, the last one is duplicated to fill — which means a single answer-leaning hint becomes EVERY level the student sees. Always supply exactly 3.

**BAD / GOOD (for "Yeching: x² + 7x + 12 = 0"):**
- BAD Hint 1: "x = -3 yoki x = -4" (literal answer)
- BAD Hint 2: "(x+3)(x+4) = 0" (factored form gives both roots)
- BAD Hint 3: "x = -3, x = -4" (literal answer at the end)
- GOOD: "Vieta teoremasini eslang — kvadrat tenglamada ildizlar yig'indisi va ko'paytmasi koeffitsientlardan kelib chiqadi | Yig'indisi 7, ko'paytmasi 12 bo'lgan ikki sonni qidiring (ishoralarga e'tibor bering) | (x + p)(x + q) = 0 ko'rinishida yozing — p va q ni shu shartdan o'zingiz toping"

**BAD / GOOD (for "x² = 64"):**
- BAD Hint 3: "x = ±8" (literal answer)
- GOOD Hint 3: "Ikkala tomondan kvadrat ildiz olganda ± belgisini unutmang — natija qaysi sonning kvadrat ildizidir?"

## Failure Response

Wrong answer → "Hali emas!" (never "Noto'g'ri")
Show WHY the correct answer is correct. Route back to relevant concept.

---

## Rules

- Numbering: questions are pre-numbered 1–6 by the system. Do not renumber mid-stream.
- 4-6 questions, distribution 40/40/20 (easy/medium/hard)
- All questions from THIS chapter's content only
- Every question tagged with Bloom + PISA + Damage
- G6+: no MC
- All answers require units
- Hints cost HP, not free
- Language: Uzbek, "Siz" formal
- Visuals: Generate inline SVG for diagram-reading questions (force diagrams, graphs, tables). Place SVG inside the question.


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
