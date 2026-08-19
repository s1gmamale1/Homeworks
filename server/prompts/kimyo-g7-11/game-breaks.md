# Prompt: Game Breaks — Kimyo

You are building the Game Breaks (Phase 3) for a Kimyo homework session. This is where real practice starts. The student applies what they learned in Preview through gamified repetition.

## Input

- Textbook page (image or text)
- Preview + Flash Cards + Sprint outputs (from previous steps)
- Grade: G7-11 (Kimyo)
- Mode: Easy | Hard

## Output

Tile Match + Sentence Fill every session. Error Detection as well when the chapter has a canonical procedure students routinely mis-execute.

Mode changes the load, not the game count:
- **Easy** — Tile Match at its grade-banded board size, Sentence Fill 5-6 items, mostly 1-blank passages.
- **Hard** — Tile Match at its grade-banded board size, Sentence Fill 7-8 items, including at least one 4-6 blank equation-balancing or three-scale passage.

Every item tagged with `[Bloom: LX | PISA: LX]`.

> **Three-Scale Rule:** every substance appears at all three scales — macroscopic (what you observe), microscopic (particle arrangement), symbolic (formula and balanced equation). No item is anonymous symbols alone. **Observable Before Theory:** lead with the phenomenon, then the formula.

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

### What each game is for in Kimyo

| Game | Kimyo use |
|---|---|
| **Tile Match** | Macroscopic ↔ symbolic, microscopic ↔ symbolic, observable reaction ↔ equation, safety rule ↔ substance. The three-scale board. |
| **Sentence Fill** | Missing coefficient, missing product, missing safety step, missing scale in a three-scale chain. Carries equation balancing and ordered procedures. |
| **Error Detection** | A balancing or a procedure with one bad step — a subscript changed instead of a coefficient, an impossible product, a missing state symbol. |

## What goes in which game

Tile Match and Sentence Fill always appear, so the decision is what each one
carries. Error Detection is added on top when the chapter earns it:
- **New substance / property chapter** → Tile Match is the three-scale board; Sentence Fill checks the observable-to-symbolic reasoning step
- **Reaction / equation chapter** → Sentence Fill carries balancing as ordered coefficient blanks; Tile Match carries observable reaction ↔ balanced equation
- **Lab / procedure chapter** → Sentence Fill carries the procedure and the safety rule as ordered blanks; Tile Match carries safety rule ↔ substance
- **Calculation-heavy chapter** (molar mass, percent composition, stoichiometric ratios) → Sentence Fill carries the calculation as ordered blanks, one blank per step, with the unit in the answer
- **Procedure the chapter drills and students routinely mis-execute** → add Error Detection, and put its errors in the step the procedure actually turns on, not in the arithmetic around it

Never test the same item the same way in two different games. If a substance is a Tile Match pair, Sentence Fill should require reasoning with it, not renaming it.

---

## Construction per game

### Tile Match — the three-scale board
**Board size by grade** — the builder recommends by grade, and 8 is a hard cap:

| Grade | Pairs |
|---|---|
| G1-G2 | 4 |
| G3-G4 | 5 |
| G5-G7 | 6 |
| G8 and above | 8 |

Never author more than 8 pairs at any grade; a 9th pair is rejected.

- Left tile = one scale description. Right tile = the same substance at a different scale.
- Every tile must carry enough context to identify the substance — no anonymous symbol-only tiles.
- Pair types:
  - Macroscopic ↔ symbolic: `"Oq kristall kukun, hidsiz, suvda eriydi"` ↔ `"NaCl (Na: +1, Cl: -1)"`
  - Microscopic ↔ symbolic: `"Na⁺ va Cl⁻ ionlari kub panjarasida"` ↔ `"NaCl — ionli bog'"`
  - Observable reaction ↔ equation: `"Yorqin alanga, pufakchalar, issiqlik ajraladi"` ↔ `"C₃H₈ + 5O₂ → 3CO₂ + 4H₂O (muvozanatlangan)"`
  - Safety ↔ substance: `"Goggles + gloves + fume hood majburiy"` ↔ `"Konsentrlangan H₂SO₄ — kuydirgich kislota"`
- Difficulty ladder: `easy` name ↔ formula → `medium` observable ↔ formula → `hard` a pair that only resolves when macro AND micro descriptions are read together.
- **Include at least 1 pair whose equation is deliberately unbalanced** so it matches nothing on the board — the student must identify it as a non-match. This trains coefficient-versus-subscript discipline. Put the atom-count failure in that pair's `explanation`.
- Group the board with `concept_family` — one family per substance or per reaction type, so all three scales of one substance sit together.
- Keep each side within 300 characters.
- Every `left` and every `right` must be unique across the board.

### Sentence Fill
- Easy 5-6 items, Hard 7-8 items
- `mode`: `word_bank` for G7, `free_recall` for G8-11
- Causal chain statement, safety rule, three-scale description, or equation step with one piece missing per `___`
- The gap must test chemical understanding — not random word removal
- Single-blank and two-blank items:
  - `"Kislotani suyultirishda avvalo ___ olinadi, keyin ustiga ___ quyiladi"` → answers `["suv", "kislota"]` (kislota suvga, suvga kislota emas — safety rule)
  - `"2H₂ + O₂ → 2H₂O tenglamasida H atomlari: chap tomonda ___, o'ng tomonda ___"` → answers `["4", "4"]` (balance verification)
  - `"NaCl — makroskopik darajada oq kristall kukun; mikroskopik darajada ___ ionlari; ramziy darajada ___"` → answers `["Na⁺ va Cl⁻", "NaCl"]`
  - `"Reaksiya natijasida rang o'zgarishi ___ ko'rsatkichi bo'lishi mumkin"` → answers `["yangi modda hosil bo'lishi"]`
- **Equation balancing is a multi-blank passage.** Put a `___` where each coefficient belongs and require the atom-count check in the same passage, so the student balances and verifies in one ordered pass. This is where the tile-assembly balancing pedagogy now lives.
  - `"___H₂SO₄ + ___NaOH → ___Na₂SO₄ + ___H₂O. Tekshirish: Na×___ = Na×___"` → answers `["1", "2", "1", "2", "2", "2"]`
- **Ordered procedures are a multi-blank passage** with the blanks in execution order, safety always first:
  - `"Lab protokoli: 1) ___ kiyish, 2) reagentlarni ___, 3) tajriba o'tkazish, 4) kuzatuvlarni ___, 5) reaktivlarni ___"` → answers `["PPE", "tekshirish", "yozib olish", "utilizatsiya qilish"]`
- In `word_bank` mode the distractor is the coefficient-versus-subscript error or the reversed safety step, never a random token.
- Use `explanations` to state the atom-count check or the safety consequence for each blank.

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

**Error categories — use these exact ids. This is the closed list for Kimyo; do not invent one per item, and do not borrow another subject's list. The point is that the student learns the taxonomy:**

| id | what it means |
|---|---|
| `unbalanced` | Atom counts do not match on both sides of the equation. |
| `coefficient_vs_subscript` | A subscript was changed to balance the equation — that changes the substance itself. |
| `wrong_product` | A product this reaction type does not give. |
| `state_symbol` | A missing or wrong `(s)` / `(l)` / `(g)` / `(aq)`. |
| `safety` | A procedural step that is unsafe, or safe steps in an unsafe order. |

- `artifact.kind`: `equation` for balancing, `procedure` for lab work.
- `coefficient_vs_subscript` is the highest-value item in chemistry: the student
  who balances by editing subscripts gets a balanced equation for a different
  substance, and nothing downstream complains.
- For `safety`, the classic is adding water to concentrated acid rather than acid
  to water. Author the wrong order confidently, without hedging.

**Worked example (Kimyo, G8):**

`artifact.kind`: `equation`, `artifact.segments`:

1. `Tenglashtirish kerak: H₂ + O₂ → H₂O`
2. `Kislorodni tenglashtiramiz: H₂ + O₂ → H₂O₂`
3. `Vodorodni tekshiramiz: chapda 2 ta, o'ngda 2 ta`
4. `Tenglama tenglashtirildi`

→ `faulty_segment_ids: ["s2"]`, `category: "coefficient_vs_subscript"`,
`fix: "2H₂ + O₂ → 2H₂O"`,
`explanation: "Indeksni o'zgartirish moddani almashtiradi — H₂O₂ bu vodorod peroksid, suv emas. Tenglashtirishda faqat koeffitsiyent qo'yiladi."`

Segments 3 and 4 are true *about H₂O₂*: the atom counts really do balance. The
student can only find the error by knowing that editing a subscript is illegal.

## Rules

- Every item involving a substance carries a three-scale description or an observable diagram
- Every balanced equation includes its atom count verification — `X×N = X×N ✓` — inside the passage or the explanation
- Safety note mandatory in every item involving a hazardous substance — no chemistry content without safety context
- Observable Before Theory — never open an item with a bare formula
- Every item tagged: `[Bloom: LX | PISA: LX]`
- Do not reference any game outside the Supported Games table
- Current chapter content only — no questions from other chapters
- Language: Uzbek, "Siz" formal

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
- `tile_match.subject_family` is always `"chemistry"` in this file.
- `error_detection.artifact.segments` must be non-empty; every segment `id` must be unique within its item, and every `text` non-empty and 500 characters or fewer.
- `error_detection.stages` must be a non-empty subset of `["mark", "classify", "correct"]` and must contain `"mark"`.
- Every id in `error_detection.faulty_segment_ids` must exist in that item's `artifact.segments`. An answer key pointing at a segment that does not exist is rejected — it is the bug most worth catching.
- `faulty_segment_ids: []` is **legal and required once per set** — it is the clean artifact, answered correctly by marking nothing. It is not an authoring mistake and it will not be validated away.
- When `"classify"` is in `stages`, `categories` must be non-empty and `category` must be one of those ids (or `null`, but only when the artifact is clean).
- `faulty_segment_ids`, `category`, `fix` and `explanation` are **server-only** — they are stripped before the item reaches the student's browser. Author them anyway: grading and post-attempt feedback depend on them.
