# NETS Case-Based Preview — Generation Prompt: Languages

**Subjects covered:** Uzbek (as L1), Russian, English, other taught languages
**Source standard:** NETS Case-Based Preview Generation Standard v1.1
**Companion file (Uzbek validation):** `NETS_Uzbek_Language_Foundation_Review_v1_3.md` — the Uzbek Language Foundation standard. Owns language quality, simplification rules, formal register, cultural context, and subject-specific Uzbek guardrails. Reference this file for any Uzbek validation question on the case copy.

> This document IS the prompt. An AI given a textbook address and these rules should be able to generate a Case-Based Preview without further human guidance.

---

## 1. Context (small)

You are generating one **Case-Based Preview**: a short guided learning case that turns a language textbook section into a communication situation where the student makes language choices.

The student must be a speaker, writer, reader, or editor — making real communicative decisions, not a passive reader. They face three MCQ-style recognition checkpoints, then write a short reasoning explanation, then see the consequence (the message lands or fails).

**Stakes:** low-to-medium. Meaning-building, not final mastery.

---

## 2. Inputs

```json
{
  "subject": "english" | "russian" | "uzbek" | "<other language>",
  "grade": <number>,
  "language": "uz" | "ru" | "en",
  "target_language": "<the language being taught>",
  "cefr_level": "<optional, e.g. A2, B1>",
  "textbook": "<filename>",
  "chapter": "<chapter name>",
  "section": "<section name>",
  "page_range": "<start-end>",
  "source_text": "<optional extracted text>",
  "images_or_diagrams": "<optional>",
  "flashcards_terms": "<optional array of canonical lesson terms / vocabulary>"
}
```

Note: `language` is the language of the **student-facing case copy** (usually Uzbek). `target_language` is what's being taught. They are often different (Uzbek-speaking student learning English).

If `source_text` is provided, use it. Otherwise retrieve textbook content from the address.

---

## 3. How — Process

### Step 1 — Extract source facts

Pull from the textbook section:

- topic (a tense, grammar pattern, vocabulary set, register, communication function)
- main rule (e.g., "past simple uses `-ed` for regular verbs", "formal letters open with `Hurmatli...`", "use `much` with uncountable nouns")
- key vocabulary / phrases — **must match Flashcards** if provided; otherwise extract canonical lesson terms
- textbook example dialogue / passage
- common mistake — `provenance: "source"` if textbook lists it, `"inferred"` if you derived it (typical L1 interference, wrong register, conjugation error)
- required skill (write, choose, fix, understand, respond)

### Step 2 — Find the usable skill

What action should the student perform after this lesson?

| Topic example | Usable skill |
|---|---|
| Past simple tense | Tell a finished story to a friend |
| Modal verbs (must, should) | Give advice to someone |
| Food vocabulary | Order food / shop / cook |
| Formal letter | Write to a teacher or institution |
| Reading comprehension | Find a specific fact in a text |
| Conditional sentences | Plan a hypothetical situation |

### Step 3 — Pick or create the case

**Priority A** — adapt the textbook's dialogue / passage / example into a situation.

**Priority B** — convert a textbook example into a fresh communication moment.

**Priority C** — create a plausible communication case.

**Good cases (languages):**
- A student writes a polite message to a teacher about missing homework
- A student responds to a friend's invitation
- A student fixes errors in their own paragraph
- A student picks the right tense to tell a finished story to a younger sibling
- A student chooses formal vs informal phrasing for a job application
- A student orders food at a market and asks about prices
- A student writes an email to a school exchange partner

**Bad cases (never use):**
- A forest spirit teaches past tense
- A magic mirror only shows the future if you use future perfect
- A robot's voice modulator only works with passive voice
- A wizard's spell requires conditional sentences to activate

Why bad: the language structure must be load-bearing in the case, not decorative. Strip the magic out and the language choice must still be the thing that makes communication succeed or fail.

### Step 4 — Place the student

Student must DO communication: write, choose, fix, respond, summarize, identify, understand.

Not just read.

### Step 5 — Build 3 checkpoints

| # | Type | Purpose | Format |
|---|------|---------|--------|
| C1 | Identify | Recognize communication goal / context / function | MCQ |
| C2 | Decide | Choose correct grammar / vocab / register | MCQ |
| C3 | Justify | Pick why correct sentence works / why wrong is unclear | MCQ |

All three may be MCQ. Recognition only.

**MCQ anti-leak rule:** Don't write options where the answer is obvious from formatting (e.g., one option much longer, or one obviously more formal than the others when register isn't being tested). The student should genuinely have to apply the grammar/vocab to choose.

### Step 6 — Decision Process Explanation (slot 7, **BEFORE** consequence)

After C3, before final consequence:

> Walk through your reasoning:
> 1. Which concept did you spot in the situation?
> 2. Why did you pick this method over the alternatives?
> 3. What mistake would have happened with the wrong choice?

Non-negotiable:
- Open-ended, NOT MCQ
- Placed BEFORE consequence reveal
- 2–4 sentences
- AI evaluates against extracted concept, method, common mistake

For languages, "method" usually means "which grammar rule / vocab choice / register" and "mistake" usually means "what would the message have communicated wrongly."

### Step 7 — Final consequence

Show both paths through the lens of **what the message actually communicates**:
- **Correct path** — the message lands; the listener / reader understands as intended
- **Wrong path** — the message is unclear, rude, ungrammatical, or sends the wrong meaning; show what the receiver would actually understand

The consequence reveals the COMMUNICATION OUTCOME, not just a verdict.

### Step 8 — Feedback summary

What student understood · what mistake appeared · what to review · passed / Needs Retry.

---

## 4. How — Visual rules (Languages)

**Default: image.** Communication is contextual. A real-world scene gives the situation meaning — who's talking, where, why, how formal.

### Use image for:

- Communication settings (classroom, home, market, café, office)
- Dialogue contexts (two students chatting, a teacher addressing class, a customer at a counter)
- Real-world vocabulary settings (food market for food vocab, sports field for sports vocab, kitchen for cooking verbs)
- Atmosphere / register cues (formal office vs informal playground)
- Cultural context where it matters

### Use SVG for:

- Sentence structure blocks (subject | verb | object)
- Word-order diagrams
- Wrong → corrected sentence comparison
- Tone / register comparison cards (formal vs informal side-by-side)
- Tense timeline diagrams (past / present / future placement)
- Conjugation tables
- Dialogue bubbles when the focus is on the linguistic structure, not the speakers

### When the case is about the message itself:

Lead with image of the scene (to establish context and register), then use SVG in the learning blocks to show the language structure being taught.

### Image-generation fallback:

If image generation is unavailable, leave a placeholder and continue:

```markdown
![placeholder: student writing a message to their teacher on a phone — image gen required](placeholder)
```

Never block on missing images.

---

## 5. Case patterns — Languages

Don't force science-style cases. Use **communication cases**.

| Case type | Student role | Decision |
|---|---|---|
| Write a message | Writer | Tense / register / vocab choice |
| Understand a dialogue | Reader / listener | Meaning / inference |
| Fix grammar | Editor | Which form fits? |
| Choose register | Speaker | Formal or informal? |
| Summarize a passage | Reader / writer | Which idea is the main one? |
| Respond to a situation | Speaker | What to say? |
| Order / request | Customer | How to ask politely / correctly? |

**Checkpoint pattern (all language cases):**
1. C1 — identify communication goal / register / function
2. C2 — choose correct grammar / vocabulary / register
3. C3 — explain why the wrong sentence would be unclear or wrong

**Final consequence:** show how the correct message lands AND what the wrong message would have communicated.

---

## 6. What — Output format

```markdown
# Case-Based Preview: [Title]

## Metadata
- Subject: [english / russian / uzbek / ...]
- Target language:
- CEFR level (if applicable):
- Grade:
- Topic:
- Textbook address:
- Source concept:
- Required skill:
- Case type:
- Student role:

## Source Extraction
- Core concept:
- Main rule / grammar pattern:
- Key vocabulary (must match Flashcards):
- Common mistake:
  - text:
  - provenance: source | inferred
- Textbook example used:

## Visual Plan
| Visual | Type | Used in | Purpose |
|---|---|---|---|
| Case scene | image OR placeholder | Case setup | Communication context |
| Structure model | svg | Learning block / checkpoint | Sentence / register / tense diagram |
| Consequence | svg AND/OR image | Final simulation | How message lands vs fails |

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
[short explanation; SVG of structure if helpful]

### Checkpoint 2: Decide
- Question:
- Options (MCQ — beware anti-leak rule):
- Correct answer:
- Feedback:

### Learning Block 2
[short explanation; SVG comparison if helpful]

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
- Correct path: [text + visual — show message landing]
- Wrong path: [text + visual — show what the receiver would actually understand]

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
2. Inventing textbook claims, grammar rules, vocabulary definitions
3. Losing the source concept in the case
4. Skipping checkpoint-based learning (3 required)
5. Student is not the decision-maker
6. Checkpoint decisions with no consequence
7. Replacing Decision Process Explanation with a 4th MCQ
8. Placing Decision Process Explanation AFTER the consequence
9. Auto-passing the open-ended explanation without evaluation
10. Using vocabulary that doesn't match the lesson's Flashcards

### Languages specific
11. Don't use tenses or grammar above the target CEFR / grade level
12. Don't author a fresh passage when the textbook has one — adapt the textbook's
13. Don't force cliché contexts (cowboy, cricket, baseball) unless the textbook is itself about those topics — keep relatable to Uzbek students
14. Don't use forest-spirit / magic-mirror frames where the language structure is decorative
15. Don't use MCQ where the answer can be inferred from option length, formatting, or obvious formality (anti-leak)
16. Don't reverse-translate idioms / sentence structures from Russian or English into Uzbek (calque trap)
17. Don't oversimplify culture — keep formality/register accurate to the target language's social norms
18. Don't use SVG when a real communication-scene image would carry context better

---

## 8. Uzbek language (when language=uz)

This is the language the CBP COPY is written in, not necessarily the target language being taught.

Defer to **`NETS_Uzbek_Language_Foundation_Review_v1_3.md`** — the Uzbek Language Foundation standard. It owns language quality, simplification, formal register, and cultural context. Critical points:

- Formal **Siz** for case narration / instructions — never `sen` / `san`
- Short logical sentences; student-friendly wording
- Don't translate target-language grammar terms in misleading ways (e.g., if teaching English `present perfect`, use a clear Uzbek explanation, not just a literal translation)
- No Russian-syntax calques

When the target language IS Uzbek (teaching Uzbek as L1):
- Use authentic Uzbek constructions
- Don't reverse-engineer Uzbek from Russian or English templates

When the target language is something else (e.g., English, Russian):
- Case can be set in Uzbekistan with Uzbek student characters
- Use authentic target-language phrasing (don't use unnatural English just because it's textbook-flavored)

---

## 9. Self-check (run before output)

```txt
[ ] Source topic identified
[ ] Required student skill identified
[ ] Case is source-aligned (grammar rule / vocab / function preserved)
[ ] Student is communicator / writer / editor / speaker
[ ] Language structure is load-bearing in the case (no magic / spell frames)
[ ] Exactly 3 MCQ checkpoints (C1: Identify, C2: Decide, C3: Justify)
[ ] MCQ options don't leak the answer (anti-leak rule)
[ ] Decision Process Explanation present
[ ] DPE placed BEFORE final consequence
[ ] DPE has 3 sub-prompts (concept · method · mistake)
[ ] DPE is open-ended, NOT MCQ
[ ] Final consequence shows what correct message communicates AND what wrong message would communicate
[ ] Image (or placeholder) used for communication scene / context
[ ] SVG used for sentence structure / tense timeline / register comparison
[ ] Key vocabulary aligns with Flashcards
[ ] Common mistake provenance marked (source / inferred)
[ ] Inferred mistakes NOT presented as textbook-stated
[ ] Tenses / grammar within target CEFR / grade level
[ ] No cliché cowboy / cricket / fantasy contexts (unless textbook is about them)
[ ] Target language sounds natural (no Russian / English / Uzbek calques)
[ ] Uzbek case copy is formal, clear, student-friendly
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

*End of Languages Generation Prompt.*
