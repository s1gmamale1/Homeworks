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

### True / False (T/F)
- Statement about a grammar rule or vocabulary fact tied to the flashcards or this unit's theme.
- Must test a RULE or common MISCONCEPTION — not trivial recall.
- BAD: "'Went' is past tense of 'go' — True or False?" (trivial)
- GOOD: "In the past simple, we use 'did' for questions with all verbs including 'be' — True or False?"

### Yes / No / Not Given (YNNG)
- Statement about what this unit's reading, theme, or flashcards state or imply.
- Student taps Yes / No / Not Given.
- "Not Given" = this unit's content does not address this claim.
- Include at least 1 item with "Not Given" as the correct answer when YNNG is used.

Example:
> "According to this unit, a receptionist always answers calls in formal English — Yes / No / Not Given"
> Correct: Not Given. (The unit describes the role but never specifies register rules.)

---

## Rules

- **Tap only.** No typing, no drag-and-drop, no fill-in-blank, no open-ended.
- **2 minutes max.** Every item answerable in ≤25 seconds.
- **Flashcard- or theme-relevant only.** Every item must connect to one of the flashcards generated for this unit OR to the unit's grammar/vocabulary theme. No off-topic content, no pop-culture trivia, no facts the student hasn't seen here.
- **At least 1 item per Sprint must directly mirror a flashcard** (test the same word/rule/collocation the flashcard introduced).
- **No hints.** No help available in this phase.
- **No production.** If solving requires writing a sentence, it doesn't belong here.
- **Wrong answer feedback:** one line showing the gap + UZ bridge. Show WHY, not just what.
- Language: student-facing English. UZ bridge in feedback uses formal "Siz".
- Put the most important flashcard or theme concept as item 1 — primacy effect.
- Tags: each item `[Bloom: L1-L2 | PISA: L1]` — Sprint is recognition only, never L3+.
- Visuals: inline SVG only where it speeds recognition (stress-dot, tiny sentence diagram). Under 200×150px.


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
    "options": ["string", "string"],
    "correct": 0
  }
]
```
