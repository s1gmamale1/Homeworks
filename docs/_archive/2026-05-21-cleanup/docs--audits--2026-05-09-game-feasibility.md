# Game Proposals — Feasibility Review — 2026-05-09

*(Agent C / Feasibility Realist. Pressure-tested A's slate against runtime + schema reality.)*

---

## Feasibility matrix

| # | Title | Schema | Cycle | Coupling | True cost | A's est. | Risk |
|---|---|---|---|---|---|---|---|
| G1 | Sorting Hat | additive | none | clean | M | accurate | med |
| G2 | Evidence Relay | additive | none | clean | M (high-end) | off-2x | med |
| G3 | Analogy Bridge | additive | none | clean | S | accurate | low |
| G4 | Number Line Sprint | additive | none | clean | S | accurate | low |
| G5 | Caption It | additive | none | shared-state (flashcard media refs) | M | accurate | med |
| G6 | Flashcard Confidence Tap | none | none | shared-DOM (`#fc-back`) | XS | accurate | low |
| G7 | Preview Curiosity Unlock | none | minor (preview gate) | shared-DOM + shared-state (`MS_QUESTIONS[0]`) | S | off-2x | med |
| G8 | Reflection Prompt Ladder | none | none | shared-DOM (textarea) + sessionStorage(BOST) | XS | accurate | low |
| G9 | Why Was I Wrong Tap | none | none | shared-DOM (memory-sprint render) | XS | accurate | low |
| G10 | Boss XP Persistence | **breaking-additive** (new column) | none | shared-state (boss done path) | S | accurate | low |
| G11 | Cycle Streak | depends G10 | none | shared-state | XS+G10 | accurate | low |
| G12 | Mastery Heatmap | depends G10 | minor (results screen redesign-adjacent) | shared-DOM | S | accurate | low |
| G13 | "You've Grown" Echo | depends G10 | none | shared-state | XS+G10 | accurate | low |
| G14 | Topic Revisit Nudge | none | none | shared-state (reads `phase_scores`) | S | off-2x | med |

---

## Where A's effort estimate is wrong (by ≥2x)

### G7. Preview Curiosity Unlock — A says XS, real cost is S

- **WHY:** A claims "reuses `memory_sprint[0]` (already injected)." Verified — `MS_QUESTIONS` is injected (l. 11954). BUT preview phase has its own state machine (`state.pageIndex` / `state.previewSeenPages`) and a phase-progress contract (`setPhaseRequired('preview', 1 + totalPages)` at l. 11289). Injecting a graded-style widget on the last panel forces:
  - Adding a new "panel slot" state (currently each panel is a swipe-page). Either it's a new pseudo-page (breaks `totalPages` math) or an overlay (breaks the swipe gesture handler at l. 10785).
  - `previewSeenPages` advance logic must NOT auto-tick on the curiosity panel — needs answer-tap before advance, otherwise students bypass with a swipe.
  - Plus tutor-context contract: the preview tutor sees a "panel context"; curiosity question is technically a memory-sprint item, so phase-context drift is real.
- **HOW to verify:** Grep `previewSeenPages` and `setPhaseProgress.*preview` in `perfect_homework.html` — there are 3 call sites, all of which need a "curiosity panel" exemption.
- **SAFER ALTERNATIVE:** (a) Run the curiosity widget AFTER preview phase ends, BEFORE flashcards begin — own screen, own state; cost stays S. (b) Or treat it as a non-blocking modal on the last panel that does NOT gate advance — drops to XS but defeats the "makes reading matter" goal.

### G2. Evidence Relay — A says M, real cost is M (high-end)

- **WHY:** Drag-to-rank UI is non-trivial on mobile (`touch-action`, scroll conflict, reordering animation). The existing Tile Match drag harness is pair-only and assumes side-disjoint drop-targets, not a vertical reorder list. Building rank UI = new gesture layer, not a Tile Match cousin. A's "4-arg builder editor" handwave underestimates the rank-editor complexity.
- **HOW to verify:** Grep `gb-panel-tm` drag handlers — they're `pointerdown`/`drop` based, not list-reorder.
- **SAFER ALTERNATIVE:** Ship as 3-tap pick-best (most convincing → second → third), one slot at a time, no drag. Same cognitive op, much cheaper UI. Drops to S.

### G14. Topic Revisit Nudge — A says XS, real cost is S

- **WHY:** A says "reads existing `phase_scores`." Verified — `sessions.phase_scores TEXT` exists (migrations.py l. 27). BUT `phase_scores` is currently never written by any active code path (grep returns one schema match only). Whoever shipped the column never wired writes. Cost includes auditing what triggers a write, OR adding the writes.
- **HOW to verify:** `grep -r "phase_scores" server/` returns ONE match — the schema definition. No INSERT/UPDATE references.
- **SAFER ALTERNATIVE:** Compute mastery client-side from current-session scoreboard before showing nudge — drops to XS but loses cross-session signal. Or wire the writes alongside G10 work.

---

## Hidden cross-proposal dependencies

- **G10 / G11 / G12 / G13 all depend on the SAME new `sessions.boss_xp_earned` column.** Cost is paid ONCE in G10, then G11/G13 are genuinely XS riders and G12 is genuinely S. A's per-proposal estimates are correct IF G10 ships first; shipping any of G11/G12/G13 without G10 = secret schema work each time.
- **G1 / G2 / G3 / G4 / G5 all add a new `gb_panel_*` ID + a new `gbActiveGameOrder()` slot** (l. 12666–12687). Each new game adds a slot index — currently slots 0–7 are taken (mp = 7). Adding 5 new games = slots 8–12. Risk: any test that asserts the slot count or the slot-index of an existing game would break. **Spot-check `tests/test_optional_games.py`** before shipping any new game.
- **G6 / G8 both lean on `sessionStorage` keys scoped to `${hwId}`.** No collision today, but there is no central key registry. If G6 ships with `fc_confidence_${hwId}_${cardId}` and G8 reads BOST goal under whatever P3 ships, the runtime now has 4+ ad-hoc sessionStorage namespaces with no discoverability. Recommend a 5-line `RUNTIME_STORAGE_KEYS` const alongside the first one shipped.
- **G5 (Caption It) shares state with the flashcard media pool** (`flashcards[].media`). If a homework has zero flashcards with `media`, G5 must hide the game OR the builder must enforce — neither is in A's WHAT. Edge case to spec.

---

## Schema-additive vs runtime-contract distinction

A's slate is mostly clean here, but two flags:

- **G10 IS a schema change.** A correctly admits this — `ALTER TABLE sessions ADD COLUMN boss_xp_earned`. Per CONTRACTS.md §1, `content_json` schema is frozen but DB-table schema is governed separately by `server/db/migrations.py`. The migration framework supports incremental ALTERs (l. 317–324 already adds 7 columns to `sessions`). Low risk, but it IS a real DB migration, not a "no schema change" claim.
- **G6 / G7 / G8 / G9 introduce new `sessionStorage` keys that ARE part of an undocumented runtime-state contract.** If a future "session resume" feature ships, every key collision becomes a bug. Not blocking, but flag.
- **None of the proposals touch the AI-prompt context contract** (`_shared_context_contract.md`) — verified. The tutor's `_redact_question_for_tutor` (tutor.py l. 752) is untouched by any proposal. Good.
- **G7 SECRETLY DOES touch the runtime AI-context contract** if it injects a memory-sprint question into a preview-phase tutor session. The preview tutor doesn't redact answer fields the same way; if `memory_sprint[0].correct` leaks into preview-tutor context, that's a bypass of the answer-leak guarantee. **Spec must say: G7 widget runs OUTSIDE the tutor's context window, or the preview tutor must extend its redaction list.**

---

## My feasibility ranking — top 5 by REAL impact-per-effort

1. **G6 — Flashcard Confidence Tap** — XS verified; `#fc-back` exists at l. 8332; pure DOM, zero backend, zero schema. Cheapest win on the slate.
2. **G9 — Why Was I Wrong Tap** — XS verified; `explain` field is in CONTRACTS.md and already injected via `MS_QUESTIONS` (l. 11954, used at l. 12121). Pure render-side; no state machine touched.
3. **G10 — Boss XP Persistence** — S verified; `outcome_xp` already computed (ai.py l. 1672) but discarded after response. One ALTER + one write at the `done=True` branch + one read on results screen. Unlocks G11/G13 for near-zero marginal cost.
4. **G8 — Reflection Prompt Ladder** — XS verified; reflection screen is plain DOM; no AI-contract change. Highest signal-to-effort once P3's BOST sessionStorage exists.
5. **G3 — Analogy Bridge** — S verified; smallest of the new-game proposals; reuses MC injector + checker patterns. Adds slot 8 to `gbActiveGameOrder()`. Cleanest path to a new game-break.

---

## Bottom 3 — feasibility deal-breakers (would refuse to ship without rework)

1. **G2 — Evidence Relay (drag-to-rank version)** — drag-rank UI is a 1-week swamp on mobile; ship the 3-tap pick-best variant or skip.
2. **G7 — Preview Curiosity Unlock (as specced on the LAST panel)** — couples to preview state machine + opens preview-tutor answer-leak vector. Acceptable only if redesigned as a between-phase screen.
3. **G14 — Topic Revisit Nudge (as XS)** — `phase_scores` column is unwired; "XS reads existing data" is false until somebody adds the writes. Acceptable at S, deceptive at XS.

---

## Verified runtime facts cross-checked against A's claims

- `#fc-back` exists at line 8332 → G6 claim accurate.
- `MS_QUESTIONS` const exists at line 11954, used at line 12121 → G7/G9 data-availability claims accurate.
- `gbActiveGameOrder()` at line 12666–12687 manages 8 slots (aq/wc/tm/pl/mb/ttt/sf/mp) → all new-game proposals must register here.
- `outcome_xp` is computed (ai.py:1672) but never persisted; no `boss_xp_earned` column exists today → G10 truly is the persistence gap.
- `sessions.phase_scores` column exists (migrations.py:27) but is never written → G14 hidden cost confirmed.
- `final_reports` table exists (migrations.py:211) and `server/services/final_report.py` is wired → there IS server-side results aggregation infrastructure for G11/G12/G13 to plug into. A's `homework.py` reference is wrong file (logic actually lives in `final_report.py` + a separate route), but the PATH exists.
- No proposal touches `_redact_question_for_tutor` (tutor.py:752) or the shared context contract → answer-leak invariants safe (except G7 caveat above).
