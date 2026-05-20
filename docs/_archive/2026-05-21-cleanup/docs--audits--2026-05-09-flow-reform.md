# Flow Reform — Reformer's Proposals — 2026-05-09

*(Agent B output. Grounded in: flow-recon.md + MASTER.md + engagement.md + sampled prompts: math-algebra/preview-hard.md, history/preview.md, biology/game-breaks.md)*

---

## Mapping to user complaints

- Complaint 1 (interactivity) — addressed by proposals: P1, P3, P5
- Complaint 2 (boring/raw) — addressed by: P2, P4, P6
- Complaint 3 (Uzbek grammar) — addressed by: P7, P8

---

## P1. Resurrect Memory Match — add 'mm' to gbActiveGameOrder()

- **WHY:**
  - Memory Match has full JS (`gbInitMM`, `GB_MEMORY_MATCH` constant, flip-card UI), is spec'd in flow.md for math, history, biology, physics, and english, and is listed as mandatory for history — yet `gbActiveGameOrder()` (lines 12666–12689, `server/template/perfect_homework.html`) has no `mm` entry. Every student who gets a history homework silently loses a game they were supposed to play.
  - This is a zero-cost interactivity gain: the mechanic is fully built.
- **HOW:**
  - `server/template/perfect_homework.html` line ~12687 (after the Memory Palace `mp` entry): add one `if (!skipped.has('mm') && Array.isArray(GB_MEMORY_MATCH) && GB_MEMORY_MATCH.length > 0)` guard with the `mm` slot entry (sub: 8, init: gbInitMM, panel needs to be created or confirmed).
  - Confirm/add `#gb-panel-mm` HTML panel (check if orphaned panel HTML exists; if not, clone `#gb-panel-tm` structure — it is the closest UI shape).
  - `server/prompts/biology/game-breaks.md`, `history/game-breaks.md` (and math, physics equivalents): Memory Match is already listed as an available game — no prompt changes needed. The content injector already populates `GB_MEMORY_MATCH`.
  - Add one regression test: `test_memory_match_routed.py` — assert that a history homework with `GB_MEMORY_MATCH` populated routes `mm` in `gbActiveGameOrder()`.
- **WHAT (after):**
  - `gbActiveGameOrder()` has a 9th conditional entry for `mm`.
  - A history student on Hard sees 3 game-breaks including Memory Match as spec'd.
  - The orphaned constant `GB_MEMORY_MATCH` is no longer dead code.
- **Cost estimate:** S (2–4 hours — mostly confirming the panel HTML exists, then one-line routing fix + test)
- **Targets complaint:** 1

---

## P2. Fix the Why Chain mislabel — rename 'Sentence Fill' (wc slot) to 'Why → How → What'

- **WHY:**
  - `gbActiveGameOrder()` slot 1 is `id: 'wc'` with `label: 'Sentence Fill'` — but the mechanic is `GB_WHY_CHAIN`, a causal-chain scaffold (Why → How → What). The label "Sentence Fill" is also used by slot 6 (`id: 'sf'`). Two different mechanics, same student-facing label.
  - The MASTER audit (P3 item) calls this "a 1-day fix with outsize pedagogical impact." The mechanic already exists and is used in legacy subjects — the failure is purely in labeling and prompt framing.
  - Currently no subject flow.md specifies `gb_why_chain` as mandatory, meaning the mislabel also suppresses adoption.
- **HOW:**
  - `server/template/perfect_homework.html` line 12672: change `label: 'Sentence Fill'` to `label: 'Why → How → What'` and `labelKey: 'game.wc'` to `labelKey: 'game.whw'`.
  - Add `'game.whw': { uz: "Nega → Qanday → Nima", ru: "Почему → Как → Что", en: "Why → How → What" }` to the i18n strings block.
  - `server/prompts/math-algebra/game-breaks.md` and `biology/game-breaks.md`: add `**Why → How → What**` as an explicitly named option with a 1-line description of when to use it (reasoning-chain questions for Hard mode).
  - The boss prompts in `boss-question-generator.md` currently use How→How→What per the MASTER audit — fix the first tier to Why.
- **WHAT (after):**
  - Student sees "Why → How → What" in the game-break header (not "Sentence Fill" twice).
  - The mechanic's causal scaffolding becomes legible — the student knows what they're doing.
  - Boss questions now correctly open with a Why-tier prompt.
- **Cost estimate:** S (3–5 hours including i18n key + boss prompt fix + test)
- **Targets complaint:** 2

---

## P3. Surface the preview panels' BOST goal as an interactive micro-prompt

- **WHY:**
  - Every subject's Preview (Panel 7 for math, Panel 6 for history) ends with a BOST learning-goal prompt: "Bugun [topic] haqida nimani bilmoqchisiz?" — but the student reads it passively. There is no input field; it is just rendered text. The recon confirms preview is currently read-only across all subjects.
  - The goal is stored nowhere and "resurfaced in Reflection" per the prompt spec — but if it was never captured, the Reflection phase has nothing to resurface. This is a broken contract between Preview and Reflection.
- **HOW:**
  - `server/template/perfect_homework.html` — in the Preview phase render logic, after the last panel is shown, inject a small input element (one-line text field + "Saqlash" button) immediately below the BOST prompt block. Store the value in `__sessionLog` under key `bost_goal`.
  - `server/prompts/runtime/reflection-coach.md` — add one instruction: "If `session.bost_goal` is present, open the reflection by echoing it back: 'Dars boshida Siz [bost_goal] bilmoqchi edingiz. Bugun nimani kashf ettingiz?'"
  - No schema change needed — `__sessionLog` is a client-side array; `bost_goal` is a new key in the existing log object.
- **WHAT (after):**
  - Preview ends with one 15-second interaction: student types their learning goal.
  - Reflection coach opens with a personalized callback: "You said you wanted to learn X — did you?"
  - The cycle gains a meaningful bookend that costs < 20 seconds of student time.
- **Cost estimate:** S (4–6 hours — HTML input element + sessionLog write + reflection-coach prompt patch + test)
- **Targets complaint:** 1, 2

---

## P4. Add a "Sodda so'zlar" toggle to preview panels rendered in the runtime

- **WHY:**
  - Every well-structured preview prompt (confirmed in math-algebra/preview-hard.md and history/preview.md) mandates two-layer explanation: "Qatlam 1 — Rasmiy izoh" (formal) and "Qatlam 2 — Sodda so'zlar" (plain). The LLM generates both. But the runtime renders them as flat text — both layers appear in sequence with no visual distinction, making the panel feel like a wall of text (raw / boring).
  - The content already exists; the UX is just not exposing it as designed.
- **HOW:**
  - `content_json` panel blocks already have `type: "p"` for both layers. Add a convention: the first `p` block after the layer-2 separator phrase "Sodda so'zlar bilan:" gets tagged `"layer": 2` by the injector (or by prompting the LLM to emit `{"type": "p", "layer": 2, "text": "..."}`).
  - Alternatively (simpler, no schema change): the prompts already emit "Sodda so'zlar bilan:" as a literal phrase — the runtime JS can detect this phrase and apply `.panel-plain-layer` CSS class to the block that follows, initially collapsed with a "Sodda so'zlar bilan ko'rish" toggle button.
  - `server/template/perfect_homework.html` — add ~10 lines of CSS for `.panel-plain-layer { display:none }` + `.panel-plain-toggle` button, and ~8 lines of JS to toggle.
  - No schema freeze violation — purely presentational, no new content_json keys required.
- **WHAT (after):**
  - Panel renders the formal explanation first. Below it: a small "Sodda so'zlar bilan ko'rish" pill button. Tap → the plain-language layer slides in.
  - Student chooses depth. The formal layer doesn't compete visually with the plain layer.
  - Panel no longer looks like a wall of undifferentiated text.
- **Cost estimate:** XS (1–2 hours — CSS + JS toggle + phrase-detection heuristic, no backend needed)
- **Targets complaint:** 2

---

## P5. Add a "Flashcard self-grade" tap to the flashcard flip (known / not known)

- **WHY:**
  - Flashcard phase is currently: tap to flip (front→back), swipe to advance. There is no correctness signal. Student does not declare whether they knew the answer. The flip animation is the entire interaction.
  - Every spaced-repetition system (Anki, Duolingo, Quizlet) shows at minimum a binary self-grade after reveal. Without it, the session log cannot distinguish a student who knew every card from one who guessed on all of them.
  - Engagement audit confirms: "No correctness signal" at the flashcard phase. It is the only graded phase in the cycle with zero graded output.
- **HOW:**
  - `server/template/perfect_homework.html` — after the flip animation completes (back face visible), show two tap targets: "Bildim" (green) / "Bilmadim" (red). Record `{cardId, known: true/false}` into `__sessionLog`.
  - No server call. Purely client-side. The log accumulates and is available to the reflection-coach prompt (which already reads `__sessionLog`).
  - The flashcard cluster badge (`.fc-turquoise`) can show a running count: "7/10 bildim" as the student progresses.
  - No new endpoint, no new Pydantic model, no schema change.
- **WHAT (after):**
  - Each flashcard has a 2-button self-grade after reveal.
  - The cluster badge shows real-time "N/Total known" count.
  - `__sessionLog` gains `flashcard_known_ratio` which reflection-coach can reference.
- **Cost estimate:** S (3–5 hours — flip event handler + two-button DOM + sessionLog entry + cluster badge update)
- **Targets complaint:** 1

---

## P6. Create english/flow.md — close the spec gap that is causing the English cycle to drift

- **WHY:**
  - `server/prompts/english/flow.md` does not exist (confirmed by Glob: no matches). English is the only subject with no flow.md. The 9-phase sequence is only derivable from `instruction.md`. This means every future English prompt or phase addition has no authoritative spec to reference.
  - English is also the subject most likely to have content-quality problems — it is the one subject where the LLM generates content in a language it models well but where the *Uzbek scaffolding around it* has no grammar gate.
  - The absence creates drift: what instruction.md says vs. what the runtime does can silently diverge with no way to detect it.
- **HOW:**
  - Create `server/prompts/english/flow.md` modeled on `server/prompts/math-algebra/flow.md`. Derive the 9 phases from instruction.md (phases are already enumerated there). Add the Reading phase entry (unique to English) with its position in the sequence.
  - This is a documentation fix, not a code fix — but it unblocks any future English interactivity or content-quality work by giving it a spec anchor.
  - No schema change, no code change.
- **WHAT (after):**
  - English has a canonical flow.md matching the other 6 subjects.
  - Future agents can reference it without re-deriving from instruction.md.
  - The "Reading" phase has an explicit slot in the documented flow.
- **Cost estimate:** XS (1–2 hours — copy math flow.md structure, populate from instruction.md, review)
- **Targets complaint:** 2

---

## P7. Add a Uzbek grammar self-check instruction to every subject instruction.md

- **WHY:**
  - Zero Uzbek grammar gate exists between LLM output and student-facing text. This is confirmed across all 7 subjects and all content surfaces (preview panels, flashcards, memory-sprint items, game-break items, boss questions, reflection coach). The recon is explicit: "No subject prompt explicitly addresses Uzbek grammar quality of the AI's own output."
  - The complaint is not about a missing service — it is about a missing instruction to the LLM. The cheapest fix is to tell the LLM what errors to avoid before it generates.
  - Common Uzbek LLM failure modes (which a targeted instruction can suppress): mixing Uzbek Latin and Cyrillic in the same output, using Russian loanwords where Uzbek equivalents exist, incorrect verb-final word order in embedded clauses, wrong case suffixes after consonant clusters, "Siz" + plural verb mismatch.
- **HOW:**
  - Add a `## Uzbek Grammar Quality Rules` section to each subject's `instruction.md` (7 files: `server/prompts/math-algebra/instruction.md`, `history/instruction.md`, `biology/instruction.md`, `physics/instruction.md`, `geometriya-g7-11/instruction.md`, `kimyo-g7-11/instruction.md`, `english/instruction.md`).
  - The section is 6–8 bullet rules, placed BEFORE the output schema section so it is in the LLM's active context during generation.
  - Specific rules to include:
    - Script consistency: output in Uzbek Latin only (`oʻ`, `gʻ` for OʻZb standard; no Cyrillic characters).
    - Verb-final: subordinate clauses end with `-b`, `-ib`, `-ib`, `-gan`, `-adigan` before the main verb — never invert.
    - "Siz" agreement: "Siz o'qidingiz" not "Siz o'qidi." — second-person plural verb form mandatory.
    - No Russian proxies where Uzbek exists: "ma'lumot" not "dannie", "dastur" not "programma", "hisoblash" not "vychislyat".
    - Noun case: `-ga` after vowels and voiced consonants, `-ka` after voiceless only when standard.
    - No code-switching: if a sentence starts in Uzbek, it ends in Uzbek.
  - This is a prompt-only change — no code, no schema, no backend.
- **WHAT (after):**
  - Every generation pass for every subject runs with an explicit 6-rule Uzbek grammar constraint.
  - LLM self-corrects before output rather than requiring a post-generation filter.
  - Rule violations become detectable in QA: Sigma or any reviewer can check output against the stated rules.
- **Cost estimate:** S (3–4 hours for all 7 files — mostly copy-paste with minor subject-specific adaptation)
- **Targets complaint:** 3

---

## P8. Add a lightweight post-generation Uzbek script/register check at the injector layer

- **WHY:**
  - Prompt instructions (P7) reduce LLM grammar errors but do not eliminate them — especially at high token counts where instruction-following degrades. The recon confirms the pipeline is: LLM output → `content_json` → injector → render, with no intermediate check.
  - A 5-rule regex check at the injector layer can catch the most egregious failures (Cyrillic characters in Uzbek-Latin content, "sen" pronoun leaking through, empty panel blocks) without requiring an additional LLM call or round-trip.
  - This is the only proposal that requires a new code function, but it is a pure addition with no schema impact.
- **HOW:**
  - `server/services/injector.py` — add a `_uzbek_quality_check(content: dict) -> list[str]` function called after content is deserialized but before substitution. Returns a list of warning strings (not exceptions — never block a student from their homework for a grammar check failure).
  - Rules (regex-only, < 30 LOC):
    1. Cyrillic characters in any `p`/`h2`/`quote` block text → warning: `"Cyrillic detected in panel N block M"`
    2. Literal string `"sen "` or `"sening "` (lowercase) in any block → warning: `"Informal 'sen' found in panel N"`
    3. Empty `text` field on a non-list block → warning: `"Empty block in panel N"`
    4. Panel count < 4 for any hard-mode subject → warning: `"Fewer than 4 panels generated"`
  - Warnings are logged via the existing `logging.warning()` path — they appear in server logs and can be monitored without student impact.
  - Future: a `/api/admin/content-quality` endpoint can surface the warnings for the builder UI. Out of scope for this proposal.
- **WHAT (after):**
  - Every homework generation pass produces a warning log line for any Uzbek quality failure.
  - "sen" leakage (a confirmed LLM failure mode based on the prompt rules) is immediately visible in logs.
  - Zero student impact on failure — warnings only, never blocks.
- **Cost estimate:** S (3–4 hours — `_uzbek_quality_check` function + integration point in injector + 2 tests)
- **Targets complaint:** 3

---

## Self-anticipated counters

- **P1** counter: "gbInitMM may reference a panel ID that doesn't exist in the HTML."
  Response: confirm `#gb-panel-mm` exists before merging; if absent, add a minimal panel clone of `#gb-panel-tm` (same card-flip UI pattern, ~20 lines HTML). Still S cost.

- **P2** counter: "Renaming the wc label could break i18n strings that reference `game.wc`."
  Response: `game.wc` is a new `labelKey` value in a JS object, not a DB column — find all references with Grep, update in one pass. Zero schema risk.

- **P3** counter: "If students skip typing the BOST goal, Reflection still has nothing."
  Response: Reflection-coach prompt already handles missing context gracefully — make the BOST input optional (`placeholder` not `required`). A skipped goal just means reflection opens normally, not that it crashes.

- **P4** counter: "The 'Sodda so'zlar bilan:' phrase detection is fragile — what if the LLM omits it?"
  Response: If the phrase is absent, the toggle simply doesn't appear and both layers render as-is (current behavior). No regression. The fix is purely additive.

- **P5** counter: "Self-grade is unreliable — students will just tap 'Bildim' on everything."
  Response: The data is informational, not gated. Reflection-coach can call out suspiciously high self-grades ("Barcha kartalarni bilganingiz ajoyib — keling birini tekshirib ko'raylik"). Accuracy is a v2 problem.

- **P6** counter: "Writing flow.md for English is documentation, not a feature — doesn't fix anything for the student today."
  Response: Correct — it is a foundation fix. It is cheap (XS) and unblocks every future English improvement. It should be bundled with P7 in the same PR.

- **P7** counter: "LLMs ignore long instruction lists — adding 8 rules won't actually help."
  Response: Targeted grammar rules in the system prompt context DO measurably reduce specific error classes (Cyrillic mixing, register slips) even if they don't eliminate all errors. P8 is the complementary catch-net for what P7 misses.

- **P8** counter: "Logging warnings nobody reads is useless."
  Response: Agreed as a long-term state — which is why the proposal explicitly calls out a future `/api/admin/content-quality` endpoint. The log is the minimum viable version; the monitoring surface can follow. A warning that is logged but unread is still better than a silent failure.

---

## My ranking (in order of impact-per-effort)

1. **P7** — 7 prompt files, 3–4 hours, immediately reduces Uzbek grammar errors at the generation source. Highest leverage per hour of any proposal.
2. **P1** — 1 routing line + panel confirm + 1 test, ~2–4 hours, resurrects a complete mechanic for history/biology/math students who have never seen it. Zero new infrastructure.
3. **P4** — XS cost (1–2 hours), pure CSS/JS toggle, makes preview content visually less raw instantly. No backend touch at all.
4. P5 — S cost, flashcard self-grade closes the only zero-output graded phase in the cycle.
5. P3 — S cost, closes the broken Preview→Reflection BOST contract.
6. P8 — S cost, grammar warning net complements P7 with zero student-facing risk.
7. P2 — S cost, label fix with pedagogical clarity gain.
8. P6 — XS cost, foundation hygiene; bundle with P7.
