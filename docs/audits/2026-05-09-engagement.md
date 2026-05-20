# Engagement + XP Audit — 2026-05-09

Agent D recon swarm. READ-ONLY. No edits, no Trello.

---

## TL;DR (6 bullets)

- XP already exists per-mechanic (TM, SF, RLC, TTT, MP, Final Boss) but is **cosmetic only** — no number is persisted to any DB column, no user-visible wallet survives page reload.
- The DB schema has zero XP-related columns. `phase_attempts`, `sessions`, `boss_sessions`, `final_reports` — none carry `xp_earned`.
- The `__sessionLog` accumulates per-phase correctness for AMR axis scoring on the results screen; XP is **not part of that log** — the two systems are fully disconnected.
- The boss completion already has the richest reward signal (stars 1–3, `outcome_xp` on the response, visual card); it just never writes to a ledger.
- The simplest high-impact addition: **add one new DB column (`sessions.boss_xp_earned INTEGER DEFAULT 0`) and write the boss `outcome_xp` there at defeat**. One new UI element on the results screen (`+N XP` line). No schema freeze risk, additive only.
- Second recommended mechanic: a **cycle-level "streak" counter** displayed on the results screen — count of consecutive homeworks where `boss_xp_earned > 0` (boss was defeated). Zero new logic per homework; one new column on `sessions`.

---

## Existing 6 game-break mechanics — implementation + UX status table

| Mechanic | Key server files | Runtime panel | When in cycle | XP as of today | UX quality |
|---|---|---|---|---|---|
| **TM** — Tile Match | `server/routes/ai.py:_check_answer_tile_match`; `server/services/injector.py:_serialize_tile_match` | `#gb-panel-tm` (l. ~2353) | Phase 4.7 game-breaks | `.gb-tm-xp-pill` display only, not persisted. Toast strings "Correct! +100 XP", "3-match streak! +50 XP" (i18n l. 9238–9239) | Good UX — but caret `^` renders as literal in algebra tiles (TM-01 open). Streak counter exists in `gbState.tm.streak` but never persists. |
| **SF** — Sentence Fill | `server/routes/ai.py:_check_answer_sentence_fill`; `server/services/injector.py` SF block | `#gb-panel-sf` (l. ~4484) | Phase 4.7 game-breaks | `#gb-sf-xp-pill` display only, not persisted | Solid. Mode-chip (word-bank vs free-recall) is clean. |
| **RLC** — Real-Life Challenge | `server/routes/ai.py:_check_answer_rlc`; `server/routes/ai.py` RLC session route | `#gb-panel-rlc` | Phase 6 real-life | `.rlc-xp` pill display, `rlcState.totalXp` from `resp.total_xp`, not persisted | Best-elaborated outcome UX — role badge + outcome label + XP pill. 300-XP rubric is server-authored. |
| **FB** — Flashback (Memory Sprint / Adaptive Quiz) | `server/routes/ai.py` AQ branch; MS is client-only graded | `#gb-panel-mb` (Memory Box) + AQ panel | Phase 4–4.5 sprint | `__sessionLog` score-only, no XP | AQ score goes into AMR log. Memory Sprint pure client-side score. Neither shows XP. |
| **TTT** — Tic Tac Toe | `server/routes/ai.py:_check_answer_ttt` / `_check_answer_ttt_session`; `server/schemas/content.py:TttConfig` | `#gb-panel-ttt` (l. ~8640) | Phase 4.7 game-breaks | `#gb-ttt-session-xp` display only. Server returns `session_xp`, `mastery_tier`, `duolingo_remediation` — none persisted. TTT is the most complete XP schema (5 configurable XP fields). | Very complete backend; display only. |
| **MP** — Memory Palace | `server/routes/ai.py:_check_answer_memory_palace`; `_mp_session_xp_display` docstring explicitly: "COSMETIC display-only, not persisted" | `#gb-panel-mp` (l. ~8707) | Phase 4.7 game-breaks | `#gb-mp-xp-pill` display only. Server comment (l. 1963): "once cross-session persistence lands, this helper will be replaced by an authoritative XP ledger write." Placeholder intent confirmed. | 4-step loci flow is rich UX. XP amount formula: `correct * 50 + outcome_bonus`. |

**Summary:** Every mechanic shows an XP number to the student. Zero mechanic writes that number to the DB. The server code itself (l. 1963–1966 in `ai.py`) explicitly documents this as v1 cosmetic placeholder pending "cross-session persistence."

---

## Current XP / reward state (quantified)

**What exists in the DB schema** (`server/db/migrations.py`):
- `sessions` table: `overall_score REAL`, `phase_scores TEXT` — no XP column.
- `phase_attempts` table: `score REAL`, `correct INTEGER` — no XP column.
- `boss_sessions` table: `hp`, `trials_left`, `status` — no XP column.
- `final_reports` table: `report_json TEXT` — XP could be stashed here but current `renderResults` JS does not read it.
- `session_metrics` table: `metrics_json TEXT` — same: catch-all JSON blob; XP could theoretically be written, but nothing writes it.

**What exists in the runtime:**
- 6 per-mechanic in-session XP pill/display elements (all in `#screen-game-breaks` / boss panel).
- `__sessionLog` array (l. 12193+) accumulates `{phase, id, correct, score}` entries for AMR axis computation. XP fields are absent.
- Boss result card (`#boss-result-xp`) renders `+{n} XP` from server `outcome_xp` response field.
- The results screen (`#screen-results`) shows AMR 2-axis scores + per-phase done/undone status. No XP summary line.

**Net:** XP is 100% ephemeral. Closing the tab discards all XP values. There is no persistent XP anywhere in the system.

---

## Reward-loop placement in 11-phase cycle

| Stage | Phase name | Current "good job" signal | Motivational gap |
|---|---|---|---|
| 1–2 | Preview | Gate-quote pill (cosmetic) | None — preview is info-only |
| 2.5–3 | Flashcards | Flip animation, cluster badge | No correctness signal |
| 4–4.5 | Memory Sprint / AQ | Green/red per-item feedback | Score goes into AMR but not displayed until Stage 8 |
| 4.7–5 | Game-breaks (TM/SF/TTT/MP) | Per-mechanic XP pill, outcome label | XP vanishes on advance |
| 6 | Real-Life Challenge | Role badge + outcome label + XP pill | Same — vanishes |
| 6.5–7 | Final Boss | Stars (1–3) + `outcome_xp` card | **Best signal in the system.** But also ephemeral. |
| 7.5–7.7 | Consolidation + Reflection | Next-button (recently fixed in #210) | Zero reward signal. Student sees a "you made it" screen with no explicit acknowledgment of effort quality. |
| 8 | Results (AMR screen) | Donut gauge + band pill + per-phase done/undone | No XP summary. Stars from boss not echoed here. |

**Gap:** The cycle begins with a gate-quote, ends with an AMR axis scorecard — but neither surface acknowledges the boss victory stars or accumulated XP. The student who defeats a Mythical boss (5000 XP, 3 stars) and the student who just clicked through see the same results screen.

---

## Anti-grind / anti-shortcut safeguards — present + missing

**Present:**
- TM, SF, TTT, RLC: all use **server-authoritative grading** via the `check-answer` endpoint. The client cannot fake a correct answer and receive XP credit — the server computes the outcome.
- MP: server-recomputes `is_correct` from the submitted placement map (l. 1984–1988). Not as strong as side-disjoint (tampered POST possible) but documented acceptable for cosmetic-only stakes.
- Final Boss: 3-star threshold requires `attempt_number == 1 AND hints_used == 0 AND hp_remaining >= 80%` — genuine quality gate, not just "boss finished."
- TTT: mercy-roll XP (`xp_mercy=10`, `mercy_chance=0.002`) means a losing student can earn trivially; it's low-value by design.

**Missing (if XP becomes persistent):**
- No rate-limiting on `check-answer` calls. A student could replay a TTT session repeatedly. The `_TTT_ATTEMPTS` in-memory dict provides per-session dedup but an in-memory dict resets on server restart.
- No minimum-time-on-phase guard. MP's 4-step flow can be fast-clicked; if XP is persisted a speed-runner could farm `_mp_session_xp_display` repeatedly. The only defense is the server-recompute of placements (which is tamper-visible but not spam-visible).
- Boss XP is gated by HP math — but `boss_sessions.hp` is writable via the turn-by-turn route. Without a nonce/sequence-ID the final-turn `done=True` with `hp_remaining=100` could be POST-fabricated for max XP.

---

## Frontend engagement-UI surface inventory

**Currently shown:**
- Per-mechanic XP pill in the game-break header (`.gb-tm-xp-pill`, `.gb-sf-xp-pill`, `.rlc-xp`, `.gb-ttt-session-xp`, `.gb-mp-xp-pill`) — shows "0 XP" at start, updates during play. All in `perfect_homework.html` around lines 2487, 4484, 8641, 8663, 8707.
- Boss result card: stars + `#boss-result-xp` line. The most polished end-of-mechanic reward surface in the system.
- AMR results screen (`#screen-results`): donut gauge + band pill + per-phase rows. No XP.

**Not shown anywhere:**
- Progress bar or level indicator outside a mechanic.
- Streak indicator (consecutive correct, consecutive boss defeats).
- Cycle-level XP total.
- Any persistent indicator that crosses session boundaries.

**Where a small UI element could fit with near-zero disruption:**
1. The `#screen-results` AMR card — a single line `+N XP earned this session` with the boss stars replayed below the donut. No layout change needed; the card already has a `.screen-results-phases` block for appending rows.
2. The flashcard cluster badge (`.fc-turquoise`, l. 420) — already a pill-shaped element; a streak counter could live here with purely cosmetic change.

---

## Proposed minimal XP system

### Mechanic 1 — Boss XP persistence (the one to build first)

**What it adds:** At boss defeat, write `outcome_xp` to a new `sessions.boss_xp_earned INTEGER DEFAULT 0` column. Echo it on the results screen below the AMR donut. Three words: "Boss defeated: +N XP."

**Scope:**
- `server/db/migrations.py`: add `ALTER TABLE sessions ADD COLUMN boss_xp_earned INTEGER NOT NULL DEFAULT 0;` (additive, safe online).
- `server/routes/ai.py` (~l. 1670): after writing `response["outcome_xp"]`, call `db.update_session_boss_xp(session_id, int(outcome_xp))` — 2-line addition.
- `server/db/session_metrics_repo.py` (or a new `sessions_repo.py`): one `UPDATE sessions SET boss_xp_earned = ? WHERE id = ?` helper — ~5 lines.
- `server/routes/ai.py` or results endpoint: return `boss_xp_earned` when loading results.
- `perfect_homework.html` (l. ~9110 `#screen-results`): one new `<div>` for the XP line — 3 lines HTML + 5 lines JS to populate it.

**Schema delta:** 1 column, 1 UPDATE, 1 SELECT. No migration script beyond `ALTER TABLE`.

**Complexity tax:** 4 files touched. Zero new endpoints. Zero new tables. Zero new Pydantic models. Backend change is 8–10 LOC. Frontend change is ~20 LOC. Test: 1 new test asserting `boss_xp_earned` is written when `done=True` on a final-boss turn.

**What it WON'T add:** No leaderboards. No friend comparison. No push notifications. No XP decay. No level-up system. No badge unlocks. The XP number is informational only — it does not gate any feature.

---

### Mechanic 2 — Cycle streak counter on the results screen (cosmetic, zero schema)

**What it adds:** Count how many consecutive sessions for the same `hw_id` have `boss_xp_earned > 0` (requires Mechanic 1). Display "Streak: N cycles" as a small pill on the results screen, same visual language as the existing `.screen-results-band` pill. Reset to 0 if `boss_xp_earned == 0` on the current session.

**Scope:**
- `server/routes/homework.py` or results route: `SELECT COUNT(*) FROM sessions WHERE homework_id = ? AND boss_xp_earned > 0 AND id <= ? ORDER BY started_at DESC` — the streak is the run-length of the most recent contiguous block. A CTE or Python loop over the last 20 rows is sufficient. ~10 lines.
- `perfect_homework.html` (`#screen-results`): one new pill element alongside `#results-band`. ~5 lines HTML + ~3 lines JS.

**Schema delta:** Zero. Reads `boss_xp_earned` added by Mechanic 1.

**Complexity tax:** 2 files. 10–15 LOC total. One new SQL query (no index needed for a single-homework look-up). Test: 1 new test asserting the streak count is correct for a fixture of 3 consecutive sessions, one break, two more.

**What it WON'T add:** No cross-student streaks. No social feature. No notification when streak breaks. Streak is per-homework not per-subject (student who does math every day but different homeworks will NOT see an inflated streak — this is intentional; PISA alignment requires topic mastery per task).

---

## Risks of over-complication (5 anti-patterns to avoid)

1. **XP wallet visible everywhere** — Showing a running XP total on every phase header creates a "farming loop" incentive. Students will optimize for XP, not learning. XP should appear only at boss completion and on the results screen.
2. **Level-up unlocks gating features** — Any "unlock X after Y XP" mechanic requires content moderation, edge-case handling, and a whole new auth layer. The app's value is knowledge delivery; gatekeeping creates friction without learning benefit.
3. **Leaderboards / friend comparisons** — Competitive ranking is catastrophically misaligned with PISA competency goals. It rewards fast test-pattern memorizers, not deep understanding. One student's parent mentioning their child's rank in a WhatsApp group will end the product's reputation.
4. **Per-mechanic XP that adds up to a "session total"** — TM + SF + TTT + MP + RLC all already show numbers. If these sum into a visible wallet the student will skip the game-breaks fastest (MP is slowest, TM is fastest) rather than engage. Boss XP as the single "meaningful" number is cleaner.
5. **XP for streaks inside a mechanic (not across homeworks)** — The TM i18n string already says "3-match streak! +50 XP". This is fine as cosmetic in-session feedback. But making that streak persist across sessions makes the tile-match farmable: reload the page, replay TM. The session boundary is the right XP gate.

---

## Files to touch (with line refs) — grouped by priority

**P0 — Mechanic 1 (Boss XP persistence):**
| File | Lines | Change |
|---|---|---|
| `server/db/migrations.py` | After l. 252 | `ALTER TABLE sessions ADD COLUMN boss_xp_earned INTEGER NOT NULL DEFAULT 0;` |
| `server/routes/ai.py` | l. 1672 (`response["outcome_xp"] = int(outcome_xp)`) | Add `await _write_boss_xp(req.session_id, int(outcome_xp))` call |
| `server/db/sessions_repo.py` (new ~5 lines) | new file | `async def write_boss_xp(session_id, xp)` helper |
| `server/template/perfect_homework.html` | l. ~9110 `#screen-results` DOM block | `<div id="results-boss-xp" style="display:none"></div>` + 5-line JS population |

**P1 — Mechanic 2 (Streak counter):**
| File | Lines | Change |
|---|---|---|
| `server/routes/homework.py` | Results/final-report GET path | Add streak SQL query, return in response |
| `server/template/perfect_homework.html` | l. ~9113 (`.screen-results-band` row) | Streak pill next to existing band pill |

**P2 — Tests:**
| File | Change |
|---|---|
| `tests/test_boss_xp_persistence.py` (new) | Assert `boss_xp_earned` written on `done=True` final-boss turn |
| `tests/test_session_streak.py` (new) | Assert streak count for consecutive/broken session fixtures |

---

## Constraint scoring (user's 5 criteria, 1–5 each)

| Criterion | Score | Justification |
|---|---|---|
| Interactive / gamified | 4/5 | Boss stars + visible XP line on results is a clean payoff moment; doesn't dilute the game-breaks which already do interactivity well |
| Simple, not over-complicated | 5/5 | 2 mechanics, 4 files, 1 new DB column, ~40 LOC total |
| Knowledge quality | 5/5 | Boss XP is gated by actual defeat conditions (HP, hints, attempt count); cannot be earned by clicking through |
| Phase cycle fit | 5/5 | Boss is the natural cycle-end; results screen is the natural "summary" moment — XP lives exactly where the cycle already concludes |
| PISA + real-world | 4/5 | Streak-per-homework rewards depth over breadth; boss stars map to Bloom levels; no arcade dopamine mechanic introduced |

---

## Open questions for user (3)

1. **Cross-session identity:** The current `sessions` table has no `student_id` — sessions are anonymous (token-in-URL). A streak counter requires linking sessions to the same student. Are you comfortable keying streak off the shared URL token, or is student identity out of scope for v1?

2. **Boss XP as the only persisted number:** Proposal intentionally excludes TM/SF/TTT/MP XP from persistence. If you want those to contribute, the simplest extension is `sessions.game_break_xp_earned INTEGER DEFAULT 0` written at game-break-phase completion — but this adds the farming risk noted above. Confirm exclusion or discuss scope.

3. **Results screen real-estate:** The `#screen-results` AMR card is already dense (donut gauge + band + per-phase rows + AMR axes). Should XP live on the results screen, or on a **new interstitial between boss and results** (stage 7.5→8 gap, currently "Reflection") that explicitly celebrates the boss defeat before the dry AMR analysis?
