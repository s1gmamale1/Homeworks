# Prompt: Game Breaks - English (Phase 5, HARD only)

You are building the Game Breaks phase for an English homework session. English has no Easy mode: always build the HARD pipeline. The student applies what they learned in Preview, Flash Cards, Memory Sprint, and Reading through system-supported game mechanics only.

## Input

- Textbook unit (image or text)
- Preview + Flash Cards + Memory Sprint + Reading outputs
- Mode from `classify.md`: always `HARD`
- Detected CEFR level: A1, A1+, A2, A2+, B1, B1+, or B2
- Grade (for content complexity calibration)

## Output

Exactly 2 games — Tile Match and Sentence Fill. Both, every session.

Sentence Fill items by CEFR level: A1: 5, A2: 5-6, B1: 6-7, B2: 8. These counts are higher than the old per-game figures because the phase now carries its whole load across two always-on games instead of three.

Tile Match is the exception — its board size is set by grade, not by CEFR (see the table under Tile Match). It is hard-capped, so it cannot absorb extra items; anything extra goes to Sentence Fill.

Every item must come from the current textbook unit only and be tagged `[Bloom: LX | PISA: LX]`.

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

### What each game is for in English

| Game | English use |
|---|---|
| **Tile Match** | Word ↔ meaning, term ↔ UZ bridge, collocation ↔ context, IPA ↔ word, form ↔ function. |
| **Sentence Fill** | Grammar slots, tense form, register choice, collocation completion, academic cloze. Also carries short recall, form recognition, and the closed-format contrast checks that used to sit in a quiz. |
| **Error Detection** | A confident but wrong sentence or short paragraph the student proofreads: tense, agreement, article, word order, register, collocation. |

## What goes in which game

Tile Match and Sentence Fill always appear, so the decision is what each one
carries. Error Detection is added on top when the chapter earns it:
- Vocabulary-heavy unit → the weight goes on Tile Match; Sentence Fill puts those words back into use in context
- Grammar-pattern unit → the weight goes on Sentence Fill; Tile Match carries form ↔ function pairs
- Mixed grammar + vocabulary → split evenly, with the Tile Match board grouped into 2-4 `concept_family` labels
- Contrast practice (the closed recognition drills that used to be a separate game) → `word_bank` Sentence Fill items where the single distractor IS the contrast form
- Short recall and form recognition → 1-blank Sentence Fill items with a short, reliably checkable answer; keep long production out of them
- B2 level → at least 1 IELTS collocation, academic cloze, register, or rhetorical-analysis item, in either game
- **Procedure the chapter drills and students routinely mis-execute** → add Error Detection, and put its errors in the step the procedure actually turns on, not in the arithmetic around it

Never test the same item the same way in two different games. If a word is a Tile Match pair, Sentence Fill should require it in production, not re-ask its meaning.

---

## Construction Per Game

### Tile Match
- Left tile: target word, phrase, grammar pattern, IPA cue, or example.
- Right tile: UZ bridge, definition, form name, or real-world use.
- A1: word ↔ UZ meaning. A2: collocation ↔ natural context. B1: form ↔ function. B2: academic collocation ↔ citation/register.
- Set `concept_family` from the unit's own categories — `tense`, `register`, `word class`, `collocation type`, `false friend`, `function` are the labels that group an English board cleanly. Use 2-4 families per board.
- Difficulty ladder across the board: `easy` word ↔ meaning → `medium` collocation ↔ context → `hard` form ↔ function, where the pair only resolves if the student reads the grammatical role.
- SVG or an image is allowed inside a tile only when it directly represents textbook content.
- Every `left` and every `right` must be unique across the board.
**Board size by grade** — the builder recommends by grade, and 8 is a hard cap:

| Grade | Pairs |
|---|---|
| G1-G2 | 4 |
| G3-G4 | 5 |
| G5-G7 | 6 |
| G8 and above | 8 |

Never author more than 8 pairs at any grade; a 9th pair is rejected.

### Sentence Fill
- Items per CEFR level from the table above.
- `mode`: `word_bank` for G2-G7, `free_recall` for G8+.
- Sentence or short dialogue with one missing piece per `___`; 1-3 blanks per passage is the natural English range.
- The gap must test grammar understanding, not random word removal.
- A1: one-word form. A2: tense choice between two forms. B1: modal/perfect/conditional slot. B2: inversion, cleft, register, or academic structure.
- Use level-allowed tenses only in all model answers.
- In `word_bank` mode the distractor is the contrast form the level is actually being taught (`"has gone"` against `"went"`, `"few"` against `"a few"`), never a random word. This is where closed-format contrast practice now lives.
- B2 academic cloze lives here: an authentic collocation slot inside a source-like sentence.
- Use `explanations` to say why the distractor is wrong at this CEFR level — one per answer, or omit the key entirely.

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

**Error categories — use these exact ids. This is the closed list for English; do not invent one per item, and do not borrow another subject's list. The point is that the student learns the taxonomy:**

| id | what it means |
|---|---|
| `tense` | The wrong tense for the time reference in the sentence. |
| `agreement` | Subject-verb or noun-determiner disagreement. |
| `article` | A missing, extra, or wrong article. |
| `word_order` | Constituents in an order English does not allow. |
| `register` | Formality that does not match the task or audience. |
| `collocation` | Grammatical, but not the pairing a native speaker uses. |

- `artifact.kind`: `sentence`. Segment by clause, not by word — one clause per
  segment is the unit an error lives in.
- Author the error a real learner of this level makes. An L1-Uzbek learner drops
  articles and over-uses the present simple; those are worth drilling. A random
  typo is not.
- The rest of the paragraph must stay grammatical. If two clauses are broken the
  student cannot tell which one you meant.

**Worked example (English, G9):**

`artifact.kind`: `sentence`, `artifact.segments`:

1. `Yesterday I go to the library`
2. `and borrowed three books about the history of Samarkand,`
3. `because I had an essay to finish before Monday.`

→ `faulty_segment_ids: ["s1"]`, `category: "tense"`,
`fix: "Yesterday I went to the library"`,
`explanation: "'Yesterday' fixes the sentence in past time, so the verb must be past simple."`

Segments 2 and 3 are already past tense and stay correct. Only segment 1 breaks,
and it breaks against a time marker the student can point to.

## Rules

- Exactly 2 games for English HARD mode — Tile Match and Sentence Fill, both every session.
- Every item tagged `[Bloom: LX | PISA: LX]`.
- B2 must include at least 1 IELTS collocation, academic cloze, register, or rhetorical-analysis item.
- Full answer key for every game.
- Current textbook unit content only. No items from other chapters and no outside facts.
- Language: student-facing English; UZ appears only for an explicit UZ<->EN bridge.
- Level-allowed tenses only in model answers.
- Do not reference any game outside the Supported Games table.
- Visuals: inline SVG where a visual speeds recognition. Under 200x150px. Use only textbook-supported visuals; no decorative media.

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
- `tile_match.subject_family` is always `"language"` in this file.
- `error_detection.artifact.segments` must be non-empty; every segment `id` must be unique within its item, and every `text` non-empty and 500 characters or fewer.
- `error_detection.stages` must be a non-empty subset of `["mark", "classify", "correct"]` and must contain `"mark"`.
- Every id in `error_detection.faulty_segment_ids` must exist in that item's `artifact.segments`. An answer key pointing at a segment that does not exist is rejected — it is the bug most worth catching.
- `faulty_segment_ids: []` is **legal and required once per set** — it is the clean artifact, answered correctly by marking nothing. It is not an authoring mistake and it will not be validated away.
- When `"classify"` is in `stages`, `categories` must be non-empty and `category` must be one of those ids (or `null`, but only when the artifact is clean).
- `faulty_segment_ids`, `category`, `fix` and `explanation` are **server-only** — they are stripped before the item reaches the student's browser. Author them anyway: grading and post-attempt feedback depend on them.
