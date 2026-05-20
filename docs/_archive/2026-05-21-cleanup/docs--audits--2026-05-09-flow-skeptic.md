# Flow Skeptic — Counter-Arguments — 2026-05-09

*(Agent C output. Pressure-tested B's slate against recon facts + spot-checked code/prompts.)*

---

## Verdict summary

| # | Proposal | Verdict | Conf. |
|---|---|---|---|
| P1 | Resurrect Memory Match | **Reject** (as proposed) — Modify path acceptable | H |
| P2 | Rename `wc` slot to "Why → How → What" | **Concede** | H |
| P3 | BOST goal as interactive micro-prompt | **Modify** | H |
| P4 | "Sodda so'zlar" CSS toggle | **Modify** | H |
| P5 | Flashcard self-grade (Bildim/Bilmadim) | **Concede** | M |
| P6 | Create `english/flow.md` | **Concede** | H |
| P7 | Uzbek grammar rules in instruction.md | **Modify** (don't ship alone) | H |
| P8 | Injector-layer regex grammar check | **Concede** (bundle with P7) | H |

Tally: 3 concede / 3 modify / 1 reject / 0 defer.

---

## P1. Resurrect Memory Match — REJECT (as proposed)

- **B's claim:** `gbInitMM` + `GB_MEMORY_MATCH` are dead code; one-line addition to `gbActiveGameOrder()` revives the mechanic at zero cost.
- **WHY this is wrong:**
  - Spot-check of `perfect_homework.html` lines 14121-14148: `gbMMRenderBoard()` writes to `#gb-tm-left` and `#gb-tm-right` — the **Tile Match panel's DOM nodes**. Memory Match has no panel of its own; it parasitises Tile Match's DOM.
  - `Grep gb-panel-mm`: zero matches. There is no orphaned panel HTML to "confirm." B underweights this — a clone of `gb-panel-tm` is non-trivial because TM's DOM IDs are hardcoded inside `gbInitMM` itself (`gb-tm-left`, `gb-tm-right`, `gb-mm-status`, `gb-mm-win-banner`).
  - Adding `mm` to the registry **with shared IDs** means: if both `tm` AND `mm` content are populated, two games render into one panel — a runtime collision, not a no-op.
  - The reason `mm` isn't routed today is almost certainly **deliberate disablement during the Tile Match consolidation**, not a bug. B doesn't ask why; that's the missing diligence.
- **HOW to verify:** `git log -S "id: 'mm'" --all -- server/template/perfect_homework.html` — look for the commit that removed it, read that commit's reasoning. Until done, do not re-add.
- **Safer alternative:** If the user actually wants Memory Match shipped: (a) build a real `#gb-panel-mm` panel, (b) refactor `gbMMRenderBoard` + `gbMMUpdateStatus` to use `mm`-prefixed IDs (~80 LOC change, not the "1 line" B claims), (c) add the routing entry, (d) add a sub-test that BOTH `tm` and `mm` content can populate without collision. Cost: M not S. **Or** delete `gbInitMM` + `GB_MEMORY_MATCH` as dead code (aligns with the master audit's "engine is heavier than features justify" theme).
- **My verdict: REJECT** the one-line proposal. The fix as B describes ships a runtime collision.

---

## P2. Rename `wc` slot label — CONCEDE

- **B's claim:** Slot 1 is labeled "Sentence Fill" but the mechanic is `GB_WHY_CHAIN`; rename to "Why → How → What."
- **WHY this is right:**
  - Confirmed in template line 12672: `id: 'wc' … label: 'Sentence Fill'`. Line 12682 ALSO has `label: 'Sentence Fill'` for `sf`. Two slots, identical label — straight-up bug.
  - Master audit P3 already endorses this; recon confirms the underlying GB_WHY_CHAIN constant is wired.
  - Schema-untouched, i18n-only, low blast radius.
- **HOW to verify the risk:** `Grep -r "game.wc"` for stale labelKey references. B's self-counter handles this.
- **Mitigations to add:** (1) Regression test must assert NO two slots return identical labels from `gbActiveGameLabels()`. (2) Boss-prompt fix (How→How→What → Why→How→What) needs its own answer-leak regression — boss prompts touch the security-cleared path.
- **My verdict: CONCEDE** with the two test additions above.

---

## P3. BOST interactive micro-prompt — MODIFY

- **B's claim:** Add a text input below the BOST prompt, store in `__sessionLog`, surface in reflection-coach.
- **WHY parts are wrong:**
  - **Spot-check: `__sessionLog` does NOT exist in the template.** `Grep "__sessionLog|sessionLog|session_log"` → 0 hits. B invented the storage substrate. Any "no schema change" claim collapses if the variable doesn't exist — you'd be introducing a new client-side state container with persistence questions of its own.
  - reflection-coach.md spot-check: it receives `student_reflection`, `homework_summary`, `performance` — there is **no** `session.bost_goal` slot. Wiring it requires a contract change to the runtime payload sent into the reflection prompt. B labels this "no schema change"; technically true (content_json is untouched) but the **runtime AI-context contract IS changed**.
  - Pedagogically sound, but the cost is M not S once you account for: introducing client-side state primitive + payload field on reflection invocation + ensuring the field survives page reload (or accepting it doesn't).
- **HOW to verify:** Search for any existing per-session client store (`window.NETS_CTX`? `localStorage`?). If a real one exists, pivot to it; do not invent `__sessionLog`.
- **Safer alternative:** Use `sessionStorage` (browser-native, survives reload-within-tab) keyed by homework ID. Skip the reflection-coach payload extension on V1 — instead, just inject the goal as visible text on the reflection screen ("Dars boshida Siz X bilmoqchi edingiz") via DOM, no AI prompt change needed. Adds the bookend, halves the surface area.
- **My verdict: MODIFY** — keep the input, drop the `__sessionLog` fiction, don't extend the AI prompt contract on V1.

---

## P4. "Sodda so'zlar" CSS toggle — MODIFY

- **B's claim:** Detect literal phrase "Sodda so'zlar bilan:" in panel `p` blocks; collapse + toggle.
- **WHY the heuristic is fragile:**
  - **Spot-check #1 (math-algebra/preview-hard.md line 31):** `"Sodda so'zlar bilan:"` — confirmed.
  - **Spot-check #2 (history/preview.md line 41):** `**Qatlam 2 — Sodda so'zlar:**` — different phrase (`Sodda so'zlar:` no `bilan`, wrapped in bold). B's heuristic misses history entirely.
  - **Spot-check #3 (rendered content_json line 10227 in template demo):** the layer-2 text appears AS `<strong>Sodda so'zlar bilan:</strong><br>...` **inside the same `p` block** as the formal explanation, not as a separate following block. So "tag the block AFTER the separator" doesn't work — there's no separating block boundary. B describes a structure that does not exist in real content_json.
  - The "no-op-if-phrase-missing" defense is true but masks the bigger issue: the heuristic fires on ~5 of 7 subjects and mis-fires on history's variant phrasing.
- **HOW to verify:** Render 10 sample homeworks and grep for both `"Sodda so'zlar bilan:"` and `"Sodda so'zlar:"`; count separate-`p`-block vs same-block placement.
- **Safer alternative:** Two paths, pick one:
  - (a) **Prompt-side fix:** standardise all 7 subject preview prompts to emit layer 2 as its own `p` block with a stable marker (e.g., `{type: "p", layer: 2, text: "..."}`). Schema-additive (allowed), reliable, no fragile regex. Ships with prompt audit + sample re-generation.
  - (b) Drop P4 from this round. Wait until prompt standardisation lands, then revisit.
- **My verdict: MODIFY** — kill the regex heuristic, do prompt-side standardisation first, then ship the toggle on a stable marker.

---

## P5. Flashcard self-grade — CONCEDE (with one caveat)

- **B's claim:** Add Bildim / Bilmadim buttons after flip; record in session log.
- **WHY this is sound:**
  - Recon confirms zero correctness signal at flashcards today — the only graded phase with no graded output. Closing it is genuine pedagogical value.
  - Pure DOM addition, no LLM prompt or schema touch.
- **Underweighted risk:** B inherits the same `__sessionLog` fiction from P3. Same mitigation: route through `sessionStorage` or a real existing primitive. Don't invent state containers under deadline pressure.
- **Test must guard:** the buttons render only AFTER flip (otherwise the answer is leakable on the question side — micro-version of the answer-leak invariant).
- **My verdict: CONCEDE** with the storage-substrate fix from P3.

---

## P6. Create `english/flow.md` — CONCEDE

- **B's claim:** XS doc fix; English is the only subject without flow.md.
- **WHY this holds:** Glob confirms 0 matches. instruction.md exists; deriving flow.md from it is mechanical.
- **One-liner risk:** Don't let it become a 4-hour debate about Reading-phase semantics. Time-box to 90 minutes; if scope creeps, ship the skeleton anyway.
- **My verdict: CONCEDE** — bundle into the same PR as P7.

---

## P7. Uzbek grammar rules in instruction.md — MODIFY (don't ship alone)

- **B's claim:** Add 6-8 grammar bullets to all 7 instruction.md files; LLM self-corrects.
- **WHY this is partially right but oversold:**
  - Recon-confirmed: zero current grammar gate, zero post-filter. Adding rules is genuinely +EV.
  - **BUT — published research on instruction-following:** GPT-class models follow targeted constraints in system prompts at roughly **60-80% reliability** (degrades sharply at 4k+ token context, common in our preview prompts). Kimi K2.6 has not been independently benchmarked on Uzbek-specific morphology constraints; we are guessing the adherence rate.
  - That means: if today 100% of homeworks have some Uzbek error rate `R`, after P7 the rate is roughly `0.2-0.4 × R`. The unsuppressed 20-40% becomes the new bug surface — and worse, **harder to debug** because the prompt now claims the rules are enforced.
  - Spot-check `math-algebra/instruction.md` line 40: `[ ] Language is Uzbek, formal "Siz" throughout` already exists as a self-check item. So a rules section already exists in spirit; B is proposing more granular rules. Diminishing returns curve applies.
  - Specific rule risk: B's rule "verb-final: subordinate clauses end with `-b/-ib/-gan/-adigan`" is **incorrectly stated** — `-b` is non-standard, `-ib` is the converbial, `-gan` is the perfective participle, `-adigan` is the present-future participle. These are not interchangeable; an LLM given a malformed rule may "comply" by producing worse output. Have a native Uzbek linguist sign off on every rule before shipping.
- **HOW to verify the risk:** A/B test: generate 20 homeworks with old prompt, 20 with new; have a native speaker score Uzbek grammar 1-5 (blind). If P7 alone moves the mean by < 0.5 points, the proposal is theatre.
- **Safer alternative:** Ship P7 ONLY bundled with P8 (regex catch-net for the 20-40% residual). Solo P7 creates a false sense of safety. Also: have rules linguistically reviewed before merge — wrong rules are worse than no rules.
- **My verdict: MODIFY** — bundle with P8, linguist review on rules, A/B measurement before declaring victory.

---

## P8. Injector-layer regex check — CONCEDE (must bundle with P7)

- **B's claim:** Warning-only post-generation regex (Cyrillic / `sen ` / empty / panel count).
- **WHY this is right:** Catch-net for P7's residual; non-blocking; warnings-only is the right blast radius for V1.
- **Underweighted second-order risk:** "Warning that nobody reads is useless" — B addresses this with a future admin endpoint, but in the meantime, **logged warnings rot**. Better V1: emit warnings to a dedicated log channel that gets surfaced in the existing builder UI's homework-detail view (already exists per CLAUDE.md). Adds ~20 LOC; turns logging into a tight feedback loop instead of write-only.
- **Risk B missed:** Regex `r"sen\s"` will false-positive on legitimate Uzbek words containing the substring (`sentyabr`, `sensor`, `sensatsion`, `kosinus`, `eshik`, etc. — actually `sen` is rarely word-initial outside the pronoun, but boundary checks matter). Use word-boundary regex `\bsen(?:ing|ga|i)?\b` and case-sensitivity rules.
- **My verdict: CONCEDE** with: (a) bundle with P7, (b) word-boundary regex, (c) pipe to builder UI not just log.

---

## Cross-cutting risks B underweighted

- **Phantom storage primitive (`__sessionLog`).** Cited in P3 + P5 as if it exists. Spot-check: zero hits in template. Two proposals share this fiction; either both fix or both rework storage path.
- **"No schema change" claimed too easily.** P3 changes the AI-context contract, P4 implies a schema convention even if not a key. The frozen-schema invariant covers content_json, but the runtime AI-prompt contract is also a contract students depend on; treat both with similar discipline.
- **Prompt instructions ≠ enforcement.** P7 (and any future "tell the LLM not to do X") proposals need adherence numbers, not just intent. ~70% adherence is a useful baseline assumption; the unsuppressed tail is the bug.
- **Heuristics over content boundaries.** P4's phrase-detection assumes uniformity that the corpus doesn't have. When two of seven subjects deviate, prompt standardisation is the fix; regex over deviated content is the bandaid that breaks.
- **CONTRIBUTING regression-test rule applies to all 8.** Every shipped proposal must include its specific regression test. B states this for some (P1, P2, P8) but is silent on P3, P4, P5. That's three missing tests in B's slate.

---

## My counter-ranking

- **B's top-3:** (1) P7 grammar rules, (2) P1 Memory Match, (3) P4 Sodda so'zlar toggle.
- **My re-ranking of impact-per-effort:**
  1. **P2** (label rename) — H confidence, the only proposal where B's claim AND my spot-check both hold; ships in hours; touches a security-adjacent boss prompt as a bonus fix.
  2. **P5** (flashcard self-grade, w/ storage fix) — H confidence on pedagogy; only a real storage-primitive blocker.
  3. **P7+P8 BUNDLED** — high-leverage on grammar IF a native-speaker reviews the rules and P8 is the safety net. Don't ship P7 alone.
  4. P6 (english/flow.md) — H confidence, XS cost; cheap hygiene to bundle with the P7+P8 PR.
  5. P3 (BOST bookend, modified) — M confidence; pedagogy is real but `__sessionLog` fiction needs replacement.
  6. P4 (Sodda toggle, modified) — M confidence; heuristic version is fragile; do prompt standardisation first.

- **Anything B ranked LOW that I think is high-impact:** **P8** — B ranks 6th, calls it complementary. I think it's the **load-bearing safety net**; without it, P7 is a feel-good commit with no measurement.

- **Anything B ranked HIGH that I think is risky:** **P1** (B's #2) — re-adding `mm` as a one-liner ships a DOM collision. Either invest the M-cost real refactor or delete the dead code. The "1-line zero-cost win" framing is wrong.

