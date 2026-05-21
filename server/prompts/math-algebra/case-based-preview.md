# Prompt: Case-Based Preview — Math / Algebra

**Family:** Math (math, algebra). Geometry has its own override file at `server/prompts/geometriya-g7-11/case-based-preview.md`.
**Shared contract:** `server/prompts/runtime/_cbp_contract.md` — read this first for the universal CBP rules, the 18-item validation checklist, the Uzbek register, and the JSON output schema.

This prompt only carries math-family deltas. The universal contract is non-negotiable.

---

## 1. Subject case archetype

Math is **practical-problem cases**: quantity, money, sharing, measurement, planning, comparison, error detection. The student is a planner, helper, buyer, builder, gardener, analyst, or measurer — someone who *needs* the math to make a decision.

Good math cases (concept is load-bearing):
- A school club splits a budget equally between groups (proper-fraction-by-natural-number division)
- A shopkeeper calculates change for fractional weights
- A carpenter divides a wooden plank into N equal pieces
- A delivery driver estimates remaining fuel along a route
- A student helps a classmate plan recipe scaling (proportions)

Bad math cases (dragon trap — strip the math, story still works):
- A wizard's spell requires fraction division to summon a familiar
- A spaceship pilot uses linear equations to negotiate with aliens
- A dragon opens a magic gate via algebra

---

## 2. Checkpoint shapes (math-family specific)

| # | Kind | Verb examples (Uz, formal Siz) |
|---|---|---|
| 1 | Identify | "Qaysi amal kerak?" / "Qaysi qoida qo'llaniladi?" / "Bu vaziyatda qaysi formula?" |
| 2 | Decide | "Qaysi qadam to'g'ri?" / "Qaysi formula bu masala uchun mos?" / "Qaysi raqamni avval olamiz?" |
| 3 | Justify | "Nima uchun bu yo'l to'g'ri?" / "Boshqa yo'l nega xato bo'ladi?" / "Qaysi umumiy xato bu masalada?" |

---

## 3. Concept-anchor rules (math-family)

- Numbers and units in the case MUST match the textbook example or be source-derivable. Never invent figures that contradict the chapter.
- Formula syntax MUST match the textbook (e.g., `a/b ÷ n` not `a/b / n` if the textbook uses the obelus).
- `common_mistake.provenance` is `"source"` ONLY if the textbook explicitly flags the mistake; `"inferred"` otherwise (Risk Audit §6 / Standard §3.1).
- Final simulation MUST show a numerical result on both paths (correct: X; wrong: Y or "impossible because…").

---

## 4. Soft-retry rule (Forbid #19 — math edition)

The regenerated variant must keep `core_concept` + `kind` + `common_mistake`. It must mutate at least one of:
- The **numbers** (e.g., `3/5 ÷ 3` → `4/7 ÷ 4`)
- The **scene** (juice → budget split → wooden plank)
- The **character names**

Generator-level lint: Jaccard token-similarity on `case_setup.story` MUST be < 0.6 between original and retake. If higher, regenerate.

---

## 5. Per-subject output shape

Use the universal JSON schema from `_cbp_contract.md §6`. Math-specific notes:

- `metadata.case_type` → `"practical-problem"`
- `metadata.required_skill` → an actionable verb phrase ("split a quantity equally", "translate word problem to equation", "choose right formula")
- `final_simulation.visual_description` → text like "Fraction bar showing 3/5 split into 3 equal parts; each part labeled 1/5." (SVG sanitized rendering lands in PR #6.)

---

## 6. Anti-patterns to reject

- MCQ options that include the obviously-impossible numeric answer (e.g., 9/5 for `3/5 ÷ 3`) should appear as a distractor labeled with the multiply-by-mistake reasoning — NOT as a "fun" option. The distractor must reflect a real common error.
- Free-response justify checkpoints — keep all three CBP checkpoints in MCQ or short-text mode for runtime grading reliability.
- "Bad math is funny" — never frame the wrong path as comedic. Frame it as the natural consequence of the common mistake.

---

## 7. Validation (before returning)

Run through `_cbp_contract.md §5` 18-item checklist. If any item is "no", regenerate. Pay extra attention to:
- Item 4 (source-aligned): formula and numbers match textbook
- Item 5 (decision-maker): student role is a math-doer, not a math-watcher
- Item 16 (formula preservation): no rewording the rule
