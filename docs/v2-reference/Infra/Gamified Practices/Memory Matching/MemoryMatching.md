# Case-Based Preview Interaction Mode: Memory Matching — Aligned v1.1

> **Aligned version:** This file has been updated to satisfy the NETS Case-Based Preview standards from the first three uploaded prompt files: Math Family and Sciences.
> **Core fix:** Exactly three MCQ checkpoints are used, then a separate open-ended Decision Process Explanation appears before the final consequence.

## 1. Purpose

Memory Matching turns a textbook concept set into a memory-and-meaning case. The student first recognizes a valid pair, then reconstructs the meaning after support is hidden, then identifies why a close distractor is wrong.

This is not simple Memory Match. Matching is only the entry point. The learning target is reconstructing the source meaning without relying on card position.

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
  "card_pair_count": "4-8 default | fewer for lower grades"
}
```

---

## 3. Source Extraction

Extract only source-supported card content:

- Topic
- Core concept or concept set
- Main rule, formula, process, evidence chain, definition set, chronology, or term relationships
- 4–8 short card labels, meanings, examples, steps, symbols, or evidence items
- Key terms, matching Flashcards when provided
- Textbook example, diagram, table, glossary, or paragraph used
- Common mistake:
  - text: remembering location only, confusing close meanings, pairing surface-similar cards, or reconstructing the wrong relationship
  - provenance: `source` if stated, `inferred` if generated from likely student confusion
- Required skill: recall the meaning/role of matched items after visual support is removed

Card content must come from the source. Do not test decoration, color, or card position.

---

## 4. Usable Skill

The student should be able to say:

> I can remember what a term, step, symbol, example, or evidence item means even after the visual support is removed.

Supported pair types:

```txt
term ↔ meaning
process step ↔ result
evidence ↔ claim
word ↔ correct usage
symbol ↔ rule
historical event ↔ consequence
formula part ↔ quantity
organ/system part ↔ function
```

---

## 5. Case Rules

### Student role

The student must be a checker, organizer, lab assistant, source sorter, editor, reviewer, historian, or concept archivist.

### Card stage logic

1. Student identifies a valid pair.
2. Pair is briefly shown, then hidden.
3. Student reconstructs the meaning/role from memory.
4. Student explains why a close distractor does not fit.
5. Student sees recall result: recalled, guessed, missed, or position-memory only.

### Distractor rules

Distractors must be close enough to test meaning. Do not use random fake answers.

---

## 6. Visual Rules

Memory Matching is low-asset and works through cards, chips, slots, and simple result labels.

| Visual | Type | Used in | Purpose |
|---|---|---|---|
| Card grid | CSS / SVG | Case setup and Checkpoint 1 | Show face-up / face-down card interaction |
| Reconstruction slots | CSS / SVG / text | Checkpoint 2 | Empty slots where student rebuilds meaning from memory |
| Meaning chips | CSS / text | Checkpoint 2 | Show possible reconstructed meanings |
| Recall summary | Text / SVG | Final simulation | Separate recalled, guessed, missed, and position-only memory |

### Subject-family compatibility

- **Math / Algebra / Geometry:** Use SVG for symbols, formulas, quantity models, and diagrams.
- **Sciences:** Use image/placeholder only when a real organism, apparatus, or phenomenon scene helps. Use SVG/CSS for process cards and reconstruction slots.
- **Language / History / Literature:** Text cards are usually enough.

Image fallback:

```markdown
![placeholder: source-aligned memory case scene — image generation optional](placeholder)
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
- Required skill: Recall the meaning/role of matched items after visual support is removed
- Case type: Memory reconstruction case
- Student role:

## Source Extraction
- Core concept:
- Main rule / formula / process / relationship set:
- Key terms (must match Flashcards):
- Card pair set:
- Common mistake:
  - text:
  - provenance: source | inferred
- Textbook example used:

## Visual Plan
| Visual | Type | Used in | Purpose |
|---|---|---|---|
| Case scene | image OR placeholder OR none | Case setup | Real context only when useful |
| Card grid | css/svg | Checkpoint 1 | Show source-aligned pairs |
| Reconstruction slots | css/svg/text | Checkpoint 2 | Test meaning after cards are hidden |
| Recall summary | text/svg | Final simulation | Show remembered vs guessed vs missed items |

## Student View

### Case Setup
[2–4 sentence role-based case narrative. The student must need to organize and later reconstruct source meanings.]

### Checkpoint 1: Identify
- Question: Which two cards belong to the same textbook concept?
- Options (MCQ):
  - A. [Correct source-aligned pair]
  - B. [Surface-similar but wrong pair]
  - C. [Close distractor pair]
  - D. [Irrelevant pair]
- Correct answer:
- Feedback:

### Learning Block 1
[Explain that finding a pair is only the first step. The meaning must still be remembered after support is hidden.]

### Checkpoint 2: Decide
- Question: After the cards are hidden, which meaning/step/example belonged to the concept?
- Options (MCQ):
  - A. [Correct reconstructed meaning]
  - B. [Close distractor]
  - C. [Surface-similar distractor]
  - D. [Irrelevant distractor]
- Correct answer:
- Feedback:

### Learning Block 2
[Explain the function of reconstruction: the student remembers meaning, not card location.]

### Checkpoint 3: Justify / Avoid Mistake
- Question: Which explanation best shows why this pair and meaning are correct?
- Options (MCQ):
  - A. [Correct explanation using relationship type and source concept]
  - B. [Location-memory explanation only]
  - C. [Surface similarity explanation]
  - D. [Wrong relationship explanation]
- Correct answer:
- Feedback:

### Decision Process Explanation
- Prompt: "Walk through your reasoning — (1) which concept did you reconstruct, (2) why does this meaning belong to it, (3) what mistake would happen if you relied only on card position or a close distractor?"
- Expected components: source concept · reconstructed meaning/relationship · memory mistake
- Pass condition: Student references all three components in 2–4 sentences
- Sample acceptable answer:
- AI evaluation rubric:
  - Full: reconstructs the source meaning and rejects close distractor or location-only memory
  - Partial: finds pair but gives weak explanation of meaning
  - Retry: remembers only position, guesses, or cannot distinguish close distractor

### Final Simulation / Consequence
- Correct path: Student reconstructs the hidden meaning correctly and the summary marks the item as Recalled.
- Wrong path: Student matched cards by location but fails reconstruction; the summary marks Position Memory Only, Guessed, or Missed and returns the item to review.

Example result labels:

```txt
[ Concept A ] -> Recalled
[ Concept B ] -> Guessed
[ Concept C ] -> Missed
[ Concept D ] -> Position Memory Only
```

### AI Feedback Summary
- What student understood:
- What mistake appeared:
- What to review:
- Completion status: passed | Needs Retry
```

---

## 8. Completion Rules

- **Pass:** Student selects a valid source pair, reconstructs the hidden meaning, and explains the relationship before seeing the final consequence.
- **Needs Retry:** Student completes card flipping but cannot reconstruct meaning, relies on card position, confuses a close distractor, or skips the explanation.

---

## 9. Forbids

1. Do not create card content outside the textbook source.
2. Do not test card position, color, art, or decoration.
3. Do not make distractors random or silly.
4. Do not treat matching as mastery without reconstruction.
5. Do not turn Checkpoint 3 into the open-ended explanation. Checkpoint 3 must be MCQ.
6. Do not place the Decision Process Explanation after the consequence.
7. Do not auto-pass the explanation.
8. Do not change formulas, meanings, chronology, terms, units, or source logic.
9. Do not use terminology that conflicts with Flashcards.
10. Do not skip the wrong-path recall consequence.

---

## 10. Self-Check

```txt
[ ] Source concept set extracted
[ ] 4–8 card items are source-aligned
[ ] Pair relationship is source-supported
[ ] Student role creates a memory/reconstruction need
[ ] Exactly 3 MCQ checkpoints included
[ ] Checkpoint 3 is MCQ, not written reasoning
[ ] Decision Process Explanation included after C3
[ ] DPE is before final consequence
[ ] DPE asks for concept · meaning/relation · memory mistake
[ ] Final consequence separates recalled / guessed / missed / position-only
[ ] Key terms align with Flashcards
[ ] Common mistake provenance marked source | inferred
[ ] Subject-family visual rules followed
```

If any line fails, regenerate.
