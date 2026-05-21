# NETS Flashcard & Game — Generation Prompt: Languages

**Subjects covered:** Uzbek (as L1), Russian, English, other taught languages
**Source standard:** `docs/flashcard-game-prompt-rules.md` (v1 active-recall contract)
**Companion file (Uzbek validation):** `NETS_Uzbek_Language_Foundation_Review_v1_3.md` — the Uzbek Language Foundation standard. Owns language quality, simplification rules, formal register, cultural context, and subject-specific Uzbek guardrails. Reference this file for any Uzbek validation question on the card copy.

> This document IS the prompt. An AI given a textbook address and these rules should be able to generate the flashcard deck plus all five study games for one lesson without further human guidance.

---

## 1. Context (small)

You are generating two coordinated artifacts from one language-subject textbook section:

1. A **flashcard deck** of 6–12 active-recall cards in the v1 8-field shape — vocabulary items, grammar rules, irregular verb forms, register cues, or short collocations.
2. **Five study games** sourced 1:1 from those cards: Match, Write/Spell, Learn, Test, Memory Sprint.

The deck teaches one retrievable atom per card. The games re-practice the same atoms under different cognitive loads. Cards and games are one learning unit; the games never use vocabulary the cards did not introduce.

**Stakes:** medium. This is the practice round between Case-Based Preview and Final Challenge.

Note: `language` in the inputs is the language the **card copy** is written in (usually Uzbek). `target_language` is what is being taught. They are often different — an Uzbek-speaking student learning English.

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
  "cbp_terms": "<optional array of terms already introduced by Case-Based Preview>"
}
```

If `source_text` is provided, use it. Otherwise retrieve textbook content from the address.

If `cbp_terms` is provided, the deck **must** reuse those terms verbatim.

---

## 3. How — Process

### Step 1 — Extract source facts

Pull from the textbook section:

- topic (a tense, grammar pattern, vocabulary set, register, communication function)
- main rule(s) (e.g., *"present perfect = have/has + V3"*, *"formal letters open with `Hurmatli...`"*, *"`much` with uncountable nouns"*)
- key vocabulary / phrases — must match `cbp_terms` if provided
- textbook example dialogue / passage
- common mistake — `provenance: "source"` if textbook lists it, `"inferred"` if you derived it (typical L1 interference, wrong register, conjugation error, `since`-vs-`for` swap, false friend)
- target CEFR level — never exceed it inside any card

### Step 2 — Atomise

One card carries one retrievable thing. Do not pack a tense rule plus three irregular forms plus a register caveat into one card.

**Bad (one card, paragraph back):**

> back: Present Perfect is formed with `have` / `has` + V3 and is used for actions starting in the past continuing now or just finished; common irregular V3 forms include gone, eaten, written, given, taken; remember to use `since` for points and `for` for durations and never use `yesterday` with Present Perfect.

**Good (four cards):**

- Card 1 — `type: grammar` — Present Perfect formula.
- Card 2 — `type: grammar` — when to use Present Perfect.
- Card 3 — `type: vocabulary` — past participle of *go* → *gone*.
- Card 4 — `type: grammar` — `since` vs `for`.

### Step 3 — Write cards in v1 8-field shape

```json
{
  "front": "<3-14 word retrieval cue>",
  "back": "<5-22 word key answer; never exceed 25>",
  "hint": "<≤12 word nudge that does not leak the answer>",
  "explanation": "<1-2 short sentences of context>",
  "example": "<1 short authentic example sentence in target language>",
  "misconception": "<1 short sentence common error (often L1 interference)>",
  "type": "vocabulary | grammar | term_to_meaning | definition | example | misconception | image_label",
  "difficulty": "easy | medium | hard"
}
```

Card types used by Languages: `vocabulary`, `grammar`, `term_to_meaning`, `definition`, `misconception`, `image_label` (for picture vocabulary). The `example` type is rare; example sentences usually live inside the `example` field of another card.

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

Use `vocabulary`, `term_to_meaning`, `definition`, and `image_label` cards. For image_label cards, Match pairs an image with a label.

```json
{
  "game_type": "match",
  "instruction": "Match each term with its meaning.",
  "pairs": [
    { "left": "<target-language term>", "right": "<≤12 word L1 meaning or English gloss>" }
  ]
}
```

Rules: 6–8 pairs; right side ≤ 12 words; no paragraph definitions.

### Step 6 — Derive Write/Spell Mode

Strongest fit for Languages — vocabulary, irregular forms, conjugations, short answers.

```json
{
  "game_type": "write",
  "instruction": "Type the correct term.",
  "items": [
    { "prompt": "<≤20 word cue, e.g. 'Past participle of `eat`'>", "answer": "<≤5 word typable answer>", "hint": "<≤8 word nudge>" }
  ]
}
```

Rules: 5–8 items; answer ≤ 5 words (usually 1 word for vocabulary, short phrase for collocations). Spelling matters — accept exact match only, give a single retry on near-miss.

### Step 7 — Derive Learn Mode

Mix item types. Strong types here: `multiple_choice` (which form fits), `fill_blank` (sentence with target word missing), `choose_correct_meaning`, `fix_wrong_answer` (correct the sentence).

```json
{
  "game_type": "learn",
  "instruction": "Practice weak and new cards.",
  "items": [
    {
      "question": "<question or sentence with blank>",
      "type": "multiple_choice | fill_blank | choose_correct_meaning | choose_example | fix_wrong_answer | short_answer",
      "options": [<options if applicable>],
      "answer": "<correct>",
      "feedback": "<1 short sentence; explain in the student's L1 if helpful>"
    }
  ]
}
```

Rules: 5–10 items; one-sentence feedback; MCQ has 1 correct + 3 plausible distractors. Distractors should reflect real L1-interference errors when known (e.g., Russian-speaker confusion between `much` and `many`).

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

Fast recall — best fit for vocabulary and irregular forms.

```json
{
  "game_type": "memory_sprint",
  "instruction": "Quick recall — answer fast.",
  "items": [
    { "question": "<≤12 word, e.g. 'Past participle of `give`'>", "answer": "<≤5 word, e.g. 'given'>" }
  ]
}
```

---

## 4. How — Visual rules (Languages)

**Default: image.** Communication and vocabulary are contextual. A real-world scene gives a word its meaning.

### Use image for:

- Picture vocabulary cards (food, animals, places, objects, actions)
- Communication settings (classroom, home, market, café, office) when the card is about register or situational language
- Cultural context where it matters
- Atmosphere / register cues (formal office vs informal playground)

### Use SVG for:

- Sentence-structure blocks (subject | verb | object)
- Conjugation tables
- Tense timelines (past / present / future placement)
- Wrong → corrected sentence comparison
- Tone / register comparison cards (formal vs informal side-by-side)
- Dialogue bubbles when the focus is the linguistic structure, not the speakers

### Image-generation fallback

If image generation is unavailable, leave a placeholder and continue:

```markdown
![placeholder: student writing a message to teacher on phone — image gen required](placeholder)
```

Never block on missing images.

---

## 5. Card patterns — Languages

| Card type | Use for | Powers games |
|---|---|---|
| `vocabulary` | L2 word → L1 meaning, or vice versa | Match, Write, Learn, Test, Sprint |
| `grammar` | Pattern → rule (Present Perfect = `have/has + V3`) | Learn, Test |
| `term_to_meaning` | Single term → definition | Match, Write, Learn, Test, Sprint |
| `image_label` | Picture → label | Match (image↔label), Write (typed label), Learn |
| `misconception` | Common L1-interference error or false friend | Learn, Test |
| `definition` | Term → definition (less common; mostly in metalinguistic vocabulary) | Match, Write, Learn, Test |

---

## 6. What — Output format

```markdown
# Flashcard & Game Pack: [Lesson Title]

## Metadata
- Subject: [english / russian / uzbek / ...]
- Target language:
- CEFR level (if applicable):
- Grade:
- Topic:
- Textbook address:
- Source concept(s):
- Coordinates with CBP terms: [yes — list / no]

## Source Extraction
- Core concept(s):
- Main rule(s) / grammar pattern(s):
- Key vocabulary:
- Common mistake:
  - text:
  - provenance: source | inferred
- Textbook example(s) used:

## Visual Plan
| Visual | Type | Used in | Purpose |
|---|---|---|---|
| Picture vocab | image OR placeholder | Card N | Show object / scene |
| Structure model | svg | Card N back / Learn item | Sentence / tense / register |

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
- Memory Sprint items have ≤ 12-word Qs and ≤ 5-word As.
- Every game item traces to a card (sourcing rule).
- No content above the target CEFR level.
- If CBP terms were provided, all are reused verbatim.
```

---

## 7. What — Forbids

### General (apply to all flashcard / game generation)

1. Inventing textbook facts, grammar rules, or vocabulary definitions.
2. Paragraph-length backs (max 25 words).
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

### Languages specific

14. Tenses, structures, or vocabulary above the target CEFR / grade level — not even inside example sentences.
15. Authoring a fresh passage when the textbook has one — adapt the textbook's.
16. Cliché contexts (cowboy, cricket, baseball) unless the textbook is itself about those topics. Keep relatable to Uzbek students.
17. Reverse-translating idioms or sentence structures from Russian or English into Uzbek (calque trap).
18. Oversimplifying register / formality — match the target language's social norms.
19. Match / Write items where the answer is inferable from option length, formatting, or obvious formality (anti-leak rule).
20. Authentic-sounding English that is in fact textbook-flavoured awkwardness. Read the example sentences out loud — if no native speaker would say it, rewrite.
21. False-friend cards without a `misconception` field warning of the false friend.

---

## 8. Uzbek language (when language=uz)

This is the language the **card copy** is written in, not necessarily the target language being taught.

Defer to **`NETS_Uzbek_Language_Foundation_Review_v1_3.md`** for language quality, simplification, formal register, and cultural context. Critical points:

- Formal **Siz** for any explanation / feedback text — never `sen` / `san`.
- Short logical sentences; student-friendly wording.
- Don't translate target-language grammar terms in misleading ways (e.g., if teaching English *Present Perfect*, use a clear Uzbek explanation, not just a literal translation).
- No Russian-syntax calques.

When the target language **is** Uzbek (teaching Uzbek as L1):
- Use authentic Uzbek constructions.
- Don't reverse-engineer Uzbek from Russian or English templates.

When the target language is something else (English, Russian):
- Card copy (front / back / hint / explanation / misconception) in Uzbek is fine.
- The `example` field must use authentic target-language phrasing — no unnatural English just because it is textbook-flavoured.

---

## 9. Self-check (run before output)

```txt
[ ] 6–12 flashcards generated
[ ] All cards have all 8 fields
[ ] All backs ≤ 25 words
[ ] No "Explain X" / "Describe X" fronts
[ ] Every hint avoids leaking the answer
[ ] Card types valid (vocabulary / grammar / term_to_meaning / definition / example / misconception / image_label)
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
[ ] Nothing above target CEFR / grade level
[ ] No cliché cowboy / cricket / fantasy contexts (unless textbook is about them)
[ ] Target-language example sentences sound natural (no calques)
[ ] Uzbek card copy is formal, clear, student-friendly
[ ] MCQ options don't leak via length / formatting (anti-leak rule)
```

If any line fails, regenerate the affected portion.

---

## 10. Final test

The output is valid only if the student can say:

> I learned 6–12 specific things — words, forms, or rules — each on its own card.
> I matched words to meanings via Match.
> I typed the right form from memory via Write.
> I practiced mixed formats adaptively via Learn.
> I checked my memory under pressure via Test.
> I drilled my quickest recalls via Sprint.
> Every game pulled from the same cards I just studied — nothing felt invented.
> The example sentences sound like real people talking.

If the student would say *"the game asked me about a word I never saw,"* regenerate the games. If the student would say *"the example sentences sound strange,"* regenerate the deck.

---

*End of Languages Flashcard & Game Generation Prompt.*
