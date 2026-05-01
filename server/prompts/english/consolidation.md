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

Step 1 — describe the content's structure in one sentence before you pick. Step 2 — match it to the table.

| Content structure | Signal | Technique | How to build |
|---|---|---|---|
| **Hierarchical** | One organizing concept with sub-categories. Word families, lexical fields, rule-sets with variants, vocab clusters with shared root. | **Radiant Summary** | Center = the organizing concept. 3-5 branches = sub-categories. Each branch carries one image that encodes its rule or members. |
| **Sequential** | An ordered chain. Tense-formation steps, verb-form derivation, story stages, registration flow. | **Link System** | Steps chained into a vivid story. Each step's image triggers the next via exaggerated causality. |
| **Spatial** | The content already involves real places, locations, or physical relationships. Prepositions of place, room/house vocab, neighbourhood landmarks, directions, jobs-in-places. | **Memory Palace** | See location-derivation rule below. The palace must come from the unit. |
| **Discrete** | A flat list of unrelated items needing fixed retrieval order. Irregular verb list, miscellaneous phrasal verbs without thematic grouping. | **Peg System** | Each item paired with a vivid impossible image keyed to a number/peg. |
| **Numeric** | Dates, statistics, numbered rules, centuries. | **Major System** | Digits mapped to consonant sounds; build a memorable word from the digits. |

Pick ONE technique. Match the station/branch count in the level table.

### Decision check before you commit

- If you picked **Memory Palace**, can you point to a real place that already appears in the unit's content (its reading, scenario, or central visual)? If no, your content is not spatial — re-read it and pick again. Famous landmarks are NOT a default; they only count when the unit's content actually places students inside them.
- If you picked **Radiant Summary**, is there a single clear concept the rest hangs off? If no, your content might be sequential (Link) or a flat list (Peg).
- If you picked **Link System**, is there a forced order? If the items can be learned in any order, it's not sequential — switch to Radiant or Peg.

---

## Memory Palace — location must come from the unit

When (and only when) the content is genuinely spatial, the palace location is **derived from the unit's own content**, not chosen from a list. The technique works because the place's physical structure encodes the content's relationships — a generic landmark with no link to the content defeats the technique entirely.

**Where to find the location, in priority order:**

1. **A place inside the unit's reading or scenario.** If the reading happens at a market, a school corridor, a kitchen, a wedding hall, an airport, a mahalla courtyard — that's your palace. The student has just spent minutes inside it.
2. **The unit's primary visual.** If the textbook page is built around a diagram (a tree, a house cutaway, a map, a neighbourhood plan, a flowchart), reuse that diagram's spatial structure as your palace. The student already has the picture in their head.
3. **A real place the student physically inhabits whose layout encodes the content.** Examples: prepositions unit → student's own bedroom (under the bed, on the desk, in the wardrobe). Body-parts unit → student's own body. Classroom-objects unit → the student's classroom.

**Veto rule.** Before you commit to a palace, ask: *does walking through this place in my mind force me to encounter the content's relationships in the right order?* If the answer is "I'm just plotting concepts onto unrelated rooms," abandon Memory Palace and pick Radiant Summary or Link System. **A famous landmark with no structural connection to the content is decoration, not encoding.**

Grade shapes abstraction, not location identity:
- **G5-6:** Locations should be physical and immediately known (the student's house, the maktab, the place from the reading). No metaphorical palaces.
- **G7-11:** Locations can be conceptually structured if they appear in the unit (a tree diagram, a journey route, a market floor plan, a body of work).

There is no fixed list of acceptable palaces. Do not reuse the same location across unrelated units for "consistency" — it weakens encoding.

Apply SMASHIN' SCOPE inside each station: Substitution, Movement, Association, Absurdity, Humour, Imagination, Number, Colour, Order, Positive image, Exaggeration. Cultural anchoring (UZ 55% / global 45%) applies *within* the chosen location — it does not override structural fit.

---

## Examples

### Hierarchical content → Radiant Summary

A unit teaches one organizing concept (a vocab cluster, a rule with variants) plus 2-3 connected sub-rules.

> Technique: Radiant Summary
> Center: the unit's organizing concept, anchored to the textbook's central visual where one exists.
> Branches: one per sub-category, each with a vivid image that encodes its rule or members.
>
> **Branch 1 — Core cluster.** Image: each leaf carries one named member; nodes coloured by category.
> **Branch 2 — Main pattern/rule.** Image: a glowing transformation (e.g. a suffix-stamp) acting on a base form.
> **Branch 3 — Exceptions.** Image: figures who refuse the transformation and keep their original form.
> **Branch 4 — Modifier set.** Image: a vertical slider with notches, each labelled with one modifier word.

### Spatial content → Memory Palace (location from the unit)

A unit teaches prepositions of place using the student's own bedroom as the textbook's visual scenario.

> Technique: Memory Palace — your bedroom (the same bedroom from the textbook diagram).
>
> **Station 1 — under the bed.** Concept: "under". Image: a giant cat hiding under the bed, eyes glowing.
> **Station 2 — on the desk.** Concept: "on". Image: an open notebook glowing on the desk.
> **Station 3 — in the wardrobe.** Concept: "in". Image: a friend hiding inside the wardrobe.
> **Station 4 — between the chair and the wall.** Concept: "between". Image: a backpack squeezed between them.
>
> The location is the same physical room the textbook's diagram depicts. The student doesn't translate twice — the place IS the grammar.

### Sequential content → Link System

A unit teaches a 4-step grammar sequence (e.g. forming a tense, building a question, transforming a sentence). Chain the steps into one absurd causal story so each step's image triggers the next.

### When NOT to use Memory Palace

A grammar unit on tense formation has no spatial structure. Plotting tenses onto a famous landmark's gate / courtyard / arch / dome adds zero retrieval scaffolding because the landmark doesn't encode tense relationships. The student has to translate twice (tense → station → meaning) and the second translation carries no signal. Pick Radiant Summary or Link System instead.

A vocab unit on family relations has no spatial structure either — it is hierarchical (a word family). A bedroom or a tree diagram could serve as a *visual scaffold* under Radiant Summary, but it is not a Memory Palace.

---

## Rules

- Fires only when 2+ concepts in the unit; otherwise skip.
- Stations / branches count per level table.
- ONE technique per session.
- ~3 minutes total — calm moment before Final Challenge.
- No scoring in this phase.
- Images vivid and exaggerated. Cultural anchoring (UZ 55% / global 45%) applies *within* the chosen technique — never override structural fit for cultural flavour.
- Language: student-facing English. Local names (mahalla, bozor, etc.) in parentheses where the location uses them.
- **Technique must match content structure.** Re-read the content before picking. The default for word-family or rule-set content is Radiant Summary, NOT Memory Palace.
- **Memory Palace location is derived from the unit, never from a fixed list.** No default monuments, no recurring "famous landmarks." If the content gives you no natural location, the content isn't spatial — use a different technique.
- **Visuals:** inline SVG per station/branch — simple line drawing whose shape matches the chosen scaffold (a tree if the scaffold is a tree, a bedroom outline if the palace is a bedroom, a market floor plan if the palace is a market) with the concept's image overlaid in its anchor position. **No decorative, generic, stock-like, or out-of-topic media.** Under 300×200px.
  - BAD: a famous monument outline used as a Memory Palace for content that has no spatial structure.
  - BAD: a generic shelf/door/room SVG bearing no resemblance to the named location.
  - GOOD: a stylised outline of the actual place from the unit (or the textbook's central diagram), with each concept's image planted in its anchor position.


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
