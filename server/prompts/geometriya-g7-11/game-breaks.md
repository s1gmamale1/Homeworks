# Prompt: Game Breaks — Geometry

You are building the Game Breaks (Phase 3) for a Geometry homework session. This is where real practice starts. The student applies what they learned in Preview through gamified repetition.

## Input

- Textbook page (image or text)
- Preview + Flash Cards + Sprint outputs (from previous steps)
- Grade: G7-9 (Geometriya)
- Mode: Easy | Hard

## Output

Tile Match + Sentence Fill every session. Error Detection as well when the chapter has a canonical procedure students routinely mis-execute.

Mode changes the load, not the game count:
- **Easy** — Tile Match at its grade-banded board size, Sentence Fill 5-6 items, mostly 1-blank passages.
- **Hard** — Tile Match at its grade-banded board size, Sentence Fill 7-8 items, including at least one 4-6 blank proof passage.

Every item tagged with `[Bloom: LX | PISA: LX]`.

> **SVG Rule:** Every diagram in every game must be actual SVG code — not a bracket description alone. Use `instruction.md` → SVG Output Rule for templates, color hex codes, and mark syntax. Every question involving a shape references a diagram.

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

### What each game is for in Geometry

| Game | Geometry use |
|---|---|
| **Tile Match** | Theorem name ↔ diagram, angle type ↔ degree range, congruence criterion ↔ marked figure, notation ↔ diagram, mark ↔ meaning, property clue ↔ shape or theorem. |
| **Sentence Fill** | Missing reason in a proof step, missing condition in a theorem, missing value in an angle chain. Carries the ordered proof and construction work. |
| **Error Detection** | A proof or angle chase with one bad justification — the wrong theorem, an assumption read off the diagram, a congruence criterion the marks do not support. |

## What goes in which game

Tile Match and Sentence Fill always appear, so the decision is what each one
carries. Error Detection is added on top when the chapter earns it:
- **Theorem chapter** → Tile Match is theorem name ↔ fully marked diagram; Sentence Fill asks for the missing condition
- **Proof chapter** → Sentence Fill carries the proof as an ordered multi-blank passage; Tile Match carries mark ↔ meaning so the student can read the figure at all
- **Angle/measurement chapter** → Sentence Fill carries the angle chain as ordered blanks; Tile Match is angle type ↔ degree range
- **Review chapter covering several theorems** (§4, §7, §13, §17, §22, §24, §26) → give the Tile Match board one `concept_family` per theorem, so identifying which theorem a marked figure belongs to is the task
- **Procedure the chapter drills and students routinely mis-execute** → add Error Detection, and put its errors in the step the procedure actually turns on, not in the arithmetic around it

Never test the same item the same way in two different games. If a theorem is a Tile Match pair, Sentence Fill should require citing it in a step, not naming it again.

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

- Left tile = theorem name, angle type, congruence criterion, notation, or a property clue. Right tile = the labeled diagram.
- Every right tile must be a diagram using Visual Layer notation — no text-only pairs.
- Pair types:
  - Theorem name ↔ diagram: `"SAS belgisi"` ↔ `[Diagram: triangles ABC and DEF, one tick on AB=DE (blue), one tick on BC=EF (blue), single arc at ∠B=∠E (blue)]`
  - Angle type ↔ diagram: `"O'tmas burchak"` ↔ `[Diagram: rays BA and BC, wide arc inside showing angle > 90°, label "90° < α < 180°"]`
  - Notation ↔ diagram: `"AB ∥ CD"` ↔ `[Diagram: two horizontal lines with single arrows, gap between them, symbol ∥ labeled]`
  - Mark ↔ meaning: `[Diagram: single tick mark on segment]` ↔ `"Bu tomon boshqa bir tomon bilan teng"`
  - Property clue ↔ shape or theorem: `"Ikki tomoni teng, asos burchaklari teng"` ↔ `[Diagram: isosceles triangle with two ticks and two equal base arcs]`
- Difficulty ladder: `easy` name ↔ symbol → `medium` theorem ↔ fully marked diagram → `hard` criterion ↔ real-scenario diagram with partial marks, where the student must work out which criterion fits.
- **Include at least 1 pair whose diagram carries a deliberate wrong mark** so it does not match anything on the board — the student must identify it as a non-match. This builds error-detection instinct and is the strongest single rule in this file. Put the reason in that pair's `explanation`.
- Group the board with `concept_family` — one family per theorem or per figure type.
- Keep each side within 300 characters; a long Visual Layer description must be trimmed to its load-bearing marks.
- Every `left` and every `right` must be unique across the board.

### Sentence Fill
- Easy 5-6 items, Hard 7-8 items
- `mode`: `word_bank` for G7, `free_recall` for G8-9
- Proof step, theorem statement, or angle chain with one piece missing per `___`
- The gap must test geometric understanding — not random word removal
- Single-blank items:
  - `"∠ABC va ∠BCD — ___ burchaklar (AB ∥ CD bo'lganda)"` → answers `["almashma ichki"]`
  - `"△ABC = △DEF, chunki AB=DE, ∠B=∠E, BC=EF → ___ belgisi asosida"` → answers `["SAS"]`
  - `"Uchburchak ichki burchaklari yig'indisi ___ ga teng"` → answers `["180°"]`
- **Ordered proof passages carry the step-by-step work.** A proof or construction of 4-6 steps becomes ONE passage with 4-6 `___` markers, and `answers` must be in step order so the student reconstructs the argument in sequence — each blank only answerable once the previous one is settled. This is where the linear solve-stepper pedagogy now lives.
  - `"ABC — to'g'ri burchakli uchburchak, ∠C = ___°. Barcha burchaklar yig'indisi ___°. Demak ∠A + ∠B = ___°. ∠A = 30° bo'lsa, ∠B = ___°."` → answers `["90", "180", "90", "60"]`
- Every step that references a figure must include its Visual Layer diagram in the passage; the runtime renders inline SVG when present.
- In `word_bank` mode the distractor is the confusable criterion or the wrong angle relation (`"SSS"` against `"SAS"`, `"mos"` against `"almashma ichki"`), never a random word.
- Use `explanations` to name the theorem being applied at that blank — this is where "cite the theorem at every step" survives.

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

**Error categories — use these exact ids. This is the closed list for Geometry; do not invent one per item, and do not borrow another subject's list. The point is that the student learns the taxonomy:**

| id | what it means |
|---|---|
| `wrong_theorem` | A real theorem, correctly stated, that this figure does not support. |
| `unproven_assumption` | A step that assumes what the proof must establish, or reads a property straight off the picture. |
| `mislabelled` | A vertex, side or angle named inconsistently with the figure. |
| `angle_sum` | An angle total that does not hold for the figure in question. |
| `congruence_criterion` | The wrong congruence or similarity criterion for the marks given. |

- `artifact.kind`: `proof` for a reasoned chain, `worked_solution` for an angle chase.
- Put the error in the JUSTIFICATION, not in the arithmetic. "∠C = 180° - 50° - 60°"
  computed wrongly is an arithmetic slip; citing the wrong angle sum is geometry.
- Attach the figure to the segment it belongs to with `svg` when the step is only
  checkable against the diagram. Keep it under 200×150px.

**Worked example (Geometriya, G7):**

`artifact.kind`: `worked_solution`, `artifact.segments`:

1. `ABC uchburchakda ∠A = 50°, ∠B = 60°`
2. `Uchburchak burchaklari yig'indisi 360° ga teng`
3. `∠C = 360° - 50° - 60°`
4. `∠C = 250°`

→ `faulty_segment_ids: ["s2"]`, `category: "angle_sum"`,
`fix: "Uchburchak burchaklari yig'indisi 180° ga teng"`,
`explanation: "360° — bu to'rtburchak burchaklari yig'indisi. Uchburchak uchun 180° olinadi."`

Segments 3 and 4 are arithmetically perfect *given* the wrong theorem in segment 2.
That is the craft: the student cannot find it by checking the subtraction.

## Rules

- Every question involving a shape references a diagram, and every diagram is real SVG
- Every item tagged: `[Bloom: LX | PISA: LX]`
- Do not reference any game outside the Supported Games table
- Current chapter content only — no questions from other chapters
- Language: Uzbek, "Siz" formal
- Diagram labelling standard, applied to every diagram you author: label all vertices (A, B, C), all sides (AB, BC, CA) and all angles (∠A, ∠B, ∠C); mark equal sides with tick marks, equal angles with arc marks, right angles with a square corner; blue for given, orange for found or proved
- Name the theorem at the step where it is used — in the Sentence Fill `explanations` array, or in the Tile Match pair's `explanation`

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
