# Case-Based Preview Interaction Mode: English Fill-in-the-Blanks — Aligned v1.1

> **Aligned version:** This file has been updated to satisfy the NETS Case-Based Preview standards from the first three uploaded prompt files: Math Family and Sciences.
> **Core fix:** Exactly three MCQ checkpoints are used, then a separate open-ended Decision Process Explanation appears before the final consequence.

## 1. Purpose

English Fill-in-the-Blanks turns a textbook rule, definition, process, cause/effect relation, or wording principle into an error-detection case. The student diagnoses the wrong phrase, chooses the source-aligned repair, identifies why the repair works, and explains the decision before seeing the final meaning test.

This is not a cloze exercise. There is no empty blank. The student must find the broken part first.

---

## 2. Inputs

```json
{
  "subject": "language | literature | science | history | math | other",
  "grade": "<grade number>",
  "language": "uz | ru | en",
  "textbook": "<filename>",
  "chapter": "<chapter name>",
  "section": "<section name>",
  "page_range": "<start-end>",
  "source_text": "<optional extracted text>",
  "images_or_diagrams": "<optional>",
  "flashcards_terms": ["<optional canonical lesson terms>"],
  "sentence_type": "definition | explanation | cause/effect | grammar/register | evidence claim | process statement"
}
```

---

## 3. Source Extraction

Extract only source-supported wording logic:

- Topic
- Core concept
- Main rule, definition, process, event relationship, grammar point, register rule, formula meaning, or evidence claim
- Key terms, matching Flashcards when provided
- Correct sentence meaning that must be preserved
- Broken word/phrase that creates a real misconception
- Replacement phrase that restores source meaning
- Textbook example, definition, sentence, rule, or paragraph used
- Common mistake:
  - text: fluent but conceptually wrong wording, wrong register, wrong cause/effect relation, wrong term, too broad/narrow phrase, or changed source meaning
  - provenance: `source` if stated, `inferred` if generated from likely student confusion
- Required skill: detect a wrong word/phrase, replace it, and justify the repaired meaning

The sentence must fail because of the lesson concept, not because of random grammar weirdness.

---

## 4. Usable Skill

The student should be able to say:

> I can identify the exact phrase that changes the source meaning and repair it without changing the textbook concept.

Supported sentence types:

```txt
definition repair
science mechanism wording
history cause/effect correction
literature interpretation wording
grammar/register correction
math formula meaning statement
source evidence claim repair
```

---

## 5. Case Rules

### Student role

The student must be an editor, message checker, source checker, lab note reviewer, historian, explanation improver, translator-checker, or proofreader.

### Broken sentence rules

The broken sentence should be mostly fluent. The error should be tempting, not nonsense.

Wrong phrase types:

- wrong technical term
- wrong cause/effect connector
- opposite meaning
- too broad or too narrow wording
- informal register where formal wording is required
- changed formula/unit/variable meaning
- unsupported evidence claim

### Replacement chip rules

Each replacement chip must test the concept:

- Correct repair
- Grammatically possible but conceptually wrong
- Conceptually close but too broad/narrow
- Irrelevant or wrong-register replacement

---

## 6. Visual Rules

English Fill-in-the-Blanks is low-asset and mostly text-based.

| Visual | Type | Used in | Purpose |
|---|---|---|---|
| Broken sentence card | Text / CSS | Case setup and Checkpoint 1 | Show selectable phrase chunks |
| Replacement chips | CSS / text | Checkpoint 2 | Let student choose the repair |
| Meaning test panel | Text / SVG | Final simulation | Show whether meaning, wording/register, and source concept pass |

### Subject-family compatibility

- **Math / Algebra / Geometry:** Use SVG only if the sentence explains a formula, figure, graph, or numeric relation.
- **Sciences:** Use image/placeholder only when lab or phenomenon context helps. Keep the sentence repair as the main interaction.
- **Language / History / Literature:** Text card and meaning panel are enough.

Image fallback:

```markdown
![placeholder: source-aligned editor/checker scene — image generation optional](placeholder)
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
- Required skill: Detect a wrong word/phrase, replace it, and justify the repaired meaning
- Case type: Communication case / error detection case / source-aligned wording case
- Student role:

## Source Extraction
- Core concept:
- Main rule / definition / process / wording principle:
- Key terms (must match Flashcards):
- Correct source meaning:
- Broken word/phrase:
- Correct replacement:
- Common mistake:
  - text:
  - provenance: source | inferred
- Textbook example used:

## Visual Plan
| Visual | Type | Used in | Purpose |
|---|---|---|---|
| Case scene | image OR placeholder OR none | Case setup | Real context only when useful |
| Broken sentence card | text/css | Checkpoint 1 | Show selectable word/phrase chunks |
| Replacement chips | css/text | Checkpoint 2 | Let student choose the repair |
| Meaning test panel | text/svg | Final simulation | Show pass/fail for meaning, wording, and source concept |

## Student View

### Case Setup
[2–4 sentence role-based case narrative. The student must need to repair a sentence without changing the textbook meaning.]

Broken sentence:

```txt
[Sentence with one wrong word or phrase]
```

### Checkpoint 1: Identify
- Question: Which word or phrase does not match the textbook meaning?
- Options (MCQ):
  - A. [Correct broken phrase]
  - B. [Correct surrounding phrase]
  - C. [Tempting but not main error]
  - D. [Irrelevant phrase]
- Correct answer:
- Feedback:

### Learning Block 1
[Explain that the student diagnosed the meaning problem first. This is not fill-in-the-blank.]

### Checkpoint 2: Decide
- Question: Which replacement makes the sentence match the textbook meaning?
- Options (MCQ):
  - A. [Correct replacement]
  - B. [Grammatically possible but conceptually wrong]
  - C. [Too broad or too narrow]
  - D. [Irrelevant or wrong-register replacement]
- Correct answer:
- Feedback:

### Learning Block 2
[Explain that the repair must pass meaning, wording/register, and source-concept checks.]

### Checkpoint 3: Justify / Avoid Mistake
- Question: Which explanation best shows why the old phrase is wrong and the new phrase is right?
- Options (MCQ):
  - A. [Correct explanation using source concept and repaired meaning]
  - B. [Fluent-sounding but source-changing explanation]
  - C. [Only grammar/register, missing concept]
  - D. [Wrong or unsupported explanation]
- Correct answer:
- Feedback:

### Decision Process Explanation
- Prompt: "Walk through your reasoning — (1) which concept or rule did you spot, (2) why does the replacement preserve the source meaning, (3) what mistake would happen if the old or tempting phrase stayed?"
- Expected components: source concept/rule · repaired meaning · wording mistake
- Pass condition: Student references all three components in 2–4 sentences
- Sample acceptable answer:
- AI evaluation rubric:
  - Full: identifies broken meaning, explains correct repair, rejects tempting wrong phrase
  - Partial: chooses correct replacement but explanation misses source concept or mistake
  - Retry: changes the source meaning, gives only grammar comments, or skips explanation

### Final Simulation / Consequence
- Correct path: Repaired sentence passes all required checks.
- Wrong path: Sentence may sound fluent but fails one or more checks and explains why.

Meaning test panel:

```txt
Correct path:
[✓] Meaning accurate
[✓] Wording/register clear
[✓] Source concept preserved

Weak path:
[✓] Grammar may sound acceptable
[✗] Source concept changed
[✗] Explanation missing or misleading
```

### AI Feedback Summary
- What student understood:
- What mistake appeared:
- What to review:
- Completion status: passed | Needs Retry
```

---

## 8. Completion Rules

- **Pass:** Student identifies the broken phrase, chooses a source-aligned replacement, and explains the repair before seeing the final meaning test.
- **Needs Retry:** Student guesses replacement chips, changes source meaning, selects a fluent-but-wrong phrase, comments only on grammar when concept is the issue, or skips the explanation.

---

## 9. Forbids

1. Do not use random grammar mistakes unrelated to the lesson concept.
2. Do not make the broken sentence nonsensical. The wrong phrase should be tempting.
3. Do not change source meaning, formulas, units, chronology, terms, safety rules, or evidence logic.
4. Do not use replacement chips that can all be correct.
5. Do not turn Checkpoint 3 into the open-ended explanation. Checkpoint 3 must be MCQ.
6. Do not place the Decision Process Explanation after the consequence.
7. Do not auto-pass the explanation.
8. Do not use terminology that conflicts with Flashcards.
9. Do not treat fluent grammar as correct if the source concept changed.
10. Do not skip the weak-path meaning test.

---

## 10. Uzbek Language Guardrails

When `language = uz`:

- Use formal **Siz** where direct address is needed.
- Never use `sen` / `san`.
- Keep sentences short and logical.
- Preserve formulas, units, names, terms, chronology, and source meaning.
- Avoid Russian or English calques.
- Explain difficult terms inline.
- For language-register tasks, the wrong phrase must be wrong because it violates the target rule or register, not because it sounds unusual to the generator.

---

## 11. Self-Check

```txt
[ ] Source concept/rule extracted
[ ] Correct source meaning defined
[ ] Broken phrase creates a real lesson-based misconception
[ ] Correct replacement preserves source meaning
[ ] Student role creates a repair/checking need
[ ] Exactly 3 MCQ checkpoints included
[ ] Checkpoint 3 is MCQ, not written reasoning
[ ] Decision Process Explanation included after C3
[ ] DPE is before final consequence
[ ] DPE asks for concept/rule · repaired meaning · mistake
[ ] Final consequence shows correct path and weak path
[ ] Meaning panel checks meaning, wording/register, and source concept
[ ] Key terms align with Flashcards
[ ] Common mistake provenance marked source | inferred
[ ] Subject-family visual rules followed
[ ] Uzbek guardrails followed when language=uz
```

If any line fails, regenerate.
