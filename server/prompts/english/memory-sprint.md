# Prompt: Memory Sprint — English (Phase 1)

You are building the Memory Sprint (Phase 1) for an English homework session. Quick warm-up — tap-only, under 2 minutes. The student just finished Preview and Flash Cards. Now you check that the flashcards stuck and the unit's theme is anchored, with fast recognition questions.

This is NOT new practice. No writing, no production, no multi-step analysis. Just: do you recognize the items the student just saw in the flashcards, or facts/rules tied to this unit's theme?

## Input

- Textbook unit (image or text)
- Detected CEFR level (from `classify.md`): A1 · A1+ · A2 · A2+ · B1 · B1+ · B2
- The flashcards generated for this same unit (see `flashcards.md` output) — primary source for item content
- The unit's theme (grammar focus + vocabulary cluster) — fallback source when a flashcard angle doesn't fit a chosen format

## Output

Item count and format by CEFR level. Must use at least 2 different formats.

| Level | Item count | Format distribution |
|:-:|:-:|---|
| A1 / A1+ | 3 | 2 MC + 1 T/F |
| A2 / A2+ | 4-5 | 2 MC + 1 T/F + 1 YNNG |
| B1 / B1+ | 5-6 | 3 MC + 1 T/F + 1 YNNG |
| B2 | 7 | 3 MC + 2 T/F + 2 YNNG |

When a row gives a range (4-5, 5-6), the upper bound adds **one extra MC item**. Default to the lower bound; only output the +1 if the unit content yields enough distinct, non-overlapping recognition angles.

---

## 3 Formats (ONLY these — nothing else)

### Multiple Choice (MC4)
- Question + 4 options. 1 correct, 3 wrong.
- Each wrong option must reflect a real student mistake — not random:
  - Wrong tense (simple when perfect needed)
  - False friend confusion (magazine vs shop)
  - Mis-stress leading to mis-spelling
  - Partial answer (recognised form but wrong slot)

Example:
> Which sentence uses the past simple correctly?
> A) She has went to school.  B) **She went to school.** ✓  C) She go to school.  D) She goed to school.
> (A = present perfect mistake · C = no conjugation · D = regular-rule over-application)

### To'g'ri / Noto'g'ri (T/F)
- Statement about a grammar rule or vocabulary fact tied to the flashcards or this unit's theme.
- Must test a RULE or common MISCONCEPTION — not trivial recall.
- BAD: "'Went' is past tense of 'go' — To'g'ri yoki Noto'g'ri?" (trivial)
- GOOD: "In the past simple, we use 'did' for questions with all verbs including 'be' — To'g'ri yoki Noto'g'ri?"

Question stem stays in English; the "To'g'ri yoki Noto'g'ri?" cue is required so the student knows which Uzbek button (To'g'ri / Noto'g'ri) to tap.

### Ha / Yo'q / Ma'lum emas (YNNG)
- Statement about what this unit's reading, theme, or flashcards state or imply.
- Student taps Ha / Yo'q / Ma'lum emas.
- "Ma'lum emas" = this unit's content does not address this claim.
- Include at least 1 item with "Ma'lum emas" as the correct answer when YNNG is used.
- Question stem stays in English; the "Ha / Yo'q / Ma'lum emas?" cue at the end is required so the student knows which Uzbek button to tap.

Example:
> "According to this unit, a receptionist always answers calls in formal English — Ha / Yo'q / Ma'lum emas?"
> Correct: Ma'lum emas. (The unit describes the role but never specifies register rules.)

---

## Hint (gated, on-demand)

Each item must include a `hint` field. The hint is gated — the student requests it when stuck, then sees a one-line nudge. The hint must never expose the answer.

**Hint rules (hard constraints):**
- Hint must NEVER expose the answer or any inflected form of it.
- Hint must NOT name the correct option (for MC), the correct verdict (for T/F or YNNG), or paraphrase the answer in a way that gives it away.
- Hint must be a clue, contrast cue, or location pointer — not a teaching paragraph.
- Length: ≤2 sentences.
- If a student needs deeper help after the hint, end the hint with: `Need more? Ask the AI tutor.` — but only when the concept is genuinely complex; do not pad simple items with this line.
- If no honest non-spoiler hint exists for an item, omit the `hint` field entirely.

**BAD / GOOD per format:**

MC4
- BAD: "Hint: The answer is past simple." (exposes — names the rule that is the answer)
- GOOD: "Hint: Look for the time marker — does the action complete in the past?"

T/F
- BAD: "Hint: This is true." (exposes the verdict)
- GOOD: "Hint: 'Did' already carries the past — does the main verb still need to change?"

YNNG
- BAD: "Hint: Yes." (exposes)
- GOOD: "Hint: Re-read the part of the unit about register — does it specifically state this?"

The student answers the item exactly once. The hint does not unlock a second attempt — it only helps the student think before they tap.

---

## Rules

- **Tap only.** No typing, no drag-and-drop, no fill-in-blank, no open-ended.
- **2 minutes max.** Every item answerable in ≤25 seconds.
- **Flashcard- or theme-relevant only.** Every item must connect to one of the flashcards generated for this unit OR to the unit's grammar/vocabulary theme. No off-topic content, no pop-culture trivia, no facts the student hasn't seen here.
- **At least 1 item per Sprint must directly mirror a flashcard** (test the same word/rule/collocation the flashcard introduced).
- **Hints are gated, not absent.** See the "Hint (button-revealed)" section above. Every item must carry a `hint` that guides without exposing the answer.
- **No production.** If solving requires writing a sentence, it doesn't belong here.
- **Wrong-answer feedback (`explain` field):** one line explaining WHY the correct answer is correct + UZ bridge. Do not just restate the answer; teach the rule.
  - BAD: "The answer is 'She went'."
  - GOOD: "Past simple negative uses 'didn't + base verb' — the base form follows didn't because didn't already carries the past tense."
- Language: student-facing English. UZ bridge in feedback uses formal "Siz".
- Put the most important flashcard or theme concept as item 1 — primacy effect.
- Tags: each item `[Bloom: L1-L2 | PISA: L1]` — Sprint is recognition only, never L3+.
- **Visuals (`media`):** Use inline SVG only when a visual genuinely speeds recognition. The visual must depict the specific concept the item is testing — stress-dot pattern for a stress trap, sentence-diagram tree for a grammar slot, IPA glyph for a pronunciation distractor. **No decorative, generic, stock-like, or out-of-topic media.** Under 200×150px. Omit `media` entirely when no honest concept-related visual exists.
  - BAD: a generic apple icon SVG on a stress-pattern question for "photographer".
  - GOOD: an SVG of 4 syllable beats (oOoo) with the second beat boxed, paired to the stress-pattern question.


---

## OUTPUT REQUIREMENT
Return valid JSON matching this exact schema:
```json
[
  {
    "type": "KO|TF|YNNG",
    "prompt": "string",
    "subtitle": "",
    "tags": "[Bloom: LX | PISA: LX]",
    "explain": "string",
    "hint": "string",
    "options": ["string", "string"],
    "correct": 0
  }
]
```
