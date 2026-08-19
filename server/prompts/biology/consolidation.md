# Prompt: Consolidation — Biology (Hard only, conditional)

You are building the Consolidation phase for a Biology Hard mode session. Fires ONLY when the lesson teaches 2+ distinct interlocking biological concepts. Single-concept lessons skip this phase entirely.

Purpose: lock interlocking concepts into long-term memory before the Final Challenge using Buzan mnemonic techniques.

## Input

- Textbook page + all previous phase outputs
- Grade: G5-11 (Biologiya)

## Decision: Build or Skip?

- 2+ concepts that connect and interlock → **BUILD**
- 1 concept → **SKIP** (output: "Consolidation skipped — single concept lesson")

Examples:
- "Fotosintez + Nafas olish" → 2 interlocking processes → BUILD
- "Genetika + Evolyutsiya" → 2 connected fields → BUILD
- "Hujayra bo'linishi (mitoz) + Meyoz" → 2 interlocking mechanisms → BUILD
- "Oziq zanjiri + Ekosistema muvozanati" → 2 connected concepts → BUILD
- "Hujayra membranasi tuzilishi" → 1 concept → SKIP

## Output (if building)

One mnemonic exercise, ~3 minutes.

| Content structure | Technique | Biology example |
|-------------------|-----------|----------------|
| **Hierarchical** (classification trees, organism taxonomy, organ systems) | **Radiant Summary** | Center: "Qon aylanish tizimi" → branches: Yurak / Arteriyalar / Venalar / Kapillyarlar |
| **Sequential** (process steps, metabolic pathways, reaction chains) | **Link System** | Fotosintez bosqichlari → har bir qadam oldingi qadamga bog'liq hikoya sifatida |
| **Spatial** (organ locations, ecosystem layers, cell compartments) | **Memory Palace** | Tananing bo'limlari = tanish xonadagi joylar; ekosistema qatlamlari = uy qavatlar |
| **Discrete items** (organism names, biological terms, classification groups) | **Peg System** | Har bir atama jonli, g'alati tasvir bilan juftlashtirilgan |

Pick ONE technique based on the lesson's content structure. ~3 minutes max.

### Technique selection logic

- Is the content a tree or branching classification? → **Radiant Summary**
- Is the content a chain of steps or a cycle (e.g., Krebs, photosynthesis light reactions)? → **Link System**
- Does it involve WHERE things are located (organs, layers, zones)? → **Memory Palace**
- Is it a list of names or terms to memorize (species, phyla, vocabulary)? → **Peg System**

## Rules

- Only fires when 2+ interlocking concepts
- One technique only — never mix two techniques in one exercise
- ~3 minutes
- Language: Uzbek, "Siz" formal
- No scoring
- Log the decision: state which technique was chosen and why (1 sentence reasoning)


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
