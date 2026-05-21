# Prompt: Case-Based Preview — Kimyo (G7–11)

**Family:** Sciences.
**Shared contract:** `server/prompts/runtime/_cbp_contract.md` — universal CBP rules, 18-item checklist, Uzbek register, JSON output schema.

---

## 1. Subject case archetype

Chemistry cases are **safety → observation → particle/reaction logic → result** scenarios. The student is a lab assistant, safety checker, or amateur chemist deciding what happens next.

Good chemistry cases:
- A lab intern needs to clean a beaker that held a strong acid — what's safe? (acid-base, dilution rules)
- A baker mixes vinegar and baking soda for a cake recipe and observes bubbling (acid-base reaction)
- A student tests if rust will form on iron left in salt water vs fresh water (oxidation)
- A first-aid responder identifies a substance by its color and smell (qualitative tests)
- A chef decides whether to heat a copper pan on high vs low (conductivity / specific heat)

Bad chemistry cases:
- "Balance this equation" with no context — pure problem set
- Mystery-novel-style "the killer used cyanide" — chemistry is not the load-bearing concept

---

## 2. Checkpoint shapes (chemistry-specific)

| # | Kind | Verb examples (Uz, formal Siz) |
|---|---|---|
| 1 | Identify | "Qaysi modda kuchli kislota?" / "Qaysi reaksiya bu vaziyatda?" / "Qaysi xavfsizlik qoidasi?" |
| 2 | Decide | "Qaysi tartib bilan suyultiramiz?" / "Qaysi indikator mos?" / "Qaysi qadam birinchi?" |
| 3 | Justify | "Nima uchun aynan bu reaksiya?" / "Boshqa yo'l nega xavfli?" / "Qaysi umumiy xato bu vaziyatda?" |

---

## 3. Safety-first principle

Chemistry CBP often involves real safety stakes (acids, bases, flammables, toxic compounds). The case must:
- Start with the safety-relevant observation or task
- Make the safe vs unsafe choice the load-bearing decision
- Show on the wrong path what physically happens if the student picks the unsafe option (boil-over, gas evolution, burn)

NEVER trivialize safety. "The student dies" is too far; "the beaker cracks and the solution must be discarded" is right.

---

## 4. Concept-anchor rules (chemistry-family)

- Chemical formulas MUST match textbook (e.g., `NaCl`, `H₂SO₄`, `CO₂` — preserve subscript style).
- Equation balancing MUST be correct on the correct path; the wrong path can show an unbalanced equation as the consequence of skipping the balance step.
- Common mistakes are very common in chemistry: adding water to acid (vs acid to water), confusing oxidation with reduction, ignoring stoichiometric ratios.
- Final simulation MUST show the chemical or physical outcome ("balanced equation"; "white precipitate forms"; "no reaction observed").

---

## 5. Soft-retry rule (Forbid #19 — chemistry edition)

Regenerated variant keeps `core_concept` + `kind` + `common_mistake`. Mutate ≥1 of:
- The specific compounds (HCl → H₂SO₄ for an acid-base case, both still strong acids)
- The scene (lab → kitchen → cleaning closet)
- The character

Avoid: changing the reaction type (acid-base → redox would break concept identity).

---

## 6. Per-subject output shape

Universal JSON schema. Chemistry-specific notes:

- `metadata.case_type` → `"lab-safety"` or `"reaction-prediction"` or `"qualitative-test"`
- `metadata.required_skill` → "identify safe method", "predict reaction product", "balance equation"
- `final_simulation.visual_description` → describe color change, gas evolution, precipitate, balanced equation

---

## 7. Validation

Run `_cbp_contract.md §5` 18-item checklist. Chemistry watch-outs:

- Item 4 (source-aligned): chemical formulas and equations match the textbook
- Item 6 (consequence exists): chemistry has dramatic consequences — use them; don't soften
- Item 9 (Checkpoint 3 catches mistake): chemistry mistakes (water-to-acid, etc.) are well-documented; build the justify checkpoint around one
