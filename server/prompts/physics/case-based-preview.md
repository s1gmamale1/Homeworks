# Prompt: Case-Based Preview — Physics

**Family:** Sciences.
**Shared contract:** `server/prompts/runtime/_cbp_contract.md` — universal CBP rules, 18-item checklist, Uzbek register, JSON output schema.

---

## 1. Subject case archetype

Physics cases are **phenomenon → prediction → formula/logic → consequence** scenarios. The student observes a real-world phenomenon and must predict what will happen, choose the right formula or principle, then justify why the prediction holds.

Good physics cases:
- A bicycle wheel slows after the rider stops pedaling (friction / Newton's first law)
- A student adjusts the angle of a ramp to roll a marble at a target speed (motion / acceleration)
- An electrician designs a flashlight circuit needing exactly 4.5 V (series vs parallel batteries / Ohm's law)
- A child throws a ball straight up; how high does it go? (projectile motion, energy conservation)
- A swimmer notices their underwater watch reads a different depth than expected (pressure)

Bad physics cases:
- "Solve for x using F=ma" with no scenario — that's a problem set, not a CBP
- Stories where the physics is mentioned but the answer doesn't require it

---

## 2. Checkpoint shapes (physics-specific)

| # | Kind | Verb examples (Uz, formal Siz) |
|---|---|---|
| 1 | Identify | "Qaysi kuch ta'sir qiladi?" / "Qaysi qonun bu vaziyatga tegishli?" / "Qaysi formula kerak?" |
| 2 | Decide | "Qaysi miqdorni avval hisoblaymiz?" / "Qaysi yo'nalishni tanlaymiz?" / "Qaysi formulani qo'llaymiz?" |
| 3 | Justify | "Nima uchun aynan bu kuch?" / "Boshqa javob nega fizik jihatdan noto'g'ri?" / "Qaysi xato keng tarqalgan?" |

---

## 3. Phenomenon-first principle

Physics CBP must start from the observable phenomenon (what the student sees / feels / measures) → predict outcome → identify formula or principle → confirm with reasoning.

NEVER start with the formula. Opening with "Newton's second law states F=ma" loses the case. Open with "A box slides across the floor and slows to a stop — why?"

---

## 4. Concept-anchor rules (physics-family)

- Variable letters MUST match the textbook (`F` for force, `m` for mass, `a` for acceleration in SI convention).
- Units MUST be preserved: meters, seconds, kilograms, Newtons, joules, etc. Don't substitute "feet" or "pounds".
- Common mistakes are often sign errors, unit confusion, or applying a formula to the wrong domain (Newton's laws assume constant mass; ideal-gas law assumes ideal gas).
- Final simulation MUST give a numerical answer on the correct path AND name the principle violated on the wrong path.

---

## 5. Soft-retry rule (Forbid #19 — physics edition)

Regenerated variant preserves `core_concept` + `kind` + `common_mistake`. Mutate ≥1 of:
- Numerical values (different force, mass, angle, voltage)
- The scenario (bicycle → toy car → roller skate, all friction examples)
- The character

Avoid: changing the physics principle itself.

---

## 6. Per-subject output shape

Universal JSON schema. Physics-specific notes:

- `metadata.case_type` → `"phenomenon"` or `"prediction"`
- `metadata.required_skill` → "identify the force", "choose the correct formula", "predict motion"
- `final_simulation.visual_description` → describe before/after motion, force arrows, energy state, or circuit diagram

---

## 7. Validation

Run `_cbp_contract.md §5` 18-item checklist. Physics watch-outs:

- Item 4 (source-aligned): formulas match the textbook's convention exactly
- Item 16 (units preserved): SI units, no implicit unit conversion
- Item 12 (visuals): force arrows / before-after states ARE the visual; describe them precisely for PR #6's SVG renderer
