# Prompt: Real-Life Challenge — Biology (Hard only)

You are building the Real-Life Challenge for a Biology Hard mode session. The student applies everything to ONE deep professional scenario as THE EXPERT leading a team or project.

Biology Real-Life is NOT a textbook word problem. It is a professional narrative with team dynamics — conflicting observations, competing hypotheses, and a verification task. The student is the biologist who must observe, analyze, and make the call.

## Input

- Textbook page + all previous phase outputs
- Grade: G5-11 (Biologiya)

## Output

ONE scenario with 4-6 sub-questions.

---

## Scenario Construction

**First-person POV. You are the lead biologist / researcher / specialist.**

The scenario has NARRATIVE SPICE:
- You are working on a project or investigation
- A colleague claims something, another disagrees
- You need to verify using biological observation, analysis, or reasoning
- You report your findings or make a recommendation

Template:
> "Siz [role] sifatida [project/setting] ustida ishlayapsiz. Jamoa a'zosi [Name] [claim] deb da'vo qilmoqda. Boshqa mutaxassis [Name2] esa [counter-claim] deb hisoblaydi. Siz rahbar sifatida buni tekshirib, to'g'ri xulosani topishingiz va hisobotni tayyorlashingiz kerak."

**Professional roles:**
- Biolog-tadqiqotchi (research biologist)
- Ekolog (ecologist)
- Genetik (geneticist)
- Farmatsevt (pharmacist / pharmaceutical researcher)
- Agronom (agronomist)
- Veterinar (veterinarian)
- Biotexnolog (biotechnologist)
- Tibbiy biolog (medical biologist)
- Mikrobiolog (microbiologist)

**Professional settings (use ONLY these — no bazaar/village/shopkeeper):**
- Biologiya laboratoriyasi (biology lab)
- Ilmiy-tadqiqot markazi (research center)
- Qishloq xo'jaligi institutining agrotexnologiya bo'limi (agricultural research institute)
- Shifoxona diagnostika bo'limi (hospital diagnostics department)
- Milliy qo'riqxona (national nature reserve)
- Farmatsevtika kompaniyasi (pharmaceutical company)
- Biotexnologiya zavodining nazorat laboratoriyasi (biotech plant quality lab)

**Scenario structure:**
1. Context + team dynamic (4-5 sentences) — project setting, who is observing what, who claims what
2. Sub-questions (4-6) — each requires biological reasoning, observation interpretation, or prediction to verify/settle the dispute

---

## Sub-question types

Mix these:
- 1-2 **identification/observation** — "Hamkasb A to'g'rimi? Kuzatuvlar asosida tekshiring."
- 1-2 **mechanism explanation** — "Bu hodisa qanday sodir bo'ladi? Biologik jarayonni tushuntiring."
- 1 **prediction/consequence** — "Agar [condition] o'zgarsa, nima sodir bo'ladi?"
- 1 **recommendation/decision** — "Siz rahbar sifatida qanday qaror qilasiz va nima uchun?"
- G9-11: 1 **diagnosis or systemic analysis** — "Muammoning ildiz sababi nima? Tizimli yondashing."

Every sub-question tagged: `[Bloom: LX | PISA: LX]`

---

## Example

> Siz milliy qo'riqxonada ekolog sifatida ishlayapsiz. Jamoa a'zosi Dilnoza "O'rmon maydonidagi daraxtlar kasallik tufayli nobud bo'lyapti — bu zamburug' infeksiyasi" deb da'vo qilmoqda. Boshqa mutaxassis Bekzod esa "Yo'q, bu kasallik emas — tuproqdagi azot miqdori keskin kamaygan" deb hisoblaydi. Siz ikkalasining gipotezasini tekshirib, qo'riqxona rahbariga hisobot tayyorlashingiz kerak.
>
> 1. Zamburug' infeksiyasi bilan zararlangan daraxtda qanday tashqi belgilar kuzatiladi? Bu belgilar sog'lom daraxtdan nima bilan farq qiladi? [Bloom: L2 | PISA: L2]
> 2. Tuproqdagi azot yetishmovchiligi o'simliklarda qanday alomatlarga olib keladi? Bu belgilar Dilnoza ta'riflaganlardan farq qiladimi? [Bloom: L3 | PISA: L2]
> 3. Ikkala gipotezani solishtiring: har birini tasdiqlovchi va rad etuvchi bitta kuzatuv belgisini keltiring. [Bloom: L4 | PISA: L3]
> 4. Siz qaysi gipotezani to'g'ri deb hisoblaysiz? Xulosangizni asoslang. [Bloom: L5 | PISA: L3]
> 5. Qo'riqxona rahbariga tavsiya yozing: qanday choralar ko'rish kerak va nima uchun? [Bloom: L5 | PISA: L4]

---

## SVG Diagrams

Generate 1-2 inline SVGs where the content involves:
- Cell structures (mitochondria, chloroplast, nucleus, cell membrane)
- Organism or organ diagrams (leaf cross-section, digestive tract, heart chambers)
- Process flows (photosynthesis cycle, Krebs cycle, inheritance diagram)
- Ecosystem layers or food webs

Keep SVGs under 300×200px. Use clean lines and labels. Match textbook content — no invented anatomy.

---

## Scaffolds

**W5H:**
- G5-6: mandatory, 4/6 branches
- G7-11: available via button, not forced

**Notebook Capture:** Biology is EXEMPT from Notebook Capture. No calculation steps required.

---

## Rules

- ONE scenario. Not multiple.
- First-person "Siz" POV with team narrative
- Someone claims something → student verifies with biological knowledge
- All concepts from Preview content only — no new terms introduced
- Questions test: identifying processes, predicting outcomes, diagnosing problems, recommending solutions — NOT numerical calculations
- Every sub-question tagged Bloom + PISA
- Language: Uzbek, "Siz" formal
- Modern professional context only — lab, research station, agricultural institute, hospital, nature reserve, pharmaceutical company
- NO bazaar/village/shopkeeper/farmer clichés
- SVG diagrams for cell structures, organism diagrams, and process flows where relevant


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
