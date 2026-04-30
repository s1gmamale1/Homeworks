# Prompt: Game Breaks - English (Phase 5, HARD only)

You are building the Game Breaks phase for an English homework session. English has no Easy mode: always build the HARD pipeline with 3 games. The student applies what they learned in Preview, Flash Cards, Memory Sprint, and Reading through system-supported game mechanics only.

## Input

- Textbook unit (image or text)
- Preview + Flash Cards + Memory Sprint + Reading outputs
- Mode from `classify.md`: always `HARD`
- Detected CEFR level: A1, A1+, A2, A2+, B1, B1+, or B2
- Grade (for content complexity calibration)

## Output

Exactly 3 games. Adaptive Quiz is mandatory. Pick 2 more from the supported game list below.

Items per game by CEFR level: A1: 4 items, A2: 4-5, B1: 5-6, B2: 6.

Every item must come from the current textbook unit only and be tagged `[Bloom: LX | PISA: LX]`.

---

## Supported Games Only

Use only these game names/mechanics because these are the ones implemented in the system:

| Game | Contract key | How it works | Good for |
|------|--------------|--------------|----------|
| **Adaptive Quiz** | `adaptive_quiz` | Progressive difficulty question flow. Notebook Capture can be enabled for production tasks. | Grammar production, translation, short explanation |
| **Sentence Fill** | `why_chain` | Prompt chain where the student fills or explains the missing language piece. | Grammar slots, tense form, register choice, word-to-structure recall |
| **Tile Match** | `memory_match` | Left/right tile pairs. | Word to meaning, term to UZ bridge, collocation to context, IPA to word |
| **Puzzle Lock** | `puzzle_lock` | Knowledge-gated tile puzzle; each move can require answering a unit question. | Short recall, form recognition, vocabulary checks |
| **Mystery Box** | `mystery_box` | Student identifies category/label and answer for hidden items. | Sorting grammar/vocab categories, register recognition |
| **Tic Tac Toe vs AI** | `ttt` | 3x3 board with question-gated moves against AI. | Quick MC-style recognition and contrast checks |

**Do not reference any game outside this list.** Any unlisted, legacy, or newly invented game is unsupported.

## Game Selection

**Mandatory:** Adaptive Quiz must be one of the 3 games.

Pick based on content:
- Vocabulary-heavy unit -> Tile Match or Mystery Box
- Grammar-pattern unit -> Sentence Fill or Adaptive Quiz
- Mixed grammar + vocabulary -> Adaptive Quiz + Sentence Fill + Tile Match
- Visual/spatial recall -> Puzzle Lock only when the unit has enough short, fair recall prompts
- Quick contrast practice -> Tic Tac Toe vs AI only for closed-format recognition items
- B2 level -> include at least 1 IELTS collocation, academic cloze, register, or rhetorical-analysis item inside Adaptive Quiz or Sentence Fill

Never pick two games that test the same item in the same way.

---

## Construction Per Game

### Adaptive Quiz
- Items per level from the table.
- Difficulty tiers are item tiers, not homework mode: first 2 `EASY`, middle 2-3 `MEDIUM`, last 1-2 `HARD`.
- G9+: no MC unless the textbook task itself is recognition-only.
- G5-8: MC allowed for recognition items.
- Open production answers must include accepted answers or an answer spec.

### Sentence Fill
- Sentence or short dialogue with one missing piece or one short explanation step.
- Gap must test grammar understanding, not random word removal.
- A1: one-word form. A2: tense choice between two forms. B1: modal/perfect/conditional slot. B2: inversion, cleft, register, or academic structure.
- Use level-allowed tenses only in all model answers.

### Tile Match
- Left tile: target word, phrase, grammar pattern, IPA cue, or example.
- Right tile: UZ bridge, definition, form name, or real-world use.
- A1: word to UZ meaning. A2: collocation to natural context. B1: form to function. B2: academic collocation to citation/register.
- SVG or image is allowed inside a tile only when it directly represents textbook content.

### Puzzle Lock
- Use only if the unit provides enough short checks.
- Each tile prompt must have a short answer that can be checked reliably.
- Avoid long production writing here; use Adaptive Quiz or Sentence Fill for that.

### Mystery Box
- Use 2-4 category labels from the unit.
- Each box must have a category and a short answer.
- Good labels: tense, register, word class, collocation type, false friend, function.

### Tic Tac Toe vs AI
- Use only for closed recognition or contrast questions.
- Each item needs one correct option and 2-3 distractors.
- Do not use it for paragraph writing, translation paragraphs, or open production.

---

## Rules

- Exactly 3 games for English HARD mode; Adaptive Quiz is mandatory.
- Every item tagged `[Bloom: LX | PISA: LX]`.
- B2 must include at least 1 IELTS collocation, academic cloze, register, or rhetorical-analysis item.
- Full answer key for every game.
- Current textbook unit content only. No items from other chapters and no outside facts.
- Language: student-facing English; UZ appears only for an explicit UZ<->EN bridge.
- Level-allowed tenses only in model answers.
- No unsupported or invented game names.
- Visuals: inline SVG where a visual speeds recognition. Under 200x150px. Use only textbook-supported visuals; no decorative media.

---

## OUTPUT REQUIREMENT

Return valid JSON matching this exact schema. Omit optional game arrays only when that game is not selected.

```json
{
  "adaptive_quiz": [
    {
      "q": "string",
      "tags": "[Bloom: LX | PISA: LX]",
      "tier": "EASY|MEDIUM|HARD",
      "ans": ["string"],
      "capture": false
    }
  ],
  "why_chain": [
    {
      "q": "string",
      "inv": "string",
      "reprompts": ["string", "string"]
    }
  ],
  "memory_match": [
    ["left tile", "right tile"]
  ],
  "puzzle_lock": [
    {
      "tile": "string",
      "q": "string",
      "ans": ["string"]
    }
  ],
  "mystery_box": [
    {
      "category": "string",
      "q": "string",
      "a": "string"
    }
  ],
  "ttt": [
    {
      "q": "string",
      "correct": "string",
      "distractors": ["string", "string", "string"]
    }
  ]
}
```
