# Prompt: Game Breaks — Math + Algebra

You are building the Game Breaks (Phase 3) for a Math/Algebra homework session. This is where real practice starts. The student applies what they learned in Preview through gamified repetition.

## Input

- Textbook page (image or text)
- Preview + Flash Cards + Sprint outputs (from previous steps)
- Grade: G5-6 (Matematika) or G7-9 (Algebra)
- Mode: Easy | Hard

## Output

Tile Match + Sentence Fill every session. Error Detection as well when the chapter has a canonical procedure students routinely mis-execute.

Mode changes the load, not the game count:
- **Easy** — Tile Match at its grade-banded board size, Sentence Fill 5-6 items, mostly 1-blank passages.
- **Hard** — Tile Match at its grade-banded board size, Sentence Fill 7-8 items, with 2-4 blank passages carrying multi-step procedures.

Every item tagged with `[Bloom: LX | PISA: LX]`.

---

## Supported Games Only

Three games exist in the practice arc. Use these and nothing else:

| Display name | Contract key | How it works |
|---|---|---|
| **Sentence Fill** | `sentence_fill` | Cloze passage. `___` marks each blank; the student fills every blank from a word bank or from free recall. |
| **Tile Match** | `tile_match` | Left/right concept pairs the student matches on a grade-banded board. |
| **Error Detection** | `error_detection` | A complete, confident, WRONG artifact. The student taps the segment where it goes wrong, then optionally names the error type and writes the correction. |

**Do not reference any game outside this list.** Any unlisted, legacy, or newly
invented game is unsupported: it does not render, and its array is dropped on
import.

**Tile Match and Sentence Fill run in every session.** Easy and Hard differ by
item count and difficulty mix, not by how many of these two appear. Do not invent
a game to pad the arc.

**Error Detection is the one conditional slot.** Select it when the chapter has a
canonical procedure students routinely mis-execute — it trains error-spotting
rather than production, so it earns its place only where there is a procedure
worth mis-executing. When you do not select it, omit the `error_detection` key
entirely; never emit an empty array.

### What each game is for in Math/Algebra

| Game | Math use |
|---|---|
| **Tile Match** | Formula ↔ visual, expression ↔ simplified form, term ↔ definition, formula ↔ name, number ↔ representation, equation ↔ graph, step ↔ justification. |
| **Sentence Fill** | Missing operation, missing step, missing term in a procedure. Carries the multi-step solving work that used to live in a quiz. |
| **Error Detection** | A wrong worked solve the student audits: transposition, distribution and sign slips caught in the step where they happen, not in the final answer. |

## What goes in which game

Tile Match and Sentence Fill always appear, so the decision is what each one
carries. Error Detection is added on top when the chapter earns it:
- **Procedural chapter** (solving methods) → Sentence Fill carries the procedure as an ordered multi-blank passage; Tile Match carries step ↔ justification
- **Vocabulary-heavy chapter** (new terms) → Tile Match is term ↔ definition; Sentence Fill puts the term back into a worked line
- **Formula-heavy chapter** → Tile Match is formula ↔ visual; Sentence Fill removes one variable or one operator from the formula in use
- **Mixed chapter** → split the Tile Match board into two `concept_family` groups and let Sentence Fill carry the procedure
- **Procedure the chapter drills and students routinely mis-execute** → add Error Detection, and put its errors in the step the procedure actually turns on, not in the arithmetic around it

Never test the same item the same way in two different games. If a formula is a Tile Match pair, Sentence Fill should require applying it, not restating it.

---

## Construction per game

### Tile Match
**Board size by grade** — the builder recommends by grade, and 8 is a hard cap:

| Grade | Pairs |
|---|---|
| G1-G2 | 4 |
| G3-G4 | 5 |
| G5-G7 | 6 |
| G8 and above | 8 |

Never author more than 8 pairs at any grade; a 9th pair is rejected.

- Left tile: formula, expression, or term
- Right tile: visual, simplified form, definition, or equivalent
- G5-6: fraction ↔ visual, formula ↔ bar model, number ↔ word form, formula ↔ name
- G7-9: expression ↔ equivalent, equation ↔ graph, step ↔ justification, identity pairs, function ↔ graph
- Group the board with `concept_family` — one family per method or per formula group
- Difficulty ladder across the board: `easy` term ↔ definition → `medium` expression ↔ equivalent → `hard` step ↔ justification, where the pair only resolves if the student knows WHY the step is legal
- Every `left` and every `right` must be unique across the board

### Sentence Fill
- Easy 5-6 items, Hard 7-8 items
- `mode`: `word_bank` for G5-G7, `free_recall` for G8-9
- Show a procedure or formula with one piece missing per `___`; 1-4 blanks per passage
- The gap must test mathematical understanding — not random word removal
- A multi-step solve is a multi-blank passage, and the blanks must be in solve order so the student reconstructs the method:
  - G5-6: `"43 × 20 = 43 × ___ × 10"` → answers `["2"]`
  - G7-9: `"2x + 4 = 10 → 2x = 10 ___ 4 → x = ___"` → answers `["−", "3"]`
- G5-6 stay at single-step recall; G7-9 carry the multi-step reasoning load as `free_recall` passages with no bank to lean on
- In `word_bank` mode the distractor is the sign error or the inverse operation the student is actually likely to make (`"+"` against `"−"`, `"×"` against `"÷"`), never a random symbol
- Use `explanations` to name the error the distractor represents

---

### Error Detection

> **Authored ahead of the renderer — this is deliberate.** No MARK renderer ships yet, so Error Detection content is stored and validated but does not reach students today. Author it to the same standard as the other two games anyway, so it is correct the moment the renderer lands.

Show the student a **complete, confident, WRONG** worked artifact. They tap the
segment where it goes wrong, then — when you ask for it — name the error type and
write the correction.

**Item count:** 4-6 artifacts. Each artifact is one item.

**Stages.** `mark` is mandatory and always present. Add `classify` when the error
taxonomy below is worth drilling, and `correct` when the fix has one canonical
written form.

**The two rules that make this game work. Both are load-bearing:**

1. **Exactly one error per artifact, and every step after the error must stay
   internally consistent with it.** If the working visibly breaks downstream, the
   student finds the error by inspection instead of by checking the step, and the
   game degrades into spot-the-typo. This is the hardest authoring rule and the
   one that decides whether the item teaches anything. Never author more than two
   errors in one artifact.
2. **One clean artifact per set** — `faulty_segment_ids: []`. Without it, "there
   is always an error somewhere" is a free heuristic and the game measures
   nothing. The clean artifact is answered correctly by marking nothing; it is
   not a mistake and must never be "fixed" by inventing an error.

**Segment at the granularity of the mistake** — one segment per line of working,
per clause, per equation side. Whatever unit the error lives in. Never split a
segment so finely that the student has to guess which half you meant.

**Put the error mid-artifact at least half the time.** Students already check the
last line. And never author a "wrong answer" with no wrong *step* — a bare wrong
result is a quiz question, not this game.

The `explanation` is shown only after the attempt. Write it as the reason the
step is wrong, not as a restatement of the right answer.

**Error categories — use these exact ids. This is the closed list for Math/Algebra; do not invent one per item, and do not borrow another subject's list. The point is that the student learns the taxonomy:**

| id | what it means |
|---|---|
| `sign` | A sign lost or flipped, most often moving a term across the equals sign. |
| `order_of_ops` | Operations applied in the wrong order. |
| `distribute` | A factor not distributed across every term inside the bracket. |
| `transpose` | A term moved across the equals sign without inverting its operation. |
| `arithmetic` | The method is right; the computation is not. |
| `unsimplified` | Correct but unfinished — a fraction left unreduced, like terms left uncollected. |

- `artifact.kind`: `worked_solution` for a multi-step solve, `equation` for one line.
- Put the error in the transposition or the distribution, not in the final
  arithmetic. An arithmetic slip is the one students already catch, so it makes
  the easiest and least useful item.
- Use `arithmetic` sparingly and only at `easy`.
- Keep every later line consistent with the error: if the wrong step yields
  `2x = 20`, the next line must read `x = 10`, never `x = 4`.

**Worked example (Algebra, G7):**

`artifact.kind`: `worked_solution`, `artifact.segments`:

1. `2x + 6 = 14`
2. `2x = 14 + 6`
3. `2x = 20`
4. `x = 10`

→ `faulty_segment_ids: ["s2"]`, `category: "transpose"`,
`fix: "2x = 14 - 6"`,
`explanation: "6 chap tomondan olib tashlanadi, shuning uchun o'ng tomonda ayiriladi."`

Note that segments 3 and 4 are *internally consistent with the error*: 14 + 6 really
is 20, and 20 ÷ 2 really is 10. That is the craft. The student cannot find the
mistake by spotting a broken arithmetic chain, only by checking the transposition.

## Rules

- Every item tagged: `[Bloom: LX | PISA: LX]`
- Do not reference any game outside the Supported Games table
- Current chapter content only
- Language: Uzbek, "Siz" formal
- Visuals: if a game item needs a diagram (graph, shape, equation visual), generate inline SVG. Keep simple — under 200×150px.

---

## OUTPUT REQUIREMENT

Return valid JSON matching this exact schema. **Omit optional game arrays only
when that game is not selected** — never emit an empty array, and never emit a
key for a game you did not build.

```json
{
  "sentence_fill": [
    {
      "id": "sf_001",
      "mode": "word_bank|free_recall",
      "passage": "Text with ___ marking each blank.",
      "answers": ["one entry per ___, in blank order"],
      "word_bank": ["every answer", "plus at least one distractor"],
      "explanations": ["one per answer, or omit the key"],
      "tags": "[Bloom: LX | PISA: LX]",
      "difficulty": "easy|medium|hard",
      "pisa_level": "L1|L2|L3|L4|L5"
    }
  ],
  "tile_match": [
    {
      "id": "tm_001",
      "left": "concept side, 300 chars max",
      "right": "definition side, 300 chars max",
      "concept_family": "grouping label",
      "subject_family": "math|biology|history|literature|physics|chemistry|language|geography|general",
      "difficulty": "easy|medium|hard",
      "pisa_level": "L1|L2|L3|L4|L5|L6"
    }
  ],
  "error_detection": [
    {
      "id": "ed_001",
      "artifact": {
        "kind": "worked_solution|sentence|equation|proof|procedure",
        "segments": [
          { "id": "s1", "text": "one line of working or one clause, 500 chars max", "svg": null }
        ]
      },
      "stages": ["mark"],
      "categories": ["the closed list for this subject, shown to the student"],
      "faulty_segment_ids": ["s2"],
      "category": "one id from categories, or null when the artifact is clean",
      "fix": "the corrected segment",
      "explanation": "why that step is wrong",
      "tags": "[Bloom: LX | PISA: LX]",
      "difficulty": "easy|medium|hard"
    }
  ]
}
```

The server validates every one of these (`server/schemas/content.py`):

- `sentence_fill.passage` must contain 1-6 `___` markers. `answers` length must equal the marker count, in blank order.
- `sentence_fill.mode` is `word_bank` (G2-G7) or `free_recall` (G8+). When `word_bank`, the `word_bank` key is required, must contain every answer, and must carry at least one extra distractor.
- `sentence_fill.explanations`, when present, must be exactly as long as `answers`.
- `tile_match` holds 0-8 pairs. `left` and `right` must each be non-empty and 300 characters or fewer.
- Every `tile_match.id` is unique, every `left` is unique, and every `right` is unique — a repeated side breaks the distractor logic and the whole board is rejected.
- `tile_match.subject_family` is always `"math"` in this file.
- `error_detection.artifact.segments` must be non-empty; every segment `id` must be unique within its item, and every `text` non-empty and 500 characters or fewer.
- `error_detection.stages` must be a non-empty subset of `["mark", "classify", "correct"]` and must contain `"mark"`.
- Every id in `error_detection.faulty_segment_ids` must exist in that item's `artifact.segments`. An answer key pointing at a segment that does not exist is rejected — it is the bug most worth catching.
- `faulty_segment_ids: []` is **legal and required once per set** — it is the clean artifact, answered correctly by marking nothing. It is not an authoring mistake and it will not be validated away.
- When `"classify"` is in `stages`, `categories` must be non-empty and `category` must be one of those ids (or `null`, but only when the artifact is clean).
- `faulty_segment_ids`, `category`, `fix` and `explanation` are **server-only** — they are stripped before the item reaches the student's browser. Author them anyway: grading and post-attempt feedback depend on them.
