# NETS Case-Based Preview Generation Standard v1.0

**Status:** MVP source-of-truth draft  
**Purpose:** Given a textbook/content address, any AI should be able to generate a Case-Based Preview with no human intervention.  
**Scope:** Case-Based Preview only. This document does not define Flashcards, Memory Check, Practice Arc, Boss, scoring, or gamification economy.

---

# 0. Position in NETS Flow v2

Case-Based Preview belongs to the **Learning Sections**.

```txt
Homework Tab
│
├── Learning Sections
│   ├── Case-Based Preview / Real-Life Learning Case
│   └── Flashcard Learning
│       └── Quizlet-Style Test / Memory Check
│
├── Unlock Gate
├── Practice Arc
├── Boss Arena
└── Reflection / Debrief / Marking
```

Case-Based Preview is **not** the final homework practice.  
It teaches the lesson through a case, checkpoints, and consequences.

---

# 1. Core Definition

A **Case-Based Preview** is a short guided learning case that turns textbook content into a student-facing decision situation.

It must include:

```txt
1. Textbook-based concept
2. Realistic or plausible case
3. Student role
4. Clear task
5. Exactly 3 checkpoints
6. Consequence / simulation at the end
7. Feedback summary
```

It teaches:

```txt
What is happening?
Which concept/rule applies?
What decision should be made?
Why is that decision correct?
What happens if the wrong decision is made?
```

---

# 2. Non-Negotiable Rules

## 2.1 Textbook authority

NETS does not replace the official textbook.

```txt
Textbook = source/reference
NETS = better homework journey built on top of textbook
```

The AI must not invent textbook facts, formulas, definitions, dates, or lesson claims.

If an outside source is explicitly provided, it may be used.  
If no outside source is provided, the AI must stay within textbook content and create only a plausible case/story around it.

---

## 2.2 Case must preserve source meaning

The case may be fictional, but the lesson concept must remain source-aligned.

Allowed:

```txt
Create a classroom/shop/lab/history/dialogue case that uses the textbook concept.
```

Forbidden:

```txt
Change the formula, rule, fact, process, chronology, answer logic, or source meaning.
```

---

## 2.3 No passive preview

Case-Based Preview must not be a reading blob.

It must use:

```txt
3 checkpoints + final consequence/simulation
```

---

## 2.4 Student must be decision-maker

The student must be placed as the solver, advisor, checker, writer, observer, or decision-maker.

Forbidden:

```txt
A story where the student only reads what happened.
```

Required:

```txt
Student makes decisions or judgments inside the case.
```

---

## 2.5 Consequence must exist

Every major decision must lead to a visible result.

MVP consequence can be:

```txt
text consequence
simple SVG state change
simple visual before/after
short simulation summary
```

---

# 3. Input Requirements

The AI receives a content address.

Minimum input:

```json
{
  "subject": "Math",
  "grade": 6,
  "language": "uz",
  "textbook": "6_sinf_matematika_darslik_2024_UZ.pdf",
  "chapter": "Oddiy kasrlar",
  "section": "To‘g‘ri kasrni natural songa bo‘lish",
  "page_range": "28-32",
  "workbook_reference": "optional",
  "source_text": "optional extracted text",
  "images_or_diagrams": "optional"
}
```

If exact page text is available, use it.  
If only chapter/section/page address is given, retrieve the relevant textbook content first.

---

# 4. Generation Pipeline

## Step 1 — Extract source facts

From the textbook section, extract:

```txt
topic
grade level
core concept
main rule / formula / process
key terms
example problems
visual models
common mistake
required student skill
```

Output internally:

```json
{
  "topic": "",
  "core_concept": "",
  "main_rule": "",
  "key_terms": [],
  "textbook_examples": [],
  "common_mistake": "",
  "student_must_be_able_to": ""
}
```

---

## Step 2 — Identify usable skill

Do not stop at topic name.  
Find what the student must **do**.

Ask:

```txt
What action should the student be able to perform after learning this?
```

Examples:

| Subject | Topic | Usable Skill |
|---|---|---|
| Math | Fractions | split quantity equally |
| Math | Percentages | choose correct percent model |
| Physics | Force | predict effect of force/mass |
| Chemistry | Acids | identify safe classification |
| Biology | Photosynthesis | predict plant condition |
| English | Past tense | choose correct tense in message |
| History | Cause of event | judge cause/evidence/consequence |

---

## Step 3 — Select case type

Use this decision table.

| Subject Type | Case Type | Student Role |
|---|---|---|
| Math | Practical problem case | planner, helper, buyer, analyst |
| Physics | Phenomenon case | observer, engineer, technician |
| Chemistry | Lab/safety case | lab assistant, safety checker |
| Biology | Observation/process case | researcher, doctor, ecologist |
| Language | Communication case | speaker, writer, reader, editor |
| History | Historical decision/source case | advisor, witness, historian, source checker |
| Literature | Interpretation case | reader, critic, character analyst |

---

## Step 4 — Pick or create case

### Priority A: Use textbook case if available

If the textbook already contains a real-life example, adapt it.

Example:

```txt
Textbook gives: 3/5 ℓ orange juice shared into 3 cups.
Case becomes: student helps distribute juice at a class event.
```

### Priority B: Use textbook visual model

If the textbook has a diagram/model, convert its idea into an original NETS visual.

Do not copy the textbook image directly.

### Priority C: Create plausible case

If no real case exists, create a plausible case.

Rules:

```txt
case can be fictional
concept cannot be fake
student role must make sense
decision must depend on textbook concept
consequence must reveal the math/science/language/history idea
```

Bad:

```txt
A dragon needs algebra to open a gate.
```

Better:

```txt
A school club splits a budget equally between groups.
```

---

# 5. Required Case Structure

Every Case-Based Preview must follow this order.

```txt
1. Case setup
2. Checkpoint 1: Identify
3. Learning block 1
4. Checkpoint 2: Decide
5. Learning block 2
6. Checkpoint 3: Justify / avoid mistake
7. Final consequence / simulation
8. AI/system feedback summary
9. Completion result
```

---

# 6. Checkpoint Design

## Checkpoint 1 — Identify

Purpose:

```txt
Can the student recognize what concept is needed in this situation?
```

Ask one of:

```txt
Which operation is needed?
Which rule applies?
Which factor matters?
Which evidence matters?
Which grammar/register fits?
What is the main problem?
```

Question format:

```txt
MCQ or simple choice is acceptable.
```

Required feedback:

```txt
Explain why the selected concept/rule fits the case.
```

---

## Checkpoint 2 — Decide

Purpose:

```txt
Can the student choose the correct method/action using fresh knowledge?
```

Ask one of:

```txt
Which formula should be used?
Which next step is correct?
Which sentence fits?
Which source evidence is strongest?
Which decision should the character make?
```

Required feedback:

```txt
Explain the method and show the correct reasoning step.
```

---

## Checkpoint 3 — Justify / Avoid Mistake

Purpose:

```txt
Can the student explain why the correct choice works or why the common mistake fails?
```

Ask one of:

```txt
Why is this method correct?
Why is the other choice wrong?
What would happen if the wrong choice was made?
Which mistake should be avoided?
```

Required feedback:

```txt
Connect the explanation to the final consequence.
```

---

# 7. Final Consequence / Simulation

The final simulation shows the result of the student’s decisions.

For MVP, the simulation may be:

```txt
text result
before/after SVG
simple state change
short consequence summary
```

It must show:

```txt
correct path result
common wrong path result
why wrong path fails
```

Example for math:

```txt
Correct: 3/5 ℓ ÷ 3 = 1/5 ℓ per cup.
Wrong: 3/5 × 3 = 9/5 ℓ, which is impossible because only 3/5 ℓ exists.
```

---

# 8. Image and SVG Rules

## 8.1 When to use image

Use a raster image or illustration when the visual is about:

```txt
real-life scene
human context
role
environment
story atmosphere
historical setting
communication situation
lab/classroom scene
```

Examples:

```txt
student distributing juice at a class event
lab assistant checking containers
student writing message to teacher
historical council decision scene
```

## 8.2 When to use SVG

Use SVG when the visual is about:

```txt
numbers
formula
fraction bar
chart
timeline
diagram
before/after state
step-by-step model
relationship between quantities
```

Examples:

```txt
3/5 fraction bar
3 cups each getting 1/5
cause → decision → consequence timeline
sentence structure blocks
force arrows
classification table
```

## 8.3 Visual requirements

Each visual must have:

```json
{
  "visual_type": "image | svg",
  "purpose": "",
  "where_used": "case_setup | checkpoint_1 | checkpoint_2 | checkpoint_3 | final_simulation",
  "alt_text": "",
  "labels": [],
  "source_alignment_note": ""
}
```

## 8.4 Visual forbidden rules

Forbidden:

```txt
copying textbook artwork directly
decorative images that do not support the case
SVGs with tiny unreadable labels
visuals that change formula/logic/source meaning
visuals that work without subject content
```

---

# 9. Subject-Specific Case Patterns

## 9.1 Math

Use cases about:

```txt
quantity
money
sharing
measurement
planning
comparison
error detection
```

Checkpoint pattern:

```txt
1. Identify operation/model
2. Choose formula or step
3. Explain common mistake
```

Final consequence:

```txt
show correct quantity and wrong impossible/illogical result
```

---

## 9.2 Physics

Use:

```txt
phenomenon → prediction → formula/logic → consequence
```

Checkpoint pattern:

```txt
1. Identify physical quantity/concept
2. Predict effect or choose formula
3. Explain why result makes sense physically
```

Final consequence:

```txt
before/after motion, force, energy, circuit, or graph state
```

---

## 9.3 Chemistry

Use:

```txt
safety → observation → particle/reaction logic → result
```

Checkpoint pattern:

```txt
1. Identify substance/process/safety risk
2. Choose safe method/classification
3. Explain reaction/process consequence
```

Final consequence:

```txt
safe/unsafe result, balanced/not balanced, particle/process state
```

---

## 9.4 Biology

Use:

```txt
observation → system/process → mechanism → prediction
```

Checkpoint pattern:

```txt
1. Identify process/system
2. Choose factor/mechanism
3. Predict biological consequence
```

Final consequence:

```txt
organism/process state changes
```

Important:

```txt
Do not narrow organism-wide concepts into human-only examples unless topic is human biology.
```

---

## 9.5 Language Subjects

Do not force science-style case.

Use a **communication case**.

Possible cases:

```txt
write a message
understand a dialogue
choose correct tense
fix grammar
choose formal/informal wording
summarize a passage
respond to a situation
```

Checkpoint pattern:

```txt
1. Identify communication goal
2. Choose correct grammar/vocab/register
3. Explain why wrong sentence is unclear or incorrect
```

Visuals:

```txt
dialogue bubbles
sentence cards
word-order blocks
wrong → corrected sentence
tone comparison cards
```

---

## 9.6 History

History does not always need a “real-life application case” like math/science.

Use a **Historical Decision / Source Case**.

Possible cases:

```txt
historical decision
cause/effect dilemma
source evidence
perspective switch
consequence chain
```

Checkpoint pattern:

```txt
1. Identify situation and actor goal
2. Choose strongest cause/evidence/decision
3. Explain consequence and why it happened
```

Visuals:

```txt
timeline
cause-effect chain
source card
map marker
actor perspective cards
```

Important:

```txt
Do not turn history into modern professional roleplay unless it naturally fits.
```

---

# 10. Uzbek Language Rules

Case-Based Preview Uzbek must clearly separate:

```txt
situation
student role
task
decision point
consequence
feedback
```

Use:

```txt
formal Siz
natural Uzbek
student-friendly wording
short logical sentences
clear task language
```

Avoid:

```txt
sen/san
mixed register
Russian/English calques
unexplained hard terms
difficulty caused by confusing wording
childish tone
```

Math-specific protection:

```txt
do not change numbers
do not change variables
do not change formulas
do not change units
do not change answer logic
do not change calculation order
```

---

# 11. Output Format

The AI must output this structure.

```md
# Case-Based Preview: [Title]

## Metadata
- Subject:
- Grade:
- Topic:
- Textbook address:
- Source concept:
- Required skill:
- Case type:
- Student role:

## Source Extraction
- Core concept:
- Main rule / formula / process:
- Key terms:
- Common mistake:
- Textbook example used:
- Source alignment note:

## Visual Plan
| Visual | Type | Used In | Purpose |
|---|---|---|---|
| Case scene | image | Case setup | show real-life role/context |
| Concept model | svg | checkpoint/explanation | show formula/model |
| Consequence | svg/text | final simulation | show result |

## Student View

### Case Setup
[student-facing case]

### Checkpoint 1: Identify
- Question:
- Options:
- Correct answer:
- Feedback:

### Learning Block 1
[short explanation]

### Checkpoint 2: Decide
- Question:
- Options:
- Correct answer:
- Feedback:

### Learning Block 2
[short explanation]

### Checkpoint 3: Justify / Avoid Mistake
- Question:
- Options or expected answer:
- Correct answer:
- Feedback:

### Final Simulation / Consequence
- Correct path:
- Wrong path:
- Visual/SVG description or code:

### AI/System Feedback Summary
- What student understood:
- What mistake appeared:
- What to review:
- Completion status:

## Completion Rules
- Pass condition:
- Retry condition:

## Quality Checklist
- Textbook concept preserved:
- 3 checkpoints included:
- Student is decision-maker:
- Consequence shown:
- Uzbek is formal and clear:
- Formula/source meaning preserved:
```

---

# 12. Scoring / Completion Guidance

Case-Based Preview should be low-to-medium stakes.

It may contribute to readiness, but it should not dominate final homework score.

Minimum pass condition should check:

```txt
student identified the concept
student chose correct method/action
student understood consequence or common mistake
```

If failed:

```txt
Case-Based Preview: Needs Retry
```

Do not say only:

```txt
Not Completed
```

---

# 13. Master Prompt for AI Generation

Use this prompt when generating a Case-Based Preview.

```txt
You are generating a NETS Case-Based Preview.

Inputs:
- Subject:
- Grade:
- Language:
- Textbook/content address:
- Topic/chapter/section/page range:
- Source text/images if provided:

Task:
Generate a Case-Based Preview using only source-aligned lesson content.

Follow this process:
1. Extract the source concept, main rule/formula/process, key terms, common mistake, and required student skill.
2. Choose the correct case type for the subject:
   - Math: practical problem case
   - Science: phenomenon/lab/observation case
   - Language: communication case
   - History: historical decision/source case
3. If the textbook already provides a useful real-life example, adapt it.
4. If no useful example exists, create a plausible case that preserves the textbook concept.
5. Place the student as the decision-maker or solver.
6. Create exactly 3 checkpoints:
   - Checkpoint 1: Identify the concept/problem
   - Checkpoint 2: Choose the method/action
   - Checkpoint 3: Justify or avoid the common mistake
7. Add a final consequence/simulation showing correct and common wrong paths.
8. Use images only for real-life scene/context.
9. Use SVG for formulas, charts, fraction bars, timelines, before/after states, or simple diagrams.
10. Use formal, natural, student-friendly Uzbek.
11. Do not copy textbook artwork directly.
12. Do not invent textbook facts, formulas, definitions, dates, or lesson claims.
13. Do not change formulas, numbers, units, answer logic, source meaning, SVG IDs, URLs, or grading fields.
14. Output using the required Markdown structure.

The result must be understandable without human editing.
```

---

# 14. Automatic Validation Checklist

Before accepting the generated preview, verify:

```txt
[ ] Source topic is identified.
[ ] Required student skill is identified.
[ ] Case type matches subject.
[ ] Case is source-aligned.
[ ] Student is decision-maker/solver.
[ ] Exactly 3 checkpoints exist.
[ ] Checkpoint 1 identifies concept.
[ ] Checkpoint 2 chooses method/action.
[ ] Checkpoint 3 justifies or catches mistake.
[ ] Final consequence/simulation exists.
[ ] Correct path and common wrong path are shown.
[ ] Visuals support learning, not decoration.
[ ] Image is used only for scene/context.
[ ] SVG is used for math/model/state visuals.
[ ] Uzbek is formal, natural, and clear.
[ ] Formulas/numbers/units/source meaning are preserved.
[ ] No passive reading blob.
[ ] Completion/pass condition exists.
[ ] Retry state exists.
```

If any required item fails, regenerate.

---

# 15. Minimal MVP Example Shape

```txt
Case Setup:
Student helps solve a realistic/source-aligned situation.

Checkpoint 1:
What concept/operation/rule applies?

Learning Block:
Short explanation from textbook concept.

Checkpoint 2:
Which method/formula/action is correct?

Learning Block:
Show the method.

Checkpoint 3:
Why is the common mistake wrong?

Final Simulation:
Show correct result and wrong consequence.

Feedback:
Summarize understanding, mistake, and next step.
```

---

# 16. Final Rule

A Case-Based Preview is valid only if the student can say:

```txt
I know what situation I was in.
I know what decision I made.
I know which textbook concept helped me.
I saw what happened because of my choice.
I understand the main mistake to avoid.
```

If the student only read an explanation, the Case-Based Preview failed.
