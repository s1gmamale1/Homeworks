# Prompt: Real-Life Challenge — Geometry (Hard only)

You are building the Real-Life Challenge (Phase 4) for a Geometry Hard mode session. The student has completed Preview, Flash Cards, Sprint, and Game Breaks. Now they apply everything to ONE deep real-world scenario as THE EXPERT.

This phase tests whether Preview's Diagram→Theorem Translation teaching actually worked. The student must read a scenario, identify the geometric configuration, name the theorem, and apply it to solve a real design or construction problem.

## Input

- Textbook page (image or text)
- All previous phase outputs
- Grade: G7-9 (Geometriya)

## Output

ONE scenario with 4-6 sub-questions.

> **SVG Rule:** The two-state scenario diagram (State A = problem, State B = annotated solution) must each be actual SVG code. Blue for given measurements, orange `?` for unknowns, green for student-added construction marks. Use `instruction.md` → SVG Output Rule.

---

## Scenario Construction

**First-person POV mandatory.** The student IS the expert.

> "Siz [professional role]. Sizning vazifangiz..."

Never third person ("Alisher needs to..."). Always direct: "Siz", "Sizning".

**Pick a professional role:**
- G7-9: me'mor (architect), qurilish muhandisi (structural engineer), geodezist (surveyor), plitachi usta (tile craftsman), o'yinlar ishlab chiqaruvchi (game developer), dизайнer (designer)

**Scenario structure:**
1. Context narrative (3-4 sentences) — modern professional Uzbek setting with a geometric problem embedded
2. A diagram description in brackets — the student must read this diagram as part of solving
3. Sub-questions (4-6) — each tests a skill from Preview

**Scope lock:** Every skill tested must have been taught in Preview. No new theorems. Same difficulty as the hardest Preview example — different numbers and context.

**Context policy:** Modern professional only. Samarqand Registon restavratsiyasi, Toshkent metro qurilishi, Farg'ona vodiysi yer o'lchash, Xiva Juma masjidi ta'miri, IT Park, sport inshootlari. NO bazaar, NO village, NO shopkeeper, NO farmer.

---

## Sub-question construction

Each sub-question:
- Requires reading the scenario diagram and identifying what is given
- Requires naming the theorem before applying it: "Avval qaysi teoremadan foydalanayotganingizni ayting"
- Has one correct answer with units (° or sm/m)

Mix:
- 1-2 theorem identification questions ("Qaysi tenglik belgisi qo'llaniladi?")
- 2-3 direct calculation or proof questions
- 1 interpretation question ("Bu natija qurilish uchun nimani kafolatlaydi?")
- G7-9: 1 "what if" extension ("Agar burchak 5° katta bo'lsa, nima o'zgaradi?")

---

## Diagram requirement

Every scenario MUST include a **two-state diagram** — not a single static figure. The diagram evolves as the student works:

**State A — Problem diagram (shown at the start):**
- The professional's situation: measurements given, relationships to verify, unknowns marked with "?"
- Blue = given measurements; orange = what must be found or proved; grey = context
- This is what the student reads to extract the problem

**State B — Annotated diagram (built during solving):**
- Student adds marks as they identify given conditions: tick marks for equal sides, arc marks for equal angles, square corners for right angles
- Each sub-question adds one layer of annotation to this diagram
- Final state: fully annotated with conclusion highlighted

Example:
> `[State A — Problem: roof truss — two triangles ABC and DEF sharing center vertical beam BD=BE. Blue labels: AB = 4.2 m, ∠B = 35°. Orange question mark on whether the two halves are congruent. BC and EF unlabeled.]`
>
> `[State B — After solving: one tick on AB=AE (blue), arc at ∠B=∠E (blue), one tick on BC=EC (student adds this after finding it), both triangles highlighted orange with label "△ABС = △AEC (SAS asosida)"]`

The scenario text tells the student: "Ushbu rasmga belgilarni qo'shing — berilgan ma'lumotlarni chizingga ko'rsating."

---

## Scaffolds

**W5H (Who/What/Where/When/Why/How):**
- G7-8: mandatory, 4/6 branches minimum
- G9: available via button, not forced
- Single-step theorem identification: exempt from W5H

**Notebook Capture:** Triggers on every construction or proof step. 1-2 capture points per scenario.

---

## Example

> Siz Samarqand me'mori siz. Juma masjidining eski eshigi ta'mirlanmoqda. Eshikda ikkita bir xil ko'rinuvchi uchburchak panel bor — ABC va DEF.
>
> `[Diagram: panels ABC and DEF with marks AB=DE (one tick), BC=EF (one tick), AC=DF (one tick). No angle marks shown.]`
>
> 1. Ushbu uchburchaklar uchun qaysi tenglik belgisidan foydalanish mumkin? Nima uchun?
> 2. △ABC = △DEF ekanligini isbotlang — har bir qadamda sababni ko'rsating.
> 3. Agar AB = 1.8 m, BC = 2.1 m, ∠B = 40° bo'lsa, DEF uchburchagining DE va EF tomonlari qanday?
> 4. Bu tenglik usta uchun nima kafolatlaydi — nima uchun u barcha tomonlarni qayta o'lchamasa ham bo'ladi?

---

## Rules

- ONE scenario only. Not multiple.
- First-person "Siz" POV. Never third person.
- Scenario MUST include a two-state diagram (State A = problem, State B = annotated solution) using Visual Layer notation
- Student MUST name the theorem before applying it in every sub-question
- All theorems must come from Preview content — no new methods
- All answers include units (°, sm, m)
- Language: Uzbek, "Siz" formal
- No bazaar/village clichés
- Students are instructed to add marks to the diagram as they work: "Rasmga belgilarni qo'shing"


---

## OUTPUT REQUIREMENT

**Stored key: `content_json.real_life`** — the legacy one-scenario, six-question
phase. Paste the output into the builder's "Hayotiy vazifa" (🌍) editor.

**Not `real_life_challenge`.** Despite this prompt's title, `real_life_challenge`
is a different phase that coexists with this one: a strict 5-step expert
role-play case (`steps[]` of kind decision / info_request / final_decision /
concept_select / reasoning) with its own "Hayotiy chaqiruv" (🧭) editor sitting
directly beside this one in the builder. It has no prompt file and nothing here
authors it. Output from this prompt pasted into that editor will not validate.

Per-question Bloom/PISA tags go INSIDE the `prompt` string as
`[Bloom: LX | PISA: LX]` — the renderer extracts them into the question header
and strips them from the visible text. There is no separate tags field.

`capture` is an optional per-question boolean and it is the ONLY thing that turns
on the capture points described above. Set `capture: true` on each question whose
work must be photographed: the renderer then shows that question's upload button,
blocks its submit until the photo is in, and reuses that question's `fb` as the
expected-work note. Omit it (or set `false`) everywhere else. Without this key no
capture button ever appears, whatever the capture rule above says. Put it on
whichever slots are the actual work steps — the `q3` placement below is only an
example.

Return valid JSON matching this exact schema:
```json
{
  "badge": "VAZIFA · string",
  "story": "string",
  "q1": { "prompt": "string", "ans": "string", "fb": "string" },
  "q2": { "prompt": "string", "fields": [{"id": "string", "label": "string", "ans": "string"}], "fb": "string" },
  "q3": { "prompt": "string", "ans": "string", "fb": "string", "capture": true },
  "q4": { "prompt": "string", "fields": [{"id": "string", "label": "string", "ans": "string"}], "fb": "string" },
  "q5": { "prompt": "string", "open": true, "fb": "string" },
  "q6": { "prompt": "string", "ans": "string", "fb": "string" },
  "endTitle": "string",
  "endSub": "string"
}
```
