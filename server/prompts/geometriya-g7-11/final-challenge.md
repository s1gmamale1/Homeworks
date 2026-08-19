# Prompt: Final Challenge (Boss) — Geometry (Hard only)

You are building the Final Challenge for a Geometry Hard mode session. This is the boss fight — HP combat. The student proves mastery of everything taught in this session.

## Input

- Textbook page (image or text)
- All previous phase outputs
- Grade: G7-9 (Geometriya)

## Output

4-6 boss questions with HP damage tags. Mix of difficulty tiers.

> **SVG Rule:** Every proof question shows State 0 (clean figure) as SVG. Each Visual Hint reveals the next diagram state as a new SVG — never a text-only hint. Partially-marked diagram-reading questions use orange `?` SVG labels on unknowns. Use `instruction.md` → SVG Output Rule.

---

## HP and Damage

| Grade | HP |
|-------|:--:|
| G7-9 (Geometriya) | **100** |

| Difficulty | Damage | Distribution |
|-----------|:------:|:----------:|
| Easy | -10 HP | 40% |
| Medium | -20 HP | 40% |
| Hard | -30 HP | 20% |

For 5 questions: 2 Easy + 2 Medium + 1 Hard.

---

## Question Construction

Every question tagged: `[Damage: -XX HP]`

**Must include:**
- ≥1 proof question (student constructs a 2-3 step logical argument with reasons cited)
- ≥1 diagram reading question (read a labeled figure and identify theorem, angle, or relationship)
- ≥1 real-context question (professional scenario where geometry solves a design problem)
- G7-9: ≥1 interpretation question ("Bu natija qurilish uchun nimani kafolatlaydi?" or "Bu javob mantiqiymi?")

**Every question involving a shape MUST include a diagram described in brackets** using the Visual Layer notation standard (tick marks, arc marks, square corners, arrows, color codes: blue=given, orange=to prove).

**Proof questions must show State 0 only** — clean diagram, no marks. The student adds marks as they work. The grading rubric checks: did the student add the correct marks at each step, and did they cite the theorem name?

**Diagram-reading questions show a partially marked diagram** — some marks given (blue), one element highlighted orange with a question mark. Student identifies it.

**MC restriction:**
- G7-9: **NO MC.** All open-ended with written steps.

**Difficulty scaling:**
- Easy (-10): single-step, direct theorem identification or one-step calculation
- Medium (-20): 2-3 steps, requires choosing the correct theorem and applying it
- Hard (-30): multi-step with context — identify configuration, name theorem, prove or calculate, interpret result

---

## Example (§9 — SAS congruence criterion)

> **Q1** [Damage: -10 HP]
> `[Diagram: triangles ABC and DEF with marks AB=DE (one tick), ∠B=∠E (arc), BC=EF (one tick)]`
> Bu rasmda qaysi tenglik belgisi ko'rsatilgan? Javobingizni asoslang.

> **Q2** [Damage: -10 HP]
> `[Diagram: triangle PQR with ∠Q = 90°, PQ = 5 sm, QR = 3 sm]`
> △PQR burchaklarini toping. Qaysi teoremadan foydalandingizni ko'rsating.

> **Q3** [Damage: -20 HP]
> Berilgan: △ABC va △DEF. AB = 3.5 sm, ∠B = 48°, BC = 2.8 sm. DE = 3.5 sm, ∠E = 48°, EF = 2.8 sm.
> △ABC = △DEF ekanligini isbotlang. Har bir qadamda sababni ko'rsating.

> **Q4** [Damage: -20 HP]
> Siz me'morsiz. `[Diagram: symmetric roof truss — two triangles sharing a center vertical beam, with given measurements on one side only]`
> Tomning ikkala qismi teng ekanligini SAS belgisi asosida isbotlang. Agar teng bo'lmasa, konstruksiya xavflidir.

> **Q5** [Damage: -30 HP]
> `[Diagram: quadrilateral ABCD with diagonal AC drawn, creating triangles ABC and ACD. Marks: AB=CD (one tick), ∠BAC=∠DCA (arc marks)]`
> △ABC = △CDA ekanligini isbotlang. Qaysi belgi ishlatilganini ko'rsating. Bu tenglik to'rtburchak haqida nima aytadi?

---

## Hint Ladder — Visual Progressive Reveal

Hints in the Final Challenge are delivered as diagram state reveals, not as text clues. Each hint adds one layer to the diagram:

- **Hint 1 — -5 HP:** Reveal State 1 of the diagram — add the marks for the FIRST given condition only (e.g., show one tick on AB=DE). No explanation, no theorem name. The student reads the mark and identifies what it means.
- **Hint 2 — -5 HP:** Reveal State 2 — add marks for ALL given conditions (all ticks, arcs, right angle squares now visible in blue). Still no conclusion stated. Student must name the theorem.
- **Hint 3 — -5 HP:** Reveal State 3 — the first step of the solution written out with its diagram state. Student completes the remaining steps.

**Never give a text-only hint for a geometry question.** The hint IS the diagram state. Reading a diagram is a skill — the hints reinforce it.

Example hint sequence for a SAS proof question:
> Hint 1: `[State 1: triangles ABC and DEF shown, one tick appears on AB and DE (blue). All else unmarked.]` — "Rasmda nima ko'ryapsiz?"
> Hint 2: `[State 2: one tick on AB=DE (blue), arc at ∠B=∠E (blue), one tick on BC=EF (blue). Orange question mark on conclusion.]` — "Barcha belgilar ko'rsatildi. Qaysi teorema?"
> Hint 3: `[State 2 diagram] + "1-qadam: AB = DE (berilgan). Keyingi qadamni davom eting."`

**Anti-leak rules (apply at every level):**
- Hint must never name the theorem (SAS, ASA, AAS, SSS) until the student has named it themselves — Hints 1 and 2 reveal the marked diagram only.
- Hint must never quote the model answer (numeric length, angle measure, theorem name) verbatim or in any algebraically-equivalent reduced form.
- Hint must never collapse the proof to a single deduction — at Hint 3 the student still has remaining steps to write.
- Hint must teach toward the answer (which marks to read, what the marks mean, what the first proof line should set up) — not deliver it.

**Hint format (single-string encoding):**
The injector splits the `hint` field by newline, `|`, or `•` into up to 3 ladder stages. Encode the three diagram-state references in one string, joined by ` | `:
> [State 1 description + question] | [State 2 description + question] | [State 3 description + first proof line]

If fewer than 3 stages are supplied, the last one is duplicated to fill — meaning the most-revealing diagram state becomes the FIRST hint shown. Always supply exactly 3.

**BAD / GOOD (for the SAS proof question above):**
- BAD Hint 1: "SAS teoremasi" (names the answer)
- BAD Hint 3: "AB=DE, ∠B=∠E, BC=EF → SAS bo'yicha △ABC ≅ △DEF" (full proof handed over)
- GOOD: see the example sequence above — diagram state + diagnostic question, theorem name never appears.

## Failure Response

Wrong answer → "Hali emas!" (never "Noto'g'ri")
Show WHY the correct answer is correct with diagram reference. Route back to the relevant Preview panel.

---

## Rules

- Numbering: questions are pre-numbered 1–6 by the system. Do not renumber mid-stream.
- 4-6 questions, distribution 40/40/20 (easy/medium/hard)
- All questions from THIS chapter's content only
- Every question tagged with Damage
- G7-9: no MC — all open-ended, all require written steps
- Every shape question includes a diagram described in brackets using Visual Layer notation
- Proof questions show State 0 diagram only — student builds the annotation as they prove
- Diagram-reading questions show partially marked diagram — student identifies the orange-marked unknown
- Every proof answer must cite the theorem name at each step
- All measurement answers include units (°, sm, m)
- Hints are diagram state reveals — never text-only clues
- Hints cost HP, not free
- Language: Uzbek, "Siz" formal


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
