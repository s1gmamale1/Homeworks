# Prompt: Game Breaks — History (O'zbekiston Tarixi + Jahon Tarixi)

You are building the Game Breaks (Phase 3) for a History homework session. This is where real practice happens. The student has just warmed up with Memory Sprint; now they apply what was learned in Preview through the 2 sequenced games.

Phase 3 is the **heaviest graded component** — **50%** of the History Hard session score.

## Input

- Textbook lesson content (extracted in orchestrator Step 1)
- Preview output + Flash Cards output + Sprint output
- Grade: G5–G11
- Subject: `O'zbekiston Tarixi` or `Jahon Tarixi`

## Output

**2 games in sequence:** Game 1 Tile Match (⭐ Von Restorff Anchor) → Game 2 Sentence Fill.

**~14–16 items total:** 6–8 tile pairs + 7–8 cloze passages. This is down from the old ~20 because the third game no longer exists. Do not pad to reach 20 and do not invent a game to hold the difference.

**Difficulty distribution across all items:** ~40% Easy / ~40% Medium / ~20% Hard (tolerance ±5%).

Every item carries an inline tag: `[Bloom: LX | PISA: Reading/Creative Thinking LX | Skill: ... | Standard: UZ-TARIX-G-TOPIC-G##-##]`.

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

### What each game is for in History

| Game | History use |
|---|---|
| **Tile Match** | cause ↔ effect, date ↔ event, figure ↔ achievement, figure ↔ role, place ↔ event. |
| **Sentence Fill** | historical term gaps, source-quote fills, contextual retrieval of lesson vocabulary. |
| **Error Detection** | A confident but wrong account the student audits — an anachronism, the wrong actor, a reversed cause and effect, a date that breaks the chronology. |

## Game sequence

- **Game 1 — Tile Match (⭐ Von Restorff Anchor).** Cause ↔ effect or figure ↔ achievement pairings that span the lesson's full arc. This is now where the anchor lives.
- **Game 2 — Sentence Fill.** Contextual retrieval of lesson terms or source quotes.
- **Game 3 — Error Detection (conditional).** Only when the chapter carries a narrative students routinely get wrong — an anachronism, a misattributed actor, a reversed cause and effect. Omit the key entirely when it does not.

Modalities: Verbal/Logical (Tile) → Verbal/Logical (Sentence). With one game gone, the visual/spatial modality is no longer separately available; recover it inside Tile Match by writing at least two pairs whose right side is a concrete visual description (a map boundary, a monument, a battle formation) rather than an abstract phrase.

---

## Construction per game

### Game 1 — Tile Match (Von Restorff Anchor)
**Board size by grade** — the builder recommends by grade, and 8 is a hard cap:

| Grade | Pairs |
|---|---|
| G1-G2 | 4 |
| G3-G4 | 5 |
| G5-G7 | 6 |
| G8 and above | 8 |

Never author more than 8 pairs at any grade; a 9th pair is rejected.

- 6–8 pairs; at G5–G7 the band gives 6, at G8+ it gives 8. 8 is a hard cap.
- Left column: causes / dates / figures.
- Right column: effects / events / achievements.
- Preferred pair type for History: **cause ↔ effect** — it matches the family goal of causal reasoning over date memorization.
- Pairs should **trace the lesson's full causal arc** from opening event to closing consequence.
- **⭐ Von Restorff requirement:** exactly one pair carries an **outstanding fact** — unexpected scale, surprising consequence, vivid detail. Tag it `⭐ Von Restorff` in that pair's `explanation` field. This pair is the cognitive anchor students remember most, and it is the `hard` item on the board. Never mark it `easy` or `medium`.
- Group the board with `concept_family` — one family per strand of the lesson's causal arc.
- Difficulty mix within this game: ~3 Easy + ~3 Medium + 1 Hard (the anchor).
- Every `left` and every `right` must be unique across the board.

### Game 2 — Sentence Fill

- **7–8 items** (8 for a Hard session, 7 when the lesson is thin).
- `mode`: `word_bank` for G5–G7, `free_recall` for G8+.
- Show a sentence from the lesson (or paraphrased) with ONE word or short phrase missing per `___`. 1–3 blanks per passage; use a 3-blank passage to make the student reconstruct a sequence of events in order.
- The gap must test **historical understanding** — not random word removal.
- Two sub-types:
  - **Concept/term fill** — e.g. `"Bu maʼmuriy birliklar ___ deb nomlandi."` → answers `["tuman"]`
  - **Source-quote fill** — pulled from a primary source the lesson cites. E.g. `"Namoz ___ uchunmi yoki Tarmashirin uchunmi?"` → answers `["Xudo"]`
- **Include ≥1 source-quote fill** if the lesson contains a primary source (Panel 3 content).
- In `word_bank` mode the distractor is the plausible rival — the other date, the other figure, the other administrative term — never a random word.
- Use `explanations` to state what makes the distractor historically wrong.
- Difficulty mix: ~3 Easy + ~3 Medium + ~2 Hard.

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

**Error categories — use these exact ids. This is the closed list for History; do not invent one per item, and do not borrow another subject's list. The point is that the student learns the taxonomy:**

| id | what it means |
|---|---|
| `anachronism` | Something present in the account before it existed. |
| `wrong_actor` | The action attributed to the wrong person, state or group. |
| `cause_effect_reversed` | The consequence presented as the cause. |
| `date` | A date that contradicts the chronology the chapter establishes. |

- `artifact.kind`: `sentence` for a narrative paragraph, `procedure` for a
  sequence of events.
- `cause_effect_reversed` is the category worth the most here: it is the error
  that survives into adult reasoning, and spotting it is the actual history skill.
- Keep the surrounding sentences true. A paragraph with two errors reads as
  simply badly written and the student stops looking for the specific one.

**Worked example (O'zbekiston tarixi, G8):**

`artifact.kind`: `sentence`, `artifact.segments`:

1. `Amir Temur 1370-yilda hokimiyat tepasiga keldi`
2. `va Samarqandni o'z davlatining poytaxtiga aylantirdi.`
3. `Uning qo'shinlari miltiqlar bilan qurollangan edi,`
4. `shuning uchun ular ko'plab janglarda g'alaba qozondi.`

→ `faulty_segment_ids: ["s3"]`, `category: "anachronism"`,
`fix: "Uning qo'shinlari kamon va qilich bilan qurollangan edi,"`,
`explanation: "XIV asrda Movarounnahrda o'qotar qurol bo'lmagan — u ancha keyin tarqaldi."`

Segment 4 follows consistently from the false claim in segment 3, so the student
has to know the period's military technology rather than notice a broken sentence.

## Rules

- **Exactly 2 games** in the order Tile Match → Sentence Fill.
- **Every item tagged** with Bloom / PISA / Skill / Standard. Game-level defaults are acceptable; per-item overrides when difficulty differs.
- **Von Restorff anchor on the Tile Match board** — always. Tag the outstanding pair explicitly and give it `difficulty: "hard"`.
- **Textbook fidelity** — every pair and every sentence-fill from the source lesson.
- **Current chapter only** — no cross-chapter content.
- **No calculation in History** — nothing in this phase asks the student to photograph written work.
- **Do not reference any game outside the Supported Games table.**
- **Difficulty target:** 40/40/20 across all items in the 2 games (tolerance ±5%). Within any single game, do NOT load more than ~20% Hard items.
- **PISA tag MUST include L level.** Write `Reading L1`, `Reading L2`, `Creative Thinking L2`, etc. Never just `Reading` alone.
- **Language:** Uzbek, `Siz` when addressing student. Never `sen`.
- **Weight:** Phase 3 = 50% of session score (heaviest graded component).

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
- `tile_match.subject_family` is always `"history"` in this file.
- `error_detection.artifact.segments` must be non-empty; every segment `id` must be unique within its item, and every `text` non-empty and 500 characters or fewer.
- `error_detection.stages` must be a non-empty subset of `["mark", "classify", "correct"]` and must contain `"mark"`.
- Every id in `error_detection.faulty_segment_ids` must exist in that item's `artifact.segments`. An answer key pointing at a segment that does not exist is rejected — it is the bug most worth catching.
- `faulty_segment_ids: []` is **legal and required once per set** — it is the clean artifact, answered correctly by marking nothing. It is not an authoring mistake and it will not be validated away.
- When `"classify"` is in `stages`, `categories` must be non-empty and `category` must be one of those ids (or `null`, but only when the artifact is clean).
- `faulty_segment_ids`, `category`, `fix` and `explanation` are **server-only** — they are stripped before the item reaches the student's browser. Author them anyway: grading and post-attempt feedback depend on them.
