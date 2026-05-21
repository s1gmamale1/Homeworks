# NETS Flashcard & Game — Generation Prompt: Humanities

**Subjects covered:** History, Geography, Civics, Literature (scoped initially to History; pattern extends to the others)
**Source standard:** `docs/flashcard-game-prompt-rules.md` (v1 active-recall contract)
**Companion file (Uzbek validation):** `NETS_Uzbek_Language_Foundation_Review_v1_3.md` — the Uzbek Language Foundation standard. Owns language quality, simplification rules, formal register, cultural context, and subject-specific Uzbek guardrails. Reference this file for any Uzbek validation question on the card copy.

> This document IS the prompt. An AI given a textbook address and these rules should be able to generate the flashcard deck plus all five study games for one lesson without further human guidance.

---

## 1. Context (small)

You are generating two coordinated artifacts from one humanities textbook section:

1. A **flashcard deck** of 6–12 active-recall cards in the v1 8-field shape — events, dates, key figures, places, terms, causal links, and common-misconception cards.
2. **Five study games** sourced 1:1 from those cards: Match, Write/Spell, Learn, Test, Memory Sprint.

The deck teaches one retrievable atom per card. Humanities atoms are usually: a name → a role; a date → an event; an event → its main cause; a term → its meaning; a place → its historical significance. The games re-practice those atoms under different cognitive loads.

**Stakes:** medium. Practice round between Case-Based Preview and Final Challenge.

Causal chains (event A → event B → event C) are powerful for History but do not belong on one card — they live as a series of `process_step` cards, each carrying one link.

---

## 2. Inputs

```json
{
  "subject": "history" | "geography" | "civics" | "literature",
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

- topic (an era, a figure, an event, a treaty, an institution, a literary work)
- key people, dates, places, terms
- main events and their immediate causes
- causal links the textbook itself states — do not invent causality the textbook does not assert
- common mistake — `provenance: "source"` if textbook lists it, `"inferred"` if you derived it (e.g., confusing two leaders with similar names, conflating overlapping dates, misattributing a quote, misremembering which kingdom controlled which region in a given century)
- primary-source extracts if any — these are quotation candidates for `question_answer` cards

### Step 2 — Atomise

One card carries one retrievable thing. Do not pack the entire reign of a ruler into a paragraph back.

**Bad (one card, paragraph back):**

> back: Amir Temur founded the Timurid empire in the 14th century, established his capital at Samarqand, conducted military campaigns reaching India and Anatolia, was a patron of arts and architecture commissioning the Bibi-Khanym mosque, and died in 1405 while planning a campaign against China.

**Good (six cards):**

- Card 1 — `type: question_answer` — Amir Temur's capital → Samarqand.
- Card 2 — `type: question_answer` — Year of Amir Temur's death → 1405.
- Card 3 — `type: definition` — Timurid empire (one-sentence definition).
- Card 4 — `type: image_label` — Bibi-Khanym mosque → architectural commission of Amir Temur.
- Card 5 — `type: process_step` — first major military campaign of Amir Temur.
- Card 6 — `type: misconception` — Amir Temur is not the same person as Babur (a common conflation).

This matches the v1 demo pattern (`tests/fixtures/flashcard_demo/history-silk-road.json`).

### Step 3 — Write cards in v1 8-field shape

```json
{
  "front": "<3-14 word retrieval cue>",
  "back": "<5-22 word key answer; never exceed 25>",
  "hint": "<≤12 word nudge that does not leak the answer>",
  "explanation": "<1-2 short sentences of context>",
  "example": "<1 short concrete example: a quote, a place, a specific event>",
  "misconception": "<1 short sentence common error or conflation>",
  "type": "definition | term_to_meaning | question_answer | process_step | example | misconception | image_label",
  "difficulty": "easy | medium | hard"
}
```

Card types used by Humanities: `definition`, `term_to_meaning`, `question_answer`, `process_step` (for causal chains), `misconception`, `image_label` (for portraits, maps, artifacts). The `example` type is rare; specific examples usually live inside another card's `example` field.

### Step 4 — Verify length rules

| Field | Limit |
|---|---|
| `front` | 3–14 words |
| `back` | 5–22 words; never over 25 |
| `hint` | ≤ 12 words |
| `explanation` | 1–2 short sentences |
| `example` | 1 short sentence |
| `misconception` | 1 short sentence |

If any back exceeds the limit, split into two cards.

### Step 5 — Derive Match Mode

Strong fit for Humanities — name↔role, date↔event, place↔significance, term↔meaning.

```json
{
  "game_type": "match",
  "instruction": "Match each term with its meaning.",
  "pairs": [
    { "left": "<short term / name / date>", "right": "<≤12 word meaning / role / event>" }
  ]
}
```

Rules: 6–8 pairs; right side ≤ 12 words. Don't put a paragraph of historical context as the right side.

### Step 6 — Derive Write/Spell Mode

Strong fit for names, dates, places.

```json
{
  "game_type": "write",
  "instruction": "Type the correct term.",
  "items": [
    { "prompt": "<≤20 word cue, e.g. 'Capital city of the Timurid empire'>", "answer": "<≤5 word answer, e.g. 'Samarqand'>", "hint": "<≤8 word nudge>" }
  ]
}
```

Rules: 5–8 items; answer ≤ 5 words. For dates, accept either format the textbook uses (e.g., "1405" or "15th century") but be consistent within one deck.

### Step 7 — Derive Learn Mode

Mix item types. Strong types here: `multiple_choice` (which cause, which figure), `fix_wrong_answer` (correct a wrong attribution), `choose_correct_meaning` (term → meaning), `choose_example` (era → which event).

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
      "feedback": "<1 short sentence explaining the historical context>"
    }
  ]
}
```

Rules: 5–10 items; one-sentence feedback per item. Distractors should reflect real student conflations (e.g., for Timur: Babur as a distractor; for Silk Road: incorrectly placing it inside one century only).

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

Fast recall — best fit for date↔event, name↔role.

```json
{
  "game_type": "memory_sprint",
  "instruction": "Quick recall — answer fast.",
  "items": [
    { "question": "<≤12 word, e.g. 'Year Amir Temur died?'>", "answer": "<≤5 word, e.g. '1405'>" }
  ]
}
```

---

## 4. How — Visual rules (Humanities)

**Default: mixed.** Humanities needs both real imagery (portraits, artifacts, photographs of monuments) and structural diagrams (timelines, maps, causal chains).

### Use SVG for:

- Timelines
- Causal chains (event A → event B → event C)
- Maps with key locations labelled (when a simplified outline carries the lesson better than a photographic map)
- Comparison tables (two empires side by side; old vs new regime)
- Family trees / dynasty diagrams
- Trade-route schematics

### Use image for:

- Historical portraits (when the textbook uses one)
- Monument / building photographs
- Artifacts (coins, manuscripts, weapons)
- Real geographical maps where photographic detail matters
- Picture-vocabulary cards (`image_label` type) — flag of a country, symbol of a movement

### Subject-specific notes

- **History:** distinguish what the textbook *asserts* from what it merely *describes*. Causal claims must be the textbook's, not the AI's invention. Quotations on `question_answer` cards must be reproduced exactly or marked as paraphrase in the `explanation` field.
- **Geography:** numeric data (population, area, GDP) gets units and a year. Without a year a stat is misleading; populations change.
- **Civics:** legal terms must match the current constitutional / legislative text. If the textbook is older than the most recent constitutional amendment, flag this in `explanation` rather than assert outdated facts as current.
- **Literature:** quotations are quoted verbatim. Plot summaries on the back must not spoil endings the textbook intentionally leaves open.

### Image-generation fallback

If image generation is unavailable, leave a placeholder and continue:

```markdown
![placeholder: Silk Road map showing key trade hubs Samarqand, Bukhoro, Kashgar — SVG required](placeholder)
```

Never block on missing visuals.

---

## 5. Card patterns — Humanities

| Card type | Use for | Powers games |
|---|---|---|
| `definition` | "Khanate — a state ruled by a khan" | Match, Write, Learn, Test, Sprint |
| `term_to_meaning` | Single term → short meaning | Match, Write, Learn, Test, Sprint |
| `question_answer` | "Capital of Timurid empire?" → "Samarqand"; "Year of X?" → "Y" | Match, Write, Learn, Test, Sprint |
| `process_step` | Step in a causal chain: "First step toward independence: ..." | Learn, Test |
| `misconception` | Common conflation between figures, eras, or places | Learn, Test |
| `image_label` | Portrait → name; map location → city name; artifact → era | Match (img↔label), Write, Learn |

---

## 6. What — Output format

```markdown
# Flashcard & Game Pack: [Lesson Title]

## Metadata
- Subject: [history / geography / civics / literature]
- Grade:
- Topic:
- Textbook address:
- Source concept(s):
- Coordinates with CBP terms: [yes — list / no]

## Source Extraction
- Core concept(s):
- Key people / dates / places / terms:
- Causal claims the textbook makes:
- Common mistake:
  - text:
  - provenance: source | inferred
- Textbook example(s) / quotation(s) used:

## Visual Plan
| Visual | Type | Used in | Purpose |
|---|---|---|---|
| Timeline / map | svg | Card N back / Learn item | Show sequence / location |
| Portrait / artifact | image OR placeholder | Card N (image_label) | Show real figure / object |

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
- All causal claims trace to the textbook (no AI-invented causality).
- All quotations reproduced exactly OR clearly marked as paraphrase.
- If CBP terms were provided, all are reused verbatim.
```

---

## 7. What — Forbids

### General (apply to all flashcard / game generation)

1. Inventing textbook facts, dates, or attributions.
2. Paragraph-length backs (max 25 words).
3. Combining multiple atoms into one card.
4. Fronts that prompt explanation ("Explain X", "Describe Y"). Use retrieval cues.
5. Hints that give away the answer.
6. Folding `explanation` / `example` / `misconception` into the `back`.
7. Missing `type` or `difficulty`.
8. Games using terms / names / dates the cards did not introduce.
9. Missing `instruction` string on any game shape.
10. Match pairs with right side > 12 words.
11. Write answers > 5 words.
12. Skipping `feedback` in Learn items.
13. Disagreement between the deck and `cbp_terms` when provided.

### Humanities specific

14. **Invented causality.** If the textbook lists *event B* after *event A* without claiming causation, do not write a card saying "A caused B." Use the textbook's own causal language only.
15. **Misquoted primary sources.** Quotations are reproduced exactly. If you cannot reproduce exactly, mark the `example` field as paraphrase.
16. **Anachronism.** Don't apply modern-state names to pre-modern entities (e.g., "Uzbekistan" for a 14th-century kingdom that did not exist by that name).
17. **Political characterisation.** Avoid one-sided framing of contested historical figures in the `back` field. If the textbook itself takes a position, mirror its language; if it is neutral, stay neutral.
18. **Geography statistics without a year.** Population / GDP / area cards must carry a year in the `explanation` field.
19. **Civics — outdated law.** If the textbook predates an amendment, flag the discrepancy in `explanation` rather than presenting outdated law as current.
20. **Literature — plot spoilers** the textbook intentionally avoids. If the textbook teaches act 1 without revealing act 5, the flashcard does the same.
21. Decorative imagery (a generic "castle" on every medieval card) — use the specific artifact / monument the lesson is about.
22. Maps redrawn so a contested boundary takes a side the textbook avoids.

---

## 8. Uzbek language (when language=uz)

Defer to **`NETS_Uzbek_Language_Foundation_Review_v1_3.md`** for language quality, simplification, formal register, and cultural context.

Critical points to enforce here:

- Formal **Siz** — never `sen` / `san` in any explanation / example / feedback text.
- Short logical sentences; student-friendly wording.
- Use established Uzbek spellings of historical names and places (e.g., *Amir Temur*, *Samarqand*, *Buxoro*, *Toshkent*) — not Russified or Anglicised forms.
- For non-Uzbek historical figures, use the form the Uzbek textbook uses; flag in `explanation` if the international spelling differs significantly.
- No Russian or English syntactic calques in causal explanations.
- For Uzbek history (Timurids, Shaybanids, Khanates, the Jadids, independence era), root cards in the textbook's framing.

---

## 9. Self-check (run before output)

```txt
[ ] 6–12 flashcards generated
[ ] All cards have all 8 fields
[ ] All backs ≤ 25 words
[ ] No "Explain X" / "Describe X" fronts
[ ] Every hint avoids leaking the answer
[ ] Card types valid (definition / term_to_meaning / question_answer / process_step / example / misconception / image_label)
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
[ ] All causal claims trace to the textbook (no AI-invented causality)
[ ] All quotations reproduced exactly or clearly marked as paraphrase
[ ] No anachronistic state / place names
[ ] Geography statistics carry a year
[ ] Civics cards match the current legal text (or flag if outdated)
[ ] Literature cards respect intentional plot ambiguity
[ ] SVG used for timelines / maps / causal chains; image only for real figures / artifacts
[ ] Uzbek text is formal, clear, student-friendly (if applicable)
[ ] Uzbek place / person names use established Uzbek forms
```

If any line fails, regenerate the affected portion.

---

## 10. Final test

The output is valid only if the student can say:

> I learned 6–12 specific things from this lesson, each on its own card.
> I matched names to roles or dates to events via Match.
> I typed names, places, and dates from memory via Write.
> I practiced cause-and-effect and explanation tasks via Learn.
> I checked my memory under pressure via Test.
> I drilled my quickest recalls via Sprint.
> Every game pulled from the same cards I just studied — nothing felt invented.
> Causal claims stayed honest to what the textbook said.
> Quotations stayed exact, or were clearly marked as my paraphrase.

If the student would say *"the game claimed event A caused event B but the textbook never said that,"* or *"the date on this card is one year off from my book,"* regenerate.

---

*End of Humanities Flashcard & Game Generation Prompt.*
