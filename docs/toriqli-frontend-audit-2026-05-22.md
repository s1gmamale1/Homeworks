# Toriqli Frontend Audit — 2026-05-22

**Branch:** Toriqli @ `7c1bdfe` (`Document Uzbek linguist review gate`)
**Base:** DaddysBranch @ `8bfb91a` (Toriqli is 2 commits ahead, DaddysBranch 0 ahead)
**Working-tree state:** 17 modified + ~17 untracked WIP files (flashcard/reasoning/anti-cheat suite, restored from pre-rebase stash)

## TL;DR

| Area | Result |
|---|---|
| Frontend build (`npm run build`) | **FAIL** — pre-existing TS5101 in `tsconfig.json:18` |
| Full WIP pytest (7 new suites) | **156/156 pass** in 1.08s |
| PRACTICE_LOCKED gate test suite | **12/12 pass** in 0.93s |
| `/api/runtime` answer-key strip | **PASS** — 0 leak fields in 39KB payload |
| `/api/runtime/.../gate-state` schema | **PASS** — `{cbp, mc, practice_arc_unlocked}` valid |
| Live `/api/ai/check-answer` gate enforcement | **FINDING** — bypassed when `ai_backend:none` |
| 4-viewport visual capture | **PARTIAL** — gate quotes captured, Hub not reached (multi-step gate flow) |
| Memory Check QA | **BLOCKED** — 0 HWs in `nets.db` have `memory_check` populated |
| Builder round-trip QA | **BLOCKED** — depends on Memory Check fixture |

## Findings

### 🔴 F1. Frontend build broken on `origin/Toriqli` HEAD (pre-existing)

```
tsconfig.json(18,5): error TS5101: Option 'baseUrl' is deprecated and will stop functioning in TypeScript 7.0.
Specify compilerOption '"ignoreDeprecations": "6.0"' to silence this error.
```

`tsconfig.json:18` uses `"baseUrl": "."` to support the path aliases `@/*`, `@shared/*`, `@runtime/*`, `@builder/*`. Current TS version treats the deprecation as an error.

**Fix (1 line):** add `"ignoreDeprecations": "6.0"` to `compilerOptions` in `frontend/app/tsconfig.json`.

Not patched here — pre-existing on the protected branch, owner sign-off recommended.

### 🔴 F2. Practice-arc gate bypassed when AI backend unavailable

Live POST to `/api/ai/check-answer` with `game_kind:"tile_match"` against an uninitialized session returns:

```
HTTP 200
{"correct": false, "score": 0.0, "source": "ai_unavailable", ...}
```

Expected per `server/routes/ai.py:614`: `HTTPException(403, code="PRACTICE_LOCKED")`.

In `tests/test_practice_gate_server_enforced.py` the suite passes (12/12) because the tests **patch AI to be available**. On a deployment where `/api/health` reports `"ai_backend":"none","ai_ready":false`, the AI-unavailable branch returns 200 BEFORE `_enforce_practice_unlocked(req)` raises.

**Risk:** A locked practice-arc game appears to "respond" with a benign no-grade message instead of refusing — UX may interpret this as "answer submitted, just no score yet" and allow further interaction.

**Suggested fix:** call `_enforce_practice_unlocked(req)` at the top of every practice-arc grading branch, before any AI-availability check. Add a regression test that exercises the AI-unavailable path with a locked session and asserts 403, **without patching the AI backend.**

### 🟡 F3. Memory Check fixture gap — `HW-20260521-001` does not exist; zero HWs have `memory_check`

The handoff references `http://127.0.0.1:8765/h/HW-20260521-001`. That HW is not in `nets.db` (latest seeded: `HW-20260507-010`). Scanning all 44 active HWs:

| Field | Hits |
|---|---|
| Non-empty `flashcards[]` | 33 |
| `memory_check` key present | **0** |

Consequence: Tasks 3 (Memory Check visual QA), 4 (Unlock flow QA), and 5 (Builder flashcard_ref round-trip) in the brief are blocked at the data layer.

The WIP includes test fixtures at `tests/fixtures/flashcard_demo/*.json` with the `{title, subject, grade, mode, content_json}` wrapper — they look like seed payloads but aren't loaded into the runtime DB.

**Recommended next step:** add a `scripts/seed_v2_demo.py` (or extend `_seed_v2_demo.py`) that materializes a single HW with both `flashcards[]` and `memory_check.items[]` covering all four supported types (`mcq`, `fill_blank`, `choose_explanation`, `true_false`) with `flashcard_ref` linkage, then re-run this audit.

### 🟢 F4. Runtime endpoint correctly strips answer keys

`GET /api/runtime/homeworks/HW-20260505-005` → 200, 39262 bytes. Recursive scan for fields named `answer / correct / correct_answer / correct_choice / answer_key / correct_index / is_correct / solution` returned **0 hits**. Top-level keys exposed: `content_json, flow_version, grade, id, lang, subject, title`.

### 🟢 F5. Gate state schema valid

`GET /api/runtime/homeworks/HW-20260505-005/gate-state?session_id=audit-<ts>`:

```json
{
  "cbp": {"passed": false, "checkpoints_correct": 0, "checkpoints_total": 3, "threshold": 2},
  "mc":  {"passed": false, "score_pct": 0, "correct": 0, "total": 0, "threshold_pct": 60},
  "practice_arc_unlocked": false
}
```

Both gates (`cbp`, `mc`) and the unlock flag are present with correct types.

### 🟡 F6. Browser MCP tooling not usable on this host

`mcp__ruflo__browser_session_record` returns `"command not found: npx"` — the MCP host process can't resolve `npx`, even though it's installed at `C:\Program Files\nodejs\npx` and accessible from the user shell. Worked around by installing Playwright 1.46.0 + chromium-headless-shell-1223 in `.audit-tmp/` and driving screenshots directly via `node`.

**Audit infra recommendation:** ensure the Ruflo MCP server inherits `PATH` (or set `RUFLO_NPX_PATH`) so the browser tools work without manual workarounds.

### 🟡 F7. Multi-step gate flow — Hub not directly accessible after single CTA click

Walking `HW-20260505-005` at 4 viewports: clicking "Vazifani boshlash" advances to a **second** gate card (Mirziyoyev / philosophy quotes), not the Learning Hub. The runtime cycles through multiple intro cards before exposing the Hub. This makes any Playwright test that asserts on Hub state after the first CTA fragile.

**Suggested regression test:** at `tests/test_runtime_hub_visual.py` (new), use Playwright to:
1. Open `/h/<HW>`
2. Click any "next"/"start" CTA in a loop with a max-iterations cap
3. Wait until the URL hash changes or a Hub-specific selector becomes visible
4. Snapshot + assert no clipped text and tutor bubble doesn't overlap any primary CTA

## Visual evidence (4 viewports)

Captured at `docs/audit-screenshots-2026-05-22/`:

```
01-gate-mobile-iphone15-390x844.png         184 KB
01-gate-mobile-iphone15plus-430x932.png     211 KB
01-gate-tablet-ipad-768x1024.png            330 KB
01-gate-desktop-1440x900.png                513 KB
02-hub-* / 04-after-gate-*                  (same as 01-* — gate didn't advance on first attempt)
```

Observations from gate-card layout across viewports:
- **390x844 (iPhone 15)**: Title text wraps over 4 lines, primary CTA is full-width with generous tap target, tutor bubble (?) bottom-right doesn't overlap CTA — OK.
- **430x932 (iPhone 15+)**: Same layout, slightly more breathing room — OK.
- **768x1024 (iPad)**: Card stays the same physical size — feels under-scaled for tablet width — visual finding.
- **1440x900 (desktop)**: Card and title look small/cramped relative to viewport — there's a lot of empty whitespace at top/bottom — visual finding.

Full-Hub visual QA (overlap/clip checks, Bildim/Bilmadim flashcard walk, Weak chip verification, MCQ/TF/CE/FB Memory Check feedback positioning) **was not completed** in this pass.

## Suggested regression tests

Per the audit brief's "Suggested Regression Tests" section, scoped to what's verifiable today:

| Test | Path | Status |
|---|---|---|
| Playwright screenshot smoke (Hub + Flashcards + Memory Check, 4 viewports) | `tests/e2e/test_visual_smoke.spec.ts` (new) | **TODO** — depends on F3 fixture |
| Source-level guard: Flashcards uses menu-style tokens; Hub unchanged | `tests/test_flashcard_source_guard.py` (new) | **TODO** — needs token catalog from `frontend/app/src/runtime/styles/` |
| Builder round-trip for `flashcard_ref` | `tests/test_builder_flashcard_ref_roundtrip.py` (new) | **TODO** — depends on F3 fixture |
| Practice gate enforced when AI unavailable | `tests/test_practice_gate_ai_unavailable.py` (new) | **TODO** — covers F2 finding |
| Existing flashcard prompt quality | `tests/test_flashcard_prompt_quality.py` | **PRESENT (WIP)** — part of 156 passing tests |
| Existing PRACTICE_LOCKED suite | `tests/test_practice_gate_server_enforced.py` | **PRESENT** — 12/12 pass (but see F2) |
| Existing anti-cheat grading | `tests/test_anticheat_grading.py` | **PRESENT (WIP)** — passing |
| Existing tag validation | `tests/test_tag_validation.py` | **PRESENT (WIP)** — passing |
| Existing reasoning checkpoints | `tests/test_reasoning_checkpoints.py` | **PRESENT (WIP)** — passing |

## Audit-brief task coverage

| # | Task (per brief) | Coverage |
|---|---|---|
| 1 | Mobile QA pass for Hub (4 viewports) | **Partial** — gate captured, Hub not reached (F7) |
| 2 | Flashcards menu-style polish + Bildim/Bilmadim + Weak chip | **Not done** — multi-step gate + interactive walk needed |
| 3 | Memory Check visual QA (mcq/tf/ce/fb) | **Blocked** by F3 (no fixture) |
| 4 | Unlock flow QA (CBP + MC pass → unlock) | **Blocked** downstream of F3 |
| 5 | Builder QA for flashcard_ref round-trip | **Blocked** downstream of F3 |
| 6 | Accessibility + reduced-motion | **Not done** — needs interactive walk |
| 7 | Backend/API sanity | **Done** — F4 ✅, F5 ✅, F2 finding |

## Sign-off checklist (not green yet)

- [ ] F1 — `tsconfig.json` baseUrl fix landed; `npm run build` passes
- [ ] F2 — gate enforcement test added that does NOT patch AI; ai-unavailable branch returns 403 for locked sessions
- [ ] F3 — seeder produces v2 HW with `flashcards[]` + `memory_check.items[]` covering 4 types
- [ ] F6 — MCP host PATH fix or documented workaround
- [ ] Tasks 1, 2, 6 — interactive visual walk (mobile + a11y) completed with screenshots committed
- [ ] Tasks 3, 4, 5 — re-run after F3 seeder lands
