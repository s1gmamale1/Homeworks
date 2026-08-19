# Prompt: Consolidation — Math + Algebra (Hard only, conditional)

You are building the Consolidation phase (Phase 5) for a Math/Algebra Hard mode session. This phase fires ONLY when the lesson teaches 2 or more distinct interlocking concepts. If the lesson covers a single concept, skip this phase entirely.

Purpose: lock the concepts into long-term memory using a mnemonic technique before the Final Challenge.

## Input

- Textbook page (image or text)
- All previous phase outputs
- Grade: G5-6 (Matematika) or G7-9 (Algebra)

## Decision: Build or Skip?

- Lesson has 2+ distinct concepts that connect → **BUILD**
- Lesson covers 1 concept → **SKIP** (output: "Consolidation skipped — single concept lesson")

Examples:
- "Kasrlarni qo'shish va ayirish" → 2 operations → BUILD
- "Kvadrat tenglama va diskriminant" → 2 concepts → BUILD
- "Natural sonlarni ko'paytirish" → 1 method → SKIP

## Output (if building)

One mnemonic exercise, ~3 minutes.

---

## Pick a technique based on content structure

| Content structure | Technique | How to build |
|-------------------|-----------|-------------|
| **Hierarchical** (types, categories) | **Radiant Summary** | Center = main concept. 3-5 branches = sub-types. Each branch has definition + example. Student fills in missing branches. |
| **Discrete formulas** (2-5 rules to remember) | **Peg System** | Each formula paired with a vivid image. Student recalls formula from image and image from formula. |
| **Sequential** (steps of a procedure) | **Link System** | Steps of the method chained into a vivid story. Each step links to the next through an image or action. |
| **Spatial** (shapes, graphs, geometry) | **Memory Palace** | Concepts placed at locations in a familiar space. Student walks through and recalls what's at each spot. |

Pick ONE technique. Keep it to 3 minutes — this is a quick lock, not a deep exercise.

---

## Rules

- Only fires when 2+ concepts in the lesson
- One technique only
- ~3 minutes max
- Language: Uzbek, "Siz" formal
- No scoring — this is a calm moment before the Final Challenge


---

## OUTPUT REQUIREMENT

**Stored key: `content_json.consolidation`.** Paste the output into the
builder's "Mustahkamlash" (🧠) editor.

The renderer reads exactly these keys and ignores every other key:
- `mnemonic` — required. The mnemonic exercise itself. Inserted as raw HTML,
  so inline `<strong>`, `<br>`, `<ul>`, `<details>` and inline `<svg>` all
  work. Markdown is NOT converted — write real tags, not `**bold**`.
- `bullets[]` — the supporting prose, one string per line item, rendered as a
  list under the mnemonic. Put the walkthrough steps / branches / stations
  here rather than cramming them into a single `mnemonic` string.
- `title` — optional header override. Defaults to the phase name when omitted.
- `check_prompt` / `check_answer` — optional ungraded self-check. The student
  sees `check_prompt`; a "show answer" button then reveals `check_answer`. No
  verdict, no score, no gating. Omit both when the technique has no recall test.

Do NOT emit `explanation` or `lock_code`. Both are dead keys from a retired
shape: the builder editor discards them on save and the renderer never reads
them, so anything written there is silently lost. The BUILD/SKIP decision and
the technique-choice reasoning are notes to the author — report them alongside
the JSON, never inside it.

Return valid JSON matching this exact schema:
```json
{
  "title": "string",
  "mnemonic": "string",
  "bullets": ["string", "string"],
  "check_prompt": "string",
  "check_answer": "string"
}
```
