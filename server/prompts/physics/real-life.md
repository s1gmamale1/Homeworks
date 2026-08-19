# Prompt: Real-Life Challenge — Physics (Hard only)

You are building the Real-Life Challenge for a Physics Hard mode session. The student applies everything to ONE deep professional scenario as THE EXPERT leading a team or project.

Physics Real-Life is NOT a simple word problem. It's a professional narrative with team dynamics — conflicting claims, verification tasks, and reporting. The student is the physicist who has to confirm, verify, calculate, and make the call.

## Input

- Textbook page + all previous phase outputs
- Grade: G7-11 (Fizika)

## Output

ONE scenario with 4-6 sub-questions.

---

## Scenario Construction

**First-person POV. You are the lead physicist / project engineer / team leader.**

The scenario has NARRATIVE SPICE:
- You're on a team or leading a project
- A colleague claims something, another disagrees
- You need to verify with actual physics calculations
- You report your findings or make a go/no-go decision

Template:
> "Siz [role] sifatida [project] ustida ishlayapsiz. Jamoa a'zosi [Name] [claim] deb da'vo qilmoqda. Boshqa mutaxassis [Name2] esa [counter-claim] deb hisoblaydi. Siz rahbar sifatida buni tekshirib, to'g'ri javobni topishingiz va hisobotni tayyorlashingiz kerak."

**Professional roles:**
- Loyiha muhandisi (project engineer)
- Energetika mutaxassisi (energy specialist)
- Sifat nazoratchi (quality controller)
- Aviatsiya muhandisi (aviation engineer)
- Telekommunikatsiya muhandisi (telecom engineer)
- Tibbiyot fizigi (medical physicist)

**Scenario structure:**
1. Context + team dynamic (4-5 sentences) — project setting, who claims what
2. Sub-questions (4-6) — each requires physics calculation or reasoning to verify/settle the dispute

---

## Sub-question types

Mix these:
- 2-3 **verification calculations** — "Hamkasb A to'g'rimi? Hisoblang va tekshiring."
- 1 **estimation/sanity check** — "Bu natija mantiqiymi? Chamalab tekshiring."
- 1 **interpretation** — "Natijangiz loyiha uchun nimani bildiradi? Ishlab chiqarishni davom ettiramizmi?"
- G9-11: 1 **what-if** — "Agar [parameter] o'zgarsa, natija qanday o'zgaradi?"

Every sub-question tagged: `[Bloom: LX | PISA: LX]`

---

## Example

> Siz Toshkent viloyatidagi quyosh panellari loyihasida energetika muhandisisiz. Jamoa a'zosi Sardor "Har bir panel 200 W quvvat beradi, 50 ta panel bilan butun binoni ta'minlash mumkin" deb aytmoqda. Boshqa mutaxassis Nodira esa "50 ta panel yetarli emas, kamida 80 ta kerak" deb hisoblaydi. Bino kuniga 60 kWh energiya sarflaydi. Quyosh panellari kuniga o'rtacha 5 soat ishlaydi. Siz rahbar sifatida kim to'g'ri ekanligini aniqlashingiz kerak.
>
> 1. Bitta panel kuniga qancha energiya ishlab chiqaradi? [Bloom: L3 | PISA: L2]
> 2. 50 ta panel kuniga jami qancha kWh beradi? Sardor to'g'rimi? [Bloom: L3 | PISA: L3]
> 3. Binoni ta'minlash uchun kamida nechta panel kerak? Nodira to'g'rimi? [Bloom: L4 | PISA: L3]
> 4. Natijangizni chamalab tekshiring — 200 W ni 250 W deb oling. Javob o'zgaradimi? [Bloom: L4 | PISA: L3]
> 5. Loyiha rahbariga qisqa hisobot yozing: nechta panel kerak va nima uchun. [Bloom: L5 | PISA: L4]

---

## Scaffolds

**W5H:**
- G7-8: mandatory, 4/6 branches
- G9-11: available via button, not forced

**Notebook Capture:** Every calculation step.

---

## Rules

- ONE scenario. Not multiple.
- First-person "Siz" POV with team narrative
- Someone claims something → student verifies with physics
- All formulas from Preview content only — no new concepts
- Every sub-question tagged Bloom + PISA
- All answers include units
- Language: Uzbek, "Siz" formal
- Modern professional context: labs, energy projects, manufacturing, telecom, medical physics
- NO bazaar/village cliches
- Visuals: Generate 1-2 inline SVGs per scenario — setup diagram (circuit layout, force diagram, energy flow) and/or data visualization. Keep under 300×200px.


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
