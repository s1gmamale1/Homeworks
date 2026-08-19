# Prompt: Game Breaks — Physics

You are building the Game Breaks (Phase 3) for a Physics homework session. Real practice starts here — the student applies what they learned through gamified repetition.

## Input

- Textbook page + all previous phase outputs
- Grade: G7-11 (Fizika)
- Mode: Easy | Hard

## Output

Tile Match + Sentence Fill every session. Error Detection as well when the chapter has a canonical procedure students routinely mis-execute.

Mode changes the load, not the game count:
- **Easy** — Tile Match at its grade-banded board size, Sentence Fill 5-6 items, mostly 1-blank passages.
- **Hard** — Tile Match at its grade-banded board size, Sentence Fill 7-8 items, with 2-4 blank passages carrying derivations and unit conversions.

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

### What each game is for in Physics

| Game | Physics use |
|---|---|
| **Tile Match** | Formula ↔ law name, quantity ↔ unit, symbol ↔ quantity, diagram ↔ concept, cause ↔ effect, term ↔ definition. |
| **Sentence Fill** | Missing variable in a formula, missing unit, missing step in a derivation. Carries the formula-application and unit-conversion work that used to live in a quiz. |
| **Error Detection** | A worked calculation with one bad step — an unconverted unit, a formula that does not apply here, a dropped vector sign. |

## What goes in which game

Tile Match and Sentence Fill always appear, so the decision is what each one
carries. Error Detection is added on top when the chapter earns it:
- **Formula-heavy chapter** → Sentence Fill removes the variable in use (`F = m × ___`); Tile Match carries formula ↔ law name
- **Terminology chapter** → Tile Match is term ↔ definition and symbol ↔ quantity; Sentence Fill puts the term into a physical statement
- **Multi-concept chapter** → Tile Match links formula ↔ quantity ↔ unit across `concept_family` groups; Sentence Fill carries the derivation
- **Measurement chapter** → Sentence Fill carries unit conversion as ordered multi-blank passages
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

- Physics pair types:
  - Formula ↔ law name: `"F = ma"` ↔ `"Nyuton 2-qonuni"`
  - Quantity ↔ unit: `"Kuch"` ↔ `"N (Nyuton)"`
  - Symbol ↔ quantity: `"F"` ↔ `"Kuch"`, `"m"` ↔ `"Massa"`, `"a"` ↔ `"Tezlanish"`
  - Diagram ↔ concept: `[Circuit with resistor]` ↔ `"Om qonuni"`
  - Cause ↔ effect: `"Harorat oshadi"` ↔ `"Jism kengayadi"`
- Group the board with `concept_family` — one family per law or per quantity group, so symbol, quantity and unit for the same concept sit together
- Difficulty ladder across the board: `easy` symbol ↔ quantity → `medium` formula ↔ law name → `hard` diagram ↔ concept, where the pair only resolves if the student reads the physical situation
- Every `left` and every `right` must be unique across the board — `"Kuch"` cannot be the right side of two pairs, so pick one canonical phrasing per quantity

### Sentence Fill
- Easy 5-6 items, Hard 7-8 items
- `mode`: `word_bank` for G7, `free_recall` for G8-11
- Show a formula, law statement, or derivation step with one piece missing per `___`; 1-4 blanks per passage
- The gap must test physical understanding — not random word removal
- **Units are part of the answer.** Where the blank is a quantity, the expected answer carries its unit, and where the blank IS the unit, say so in the passage.
- A derivation is a multi-blank passage, and the blanks must be in derivation order:
  - `"F = m × ___"` → answers `["a"]`
  - `"Kuchning birligi — ___"` → answers `["Nyuton"]`
  - `"Om qonuni: I = U / ___"` → answers `["R"]`
  - `"Ish = Kuch × ___"` → answers `["ko'chirish"]`
  - `"Tezlanish a = (v − v₀) / ___, uning birligi ___"` → answers `["t", "m/s²"]`
- In `word_bank` mode the distractor is the confusable quantity or the wrong unit for the right quantity (`"J"` against `"N"`, `"massa"` against `"og'irlik"`), never a random symbol
- Use `explanations` to name the confusion the distractor represents

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

**Error categories — use these exact ids. This is the closed list for Physics; do not invent one per item, and do not borrow another subject's list. The point is that the student learns the taxonomy:**

| id | what it means |
|---|---|
| `unit` | Units not converted, or the answer carries the wrong unit. |
| `formula_choice` | A valid formula that does not apply to this situation. |
| `sign_vector` | A direction or vector sign dropped or reversed. |
| `substitution` | The right formula, the wrong value substituted into it. |
| `sig_figs` | An answer reported to a precision the data does not justify. |

- `artifact.kind`: `worked_solution`. One segment per line of the calculation:
  the givens, the formula, the substitution, the result.
- `unit` is the highest-value category — carry the unit in the segment text so
  the error is visible to a student who is actually tracking units.
- The substitution line is the best place for the error: the formula above it is
  right, the arithmetic below it is right, and only the value is wrong.

**Worked example (Fizika, G8):**

`artifact.kind`: `worked_solution`, `artifact.segments`:

1. `Berilgan: v = 72 km/soat, t = 5 s`
2. `Formula: s = v · t`
3. `s = 72 · 5`
4. `s = 360 m`

→ `faulty_segment_ids: ["s3"]`, `category: "unit"`,
`fix: "s = 20 · 5"`,
`explanation: "72 km/soat = 20 m/s. Vaqt sekundda berilgan, shuning uchun tezlik ham m/s da bo'lishi kerak."`

Segment 4 is arithmetically correct for segment 3 — 72 × 5 really is 360 — and the
unit `m` is even written confidently. Only a student tracking units finds it.

## Rules

- Every item tagged: `[Bloom: LX | PISA: LX]`
- All answers must carry proper physics units
- Do not reference any game outside the Supported Games table
- Current chapter content only
- Language: Uzbek, "Siz" formal
- Visuals: if a game item needs a diagram (circuit, force vector, graph), generate inline SVG. Keep simple — under 200×150px.

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
- `tile_match.subject_family` is always `"physics"` in this file.
- `error_detection.artifact.segments` must be non-empty; every segment `id` must be unique within its item, and every `text` non-empty and 500 characters or fewer.
- `error_detection.stages` must be a non-empty subset of `["mark", "classify", "correct"]` and must contain `"mark"`.
- Every id in `error_detection.faulty_segment_ids` must exist in that item's `artifact.segments`. An answer key pointing at a segment that does not exist is rejected — it is the bug most worth catching.
- `faulty_segment_ids: []` is **legal and required once per set** — it is the clean artifact, answered correctly by marking nothing. It is not an authoring mistake and it will not be validated away.
- When `"classify"` is in `stages`, `categories` must be non-empty and `category` must be one of those ids (or `null`, but only when the artifact is clean).
- `faulty_segment_ids`, `category`, `fix` and `explanation` are **server-only** — they are stripped before the item reaches the student's browser. Author them anyway: grading and post-attempt feedback depend on them.
