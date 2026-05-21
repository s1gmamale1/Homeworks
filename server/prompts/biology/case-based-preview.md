# Prompt: Case-Based Preview — Biology

**Family:** Sciences.
**Shared contract:** `server/prompts/runtime/_cbp_contract.md` — universal CBP rules, 18-item checklist, Uzbek register, JSON output schema.

This file extends the sciences family with biology-specific case patterns.

---

## 1. Subject case archetype

Biology cases are **observation / process / mechanism** scenarios — anywhere a biological system, plant, animal, cell, organ, or ecosystem produces an outcome the student must predict, diagnose, or judge.

Good biology cases:
- A school nurse evaluates a 14-year-old with rapid breathing and cyanotic lips (gas exchange / cellular respiration)
- A gardener notices wilting plants in a sunny corner (transpiration / water balance)
- A student observes oxygen bubbling from pondweed under sunlight (photosynthesis)
- A veterinarian checks why a chicken stopped laying eggs in winter (photoperiod / reproduction)
- A wound-care assistant decides which dressing to use on a healing scrape (immune response, skin layers)

Bad biology cases:
- "DNA helps you solve a mystery" — only biology if the molecular concept is load-bearing
- Animal-rights debates framed as biology — those are ethics cases
- Cases that mention biology terminology but could be solved by guessing

---

## 2. Checkpoint shapes (biology-specific)

| # | Kind | Verb examples (Uz, formal Siz) |
|---|---|---|
| 1 | Identify | "Bu jarayon qaysi tizimga tegishli?" / "Qaysi hujayra organoid qatnashadi?" / "Qaysi sabab eng ehtimolli?" |
| 2 | Decide | "Qaysi qadam birinchi tekshiriladi?" / "Qaysi mexanizm bu o'zgarishni keltirib chiqaradi?" / "Qanday natija kutiladi?" |
| 3 | Justify | "Nima uchun aynan shu jarayon?" / "Boshqa tushuntirish nega kamroq mos?" / "Qaysi belgi farqlovchi?" |

---

## 3. Mechanism-first principle

Biology is about understanding WHY living things work the way they do. CBP must start from observation (what student sees) → mechanism (cellular / physiological / ecological reason) → terminology (the scientific name).

NEVER start with terminology. A case opening with "Photosynthesis is when…" is wrong; the case must open with the observation that requires the student to deduce the concept.

---

## 4. Concept-anchor rules (biology-family)

- Scientific names must match the textbook spelling (e.g., `mitoxondriya` if the chapter uses that transliteration, not `mitochondria`).
- Process diagrams (Krebs cycle, gas exchange, DNA replication) — if the case touches them, the `source_extraction.main_rule` quotes the textbook's process summary verbatim.
- Common mistakes are HIGH-VALUE in biology — students conflate processes (photosynthesis ↔ respiration, mitosis ↔ meiosis). Build the wrong path around a named mistake.
- Final simulation MUST distinguish observable outcome from mechanism: "Plant wilts because turgor pressure drops, not because the leaves are dirty."

---

## 5. Soft-retry rule (Forbid #19 — biology edition)

Regenerated variant keeps `core_concept` + `kind` + `common_mistake`. Mutate ≥1 of:
- The organism (plant → animal → microbe, within the same process)
- The scene (lab → field → home → clinic)
- The numbers (if quantitative — e.g., breathing rate, leaf count)

Avoid: changing the process itself (photosynthesis → respiration breaks concept identity).

---

## 6. Per-subject output shape

Universal JSON schema. Biology-specific notes:

- `metadata.case_type` → `"observation"` or `"diagnostic"` or `"phenomenon"`
- `metadata.required_skill` → "predict plant condition", "identify body system", "judge cause/effect"
- `final_simulation.visual_description` → describe organism, structure, before/after state

---

## 7. Validation

Run `_cbp_contract.md §5` 18-item checklist. Biology watch-outs:

- Item 3 (case matches subject): biology cases should NOT use math-style numeric calculations as the primary decision; the decision is about *which biological process* or *which mechanism*
- Item 4 (source-aligned): no inventing biological "facts" (e.g., "frogs have 4 lungs")
- Item 9 (Checkpoint 3 catches mistake): biology mistake catching is high-value because confusable processes are common
