# Prompt: Real-Life Challenge — English (Phase 4, HARD only)

You are building the Real-Life Challenge (Phase 4) for an English HARD mode session. The student has completed Preview, Flash Cards, Sprint, Reading, and Game Breaks. Now they apply everything to ONE deep real-world scenario as THE EXPERT.

This phase tests whether Preview's Word→Structure Translation actually worked. The student must read a scenario, identify the language target in context, and produce correct English under professional pressure.

## Input

- Textbook unit (image or text)
- All previous phase outputs
- Detected CEFR level (from `classify.md`): A1 · A1+ · A2 · A2+ · B1 · B1+ · B2
- Grade (for pro-role selection)

## Output

ONE scenario with questions (count by CEFR level). Answer key included.

| Level | Scenario words | Questions |
|:-:|:-:|:-:|
| A1 / A1+ | 40-70 | 2 |
| A2 / A2+ | 60-110 | 3 |
| B1 / B1+ | 90-155 | 3-4 |
| B2 | 130-180 | 4 |

**Tenses in model answers:** level-allowed set only (see `classify.md`).

---

## Scenario Construction

**First-person POV mandatory.** The student IS the professional.

> "You are [role]. Your task is..."

Never third person ("Dilnoza needs to..."). Always direct: "You", "Your".

**Pick a pro-role from the grade-anchored list (grade drives role, NOT level):**
- **G5-6 — LOCAL ONLY:** Chorsu bozor helper, mahalla football captain, school monitor, young Samarkand kid-tourist guide, family bakery helper, Telegram-group admin
- **G7-8:** Tashkent IT intern, Chorsu export seller, Hilton Tashkent receptionist, BBC Tashkent young reporter, NASA young-scholar, airline ground staff, CoderDojo mentor
- **G9-10:** NASA stringer, BBC Tashkent reporter trainee, UN interpreter trainee, airline cabin crew applicant, Uzbekistan Airways customer-service lead, Presidential School IELTS tutor, Samarkand heritage-site docent
- **G11:** IELTS Task-2 essayist, TEDx Tashkent speaker, Cambridge UCAS personal-statement writer, startup pitch presenter (Tashkent IT Park), UN MUN delegate

**Wise Status Injection Recipe:**
1. Assign a high-status, credible professional role
2. Anchor in UZ (55%) or global (45%) — no more than 45% global
3. Close the scenario frame with: "Your precision builds the Third Renaissance." OR "Your accuracy meets Global Standards."

**A1/A2 levels: W5H scaffold required.** Include 4 of 6 W5H branches (Who / What / When / Where / Why / How) visible inside the scenario prompt.

**Scope lock:** Every skill tested must have been taught in Preview. No new grammar or vocabulary. Same difficulty as the hardest Preview example — different context.

---

## Sub-question Construction

Bloom progression:
1. **Application** — use the chapter's grammar/vocab to complete a realistic task (Bloom L3)
2. **Analysis** — compare two English options and explain which is correct in this context (Bloom L4)
3. **Transfer** — adapt the language to a related but different professional moment (Bloom L4-L5)
4. **(B1+/B2 only) Evaluation** — critique a piece of English for register, accuracy, or effect (Bloom L5-L6)

A1/A2: questions 1-2 only (Application + simple Analysis). No Transfer or Evaluation.

Each question:
- Requires producing English (sentence, short dialogue, 2-3 sentence response)
- Uses level-allowed tenses in the model answer
- Tagged `[Bloom: LX | PISA: LX]`

---

## Example (B1 level, G7 pro-role)

> You are a **BBC Tashkent junior reporter**. Your editor has asked you to write a 3-sentence update on the new IT Park expansion in Tashkent. You have already visited the site and interviewed two engineers. Your accuracy meets Global Standards.

> **Q1.** Write 3 sentences reporting what you saw at the IT Park. Use the present perfect at least once. `[Bloom: L3 | PISA: L2]`
>
> Model: "The new IT Park expansion **has added** 15,000 square metres of co-working space. Engineers **have installed** fibre-optic cables across the entire building. The project **has already attracted** 20 international startups."

> **Q2.** Your editor says: "Use past simple, not present perfect." Which sentence below fits past simple correctly — and why?
> A) "The engineers installed the cables last Tuesday."  B) "The engineers have installed the cables last Tuesday." `[Bloom: L4 | PISA: L2]`
>
> Model: A is correct. "Last Tuesday" is a fixed past time → past simple. Present perfect is banned when the time is named.

> **Q3.** Now write one sentence about the IT Park for a formal UN report. Upgrade the register. `[Bloom: L4 | PISA: L3]`
>
> Model: "The Tashkent IT Park expansion, completed in March 2024, **has significantly enhanced** Uzbekistan's digital infrastructure capacity."

---

## Rules

- ONE scenario only — not multiple
- First-person "You" POV. Never third person.
- Pro-role from grade table — grade drives role, not level
- All grammar must come from Preview content — no new methods
- Every question tagged with Bloom + PISA
- A1/A2 levels: W5H scaffold visible in scenario prompt
- Model answers use level-allowed tenses — never a banned tense
- Language: student-facing English. UZ bridge allowed in model answers.
- No bazaar/village/shopkeeper clichés
- Apply Wise Status Injection Recipe on every scenario
- **Visuals:** inline SVG only when a visual aids understanding of THIS scenario — a setup diagram of the workplace/location, a timeline of the scenario's events, a register-comparison table when the question pivots on formal vs informal. **No decorative, generic, stock-like, or out-of-topic media.** Under 300×200px. Priority SVG > Mermaid > ASCII.
  - BAD: a generic city-skyline SVG attached to a hotel-receptionist scenario.
  - GOOD: a phone-handset SVG with two speech bubbles ("Good morning" / "Hello") labeled "formal" and "informal", paired to the register-choice question.


---

## OUTPUT REQUIREMENT

**Stored key: `real_life`** — the legacy one-scenario, six-question phase. Paste the output into the builder's "Hayotiy vazifa" (🌍) editor.

**Not `real_life_challenge`.** Despite this prompt's title, `real_life_challenge`
is a different phase that coexists with this one: a strict 5-step expert
role-play case (`steps[]` of kind decision / info_request / final_decision /
concept_select / reasoning) with its own "Hayotiy chaqiruv" (🧭) editor sitting
directly beside this one in the builder. It has no prompt file and nothing here
authors it. Output from this prompt pasted into that editor will not validate.

Per-question Bloom/PISA tags go INSIDE the `prompt` string as
`[Bloom: LX | PISA: LX]` — the renderer extracts them into the question header
and strips them from the visible text. There is no separate tags field.

Return valid JSON matching this exact schema:
```json
{
  "badge": "VAZIFA · string",
  "story": "string",
  "q1": { "prompt": "string", "ans": "string", "fb": "string" },
  "q2": { "prompt": "string", "fields": [{"id": "string", "label": "string", "ans": "string"}], "fb": "string" },
  "q3": { "prompt": "string", "ans": "string", "fb": "string" },
  "q4": { "prompt": "string", "fields": [{"id": "string", "label": "string", "ans": "string"}], "fb": "string" },
  "q5": { "prompt": "string", "open": true, "fb": "string" },
  "q6": { "prompt": "string", "ans": "string", "fb": "string" },
  "endTitle": "string",
  "endSub": "string"
}
```
