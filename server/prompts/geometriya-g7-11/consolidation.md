# Prompt: Consolidation — Geometry (Hard only, conditional)

You are building the Consolidation phase (Phase 5) for a Geometry Hard mode session. This phase fires ONLY when the lesson teaches 2 or more distinct interlocking concepts. If the lesson covers a single concept, skip this phase entirely.

Purpose: lock the concepts into long-term memory using a mnemonic technique before the Final Challenge.

## Input

- Textbook page (image or text)
- All previous phase outputs
- Grade: G7-9 (Geometriya)

> **SVG Rule:** Any concept map, mnemonic diagram, or comparison figure must be actual SVG code — not a bracket description alone. Use `instruction.md` → SVG Output Rule for templates and color hex codes.

## Decision: Build or Skip?

- Lesson has 2+ distinct concepts that connect → **BUILD**
- Lesson covers 1 concept → **SKIP** (output: "Consolidation skipped — single concept lesson")

Examples:
- "SAS, SSS, ASA tenglik belgilari" → 3 criteria → BUILD
- "Parallel to'g'ri chiziqlar va kesuvchi burchaklari" → 2+ angle relationships → BUILD
- "To'g'ri burchak ta'rifi" → 1 concept → SKIP

## Output (if building)

One mnemonic exercise, ~3 minutes.

---

## Pick a technique based on content structure

| Content structure | Technique | How to build |
|-------------------|-----------|-------------|
| **Hierarchical** (theorem families, angle classifications, shape types) | **Radiant Summary** | Center = main concept (e.g., "Tenglik belgilari"). 3-5 branches = sub-types (SAS, SSS, ASA). Each branch has theorem statement + diagram description. Student fills in missing branches. |
| **Discrete theorems** (2-5 rules to remember) | **Peg System** | Each theorem paired with a vivid image. Student recalls theorem from image and image from theorem — in both directions. |
| **Sequential** (steps of a proof or construction procedure) | **Link System** | Steps of the proof chained into a vivid story. Each step links to the next through an image or action. Every step cites the theorem or property used. |
| **Spatial** (angle relationships at a transversal, shapes in a diagram) | **Memory Palace** | Concepts placed at locations in Registan Square. Student walks through and recalls the theorem or property at each spot. Example: SAS at the main arch, SSS at the left minaret, ASA at the right minaret. |

Pick ONE technique. Keep it to 3 minutes — this is a quick lock, not a deep exercise.

---

## After the mnemonic (mandatory)

Show 3-4 diagrams — student names the theorem or property illustrated by each. 45 seconds.

> "Teoremalar galereyasi — har bir rasmda qaysi teorema ko'rsatilgan?"
> `[Diagram 1: ...]` → answer
> `[Diagram 2: ...]` → answer
> `[Diagram 3: ...]` → answer

Every diagram described in brackets.

---

## Rules

- Only fires when 2+ concepts in the lesson
- One technique only
- ~3 minutes max
- Every diagram referenced in brackets
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
