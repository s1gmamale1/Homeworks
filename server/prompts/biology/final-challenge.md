# Prompt: Final Challenge (Boss) — Biology (Hard only)

You are building the Final Challenge for a Biology Hard mode session. HP boss fight. The student proves mastery of biological concepts.

## Input

- Textbook page + all previous phase outputs
- Grade: G5-11 (Biologiya)

## Output

4-6 boss questions with HP damage tags. Mix of difficulty tiers.

---

## HP and Damage

| Grade | HP |
|-------|:--:|
| G5-8 | **100** |
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
- ≥1 **diagram analysis** — identify or label a biological structure or process from an SVG (organelle, organ cross-section, food web, cell cycle stage)
- ≥1 **mechanism explanation** — explain HOW or WHY a biological process works (e.g., "Fotosintez jarayonida kislorod qanday hosil bo'ladi?")
- ≥1 **real-context question** — professional scenario requiring biological knowledge to solve (lab finding, diagnostic observation, ecological data)
- ≥1 **prediction/consequence** — "Agar [condition] bo'lsa, nima sodir bo'ladi?" (e.g., "Agar xlorofill yo'q bo'lsa...")

**MC restriction:**
- G5: up to 30% MC allowed
- G6+: **NO MC.** All open-ended.

**Difficulty scaling:**
- Easy (-10): direct recall or single-step identification (name a structure, state a function)
- Medium (-20): 2-step reasoning (describe a process AND connect it to an outcome)
- Hard (-30): multi-step with context — observe data or diagram → explain mechanism → predict consequence OR recommend action

---

## Hint Ladder

- **Hint 1: -5 HP.** Highlight or label one key component on the diagram — never name the mechanism, never name the conclusion.
- **Hint 2: -5 HP.** Hint at the category of the answer ("bu jarayon energiya almashuvi bilan bog'liq") — never name the specific organelle, enzyme, or species the answer requires.
- **Hint 3: -5 HP.** Show the first analytical step (e.g. "Diagrammada qaysi tuzilma kislorod bilan ishlaydi?") as a **diagnostic question**, not a fill-in-blank skeleton of the answer.

**Anti-leak rules (apply at every level):**
- Hint must never quote the model answer (organism name, organelle name, enzyme, mechanism, predicted outcome) verbatim or in any inflected/translated form.
- Hint must never write "Javob: X" or "Bu jarayon X" with the answer in place of X.
- Hint must teach toward the answer (which structure to look at, which trophic level, which gas, which phase) — not deliver it.
- Hint must never name the correct option for any sub-choice in a multi-part question.

**Hint format (single-string encoding):**
The injector splits the `hint` field by newline, `|`, or `•` into up to 3 ladder stages. Encode all three levels in one string, joined by ` | `:
> Hint 1 text | Hint 2 text | Hint 3 text

If fewer than 3 stages are supplied, the last one is duplicated to fill — meaning a single answer-leaning line becomes EVERY level the student sees. Always supply exactly 3.

**BAD / GOOD (for "Fotosintez qaysi organellada sodir bo'ladi?"):**
- BAD Hint 1: "Xloroplast" (literal answer)
- BAD Hint 2: "Bu jarayon xloroplastda boshlanadi..." (literal answer in a sentence)
- BAD Hint 3: "Javob: xloroplast" (answer at the end)
- GOOD: "Diagrammadagi yashil rangli organellaga e'tibor bering | Bu organella faqat o'simlik hujayralarida bor — qaysi pigment bilan bog'liqligini eslang | O'zingizga savol bering: 'Yorug'lik energiyasini kim yutadi?' — diagrammadan shu organellani toping"

**BAD / GOOD (for "Ikkinchi tartibli konsument yo'q bo'lsa nima bo'ladi?"):**
- BAD Hint 3: "Birinchi konsumentlar soni ko'payadi, uchinchi konsumentlar kamayadi" (full answer)
- GOOD Hint 3: "O'zingizga savol bering: (1) Yo'qolgan tur kimni iste'mol qilardi? (2) Endi shu tur soniga nima bo'ladi? (3) Bu o'zgarish yuqoriga qanday tarqaladi?"

## Failure Response

"Hali emas!" — never "Noto'g'ri". Always show WHY the correct answer is correct, with a supporting diagram or step-by-step explanation.

---

## Example (5-question set, Grade 7-8)

> **1. [Easy | -10 HP]**
> Quyidagi hujayra diagrammasida mitoxondriyani toping va uning asosiy vazifasini ayting.
> [SVG: animal cell with organelles labeled A–F]
> `[Bloom: L1 | PISA: L1 | Damage: -10 HP]`
>
> **2. [Easy | -10 HP]**
> Fotosintez qaysi organellada sodir bo'ladi? Bu organellaning o'ziga xos tuzilishi nima uchun kerak?
> `[Bloom: L2 | PISA: L2 | Damage: -10 HP]`
>
> **3. [Medium | -20 HP]**
> Siz mikrobiolog sifatida namunani tekshiryapsiz. Mikroskopda hujayra devori va vakuola ko'rinmoqda. Bu hujayra o'simlikka yoki hayvonga tegishli? Xulosangizni asoslang.
> `[Bloom: L4 | PISA: L3 | Damage: -20 HP]`
>
> **4. [Medium | -20 HP]**
> Quyidagi oziq zanjirini ko'ring. Agar ikkinchi tartibli konsument yo'q bo'lib ketsa, qolgan organizmlar soniga qanday ta'sir qiladi?
> [SVG: food chain with 4 trophic levels]
> `[Bloom: L4 | PISA: L3 | Damage: -20 HP]`
>
> **5. [Hard | -30 HP]**
> Tadqiqotchilar o'rmon ekotizimasida azot miqdori keskin kamayganini aniqladilar. Bu holat: (a) tuproq mikroorganizmlariga, (b) o'simliklarga, (c) hayvonlarga qanday ta'sir qiladi? Har bir trofik daraja bo'yicha izohlab bering.
> `[Bloom: L5 | PISA: L4 | Damage: -30 HP]`

---

## SVG Diagrams

Generate inline SVGs for every diagram analysis question. Include SVGs for:
- Cell structures (plant cell, animal cell, organelles with labels)
- Biological process flows (photosynthesis, respiration, cell division stages)
- Organism anatomy (leaf cross-section, heart chambers, digestive tract segments)
- Ecological diagrams (food web, ecosystem layers, population graphs)

Place the SVG directly inside the question it belongs to. Keep under 300×200px. Use clean lines and readable labels.

---

## Rules

- Numbering: questions are pre-numbered 1–6 by the system. Do not renumber mid-stream.
- 4-6 questions, 40/40/20 distribution
- THIS chapter content only — no concepts from outside the session
- Every question tagged Bloom + PISA + Damage
- G6+: no MC — open-ended only
- No numerical calculations — biology questions test observation, explanation, and prediction
- Hints cost HP (-5 HP each)
- Language: Uzbek, "Siz" formal
- "Hali emas!" on wrong answer — never "Noto'g'ri"
- SVGs required for all diagram-analysis questions


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
