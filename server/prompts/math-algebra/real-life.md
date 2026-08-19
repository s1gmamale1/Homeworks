# Prompt: Real-Life Challenge — Math + Algebra (Hard only)

You are building the Real-Life Challenge (Phase 4) for a Math/Algebra Hard mode session. The student has completed Preview, Flash Cards, Sprint, and Game Breaks. Now they apply everything to ONE deep real-world scenario as THE EXPERT.

This phase tests whether Preview's Word→Formula Translation teaching actually worked. The student must read a scenario, extract data, and apply this chapter's formulas.

## Input

- Textbook page (image or text)
- All previous phase outputs
- Grade: G5-6 (Matematika) or G7-9 (Algebra)

## Output

ONE scenario with 4-6 sub-questions.

---

## Scenario Construction

**First-person POV mandatory.** The student IS the expert.

> "Siz [professional role]. Sizning vazifangiz..."

Never third person ("Alisher needs to..."). Always direct: "Siz", "Sizning".

**Pick a professional role:**
- G5-6: loyiha koordinatori, logist, do'kon menejeri, qurilish boshqaruvchisi
- G7-9: biznes tahlilchi, dasturchi, muhandis, iqtisodchi, farmatsevt

**Scenario structure:**
1. Context narrative (3-4 sentences) — modern professional Uzbek setting
2. Sub-questions (4-6) — each tests a skill from Preview

**Scope lock:** Every skill tested must have been taught in Preview. No new concepts. Same difficulty level as the hardest Preview example — different numbers and context.

**Context policy:** Modern professional only. IT Park, Yashil Makon, Afrosiyob, Tashkent City, startups, tech companies. NO bazaar, NO village, NO shopkeeper, NO farmer.

---

## Sub-question construction

Each sub-question:
- Requires extracting data from the scenario text
- Requires applying this chapter's formula
- Has one correct answer with units
- Tagged: `[Bloom: LX | PISA: LX]`

Mix:
- 2-3 direct calculation questions
- 1 "chamalab tekshiring" (estimate and verify) question
- 1 interpretation question ("Javobingiz nimani bildiradi?")
- G7-9: 1 "what if" extension ("Agar narx 20% oshsa, nima o'zgaradi?")

---

## Scaffolds

**W5H (Who/What/Where/When/Why/How):**
- G5-6: mandatory, 4/6 branches minimum
- G7-8: default on
- G9: available via button, not forced
- Pure single-step calculation: exempt from W5H

**Notebook Capture:** Triggers on every calculation solve-step. 1-3 capture points per scenario.

---

## Example

> Siz Toshkent IT Parkda loyiha koordinatorisiz. Yangi server xonasi uchun 48 ta kabel o'tkazish kerak. Har bir kabel uchun 60 metr sim zarur. Omborda 3000 metr sim bor.
>
> 1. Jami qancha metr sim kerak? [Bloom: L3 | PISA: L2]
> 2. Ombordagi sim yetadimi? Qancha ortiqcha yoki kamomad bor? [Bloom: L3 | PISA: L3]
> 3. Javobingizni chamalab tekshiring — 48 ni 50 deb oling. [Bloom: L4 | PISA: L3]
> 4. Agar har bir kabel 400 so'm tursa, jami xarajat qancha? [Bloom: L3 | PISA: L2]

---

## Rules

- ONE scenario only. Not multiple.
- First-person "Siz" POV. Never third person.
- All formulas must come from Preview content — no new methods
- Every sub-question tagged with Bloom + PISA
- All answers include units
- Language: Uzbek, "Siz" formal
- No bazaar/village cliches
- Visuals: Generate 1-2 inline SVGs per scenario — scenario setup diagram and/or data visualization. Keep under 300×200px.


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
