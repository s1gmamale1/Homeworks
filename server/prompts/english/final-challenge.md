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

These are question difficulty tiers, not homework modes. English homework mode remains HARD.

| Difficulty | Damage | Distribution |
|-----------|:------:|:----------:|
| Easy | -10 HP | 40% |
| Medium | -20 HP | 40% |
| Hard | -30 HP | 20% |

---

## Question Construction

Every question tagged: `[UZ-ENG{G}-UNIT{N}-{SEQ}] | Bloom: LX | PISA: LX | Damage: -XX HP`

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

> **Q1** `[UZ-ENG7-UNIT4-01] | Bloom: L2 | PISA: L1 | Damage: -10 HP`
> Read: "Scientists have discovered a new species in the Zarafshon river delta."
> What tense is used, and why is it correct here — not past simple?

> **Q2** `[UZ-ENG7-UNIT4-02] | Bloom: L3 | PISA: L2 | Damage: -10 HP`
> Write 2 sentences about Tashkent IT Park using present perfect. Each sentence must use a different time adverb (already / yet / just / ever / never / recently).

> **Q3** `[UZ-ENG7-UNIT4-03] | Bloom: L4 | PISA: L2 | Damage: -20 HP`
> A student wrote: "She has visited Paris last summer." Find the error, explain why it is wrong, and rewrite correctly. Then write a second sentence about the same topic using past simple.

> **Q4** `[UZ-ENG7-UNIT4-04] | Bloom: L5 | PISA: L3 | Damage: -30 HP`
> You are a BBC Tashkent junior reporter. Write a 40-word news paragraph about the Samarkand UNESCO Heritage Festival using at least 2 present perfect sentences and 1 past simple sentence. Your paragraph must flow naturally — not a list of grammar examples.

---

## Hint Ladder

- Hint 1: -5 HP. Remind which grammar rule or vocabulary item applies.
- Hint 2: -5 HP. Show the formula structure or the first clause.
- Hint 3: -5 HP. Show the frame; student completes the content.

## Failure Response

Wrong answer → "Hali emas!" / "Not yet" — never "Noto'g'ri" / "Wrong".
Show WHY the correct answer is correct. Route back to the relevant Preview card.

---

## Rules

- Question count and HP from level table. Grade HP override applies (take higher value).
- Distribution 40/40/20 (easy/medium/hard)
- All questions from THIS unit's content only
- Every question tagged with full inline tag format
- A1: up to 30% MC. A2+ and above: no MC — all open-ended
- Model answers use level-allowed tenses — never a banned tense
- Hints cost HP, not free
- Language: student-facing English
- "Hali emas!" / "Not yet" — never "Noto'g'ri"
- Visuals: inline SVG for diagram-reading questions (force diagrams, sentence trees, IPA charts, timelines). Under 300×200px. Priority SVG > Mermaid > ASCII.


---

## OUTPUT REQUIREMENT
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
