# NETS Case-Based Preview — Generation Prompt: Sciences

**Subjects covered:** Physics, Biology, Chemistry
**Source standard:** NETS Case-Based Preview Generation Standard v1.1
**Companion file (Uzbek validation):** `NETS_Uzbek_Language_Foundation_Review_v1_3.md` — the Uzbek Language Foundation standard. Owns language quality, simplification rules, formal register, cultural context, and subject-specific Uzbek guardrails. Reference this file for any Uzbek validation question.

> This document IS the prompt. An AI given a textbook address and these rules should be able to generate a Case-Based Preview without further human guidance.

---

## 1. Context (small)

You are generating one **Case-Based Preview**: a short guided learning case that turns a science textbook section into a student-facing observation / decision situation.

The student must be an observer, predictor, lab assistant, or analyst — not a passive reader. They face three MCQ-style recognition checkpoints, then write a short reasoning explanation, then see the physical / biological / chemical consequence of their choice.

**Stakes:** low-to-medium. Meaning-building, not final mastery.

---

## 2. Inputs

```json
{
  "subject": "physics" | "biology" | "chemistry",
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

If `source_text` is provided, use it. Otherwise retrieve textbook content from the address.

---

## 3. How — Process

### Step 1 — Extract source facts

Pull from the textbook section:

- topic
- core concept (a phenomenon, process, system, or principle)
- main rule / law / mechanism (e.g. `F = ma`, photosynthesis equation, acid-base classification, conservation of energy)
- key terms — **must match Flashcards** if `flashcards_terms` provided; otherwise extract canonical lesson terms
- mechanism diagrams from textbook
- common mistake — `provenance: "source"` if textbook lists it, `"inferred"` if you derived it
- required skill (predict, observe, classify, explain)

### Step 2 — Find the usable skill

What action should the student perform after this lesson?

| Subject | Topic example | Usable skill |
|---|---|---|
| Physics | Force / motion | Predict effect of force on mass |
| Physics | Electric circuit | Identify why circuit fails |
| Biology | Photosynthesis | Predict plant condition under conditions |
| Biology | Digestive system | Trace path of nutrient |
| Chemistry | Acids and bases | Classify substance for safety |
| Chemistry | Reaction types | Predict reaction outcome |

### Step 3 — Pick or create the case

**Priority A** — adapt the textbook's real-life example into a situation.

**Priority B** — convert a textbook mechanism diagram into a fresh NETS visual.

**Priority C** — create a plausible case grounded in real phenomena.

**Good cases (sciences):**
- A lab assistant verifies labels before mixing two substances (chemistry)
- A biologist observes leaf wilting and predicts cause (biology)
- A technician identifies why a circuit overheats (physics)
- A pharmacist reads a label to confirm acid-base safety (chemistry)
- A field researcher predicts how a frog population responds to drought (biology)
- A driver explains why braking distance increases on a wet road (physics)
- A doctor identifies which organ system is involved (biology — **only when topic is explicitly human biology**)

**Bad cases (never use):**
- A unicorn's horn reflects light to teach refraction
- A magic potion's pH changes when you add tears
- A dragon's metabolism teaches photosynthesis

Why bad: the phenomenon must be real. Strip the unicorn out and the science still has to hold.

### Step 4 — Place the student

Student must be an observer, researcher, lab assistant, technician, ecologist, doctor (when human biology), or analyst — someone who *needs* the science to make a decision.

### Step 5 — Build 3 checkpoints

| # | Type | Purpose | Format |
|---|------|---------|--------|
| C1 | Identify | Recognize phenomenon / system / process | MCQ |
| C2 | Decide | Choose method / safe action / prediction | MCQ |
| C3 | Justify | Explain why correct works / why mistake fails | MCQ |

All three may be MCQ. Recognition only.

### Step 6 — Decision Process Explanation (slot 7, **BEFORE** consequence)

After C3, before the final consequence:

> Walk through your reasoning:
> 1. Which concept did you spot in the situation?
> 2. Why did you pick this method over the alternatives?
> 3. What mistake would have happened with the wrong choice?

Non-negotiable:
- Open-ended, NOT MCQ
- Placed BEFORE the consequence reveal
- 2–4 sentences
- AI evaluates against extracted concept, method, common mistake

### Step 7 — Final consequence

Show both paths:
- **Correct path** — the actual physical / biological / chemical result
- **Wrong path** — what the common mistake would produce and why it's wrong

The consequence should reveal the SCIENCE, not just a verdict.

### Step 8 — Feedback summary

What student understood · what mistake appeared · what to review · passed / Needs Retry.

---

## 4. How — Visual rules (Sciences)

**Default: image.** Sciences are visual-heavy and benefit from real atmosphere. Lab settings, organisms, phenomena, and equipment read better as images than SVG.

### Use image for:

- **Physics** — apparatus, motion contexts, real circuits, weather, light/optics setups
- **Chemistry** — lab benches, test tubes, beakers, equipment, substance close-ups, hazard contexts
- **Biology** — organisms, ecosystems, anatomical context, microscope views, field settings
- Real-world phenomena (motion, force application, weather, plant growth)
- Equipment / instrumentation context

### Use SVG for:

- Concept breakdown (force vector diagrams, energy flow charts)
- Particle / molecular diagrams
- Process flowcharts (photosynthesis stages, water cycle, digestion path)
- Before/after state comparisons (chemical reaction, organism state, system change)
- Anatomical schematics when outline serves better than photo
- Free-body diagrams
- Simple state-change indicators

### When the phenomenon is complex / multi-step:

Use image for the overall scene, then SVGs in the learning blocks to break down the mechanism step-by-step.

### Image-generation fallback:

If image generation is unavailable, leave a placeholder and continue:

```markdown
![placeholder: chemistry lab bench with two unlabeled beakers — image gen required](placeholder)
```

Never block on missing images.

---

## 5. Case patterns — Sciences

### 5.1 Physics

**Flow:** Phenomenon → prediction → formula / logic → consequence

| Case type | Student role | Decision |
|---|---|---|
| Force / motion | Observer, engineer | Predict effect |
| Energy transfer | Technician | Choose efficient path |
| Circuit fault | Electrician | Identify the fault |
| Light / optics | Photographer, designer | Choose lens / angle |
| Pressure / fluids | Plumber, diver | Predict behavior |

Checkpoint pattern: identify physical quantity → predict effect or choose formula → explain why result makes physical sense.

Final consequence: before/after motion, force result, energy state, circuit behavior, graph state.

### 5.2 Chemistry

**Flow:** Safety / observation → particle / reaction logic → result

| Case type | Student role | Decision |
|---|---|---|
| Safety check | Lab assistant | Safe or not? |
| Reaction prediction | Chemist | Will it react? What forms? |
| Classification | Analyst | Acid, base, salt? |
| State change | Observer | Phase / energy result? |
| Concentration | Pharmacist, technician | Dilution / strength choice |

Checkpoint pattern: identify substance / process / safety risk → choose safe method / classification → explain reaction or process consequence.

Final consequence: safe / unsafe result, balanced / unbalanced reaction, particle or process state change.

### 5.3 Biology

**Flow:** Observation → system / process → mechanism → prediction

| Case type | Student role | Decision |
|---|---|---|
| Organism response | Researcher, ecologist | Predict reaction to change |
| System malfunction | Doctor (only if human biology) | Identify cause |
| Process identification | Lab technician | What's happening here? |
| Ecosystem balance | Field biologist | Predict consequence of change |
| Genetic outcome | Researcher | Predict trait expression |

Checkpoint pattern: identify process / system → choose factor / mechanism → predict biological consequence.

Final consequence: organism or process state changes.

**Important biology rule:** Do not narrow organism-wide concepts to human-only examples unless the topic is explicitly human biology. Photosynthesis is plant-wide; respiration is most multicellular life — don't reduce these to humans by default.

---

## 6. What — Output format

```markdown
# Case-Based Preview: [Title]

## Metadata
- Subject: [physics / biology / chemistry]
- Grade:
- Topic:
- Textbook address:
- Source concept:
- Required skill:
- Case type:
- Student role:

## Source Extraction
- Core concept:
- Main rule / law / mechanism:
- Key terms (must match Flashcards):
- Common mistake:
  - text:
  - provenance: source | inferred
- Textbook example used:

## Visual Plan
| Visual | Type | Used in | Purpose |
|---|---|---|---|
| Case scene | image OR placeholder | Case setup | Real lab / field / phenomenon context |
| Concept model | svg | Learning block / checkpoint | Show mechanism / flow / particle diagram |
| Consequence | image AND/OR svg | Final simulation | Correct + wrong path state |

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
[short explanation; SVG mechanism diagram if helpful]

### Checkpoint 2: Decide
- Question:
- Options (MCQ):
- Correct answer:
- Feedback:

### Learning Block 2
[short explanation; SVG of process if helpful]

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
- Correct path: [text + image / svg]
- Wrong path: [text + image / svg showing failure]

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
2. Inventing textbook facts, laws, mechanisms, definitions
3. Losing the source concept in the case
4. Skipping checkpoint-based learning (3 required)
5. Student is not the decision-maker / observer
6. Checkpoint decisions with no consequence
7. Replacing Decision Process Explanation with a 4th MCQ
8. Placing Decision Process Explanation AFTER the consequence
9. Auto-passing the open-ended explanation without evaluation
10. Using terminology that doesn't match the lesson's Flashcards

### Sciences specific
11. Don't change observed phenomena from the source
12. Don't replace mechanism with an unrelated process
13. Don't fictionalize chemistry — a real reaction must remain real
14. Don't oversimplify safety rules — wrong safety = real-world harm
15. Don't narrow organism-wide biology to humans by default
16. Don't use SVG when a real lab/field image would carry meaning better
17. Don't copy textbook artwork directly
18. Don't render multi-step mechanisms as one dense image — break into SVG stages

---

## 8. Uzbek language (when language=uz)

For Uzbek validation, defer to **`NETS_Uzbek_Language_Foundation_Review_v1_3.md`** — the Uzbek Language Foundation standard. It owns language quality, simplification, formal register, and cultural context. Critical points:

- Formal **Siz** — never `sen` / `san`
- Short logical sentences; student-friendly wording
- Don't change scientific terms, formulas, units, or chemical names in translation
- Use established Uzbek scientific terminology; don't reverse-translate from Russian / English calques
- Explain hard terms inline

---

## 9. Self-check (run before output)

```txt
[ ] Source topic identified
[ ] Required student skill identified
[ ] Case is source-aligned (phenomenon / law / mechanism preserved)
[ ] Student is observer / decision-maker / predictor
[ ] Phenomenon is real (no unicorns / dragons / magic)
[ ] Biology: organism-wide concepts NOT narrowed to humans by default
[ ] Exactly 3 MCQ checkpoints (C1: Identify, C2: Decide, C3: Justify)
[ ] Decision Process Explanation present
[ ] DPE placed BEFORE final consequence
[ ] DPE has 3 sub-prompts (concept · method · mistake)
[ ] DPE is open-ended, NOT MCQ
[ ] Final consequence shows correct AND wrong path
[ ] Image (or placeholder) used for case scene / phenomenon / lab context
[ ] SVG used for concept breakdown / mechanism / before-after state
[ ] Multi-step phenomena broken into SVG stages, not one dense image
[ ] Key terms align with Flashcards
[ ] Common mistake provenance marked (source / inferred)
[ ] Inferred mistakes NOT presented as textbook-stated
[ ] Scientific terms / formulas / chemical names preserved
[ ] Safety rules accurate (chemistry)
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

*End of Sciences Generation Prompt.*
