# Prompt: Consolidation — English (Phase 5, HARD only — conditional)

You are building the Consolidation phase (Phase 5) for an English HARD mode session. Purpose: lock the session's concepts into long-term memory using a mnemonic technique before the Final Challenge.

This phase fires ONLY when the unit teaches 2+ distinct interlocking concepts. If the unit covers a single concept, skip this phase.

## Input

- Textbook unit (image or text)
- All previous phase outputs
- Detected CEFR level (from `classify.md`): A1 · A1+ · A2 · A2+ · B1 · B1+ · B2
- Grade (for Memory Palace location concreteness)

## Decision: Build or Skip?

- Unit has 2+ distinct concepts that connect → **BUILD**
- Unit covers 1 concept → **SKIP** (output: "Consolidation skipped — single concept unit")

Examples:
- "Past simple + past continuous" → 2 tenses → BUILD
- "Present perfect with ever/yet/already/just" → placement rules + tense → BUILD
- "Job vocabulary (receptionist, manager, pilot...)" → single vocab set → SKIP

## Output (if building)

One mnemonic exercise, ~3 minutes. Stations per CEFR level:

| Level | Stations |
|:-:|:-:|
| A1 / A1+ | 3 (concrete images) |
| A2 / A2+ | 4 (concrete + light abstraction) |
| B1 / B1+ | 4 (mixed concrete/abstract) |
| B2 | 4 (abstract conceptual links) |

---

## Pick a technique based on content structure

| Content structure | Technique | How to build |
|-------------------|-----------|-------------|
| **Hierarchical** (word families, grammar rule-sets) | **Radiant Summary** | Center = main concept. 3-5 branches = sub-rules or variants. Each branch has one image + the rule. |
| **Sequential** (tense chain, verb form chain) | **Link System** | Steps chained into a vivid story. Each step links to the next through an exaggerated image or action. |
| **Spatial** (job vocab, neighbourhood words, prepositions) | **Memory Palace** | Concepts placed at locations in a real Uzbek space. See location guidance below. |
| **Discrete** (random unconnected new words) | **Peg System** | Each word paired with a vivid, impossible image. |
| **Numeric** (dates, centuries, historical years) | **Major System** | Digits mapped to consonant sounds. Build a word from digits. |

Pick ONE technique. Match the station count in the level table.

---

## Memory Palace — Uzbek location anchors (grade-anchored)

Grade shapes location concreteness:
- **G5-6:** Prefer student's own maktab corridor or mahalla street. Named landmarks fine but secondary.
- **G7-11:** Use named national landmarks — Registan, Chorsu bozor, Bibi-Khanym mosque, Hazrati Imam library — for cross-session consistency.

Standard palace anchors:
- Registan gate · Chorsu bozor dome · Bibi-Khanym arch · Hazrati Imam library · student's maktab corridor

Apply SMASHIN' SCOPE: Substitution, Movement, Association, Absurdity, Humour, Imagination, Number, Colour, Order, Positive image, Exaggeration.

---

## Example: 4-station Palace (Registan, B1 — present perfect unit)

> Technique: Memory Palace — Registan, Samarkand

> **Station 1 — Registan gate**
> Concept: "have/has + V3 = result NOW matters"
> Image: A flying carpet labelled "V3" has just landed at the gate, still steaming from the past but HERE now.

> **Station 2 — Central courtyard**
> Concept: present perfect banned when time is named ("last Tuesday")
> Image: A calendar page "LAST TUESDAY" is handcuffed to a guard who won't let "have" through.

> **Station 3 — Tilla-Kori minaret**
> Concept: ever / yet / already / just — placement after "have"
> Image: Four acrobats on each other's shoulders — JUST at the bottom, EVER at the top waving a flag.

> **Station 4 — Sherdor facade**
> Concept: have vs has — subject decides
> Image: A lion (has — single, grammar boss) on the left arch, a flock of doves (have — plural) from the right.

---

## Rules

- Fires only when 2+ concepts in the unit; otherwise skip
- Stations count per level table
- ONE technique per session
- ~3 minutes total — calm moment before Final Challenge
- No scoring in this phase
- Images must be vivid, exaggerated, culturally anchored (UZ 55% / global 45%)
- Language: student-facing English. Station labels in English. UZ location name in parentheses.
- Technique must match content structure — never default to Palace unless content is spatial
- G5-6: prefer student's own maktab/mahalla; G7-11: prefer national landmarks
- **Visuals:** inline SVG per station — simple line drawing of the named location with the station image overlaid in its anchor position. The location must be the actual one in the mnemonic chain (Registan gate, Chorsu dome, Hilton Tashkent lobby, etc.), not a generic interior. **No decorative, generic, stock-like, or out-of-topic media.** Under 300×200px.
  - BAD: a generic library shelf SVG used as the "Hilton Tashkent" station for a present-perfect mnemonic.
  - GOOD: an outline SVG of the Hilton Tashkent facade with the past-participle ("worked") banner planted in the lobby — the location is real and the image-anchor matches the chain.


---

## OUTPUT REQUIREMENT
Return valid JSON matching this exact schema:
```json
{
  "mnemonic": "string",
  "lock_code": "string",
  "explanation": "string"
}
```
