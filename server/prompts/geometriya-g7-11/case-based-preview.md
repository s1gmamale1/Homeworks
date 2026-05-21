# Prompt: Case-Based Preview — Geometriya (G7–11)

**Family:** Math, with geometry-specific overrides.
**Shared contract:** `server/prompts/runtime/_cbp_contract.md` — universal CBP rules, the 18-item checklist, Uzbek register, and the JSON output schema.
**Sibling:** `server/prompts/math-algebra/case-based-preview.md` — the algebra-side math-family prompt.

This file extends the math family with geometry-specific case patterns and visual emphasis.

---

## 1. Subject case archetype

Geometry is the visual-spatial branch of the math family. Cases lean toward **construction, measurement, fencing, layout, design** — anywhere a real geometric relationship determines a decision.

Good geometry cases:
- A gardener fences a triangular plot and needs to estimate perimeter / required wire
- A carpenter cuts a board at a specific angle and needs to identify which side to measure
- A student designs a poster layout where two rectangular sections share a diagonal
- A surveyor checks whether two streets meet at a right angle using a ladder against a wall (Pythagoras)
- A baker fits round trays of different radii into a rectangular oven

Bad geometry cases:
- Anything where the shape is mentioned but the calculation could be done without geometry
- Pure abstract proofs framed as "in this story" — geometry CBP at this layer is recognition + application, not proof

---

## 2. Checkpoint shapes (geometry-specific)

| # | Kind | Verb examples (Uz, formal Siz) |
|---|---|---|
| 1 | Identify | "Bu vaziyatda qaysi geometrik shakl?" / "Qaysi xossa qo'llaniladi?" / "Qaysi formula bu uchburchakka mos?" |
| 2 | Decide | "Qaysi tomoni o'lchaymiz?" / "Qaysi formula bu masala uchun to'g'ri?" / "Qaysi qadam keyingi?" |
| 3 | Justify | "Nega bu uchburchak to'g'ri burchakli?" / "Nega katet emas, gipotenuza?" / "Qaysi umumiy xato bu vaziyatda?" |

---

## 3. Geometry-specific visual emphasis

Geometry has the **strongest visual demand** in the math family. The `final_simulation.visual_description` for geometry CBP should describe:

- The geometric figure in the scene (triangle, circle, rectangle, etc.)
- Which sides/angles are known vs. unknown
- Where the right-angle or symmetry mark goes
- Labels for letters / numbers

Example: "Right triangle. Vertical leg = 12 (wall height to ladder top). Horizontal leg = 5 (base distance). Hypotenuse = 13 (ladder length). Right-angle mark at the wall-ground corner."

PR #6 will add sanitized SVG rendering of these descriptions. For v1, text is sufficient and parseable.

---

## 4. Concept-anchor rules (geometry-family)

- Side/angle labels MUST match the textbook's letters (e.g., if the textbook uses `a, b, c` for triangle sides, the case uses those — not `x, y, z`).
- Formula syntax MUST match the textbook (e.g., `a² + b² = c²` for Pythagoras, not `a^2 + b^2`).
- Common-mistake provenance follows the math-family rule: `"source"` if textbook flags it, `"inferred"` otherwise.
- Final simulation MUST show both numerical AND geometric reasoning ("Hypotenuse = √(5² + 12²) = 13 meters. The ladder is just long enough.").

---

## 5. Soft-retry rule (Forbid #19 — geometry edition)

The regenerated variant keeps `core_concept` + `kind` + `common_mistake`. Mutate at least one of:
- Numerical values (different leg lengths)
- The scene (ladder → kite string → garden fence)
- The character / role

Avoid: mutating the geometric shape itself (changing triangle to circle would change the concept).

---

## 6. Per-subject output shape

Universal JSON schema from `_cbp_contract.md §6`. Geometry-specific notes:

- `metadata.case_type` → `"geometric-construction"` or `"practical-problem"` (geometry sub-type)
- `metadata.required_skill` → "identify the right triangle", "choose the correct side", "apply the Pythagorean theorem", etc.
- `final_simulation.visual_description` — extra-rich (see §3 above). Spell out figure, knowns, unknowns, labels.

---

## 7. Validation

Run `_cbp_contract.md §5` 18-item checklist. Geometry-specific watch-outs:

- Item 12 (visuals support learning): visual description names the figure, the right-angle mark, the labels
- Item 13 (image vs SVG): geometry leans heavily toward SVG (deferred to PR #6); v1 text descriptions must be precise enough that PR #6 can convert them mechanically
- Item 16 (formula preservation): no rewording theorems
