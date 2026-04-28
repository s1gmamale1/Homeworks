# End-to-end smoke tests (Puppeteer)

> **Looking for the visible "watch a student play" script?**
> See `scripts/watch.sh` and `scripts/watch_simulation.cjs` one level up.
> Those open a real Chromium window so you can see every click. The
> scripts in *this* folder are headless regression tests for CI.

Headless-browser audits for the runtime homework page (`/h/{id}`) and the
builder editor (`/builder.html`). They probe live state — running runtime
JS, hitting `/api/ai/check-answer`, walking through phase transitions —
so they need:

- The dev server running on `http://127.0.0.1:8000`
- A populated homework record (the suite uses `HW-20260427-008` by default)
- Puppeteer installed somewhere `node` can find it (`NODE_PATH` env var)

These complement the pytest suite (`tests/`), which covers Python-side
units. The pytest suite does **not** boot a browser — these scripts do.

## Quick run

```bash
# Run the full suite — exits non-zero if any audit fails.
bash scripts/run_e2e.sh

# Or run a single audit:
NODE_PATH="$(npm root -g)" node scripts/e2e/verify_hw008.cjs
```

## What each audit checks

| File | Verdict surface | What it checks |
|---|---|---|
| `verify_hw008.cjs`     | content shape | All sections of HW-008 round-trip correctly (panels, flashcards, MS, AQ, SF, TM, RL, Boss, reflection) |
| `mechanics.cjs`        | runtime data | Memory Sprint options, AQ no-repeat picker, SF chains, Tile Match pairs, Boss accept lists |
| `new_mechanics.cjs`    | recent rewrites | SF AI grading round-trip + Tile Match left/right column matching |
| `post_tilematch.cjs`   | regression | RL_SCENARIO injector doesn't eat `stage6State` (the white-screen-after-Tile-Match bug) |
| `preview_quality.cjs`  | rendered DOM | Panel 4 (Misollar) renders 5 SVGs + 2 h2 headings, no leaked markdown, KaTeX active |
| `katex.cjs`            | math rendering | Probe injection — `$P$`, `$100^\circ$` etc. render via KaTeX on the runtime page |
| `katex_builder.cjs`    | dual behavior | Display areas render math; `[contenteditable=true]` fields keep raw `$...$` |
| `amr_results.cjs`      | scorecard | Backend returns axis_1/axis_2 for semantic+amr; results screen renders 6 phase rows + 2 axis cards |

## Adding a new audit

1. Drop a self-contained `<name>.cjs` in this folder.
2. Make it `process.exit(0)` on success, non-zero on failure.
3. Print a `=== Verdicts ===` JSON object so failures are scannable.
4. Add a row to the table above + a line to `scripts/run_e2e.sh`.
