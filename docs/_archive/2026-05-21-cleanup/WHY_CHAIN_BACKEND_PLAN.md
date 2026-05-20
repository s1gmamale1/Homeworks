# Why Chain — Redesign Plan (Backend + Frontend + Builder)

**Author:** backend session (Opus 4.7 orchestrator)
**Date:** 2026-05-04
**Reference design:** `Downloads/why-chain-minimal-glass-preview.html`
**Spec:** `Sigma_Edu_3000/standards/system/games/Game_Mechanics_Docs/09_Why_Chain/why-chain-concept-definition.md`
**Frontend session:** runs in another worktree per `docs/IMPLEMENTING_EXTERNAL_DESIGNS.md`

---

## 0. Reframing minute — REDESIGN-IN-PLACE (closest sibling: FB #148)

Why Chain mechanic EXISTS in the codebase but is structurally incomplete. This is closer to Final Boss redesign (#148) than Memory Palace build-new (#152).

| Layer | Current state | Reference / spec target | Relationship |
|---|---|---|---|
| Schema | `WhyChainItem(q, inv, reprompts, expects?)` flat — `_Permissive`, `extra="allow"` | Same fields + grade-aware level count + per-level `accept[]` keyword array + per-level `min_length` + per-level `ack`/`next` | **EXTEND** schema; add `WhyChainLevel` nested model |
| Injector | `_serialize_why_chain` builds 3-level chain, ships `expect` (correct keywords) to client | Side-disjoint: ship `{level, probe, color}` only, keep `accept[]` keywords on server | **REWRITE** for side-disjoint + grade scaling |
| Routes | **NO** `phase=why-chain` route. Runtime calls `phase=sentence-fill` as a workaround | Proper `/api/ai/check-answer?phase=why-chain` (free-text grading: keyword + length, with AI fallback) + `?phase=why-chain-session` end-of-chain tally | **NEW** route + dispatcher branch |
| Runtime UI | Legacy claymorphism CSS (~lines 2165-2281), 3-level state machine `gbState.wc`, calls `phase=sentence-fill` | Apple-glass design, 5-level (grade-scaled) state machine, single-swap-point `gbWCCheckAnswer` → `phase=why-chain` | **REPLACE** (frontend session's job) |
| Builder editor | 3-arg `render(container, data, onChange)`, no grade context, no level-color awareness | 4-arg `render(container, data, onChange, context)`, grade-banded scaffolds (3/4/5 levels), Buzan color preview | **PROMOTE + EXTEND** |
| `_GB_KEYS` | Already includes `gb_why_chain` | Same | **NO CHANGE** |
| Tests | Only schema validation + migration tests; zero runtime/route tests | Add injector + route + drift fence + sweep | **ADD** ~400 LOC tests |
| `docs/API.md` | Not documented (ghost phase) | Pre-emptive entry per `phase=why-chain` + `phase=why-chain-session` | **NEW** entries |
| `CONTRACTS.md` | Has `gb_why_chain` row | Update to reflect new wire format + add config row | **EXTEND** |

**Critical: side-disjoint pattern applies fully here.** Author writes `accept` keywords; runtime currently ships them to client; student can `console.log(GB_WHY_CHAIN)` to see correct keywords. Same answer-leak class as TM/TTT/FB before modernization. The redesign closes it.

**Critical: replace `phase=sentence-fill` workaround.** Current runtime grades Why Chain through Sentence Fill's route. That's wrong from API ergonomics + Sigma's consistency axis. Proper `phase=why-chain` is non-negotiable in this PR.

**XP economy: aesthetic-only per MP precedent.** Server returns `session_xp_display` for the result card (+150/level, +250 chain bonus, -10/hint per spec) but no persistence, no unified counter. When unified XP arrives, this becomes the real delta — schema-compatible.

---

## 1. Data contract (FROZEN once this plan ships)

### 1.1 Storage (DB `homeworks.content_json`) — extended schema

```json
{
  "gb_why_chain": [
    {
      "id": "wc-1",
      "topic": "Photosynthesis",
      "bloom": "L3",
      "pisa": "L3",
      "levels": [
        {
          "level": 1,
          "title": "Surface",
          "color": "l1",
          "probe": "Nima uchun o'simliklar yorug'likka muhtoj?",
          "accept": ["energiya", "energy", "oziq", "food", "ovqat", "fotosintez", "photosynthesis"],
          "min_hits": 1,
          "min_length": null,
          "ack": "Yaxshi boshlanish! Sen sababni yuzaki darajada ushlading.",
          "next": "Endi bir qatlam chuqurroq o'ylaymiz.",
          "hint": "Think about what light gives to the plant — not the final answer."
        },
        {
          "level": 2,
          "title": "Mechanism",
          "color": "l2",
          "probe": "Nima uchun yorug'lik o'simlikka energiya hosil qilishda yordam beradi?",
          "accept": ["fotosintez", "photosynthesis", "chlorophyll", "xlorofill", "glucose"],
          "min_hits": 1,
          "ack": "Zo'r, mexanizm tomonga o'tding.",
          "next": "Endi bu jarayonni boshqa tirik organizmlar bilan solishtiramiz.",
          "hint": "Look for the process name from the lesson. Which process uses light?"
        }
        // ... up to 5 levels per chain
      ]
    }
  ],
  "gb_why_chain_config": {
    "level_count_grade_overrides": { "low": 3, "mid": 4, "high": 5 },
    "timer_seconds": 180,
    "min_chains_per_homework": 1
  }
  // NOTE: XP rubric removed — XP is aesthetic-only (no unified economy yet).
}
```

**Backwards-compatible legacy shim** — existing `gb_why_chain` items shaped as `{q, inv, reprompts[], expects[]}` continue to work. Injector/builder both auto-migrate at read time:
- `q` → `levels[0].probe`
- `inv` → `levels[*].accept` fallback (split on whitespace + comma; if a single word, use as-is in single-element array)
- `reprompts[i]` → `levels[i+1].probe`
- `expects[i]` → `levels[i].accept` (override `inv` fallback if present)

**Invariants (validated server-side):**
- Each chain has 2-5 levels (`level_count_grade_overrides` resolves at runtime/injector).
- Each level has non-empty `probe`. Each level has `accept` (≥1 entry) OR `min_length` (≥1) — at least one acceptance criterion per level.
- `level.color` is one of `l1, l2, l3, l4, l5` (Buzan: blue → green → gold → purple → red, per spec §9).
- `chain.id` unique across the array; auto-fill `wc-{idx+1}` if missing.

### 1.2 Wire format (client gets via `__GB_WHY_CHAIN__` injector — side-disjoint)

```json
[
  {
    "id": "wc-1",
    "topic": "Photosynthesis",
    "level_count": 5,
    "levels": [
      {
        "level": 1,
        "title": "Surface",
        "color": "l1",
        "probe": "Nima uchun o'simliklar yorug'likka muhtoj?",
        "ack": "Yaxshi boshlanish! Sen sababni yuzaki darajada ushlading.",
        "next": "Endi bir qatlam chuqurroq o'ylaymiz.",
        "hint": "Think about what light gives to the plant — not the final answer."
      }
      // ... but NO `accept` array, NO `min_hits`, NO `min_length` (server-only)
    ]
  }
]
```

- `accept` keywords + `min_hits` + `min_length` are **stripped server-side** — kept in module-level `_WC_ANSWER_KEY[hw_id][chain_id][level_idx]` for the route handler.
- `ack`/`next`/`hint` ARE shipped to client (those are AI response strings, not answer keys — already meant to be visible upon request).
- `level_count` matches `len(levels[])` after grade-band slicing — client renders that many color-coded nodes.

### 1.3 Check-answer roundtrip — single endpoint per turn

```
POST /api/ai/check-answer?phase=why-chain
Body:
{
  "homework_id": "<id>",
  "chain_id": "wc-1",
  "level_idx": 0,           // 0-based level index
  "student_text": "yorug'lik o'simlikka energiya beradi...",
  "hints_used_in_level": 0,
  "elapsed_ms_in_level": 4200
}

200 OK (correct):
{
  "is_correct": true,
  "advance": true,                                  // True if at last level → finish
  "ack": "Yaxshi boshlanish!...",                   // From server-side level.ack (echoed for client convenience)
  "next_probe": "Nima uchun yorug'lik...",          // From level[idx+1].probe (or null if last)
  "feedback": "Accepted. The chain moves one level deeper.",
  "xp_delta_display": 150                           // Aesthetic-only
}

200 OK (wrong, more retries available):
{
  "is_correct": false,
  "advance": false,
  "feedback": "Hali emas. The answer is too surface-level. Use the hint if stuck.",
  "retries_remaining": 1,                           // 2 retries default before forced reveal
  "xp_delta_display": 0
}

200 OK (wrong, retries exhausted, force-reveal):
{
  "is_correct": false,
  "advance": true,                                  // Force advance (chain still progresses)
  "force_revealed": true,
  "revealed_canonical": "fotosintez",               // Top-keyword from accept[]
  "next_probe": "...",
  "feedback": "Bu darajaning kaliti: fotosintez. Keyingi savolga o'tamiz.",
  "xp_delta_display": 0
}
```

**Server-side acceptance logic:**
1. Lookup `_WC_ANSWER_KEY[hw_id][chain_id][level_idx]` → `{accept, min_hits, min_length}`. If missing → 404 `wc_level_not_found`.
2. Lowercase `student_text`. Count keyword hits: `hits = sum(1 for kw in accept if kw.lower() in text.lower())`.
3. Length check: `length_ok = (min_length is None) or (len(student_text.strip()) >= min_length)`.
4. **Pass condition:** `hits >= min_hits AND length_ok`.
5. If wrong, increment session retry counter `_WC_RETRIES[hw_id][chain_id][level_idx]`. After 2 failed attempts, return `force_revealed: true` and reveal `revealed_canonical = accept[0]` (the canonical first keyword). Reset retry counter. Force advance.

### 1.4 Session tally roundtrip — end of chain

```
POST /api/ai/check-answer?phase=why-chain-session
Body:
{
  "homework_id": "<id>",
  "chain_id": "wc-1",
  "levels_completed": 5,
  "total_levels": 5,
  "hints_used": 2,
  "force_reveals": 0,
  "elapsed_ms_total": 168000
}

200 OK:
{
  "outcome": "perfect" | "complete" | "complete_no_bonus",
  "outcome_title": "Perfect Chain",
  "outcome_text": "No hints used. You built the full reasoning path independently.",
  "session_xp_display": 1000,                       // 5×150 + 250 chain bonus = 1000
  "timer_status": "in_time" | "over_time",
  "level_label": "Synthesizer" | "Apprentice ↗" | "Apprentice"
}
```

**Outcome thresholds (per spec §4):**
- `perfect` — all levels completed, 0 hints, 0 force-reveals, in time → `xp_display = level_count × 150 + 250`
- `complete` — all levels completed, hints used or force-reveals > 0, in time → `xp_display = (levels_completed × 150 - hints × 10) + 250` (chain bonus still awarded)
- `complete_no_bonus` — timer expired before all levels completed → `xp_display = levels_completed × 150 - hints × 10` (no chain bonus)

### 1.5 Grade-band level scaling (server-side)

| Grade | level count |
|---|---|
| 1–3 | 3 (`level_count_grade_overrides.low`) |
| 4–6 | 4 (`mid`) |
| 7–11 | 5 (`high`) |

Server reads `hw.grade`, slices `levels[:N]` in the wire format. Author writes 5 levels; basic G3 sees first 3.

---

## 2. Backend lane (THIS session)

### 2.1 Files

| File | Change | LOC delta |
|---|---|---|
| `server/schemas/content.py` | Extend `WhyChainItem` with optional `id`, `topic`, `bloom`, `pisa`, `levels: Optional[List[WhyChainLevel]]`. Add `WhyChainLevel` nested model with `level`, `title`, `color`, `probe`, `accept`, `min_hits`, `min_length`, `ack`, `next`, `hint`. Add `WhyChainConfig` model. Add `gb_why_chain_config: Optional[WhyChainConfig]` to `ContentJSON`. Validators: chain.id unique, color in `{l1..l5}`, levels 2-5, accept ≥1 OR min_length set | +110 |
| `server/services/injector.py` | Rewrite `_serialize_why_chain` (lines ~1046-1094) into `_serialize_why_chain(items, config, grade)` — side-disjoint output (strips `accept`/`min_hits`/`min_length`); records key map in `_WC_ANSWER_KEY[hw_id]`; supports legacy `{q, inv, reprompts}` shim; auto-migrates to nested `levels[]`; grade-band slicing | +90 / -50 |
| `server/services/injector.py` | Add `_WC_ANSWER_KEY: dict[str, dict[str, list]]` module-level + `get_wc_answer_key(hw_id)` accessor | +12 |
| `server/routes/ai.py` | New `_check_answer_why_chain(req)` + `_check_answer_why_chain_session(req)` handlers. Helpers: `_wc_outcome(levels_completed, total, hints, reveals, in_time)`, `_wc_session_xp_display(levels_completed, total, hints, outcome)`, `_wc_level_label(outcome)`. In-memory `_WC_RETRIES: dict[hw_id, dict[chain_id, dict[level_idx, int]]]` for retry tracking. Dispatcher branches | +200 |
| `server/services/progress.py` | `_has_why_chain` already exists conceptually via `_GB_KEYS` membership — but extend to handle the new nested `levels[]` shape: `_has_why_chain(content)` checks for any chain with at least one level with non-empty `probe` (covers both legacy `q` and new `levels[0].probe` via the lazy migrator) | +12 |
| `docs/API.md` | New subsections: `phase=why-chain` (per-level grade) + `phase=why-chain-session` (chain tally). Match TM/RLC/FB/TTT/MP shape | +90 |
| `tests/test_why_chain_injector.py` | NEW — 9 tests: legacy `{q, inv, reprompts}` shim still produces nested `levels[]`, new explicit `levels[]` shape passes through, `accept`/`min_hits`/`min_length` STRIPPED from wire, grade-band slicing G3/G6/G10, `_WC_ANSWER_KEY` populated, color values shipped, ack/next/hint shipped | +200 |
| `tests/test_why_chain_check_answer.py` | NEW — 12 tests: keyword hit accepts, length-only accepts (L5), keyword + length both required (L5+), wrong increments retries, 2 wrong = force-reveal returns canonical, session perfect/complete/complete_no_bonus outcomes, hints decrement xp_display, 400 codes (`WC_MISSING_HW`, `WC_MISSING_CHAIN_ID`, `WC_MISSING_LEVEL_IDX`), 404 (`wc_level_not_found`) | +260 |
| `tests/test_why_chain_schema.py` | NEW — 7 tests: levels 2-5 enforced, color enum, accept-or-min_length-required, chain.id uniqueness + auto-fill, legacy shim, `extra="allow"`, config defaults | +130 |
| `tests/test_api_md_documents_every_router_endpoint.py` | Add `"why-chain"` + `"why-chain-session"` to `_CHECK_ANSWER_PHASES` set | +2 |
| `CONTRACTS.md` | Update `gb_why_chain` example with new nested shape (keep legacy reference). Update injector contract table row for `GB_WHY_CHAIN` to note side-disjoint. Add `gb_why_chain_config` to optional config keys section | +35 |

**Total backend:** ~615 LOC source + ~590 LOC tests.

### 2.2 Side-disjoint injector pattern — applied (load-bearing)

```python
# server/services/injector.py
def _serialize_why_chain(items, config, grade):
    """Returns wire array; populates _WC_ANSWER_KEY[hw_id][chain_id] = {level_idx: {accept, min_hits, min_length}}."""
    cfg = {**_WC_DEFAULTS, **(filter_none(config) or {})}
    level_count = _resolve_wc_level_count(grade, cfg)
    wire, key_map = [], {}
    for idx, raw in enumerate(items or []):
        chain_id = raw.get("id") or f"wc-{idx+1}"
        # Auto-migrate legacy shape
        levels_raw = raw.get("levels") or _migrate_legacy_wc(raw)
        if not levels_raw:
            continue
        # Slice per grade
        levels_raw = levels_raw[:level_count]
        wire_levels = []
        chain_key_map = {}
        for li, lvl in enumerate(levels_raw):
            wire_levels.append({
                "level": li + 1,
                "title": lvl.get("title", ""),
                "color": lvl.get("color", f"l{li+1}"),
                "probe": lvl["probe"],
                "ack": lvl.get("ack", ""),
                "next": lvl.get("next", ""),
                "hint": lvl.get("hint", ""),
            })
            chain_key_map[li] = {
                "accept": lvl.get("accept", []),
                "min_hits": lvl.get("min_hits", 1),
                "min_length": lvl.get("min_length"),
            }
        wire.append({
            "id": chain_id, "topic": raw.get("topic", ""),
            "level_count": len(wire_levels), "levels": wire_levels,
        })
        key_map[chain_id] = chain_key_map
    return wire, key_map
```

The legacy migrator splits `inv` on whitespace+comma, treats each token as an `accept` candidate, fills missing `accept[]` arrays. Single-word `inv` becomes a 1-element array.

### 2.3 Out of scope (separate PRs)

- **Premium dynamic AI follow-ups** — spec §7 says Premium tier gets LLM-generated `ack`/`next`. v1 ships static author-supplied strings only. Future PR adds an opt-in flag + Kimi/Gemini call wrapper.
- **AI-fallback grading** — current Sentence Fill route has `allow_ai_fallback: true`. v1 of Why Chain does pure keyword + length matching. AI fallback in v2 if keyword precision is insufficient.
- **Multi-topic chains** (Premium) — v1 single-topic per chain.
- **Cross-PR mastery persistence** — defer (same as TTT/MP).
- **Chain branching / non-linear** — out; spec is explicitly linear.
- **Resume from last completed level** — out; v1 is single-session.

---

## 3. Frontend lane (OTHER session — copy this section into the frontend brief)

### 3.1 Files

| File | Change | LOC delta |
|---|---|---|
| `server/template/perfect_homework.html` | **REPLACE** Why Chain CSS block (lines ~2165-2281 + dark mode 6536-6550) with reference design's Apple-glass scoped to `.gb-wc-*`. **REPLACE** HTML markup (lines ~7779-7794) with reference's structure (topbar with timer + dots, hero card, chain progression card with 5 color-coded nodes, dialogue card with bubbles + question box, answer textarea card with hint/clear buttons, result card). **REWRITE** JS state machine: `gbState.wc` extends to `{chainIdx, levelIdx, retries, xp, hints, timer, expired, complete}`. New handlers: `gbInitWC`, `gbWCRenderChain`, `gbWCRenderLevel`, `gbWCEvaluate`, `gbWCUseHint`, `gbWCFinish`, `gbWCStartTimer`. **SWAP endpoint adapter** from current `phase=sentence-fill` to single-swap-point `gbWCCheckAnswer(hwId, chainId, levelIdx, studentText, hintsUsed, elapsedMs)` → `phase=why-chain`. Add session-end `gbWCSubmitChainSession`. Drop client-side `expect` reads — trust server response | +500 / -380 |
| `server/template/perfect_homework.html` | Add `const GB_WHY_CHAIN_RAW = __GB_WHY_CHAIN__;` already exists; rename or extend if needed | +1 |
| `tests/test_runtime_why_chain_ui.py` | NEW — JSDOM smoke: 5 color-coded nodes render, level dot states (active/done/hinted), timer countdown, hint button decrements XP display, evaluate calls adapter, force-reveal renders revealed canonical, session result renders Perfect/Complete/over-time outcomes | +200 |
| `tests/test_phase_announcement_card.py` | Confirm `("why_chain", "game.why_chain")` registry entry stays / extends | +0 / +6 |
| `i18n/strings.js` (or wherever runtime strings live) | New i18n keys for the redesigned strings: `wc.heroTitle/Sub`, `wc.depthLabel/{l1..l5}`, `wc.feedbackAccepted/RejectedSurface/RejectedRetry/ForceReveal`, `wc.toastTryDeeper/HintUsed/TimerExpired`, `wc.resultPerfect/Complete/CompleteNoBonus` × 3 langs | +50 |

### 3.2 Single-swap-point endpoint adapter (load-bearing)

```javascript
async function gbWCCheckAnswer({ chainId, levelIdx, studentText, hintsUsedInLevel, elapsedMsInLevel }) {
  const ctx = window.__hwContext || {};
  const hwId = ctx.hwId || ctx.homework_id || ctx.homeworkId || null;  // canonical 3-key idiom
  if (!hwId) return null;
  try {
    const res = await fetch('/api/ai/check-answer?phase=why-chain', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        homework_id: hwId, chain_id: chainId, level_idx: levelIdx,
        student_text: studentText, hints_used_in_level: hintsUsedInLevel, elapsed_ms_in_level: elapsedMsInLevel
      })
    });
    if (!res.ok) throw new Error('check-answer failed');
    return await res.json();
  } catch (e) {
    console.warn('[wc] check-answer error', e);
    return null;
  }
}
```

### 3.3 Visual contract (reference design — direct port)

- Apple-glass topbar with 3-dot phase progression + 03:00 timer pill
- Hero card: "AI Socratic Dialogue" kicker + "Answer why. Then why again." + xp pill
- Chain progress card: 5 horizontal color-coded nodes (l1 blue / l2 green / l3 gold / l4 purple / l5 red — Buzan)
- Dialogue card: AI/student bubbles (different gradients), question box with depth pill ("Level N · Title")
- Answer card: textarea + hint button (-10 XP) + clear button + feedback bar
- Result card: 4-cell score grid (Levels / Hints / Timer / XP) + outcome title
- Dock submit button

### 3.4 Out of scope for v1 (frontend)

- Animated line drawing between completed nodes
- Branching reasoning tree visualization (Premium per spec)
- Audio cues
- Animated AI bubble typing
- Reverse chain mode (Premium)

---

## 4. Builder lane (BACKEND session per scope)

### 4.1 Files

| File | Change | LOC delta |
|---|---|---|
| `frontend/js/editors/games/why-chain.js` | Promote to **4-arg signature** `render(container, data, onChange, context)`. Use `context.grade` to derive default level count via `WhyChainHelpers.levelCountFor(grade)` (3/4/5). Lazy-migrate legacy `{q, inv, reprompts}` items to nested `levels[]` on first render (so old homeworks display in the new UI cleanly). Per-level form: title + color picker (5 swatches Buzan) + probe + `accept[]` editable chip list + min_hits + min_length + ack + next + hint. Inline non-blocking validation. Auto-assign chain.id on save | +250 |
| `frontend/js/editors/_why-chain-helpers.js` | NEW — exports: `levelCountFor(grade)`, `colorPaletteForLevel(idx)` (returns Buzan color), `migrateLegacyChain(legacyItem)` (`{q, inv, reprompts}` → `{id, levels[]}`), `ensureChainId(chain, idx)`, `validateLevel(level)`, `validateChain(chain)`. Mirror `_ttt-helpers.js` shape | +180 |
| `frontend/js/editors/game-breaks.js` | Update `normalizeWhyChain` to handle BOTH legacy AND new nested shape. Pass through `levels[]` if present, else lazy-migrate. Keep `extra="allow"` semantics | +25 |
| `frontend/js/builder.js` | No structural change — `gb_why_chain` already in CONTRACT_KEYS + phase routing | +0 |
| `frontend/builder.html` | Add `<script src="/js/editors/_why-chain-helpers.js?v=__VERSION__"></script>` BEFORE `why-chain.js` | +1 |

### 4.2 Buzan color palette (per spec §9 — load-bearing)

Builder shows 5 color swatches per level slot:
- **L1 Surface** — `--accent` (Apple blue) — cool, beginning
- **L2 Mechanism** — `--green` (Apple green) — process
- **L3 Principle** — gold/amber `#a36500` — depth
- **L4 Synthesis** — `--purple` — synthesis
- **L5 Paradox** — red `#a82821` — peak / paradox

Color is auto-assigned by level index but editable. Premium author can override.

---

## 5. Verification matrix

| Layer | Verification |
|---|---|
| Schema | `pytest tests/test_why_chain_schema.py -v` — 7 green |
| Injector | `pytest tests/test_why_chain_injector.py -v` — 9 green; grep rendered HTML for `"accept"` ABSENT inside `GB_WHY_CHAIN` (side-disjoint audit), `"min_hits"` ABSENT |
| Routes | `pytest tests/test_why_chain_check_answer.py -v` — 12 green |
| API doc fence | `pytest tests/test_api_md_documents_every_router_endpoint.py` — `phase=why-chain` + `phase=why-chain-session` documented |
| Runtime | `pytest tests/test_runtime_why_chain_ui.py -v` — JSDOM cases green |
| Local smoke | uvicorn 8765, render `/h/<id>` with why-chain homework, walk all 5 levels, side-by-side compare to `Downloads/why-chain-minimal-glass-preview.html` |
| Answer-leak audit | `_serialize_why_chain` round-trip CLI — wire format contains zero `accept` / `min_hits` / `min_length` keys |
| Cross-PR sweep | `_has_why_chain` extended for nested shape, `docs/API.md` covers both phases, `STATE.md` notes deferred AI follow-ups, `CONTRACTS.md` updated |
| Legacy compat | Existing homeworks with `{q, inv, reprompts}` shape continue to render + grade correctly through the lazy-migrator |

---

## 6. Sequencing

```
T1 — Schema extension + side-disjoint injector + legacy migrator                Sonnet 4.6  (~225 LOC, mechanical w/ migrator nuance)
   │
   ├──► T2 — /api/ai/check-answer phase=why-chain + phase=why-chain-session     Opus 4.7    (~200 LOC, judgment — keyword/length/retry logic)
   │
   ├──► T4 — Builder editor 4-arg + helpers + Buzan color UI                    Sonnet 4.6  (~430 LOC mechanical)
   │
   ▼
T3 — docs/API.md + Sigma drift fence + cross-PR sweep                            Sonnet 4.6  (~85 LOC docs/tests)
   │
   ▼
T5 — Local smoke + answer-leak grep audit + legacy-compat smoke                  inline
   │
   ▼
T6 — Push branch + open PR (per revoked-protocol rule, no separate auth)
```

**T2 + T4 file-disjoint** (T2: routes + tests; T4: frontend builder + helpers). Run in parallel after T1.

**Worktree:** `Homeworks-wc-backend` (fresh, off `origin/server` `b4318bf`).
**Re-fetch origin/server** before each chunk + once at the end.

---

## 7. Open decisions (debate to ~90% before dispatch)

1. **Side-disjoint server-side answer-check — confirm?** YES = closes the same answer-leak class as TM/TTT/FB/RLC. **Recommend YES.**
2. **Replace `phase=sentence-fill` workaround with `phase=why-chain`?** YES = clean architecture, parallel with other mechanics. **Recommend YES.** (The runtime currently calling `phase=sentence-fill` will swap to `phase=why-chain` in the frontend session's PR. No regression — both routes coexist briefly.)
3. **Grade-banded level count (3/4/5)?** Per spec §2. **Recommend YES** — matches TTT's grade-banded scaffolds pattern.
4. **`gb_why_chain_config` authorable + spec defaults?** **Recommend YES** mirror TttConfig/MemoryPalaceConfig pattern.
5. **XP economy aesthetic-only?** Per MP precedent + user's earlier direction "no unified XP counter or ecosystem yet". **Recommend YES** — server returns `session_xp_display`, no persistence.
6. **Server-side retry counter (2 retries before force-reveal)?** Per reference HTML behavior. **Recommend YES** — server-tracked via `_WC_RETRIES[hw_id][chain_id][level_idx]`.
7. **Force-reveal on retry exhaustion — show top accept[0] keyword?** Per reference HTML's "right answer" reveal. **Recommend YES** — accept[0] is the canonical keyword by author convention.
8. **Premium dynamic AI follow-ups (LLM-generated `ack`/`next`)?** Spec §7. **Recommend DEFER** to v2 — separate PR, separate prompt template, separate cost budget.
9. **Lazy migrate legacy `{q, inv, reprompts}` items at injector + builder time?** Existing homeworks must keep working. **Recommend YES** — don't force a one-shot DB migration.
10. **Buzan color palette adopted from spec §9?** Cool→warm 5-tier. **Recommend YES** — visual pedagogy, low CSS cost.

If you authorize all 10 as recommended, plan is ~95% locked.

---

## 8. Out of scope (Wave M+ / future PRs)

- Premium dynamic AI follow-ups (LLM-generated)
- AI-fallback grading on top of keyword/length
- Multi-topic chains (Premium per spec)
- Branching reasoning tree visualization (Premium)
- Resume from last completed level
- Mastery persistence (cross-session "Synthesizer" tier promotion)
- Reverse chain mode (Premium)
- Animated line drawing between nodes
- Audio cues / typing animation
- Phase 5 (Consolidation) pipeline placement override
- Real XP economy wiring (when unified system arrives, `session_xp_display` becomes the real delta)
- Frontend runtime UI swap (separate session — §3 of this plan)

---

## 9. Risks + mitigations

| Risk | Mitigation |
|---|---|
| Legacy `{q, inv, reprompts}` items break in new injector | Lazy-migrator covers; test pin `test_inject_serializes_legacy_shape_into_new_levels` |
| Current runtime calls `phase=sentence-fill` and breaks when frontend lands | Both routes coexist (Sentence Fill stays); runtime swap is in frontend's PR. No breakage during transition window. |
| Side-disjoint missed a keyword field | Server-side audit test grep `_serialize_why_chain` output for `accept`/`min_hits`/`min_length` ABSENT |
| Grade-band slicing eats author's last (most paradoxical) levels | Slicing is `levels[:N]` — front-loads. Documented; author writes 5, basic G3 sees first 3 (Surface→Mechanism→Principle), missing Paradox. Acceptable for v1; future override flag possible. |
| Legacy `inv` → `accept` migration produces noisy keywords | Tokenize on whitespace + comma + lowercase; if single-word, single-element array. Test case for both shapes. |
| Force-reveal exposes the canonical → student abuses by deliberately failing twice | Acceptable — force-reveal still costs the level's +150 XP (xp_delta_display: 0). Not a real exploit since v1 XP is aesthetic. |
| Frontend session lands their PR before backend → broken `phase=why-chain` route | Same scar tissue as MP — backend lands first; frontend rebases on top. |
| Builder edits to legacy shape silently lose data on save | Save path always writes new nested shape after migrator runs; round-trip pin test |

---

## 10. Spec → plan compliance ledger

| Spec rule | Plan section |
|---|---|
| Linear chain progression L1→LN | §1.1 levels[].level field |
| Grade-scaled depth (G2-3=2-3, G3-4=4, G5-6+=5) | §1.5 + §2 grade slicing |
| Keyword + length acceptance | §1.3 server-side acceptance logic |
| AI never gives direct answer | Server `feedback` + `next_probe` are not solutions; spec compliance |
| Acknowledgment phrase before deeper probe | §1.1 `level.ack` + `level.next` |
| Hint cost -10 XP | §1.3 + reference HTML; aesthetic-only per §7 #5 |
| Timer 3 minutes (no auto-end) | §1.4 timer_status + frontend client-tracked |
| +150/level, +250 chain bonus | §1.4 _wc_session_xp_display |
| Premium dynamic AI follow-ups | OUT OF SCOPE (§7 #8, §8) |
| Premium cross-topic chains | OUT OF SCOPE |
| Buzan color encoding (cool→warm) | §1.1 `level.color` + §4.2 builder palette |
| Resume from last completed level | OUT OF SCOPE (v1 single session) |
| Mastery tiers (Synthesizer etc.) | OUT OF SCOPE (cross-session persistence) |
| 15+ char min for L5, 20+ for L6 | §1.1 `min_length` field optional per level; spec values authored, not hardcoded |
