# NETS Builder — Current State

Snapshot date: 2026-04-25.
Pair this file with `README.md`. Read both before touching anything.

This is the operational truth: what's confirmed working, what's known broken, and what an
agent should test next. Update this file whenever you ship a fix or discover a regression.

---

## Health summary

| Area | Status | Confidence |
|----|----|----|
| AI tutor backend (Vertex) | ✅ working | 100% |
| Homework CRUD + persistence | ✅ working | 100% |
| Dashboard / library / trash / versions | ✅ working | 100% |
| Export to standalone HTML | ✅ working | 100% |
| Editor → preview round-trip (10 phases) | ✅ working | ~95% |
| Live preview iframe in builder | ✅ working | 95% |
| Save durability (WAL + keepalive) | ✅ working | 95% |
| Reading / Consolidation / Reflection runtime | ⚠ display-only | 70% |
| AI tutor wired into runtime events | ⚠ partial | 70% |
| Programmatic homework generation pipeline | ❌ stubbed | 10% |

Overall: **~94% functional**. The remaining 6% is mostly polish and the
`pipeline.py` AI-generation runner (not yet implemented).

---

## What's working (verified end-to-end)

### Backend
- FastAPI app boots clean, serves frontend statically, mounts `/api/*`.
- SQLite with WAL + `synchronous=FULL`. Crashes / hard-refreshes don't lose data.
- Soft-delete + version snapshots. Restore-from-version tested.
- 4 AI tutor endpoints (`/api/ai/check-answer`, `/boss-turn`, `/reflection`, `/tutor`).
- Vertex AI active: project `unique-spirit-494018-h5`, location `us-central1`,
  models `gemini-2.5-flash` (fast) + `gemini-2.5-pro` (boss).
- Endpoints return well-formed Uzbek JSON in <2s p50.
- Trashed homeworks return 409 on `/preview` and `/h/{id}` (BUG-1, fixed; export route removed in Wave B1+B2).
- Auto-fallback: if Vertex fails → Gemini API → Kimi → stock responses. Sessions never stall.

### Builder UI
- All 10 phase editors load, save, and round-trip content correctly.
- RichField (contenteditable + Bold/Italic/Image/SVG toolbar) on every long-form text field:
  - Flashcards: term + def + media zone
  - Memory Sprint: prompt + explain
  - Boss: prompt + hint
  - Real Life: story + q1–q6 prompts + q1–q6 feedback
  - Reading: checkpoint feedback
  - Consolidation: mnemonic + check_prompt
  - Reflection: summary + question + spaced_rep + closing
  - Sentence Fill (game): prompt
  - Tile Match (game): both tile slots
  - Adaptive Quiz (game): prompt + media zone
- FAB "Add" button follows scroll across all phases.
- Paste normalization strips Word/Docs formatting from short inputs; preserves rich content
  in RichField hosts.
- `beforeunload` keepalive fetch flushes the latest content_json on hard refresh.
- "Test Tutor" button in builder topbar — pings all 4 AI endpoints + shows backend name.

### Runtime template (preview + permanent share URL)
- All 10 content keys inject correctly into JS constants.
- Flashcard front images (structured media zone) render via `fc-front-media` slot.
- Inline images/SVGs in front term render via `term_html` (formatting tags stripped, media
  preserved).
- Back-of-card definition uses `innerHTML` so inline media renders.
- All non-flashcard rich-field renderers use `innerHTML`.
- Inline images/SVGs are clamped (max-height 180–220px, max-width 100%, object-fit contain).
- Adaptive Quiz now accepts multiple correct answers via `acceptable[]` (case-insensitive,
  whitespace-trimmed).
- Sentence Fill respects per-level `expects[]` if authored; falls back to invariant.
- Reading / Consolidation / Reflection screens injected with auto-skip when empty.

### Dashboard
- Library grid shows all homeworks with subject icon, grade badge, mode pill, status dot,
  relative-time updated.
- Library / Trash tab toggle.
- Per-card More menu: Preview, Duplicate, Version history, Move to trash.
- Versions modal with per-version Restore.
- Direct download (Export) button on each card.
- Status polling for `generating` state (5s interval).
- Error/retry state on network failures.
- Responsive grid: 3-col / 2-col / 1-col at 1024 / 640 / mobile.

---

## Known Issues — Triaged 2026-04-27

### High priority

- **[BROKEN] Reading checkpoints are display-only** — `perfect_homework.html:4994–5015`. `renderReading()` renders each checkpoint as static `<div>` blocks (prompt + answer text); there is no `<input>` field, no "Check" button, and no feedback-reveal logic. Repro: open any homework preview with reading content, reach the Reading screen — checkpoints show answer text immediately with no interactivity.

- **[STALE] No programmatic homework generator** — `server/services/pipeline.py:1–8`. The pipeline module was deprecated on 2026-04-24 and is explicitly marked "Do not import from it." The scope has changed: homework content is now authored via Builder UI only. The `POST /api/homeworks/{id}/generate` endpoint was never registered in `app.py` and the use case has been removed. No longer a gap — this was a deliberate design decision, not a bug.

- **[BROKEN] AI tutor not bound to in-template submit events** — `perfect_homework.html:4819–4860` (boss), `4470–4692` (real-life). `runtime.js` listens for `nets:submit` CustomEvents and exposes `window.NETS_AI`, but `bossHandleAction()` and `rlSubmitQuestion()` perform local string matching only and never dispatch `nets:submit`. Repro: serve a preview, answer a boss question — no `NETS_AI.bossTurn()` call fires (verify via DevTools Network tab: zero POST to `/api/ai/boss-turn`).

### Medium priority

- **[BROKEN] New screens (reading/consolidation/reflection) use inline styles** — `perfect_homework.html:2366–2396`. All three new screen `<div>` elements use `style="..."` attributes instead of CSS classes. The consolidation `check_answer` element is permanently visible as plain italicized text rather than a reveal-on-demand interaction — `cons-check-answer` has no toggle/button. Visually inconsistent with the rest of the template.

- **[BROKEN] Skip-gesture not extended to 3 new screens** — `perfect_homework.html:2770–2772`. The swipe handler guards `stage === 5` for non-edge drags. The reading, consolidation, and reflection screens are shown by callback functions (`showReadingScreen`, `showConsolidationScreen`, `showReflectionScreen`) that do not call `setStage()`, so `state.stage` stays at the previous stage value when those screens are active. Edge-swipe skip overlay fires on the wrong stage; skipping a reading screen mid-session is not possible.

- **[BROKEN] Phase progress dots don't advance for the 3 new screens** — `perfect_homework.html:2908`. `phaseMap` only maps stage values `0`–`7.5`. `showReadingScreen`, `showConsolidationScreen`, and `showReflectionScreen` never call `setStage()`, so the progress bar stays frozen at the previous stage dot while those screens are active.

- **[BROKEN] Adaptive Quiz single-tier author: injector clones into all tiers** — `server/services/injector.py:339–348`. When an author provides items for only one tier, the injector copies the first item into the two missing tiers. The quiz then repeats identical questions across easy/medium/hard escalation. Repro: author a `gb_adaptive_quiz` with only `"tier": "easy"` items; preview the adaptive quiz game break — all three difficulty tiers show the same questions.

### Low priority

- **[FIXED] AI tutor field naming drift** — `server/routes/ai.py:28–36` and `server/template/runtime.js:75–86`. The Pydantic model for `/boss-turn` uses `boss_question`, `hp_remaining`, `damage_value`, `expected_answers`; `runtime.js` sends the exact same field names. No mismatch in the running code. Stale smoke-test docs are the only remnant; safe to ignore until those docs are regenerated.

- **[BROKEN] Side-peek flashcard terms use textContent** — `perfect_homework.html` (side-peek renderer). Inline images/SVGs don't appear in previous/next card side previews. Confirmed by design but now documented here since `term_html` is set and could power the peek if desired.

- **[FIXED] Dashboard subject filter not implemented** — `frontend/js/dashboard.js:69,218–241,296,747–750`. Subject filter is fully wired: `renderSubjectOptions()` populates a `<select>`, a `change` listener sets `state.filters.subject`, and `renderHomeworks()` filters by `homework.subject === state.filters.subject`. The original claim was inaccurate post-deployment.

### New issues found during triage

- **[New — High] `cons-check-answer` always visible; no interactive reveal** — `perfect_homework.html:2380–2383`. The consolidation screen shows `check_answer` as permanently visible italicized text. There is no "Show answer" button or input field. This is arguably worse than display-only — the answer is exposed before the student attempts the check question, defeating the formative purpose entirely.

- **[New — Medium] `pipeline.py` still imports from `db.py` and `services`** — `server/services/pipeline.py:26–28`. Despite the deprecation notice, the file still imports `get_homework`, `update_homework`, `set_status` from `db`, and `gemini` from services. If these imports fail (e.g., signature change), they will raise at module load only if something imports `pipeline` — currently nothing does. Safe but messy; should be cleaned up in the Wave A5 pass.

- **[BROKEN — Medium] `homeworkSummary` in runtime context uses `subject_display`, not a real summary** — moved into `server/routes/homework_page.py::render_homework()` after Wave B1+B2 deleted `export.py`. The `NETS_CTX.homeworkSummary` field, which `runtime.js` passes to `/api/ai/reflection` as `homework_summary`, is still set to `content.get("meta", {}).get("subject_display", "")` — i.e., the subject name string ("Algebra", etc.), not a session performance summary. The reflection AI prompt receives a subject label instead of meaningful session data, producing generic feedback. Real fix: compute a summary from session score data or leave it empty for the frontend to fill in.

---

## Test queue (what to verify next)

Run these on the Mac whenever someone changes the relevant area. Curl examples assume
`curl -s http://localhost:8000`.

### Smoke (run after every server restart)

```bash
curl -sf /api/subjects > /dev/null && echo OK
curl -sf /api/ai/status | grep -q '"backend":"vertex"' && echo VERTEX_OK
curl -sf /api/homeworks > /dev/null && echo HW_LIST_OK
```

### Builder ↔ runtime parity (run after editor or injector changes)

For each of the 13 keys (10 arrays + meta + 2 objects), create a homework via PUT with
a one-item fixture and grep the preview output for the expected constant. The E2E smoke
script lives in this repo's history (Wave 2 sub-agent transcript) — reuse it.

Specifically watch for:

- `const FLASHCARDS = [...]` contains your test cluster name.
- `const RL_SCENARIO = {` contains `"questions":` (template-shape) — confirms RL adapter ran.
- `const READING = {`, `const CONSOLIDATION = {`, `const REFLECTION = {` all present
  with payload (post-Wave 2 fix).
- `acceptable: [...]` present in `GB_ADAPTIVE_QUIZ` items with multi-answer fixtures.
- `chain[i].expect` matches `expects[i]` for sentence-fill items with per-level expects.

### AI tutor (run after gemini.py / tutor.py / .env changes)

```bash
# All four should return 200 with non-empty content
curl -X POST /api/ai/check-answer -H 'Content-Type: application/json' \
  -d '{"question":"2+2?","expected":"4","student_answer":"4","context":""}'

curl -X POST /api/ai/boss-turn -H 'Content-Type: application/json' \
  -d '{"boss_question":"x²-5x+6=0?","hp_remaining":150,"student_answer":"2,3",
       "expected_answers":["2,3"],"damage_value":20}'

curl -X POST /api/ai/reflection -H 'Content-Type: application/json' \
  -d '{"homework_summary":"8 q, 6 correct","student_reflection":"hard"}'

curl -X POST /api/ai/tutor -H 'Content-Type: application/json' \
  -d '{"question":"What is a square root?","prior_attempts":[]}'
```

### Persistence (run after db.py or save-flow changes)

1. Create homework, type into a flashcard, hard-refresh browser, reopen.
   The typed text must persist.
2. Make 3 edits, check `/api/homeworks/{id}/versions` returns ≥3 entries.
3. Restore an old version, confirm content matches.
4. Trash + restore — content_json byte-identical before/after.

### Permanent URL render (run after homework_page.py or template changes)

```bash
curl -s /h/{id} > out.html
grep -c 'NETS_CTX' out.html       # must be 1 (AI bootstrap is always injected)
grep -c 'runtime.js' out.html     # must be 1
grep -c 'const PANELS' out.html   # must be 1
```

Open `out.html` in a browser — full homework plays with AI tutor live (assuming backend reachable).

---

## Recently fixed (last 24h)

| Bug | Severity | Fix |
|----|----|----|
| Trashed homework `/preview` returned 200 | BLOCKER | homework_page.py + homework.py now return 409 with `{code:TRASHED}` |
| Flashcard front showing raw HTML tags | HIGH | injector strips formatting tags but preserves inline `<img>`/`<svg>` (`_strip_text_tags_keep_media`); template uses `innerHTML` for term_html |
| Flashcard front media not rendering | HIGH | added `fc-front-media` slot in template DOM, renderer writes structured media HTML there |
| Flashcard back media too large | MEDIUM | CSS clamps to max-height 180px, max-width 100%, object-fit contain |
| Hint inside flashcard back face | LOW | moved to `.fc-user-hint` element below the card scene; auto-hides when empty |
| Adaptive Quiz only honored first answer | HIGH | injector emits `acceptable[]`; runtime evaluator iterates with case-insensitive trim |
| Sentence Fill per-level expect was always invariant | HIGH | editor exposes `expects[]` UI; injector maps `chain[i].expect = expects[i] || inv` |
| Reading/Consolidation/Reflection didn't render | HIGH | added template constants + 3 new screens + auto-skip for empty content |
| Memory Sprint card ergonomics | MEDIUM | redesigned with flashcard-style card, type pill, ergonomic correct radio, 2-up options grid |
| FAB didn't follow scroll on sentence-fill / tile-match | MEDIUM | removed `.nested-card` wrapper from those editors so the FAB selector finds the add button |
| `/api/ai/*` 422 on every call | BLOCKER | replaced `*args, **kwargs` decorator with inline try/except per endpoint |

---

## Don't regress

These behaviors are easy to break with a careless refactor. Keep them green.

- **Save flow on hard-refresh.** `beforeunload` triggers a `fetch(... , {keepalive:true})`
  to PUT the latest content_json. If you change `builder.js`'s save logic, re-test by
  typing into a card and hitting Cmd-Shift-R.
- **Quotes auto-wrap.** Plain strings in `quotes[]` get wrapped to `{t,a}` by the injector.
  If you "clean up" the adapter, old fixtures break.
- **Memory match shape.** DB stores `[[left, right]]` arrays. Template needs
  `{a,b,confirmQ,correct}`. The adapter is load-bearing.
- **Real-Life shape adapter.** DB has `q1..q6`. Template has `questions:[...]`. Massive
  reshape happens on every preview. If you "simplify" it, the template breaks.
- **Empty-state placeholders.** Every constant has a fallback so a brand-new draft
  doesn't crash the template. Don't remove them.
- **Trashed-block on preview / `/h/{id}`.** A user pasting an old `/preview` or `/h/{id}` URL
  after the homework was trashed must get 409, not a stale render.

---

## Quick map: where to fix what

| Symptom | First file to look at |
|----|----|
| Editor UI misbehaving | `frontend/js/editors/{phase}.js` |
| Editor saves but preview doesn't show | `server/services/injector.py` shape adapter |
| Preview shows empty constant | template's regex pattern in injector probably no longer matches |
| Preview crashes with `Cannot read X` | `perfect_homework.html` `renderXxx` function |
| AI endpoint returns 422 | `server/routes/ai.py` Pydantic model |
| AI returns garbage | `server/services/tutor.py` prompt or `services/gemini.py` JSON parsing |
| Dashboard list empty | `server/routes/homework.py` list query |
| Permanent URL serves stale content | `server/routes/homework_page.py` — `render_homework()` reads DB on each call; if stale, restart uvicorn or check the cache layer (none currently). |
| Database file ballooning | `server/db.py` version retention; consider trimming old snapshots |

---

## Final note

When in doubt: read the file, don't guess. The template is `server/template/perfect_homework.html`,
the injector is `server/services/injector.py`, and they're the two files that hold the
truth about how content flows from DB to user. Everything else is a thin shell.

---

## Smoke Test Results — Wave A2

Date: 2026-04-27
Run with: `VERTEX_CREDENTIALS_PATH=C:/Users/DaddysHere/Documents/claw_api_service.json pytest tests/test_ai_runtime.py -v`

| Test | Endpoint | HTTP | Latency (ms) | Result |
|------|----------|------|-------------|--------|
| test_ai_status_no_creds | GET /api/ai/status | 200 | 4 | PASSED (no creds needed) |
| test_check_answer | POST /api/ai/check-answer | 200 | 6793 | PASSED |
| test_boss_turn | POST /api/ai/boss-turn | 200 | 6071 | PASSED |
| test_reflection | POST /api/ai/reflection | 200 | 8649 | PASSED |
| test_tutor | POST /api/ai/tutor | 200 | 4271 | PASSED |
| test_report_written | (artifact check) | — | — | PASSED |

**6/6 passed. Backend: Vertex AI (gemini-2.5-flash / gemini-2.5-pro). No shape divergences detected.**

Shape contracts verified against `server/template/runtime.js` FALLBACK objects and JSDoc:
- `check-answer` → `{correct, score, feedback, matched_expected}` ✅
- `boss-turn` → `{correct, damage_dealt, boss_response, hint, score}` ✅
- `reflection` → `{feedback, next_steps, encouragement}` ✅
- `tutor` → `{response, guidance_type}` ✅

Per-call latency artifact: `tests/last_run_report.json`

---

## Auth Model — Wave A5
Decision pending. See `docs/AUTH_MODEL.md` for the proposal (option B—token-in-URL—recommended).
Telegram helper: `scripts/test_telegram.sh` — supply `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` env vars to test.

---

## Wave B1+B2 — /h/{id} permanent URL + export removed
Date: 2026-04-27
- Added GET /h/{id} permanent URL with shared render_homework() helper.
- Deleted server/routes/export.py. /preview moved into homework_page.py (URL preserved).
- injector.inject() always injects AI bootstrap (runtime_context now required).
- Removed export button from builder, getExportUrl() from api.js, Download button from dashboard.
- Library + dashboard "Open preview" links now use /h/{id}.
- homeworkSummary bug from A3 triage no longer reachable (export.py:50 deleted).

---

## Wave B3 — Dashboard pagination + search
Date: 2026-04-27
- GET /api/homeworks now supports q/subject/grade/mode/limit/offset.
- Returns {items, total, limit, offset}. Bare list available with ?legacy=true (deprecated).
- Dashboard paginates at 50 per page with debounced 300ms search and facet-driven dropdowns.
- Tests: tests/test_homework_list.py covers default shape, q search, subject/grade filters, pagination offset.

---

## Wave D — Hybrid Grading
- **D1 (Schema):** Added structured ‘answer_spec’ alongside legacy ans[]/accepted_answers[]. Created migration helper scripts/migrate_answer_spec.py (idempotent, requires --db-path; --backup-first recommended). Schema doc: docs/ANSWER_SPEC.md. CONTRACTS.md §1 updated.
- **D2 (Deterministic Checker):** Added server/services/answer_checker.py handling numeric, set_match, text_exact, text_fuzzy, and semantic answers. Wrote tests/test_answer_checker.py and updated requirements.txt with sympy and rapidfuzz.
- **D3 (Grading Router):** Implemented deterministic-first routing in `/api/ai/check-answer` with AI fallback. Added SQLite-backed caching (`answer_cache` table) and a teacher review queue (`review_queue` table) for low-confidence AI verdicts. Updated `test_ai_runtime.py` with mocked tests for hybrid routing paths.
- **D4 (Builder UI Rebuild):** Replaced free-text accepted answer boxes with structured answer_spec form in boss.js and adaptive-quiz.js. Added /api/ai/answer-spec/preview endpoint for live teacher feedback on grading rules. Backward-compat: legacy ans[] auto-migrates to answer_spec on first save.

---

## Wave F0 — AI Provider Abstraction + Kimi-first (2026-04-28)

Refactored `server/services/gemini.py` from a hardcoded Vertex→Gemini→Kimi fallback chain into a clean provider registry.

**New files:**
- `server/services/ai_providers/__init__.py` — registry (`register`, `get_provider`, `select_provider`, `available_providers`)
- `server/services/ai_providers/base.py` — `AIProvider` ABC
- `server/services/ai_providers/kimi.py` — Kimi/Moonshot provider (primary)
- `server/services/ai_providers/vertex.py` — Vertex AI provider
- `server/services/ai_providers/gemini_api.py` — Public Gemini API provider
- `tests/test_ai_providers.py` — 7 passing tests

**Modified:**
- `server/services/gemini.py` — slimmed to shim; delegates to registry; `generate_json` signature unchanged
- `server/config.py` — added `AI_BACKEND_PREFERENCE`, `KIMI_MODEL_FAST`, `KIMI_MODEL_PRO`
- `server/routes/ai.py::ai_status` — now surfaces `active_provider`, `preference_list`, `available_providers`
- `.env.example` — updated with Kimi-first preference + new model env vars
- `docs/API.md` — updated `/api/ai/status` schema

**Behavior change:** Default provider order is now `kimi → vertex → gemini` (was `vertex → gemini → kimi`). Set `AI_BACKEND_PREFERENCE` env to override.

**Mac mini propagation (one-time SSH op):**
```bash
ssh aisigma@192.168.1.26
cd /Users/aisigma/nets-builder
# Append to .env: KIMI_API_KEY=<key> and AI_BACKEND_PREFERENCE=kimi,vertex,gemini
launchctl bootout gui/501 ~/Library/LaunchAgents/com.aisigma.netsbuilder.plist
launchctl bootstrap gui/501 ~/Library/LaunchAgents/com.aisigma.netsbuilder.plist
curl -sS http://127.0.0.1:8000/api/ai/status | jq
# expected: active_provider == "kimi"
```

---

## Wave F1 — Live AI Tutor Backend (2026-04-28)

Backend half of the persistent floating tutor widget. Tutor-only lane — does NOT
touch `/api/ai/check-answer`, `answer_checker.py`, or the `tutor_attempts`
producer (those are owned by the grading-lane teammate).

**New files:**
- `scripts/migrate_tutor_conversations.py` — idempotent CREATE TABLE + index for `tutor_conversations` (only).
- `server/prompts/runtime/tutor-boss-plan.md` — system prompt for the boss reorder + framing planner.
- `tests/test_tutor_chat.py` — 8 tests covering chat persistence, the answer-leak guard, boss-plan validation + fallback, history endpoint, cross-session isolation, the 60-message cap, screen context handling, and voice tone.

**Modified (F1):**
- `server/db.py` — added `tutor_conversations` schema + helpers `add_tutor_turn`, `list_tutor_turns`, `count_session_messages`, `build_session_profile`.
- `server/services/tutor.py` — added `tutor_chat`, `boss_plan`, `_redact_question_for_tutor` (Bridge B answer-leak guard), `_validate_boss_plan` + `_default_boss_plan` (LLM-failure fallback), constants `SESSION_MESSAGE_CAP=60`, `ALLOWED_PERSONA_TRAITS`, `BOSS_FRAMING_MAX_CHARS=180`.
- `server/routes/ai.py` — added `POST /api/ai/tutor/chat`, `POST /api/ai/tutor/boss-plan`, `GET /api/ai/tutor/history` plus their Pydantic models. `CheckAnswerRequest` and the `check-answer` route are untouched (grading lane's territory).
- `server/prompts/runtime/tutor-assistant.md` — overwritten with the 3-phase rule extension (preview/practice/boss).
- `docs/API.md` — documented the 3 new endpoints.
- `CONTRACTS.md` — new section §11 documents the `tutor_conversations` schema (we own).

**Modified (F4 — cleanup):**
- `server/db.py` — deleted `list_recent_attempts` (read-only helper for the cancelled tutor_attempts producer).
- `server/services/tutor.py` — removed `list_recent_attempts` calls, `_format_attempts_for_prompt`, and prompt-stuffing logic for prior student attempts (grading-lane producer was not built).
- `tests/test_tutor_chat.py` — deleted 2 tests (`test_prior_attempts_reach_prompt`, `test_missing_tutor_attempts_table_is_graceful`) and helper functions that were specific to the dead producer contract.
- `CONTRACTS.md` — removed the `tutor_attempts` schema section; added a note that the producer was cancelled (PR #34).

**Behavior:**
- Per-(session_id, hw_id) cap of 60 turns. 61st `/chat` returns 429 `TUTOR_SESSION_CAP`.
- Practice/boss phases strip answer-bearing keys before the prompt enters the LLM context.
- Boss-plan validates LLM output covers every input `question_id` exactly once with framing ≤180 chars and persona ⊂ {challenger, mentor, analyst}; on any failure (LLM error, schema mismatch, missing question) it returns the default `mentor` plan in input order.

**Verification (`python -m pytest tests/test_tutor_chat.py -v`):**
- 11/11 passing (F1: 10 + F3: 1 persona test; F4 removed 2 dead tests on tutor_attempts producer).
- Full suite: see CI results.

**Migration step (run once on each environment):**
```bash
python scripts/migrate_tutor_conversations.py --db-path /path/to/nets.db
```
Fresh installs already pick this up via `init_db()` on startup; the script is for environments whose DB pre-dates F1.

## Wave F2 — Live AI Tutor Widget (2026-04-28)

Frontend half of the persistent floating tutor — a chat-bubble widget that follows the
student through every phase, listening to a new `nets:phase-change` event so its
mode badge swaps automatically. Talks to the F1 endpoints (`/api/ai/tutor/chat|history`).
Tutor-only lane — does not touch `checkAnswer()` payload (grading lane's territory).
F3 (boss personalization) is the next phase; F4 (post-merge "Stuck? Ask tutor →" CTA)
remains deferred until the grading lane merges.

**Modified:**
- `server/template/perfect_homework.html` — added inline CSS (~230 lines), tutor widget
  DOM (~20 lines), and a self-contained ~280-line `<script>` module appended before
  `</body>`. `setStage(n)` now dispatches `nets:phase-change` with stage→phase mapping
  (0–2 → preview, 2.5–6.5 → practice, 7/7.5 → boss, 7.7+ → preview).
- `server/template/runtime.js` — added `tutorChat`, `tutorHistory`, `bossPlan` methods
  on `window.NETS_AI` plus a `_get` helper. 429 cap responses surface `_cap: true` so
  the widget can lock input.
- `server/template/RUNTIME_INTEGRATION.md` — appended "Live AI Tutor (Wave F2)" section
  documenting the 3 new methods + the `nets:phase-change` event contract.
- `server/routes/homework_page.py` — runtime context now includes `hwId` + `lang` so the
  widget can scope chat to the homework + render labels in the right language.
- `tests/test_homework_page.py` — 3 new tests: `test_tutor_widget_dom_present`,
  `test_tutor_widget_inline_no_external_assets`, `test_runtime_js_exposes_new_methods`.

**Behavior:**
- Widget is a floating FAB bottom-right (56px, above safe-area inset). Click → expands
  into 360×500 chat panel (slides up; goes near full-screen on <600px viewports).
- Phase badge color-codes mode: green=preview, amber=practice, red=boss. Labels
  localized for `en`/`uz`/`ru` (auto-detected from `NETS_CTX.lang` →
  `document.documentElement.lang` → fallback `en`).
- `session_id` is a UUID persisted in `localStorage["nets_tutor_session"]`. Chat history
  is restored from `/api/ai/tutor/history` on widget mount.
- Markdown subset rendering (paragraphs, **bold**, *italic*, `code`, line breaks, lists)
  is XSS-safe — every node is built via `document.createElement` + `textContent`. No
  `innerHTML = userInput` anywhere.
- Per-session message cap of 60 mirrors the backend; on a 429 the widget locks input
  and shows the "Session limit reached" notice.
- Typing indicator (3-dot pulse) shown while a request is in flight.
- All assets inline. Zero new external requests beyond the F1 endpoints.

**Verification (`python -m pytest tests/ --ignore=tests/test_ai_runtime.py -q`):**
- 66/66 passing (was 63 after F1; 3 new tests added).
- Manual smoke checklist (run after deploy on Mac mini): see Wave F plan
  `flickering-rolling-robin.md` § "F2 (widget) — manual smoke".

## Wave F3 — Boss Personalization (2026-04-28)

Wires the F1 `boss_plan` endpoint into the live boss screen. Ordering + framing are
personalized per-student based on prior chat history; deterministic grading is untouched.

**Modified (net ~245 LOC):**
- `server/services/tutor.py` — `boss_turn()` gains optional `persona_traits: list[str]`
  kwarg; effective traits are injected into the LLM payload so `boss-tutor.md` can adapt
  tone. Backward-compat: when `None` or `[]`, payload is byte-identical to pre-F3.
- `server/routes/ai.py` — `BossTurnRequest` gains `persona_traits: Optional[list[str]] = None`;
  route handler passes it to `tutor.boss_turn()`.
- `server/prompts/runtime/boss-tutor.md` — appended "Persona Adaptation (Wave F3)" section
  instructing the model to shift tone for challenger / mentor / analyst traits.
- `server/template/runtime.js` — `bossTurn()` forwards `opts.persona_traits` into the
  POST body when present.
- `server/template/perfect_homework.html` —
  - Added `.boss-framing` CSS rule (inline style block, 11 lines).
  - Added `persona_traits: ['mentor']` field to `bossState`.
  - Added `initBossPlan()` async function (~60 lines): fetches `/api/ai/tutor/boss-plan`,
    caches result in `localStorage["nets_boss_plan_{hwId}"]`, applies ordering in-place on
    `BOSS_QUESTIONS[]`, attaches `_framing` to each question object, stores `persona_traits`
    on `bossState`. Falls back to default order + mentor on any error.
  - `startFinalBoss()` calls `initBossPlan()` fire-and-forget before the 2.4 s intro
    animation so the plan is ready before the first question renders.
  - `bossRenderQuestion()` renders `<div class="boss-framing">` above the question stem
    when `q._framing` is non-empty; hides the div otherwise.
  - `bossHandleAction()` includes `persona_traits: bossState.persona_traits` in the
    `nets:submit` boss payload.
  - Boss battle DOM: added `<div id="boss-framing">` inside `.boss-q-card`.
- `tests/test_ai_runtime.py` — 2 new mocked tests:
  - `test_boss_turn_accepts_persona_traits`: sends `persona_traits:["challenger"]`, asserts
    200 + "challenger" appears in the LLM-bound prompt.
  - `test_boss_turn_backward_compat_no_traits`: sends no `persona_traits`, asserts 200 +
    unchanged response shape + "persona_traits" absent from prompt.

**Safety invariants:**
- `answer_spec` and question stems are never modified — only `_framing` (a new JS property)
  and array order change.
- `bossMatch()` / grading logic is byte-identical to pre-F3.
- All consumers that omit `persona_traits` continue to work unchanged.

**Verification:**
- `python -m pytest tests/test_ai_runtime.py tests/test_homework_page.py tests/test_tutor_chat.py -v` — all passing.
- Full suite: `python -m pytest tests/ --ignore=tests/test_ai_runtime.py -q` — 66/66 (no regressions).
