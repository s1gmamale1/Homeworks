# NETS Case-Based Preview — Generation Prompt: Math Family

**Subjects covered:** Math, Algebra, Geometry
**Source standard:** NETS Case-Based Preview Generation Standard v1.1
**Companion file (Uzbek validation):** `NETS_Uzbek_Language_Foundation_Review_v1_3.md` — the Uzbek Language Foundation standard. Owns language quality, simplification rules, formal register, cultural context, and subject-specific Uzbek guardrails. Reference this file for any Uzbek validation question.

> This document IS the prompt. An AI given a textbook address and these rules should be able to generate a Case-Based Preview without further human guidance.

---

## 1. Context (small)

You are generating one **Case-Based Preview**: a short guided learning case that turns a math/algebra/geometry textbook section into a student-facing decision situation.

The student must be a decision-maker, not a reader. They face three MCQ-style recognition checkpoints, then write a short explanation of their reasoning, then see the consequence of their choices.

**Stakes:** low-to-medium. This is meaning-building, not final mastery.

You do not need to know anything else about where this fits in the larger homework flow. Just produce one CBP.

---

## 2. Inputs

```json
{
  "subject": "math" | "algebra" | "geometry",
  "grade": <number>,
  "language": "uz" | "ru" | "en",
  "textbook": "<filename>",
  "chapter": "<chapter name>",
  "section": "<section name>",
  "page_range": "<start-end>",
  "source_text": "<optional extracted text>",
  "images_or_diagrams": "<optional>",
  "flashcards_terms": "<optional array of canonical lesson terms>"
}
```

If `source_text` is provided, use it. Otherwise retrieve the textbook content from the address.

---

## 3. How — Process

### Step 1 — Extract source facts

Pull from the textbook section:

- topic
- core concept (e.g. "dividing a proper fraction by a natural number")
- main rule / formula (e.g. `a/b ÷ n = a/(b·n)`)
- key terms — **must match Flashcards** if `flashcards_terms` provided; otherwise extract canonical lesson terms
- textbook example problems
- visual models if any
- common mistake — flag `provenance: "source"` if textbook lists it, `"inferred"` if you derived it
- required skill (what the student must **do**, not just know)

### Step 2 — Find the usable skill

Don't stop at the topic name. Ask: what action should the student perform after this lesson?

| Topic example | Usable skill |
|---|---|
| Fractions | Split a quantity equally |
| Percentages | Choose correct percent model |
| Linear equations | Translate word problem to equation |
| Right triangles | Identify which side to find |
| Circle area / circumference | Choose right formula |

### Step 3 — Pick or create the case

**Priority A** — adapt a real-life example the textbook already gives.
*Example: textbook gives `3/5 ℓ orange juice shared into 3 cups` → case becomes "student helps distribute juice at a class event."*

**Priority B** — convert a textbook diagram into a fresh NETS visual. Don't copy the textbook image.

**Priority C** — create a plausible case. Fictional OK, concept must remain source-aligned.

**Good cases (math family):**
- A school club splits a budget equally between groups
- A shopkeeper calculates change for fractional weights
- A carpenter divides a wooden plank
- A gardener fences a triangular plot
- A delivery driver estimates remaining fuel for a route

**Bad cases (never use):**
- A dragon needs algebra to open a magic gate
- A wizard's spell requires fraction division to summon a familiar
- A spaceship pilot uses linear equations to negotiate with aliens

Why bad: strip the math out and the story still works. The concept must be load-bearing, not decorative.

### Step 4 — Place the student

Student must be a planner, helper, buyer, builder, gardener, analyst, or measurer — someone who *needs* the math to make a decision.

### Step 5 — Build 3 checkpoints

| # | Type | Purpose | Format |
|---|------|---------|--------|
| C1 | Identify | Recognize which operation/concept applies | MCQ |
| C2 | Decide | Choose correct formula or step | MCQ |
| C3 | Justify | Pick why correct works / why mistake fails | MCQ |

All three may be MCQ. The student is recognizing here, not producing reasoning.

### Step 6 — Decision Process Explanation (slot 7, **BEFORE** consequence)

After C3 and **before** the final consequence, present one open-ended prompt with three sub-questions:

> Walk through your reasoning:
> 1. Which concept did you spot in the situation?
> 2. Why did you pick this method over the alternatives?
> 3. What mistake would have happened with the wrong choice?

**Non-negotiable rules:**
- This is NOT a fourth MCQ
- Must be placed BEFORE the consequence reveal (otherwise student rationalizes backwards)
- Student writes 2–4 sentences total
- AI evaluates: response must reference (1) correct concept, (2) correct method, (3) common mistake. Partial credit allowed.

### Step 7 — Final consequence

Show both paths:
- **Correct path** — the right result (e.g. `3/5 ÷ 3 = 1/5 ℓ` per cup)
- **Wrong path** — the common mistake's outcome and why it fails (e.g. `3/5 × 3 = 9/5 ℓ`, impossible because only 3/5 ℓ existed)

### Step 8 — Feedback summary

For the whole case:
- What the student understood
- What mistakes appeared (per checkpoint + per explanation)
- What to review
- Completion status: passed / Needs Retry

---

## 4. How — Visual rules (Math family)

**Default: SVG.** Math is numeric and structural. SVG handles math content better than raster images.

### Use SVG for:

- Fraction bars, area models
- Coordinate planes, graphs, function plots
- Geometric figures (triangles, polygons, circles, angles, constructions)
- Charts and tables
- Step-by-step state diagrams (multi-chained concept breakdowns)
- Before/after states (e.g., 3/5 full glass → split into 3 cups)
- Formula visualizations
- Number lines

### Use image for:

- Real-world scene context (student at market, club meeting, workshop)
- Strong illustrative atmosphere when SVG can't carry meaning
- Cases needing human or environmental presence

### Multi-chained concepts:

Always SVG. A 4-step SVG state diagram reads better than one dense image.

### Geometry specifically:

Strongest visual demand of the math family. Geometric figures are inherently SVG-friendly — use SVG for any figure, angle, polygon, or construction. Use image only for real-world context (e.g., student measuring an actual garden) before transitioning to the SVG geometric model.

### Image-generation fallback:

If image generation is unavailable, leave a placeholder and continue:

```markdown
![placeholder: student distributing juice at class event — image gen required](placeholder)
```

Never block on missing images.

---

## 5. Case patterns — Math family

| Case type | Student role | Decision type |
|---|---|---|
| Practical sharing | Helper distributing a quantity | Which operation? |
| Money / change | Shopkeeper or buyer | Which arithmetic step? |
| Measurement | Builder, gardener, planner | Which formula? |
| Comparison | Analyst | Which is bigger / cheaper / better? |
| Error detection | Reviewer of someone's work | Which step is wrong? |
| Geometric construction | Builder, designer | Which shape / measurement? |

**Checkpoint pattern (all math family):**
1. C1 — identify operation / model / figure
2. C2 — choose formula or step
3. C3 — explain why common mistake fails

**Final consequence:** show correct quantity + show wrong path producing an impossible or illogical result.

---

## 6. What — Output format

```markdown
# Case-Based Preview: [Title]

## Metadata
- Subject: [math / algebra / geometry]
- Grade:
- Topic:
- Textbook address:
- Source concept:
- Required skill:
- Case type:
- Student role:

## Source Extraction
- Core concept:
- Main rule / formula:
- Key terms (must match Flashcards):
- Common mistake:
  - text:
  - provenance: source | inferred
- Textbook example used:

## Visual Plan
| Visual | Type | Used in | Purpose |
|---|---|---|---|
| Case scene | image OR placeholder | Case setup | Real-life context |
| Concept model | svg | Learning block / checkpoint | Show formula / figure |
| Consequence | svg | Final simulation | Correct + wrong path |

## Student View

### Case Setup
[2–4 sentence case narrative]
[scene image or placeholder]

### Checkpoint 1: Identify
- Question:
- Options (MCQ):
- Correct answer:
- Feedback:

### Learning Block 1
[short explanation; SVG of concept if helpful]

### Checkpoint 2: Decide
- Question:
- Options (MCQ):
- Correct answer:
- Feedback:

### Learning Block 2
[short explanation; SVG of method if helpful]

### Checkpoint 3: Justify / Avoid Mistake
- Question:
- Options (MCQ):
- Correct answer:
- Feedback:

### Decision Process Explanation
- Prompt: "Walk through your reasoning — (1) which concept, (2) why this method, (3) what mistake?"
- Expected components: concept · method · mistake
- Pass condition: response references all three
- Sample acceptable answer:
- AI evaluation rubric:

### Final Simulation / Consequence
- Correct path: [text + SVG]
- Wrong path: [text + SVG showing failure]

### AI Feedback Summary
- What student understood:
- What mistake appeared:
- What to review:
- Completion status: passed | Needs Retry
```

---

## 7. What — Forbids

### General (apply to all CBP generation)
1. Pretending to replace the textbook
2. Inventing textbook facts, formulas, definitions
3. Losing the source concept in the case
4. Skipping checkpoint-based learning (3 required)
5. Student is not the decision-maker
6. Checkpoint decisions with no consequence
7. Replacing Decision Process Explanation with a 4th MCQ
8. Placing Decision Process Explanation AFTER the consequence
9. Auto-passing the open-ended explanation without evaluation
10. Using terminology that doesn't match the lesson's Flashcards

### Math family specific
11. Changing numbers, variables, formulas, units, or calculation order
12. Decorative SVGs that don't carry the actual problem's content
13. The "dragon needs algebra" trap — math must be load-bearing in the case
14. Copying textbook artwork directly
15. SVGs with unreadable labels or tiny figures
16. Using image where SVG would do the math content better

---

## 8. Uzbek language (when language=uz)

For Uzbek validation, defer to **`NETS_Uzbek_Language_Foundation_Review_v1_3.md`** — the Uzbek Language Foundation standard. It owns language quality, simplification, formal register, and cultural context. Critical points to enforce in this prompt:

- Formal **Siz** — never `sen` / `san`
- Short logical sentences; student-friendly wording
- Never change numbers, formulas, variables, units, or calculation order in translation
- No Russian or English calques (e.g., don't directly translate Russian sentence structure)
- Explain hard terms inline; never assume

---

## 9. Self-check (run before output)

```txt
[ ] Source topic identified
[ ] Required student skill identified
[ ] Case is source-aligned (concept preserved)
[ ] Student is decision-maker
[ ] Exactly 3 MCQ checkpoints (C1: Identify, C2: Decide, C3: Justify)
[ ] Decision Process Explanation present
[ ] DPE placed BEFORE final consequence
[ ] DPE has 3 sub-prompts (concept · method · mistake)
[ ] DPE is open-ended, NOT MCQ
[ ] Final consequence shown with correct path AND wrong path
[ ] SVG used for math content (figures, fractions, charts, state diagrams)
[ ] Image (or placeholder) used only for real-life scene
[ ] Geometry: figures rendered as SVG, real-world scene as image
[ ] Key terms align with Flashcards
[ ] Common mistake provenance marked (source / inferred)
[ ] Inferred mistakes NOT presented as textbook-stated
[ ] Numbers, formulas, units preserved
[ ] No decorative visuals
[ ] Uzbek is formal, clear, student-friendly (if applicable)
```

If any line fails, regenerate.

---

## 10. Final test

The output is valid only if the student can say:

> I know what situation I was in.
> I know what decision I made.
> I know which textbook concept helped me.
> I explained my reasoning before seeing the outcome.
> I saw what happened because of my choice.
> I understand the main mistake to avoid.

If the student only read an explanation, regenerate.

---

*End of Math Family Generation Prompt.*
