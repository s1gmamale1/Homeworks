# NETS Flashcard & Game — Generation Prompt: Math Family

**Subjects covered:** Math, Algebra, Geometry
**Source standard:** `docs/flashcard-game-prompt-rules.md` (v1 active-recall contract)
**Companion file (Uzbek validation):** `NETS_Uzbek_Language_Foundation_Review_v1_3.md` — the Uzbek Language Foundation standard. Owns language quality, simplification rules, formal register, cultural context, and subject-specific Uzbek guardrails. Reference this file for any Uzbek validation question on the card copy.

> This document IS the prompt. An AI given a textbook address and these rules should be able to generate the flashcard deck plus all five study games for one lesson without further human guidance.

---

## 1. Context (small)

You are generating two coordinated artifacts from one math / algebra / geometry textbook section:

1. A **flashcard deck** of 6–12 active-recall cards in the v1 8-field shape.
2. **Five study games** sourced 1:1 from those cards: Match, Write/Spell, Learn, Test, Memory Sprint.

The deck teaches atomic facts — one card carries one retrievable idea, the back never exceeds 25 words (formula and process-step cards excepted). The games reuse the same cards under different cognitive loads. Cards and games together are one learning unit; the games never invent vocabulary the cards did not introduce.

**Stakes:** medium. This is the practice round between the Case-Based Preview and the Final Challenge.

You do not need to know anything else about the larger homework flow. Just produce one deck plus five games.

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
  "cbp_terms": "<optional array of terms already introduced by Case-Based Preview>"
}
```

If `source_text` is provided, use it. Otherwise retrieve the textbook content from the address.

If `cbp_terms` is provided, the flashcard deck **must** reuse those terms verbatim — coordination with Case-Based Preview is non-negotiable. Same lesson, same anchors.

---

## 3. How — Process

### Step 1 — Extract source facts

Pull from the textbook section:

- topic
- core concept(s) — every concept that requires its own retrieval becomes its own card; aim 6–12 cards
- main rule(s) / formula(s)
- key terms — coordinate with CBP if `cbp_terms` is present
- worked textbook example(s)
- common mistake — `provenance: "source"` if textbook lists it, `"inferred"` if you derived it (e.g., typical sign-flip error, dropping ±, swapping numerator/denominator)
- visual model(s) if any

### Step 2 — Atomise concepts

Math family rule: never combine definition + formula + caveat into one back paragraph. Use the dedicated `explanation`, `example`, and `misconception` fields for the supporting context.

**Bad (one card, paragraph back):**

> back: A quadratic equation is `ax² + bx + c = 0` where `a ≠ 0`; we solve with the quadratic formula; a common mistake is forgetting the ± sign which gives only one root instead of both.

**Good (three cards):**

- Card 1 — `type: definition` — quadratic equation in standard form.
- Card 2 — `type: formula` — quadratic formula.
- Card 3 — `type: misconception` — dropping the ± loses a root.

### Step 3 — Write cards in v1 8-field shape

For each atomic concept, produce one card:

```json
{
  "front": "<3-14 word retrieval cue>",
  "back": "<5-22 word key answer; never exceed 25 unless formula/process>",
  "hint": "<≤12 word nudge that does not give away the answer>",
  "explanation": "<1-2 short sentences of context>",
  "example": "<1 short sentence applied case>",
  "misconception": "<1 short sentence common error>",
  "type": "definition | formula | process_step | example | misconception | question_answer",
  "difficulty": "easy | medium | hard"
}
```

Card types used by Math Family: `definition`, `formula`, `process_step`, `question_answer`, `misconception`. The `example` type is rare here — most worked examples belong inside the `example` field of another card, not as a standalone card.

### Step 4 — Verify length rules

| Field | Limit |
|---|---|
| `front` | 3–14 words |
| `back` | 5–22 words; never over 25 (formula / process-step exception) |
| `hint` | ≤ 12 words |
| `explanation` | 1–2 short sentences |
| `example` | 1 short sentence |
| `misconception` | 1 short sentence |

If any back exceeds the limit, split into two cards. Do not abbreviate by stripping the verb.

### Step 5 — Derive Match Mode

Use cards whose `type` is `definition`, `formula`, `process_step`, or `question_answer` and whose back fits in 12 words.

```json
{
  "game_type": "match",
  "instruction": "Match each term with its meaning.",
  "pairs": [
    { "left": "<short term>", "right": "<≤12 word meaning>" }
  ]
}
```

Rules: 6–8 pairs; right side ≤ 12 words; no paragraph definitions. If your deck has fewer than 6 pair-shaped cards, add more cards rather than padding with non-pair types.

### Step 6 — Derive Write/Spell Mode

Use cards where the answer is a short term, formula, or named entity.

```json
{
  "game_type": "write",
  "instruction": "Type the correct term.",
  "items": [
    { "prompt": "<≤20 word cue>", "answer": "<≤5 word typable answer>", "hint": "<≤8 word nudge>" }
  ]
}
```

Rules: 5–8 items; answer ≤ 5 words (Math Family: usually 1–2 words for terms, short symbolic for formulas — e.g., `a² + b² = c²`).

### Step 7 — Derive Learn Mode

Adaptive practice. Mix item types. Surface `difficulty: hard` cards more often.

```json
{
  "game_type": "learn",
  "instruction": "Practice weak and new cards.",
  "items": [
    {
      "question": "<question text>",
      "type": "multiple_choice | fill_blank | choose_correct_meaning | choose_example | fix_wrong_answer | short_answer",
      "options": [<MCQ options if applicable>],
      "answer": "<correct>",
      "feedback": "<1 short sentence>"
    }
  ]
}
```

Rules: 5–10 items; one-sentence feedback per item; MCQ has 1 correct + 3 plausible distractors drawn from real student mistakes when known.

### Step 8 — Derive Test Mode

Mixed-format final check. No feedback during the test.

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

Rules: 8–12 items mixed across types; no two consecutive items of the same type when possible.

### Step 9 — Derive Memory Sprint

Fast recall only.

```json
{
  "game_type": "memory_sprint",
  "instruction": "Quick recall — answer fast.",
  "items": [
    { "question": "<≤12 word question>", "answer": "<≤5 word answer>" }
  ]
}
```

---

## 4. How — Visual rules (Math Family)

**Default: SVG.** Math is numeric and structural; SVG carries it better than raster images.

### Use SVG for:

- Fraction bars, area models
- Coordinate planes, graphs, function plots
- Geometric figures (triangles, polygons, circles, angles, constructions)
- Step diagrams (factoring steps, equation rearrangement)
- Number lines
- Formula visualisations
- Before/after states (e.g., `3/5 ℓ` glass split into 3 cups)

### Use image for:

- Real-world scene context only (workshop, classroom, market) — and only if the card carries a context that genuinely needs it (rare for atomic flashcards; common for CBP, not for this prompt)

### Geometry specifically

Strongest visual demand of the family. Every figure, angle, polygon, or construction is SVG. Image only for the real-world setting before transitioning to the SVG geometric model — but on a flashcard deck this is usually overkill; prefer SVG-only.

### Image-generation fallback

If image generation is unavailable, leave a placeholder and continue:

```markdown
![placeholder: right triangle with legs a, b and hypotenuse c — SVG required](placeholder)
```

Never block on missing visuals.

---

## 5. Card patterns — Math Family

| Card type | Use for | Powers games |
|---|---|---|
| `definition` | "Quadratic equation = `ax² + bx + c = 0`, `a ≠ 0`" | Match, Write, Learn, Test, Sprint |
| `formula` | "Pythagorean theorem: `a² + b² = c²`" | Match, Write, Learn, Test, Sprint |
| `process_step` | "First step in solving by factoring: rearrange to standard form." | Learn, Test |
| `question_answer` | "Sum of angles in a triangle?" → "180°" | Write, Learn, Test, Sprint |
| `misconception` | "`(a + b)² ≠ a² + b²` — there is a `2ab` cross term." | Learn, Test |
| `example` | Rare as standalone; usually lives inside another card's `example` field. | Learn |

---

## 6. What — Output format

```markdown
# Flashcard & Game Pack: [Lesson Title]

## Metadata
- Subject: [math / algebra / geometry]
- Grade:
- Topic:
- Textbook address:
- Source concept(s):
- Coordinates with CBP terms: [yes — list / no]

## Source Extraction
- Core concept(s):
- Main rule(s) / formula(s):
- Key terms:
- Common mistake:
  - text:
  - provenance: source | inferred
- Textbook example(s) used:

## Visual Plan
| Visual | Type | Used in | Purpose |
|---|---|---|---|
| Concept figure | svg | Card N back / Learn item | Show formula or shape |
| Real-world scene | image OR placeholder | Optional context only | Where this math is used |

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
- All cards under 25 words on back (formula/process exception accounted for).
- All games have a required `instruction` string.
- Match right sides ≤ 12 words; 6–8 pairs.
- Write answers ≤ 5 words; 5–8 items.
- Learn items have a one-sentence `feedback`; 5–10 items.
- Test items mix 5 types, no consecutive same-type; 8–12 items.
- Memory Sprint items have ≤ 12-word Qs and ≤ 5-word As.
- Every game item traces to a flashcard in the deck above (sourcing rule).
- If CBP terms were provided, all of them are reused verbatim in the deck.
```

---

## 7. What — Forbids

### General (apply to all flashcard / game generation)

1. Inventing textbook facts, formulas, or definitions.
2. Paragraph-length backs (max 25 words; formula / process exception only).
3. Combining multiple concepts into one card.
4. Fronts that prompt explanation ("Explain X", "Describe Y", "Discuss Z"). Use retrieval cues instead.
5. Hints that give away the answer.
6. Folding `explanation` / `example` / `misconception` into the `back` field.
7. Missing `type` or `difficulty`.
8. Games inventing vocabulary the cards did not introduce (sourcing rule).
9. Missing `instruction` string on any game shape.
10. Match pairs with right side > 12 words.
11. Write answers > 5 words.
12. Skipping the `feedback` field in Learn items.
13. Disagreement between the flashcard deck and `cbp_terms` when provided.

### Math Family specific

14. Changing numbers, variables, formulas, units, or calculation order.
15. Decorative SVGs that do not carry the actual problem content.
16. SVGs with unreadable labels or tiny figures.
17. Copying textbook artwork directly.
18. Using image where SVG would do the math content better.
19. Word-problem flashcards — those belong in Case-Based Preview. Flashcards are atomic facts, not scenarios.
20. Process-step cards that exceed 25 words by chaining multiple sub-steps. Each step is its own card.

---

## 8. Uzbek language (when language=uz)

Defer to **`NETS_Uzbek_Language_Foundation_Review_v1_3.md`** for language quality, simplification, formal register, and cultural context.

Critical points to enforce here:

- Formal **Siz** — never `sen` / `san` in any explanation / example / feedback text.
- Short logical sentences; student-friendly wording.
- Never change numbers, formulas, variables, units, or calculation order in translation.
- No Russian or English calques in sentence structure (e.g., don't directly map `let x equal` to Russian-syntax Uzbek).
- Explain hard terms inline (e.g., *kvadratik tenglama — bu `ax² + bx + c = 0` shakldagi tenglama*).

---

## 9. Self-check (run before output)

```txt
[ ] 6–12 flashcards generated
[ ] All cards have all 8 fields (front, back, hint, explanation, example, misconception, type, difficulty)
[ ] All backs ≤ 25 words (formula / process exception accounted for)
[ ] No "Explain X" / "Describe X" fronts
[ ] Every hint avoids leaking the answer
[ ] Card types valid (definition / formula / process_step / example / misconception / question_answer)
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
[ ] Numbers, formulas, units preserved exactly
[ ] SVG used for math content; image only for real-world scene
[ ] Uzbek text is formal, clear, student-friendly (if applicable)
```

If any line fails, regenerate the affected portion.

---

## 10. Final test

The output is valid only if the student can say:

> I learned 6–12 specific things, each on its own card.
> I tested myself on names and meanings via Match.
> I had to type the terms from memory via Write.
> I practiced mixed formats adaptively via Learn.
> I checked my memory under pressure via Test.
> I drilled my quickest facts via Sprint.
> Every game pulled from the same cards I just studied — nothing felt invented.

If the student would say *"the game asked me about a term I never saw,"* regenerate the games. If the student would say *"the card just gave me a paragraph to read,"* regenerate the deck.

---

*End of Math Family Flashcard & Game Generation Prompt.*
