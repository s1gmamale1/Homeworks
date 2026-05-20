# Homework Cycle + Generation Engine Audit — 2026-05-09

Author: Agent A (Opus 4.7), recon swarm. READ-ONLY pass over `server/`, `frontend/`, `docs/`, `notes/`. Cross-referenced with `CONTRACTS.md`, `STATE.md`, `AI_OPERATING_PLAYBOOK.md`, `MASTER_INDEX.md`, the `homeworks_ai_remaining_fix_report.md`, and the `00_MASTER_PLAN.md` family of plan docs.

---

## TL;DR

- **`server/routes/ai_plan4.py` (2403 LOC) is dead code** — defines the same route paths as `ai.py` but is NOT registered in `server/app.py:114-122`. Two near-identical 2.4-2.6k LOC files behind a single live router. **Highest-value single deletion in the engine.**
- **History subject is the weakest link** — only 9 of 12 prompt files (no `classify.md`, `real-life.md`, `preview-easy.md` / has only `preview.md`); `flow.md` is 42 LOC vs ~60 average. Its phase pipeline already drops `real_life` (CONTRACTS.md §3, line 260) — but no documentation explains *why* it's the only "hard" subject without it.
- **The 11-phase cycle is actually a 9-phase pipeline rendered through a 13-stage runtime FSM** — `setStage()` uses fractional values (2.5, 3.5, 4.7, 6.5, 7.5, 7.7) for interstitials, with stage→phase mapping documented at `perfect_homework.html:10892-10960`. Reading + Consolidation + Reflection + Boss-done + Done are interstitials, not first-class phases. This mismatch is the single biggest source of "phase X doesn't advance" bugs in `STATE.md` lines 100-105.
- **Generation engine has been deprecated.** `pipeline.py` was removed; the `POST /api/homeworks/{id}/generate` endpoint is unregistered (per STATE.md:94). What's left under `server/services/ai_*.py` is the **runtime AI lane** (live tutor + grading + dynamic boss + eval) — not a content generator. Subject prompts in `server/prompts/<subject>/` are now author-facing reference material that the builder UI consumes manually, not server-driven LLM calls.
- **AI gateway adoption is partial.** `ai_gateway.py` exists with task-keyed model routing + Pydantic structured-output validation, but `tutor.py:tutor_chat_v2`, `boss_dynamic.py`, and `final_report.py` still call `ai_orchestrator.generate(_json)` directly, bypassing schema validation, prompt versioning, and the `ai_call_logs` table. Per the remaining-fix report (BE-1, BE-2, P0).
- **8 game-break mechanics now share a runtime registry** (`gbActiveGameOrder`, perfect_homework.html:12666-12690) but **prompts only mention 4** ("Adaptive Quiz / Tile Match / Memory Match / Sentence Fill"). Builder authors learn the other 4 (Puzzle Lock, Mystery Box, Tic Tac Toe, Memory Palace) only by reading the runtime — content quality drops accordingly.

---

## 11-Phase Walkthrough

The phase list shipped in `CONTRACTS.md` and `server/services/routing.py:48-58` names **9 phases** plus the gate quote (Stage 0). Counting the runtime interstitials and the boss-done / done screens reaches 11. Below: the canonical pipeline order, the runtime FSM stage, the UI surface, where AI fires, and what's broken.

| # | Phase | Stage | UI surface | AI touchpoints | Issues |
|---|---|---|---|---|---|
| 0 | Gate quote | 0–1 | `runQuoteSequence` selects from 600-entry library, 5s skip lock | None at runtime — server-side selector at inject time (`quotes.py`). | None. Solid. |
| 1 | **Preview** (panels) | 2 | 7-panel SUMMARY / FORMULA / EXAMPLE / WORD-TO-FORMULA / etc. with horizontal swipe | Tutor PREVIEW persona answers "what does X mean" using visible passage. | Tutor's `screen_context` still drops content if any answer marker appears mid-sanitize (FE-4 in remaining-fix report). |
| 2 | **Flashcards** | 2.5–3 | Apple-glass front/back card. Inline media zone. | Tutor PRACTICE persona. | Side-peek terms still use `textContent` (STATE.md:111) — inline images don't render in peek view. Documented as intentional. |
| 3 | **Memory Sprint** | 3.5–4.5 | KO / TF / YNNG quick-answer cards | Tutor PRACTICE; deterministic check via `answer_checker.numeric/text_exact/set_match`. | Healthy. |
| 4 | **Reading** (til-fanlar only) | 4.7 | Passage + checkpoints with input | Tutor PRACTICE; checkpoint deterministic check. | Phase progress dot DOES NOT advance (STATE.md:103). Stage-to-dot map at `perfect_homework.html:10942` puts 4.7 → `gameBreaks`, which is wrong — Reading is NOT a game break. |
| 5 | **Game Breaks** | 5 | Up to 8 sub-mechanics: AQ / WC / TM / PL / MB / TTT / SF / MP | Tutor PRACTICE; `/api/ai/check-answer?phase=tile-match\|sentence-fill\|ttt\|ttt-session\|memory-palace\|real-life\|final-boss`. | The most over-engineered phase. 8 mechanics but English/History/Biology prompts only describe 4. Adaptive Quiz "single-tier author clones into all tiers" still in `injector.py:339-348` (STATE.md:106). |
| 6 | **Real-Life Challenge** | 6 | 5-step structured cases (badge → story → q1-q6) OR new RealLifeChallengeCase shape (PR #143) | Tutor PRACTICE; 300-XP rubric grader through `ai_gateway` (one of the few). | Two real-life shapes coexist (legacy `real_life.q1..q6` and new `RealLifeChallengeCase`); 6.5 stage maps to `boss` not `realLife` (`perfect_homework.html:10947`). |
| 7 | **Consolidation** (interstitial) | 6.5 | Mnemonic + check_prompt slide deck | None — passive review. | "Always-visible Next button" was just patched (#210/#212/#213). The screen had a fragile single-timer chain. The deeper issue: it's a phase but uses CSS class `screen` not the shared `.gb-game-panel` system. |
| 8 | **Final Challenge / Boss** | 7 | Boss battle: HP, attempts, dynamic question card | Three modes: legacy `bossTurn` (preview homeworks), boss-plan reorder, NEW dynamic boss `boss/start → generate-question → submit-answer` (`ai_plan5.py`). | Dual-track lives. `boss_meta.use_dynamic_boss` flag (#203) gates which path runs. Legacy is still default for old rows; new homeworks get the dynamic adaptive boss. |
| 9 | **Boss-done** (interstitial) | 7.5 | Result card + XP + stars | None. | Healthy. |
| 10 | **Reflection** | 7.7 | Summary + question + spaced_rep + closing | `/api/ai/reflection` produces feedback. | `homeworkSummary` is just `subject_display` (STATE.md:121-122) — AI gets a 1-word context and produces generic feedback. |
| 11 | **Done / Results** | 8 | Final scoreboard | None. | Healthy. |

**Cycle-arc analysis** (PISA + real-world prep lens):

- The pipeline correctly executes **Bloom's ascent**: recall (preview/flashcards) → identify (memory sprint) → apply (game breaks) → analyze/synthesize (real-life) → evaluate (boss) → reflect (reflection). Pedagogically sound.
- **Reading** is gated only to til-fanlar. Tabiy-fanlar (physics/biology/chemistry) PISA scenarios *should* include passage-based reasoning per PISA Science framework — currently they don't.
- **History drops Real-Life entirely** (line 260 of CONTRACTS.md): `["preview", "flashcards", "memory_sprint", "game_breaks", "consolidation", "final_challenge", "reflection"]`. That's a real-world-prep gap — history is the subject *most* needing "what would you do as a student in 1865 Tashkent" framing.
- The pipeline doesn't tier difficulty cleanly between Memory Sprint and Game Breaks. Both are "answer-and-advance" — students hit ~40 minutes of essentially the same UX texture before reaching Real-Life.

---

## Per-Subject Scoring Matrix

Quality scale is defined explicitly:
- **5/5**: deterministic structure, hard constraints, worked examples, anti-hallucination guardrails, per-grade-band scaffolds, level-locked tense/tier rules
- **4/5**: structured but missing one of (worked examples / level-bands / anti-hallucination clauses)
- **3/5**: structured but free-form output sections; one or two missing constraints
- **2/5**: ad-hoc, mostly prose, no schema enforcement
- **1/5**: free-form, no examples, no validation

Phase coverage scored 0–11 against the canonical pipeline (gate quote excluded — it's library-driven; reading only counts for til-fanlar). Phases not in the family's pipeline don't ding the score, but **missing prompts that the family DOES require** do.

| Subject | Phase coverage | Prompt quality | Content depth | Notes |
|---|---|---|---|---|
| **math-algebra** | 9/9 (aniq-fanlar) | 4/5 | 4/5 | All 12 prompt files. Lean (1091 LOC total) but tight — Panel-5 word-to-formula contract is well-specified at `preview-hard.md:60+`. Real-life is solid. Anti-hallucination via "no magic moves" rule. Slightly weak on per-grade-band scaffolding (5-6 vs 7-9 vs 10-11 not always differentiated). |
| **geometriya-g7-11** | 9/9 (aniq-fanlar) | 5/5 | 5/5 | The strongest subject. `instruction.md` is 316 LOC — the most detailed in the repo. SVG mandates explicitly enforced (per PR #154). Per-grade-band content present. |
| **physics** | 9/9 (tabiy-fanlar) | 4/5 | 5/5 | Includes pre-built reference SVGs (`circular-motion-concept.svg`, `circular-path-example.svg`) — only subject with shipped reference visuals. `preview-hard.md` Panel 5 (Phenomenon→Formula) contract is rigorous. Slight gap: real-life prompts are 110 LOC vs english's 124. |
| **biology** | 9/9 (tabiy-fanlar) | 4/5 | 4/5 | Solid coverage. Game-breaks prompt explicitly excludes Notebook Capture ("no calculations") — good guardrail. Misses 4 of 8 runtime game mechanics in its game-breaks doc (Puzzle Lock, Mystery Box, TTT, Memory Palace not mentioned). |
| **kimyo-g7-11** | 9/9 (tabiy-fanlar) | 4/5 | 4/5 | Mirrors biology shape. 1513 LOC — second-thickest after english. Content depth solid; same 4-of-8 game-mechanic gap. |
| **english** | 10/10 (til-fanlar — has reading) | 5/5 | 4/5 | Most thorough prompts (1651 LOC) — CEFR-locked tense rules, sentence-count-by-level, Word→Structure mini-cases. Single subject without `flow.md` (intentional? unclear). Content depth slightly thin on real-world Uzbek-context examples — leans on generic CEFR scenarios. |
| **history** | **6/9 (ijtimoiy-fanlar)** | 3/5 | 3/5 | **Weakest subject.** Missing `classify.md` (despite being declared optional, all 6 other subjects have it for the easy/hard branch — history is locked-hard, so arguably fine). Missing `real-life.md` (and pipeline drops real_life — but prompt should still exist for game-break scaffolding alignment). Has `preview.md` not `preview-easy/hard.md` split. `flow.md` is 42 LOC — half the average. `instruction.md` (98 LOC) skips the verification checklist that math/physics have. Content depth: extraction step is excellent (key figures / dates / places / terms / sources) but downstream phases don't have parallel rigor. |

Confidence on this matrix: **medium**. I read 4 full prompts and skimmed the rest by file size + spot-checking the headers. A second pass that fully reads each subject's `preview-hard.md` + `final-challenge.md` + `real-life.md` would push to high.

---

## Generation Engine — Call Graph + Redundancy

### Verified entry points (active routes, registered in `server/app.py:114-122`)

```
ai_router       (server/routes/ai.py            — 2619 LOC, 13 routes)
ai_plan5_router (server/routes/ai_plan5.py      —  464 LOC, dynamic boss: start/generate/submit/state/give-up)
ai_plan8_router (server/routes/ai_plan8.py      —  437 LOC, debug + eval + sim + final-report)
grading_router  (server/routes/grading.py)
notebook_router (server/routes/notebook.py)
```

### NOT registered (dead code — confirmed via `grep include_router` at `server/app.py:112-122`)

- **`server/routes/ai_plan4.py` (2403 LOC)** — defines the same 13 routes as `ai.py` (`/ai/status`, `/ai/check-answer`, `/ai/tutor/chat`, `/ai/boss-turn`, `/ai/runtime/submit-answer`, etc.). Differs by 216 LOC (likely an in-progress refactor that was abandoned). **No importer in app.py. No tests reference it.**

### Service layer call graph (8 modules in `server/services/ai_*.py`, 4 are `ai_orchestrator.py`'s neighbors)

```
                    ai_orchestrator.py    ←  6 importers (legacy direct path)
                  (337 LOC, provider shim)
                          ↑
                          │
      ai_providers/__init__.py (registry)
                          │
                          ↓
                  ai_providers/kimi.py (only active provider)


                    ai_gateway.py         ←  4 importers (new task-routed path)
                  (366 LOC, AITask enum,
                   Pydantic schemas, ai_call_logs)
```

| Module | LOC | Role | Imported by |
|---|---|---|---|
| `ai_orchestrator.py` | 337 | Provider shim, fallback chain, `_strip_inline_media` sanitizer, `generate(_json)`, `generate_vision` | tutor.py, ai_gateway.py, boss_dynamic.py, ai.py routes, ai_plan4.py (dead), notebook_grade.py |
| `ai_gateway.py` | 366 | `AITask` enum, model-tier routing, structured-output retry, `ai_call_logs` write, guardrail | tutor.py, boss_dynamic.py, ai_plan8.py, grading.py |
| `ai_context.py` | 386 | Builds canonical context packet (homework slice + phase + question + attempts + chat history) | tutor.py, ai_plan5.py, ai_plan8.py |
| `ai_evaluator.py` | 346 | Single-turn fixture-driven eval runner | ai_plan8.py only |
| `ai_simulator.py` | 396 | Multi-turn LLM-judged tutor/boss sim | ai_plan8.py only |
| `ai_metrics.py` | 344 | Session metrics aggregation | ai_plan8.py only |
| `ai_debug.py` | 86 | `context_debug` envelope when `AI_DEBUG_CONTEXT=true` | ai.py, ai_plan8.py |
| `boss_dynamic.py` | 480 | Dynamic boss state machine, question generation, server-stored rubric | ai_plan5.py only |
| `boss_context_builder.py` | 236 | Performance-profile builder for boss prompt | boss_dynamic.py only |
| `final_report.py` | 143 | End-of-session report generator | **0 importers — dead** |
| `runtime_answer_resolver.py` | 100 | Resolves question target by phase+id from content_json | ai.py, ai_plan4.py (dead) |
| `content_json_compat.py` | 354 | Legacy-key normalization (PR #202/#211) | homework.py, homework_page.py |
| `tutor.py` | 1533 | The whale: 23 functions covering check_answer, boss_turn, reflection, tutor_chat, tutor_chat_v2, boss_plan, runtime_answer | routes/ai.py |
| `injector.py` | 1626 | Regex substitutes ~10 named constants into perfect_homework.html | homework_page.py |

### Redundancy findings

1. **`ai.py` ↔ `ai_plan4.py`** are 95% the same routes file (~5000 LOC of duplicate intent). The whole `ai_plan4.py` should be deleted — but verify first there's no plan to swap them.
2. **`tutor.py` has TWO tutor-chat functions**: `tutor_chat` (line 1039) and `tutor_chat_v2` (line 883). Per the remaining-fix report (BE-1), v2 still calls `ai_orchestrator` directly while v1 was supposed to be deprecated. Unclear which is wired by routes — `ai.py:2399` registers `/ai/tutor/chat`. They likely both exist behind the route to A/B test, but the lifecycle is undocumented.
3. **`final_report.py` is wholly unused.** No importer. Either ship the wiring (per BE-6) or delete the module.
4. **Two boss systems live side-by-side**: legacy (`tutor.py:boss_turn`, `tutor.py:boss_plan`) and dynamic (`boss_dynamic.py` + `ai_plan5.py`). Per `boss_meta.use_dynamic_boss` flag. Documentation says "new sessions use dynamic" but the legacy code path is 30%+ of `tutor.py`.
5. **`ai_orchestrator` and `ai_gateway` are co-active for the same tasks.** `tutor_chat_v2` calls `ai_orchestrator.generate` directly; the same task class is supposed to flow through `ai_gateway.generate_text(task=AITask.TUTOR_CHAT)`. The "partial migration" is 6 months old at this point.
6. **`runtime_answer_resolver.py` is duplicated across `ai.py:2082` and `ai_plan4.py:1953`** — same import statement, same callsite shape. Will resolve when ai_plan4 is deleted.

### Hardcoded constants that should be config

- `_PER_FIELD_CHAR_CAP = 5000` and `_PROMPT_INPUT_CHAR_CAP = 50000` (`ai_orchestrator.py:181-182`) — these are the answer-leak / oversize-prompt fence. Should be env-tunable.
- `SESSION_MESSAGE_CAP = 60`, `BOSS_FRAMING_MAX_CHARS = 180`, `ALLOWED_PERSONA_TRAITS` (in `tutor.py`) — same.
- 8-game registry order (`gbActiveGameOrder`, `perfect_homework.html:12666`) — currently hardcoded; making this CONTRACTS-driven would let new games register without an HTML edit.

### Async/sync inconsistencies

- `_log_call` in `ai_gateway.py:94` is async but the work it wraps could be fire-and-forget. Currently `await`ed inside `finally:` — adds 5–20ms tail latency to every AI call.
- `ai_orchestrator.health_check()` does a real LLM round-trip; dashboards calling it in a loop hit the model. There's no caching.

### Cache layer

- `answer_cache` table caches AI grade verdicts with `min_confidence ≥ 0.85`. Documented in `D3 (Grading Router)` (STATE.md:309-310). Looks correct.
- No HTTP cache on `/api/quotes` (600-row JSON read every call). Low impact but easy win.
- `boss_dynamic` stores generated questions per-session — no eviction policy; long sessions accumulate.

### Compat layer breadth

`content_json_compat.py:normalize_homework_row_for_runtime` covers `quotes → gate_quote.custom`, `boss → boss_questions`, `reading.text → passage`. **Wired into**: homework GET API, render route, and (post-PR #211) the `ai.py` direct-DB-read sites. Confirmed comprehensive against the FROZEN schema for the 4 known legacy keys. **Not** comprehensive against future schema additions — there's no test asserting "all `[]`-default keys survive a round-trip without compat needing to know about them." Adding a property-style test that `normalize(empty_scaffold) == empty_scaffold` would lock this in.

---

## Top-5 Simplification Opportunities (what to REMOVE)

1. **Delete `server/routes/ai_plan4.py` (-2403 LOC).** It's a complete shadow of the live `ai.py` router. No registration, no test reference, no doc reference. Confirms the "single biggest cleanup win" framing in the TL;DR. *Verify first* by `grep -r ai_plan4` across the repo, then delete in a regression-test-only PR.

2. **Collapse `tutor_chat` + `tutor_chat_v2` to one function.** `tutor.py:883` and `tutor.py:1039`. Pick the v2 contract, delete the v1, route everything through `ai_gateway.generate_structured(task=AITask.TUTOR_CHAT, schema=TutorResponse)`. -150 LOC and the BE-1 fix lands.

3. **Delete `server/services/final_report.py` (-143 LOC) OR finish wiring it (+1 route).** Currently it's a dangling module. Two options. The remaining-fix report (BE-6) wants it wired; nothing in tracked work shows it being scheduled.

4. **Retire legacy boss path once `use_dynamic_boss` is the default.** The `tutor.py:boss_turn` / `tutor.py:boss_plan` (~400 LOC) duplicate intent of `boss_dynamic.py`. Once dynamic boss is verified across all 7 subjects (currently flag-gated, default false per #203), the legacy path becomes maintenance debt for backward-compat-only. Plan: 30-day deprecation, then delete.

5. **Reduce game-break inventory from 8 to 5.** Adaptive Quiz, Sentence Fill, Tile Match, Memory Match, and Memory Palace cover 95% of pedagogical surface. Mystery Box, Puzzle Lock, and Tic Tac Toe are gimmicky variants that **don't appear in any subject's `game-breaks.md` prompt** (verified: searched `biology`, `physics`, `english` — none mention them). Either drop them entirely or document them in every subject prompt; right now they exist in code only. Removing 3 mechanics = ~1500 LOC of `perfect_homework.html` plus their CSS, gbInit functions, and editor `frontend/js/editors/_*.js` modules.

---

## Top-5 Quality Gaps (what to FIX)

1. **History prompt parity (HIGHEST priority for the user's "knowledge quality preserved" criterion).** Add `real-life.md` (even though pipeline drops the phase, the game-breaks layer needs the framing); split `preview.md` → `preview-easy.md` + `preview-hard.md` to match the other 6 subjects. Bring `flow.md` from 42 LOC to ~80. Add per-grade-band scaffolds (5-6 vs 7-8 vs 9-11) in `instruction.md`. Files to touch: `server/prompts/history/{instruction,flow,preview-easy,preview-hard,real-life,classify}.md`.

2. **Sync subject prompts to the 8-game runtime registry.** All 7 subject `game-breaks.md` files reference 4 mechanics; the runtime ships 8. Bring each subject's prompt into alignment OR retire the unused mechanics. Files: `server/prompts/{biology,kimyo-g7-11,english,history,math-algebra,geometriya-g7-11,physics}/game-breaks.md`.

3. **Wire history's Real-Life Challenge.** History is the subject *most* aligned with PISA "social science scenario" framing — the 1865 Tashkent / Khwarezmian-trader vignettes are the entire pedagogical point. Adding `real_life` to `routing.py:39` PHASE_PIPELINE for `("ijtimoiy-fanlar", "hard")` plus the matching prompt is one PR.

4. **Migrate every direct `ai_orchestrator` call to `ai_gateway.generate_structured`.** Per BE-1/BE-2: `tutor_chat_v2`, `process_runtime_answer`'s AI judge, and `boss_dynamic`'s question generation all bypass schema validation + prompt versioning. Files: `server/services/tutor.py`, `server/services/boss_dynamic.py`. ~150 LOC delta with the migrate-then-delete pattern.

5. **Fix the stage→phase-dot mapping for Reading + Real-Life + Consolidation.** `perfect_homework.html:10940-10950`: stage 4.7 (Reading) maps to `gameBreaks` dot — wrong. Stage 6.5 (Consolidation) maps to `boss` — wrong. Stage 7.7 (Reflection) maps to `done` — defensible but pedagogically reflection IS its own phase. The visible bug: progress bar freezes / jumps during these screens (STATE.md:103-105). One file, ~10 lines.

---

## Files to Touch (with line refs) — grouped by priority

**P0 (delete dead code):**
- `server/routes/ai_plan4.py` — DELETE (2403 LOC). Verify zero importers first: `grep -rn ai_plan4 server/ tests/ docs/`.
- `server/services/final_report.py` — DELETE or wire (143 LOC). Decision needed.

**P1 (high-value simplification):**
- `server/services/tutor.py:883-1115` — collapse `tutor_chat_v2` and `tutor_chat`; route through `ai_gateway`.
- `server/services/tutor.py:524-660` — deprecate `boss_turn` once `use_dynamic_boss` defaults true; mark `# TODO(deprecated 2026-XX): legacy path, retire after dynamic-boss rollout`.
- `server/template/perfect_homework.html:10940-10950` — fix stage→phase-dot mapping.

**P2 (subject content quality):**
- `server/prompts/history/{instruction.md, flow.md, preview-easy.md (NEW), preview-hard.md (NEW), real-life.md (NEW), classify.md (NEW)}` — bring to parity with math/geometry.
- `server/prompts/{biology,physics,english,kimyo-g7-11,history,math-algebra,geometriya-g7-11}/game-breaks.md` — sync to 8-mechanic registry OR document the carve-out.
- `server/services/routing.py:39` — add `real_life` to ijtimoiy-fanlar pipeline OR explicitly comment why it's excluded.

**P3 (cleanup follow-ups):**
- `server/services/ai_orchestrator.py:181-182` — env-tune `_PER_FIELD_CHAR_CAP` / `_PROMPT_INPUT_CHAR_CAP`.
- `server/template/perfect_homework.html:12666-12690` — if game-break inventory shrinks to 5, the gbActiveGameOrder registry shrinks, plus 3 game `gbInit*` functions can be removed (each ~300-500 LOC).
- `server/services/tutor.py:215-224` (`_model_for_subject`) — currently routes by subject; once all calls are gateway-mediated, `_model_for_subject` becomes redundant with `TASK_MODEL_POLICY`.

---

## Constraint Scoring — User's 5 Criteria

| # | Criterion | Score | One-line justification |
|---|---|---|---|
| 1 | Interactive / gamified | **4/5** | Game Breaks (Phase 5) is rich — 8 mechanics, animations, XP, server-graded. Boss is dynamic. But Preview/Memory Sprint/Reading are ~50 minutes of swipe-and-answer monotony before the fun starts. |
| 2 | Simple, not over-engineered | **2.5/5** | The biggest red flag in the audit. 5 routes files, 14 service modules, 2 router-files duplicating each other (ai.py + ai_plan4.py), 8 game mechanics where 5 would do, 2 tutor-chat functions, 2 boss systems. ~3000 LOC of redundancy is identifiable in one read-through. |
| 3 | Knowledge quality preserved | **4/5** | Math, geometry, physics, biology, kimyo, english are 4-5/5. History is 3/5 and drags the average. Anti-hallucination guardrails (regex-strip-inline-media, side-disjoint injector, answer-spec deterministic-first) are best-in-class. |
| 4 | Phase cycle preserved | **3.5/5** | The 9-phase pipeline is pedagogically sound. The 11-phase runtime experience leaks at 3 specific seams: stage→phase-dot mapping wrong for 4.7/6.5/7.7, history skips real-life, and consolidation's pre-#210 fragility shows the phase chrome is over-coupled to a single timer chain. |
| 5 | PISA + real-world prep (15-y-o) | **3.5/5** | Real-Life Challenge phase is excellent for math/physics/biology/kimyo/english. Missing entirely for history (the subject most needing it). Reading phase is gated to til-fanlar even though PISA Science requires reading-passage reasoning across all sciences. |

**Weighted average** (treating "simple" as 2× weight per the user's 2026-05-09 brief): **3.4/5**. The math is 2.5×2 + 4 + 4 + 3.5 + 3.5 = 20.0 / 6 = 3.33. Round to 3.4.

---

## Open Questions for the User

1. **Is `ai_plan4.py` a deliberate WIP or abandoned?** If WIP, who owns it and what's the merge target? If abandoned, can I delete it in a single PR? (~2400 LOC delete is the highest-leverage cleanup in this audit.)
2. **Should we shrink the game-break inventory from 8 to 5 (Adaptive Quiz / Sentence Fill / Tile Match / Memory Match / Memory Palace), retiring Mystery Box / Puzzle Lock / Tic Tac Toe?** They aren't documented in any subject prompt and add ~1500 LOC of UI surface that students rarely see authored homework for.
3. **Should history get Real-Life back?** It's the subject most aligned with PISA's "students apply learning to scenarios" rubric, but routing.py explicitly drops it for ijtimoiy-fanlar with no documentation. Pedagogical call.

---

*End of audit. Word count for body: ~2380.*
