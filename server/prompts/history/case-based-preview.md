# Prompt: Case-Based Preview — History

**Family:** History (no Infra family-prompt; derived from Standard §9.6).
**Shared contract:** `server/prompts/runtime/_cbp_contract.md` — universal CBP rules, 18-item checklist, Uzbek register, JSON output schema.

---

## 1. Subject case archetype

History CBP uses **historical decision / source-evaluation cases**. The student is an advisor, witness, historian, source-checker, or perspective-taker who must judge cause, evidence, decision, or consequence.

Good history cases:
- A 19th-century Bukhara emir's advisor must decide which neighboring policy to recommend (cause/effect, consequences)
- A student-historian evaluates two primary sources about the founding of a city (source evaluation, evidence weighing)
- A village elder during a famine year must choose which crop to plant next (decision under uncertainty)
- A modern historian reads two accounts of the same battle and judges which is more reliable (perspective, bias)
- A student must place an event in its proper chronological context (cause-effect chain)

Bad history cases:
- "Memorize the date of X" — that's a flashcard, not a CBP
- Modern-professional-roleplay forced onto a historical setting (a historical figure "uses LinkedIn") — anachronism

---

## 2. Checkpoint shapes (history-specific)

| # | Kind | Verb examples (Uz, formal Siz) |
|---|---|---|
| 1 | Identify | "Bu vaziyatda asosiy sabab nima?" / "Qaysi manba ko'proq ishonchli?" / "Qaysi davr kerak?" |
| 2 | Decide | "Qaysi qaror bu vaziyatda eng o'rinli?" / "Qaysi dalil eng kuchli?" / "Qaysi natija ehtimoldan kuchli?" |
| 3 | Justify | "Nega aynan bu qaror?" / "Boshqa variant nega zaifroq?" / "Qaysi keng tarqalgan xato bu davrda?" |

---

## 3. Decision / source / perspective principle

History CBP cases must center on judgment — of evidence, of decisions, of consequences. NEVER center on memorization of dates or names.

Open with the situation that requires the judgment: "A councilor in 1865 advises…" / "Two letters survive about the same event: …"

---

## 4. Concept-anchor rules (history-family)

- Dates, names, places MUST match the textbook (and ideally the wider historical record). Don't invent figures.
- The historical period MUST be the one the chapter covers; don't pull cross-period concepts.
- Common mistakes are anachronism (applying modern values to historical actors), single-cause explanations (when the textbook teaches multi-cause), and ignoring perspective bias.
- Final simulation MUST show consequence (what historically happened, or what plausibly would have happened) AND the lesson the student takes away.

---

## 5. Soft-retry rule (Forbid #19 — history edition)

Regenerated variant keeps `core_concept` (the historical concept being taught) + `kind` + `common_mistake`. Mutate ≥1 of:
- The specific actor / event (different councilor, different city, same period)
- The framing (decision case → source-evaluation case if both probe the same skill)
- The character

Avoid: changing the historical period or the concept being taught.

---

## 6. Per-subject output shape

Universal JSON schema. History-specific notes:

- `metadata.case_type` → `"historical-decision"` or `"source-evaluation"` or `"perspective-switch"` or `"cause-effect-chain"`
- `metadata.required_skill` → "judge cause / evidence / consequence", "weigh primary sources", "place event in context"
- `metadata.historical_period` → MUST match the chapter
- `final_simulation.visual_description` → describe timeline marker, source card, map marker, perspective-comparison card

---

## 7. Validation

Run `_cbp_contract.md §5` 18-item checklist. History watch-outs:

- Item 4 (source-aligned): dates, names, places match the textbook
- Item 5 (decision-maker): student judges, doesn't recite
- Anti-anachronism: explicit check that no modern concept leaks into the historical setting
- Item 12 (visuals support learning): timeline / map / source card, NOT decorative period art
