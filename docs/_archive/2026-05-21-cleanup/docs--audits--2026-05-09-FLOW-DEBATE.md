# Homework Flow Debate — Synthesis — 2026-05-09

3-agent swarm (Recon → Reformer → Skeptic). Pure flow review focused on user complaints: lack of interactivity, boring/raw content, Uzbek grammar errors. **No code changed.**

Sub-docs: [recon](2026-05-09-flow-recon.md) · [reform](2026-05-09-flow-reform.md) · [skeptic](2026-05-09-flow-skeptic.md)

---

## TL;DR

- **8 proposals debated** → **3 ship as-is** · **3 ship modified** · **1 deferred** · **1 rejected**
- **Highest leverage:** label rename (P2) + flashcard self-grade (P5) + grammar bundle (P7+P8)
- **Surprising fact:** Memory Match is in the spec for 4 subjects but is **runtime-unreachable** (no panel HTML, parasitises Tile Match's DOM IDs)
- **Confirmed user pain:** zero Uzbek grammar gate exists between LLM and student. Anywhere.
- **Key rejection:** "resurrect Memory Match in 1 line" actually requires ~80 LOC + DOM refactor

---

## Current state — 4 facts that matter

- **Common backbone (all 7 subjects):** `preview → flashcards → memory-sprint → game-breaks → [maybe consolidation/real-life] → final-challenge → reflection`. Math has Easy/Hard branching (5/8 phases). History is always Hard (6 phases, no Real-Life because narrative IS content).
- **Game inventory mismatch:** 8 game slots in `gbActiveGameOrder()` (template line 12666). Memory Match (`mm`) is **specced** in flow.md for math/history/biology/physics but has **no routing entry** and **no panel HTML** (`#gb-panel-mm` = 0 grep hits).
- **Interactivity profile:** preview = read-only · flashcards = tap-flip (no correctness signal) · memory-sprint = MC/TF tap · game-breaks = varied (Adaptive Quiz/Tile Match/Sentence Fill) · real-life = typed · final-challenge = typed + boss · reflection = read-only. **Half the cycle is one-way.**
- **Uzbek surface:** every phase generates Uzbek. Zero post-generation grammar check. Zero "self-check Uzbek" rule in any of the 7 instruction.md files. The complaint is structurally correct.

---

## Issues — 5 that the swarm confirmed

1. **Mislabeled mechanic (P2 territory):** slots 1 (`wc`) and 6 (`sf`) both display "Sentence Fill" to students — but `wc` is the GB_WHY_CHAIN causal scaffold, not Sentence Fill. Two different mechanics, same label. Suppresses adoption + confuses students.
2. **Broken Preview→Reflection contract (P3 territory):** Preview ends with a BOST goal prompt ("Bugun … nimani bilmoqchisiz?") that the student reads but never answers. Reflection-coach is told to "resurface it" — it has nothing to resurface.
3. **Two-layer panel content collapsed visually (P4 territory):** preview prompts mandate "Qatlam 1 — Rasmiy izoh" + "Qatlam 2 — Sodda so'zlar" — but the runtime renders them as flat text, indistinguishable. Wall-of-text visual = "boring/raw" complaint, confirmed.
4. **Flashcard phase has zero correctness signal (P5 territory):** the only graded-style phase with no graded output. Student flips card and moves on; the cycle never knows if they knew it.
5. **English has no flow.md (P6 territory):** only subject without canonical flow spec. Every future English work re-derives from instruction.md. Drift risk = real.

---

## The 8 proposals — Reformer pitch vs. Skeptic counter vs. my verdict

### P1. Resurrect Memory Match — 🚫 REJECT as proposed

- **B (Why):** Memory Match has full JS, is specced for 4 subjects, runtime is silently dropping it. Free interactivity win.
- **B (How):** add 1 line to `gbActiveGameOrder()` (template ~line 12687) + confirm panel exists.
- **B (What):** 9th conditional in the routing fn. ~2-4 hrs.
- **C (counter):** spot-checked lines 14121-14148 — `gbInitMM` writes to `#gb-tm-left`/`#gb-tm-right` (Tile Match's DOM). MM has no panel of its own; it parasitises TM. Adding `mm` to the registry while both `tm` and `mm` content populate = **runtime collision, not no-op**. The mechanic was likely deliberately disabled during TM consolidation. Real fix: build `#gb-panel-mm` panel + refactor MM to use `mm`-prefixed IDs (~80 LOC) — or **delete the dead code** (aligns with "engine simplification" theme from yesterday's MASTER audit).
- **My verdict:** **REJECT** the 1-line version. Two paths forward: (a) deliberate medium-cost refactor IF you actually want MM live, or (b) delete `gbInitMM` + `GB_MEMORY_MATCH` constant as dead code. **Pick "delete" unless you have a pedagogical reason MM beats TM/MP for a specific phase.**

### P2. Rename `wc` slot label "Sentence Fill" → "Why → How → What" — ✅ SHIP

- **B (Why):** `wc` and `sf` both display "Sentence Fill" — bug. The mechanic IS Why-Chain.
- **B (How):** template line 12672 label change + new i18n key `game.whw` (uz/ru/en) + add "Why → How → What" as named option in subject `game-breaks.md` files + fix boss prompts (How→How→What → Why→How→What).
- **B (What):** student sees correct label; mechanic legible; boss opens with proper Why-tier.
- **C (counter):** concedes. Adds two test requirements: (1) regression assert `gbActiveGameLabels()` returns no duplicate labels; (2) boss-prompt fix needs answer-leak regression (touches the security path).
- **My verdict:** **SHIP** with C's two test requirements. Cost S (3-5 hrs). Highest impact-per-hour in the slate.

### P3. BOST goal as interactive micro-prompt — 🛠️ SHIP MODIFIED

- **B (Why):** Preview ends with a BOST learning-goal prompt that students read passively. Reflection is told to surface it but nothing was captured.
- **B (How):** add input field below BOST → store in `__sessionLog` → reflection-coach echoes it back.
- **B (What):** 15-second interaction at end of Preview, personalized callback in Reflection.
- **C (counter):** **`__sessionLog` does not exist** (grep: 0 hits). B invented the storage. Reflection-coach prompt also has no `bost_goal` slot — wiring it changes the runtime AI-context contract. Real cost is M not S.
- **My verdict:** **SHIP MODIFIED** — keep the input idea, drop the `__sessionLog` fiction. Use `sessionStorage` keyed by homework ID. **V1 surfaces the goal as visible DOM text on the reflection screen, NOT through the AI prompt** ("Dars boshida Siz X bilmoqchi edingiz" injected as static text). Halves the surface area; no AI-contract change. Cost: S (4-6 hrs).

### P4. Sodda so'zlar CSS toggle — ⏳ DEFER

- **B (Why):** preview panels mandate two-layer (formal + plain) text but render flat. Wall-of-text problem.
- **B (How):** detect literal phrase "Sodda so'zlar bilan:" → apply collapse + toggle CSS class.
- **B (What):** XS fix, no backend, makes panels visibly less raw.
- **C (counter):** spot-check confirmed math uses "Sodda so'zlar bilan:" but **history uses "Qatlam 2 — Sodda so'zlar:"** (different phrase, no `bilan`, wrapped in bold). Worse: in real content_json, the layer-2 text is **inside the same `p` block** as layer 1 (same `<strong>` boundary). B's structure assumption is wrong — there's no separate block to tag. Heuristic mis-fires on history; structure mis-fires across the corpus.
- **My verdict:** **DEFER** — don't ship the regex heuristic. Instead, do prompt-side standardisation first: update all 7 preview prompts to emit Layer 2 as its own `p` block with a stable marker (`{type: "p", layer: 2, text: "..."}`). Schema-additive (allowed). Then the toggle ships on a stable marker, not regex. Two PRs: prompt-standardise (S) → toggle (XS). Together M.

### P5. Flashcard self-grade (Bildim/Bilmadim) — ✅ SHIP

- **B (Why):** flashcard phase is the only graded-style phase with zero correctness signal.
- **B (How):** two tap targets after flip + record `{cardId, known}` in session log + cluster badge shows `7/10 bildim`.
- **B (What):** binary self-grade per card; ratio surfaces to reflection-coach.
- **C (counter):** concedes pedagogy. Same `__sessionLog` fix from P3 applies (use `sessionStorage`). Test must guard buttons render only AFTER flip (otherwise micro answer-leak).
- **My verdict:** **SHIP** with C's two fixes (real storage primitive + post-flip-only test). Cost S (3-5 hrs).

### P6. Create `english/flow.md` — ✅ SHIP

- **B (Why):** English is the only subject without flow.md; instruction.md is the only spec; drift risk.
- **B (How):** copy math-algebra/flow.md structure + populate from existing english/instruction.md.
- **B (What):** 7-of-7 subjects have canonical flow spec.
- **C (counter):** concedes. One-liner risk: don't let it become a 4-hr Reading-phase semantics debate. Time-box 90 min.
- **My verdict:** **SHIP** as XS hygiene fix. Bundle with P7+P8 in a single grammar-quality PR.

### P7. Uzbek grammar rules in instruction.md — 🛠️ SHIP MODIFIED (don't ship alone)

- **B (Why):** zero grammar gate exists. Cheapest fix: tell the LLM what NOT to do at generation time.
- **B (How):** add `## Uzbek Grammar Quality Rules` section to all 7 instruction.md files (6-8 bullet rules: script consistency, "Siz" agreement, no Russian proxies, verb-final order, etc.).
- **B (What):** LLM self-corrects before output.
- **C (counter):** real but oversold. Research: GPT-class models follow targeted system-prompt constraints at ~60-80%, **degrades sharply at 4k+ token context** (common in our preview prompts). Kimi K2.6 has zero published Uzbek-morphology benchmarks — we're guessing. After P7, residual error rate is 20-40% of current → **the new bug surface, harder to debug because the prompt now CLAIMS the rules are enforced**. Worse: B's specific rule "verb-final: subordinate clauses end with `-b/-ib/-gan/-adigan`" is **linguistically wrong** — these aren't interchangeable. Wrong rules are worse than no rules.
- **My verdict:** **SHIP MODIFIED** — (1) bundle with P8 (catch-net for residual), (2) **native Uzbek linguist signs off on every rule before merge**, (3) A/B test: 20 homeworks before, 20 after, blind native-speaker scoring. If P7 alone moves the mean by < 0.5 points, it's theatre.

### P8. Injector-layer regex grammar check — ✅ SHIP (must bundle with P7)

- **B (Why):** P7 reduces but doesn't eliminate errors. Regex catch-net at injector layer for the residual.
- **B (How):** `_uzbek_quality_check(content)` in `server/services/injector.py` — returns warning list (Cyrillic / "sen " / empty blocks / panel count). Logged via `logging.warning()`, never blocks student.
- **B (What):** every generation produces a warning trail; "sen" leaks become visible.
- **C (counter):** concedes the catch-net design. Two improvements: (1) `\bsen(?:ing|ga|i)?\b` word-boundary regex (B's `r"sen\s"` misses cases + can false-positive); (2) **pipe warnings to builder UI homework-detail view**, not just log — logged warnings rot. Adds ~20 LOC, turns logging into a tight feedback loop.
- **My verdict:** **SHIP** with C's word-boundary + builder-UI surfacing. Bundle with P7 + P6 in one "Uzbek quality" PR.

---

## Cross-cutting risks B underweighted (per Skeptic)

- **Phantom storage (`__sessionLog`)** — referenced in P3 + P5 as if it exists. It doesn't. Both fixes route through `sessionStorage`.
- **"No schema change" claimed too easily** — P3 changes the AI-context contract; P4 implies a schema convention. The frozen-schema invariant covers content_json, but the runtime AI-prompt contract is also a contract.
- **Prompt instructions ≠ enforcement** — P7-style "tell the LLM not to do X" needs measurement (A/B + adherence numbers), not just intent.
- **Missing regression tests** — B specifies tests for P1/P2/P8 but is silent on P3/P4/P5. Project rule (CONTRIBUTING.md) requires every fix ship a regression test.

---

## Final ship list (my synthesized PR plan)

**PR 1 — "Game-break clarity" (S, ~1 day)**
- P2 ship as-is + 2 test requirements (no duplicate labels, boss answer-leak regression)

**PR 2 — "Cycle bookends + signal" (M, ~2 days)**
- P3 modified (sessionStorage + DOM-only V1)
- P5 ship (with sessionStorage + post-flip-only test)

**PR 3 — "Uzbek quality bundle" (M, ~2-3 days)**
- P6 ship (english/flow.md)
- P7 modified (bundled, linguist-reviewed rules, A/B measurement plan)
- P8 ship (with word-boundary regex + builder-UI surfacing)

**Decision needed — Memory Match:**
- P1 — **decide between (a) M-cost real refactor or (b) delete the dead code**. Don't ship the 1-line version. Recommend (b) unless you have a pedagogical reason MM beats TM/MP.

**Deferred:**
- P4 — needs prompt-side standardisation PR FIRST (flatten Layer 2 to its own block); then the toggle ships on a stable marker.

**Total ship-now cost:** ~5-6 dev-days across 3 PRs.

---

## 3 open questions for you

1. **Memory Match decision** — refactor (medium-cost real fix) OR delete (~50 LOC removed, aligns with simplification)? Recommend delete unless you remember a specific pedagogical reason it earned a slot.
2. **Native Uzbek linguist availability** — P7's rules MUST be reviewed by someone who actually speaks the language before they go into 7 instruction.md files. Do you have someone, or should we ship a smaller, lower-risk rule set first (e.g., only the 3 rules we're 100% sure about: Latin script, "Siz" formal, no informal "sen")?
3. **A/B measurement appetite** — P7 needs blind-scored before/after to prove it works. Do we ship the rules now and measure later, or block the PR on the measurement plan? (My take: ship the smaller-rule version now without measurement; gate the full rule set on measurement.)
