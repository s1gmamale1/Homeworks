# Case-Based Preview Interaction Mode: Tic-Tac-Toe Decision Grid — Aligned v1.1

> **Aligned version:** This file has been updated to satisfy the NETS Case-Based Preview standards from the first three uploaded prompt files: Math Family and Sciences.
> **Core fix:** Exactly three MCQ checkpoints are used, then a separate open-ended Decision Process Explanation appears before the final consequence.

## 1. Purpose

Tic-Tac-Toe Decision Grid turns a textbook concept into a 3×3 board decision case. The student identifies the source concept, chooses the best action from a board grid, justifies why the action fits, and then sees the consequence of the decision.

The grid must be solved through the lesson concept, not through general intuition. No "common sense only" cells.

---

## 2. Inputs

```json
{
  "subject": "math | algebra | geometry | physics | biology | chemistry | history | language | literature | other",
  "grade": "<grade number>",
  "language": "uz | ru | en",
  "textbook": "<filename>",
  "chapter": "<chapter name>",
  "section": "<section name>",
  "page_range": "<start-end>",
  "source_text": "<optional extracted text>",
  "images_or_diagrams": "<optional>",
  "flashcards_terms": ["<optional canonical lesson terms>"],
  "grid_size": "3x3 default | 2x2 for lower grades"
}
```

---

## 3. Source Extraction

Extract only from the textbook section:

- Topic
- Core concept
- Main rule, formula, process, mechanism, definition, or evidence principle
- Key terms, matching Flashcards when provided
- Textbook example, diagram, scenario, or worked problem used
- Decision condition: the clue that determines the correct action
- Common mistake:
  - text: choosing a surface-level, fast, unsafe, unsupported, or irrelevant strategy
  - provenance: `source` if the textbook states it, `inferred` if generated from likely student confusion
- Required skill: choose the best action/strategy for a situation and justify it using the lesson concept

The decision cells must test the extracted concept. A student should not solve the grid by generic test-taking logic.

---

## 4. Usable Skill

The student should be able to say:

> I can identify the lesson concept inside a situation and choose the action that correctly applies it.

Examples:

| Subject area | Decision skill |
|---|---|
| Math | Choose the correct formula, operation, diagram, or solving strategy |
| Physics | Choose the prediction/action that follows the law or mechanism |
| Chemistry | Choose the safe classification, reaction check, or handling step |
| Biology | Choose the mechanism, cause, or predicted response |
| Language | Choose the correction or register decision that preserves meaning |
| History | Choose the evidence, cause, or consequence that fits the source |

---

## 5. Case Rules

### Student role

The student must be a solver, advisor, checker, editor, analyst, observer, lab assistant, technician, historian, or planner.

### Grid structure

Default grid: **3×3**. For G2–G3 or simpler lessons, use **2×2**.

Each cell must be one of these:

- Correct action: directly applies the source concept
- Plausible but incomplete action
- Fast but unsafe/unsupported action
- Surface-clue action
- Irrelevant action
- Overly broad action
- Wrong-order action
- Distractor based on common mistake

### Bad grid cells

Do not include cells that are obviously silly. Distractors must be tempting for a real learner.

---

## 6. Visual Rules

Tic-Tac-Toe Decision Grid is low-asset and works with CSS/SVG.

| Visual | Type | Used in | Purpose |
|---|---|---|---|
| Decision board | CSS / SVG | Case setup and Checkpoint 2 | Show action cells |
| State meters | CSS / SVG / text | Feedback and final simulation | Show impact on accuracy, clarity, evidence, balance, risk, safety, or efficiency |
| Result panel | SVG / text | Final simulation | Compare correct strategy path and weak strategy path |

### Subject-family compatibility

- **Math / Algebra / Geometry:** Use SVG for formulas, figures, graphs, quantities, and before/after calculations.
- **Sciences:** Use image or placeholder for lab/field/phenomenon scene if it adds context. Use SVG/CSS for mechanism and meters.
- **Language / History / Literature:** Use text cards, evidence meters, clarity meters, and source panels.

Image fallback:

```markdown
![placeholder: source-aligned decision scene — image generation optional](placeholder)
```

---

## 7. Required Output Format

```markdown
# Case-Based Preview: [Title]

## Metadata
- Subject:
- Grade:
- Topic:
- Textbook address:
- Source concept:
- Required skill: Choose the best action/strategy and justify it using the lesson concept
- Case type: Practical decision case / communication case / historical decision case / observation case
- Student role:

## Source Extraction
- Core concept:
- Main rule / formula / process / mechanism:
- Key terms (must match Flashcards):
- Decision condition:
- Common mistake:
  - text:
  - provenance: source | inferred
- Textbook example used:

## Visual Plan
| Visual | Type | Used in | Purpose |
|---|---|---|---|
| Case scene | image OR placeholder OR none | Case setup | Real context only when useful |
| Decision board | css/svg | Checkpoint 2 | Show source-aligned action choices |
| State meters | css/svg/text | Feedback / consequence | Show visible impact of decision |
| Result panel | svg/text | Final simulation | Compare correct and weak path |

## Student View

### Case Setup
[2–4 sentence role-based case narrative. The student must need the lesson concept to choose an action.]

### Checkpoint 1: Identify
- Question: What is the main textbook concept controlling this situation?
- Options (MCQ):
  - A. [Correct source concept]
  - B. [Related but wrong concept]
  - C. [Surface clue only]
  - D. [Irrelevant detail]
- Correct answer:
- Feedback:

### Learning Block 1
[Explain why the correct concept controls the situation and why the distracting clue is not enough.]

### Checkpoint 2: Decide
- Question: Which board action is most suitable for this situation?
- Options (MCQ):
  - A. [Correct action cell]
  - B. [Plausible but incomplete action]
  - C. [Fast but unsafe/unsupported action]
  - D. [Irrelevant or surface action]
- Correct answer:
- Feedback: [Include meter changes such as Accuracy +30, Evidence +25, Risk -20, Safety +20]

### Learning Block 2
[Explain that the action is correct because it applies the source concept, not because it feels convenient.]

### Checkpoint 3: Justify / Avoid Mistake
- Question: Which explanation best justifies the chosen action and rejects the tempting weak strategy?
- Options (MCQ):
  - A. [Correct explanation using source concept + action reason]
  - B. [General intuition without lesson concept]
  - C. [Tempting but incomplete strategy]
  - D. [Wrong or unsafe strategy]
- Correct answer:
- Feedback:

### Decision Process Explanation
- Prompt: "Walk through your reasoning — (1) which concept did you spot, (2) why did this action fit better than the alternatives, (3) what mistake would happen with the weak strategy?"
- Expected components: source concept · selected action · tempting mistake
- Pass condition: Student references all three components in 2–4 sentences
- Sample acceptable answer:
- AI evaluation rubric:
  - Full: identifies concept, explains why action fits, rejects weak strategy
  - Partial: chooses correct action but explanation is vague or misses the mistake
  - Retry: chooses by general intuition, skips source concept, or cannot explain the weak path

### Final Simulation / Consequence
- Correct path: [Correct action] improves the visible state meters and produces a solved/controlled outcome.
- Wrong path: [Tempting weak action] worsens at least one meter and explains why the result does not satisfy the lesson concept.

Example meter format:

```txt
Correct path:
Accuracy: 85%   Evidence: 75%   Risk: 20%

Weak path:
Accuracy: 45%   Evidence: 30%   Risk: 70%
```

### AI Feedback Summary
- What student understood:
- What mistake appeared:
- What to review:
- Completion status: passed | Needs Retry
```

---

## 8. Completion Rules

- **Pass:** Student identifies the source concept, chooses a source-aligned board action, and explains the action before seeing the final consequence.
- **Needs Retry:** Student chooses an action that can be selected without the lesson concept, skips explanation, or cannot explain why the tempting wrong strategy fails.

---

## 9. Forbids

1. Do not invent textbook facts, formulas, laws, mechanisms, definitions, or historical relationships.
2. Do not make the correct cell solvable by general intuition alone.
3. Do not use random or silly distractors.
4. Do not turn Checkpoint 3 into the open-ended explanation. Checkpoint 3 must be MCQ.
5. Do not place the Decision Process Explanation after the consequence.
6. Do not auto-pass the explanation.
7. Do not use decorative animations as learning evidence.
8. Do not change numbers, formulas, terms, units, chronology, safety rules, or source meaning.
9. Do not use terminology that conflicts with Flashcards.
10. Do not skip the wrong-path consequence.

---

## 10. Self-Check

```txt
[ ] Source concept extracted
[ ] Decision condition extracted
[ ] Student role creates a real decision need
[ ] Board actions are source-aligned
[ ] Distractors are plausible but wrong
[ ] Exactly 3 MCQ checkpoints included
[ ] Checkpoint 3 is MCQ, not written reasoning
[ ] Decision Process Explanation included after C3
[ ] DPE is before final consequence
[ ] DPE asks for concept · action · mistake
[ ] Final consequence shows correct path and weak path
[ ] Meters reflect source-based consequence, not decorative scoring
[ ] Key terms align with Flashcards
[ ] Common mistake provenance marked source | inferred
[ ] Subject-family visual rules followed
```

If any line fails, regenerate.
