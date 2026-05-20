# Game Proposals — 2026-05-09 (Inventor's Slate)

*(For Agents B [pedagogy] + C [feasibility]. 15 proposals across 4 categories.)*

---

## Existing inventory recap (1-line each — what we already have)

- **Adaptive Quiz:** typed answer + optional notebook-photo; server-graded; used in math/physics/biology/kimyo/geometriya.
- **Tile Match:** drag-and-drop term-definition pairs; side-disjoint; server-graded.
- **Memory Match:** orphaned — JS exists, no panel HTML, parasitises Tile Match DOM; FLOW-DEBATE recommends delete.
- **Sentence Fill (sf):** drag/select missing word into blank; server-graded; used across most subjects.
- **Why-Chain (wc):** causal scaffold mechanic; mislabeled "Sentence Fill" in UI (FLOW-DEBATE P2 fix shipping).
- **Puzzle Lock:** step-by-step typed input per formula step; mandatory for geometriya/kimyo.
- **Memory Palace:** 4-step method-of-loci flow; server-graded recall MC; content-gated.
- **Tic Tac Toe:** tap-grid, server-authoritative grading; not in any current flow.md — low adoption.
- **Mystery Box:** tap-to-reveal mechanic; panel exists; interaction model unclear; no subject mandates it.
- **Real-Life Challenge:** typed free-response; 2-axis AMR rubric; Hard-only phase (not a game-break slot).
- **Final Boss:** HP overlay typed battle; stars 1–3; richest reward signal in cycle.

---

## Cat 1 — Game-break replacements / additions

### G1. Sorting Hat (Tartiblash)

- **WHY:** Memory Sprint already covers MC/TF recall, but students have no mechanic that forces them to categorise multiple concepts simultaneously. Tile Match is pair-matching — not group-sorting. Classification thinking (Bloom L3) is absent from game-breaks.
- **HOW:** Student sees 6–8 concept cards floating on screen. Three labelled "buckets" (e.g., "Yadro", "Sitoplazma", "Membrana") appear at the bottom. Student drags each card into the correct bucket. Server validates the full submission at once (not card-by-card) — answer is all-or-nothing at bucket level, with partial-credit XP (50 % correct buckets = 50 % XP). Wrong cards shake; correct buckets seal. One retry permitted.
- **WHAT:** New `gb_sorting_hat` key in `content_json` (additive, `extra="allow"`): `{buckets: [{label, correct_item_ids}], items: [{id, text}]}`. New `_check_answer_sorting_hat` route branch in `ai.py`. Runtime: new `#gb-panel-sh` panel (~80 LOC HTML/CSS), ~100 LOC JS state machine. Builder: 4-arg editor matching TM/SF pattern.
- **Best phase fit:** game-breaks
- **Cheat-resistance check:** All-at-once server validation — the client cannot fake a full correct bucket layout without knowing the answer. Side-disjoint injector (bucket membership not sent to client before submission).
- **Targets complaint:** 1 (interactivity), 2 (boring — physical sorting feel vs passive reading)
- **Effort:** M

---

### G2. Evidence Relay (Dalil Zanjiri)

- **WHY:** Why-Chain covers causal logic but only in one direction (A→B). Science subjects (biology/chemistry/physics) require bidirectional reasoning: "what is the evidence FOR claim X?" Currently no mechanic tests this skill.
- **HOW:** Student sees a central claim (e.g., "Ferment reaksiyasi haroratga bog'liq"). Three cards below — each is a potential piece of evidence. Student ranks them 1–3 (most convincing → least) using drag-to-rank. Server checks the correct ranking from `answer_spec.ordered_ids`. If order is perfect: full XP. Top-2 correct: 60 % XP. Only top-1 correct: 30 % XP. A brief one-sentence rationale for the correct order is shown post-submit (from `explain` field).
- **WHAT:** New `gb_evidence_relay` key: `{claim: str, items: [{id, text, rank}], explain: str}`. New `_check_answer_evidence_relay` route. `#gb-panel-er` panel. 4-arg builder editor.
- **Best phase fit:** game-breaks (Hard tier); consolidation phase as optional self-check
- **Cheat-resistance check:** Ranked submission is compared server-side against stored rank order. No correct ordering is ever sent to the client (side-disjoint injector). Random item ordering each render prevents pattern memorisation.
- **Targets complaint:** 1 (interactivity), 2 (boring — active judgment vs passive reading)
- **Effort:** M

---

### G3. Analogy Bridge (O'xshashlik Ko'prigi)

- **WHY:** PISA reading literacy requires students to map concepts to novel contexts. No current game-break tests analogical transfer. This is the most predictive PISA skill gap in Uzbek schools.
- **HOW:** Student sees a known concept pair (A : B) and a partial analogy (C : ?). Four options for "?" are provided as tappable pills. On correct tap: a brief "correct, because…" explanation line slides in from the answer's `explain` field. On wrong tap: one retry with a subtle hint injected. Graded server-side via `answer_spec.correct` index.
- **WHAT:** Reuses `memory_sprint` MC shape almost exactly — new `gb_analogy` array with items `{prompt_pair, options, correct, explain}`. `#gb-panel-analogy` panel (~50 LOC HTML) + ~60 LOC JS state. Builder: trivial (same shape as AQ editor). **Smallest new schema in this slate.**
- **Best phase fit:** game-breaks; flashcards phase (as optional "analogy card" cluster)
- **Cheat-resistance check:** MC with server-graded correct index. Options randomised per render.
- **Targets complaint:** 2 (boring), PISA literacy (analogical transfer = PISA reading Level 4+)
- **Effort:** S

---

### G4. Number Line Sprint (Raqamlar Yo'li) — math/physics/kimyo only

- **WHY:** Current math game-breaks (AQ + Tile Match) require full equation answers. There is no low-stakes estimation game. Number sense and magnitude estimation are PISA mathematical literacy L2 skills; none of the current mechanics train them.
- **HOW:** Student sees a blank number line with two anchor values (e.g., 0 and 100). A target value appears ("Yer yuzidan troposfere qadar: ? km"). Student drags a marker to their estimate on the line. If within ±15 % of correct: full XP + "Ajoyib!" feedback. Within ±30 %: half XP + correct position revealed. Outside: 0 XP + correct position revealed with a one-line explanation. Time pressure: 20 s clock (runs down visually, no penalty for running out — the clock is engagement scaffolding, not a punishment).
- **WHAT:** New `gb_number_line` key: `{items: [{prompt, correct_value, unit, range_min, range_max, explain}]}`. Client-side grading acceptable here (no answer-leak risk — the correct value is a number, not domain knowledge). Inject `correct_value` client-side post-submit only. `#gb-panel-nl` panel (~70 LOC HTML with SVG line), ~80 LOC JS drag logic. Subject-gated at `gbActiveGameOrder`: only injected when `subject_family in ['math-algebra','physics','kimyo','geometriya']`.
- **Best phase fit:** game-breaks
- **Cheat-resistance check:** Continuous value submitted to server for logging; ±15 % window is set server-side (not client-hardcoded); value is never visible in the DOM before submission. Spamming is irrelevant — estimate is a single drag gesture, not a tapfarm.
- **Targets complaint:** 2 (boring — kinesthetic drag vs passive), PISA math L2 (estimation)
- **Effort:** S

---

### G5. Caption It (Sarlavha Ber)

- **WHY:** English and biology have diagram/image content. No mechanic forces students to produce language from an image. This directly targets PISA reading literacy: "integrating and interpreting" (Level 3-4). Existing mechanics are text-in, text-out.
- **HOW:** A diagram or SVG from the current homework's `flashcards[].media` is displayed. Below it: a text input. Student writes a one-sentence caption (in Uzbek/English depending on subject). AI grader (`answer-checker-language.md` for English; `answer-checker.md` with a new `caption` rubric for science subjects) returns 1–3 stars + a model caption. Stars map to XP (100/60/20).
- **WHAT:** New `gb_caption` key: `{items: [{media_ref: str (points to flashcard id), prompt_hint: str, model_answer: str}]}`. New `_check_answer_caption` route using existing AI grader pattern. `#gb-panel-cap` panel. Builder: image-picker from the homework's flashcard media pool.
- **Best phase fit:** game-breaks; consolidation (as optional image-annotation self-check)
- **Cheat-resistance check:** Free-text graded by AI — no pattern-matching shortcut. Rate-limited by existing AI route rate limiting.
- **Targets complaint:** 1 (interactivity — first image-production mechanic), 3 (English grammar — AI gives feedback on the student's Uzbek/English quality)
- **Effort:** M

---

## Cat 2 — Phase-internal interactivity

### G6. Flashcard Confidence Tap (Ishonch Tugmasi)

- **WHY:** FLOW-DEBATE P5 approved "Bildim/Bilmadim" as SHIP. This is the concrete design. Flashcard phase is the only graded-style phase with zero correctness signal; students flip and advance with no reflection.
- **HOW:** After the card flips to the back face, two pill buttons appear below: "Bildim" (green) and "Bilmadim" (red). Tap fires a `sessionStorage.setItem('fc_confidence_${hwId}_${cardId}', 'known'/'unknown')`. A cluster badge on the card stack updates in real-time: "7/10 bildim". On reaching the reflection screen, a static DOM line is injected: "Flashcard bo'limida 7/10 kartani bildingiz." No AI prompt change — FLOW-DEBATE confirmed DOM-only V1.
- **WHAT:** `perfect_homework.html` only — two new `<button>` elements inside `.fc-card-back` reveal block (~6 LOC HTML). ~30 LOC JS reading `sessionStorage`. Cluster badge already exists (`.fc-turquoise` l. 420); piggyback it. Reflection screen: 1 `<p>` element with JS population (~8 LOC). Zero backend change. Zero schema change.
- **Best phase fit:** flashcards (buttons), reflection (echo line)
- **Cheat-resistance check:** Self-grade is not externally validated — it's for the student's own reflection loop, not for XP/grading. No farming incentive.
- **Targets complaint:** 1 (interactivity — first correctness signal on flashcards)
- **Effort:** XS

---

### G7. Preview Curiosity Unlock

- **WHY:** Preview panels are purely read-only (swipe to advance). Students have no reason to read carefully — they can swipe through all 5 panels in 5 seconds. There is zero penalty and zero signal for skipping.
- **HOW:** On the last preview panel, a single "Qiziqarli savol" (Curious Question) appears — a 1-sentence open MC drawn from `memory_sprint[0]` (the easiest item). Student taps an answer. If correct: a short "Bilasiz-ku!" celebration + smooth transition to flashcards. If wrong: the correct answer is revealed, one sentence of explanation, then the same smooth transition. Either way, the flow continues. The question is NOT graded toward AMR score. It is purely engagement scaffolding — a warm-up that signals "reading matters."
- **WHAT:** Runtime-only change: at preview `pageIndex == totalPages - 1`, inject a "curiosity question" widget using `memory_sprint[0]` (already injected). ~40 LOC JS to detect last panel + render the question. Zero schema change — reuses existing `memory_sprint` array. One new i18n key (`preview.curiosity_prompt`).
- **Best phase fit:** preview (last panel only)
- **Cheat-resistance check:** Not graded; no XP attached. Cannot be farmed.
- **Targets complaint:** 2 (boring — makes the last preview panel active)
- **Effort:** XS

---

### G8. Reflection Prompt Ladder

- **WHY:** Reflection phase is a free-text input with no scaffolding. Students write "yaxshi edi" (it was good) and submit. The reflection-coach prompt is told to produce personalised coaching — but has nothing meaningful to personalise on. FLOW-DEBATE confirmed the BOST-goal echo (P3) as SHIP MODIFIED. This extends it with a second scaffolding layer without touching the AI contract.
- **HOW:** Replace the blank reflection textarea with a 3-rung ladder. Rung 1 auto-populated from the BOST goal (P3's sessionStorage value). Rung 2: "Bugun eng qiyin bo'lgan narsa:" (a pre-filled label, student fills in the blank — a short 1-line input). Rung 3: "Keyingi safar sinab ko'raman:" (student fills in 1 line). These 3 lines are concatenated into the textarea payload before submission — the reflection-coach receives a structured 3-line prompt instead of "yaxshi edi." No AI contract change; same endpoint; richer input.
- **WHAT:** `perfect_homework.html` reflection screen only. Replace one `<textarea>` with a 3-rung scaffold widget (~20 LOC HTML). ~15 LOC JS to concatenate before submit. Zero backend change.
- **Best phase fit:** reflection
- **Cheat-resistance check:** Free text — not graded, no XP. No farming vector.
- **Targets complaint:** 1 (interactivity — reflection becomes structured), 2 (boring — the ladder gives students language to articulate difficulty)
- **Effort:** XS

---

### G9. Memory-Sprint "Why Was I Wrong?" Tap

- **WHY:** Memory Sprint (MC/TF/YNNG) shows green/red per-item but the `explain` field is never surfaced in the current runtime. Students learn they were wrong but not why. The data is already in `content_json.memory_sprint[].explain`.
- **HOW:** After a wrong tap, the correct answer highlight appears AND a small "Nima uchun?" pill appears below the item. Tapping it expands a one-sentence `explain` text inline (same collapsed-expansion pattern from Design Patterns catalog). Correct answers get no pill — no interruption for right answers. Expand is purely cosmetic (no state machine change needed; `explain` is already in the injected JS constant).
- **WHAT:** `perfect_homework.html` memory-sprint section only. On wrong-answer render path (~l. 5200 area), inject the pill + hidden `<span>` with `explain` text. ~15 LOC HTML + ~10 LOC JS. Zero backend change. Zero schema change (`explain` field already exists in CONTRACTS.md).
- **Best phase fit:** memory-sprint
- **Cheat-resistance check:** No interaction required for the tap — it's a content-reveal, not a graded action. No farming vector.
- **Targets complaint:** 2 (boring — makes memory sprint a learning surface, not just a score surface)
- **Effort:** XS

---

## Cat 3 — Cycle-level reward / micro-XP (max 2)

### G10. Boss XP Persistence (the one that matters)

- **WHY:** XP exists cosmetically in every mechanic but nothing survives page reload. Engagement audit confirmed: the simplest, highest-impact fix is persisting boss `outcome_xp` — already server-computed, already a quality-gated number (requires HP ≥ 80 %, no hints, first attempt for max stars). This is the ONLY cycle-level number worth persisting for v1.
- **HOW:** Add `sessions.boss_xp_earned INTEGER DEFAULT 0`. At boss defeat (`done=True`): write `outcome_xp` to this column. On results screen: one new line below the AMR donut — "Boss mag'lub etildi: +{N} XP" (only shown if `> 0`). No running XP wallet visible anywhere else in the cycle.
- **WHAT:** `server/db/migrations.py` (1 line `ALTER TABLE`). `server/routes/ai.py` l. 1672 (2-line write call). New `server/db/sessions_repo.py` helper (~5 LOC). `perfect_homework.html` `#screen-results` (~8 LOC). 2 new tests. Total: ~40 LOC. Engagement audit already confirmed exact line numbers.
- **Best phase fit:** final-boss (write) + results screen (display)
- **Cheat-resistance check:** Boss XP is gated by HP math on the server. `boss_sessions.hp` sequence requires the full fight — no shortcut to `done=True` with fake HP without a nonce. Engagement audit noted this gap; a session nonce is a v2 hardening, acceptable for v1 at non-monetary stakes.
- **Targets complaint:** none (pure new feature — closes the persistence gap the server code itself documents as "v1 cosmetic placeholder")
- **Effort:** S

---

### G11. Cycle Streak Counter (Davomiylik)

- **WHY:** Students need a personal growth signal that crosses session boundaries without comparing to others. A per-homework streak ("you've defeated this boss N times in a row") rewards mastery depth over breadth — directly PISA-aligned.
- **HOW:** Count consecutive sessions for the same `homework_id` where `boss_xp_earned > 0`. Display "Davomiylik: N" as a small pill on the results screen next to the existing `.screen-results-band` pill. Streak resets to 0 when `boss_xp_earned == 0`. No social comparison — this number is private to the session URL (token-in-URL auth means only the student with the link sees their own streak).
- **WHAT:** Depends on G10 (needs `boss_xp_earned` column). `server/routes/homework.py` results GET path: 1 SQL CTE (~10 LOC). `perfect_homework.html` results screen: 1 pill element + ~5 LOC JS. 1 new test (fixture of 3-break-2 consecutive sessions). Total: ~20 LOC beyond G10.
- **Best phase fit:** results screen
- **Cheat-resistance check:** Streak is server-computed from DB column written only at boss defeat. Client cannot influence it.
- **Targets complaint:** none (pure persistence / cross-session growth signal)
- **Effort:** XS (requires G10 first)

---

## Cat 4 — Cross-session / persistence (no social)

### G12. Mastery Heatmap Tile (Bilim Xaritasi)

- **WHY:** The results screen shows AMR scores for the CURRENT session only. Students have no sense of which topics they've mastered over time vs. which they keep struggling with. No "you've grown" signal exists.
- **HOW:** On the results screen, below the AMR donut, a row of small coloured squares — one per previous session on this homework (max 8 shown). Square colour: green (boss defeated, `boss_xp_earned > 0`), amber (completed, no boss), grey (not done). No numbers, no names, no comparisons. Just a visual "your journey" strip. On hover/tap: the session date is shown (not the score — date only, no ranking temptation).
- **WHAT:** `server/routes/homework.py`: query last 8 `sessions` rows for this `hw_id` with `boss_xp_earned` and `created_at` (~8 LOC SQL). Pass as JSON to results screen. `perfect_homework.html`: ~20 LOC HTML + ~15 LOC JS to render squares. Depends on G10 for `boss_xp_earned`.
- **Best phase fit:** results screen
- **Cheat-resistance check:** Read-only display. Server-sourced data only. No clickable interaction that produces XP.
- **Targets complaint:** none (pure persistence / growth signal)
- **Effort:** S (requires G10 first)

---

### G13. "You've Grown" Phrase Echo

- **WHY:** No phase acknowledges longitudinal improvement. The cycle ends with a dry AMR scorecard. Students who improve across sessions see nothing different on the results screen.
- **HOW:** If `boss_xp_earned` for this session is ≥ previous session's `boss_xp_earned` by ≥ 10 %, add one personalised sentence to the results screen: "O'tgan safarga nisbatan yaxshilandingiz!" (compared to your OWN previous score — not to any other student). If first session: no message. If declined: no message (no shaming). The phrase is a single static i18n string with a conditional render — no AI call needed.
- **WHAT:** `server/routes/homework.py` results path: compare current vs previous `boss_xp_earned` for same `hw_id` (~5 LOC SQL). Return a boolean `improved: true/false`. `perfect_homework.html`: 1 conditional `<p>` element (~5 LOC JS). Depends on G10.
- **Best phase fit:** results screen
- **Cheat-resistance check:** Read-only display; boolean computed server-side.
- **Targets complaint:** none (pure cross-session "you've grown" signal)
- **Effort:** XS (requires G10 first)

---

### G14. Topic Revisit Nudge (Takrorlash Eslatmasi)

- **WHY:** Students do a homework once and move on regardless of score. No mechanic surfaces "you got this wrong last time — try again." Without a revisit prompt, the spaced-repetition value of the homework is zero.
- **HOW:** On the results screen, if `phase_scores` for `memory-sprint` OR `game-breaks` is < 60 % for this session AND a prior session exists with the same result pattern: show a small pill "Ushbu mavzuni qayta ko'ring" (suggested, not mandatory — a pill tap just closes the results screen and reopens the homework from the beginning). This is a nudge, not a gate. The pill appears once, disappears on tap or dismiss.
- **WHAT:** `server/routes/homework.py`: check `phase_scores` JSON field for current session (~5 LOC). `perfect_homework.html`: 1 conditional pill element (~10 LOC JS). Zero new DB column (reads existing `phase_scores`). Zero AI call.
- **Best phase fit:** results screen (as a post-completion nudge)
- **Cheat-resistance check:** Read-only nudge; no XP attached; no gate on future sessions.
- **Targets complaint:** 2 (boring → makes the cycle feel responsive to actual performance)
- **Effort:** XS

---

## Self-anticipated criticism

- **G1 (Sorting Hat):** "Too similar to Tile Match" — counter: Tile Match is 1:1 pair matching; Sorting Hat is N:bucket grouping. Different cognitive operation (classification vs association).
- **G2 (Evidence Relay):** "Ranking is subjective — what's the 'correct' ranking?" — counter: for science claims, evidence hierarchy is defined by experimental primacy; builder author sets canonical rank; `explain` field shows reasoning post-submit.
- **G3 (Analogy Bridge):** "PISA transfer is hard to generate reliably from LLM" — counter: builder author writes the analogy pairs manually; not LLM-generated at runtime.
- **G4 (Number Line Sprint):** "SVG drag on mobile is notoriously finicky" — counter: use a `<input type="range">` slider instead of raw SVG drag; same estimation mechanic, native mobile UX.
- **G5 (Caption It):** "AI grader latency adds friction mid-game-break" — counter: show a loading state matching the existing AQ pattern; grader call is already the norm in this system.
- **G6 (Flashcard Confidence Tap):** "Self-grade is unreliable — students will always tap Bildim" — counter: it's a reflection tool, not a grade; the cycle already has server-graded phases; this adds metacognitive scaffolding, not a score.
- **G7 (Preview Curiosity Unlock):** "Students will just guess to skip" — counter: correct. The mechanic is a warm-up, not a gate; even guessing requires reading the question, which is the goal.
- **G8 (Reflection Prompt Ladder):** "3-rung ladder may feel bureaucratic on mobile" — counter: rungs 2 and 3 are one-liners; total word count expectation is lower than current blank textarea; the scaffold reduces friction, not adds it.
- **G9 (Why Was I Wrong Tap):** "Explain field quality varies — may be empty or LLM-generic" — counter: already flagged in CONTRACTS.md as optional; render only if `explain.trim().length > 0`; empty = no pill.
- **G10 (Boss XP Persistence):** "Boss nonce gap means fabricated HP is possible" — counter: at non-monetary stakes, this is v2 hardening; engagement audit explicitly calls it out and defers it.
- **G11 (Cycle Streak):** "Token-in-URL auth means anyone with the link can fake a streak" — counter: the link is shared 1:1 (student's own URL); the streak is not visible to others; social-gaming incentive is absent.
- **G12 (Mastery Heatmap):** "8-session window is arbitrary" — counter: 8 = two school weeks at 1 homework/day; adjustable constant; the cap prevents the strip from overflowing narrow mobile screens.
- **G13 ("You've Grown" Echo):** "10 % threshold is arbitrary" — counter: configurable server constant; set conservatively to avoid false-positive congratulations on noise.
- **G14 (Revisit Nudge):** "Students will dismiss it every time" — counter: that's fine; a nudge is a nudge, not a gate. Even one-in-five students who follow it recaptures pedagogical value.

---

## My ranking by impact-per-effort

1. **G6** — Flashcard Confidence Tap: XS effort, fixes the only graded-style phase with zero signal. Immediate interactivity win.
2. **G10** — Boss XP Persistence: S effort, closes the persistence gap the server code itself documents. Unlocks G11/G12/G13.
3. **G9** — Memory-Sprint "Why Was I Wrong?" Tap: XS effort, surfaces already-existing `explain` data. No schema, no backend.
4. **G3** — Analogy Bridge: S effort, directly targets PISA transfer gap, minimal new schema (reuses MC shape).
5. **G8** — Reflection Prompt Ladder: XS effort, richer AI input for free; makes reflection feel designed.
6. **G7** — Preview Curiosity Unlock: XS effort, reuses `memory_sprint[0]` data; makes last preview panel active at near-zero cost.
7. **G11** — Cycle Streak: XS effort (post G10), free cross-session growth signal.
8. **G13** — "You've Grown" Echo: XS (post G10), single conditional sentence; highest emotional impact per LOC.
9. **G14** — Revisit Nudge: XS, reads existing `phase_scores`; spaced-repetition alignment.
10. **G4** — Number Line Sprint: S effort, unique kinesthetic mechanic; strong math/physics/kimyo fit.
11. **G1** — Sorting Hat: M effort, classification mechanic gap is real but Tile Match partially covers it.
12. **G12** — Mastery Heatmap: S (post G10), compelling visual but results screen is already dense.
13. **G5** — Caption It: M effort, strong PISA alignment but adds AI grader latency to a game-break.
14. **G2** — Evidence Relay: M effort, strong science fit but ranking UI is non-trivial on mobile.
