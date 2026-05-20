# Game-Break Audit — Tile Match, Puzzle Lock, AQ revisit (2026-05-07)

**Branch:** `claude/game-break-audit-2026-05-07` (off `server@72d0507`).
**Mandate:** audit only — no edits until approval. PR #165 is merged; do not duplicate its work.

## What was inspected

| Layer | Files / artifacts |
|---|---|
| Runtime | `server/template/perfect_homework.html` — `.gb-tm-*` (l. 2353–2802), `.gb-pl-*` (l. 3458–3614, 5092, 6770–6787, 7663), JS `gbInitTM`/`gbTMRenderBoard`/`gbTMHandleResponse` (l. 13612–13893), `gbInitPL`/`gbPLClickTile`/`gbPLAction` (l. 14554–14722) |
| Server  | `server/services/injector.py` `_serialize_tile_match` (l. 469–518) + flat-shape adapter for `gb_puzzle_lock` (l. 1268–1281); `server/routes/ai.py` `_check_answer_tile_match` (l. 576+) |
| Prompts | `server/prompts/math-algebra/game-breaks.md`, `server/prompts/geometriya-g7-11/game-breaks.md` |
| Data    | `nets.db` rows for `HW-20260505-005` (geo G8), `HW-20260505-009` (alg G7), `HW-20260505-010` (alg G7) |
| Tests   | `tests/test_tile_match_*`, `tests/test_runtime_tile_match_ui.py` |

## Real-data baseline

| Homework | Subject | TM source | TM rendered? | PL items | AQ items (capture=true) |
|---|---|---|---|---|---|
| HW-20260505-005 | geometriya G8 | `gb_memory_match` (6 pairs, all complementary-angle: `sin 35°`↔`cos 55°`, `tg 25°`↔`ctg 65°`, `sin(90°−α)`↔`cos α`, …) | ✅ via `_serialize_tile_match` legacy shim | 5 step-by-step proof items (`Qadam 1..5`) | 6 (3 capture) |
| HW-20260505-009 | math-algebra G7 | `gb_memory_match` (8 pairs: `A^2-B^2`↔`(A-B)(A+B)`, `(2a+3b)^2-(3a-2b)^2`↔`(-a+5b)(5a+b)`, `Guruhlash`↔`umumiy qavsni topish`, …) | ✅ | 5 factoring-method step items | 6 |
| HW-20260505-010 | math-algebra G7 | `gb_memory_match` empty (no TM rendered) | — | none | 6 (3 capture) |

**Important:** zero homeworks have content under the canonical `gb_tile_match` key — all live demo TM content is pulled from the legacy `gb_memory_match` field through `_serialize_tile_match`'s `legacy_pairs` shim. This is fine functionally but means the schema-test coverage in `tests/test_tile_match_*` does not exercise what students actually see.

---

## Bug list

| ID | Severity | Game | File / selector / function | Repro | Expected | Actual | Suggested fix |
|----|----------|------|----------------------------|-------|----------|--------|---------------|
| **PL-01** | **Critical** | Puzzle Lock | `gbInitPL` `perfect_homework.html:14554–14591` | Open `HW-20260505-005` → Stage 5 → reach Puzzle Lock. 5 items + 3×3 grid. Initial cells `[0..4]` populated, `[5..8]` left as raw `null`; `emptyIdx=8`; 200-iteration scramble swaps only `emptyIdx` with one neighbor at a time. | Each cell is either a real tile or the single empty slot the student is solving. | 3 stale `null` cells become **click-dead** (empty-styled + render dashed but `gbPLClickTile` returns at `if (!cell) return;`). Student sees 4 dashed cells, can swap into only 1, with no UI hint why. | When `tileCount < size*size - 1`, either reduce grid size to fit (e.g. drop to `2×3` for 5 items) or pad with blank-but-locked decoy tiles. Easier short-term: bail out of sliding mode entirely and switch to the linear mechanic in PL-02. |
| **PL-02** | **Critical** | Puzzle Lock | `gbInitPL`/`gbPLClickTile`/`gbPLAction` | Whole game loop. | User-stated intent: only one slot open at a time, student answers IN ORDER, correct → unlock NEXT slot, wrong → feedback/hint, final state = sequence solved. | Implementation is a 15-style sliding puzzle: random scramble + neighbor-swap mechanic, "in place" XP based on `cell.pid === idx`. Order-of-solving is destroyed by the scramble; "Qadam 1..5" tiles end up randomly placed. | Replace mechanic with a linear stepper: one active step at a time, `currentStep` starts at 0, question box always shows `pl.tiles[currentStep].q`, correct answer increments `currentStep` and "locks" the previous step in green; wrong shows the per-step hint (currently authored hints aren't even rendered — the prompt schema lacks a `hint` field for PL items). Status pill becomes "Qadam X / N" instead of "Mos joyga: X / Y". |
| PL-03 | High | Puzzle Lock | `.gb-pl-cell` CSS l. 3478–3496 | View geo PL — each cell is `aspect-ratio: 1/1`, `font-size:13px`, `overflow:hidden`. Real content is HTML like `<b>Qadam 1.</b> ABC — to'g'ri burchakli uchburchak; ∠C = 90°, ∠A = α (berilgan).` (~80 chars). | All step text is readable inside the cell. | At 3×3 in 420 px max grid → ~133 px square cell. With `overflow:hidden` + 13 px font, only the first ~3 lines render; the rest is clipped. | Drop `aspect-ratio: 1/1` once mechanic switches to linear (PL-02); render the active step as a card-width block with full text, not a square. If sliding mechanic is kept short-term, at minimum increase `min-height` to `auto` and remove `overflow:hidden` for cells with text-heavy content. |
| PL-04 | High | Puzzle Lock | `gbPLAction` l. 14680–14687 | Geometry PL Step 5 expects `cos α`. Student types `cos alfa` or `cosα`. | After PR #165 the AQ/Boss accept α/alfa/alpha; PL should be at parity. | PL uses its own ad-hoc `norm` (lowercase + collapse-spaces only). `mathNormalize` from PR #165 is **not wired in**, so `cos alfa` and `cos α` mismatch even though the demo UX promised they would. | Replace the local `norm` with `mathNormalize` (already in `window.mathNormalize`) — same dual-pass pattern PR #165 used for `gbAQAction`. |
| PL-05 | Medium | Puzzle Lock | `gbInitPL` "Scramble" comment l. 14576 | `200 random valid moves keeps puzzle solvable (parity preserved).` | Comment is correct for a true 15-puzzle. | With the stale-null bug (PL-01), the scramble does NOT preserve solvability — only one of the 4 `null` cells participates in moves; tiles can end up in positions the algorithm can never reach. | Moot once PL-02 lands. While sliding mechanic is live, fix PL-01 first or scramble breaks the solvability guarantee. |
| PL-06 | Medium | Puzzle Lock | content `_serialize` shape (`gb_puzzle_lock` adapter l. 1268–1281) + prompts | DB items are `{content, q, a}`. Geometry prompt §51 promises "Diagram assembly / Proof-step ordering" + "every tile that references a figure must include a Visual Layer diagram" (SVG). | Each step has a small diagram fragment when the step references geometry. | Real content is plain HTML (no `<svg>` inside `content`). The runtime renders via `innerHTML` so SVGs would work — they're just absent in authored data. | Out of scope per task brief (no prompt rewrite). Worth flagging for a future prompt-tightening PR; runtime fix is prepared once authors comply. |
| **TM-01** | **High** | Tile Match | `.gb-tm-tile` CSS l. 2556–2606 | Open `HW-20260505-009` → Stage 5 TM. Math content `A^2-B^2`, `(2a+3b)^2-(3a-2b)^2`, `(x^2+x+2)(x^2-x+2)` — `^` is literal. | Math expressions render with proper exponents (`A²`, `(2a+3b)²`) — at minimum no caret-as-text. | Tile uses `innerHTML = entry.text` so the `^` ASCII renders as caret literal; `A^2-B^2` reads as ugly code. Geometry TM uses `°` and Greek `α` and renders fine; algebra TM is the regression. | Inject a small renderer step: server-side or `gbTMRenderBoard` runs `text.replace(/\^(\d+)/g, '<sup>$1</sup>')` (and `_` for subscript) on TM tile content before assignment. Cheap, scoped to TM. Same fix should apply to Memory Sprint / Boss expressions if they share the issue (out of scope today). |
| TM-02 | High | Tile Match | `.gb-tm-tile { font-size: 13.2px; min-height: 58px; padding: 12px 13px; text-align: left; }` | View algebra TM pair `(2a+3b)^2-(3a-2b)^2` ↔ `(-a+5b)(5a+b)`. | Math expressions readable at-a-glance. | 13.2 px is below algebra-readable threshold; long parenthesised expressions wrap awkwardly inside ~140 px column. | Bump `font-size` to 14.5 px on tiles with math content (detect via `^`/`²`/`α-ω`/`±` regex on text) or unconditionally; widen tile min-height to `64px`; `text-align: center` for short formula tiles. Keep `text-align: left` for Boolean/text-only pairs. |
| TM-03 | Medium | Tile Match | `.gb-tm-tile.selected` l. 2591–2595 | Click a left tile in dark mode. | Selected state visually distinct from hover and from neighboring tiles. | The selected gradient is a faint blue tint over a light glass background. In dark mode it's even subtler because the `linear-gradient(rgba(0,102,204,.12), rgba(255,255,255,.22))` includes a near-white stop that doesn't contrast with the dark surface. | Add a sturdier selected ring (`box-shadow: 0 0 0 2px var(--accent)`) and a dedicated `[data-theme=dark] .gb-tm-tile.selected` override that drops the white stop. |
| TM-04 | Medium | Tile Match | `gbTMShowToast` + `.gb-tm-toast` l. 2677–2724 | Wrong pick. | Server hint visible inside the wrong-pick feedback. | Hint is rendered via `gbTMShowHint(rightEl, resp.hint)` (l. 13868) which appends a `.gb-tm-hint` *inside* the wrong tile. After the 1.5 s wrong-state reset (l. 13874–13880) the hint is removed. Effective time-to-read is ~1 s — too short for a hint a student should learn from. | Either lengthen the wrong-state hold to 3 s, OR move the hint into the toast (which already auto-clears at its own pace), OR keep the hint pinned in a dedicated row beneath the board until the next attempt. |
| TM-05 | Low | Tile Match | content shape on `HW-20260505-009` | Pair 6/7: `Guruhlash`↔`umumiy qavsni topish`, `Tekshirish`↔`ko'paytuvchilarni ochish`. | All pairs are visually consistent (formula↔factored, name↔diagram). | Math pairs and concept-name pairs sit on the same board; concept pairs read as definitions, math pairs as expressions, the eye can't establish a single matching strategy. | Out of scope (prompt fix). Worth noting that on a 8-pair board with 2 outliers, the demo will look "noisy". |
| **AQ-RC-01** | Low (regression check) | Adaptive Quiz | `gbAQShowNext` + `aq-upload-gate` toggle l. 12415, 12469 | Geo AQ Q1 has `capture=false` (verified DB) → `aq.captureOk = !item.capture = true` → upload gate hidden. | Capture-required gate appears only when item demands it; never blocks `capture=false` items. | Working as intended on real data: 9/12 capture=false items pre-satisfy the gate and don't show the camera UI. Behavior matches PR #161/#162 fixes. | No fix needed. Monitor only. |
| AQ-RC-02 | Low (regression check) | Adaptive Quiz | result-box / status-pill dark-mode coverage l. 6650–6726 | Light + dark answer flow. | All AQ surfaces legible in both modes. | All AQ-* selectors covered by existing `[data-theme=dark]` rules in current template. | No fix needed. |
| AQ-RC-03 | Low (regression check) | Adaptive Quiz | `gbAQAction` l. 12568+ post-PR-165 | Student answers `sin B = 0,6` to expected `0.6`. | Accepted via `mathNormalize` dual-pass. | PR #165 logic in place, `mathNormalize(a) === userMath` line present in served HTML. | No fix needed. |

Severity map: **Critical = demo-blocker**, High = visible polish required, Medium = noticeable but tolerable, Low = monitor / cosmetic.

---

## Cross-cutting observations

1. **Puzzle Lock prompt vs. user intent** — Geometry prompt §51 explicitly calls Puzzle Lock a "Sliding Tile" game and the runtime implements that. The user described a different mechanic (sequential unlock-next). PL-02 is therefore both a runtime change AND a prompt change; if we do PL-02 we must also update the geometry prompt to stop authoring 15-puzzle-style content.
2. **Math-algebra prompt forbids Puzzle Lock entirely** (§77) yet `HW-20260505-009` ships 5 PL items — the generation pipeline is not honoring its own contract for math-algebra. Out of scope today.
3. **Tile Match content always travels through the legacy `gb_memory_match` field** — none of the existing schema/contract tests for `gb_tile_match` exercise the rendered demo path. Worth a follow-up assertion.

---

## Suggested PR split

### PR A — Puzzle Lock mechanic flip (Critical, demo-blocking)

**Scope:** PL-01, PL-02, PL-03, PL-04.

- Replace sliding-puzzle UI + JS with a linear "stepper": `currentStep` index, one question at a time, correct answer locks the step in green and reveals the next, wrong answer shows authored hint (or generic "Qaytadan urinib ko'ring" until prompt adds `hint`). Status pill becomes "Qadam X / N".
- Rewrite `.gb-pl-grid` / `.gb-pl-cell` CSS — vertical card stack, no `aspect-ratio`, full content visible, proof-step look (numbered chip on the side).
- Wire `mathNormalize` for answer compare so `cos α` ↔ `cos alfa` matches at parity with PR #165's AQ/Boss.
- Tests:
  - `test_runtime_puzzle_lock_linear.py` — DOM has linear-stepper markers; status reads "Qadam X / N"; click on locked step does nothing; correct answer advances `currentStep`.
  - `test_runtime_puzzle_lock_math_normalize.py` — same fixture set as PR #165's AQ test.
  - Browser smoke `HW-20260505-005`, `HW-20260505-009` light + dark.
- Risk: the prompts already author 5 sequential `Qadam X` items per fixture — perfect fit for the linear mechanic. Geometry prompt copy needs a sentence update ("Sliding Tile" → "Linear stepper") but content-shape stays `{content, q, a}` so no regeneration needed.

### PR B — Tile Match math typography (High polish)

**Scope:** TM-01, TM-02, TM-03, TM-04.

- Renderer step in `gbTMRenderBoard`: replace `^N` with `<sup>N</sup>`, `_N` with `<sub>N</sub>` before `innerHTML`. Keep raw HTML pass-through for already-formatted content.
- Bump `.gb-tm-tile` font-size to 14.5 px; `min-height` to 64 px; `text-align: center` for short formula tiles.
- Add `[data-theme=dark] .gb-tm-tile.selected` override + `box-shadow: 0 0 0 2px var(--accent)` ring on `.selected`.
- Lengthen wrong-state hint hold to 3 s (or move hint into toast).
- Tests:
  - `test_runtime_tile_match_caret_to_sup.py` — given `A^2-B^2` injected as legacy pair, served HTML/serialized JS contains `A<sup>2</sup>` (or runtime renderer leaves the source untouched and a JS unit test asserts the in-DOM transformation).
  - `test_runtime_tile_match_selected_ring.py` — CSS rule pinned.
- Browser smoke `HW-20260505-005` (Greek/°), `HW-20260505-009` (caret/factored expressions).
- Risk: low — Tile Match works today, this is pure polish. The caret-to-sup transform is purely cosmetic and reversible.

### Can wait (do NOT include in PR A or B)

- **PL-06** — Puzzle Lock SVG diagram fragments (prompt-side; runtime is ready)
- **TM-05** — mixed math/concept pairs on the same board (prompt-side)
- Math-algebra prompt's "no Puzzle Lock" rule violation in current homeworks (prompt-side; would require regeneration)
- Tile Match coverage of authored `gb_tile_match` shape (test-only follow-up)

### Demo-day workaround if PR A slips

- Use `HW-20260505-005` (geometry) for live demo only on AQ + Boss + Tile Match phases; **skip the Puzzle Lock screen** during showcase since the sliding mechanic is broken. Or add a temporary skip-button affordance gated to the `pl` panel only.
- `HW-20260505-010` algebra has no TM/PL content and is therefore safe end-to-end.
