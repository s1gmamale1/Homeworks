# Case-Based Preview Interaction Mode: Jigsaw Matching — Aligned v1.1

> **Aligned version:** This file has been updated to satisfy the NETS Case-Based Preview standards from the first three uploaded prompt files: Math Family and Sciences.
> **Core fix:** Exactly three MCQ checkpoints are used, then a separate open-ended Decision Process Explanation appears before the final consequence.

## 1. Purpose

Jigsaw Matching turns a textbook concept into a puzzle-style relationship-reasoning case. The student does not only match two items. The student must decide **which two source-supported nodes fit together**, **what complete concept they form when assembled**, and **why the wrong piece combination cannot fit**.

This is a Case-Based Preview interaction pattern, not a replacement for the textbook. The generator must fill it using the extracted textbook section.

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
  "allowed_jigsaw_types": ["concept-definition", "formula-variable", "cause-effect", "evidence-claim", "step-result", "term-example"]
}
```

If `flashcards_terms` are provided, piece labels and assembly wording must align with those terms.

---

## 3. Source Extraction

Extract only source-supported material:

- Topic
- Core concept
- 3–6 related piece nodes from the textbook section
- Main rule, formula, process, evidence chain, cause/effect link, or example relationship
- Key terms, matching Flashcards when provided
- Textbook example, diagram, table, or paragraph used
- Common mistake:
  - text: choosing a surface-related but unsupported pair, choosing the wrong direction, or connecting surface-related nodes
  - provenance: `source` if the textbook states it, `inferred` if generated from likely student confusion
- Required skill: connect two items and select the correct assembly relationship type

An assembly is valid only if the relationship type is supported by the source. Do not create a relationship because it "sounds right."

---

## 4. Usable Skill

The student should be able to say:

> I can identify two textbook concepts that fit together and explain the complete concept they form.

Examples:

| Source type | Usable skill |
|---|---|
| Cause and effect | Choose which event causes or leads to another |
| Evidence and claim | Select which evidence supports a claim |
| Rule and example | Connect a rule to the example that uses it |
| Formula and quantity | Connect a variable to what it represents |
| Process step and result | Connect a step to its outcome |

---

## 5. Case Rules

### Student role

The student must act as a puzzle assembler, source checker, analyst, editor, technician, historian, or reviewer. They are not a passive reader.

### Allowed assembly types

Use a maximum of **3 assembly types per round** for MVP clarity.

Recommended type pool:

```txt
concept-definition / formula-variable / cause-effect / evidence-claim / step-result / term-example
```

### Good cases

- A student checks whether an example supports a science claim
- A technician connects a circuit fault to its cause
- A historian connects an event to its consequence
- A math learner connects a formula term to the quantity it represents
- A language editor connects a rule to a sentence correction

### Bad cases

- Decorative concept puzzles with no source-supported relationships
- Random matching where either pair could be argued as correct
- "Vibes-based" links that are not in the textbook section
- Assembly types that are too broad to test the lesson concept

---

## 6. Visual Rules

Jigsaw Matching is low-asset by default. Use cards, pieces, CSS, and SVG assembly animations.

| Visual | Type | Used in | Purpose |
|---|---|---|---|
| Piece cards | CSS / SVG | Case setup | Show concepts, examples, evidence, rules, or outcomes |
| Assembly slots | SVG | Checkpoints and consequence | Show selected assembly direction and completeness |
| Assembly type labels | CSS / text | Checkpoint 2 | Let student choose the source-supported assembly relation |
| Result puzzle | SVG / text | Final simulation | Compare valid assembly vs weak assembly |

### Subject-family compatibility

- **Math / Algebra / Geometry:** SVG is preferred for math content, formulas, figures, graphs, number lines, and relationship diagrams.
- **Sciences:** Use image or placeholder for real lab/field/phenomenon context when needed, then SVG/CSS for the relationship puzzle and mechanism breakdown.
- **Language / History / Literature:** Text cards and simple source-evidence puzzles are enough.

Image fallback:

```markdown
![placeholder: source-aligned case scene — image generation optional](placeholder)
```

Do not block generation if image generation is unavailable.

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
- Required skill: Connect two source items and choose the correct assembly relationship type
- Case type: Relationship reasoning case
- Student role:

## Source Extraction
- Core concept:
- Main rule / formula / process / evidence relationship:
- Key terms (must match Flashcards):
- Piece set:
- Allowed assembly types for this round:
- Common mistake:
  - text:
  - provenance: source | inferred
- Textbook example used:

## Visual Plan
| Visual | Type | Used in | Purpose |
|---|---|---|---|
| Case scene | image OR placeholder OR none | Case setup | Real context only when useful |
| Piece cards | css/svg | Checkpoints | Show selectable source items |
| Assembly model | svg | Learning blocks / consequence | Show source-supported relation |
| Result puzzle | svg/text | Final simulation | Compare correct and weak assembly |

## Student View

### Case Setup
[2–4 sentence role-based case narrative. The student must need the assembly relationship to make a decision.]

### Checkpoint 1: Identify
- Question: Which pair of pieces truly fits together in the textbook situation?
- Options (MCQ):
  - A. [Correct source-supported pair]
  - B. [Surface-related but unsupported pair]
  - C. [One correct node + one wrong node]
  - D. [Irrelevant or reversed pair]
- Correct answer:
- Feedback:

### Learning Block 1
[Explain that the pair is valid only because the source gives a relationship between them.]

### Checkpoint 2: Decide
- Question: Which assembly type label correctly connects the selected pieces?
- Options (MCQ):
  - A. [Correct assembly type label]
  - B. [Related but wrong label]
  - C. [Too broad label]
  - D. [Opposite or reversed label]
- Correct answer:
- Feedback:

### Learning Block 2
[Explain direction and role: Piece A does not merely sit near Piece B; it causes/supports/depends on/etc.]

### Checkpoint 3: Justify / Avoid Mistake
- Question: Which explanation best proves the assembly relationship and avoids the tempting wrong label?
- Options (MCQ):
  - A. [Correct explanation using source concept + assembly type label]
  - B. [Correct pair but wrong relationship]
  - C. [Surface similarity explanation]
  - D. [Unsupported or reversed explanation]
- Correct answer:
- Feedback:

### Decision Process Explanation
- Prompt: "Walk through your reasoning — (1) which concept did you spot, (2) why is this assembly type label correct, (3) what mistake would happen with the wrong label or weak pair?"
- Expected components: source concept · assembly relationship label · common mistake
- Pass condition: Student references all three components in 2–4 sentences
- Sample acceptable answer:
- AI evaluation rubric:
  - Full: names the source concept, uses the correct relationship, rejects the tempting wrong pair/label
  - Partial: identifies pair but gives weak or incomplete relationship explanation
  - Retry: only says the pieces are "similar" or cannot explain the relationship

### Final Simulation / Consequence
- Correct path: [Piece A] — [correct assembly relationship] → [Piece B]. The line is solid and locked because the relationship is source-supported.
- Wrong path: [Wrong pair OR wrong relationship]. The line is dotted/crossed because the relationship is unsupported, reversed, or too broad.

### AI Feedback Summary
- What student understood:
- What mistake appeared:
- What to review:
- Completion status: passed | Needs Retry
```

---

## 8. Completion Rules

- **Pass:** Student selects a valid source pair, chooses the correct assembly type, and explains the relationship before seeing the final consequence.
- **Needs Retry:** Student only matches pieces without relationship reasoning, chooses a relationship not supported by the source, reverses the direction, or skips the explanation.

---

## 9. Forbids

1. Do not invent textbook relationships.
2. Do not treat surface similarity as a valid connection.
3. Do not use more than 3 assembly types in one MVP round.
4. Do not turn Checkpoint 3 into the open-ended explanation. Checkpoint 3 must be MCQ.
5. Do not place the Decision Process Explanation after the consequence.
6. Do not auto-pass the explanation.
7. Do not copy textbook diagrams directly.
8. Do not use decorative node puzzles that do not carry the actual source relationship.
9. Do not change formulas, numbers, terms, chronology, causes, or evidence meaning.
10. Do not use terminology that conflicts with Flashcards.

---

## 10. Self-Check

```txt
[ ] Source concept extracted
[ ] 3–6 source-supported pieces extracted
[ ] Assembly types limited to 3 for the round
[ ] Student is decision-maker / assembler / checker
[ ] Exactly 3 MCQ checkpoints included
[ ] Checkpoint 3 is MCQ, not written reasoning
[ ] Decision Process Explanation included after C3
[ ] DPE is before final consequence
[ ] DPE asks for concept · relationship · mistake
[ ] Correct path and wrong path both shown
[ ] Wrong path explains weak/unsupported/reversed relation
[ ] Key terms align with Flashcards
[ ] Common mistake provenance marked source | inferred
[ ] Visuals are low-asset and source-carrying, not decorative
[ ] Subject-family visual rules followed
```

If any line fails, regenerate.
