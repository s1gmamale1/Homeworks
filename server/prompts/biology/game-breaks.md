# Prompt: Game Breaks — Biology (Biologiya G5-11)

You are building the Game Breaks (Phase 3) for a Biology homework session. Real practice starts here — the student applies what they learned through gamified repetition.

## Input

- Textbook page + all previous phase outputs
- Grade: G5-11 (Biologiya)
- Mode: Easy | Hard

## Output

Tile Match + Sentence Fill every session. Error Detection as well when the chapter has a canonical procedure students routinely mis-execute.

Mode changes the load, not the game count:
- **Easy** — Tile Match at its grade-banded board size, Sentence Fill 5-6 items, mostly 1-blank passages.
- **Hard** — Tile Match at its grade-banded board size, Sentence Fill 7-8 items, with 2-3 blank passages carrying the multi-step processes.

Every item tagged with `[Bloom: LX | PISA: LX]`. Bloom levels must span L1 (recall) → L3 (application) across the whole phase.

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

### What each game is for in Biology

| Game | Biology use |
|---|---|
| **Tile Match** | Structure ↔ function, organism ↔ classification, process ↔ result, cause ↔ effect, term ↔ diagram description. |
| **Sentence Fill** | Process descriptions with a missing step, reactant, product, or organism. Also carries the identification and structure-function recall that used to sit in a quiz. |
| **Error Detection** | A process description with one bad claim — the wrong organelle, stages out of order, a cause and its effect swapped. |

## What goes in which game

Tile Match and Sentence Fill always appear, so the decision is what each one
carries. Error Detection is added on top when the chapter earns it:

- **Taxonomy/classification chapter** → the Tile Match board is organism ↔ kingdom/phylum; Sentence Fill checks the defining trait of each group
- **Process chapter** (photosynthesis, digestion, mitosis, respiration) → Sentence Fill carries the process as multi-blank passages; Tile Match carries process ↔ result
- **Structure chapter** (cell organelles, organ systems, tissue types) → Tile Match is structure ↔ function; Sentence Fill checks where each structure sits in the larger system
- **Mixed chapter** → split the Tile Match board into two `concept_family` groups and let Sentence Fill cover the process arc
- **Procedure the chapter drills and students routinely mis-execute** → add Error Detection, and put its errors in the step the procedure actually turns on, not in the arithmetic around it

Never test the same item the same way in two different games. If a term is a Tile Match pair, Sentence Fill should ask what it *does*, not what it *is*.

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

- Biology pair types:
  - Structure ↔ function: `"Mitoxondriya"` ↔ `"ATP ishlab chiqaradi"`
  - Organism ↔ classification: `"Amyoba"` ↔ `"Sarcodina tipi"`
  - Process ↔ result: `"Fotosintez"` ↔ `"O₂ va glukoza hosil bo'ladi"`
  - Cause ↔ effect: `"Xlorofill quyosh nurini yutadi"` ↔ `"Fotosintez boshlanadi"`
  - Term ↔ diagram description: `"Yadro"` ↔ `"Dumaloq, membranali, DNAni saqlaydi"`
- Group pairs that belong to one misconception family under a shared `concept_family` (e.g. `"hujayra organoidlari"`, `"to'qima turlari"`) so the board reads as a branch, not a list
- Difficulty ladder across the board: `easy` name ↔ definition → `medium` structure ↔ function → `hard` organism ↔ classification edge case, where the pair only resolves if the student knows the defining trait
- If a structure needs a diagram to be recognisable, put a small inline SVG (under 200×150px) on that side of the pair
- Every `left` and every `right` must be unique across the board

### Sentence Fill
- Easy 5-6 items, Hard 7-8 items
- `mode`: `word_bank` for G5-G7, `free_recall` for G8-11
- Each `passage` carries 1-3 `___` markers; a process with three linked steps is a good 3-blank passage
- The gap must test biological understanding, not random word removal
- G5-7 stay at recognition and single-step recall; G8-11 carry the process-reasoning and classification-edge-case load that the harder items used to hold, as multi-blank passages the student must reason through in order
- Biology-specific gaps:
  - `"Fotosintez jarayonida o'simlik ___ ni yutadi va ___ ajratadi"` → answers `["CO₂", "O₂"]`
  - `"Mitoz natijasida ___ ta qiz hujayra hosil bo'ladi"` → answers `["2"]`
  - `"Xloroplastdagi yashil pigment ___ deb ataladi"` → answers `["xlorofill"]`
  - `"Odam teri epiteliysi ___ to'qima turiga kiradi"` → answers `["epiteliy"]`
  - `"Zamburug'lar ___ yo'l bilan oziqlanadi"` → answers `["heterotrof"]`
- In `word_bank` mode the bank must hold every answer plus at least one distractor, and the distractor should be the misconception partner (`"O₂"` against `"CO₂"`, `"meyoz"` against `"mitoz"`), never a random word
- Use `explanations` to name the misconception the distractor represents — this is where the "why the other one is wrong" teaching lives

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

**Error categories — use these exact ids. This is the closed list for Biology; do not invent one per item, and do not borrow another subject's list. The point is that the student learns the taxonomy:**

| id | what it means |
|---|---|
| `wrong_structure` | The named structure does not perform the stated function. |
| `wrong_process_order` | The stages are the right ones, in the wrong sequence. |
| `classification` | An organism or structure placed in the wrong group. |
| `cause_effect_reversed` | The consequence is stated as the cause. |

- `artifact.kind`: `procedure` for a staged process, `sentence` for a claim chain.
- The richest items are process chains — photosynthesis, respiration, digestion,
  mitosis — where one stage is attributed to the wrong structure and everything
  after it follows consistently from that wrong structure.
- Do not make the error a vocabulary slip. The student should have to know what
  the organelle *does*, not how the word is spelled.

**Worked example (Biologiya, G7):**

`artifact.kind`: `procedure`, `artifact.segments`:

1. `Fotosintez xloroplastda sodir bo'ladi`
2. `Yorug'lik energiyasi mitoxondriyada yutiladi`
3. `U yerda yorug'lik energiyasi kimyoviy energiyaga aylanadi`
4. `Hosil bo'lgan energiya glyukoza sintezi uchun ishlatiladi`

→ `faulty_segment_ids: ["s2"]`, `category: "wrong_structure"`,
`fix: "Yorug'lik energiyasi xloroplastda yutiladi"`,
`explanation: "Mitoxondriya nafas olish organoidi — u yorug'lik energiyasini yutmaydi."`

Segments 3 and 4 are internally consistent with the error: they follow correctly
from "energy absorbed in the mitochondrion". The student cannot find the mistake
by spotting a broken chain, only by knowing which organelle absorbs light.

## Rules

- Every item tagged: `[Bloom: LX | PISA: LX]`
- Biology has no calculations, so nothing in this phase asks the student to photograph written work
- Do not reference any game outside the Supported Games table
- Current chapter content only
- Language: Uzbek, "Siz" formal
- Visuals: if a game item references a structure or organism that students identify visually (cell organelle, leaf cross-section, organism diagram), generate an inline SVG. Keep simple — under 200×150px.

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
- `tile_match.subject_family` is always `"biology"` in this file.
- `error_detection.artifact.segments` must be non-empty; every segment `id` must be unique within its item, and every `text` non-empty and 500 characters or fewer.
- `error_detection.stages` must be a non-empty subset of `["mark", "classify", "correct"]` and must contain `"mark"`.
- Every id in `error_detection.faulty_segment_ids` must exist in that item's `artifact.segments`. An answer key pointing at a segment that does not exist is rejected — it is the bug most worth catching.
- `faulty_segment_ids: []` is **legal and required once per set** — it is the clean artifact, answered correctly by marking nothing. It is not an authoring mistake and it will not be validated away.
- When `"classify"` is in `stages`, `categories` must be non-empty and `category` must be one of those ids (or `null`, but only when the artifact is clean).
- `faulty_segment_ids`, `category`, `fix` and `explanation` are **server-only** — they are stripped before the item reaches the student's browser. Author them anyway: grading and post-attempt feedback depend on them.
