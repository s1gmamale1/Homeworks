# Prompt: Consolidation — History (O'zbekiston Tarixi + Jahon Tarixi)

You are building the Consolidation phase (Phase 5) for a History homework session. This phase fires when the lesson introduces 2 or more interlocking concepts. If the lesson covers a single concept, SKIP.

Purpose: lock the lesson's multiple concepts into long-term memory via a Buzan mnemonic technique. It's a calm moment between Games (Phase 3) and Final Challenge (Phase 6).

**Not scored.** ~3 minutes.

## Input

- Textbook lesson content (extracted in orchestrator Step 1)
- Preview output (especially the Memory Palace station list)
- Flash Cards output + Sprint output + Games output
- Grade: G5–G11
- Subject: `O'zbekiston Tarixi` or `Jahon Tarixi`

## Output

First: **BUILD or SKIP decision.**

- Lesson has ≥2 distinct interlocking concepts → **BUILD** (the common case for History)
- Lesson covers 1 concept only → **SKIP** — output: `"Consolidation skipped — single-concept lesson"`

If BUILD: ONE mnemonic exercise, ~3 minutes.

---

## Decision — BUILD or SKIP?

| Lesson type | Decision |
|---|---|
| Multi-figure, multi-event narrative (typical History) | BUILD |
| Reign/dynasty chronology | BUILD |
| Chapter review / synthesis | BUILD |
| Single-concept definitional (rare in History) | SKIP |

History lessons almost always BUILD. SKIP only when the lesson introduces exactly one term or concept with no accompanying figures/events/causation.

---

## Technique selection

Pick ONE based on the lesson's content structure:

| Content structure | Technique | How to build |
|---|---|---|
| **Sequential + Spatial** (events across geography — typical History) | **Memory Palace** (Method of Loci) | Full walkthrough of the 5–10 stations built in Preview. Student pauses at each to recall. |
| **Multiple figures with successive roles** (e.g., rulers of a dynasty) | **Link System** | Chain bizarre imagery across all figures in reign order. |
| **Hierarchical** (types, categories — rare in narrative History) | **Radiant Summary** | Center = dominant concept; branches = sub-categories. Student fills missing branches. |

**Default choice: Memory Palace.** Most History lessons are sequential + spatial. Only deviate when the lesson structure is fundamentally different (e.g., a "types of primary sources" lesson uses Radiant).

---

## Construction — Memory Palace walkthrough (default path)

Use the stations from Preview's palace. **Do not invent new stations in Phase 5.**

For each station:

```
### N-Bekat — PLACE NAME (era/date parenthetical)

🏰 **Tasavvur qiling:** [vivid imagery from Preview's palace — remind the student]

❓ **Savol:** [recall prompt — who was here, what happened, which date]

<details>
<summary>✓ Javob</summary>

- **Kim:** [figure(s) anchored here]
- **Sana:** [key date(s) if tied to this station]
- **Fakt:** [key event or achievement]

</details>

**Self-check:** [verify the visual — "can you still see the image clearly?"]
```

After walking all stations, close with a verification prompt:

```
> **Siz Xotira saroyining barcha bekatlaridan yurib chiqdingiz. Birortasini tushirib qoldirdingizmi?**
>
> Ha / Yoʻq
```

- **Ha** → route back to the missed station(s).
- **Yoʻq** → *"Final Challenge-ga toʻliq tayyor."*

## Alternative — Link System (chain of figures)

When the lesson is primarily a succession of rulers or scholars with no dominant geographic anchor:

- Chain 5–10 figures in chronological order
- Each figure connects to the next via a **bizarre visual link** (Buzan rule — unusual, vivid, concrete)
- Each link includes: figure name + key achievement + 1-sentence imagery tying them to the next figure
- Close with a recall prompt: "Who was third in the chain?"

## Alternative — Radiant Summary (hierarchical concept)

For rare definitional/taxonomic History lessons:

- Center node = the dominant concept
- 3–5 branches = sub-categories
- Each branch has 1 definition + 1 example from the lesson
- Student fills in 1–2 missing branches

---

## Rules

- **Conditional firing** — BUILD only when ≥2 interlocking concepts. Otherwise output the SKIP marker.
- **One technique only** per session.
- **~3 minutes max** — this is a mnemonic lock, not a deep exercise.
- **Not scored** — no HP, no XP penalty, no grading.
- **Use Preview's palace and walk through ALL stations** (when Memory Palace is chosen) — do not create new stations, and **do not skip any existing stations.** If Preview's palace has 6 stations, Phase 5 walks all 6. If 10, walks all 10.
- **Active recall format** — collapsed answers (`<details>`). Student recalls FIRST, peeks SECOND.
- **Self-check prompt REQUIRED after every station** — verify the visual imagery ("can you still see the image?"), not just the facts. This is not optional.
- **Final verification prompt REQUIRED** at the end — the "Hit all N stations?" prompt with Ha/Yoʻq options. Route missed stations back.
- **Textbook fidelity** — every station fact matches the textbook and Preview.
- **Language:** Uzbek, `Siz`. Never `sen`.
- **Tonality:** calm, satisfying, "you're almost there." No urgency, no score pressure.


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
