# Watch a student session in real time

`scripts/watch_simulation.cjs` opens a visible Chromium window and walks
every phase of HW-20260427-008 at human speed so you can see the
student's experience without manually clicking through.

## Quick start

```bash
# 1. Make sure dev server is running
curl http://127.0.0.1:8000/api/health
# {"status":"ok",...}

# 2. Make sure puppeteer is reachable
export NODE_PATH="$(npm root -g)"

# 3. Run the watcher (mid persona, default speed)
bash scripts/watch.sh
```

A Chromium window will open. The script narrates each step in your
terminal. The browser stays open at the AMR scorecard at the end so
you can poke around — close the window manually when you're done.

## Personas (accuracy on local-graded items)

```bash
bash scripts/watch.sh strong   # ~95% correct — usually clears Mastered
bash scripts/watch.sh mid      # ~70% correct — usually lands Proficient
bash scripts/watch.sh weak     # ~30% correct — usually Apprentice/Novice
```

Note: AI-graded items (Sentence Fill, Real-Life Q5, Boss Q3-Q5) always
go through the actual Kimi grader. Persona only affects the fast
local-match path.

## Speed (slowMo, ms per Puppeteer action)

```bash
bash scripts/watch.sh mid 50    # near real-time — fast click-through
bash scripts/watch.sh mid 250   # easy to follow with the eye
bash scripts/watch.sh mid 600   # very slow — good for screen recording
```

Default is 120ms per action.

## Jump to a specific phase

```bash
bash scripts/watch.sh strong 200 boss     # skip everything before Boss
bash scripts/watch.sh mid 200 sf          # only run Sentence Fill onwards
bash scripts/watch.sh mid 200 rl          # only run Real-Life onwards
```

Recognised phases: `preview`, `flashcards`, `sprint`, `aq`, `sf`, `tm`,
`rl`, `consolidation`, `boss`, `results`.

## What you'll see in the terminal

```
╔════════════════════════════════════════════════════════════╗
║  Watching student session · HW-20260427-008                ║
║  Persona: mid        (70% accuracy)                        ║
║  SlowMo : 120ms                                            ║
╚════════════════════════════════════════════════════════════╝

── Phase 1 · Memory Sprint ──────────────────────────────────
  Q1: picked=0 correct=0 OK
  Q2: picked=1 correct=1 OK
  ...
── Phase 3a · Adaptive Quiz ─────────────────────────────────
  R1: id=A2 tier=easy sent="40" expect="40" OK
  ...
── Phase 3b · Sentence Fill (AI grading, 1-3s per item) ─────
  C1: expect="ayirmasining" sent="ayirmasining"
  ...
── Stage 9 · AMR Results scorecard ──────────────────────────
  Band     : PROFICIENT
  Headline : Sizning umumiy natijangiz: 79% (15 / 28 to'g'ri)
  Phases:
    · Memory Sprint 5 / 7
    · Adaptive Quiz 4 / 5
    · Tile Match Tamomlandi
    · Sentence Fill · A1=3.2 A2=3.4  3 / 5
    · Real-Life · A1=4.0 A2=4.0  4 / 5
    · Final Boss · A1=2.0 A2=2.0  1 / 5
  AMR axes:
    · AXIS 1 — CONCEPT IDENTIFICATION 3.13 / 4 Proficient
    · AXIS 2 — PROCESS INTEGRITY 3.07 / 4 Proficient
  Retry button on results: yes
```

## Headless regression tests vs. this watcher

| | `scripts/e2e/*.cjs` | `scripts/watch_simulation.cjs` |
|---|---|---|
| Browser | headless | visible |
| Speed | as fast as possible | throttled (`SLOWMO`) |
| Output | verdicts (pass/fail) | narration + final scorecard |
| Use for | CI gating, regression hunting | spot-checking flows after a change |
| Exits when done | yes (with code 0/1) | no — keeps browser open |

Run `bash scripts/run_e2e.sh` for the headless test suite.
Run `bash scripts/watch.sh` to actually watch a student play.
