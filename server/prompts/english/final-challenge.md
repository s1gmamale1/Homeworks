# Prompt: Final Challenge (Boss) — English (HARD only)

You are building the Final Challenge for an English homework session. This is the boss fight — HP combat. The student proves mastery of everything taught in this session.

## Input

- Textbook unit (image or text)
- All previous phase outputs
- Detected CEFR level (from `classify.md`): A1 · A1+ · A2 · A2+ · B1 · B1+ · B2
- Grade (for HP override)

## Output

Boss questions with HP damage tags (count by CEFR level). Mix of difficulty tiers.

| Level | HP | Questions | Essay requirement |
|:-:|:-:|:-:|---|
| A1 / A1+ | 60-80 | 3 | none |
| A2 / A2+ | 80 | 3-4 | none |
| B1 / B1+ | 100-150 | 4-5 | 80-word paragraph |
| B2 | 150 | 5 | 150-word IELTS Task-2 |

**Grade HP override (take the higher value):** G5-6 = 80 · G7-8 = 100 · G9-11 = 150. Never punish a higher-grade student with lower HP on a detected-easier unit.

**Tenses in model answers:** level-allowed set only (see `classify.md`).

---

## Damage Table (all levels)

| Difficulty | Damage | Distribution |
|-----------|:------:|:----------:|
| Easy | -10 HP | 40% |
| Medium | -20 HP | 40% |
| Hard | -30 HP | 20% |

> **Tier disambiguation.** "Easy / Medium / Hard" in the table above refers to **item difficulty within the boss**, not homework mode. English homework mode is always HARD per `classify.md`. Do not treat a per-question tier label as a basis for switching the session's overall mode.

---

## Question Construction

Every question tagged: `[Bloom: LX | PISA: LX | Damage: -XX HP]`

**Must include:**
- ≥1 reading/vocab-in-context Q (student reads a short text and answers)
- ≥1 production Q (write a paragraph, dialogue, or transform a sentence)
- B1 level: 1 short essay (~80 words)
- B2 level: 1 IELTS Task-2 argument essay (~150 words, 4-para) + 1 register transformation (informal→formal) + 1 rhetorical analysis

**MC restriction:**
- A1: up to 30% MC allowed (max 1 of 3)
- A2+ and above: **NO MC.** All open-ended production.

**Difficulty scaling:**
- Easy (-10): single-skill recognition or controlled production (fill one blank in a fixed frame)
- Medium (-20): 2-step task (read + produce OR identify + explain)
- Hard (-30): multi-step with context (read + analyse + write + justify)

**Visual question variants (B1+):** one Hard-tier question may present an inline SVG — an IPA chart to read and produce, a sentence-diagram tree with one branch missing, or a timeline diagram. Max one per boss.

---

## Example: B1, 4 questions (present perfect unit)

> **Q1** `[Bloom: L2 | PISA: L1 | Damage: -10 HP]`
> Read: "Scientists have discovered a new species in the Zarafshon river delta."
> What tense is used, and why is it correct here — not past simple?

> **Q2** `[Bloom: L3 | PISA: L2 | Damage: -10 HP]`
> Write 2 sentences about Tashkent IT Park using present perfect. Each sentence must use a different time adverb (already / yet / just / ever / never / recently).

> **Q3** `[Bloom: L4 | PISA: L2 | Damage: -20 HP]`
> A student wrote: "She has visited Paris last summer." Find the error, explain why it is wrong, and rewrite correctly. Then write a second sentence about the same topic using past simple.

> **Q4** `[Bloom: L5 | PISA: L3 | Damage: -30 HP]`
> You are a BBC Tashkent junior reporter. Write a 40-word news paragraph about the Samarkand UNESCO Heritage Festival using at least 2 present perfect sentences and 1 past simple sentence. Your paragraph must flow naturally — not a list of grammar examples.

---

## Hint Ladder

- **Hint 1: -5 HP.** Remind which grammar rule or vocabulary item applies — name the concept, never the answer.
- **Hint 2: -5 HP.** Show the formula structure (e.g., "have/has + V3") or the first clause — never the full model answer.
- **Hint 3: -5 HP.** Show the frame with all content blanked; student fills in. Even at Hint 3, the literal answer text never appears.

**Anti-leak rules (apply at every level):**
- Hint must never quote the model answer verbatim or in any inflected form.
- Hint must never name the correct option for any sub-choice in the question.
- Hint must teach toward the answer (concept, formula, frame), not deliver it.

**BAD / GOOD (for a question whose answer is "She has already finished the report"):**
- BAD Hint 1: "The answer is present perfect with 'already'." (names the answer)
- GOOD Hint 1: "Look at the time adverb — which tense pairs with 'already'?"
- BAD Hint 2: "Use 'has already finished'." (gives the answer)
- GOOD Hint 2: "Formula: subject + has/have + V3. Time adverb sits between."
- BAD Hint 3: "She has already finished the report." (literal answer)
- GOOD Hint 3: "She _____ the report. (verb + time adverb in V3 form)"

## Failure Response

Wrong answer → "Hali emas!" / "Not yet" — never "Noto'g'ri" / "Wrong".
Show WHY the correct answer is correct. Route back to the relevant Preview card.

---

## Rules

- Numbering: questions are pre-numbered 1–6 by the system. Do not renumber mid-stream.
- Question count and HP from level table. Grade HP override applies (take higher value).
- Distribution 40/40/20 (easy/medium/hard)
- All questions from THIS unit's content only
- Every question tagged with full inline tag format
- A1: up to 30% MC. A2+ and above: no MC — all open-ended
- Model answers use level-allowed tenses — never a banned tense
- Hints cost HP, not free
- Language: student-facing English
- "Hali emas!" / "Not yet" — never "Noto'g'ri"
- **Visuals:** inline SVG only for diagram-reading boss questions — sentence trees, IPA charts, register-comparison tables, timelines. The visual must be exactly what the question references. **No decorative, generic, stock-like, or out-of-topic media.** Under 300×200px. Priority SVG > Mermaid > ASCII.
  - BAD: a generic London skyline SVG on a present-perfect question (no link to the grammar being tested).
  - GOOD: a sentence-tree SVG with the verb-phrase node circled, paired to a question asking the student to identify the present-perfect structure.


---

## OUTPUT REQUIREMENT

**Stored key: `boss_questions[]`.** `final_challenge` is only the pipeline and
builder phase name — nothing is ever stored under that name. The builder files
this array under `boss_questions`, and that is the name the runtime reads. Paste
the output into the builder's "Yakuniy jang" (👾) editor; return the bare
array, unwrapped.

Field routing — all five reach the screen:
- `q` -> the question body.
- `tags` -> parsed server-side into the Bloom/PISA header. Only the `Bloom:` and
  `PISA:` segments are read; the `Damage:` segment inside the tag string is
  inert — `dmg` is what actually sets damage. Keep the two in sync anyway.
- `ans` -> the server-only accepted-answer list. Stripped before the page is
  sent, so it never leaks to the student.
- `hint` -> split on newline, ` | ` or `•` into the 3-step hint ladder.
- `dmg` -> HP damage, and it also picks the tier badge (<=10 easy, <=20 medium,
  otherwise hard).

Return valid JSON matching this exact schema:
```json
[
  {
    "q": "string",
    "tags": "[Bloom: LX | PISA: LX | Damage: -XX HP]",
    "ans": ["string", "string"],
    "hint": "string",
    "dmg": 10
  }
]
```
