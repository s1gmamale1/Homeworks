# NETS Flashcard & Game — Generation Prompt: Sciences

**Subjects covered:** Biology, Physics, Chemistry (kimyo)
**Source standard:** `docs/flashcard-game-prompt-rules.md` (v1 active-recall contract)
**Companion file (Uzbek validation):** `NETS_Uzbek_Language_Foundation_Review_v1_3.md` — the Uzbek Language Foundation standard. Owns language quality, simplification rules, formal register, cultural context, and subject-specific Uzbek guardrails. Reference this file for any Uzbek validation question on the card copy.

> This document IS the prompt. An AI given a textbook address and these rules should be able to generate the flashcard deck plus all five study games for one lesson without further human guidance.

---

## 1. Context (small)

You are generating two coordinated artifacts from one science textbook section:

1. A **flashcard deck** of 6–12 active-recall cards in the v1 8-field shape — terms, formulas (chemistry, physics), processes (biology, chemistry), key facts, and common-mistake cards.
2. **Five study games** sourced 1:1 from those cards: Match, Write/Spell, Learn, Test, Memory Sprint.

The deck teaches one retrievable atom per card. The games re-practice those atoms under different cognitive loads. Sciences cards often pair with a diagram (anatomical structure, circuit, reaction mechanism) — these become `image_label` or `definition` cards with an SVG / image attached.

**Stakes:** medium. Practice round between Case-Based Preview and Final Challenge.

You do not need to know anything else about the larger flow. Just produce one deck plus five games.

---

## 2. Inputs

```json
{
  "subject": "biology" | "physics" | "chemistry",
  "grade": <number>,
  "language": "uz" | "ru" | "en",
  "textbook": "<filename>",
  "chapter": "<chapter name>",
  "section": "<section name>",
  "page_range": "<start-end>",
  "source_text": "<optional extracted text>",
  "images_or_diagrams": "<optional>",
  "cbp_terms": "<optional array of terms already introduced by Case-Based Preview>"
}
```

If `source_text` is provided, use it. Otherwise retrieve textbook content from the address.

If `cbp_terms` is provided, the deck **must** reuse those terms verbatim.

---

## 3. How — Process

### Step 1 — Extract source facts

Pull from the textbook section:

- topic (a system, process, reaction, law, organ, equation)
- main rule(s) / formula(s) / process step(s)
- key terms — coordinate with CBP if provided
- worked textbook example(s) or labelled diagram(s)
- common mistake — `provenance: "source"` if textbook lists it, `"inferred"` if you derived it (e.g., confusing photosynthesis with respiration, forgetting units in physics, swapping reactants and products)
- diagram(s) if present — these become candidates for `image_label` cards

### Step 2 — Atomise

One card carries one retrievable thing. Do not pack the whole process into one paragraph back.

**Bad (one card, paragraph back):**

> back: Photosynthesis is a process in chloroplasts where green plants and algae use sunlight, water and carbon dioxide to make glucose and release oxygen; the word equation is CO2 + H2O → glucose + O2; chlorophyll is the green pigment that captures light and is essential for the reaction.

**Good (six cards):**

- Card 1 — `type: definition` — what is photosynthesis (key answer only).
- Card 2 — `type: question_answer` — where it happens.
- Card 3 — `type: question_answer` — inputs.
- Card 4 — `type: question_answer` — outputs.
- Card 5 — `type: formula` — word equation.
- Card 6 — `type: definition` — role of chlorophyll.

This matches the v1 demo (`tests/fixtures/flashcard_demo/biology-photosynthesis.json`).

### Step 3 — Write cards in v1 8-field shape

```json
{
  "front": "<3-14 word retrieval cue>",
  "back": "<5-22 word key answer; never exceed 25 unless formula/process>",
  "hint": "<≤12 word nudge that does not leak the answer>",
  "explanation": "<1-2 short sentences of mechanism / why>",
  "example": "<1 short concrete example>",
  "misconception": "<1 short sentence common error>",
  "type": "definition | term_to_meaning | formula | process_step | question_answer | misconception | image_label",
  "difficulty": "easy | medium | hard"
}
```

Card types used by Sciences: `definition`, `term_to_meaning`, `formula`, `process_step`, `question_answer`, `misconception`, `image_label` (for labelled diagrams — anatomy, circuit, glassware, apparatus).

### Step 4 — Verify length rules

| Field | Limit |
|---|---|
| `front` | 3–14 words |
| `back` | 5–22 words; never over 25 (formula / process exception) |
| `hint` | ≤ 12 words |
| `explanation` | 1–2 short sentences |
| `example` | 1 short sentence |
| `misconception` | 1 short sentence |

### Step 5 — Derive Match Mode

Use cards whose `type` is `definition`, `term_to_meaning`, `formula`, `question_answer`, or `image_label`. For image_label cards, pair the image with its label.

```json
{
  "game_type": "match",
  "instruction": "Match each term with its meaning.",
  "pairs": [
    { "left": "<short term>", "right": "<≤12 word meaning>" }
  ]
}
```

Rules: 6–8 pairs; right side ≤ 12 words; no paragraph definitions.

### Step 6 — Derive Write/Spell Mode

Strong fit for scientific terms, formulas, units, named entities.

```json
{
  "game_type": "write",
  "instruction": "Type the correct term.",
  "items": [
    { "prompt": "<≤20 word cue, e.g. 'Green pigment that absorbs light'>", "answer": "<≤5 word answer, e.g. 'Chlorophyll'>", "hint": "<≤8 word nudge>" }
  ]
}
```

Rules: 5–8 items; answer ≤ 5 words. Accept exact spelling; allow one near-miss retry on long technical terms.

### Step 7 — Derive Learn Mode

Mix item types. Strong types here: `multiple_choice` (which mechanism, which equation), `fix_wrong_answer` (correct an incorrectly stated process), `choose_correct_meaning` (term → meaning).

```json
{
  "game_type": "learn",
  "instruction": "Practice weak and new cards.",
  "items": [
    {
      "question": "<question>",
      "type": "multiple_choice | fill_blank | choose_correct_meaning | choose_example | fix_wrong_answer | short_answer",
      "options": [<options if applicable>],
      "answer": "<correct>",
      "feedback": "<1 short sentence explaining mechanism>"
    }
  ]
}
```

Rules: 5–10 items; one-sentence feedback per item. Distractors should reflect real misconceptions (e.g., for photosynthesis: "plants breathe in oxygen during photosynthesis" as a distractor — captures the respiration confusion).

### Step 8 — Derive Test Mode

Mixed-format final check. No in-test feedback.

```json
{
  "game_type": "test",
  "instruction": "Check what you remember.",
  "items": [
    {
      "question": "<question>",
      "type": "multiple_choice | true_false | fill_blank | short_answer | matching",
      "answer": "<correct>"
    }
  ]
}
```

Rules: 8–12 items mixed; no two consecutive items of the same type when possible.

### Step 9 — Derive Memory Sprint

Fast recall — best fit for terms, units, key facts.

```json
{
  "game_type": "memory_sprint",
  "instruction": "Quick recall — answer fast.",
  "items": [
    { "question": "<≤12 word, e.g. 'Photosynthesis produces?'>", "answer": "<≤5 word, e.g. 'Glucose and oxygen'>" }
  ]
}
```

---

## 4. How — Visual rules (Sciences)

**Default: mixed.** Sciences need both real-world imagery (organisms, equipment, lab scenes) and structural diagrams (mechanisms, equations, circuits). Pick by what the card is teaching.

### Use SVG for:

- Chemical / physical / biological equations
- Reaction mechanisms (chemistry)
- Force / vector diagrams (physics)
- Circuit diagrams (physics)
- Process flowcharts (photosynthesis stages, water cycle, digestion)
- Anatomical schematics (when the label, not the realism, is what matters)
- Periodic-table fragments
- Graphs of measured data

### Use image for:

- Real organisms (a leaf, a cell under microscope when realism matters)
- Lab apparatus when the safety / handling context matters
- Real-world phenomena (lightning, eclipse, geological formations)
- Picture-vocabulary cards (`image_label` type)

### Subject-specific notes

- **Biology:** observation + mechanism + prediction, never numerical calculation. Diagram cards should label the *function* of each structure, not just name it.
- **Physics:** units are part of the answer. A `formula` card showing `F = ma` should have `F` measured in newtons, `m` in kg, `a` in m/s² spelled out in the `explanation` field.
- **Chemistry (kimyo):** balanced equations only. If a textbook gives an unbalanced equation as an intermediate teaching step, balance it before it reaches a flashcard.

### Image-generation fallback

If image generation is unavailable, leave a placeholder and continue:

```markdown
![placeholder: chloroplast cross-section with thylakoid stacks labelled — SVG required](placeholder)
```

Never block on missing visuals.

---

## 5. Card patterns — Sciences

| Card type | Use for | Powers games |
|---|---|---|
| `definition` | "Chlorophyll — green pigment that absorbs light" | Match, Write, Learn, Test, Sprint |
| `term_to_meaning` | Single term → short meaning | Match, Write, Learn, Test, Sprint |
| `formula` | "Photosynthesis equation: `CO2 + H2O → glucose + O2`" | Match, Write, Learn, Test, Sprint |
| `process_step` | "First step of mitosis: prophase — chromosomes condense" | Learn, Test |
| `question_answer` | "Outputs of photosynthesis?" → "Glucose and oxygen" | Write, Learn, Test, Sprint |
| `misconception` | "Plants do respire — not only animals" | Learn, Test |
| `image_label` | Diagram of plant cell — label the chloroplast | Match (img↔label), Write, Learn |

---

## 6. What — Output format

```markdown
# Flashcard & Game Pack: [Lesson Title]

## Metadata
- Subject: [biology / physics / chemistry]
- Grade:
- Topic:
- Textbook address:
- Source concept(s):
- Coordinates with CBP terms: [yes — list / no]

## Source Extraction
- Core concept(s):
- Main rule(s) / formula(s) / process step(s):
- Key terms:
- Common mistake:
  - text:
  - provenance: source | inferred
- Textbook example(s) / diagram(s) used:

## Visual Plan
| Visual | Type | Used in | Purpose |
|---|---|---|---|
| Diagram | svg | Card N back / image_label | Show structure / mechanism / equation |
| Real-world | image OR placeholder | Card N | Organism, apparatus, phenomenon |

## Flashcards

(6–12 cards)

```json
[
  {
    "front": "...",
    "back": "...",
    "hint": "...",
    "explanation": "...",
    "example": "...",
    "misconception": "...",
    "type": "...",
    "difficulty": "..."
  }
]
```

## Game 1 — Match

```json
{
  "game_type": "match",
  "instruction": "Match each term with its meaning.",
  "pairs": [ ... ]
}
```

## Game 2 — Write/Spell

```json
{
  "game_type": "write",
  "instruction": "Type the correct term.",
  "items": [ ... ]
}
```

## Game 3 — Learn

```json
{
  "game_type": "learn",
  "instruction": "Practice weak and new cards.",
  "items": [ ... ]
}
```

## Game 4 — Test

```json
{
  "game_type": "test",
  "instruction": "Check what you remember.",
  "items": [ ... ]
}
```

## Game 5 — Memory Sprint

```json
{
  "game_type": "memory_sprint",
  "instruction": "Quick recall — answer fast.",
  "items": [ ... ]
}
```

## Pass condition
- All cards under 25 words on back.
- All games have `instruction`.
- Match right sides ≤ 12 words; 6–8 pairs.
- Write answers ≤ 5 words; 5–8 items.
- Learn items have 1-sentence `feedback`; 5–10 items.
- Test items mix 5 types, no consecutive same-type; 8–12 items.
- Memory Sprint items short on both ends.
- Every game item traces to a card (sourcing rule).
- Units present in physics formula cards.
- Chemistry equations are balanced.
- If CBP terms were provided, all are reused verbatim.
```

---

## 7. What — Forbids

### General (apply to all flashcard / game generation)

1. Inventing textbook facts, formulas, or definitions.
2. Paragraph-length backs (max 25 words; formula / process exception).
3. Combining multiple concepts into one card.
4. Fronts that prompt explanation ("Explain X", "Describe Y"). Use retrieval cues.
5. Hints that give away the answer.
6. Folding `explanation` / `example` / `misconception` into the `back`.
7. Missing `type` or `difficulty`.
8. Games using vocabulary the cards did not introduce.
9. Missing `instruction` string on any game shape.
10. Match pairs with right side > 12 words.
11. Write answers > 5 words.
12. Skipping `feedback` in Learn items.
13. Disagreement between the deck and `cbp_terms` when provided.

### Sciences specific

14. **Biology — numerical calculation.** Biology is observation + explanation + prediction. Number-crunching belongs in Physics / Chemistry.
15. **Physics — missing units.** Every measured quantity must carry its unit. `F = 10` is not a complete answer; `F = 10 N` is.
16. **Chemistry — unbalanced equations.** All equations on flashcards are balanced. State symbols (`(s)`, `(l)`, `(g)`, `(aq)`) added when teachable at grade level.
17. Decorative diagrams that do not carry the actual concept (a generic leaf clipart on a chlorophyll card adds nothing — label the chloroplast inside the leaf or use SVG).
18. Diagrams copied directly from the textbook.
19. SVGs with unreadable labels or tiny figures.
20. Mechanism explanations that exceed the `explanation` field's 1–2 short sentences — if it needs more, the mechanism belongs in a process_step chain across multiple cards.
21. Lab-safety information in a `misconception` field. Safety is its own concern; if a card is genuinely about safety, make it a `definition` or `question_answer` card with safety as the topic, and put the consequence in `example`.

---

## 8. Uzbek language (when language=uz)

Defer to **`NETS_Uzbek_Language_Foundation_Review_v1_3.md`** for language quality, simplification, formal register, and cultural context.

Critical points to enforce here:

- Formal **Siz** — never `sen` / `san` in any explanation / example / feedback text.
- Short logical sentences; student-friendly wording.
- Never change formulas, units, equations, or numerical values in translation.
- Use established Uzbek scientific terminology where it exists (e.g., *fotosintez*, *xlorofill*, *kuch*, *tezlanish*) — don't reverse-engineer from Russian or English.
- Explain hard terms inline (e.g., *xlorofill — yashil pigment, yorug'likni yutadi*).
- Chemistry symbols and element names: use both the international symbol and the Uzbek name on first introduction (e.g., *Vodorod (H)*, *Kislorod (O)*).

---

## 9. Self-check (run before output)

```txt
[ ] 6–12 flashcards generated
[ ] All cards have all 8 fields
[ ] All backs ≤ 25 words (formula / process exception accounted for)
[ ] No "Explain X" / "Describe X" fronts
[ ] Every hint avoids leaking the answer
[ ] Card types valid (definition / term_to_meaning / formula / process_step / question_answer / misconception / image_label)
[ ] Difficulty assigned (easy / medium / hard)
[ ] Match game has 6–8 pairs, all right sides ≤ 12 words, has instruction
[ ] Write game has 5–8 items, all answers ≤ 5 words, has instruction
[ ] Learn game has 5–10 items mixing 6 item types, every item has 1-sentence feedback, has instruction
[ ] Test game has 8–12 items mixing 5 item types, no consecutive same-type, no in-test feedback, has instruction
[ ] Memory Sprint has short Qs (≤ 12 words) and short As (≤ 5 words), has instruction
[ ] Every game item traces to a card in the deck (sourcing rule)
[ ] CBP terms reused verbatim if provided
[ ] Common mistake provenance marked (source / inferred)
[ ] Inferred mistakes NOT presented as textbook-stated
[ ] Biology cards contain no numerical calculation
[ ] Physics formula cards carry units
[ ] Chemistry equations are balanced
[ ] No decorative diagrams; every visual labels or shows the actual concept
[ ] SVG used for diagrams/equations; image only for organisms / apparatus / phenomena
[ ] Uzbek text is formal, clear, student-friendly (if applicable)
```

If any line fails, regenerate the affected portion.

---

## 10. Final test

The output is valid only if the student can say:

> I learned 6–12 specific things from this lesson, each on its own card.
> I matched names to meanings or labels to diagrams via Match.
> I typed scientific terms and formulas from memory via Write.
> I practiced mechanism and explanation tasks via Learn.
> I checked my memory under pressure via Test.
> I drilled my quickest facts via Sprint.
> Every game pulled from the same cards I just studied — nothing felt invented.
> Units, equations, and diagrams stayed accurate the whole way.

If the student would say *"the game asked about an organ I never saw labelled,"* or *"the equation lost its units,"* regenerate.

---

*End of Sciences Flashcard & Game Generation Prompt.*
