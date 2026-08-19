# Prompt: Consolidation — Physics (Hard only, conditional)

You are building the Consolidation phase for a Physics Hard mode session. Fires ONLY when the lesson teaches 2+ distinct interlocking concepts. Single-concept lessons skip this.

Purpose: lock concepts into long-term memory before the Final Challenge.

## Input

- Textbook page + all previous outputs
- Grade: G7-11 (Fizika)

## Decision: Build or Skip?

- 2+ concepts that connect → **BUILD**
- 1 concept → **SKIP** (output: "Consolidation skipped — single concept lesson")

Examples:
- "Kuch va tezlanish" → 2 connected concepts → BUILD
- "Om qonuni + Kirchhoff qonuni" → 2 laws → BUILD
- "Inersiya tushunchasi" → 1 concept → SKIP

## Output (if building)

One mnemonic exercise, ~3 minutes.

| Content structure | Technique | Physics example |
|-------------------|-----------|----------------|
| **Hierarchical** (types of energy, types of forces) | **Radiant Summary** | Center: "Energiya" → branches: Kinetik / Potensial / Issiqlik / Elektr |
| **Formulas** (2-5 laws to remember) | **Peg System** | Each formula paired with vivid image |
| **Sequential** (experiment steps, process chain) | **Link System** | Steps chained into a story |
| **Spatial** (field lines, circuit layout) | **Memory Palace** | Concepts at locations in a familiar space |

Pick ONE technique. ~3 minutes max.

## Rules

- Only fires when 2+ concepts
- One technique only
- ~3 minutes
- Language: Uzbek, "Siz" formal
- No scoring


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
