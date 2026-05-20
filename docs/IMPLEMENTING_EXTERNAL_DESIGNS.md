# Implementing External Designs Safely

> **Purpose.** When the user hands over a static HTML/JSX mockup (reference design)
> and asks to swap it into a live runtime screen, follow this playbook.
> It's distilled from the 2026-05-01 adaptive-quiz day where one design swap
> ate ~10 hours via parallel-session collisions, agent off-spec behavior,
> false-success reports, and uvicorn template caching.
>
> **Audience.** Both the user (so they know what to expect) and Claude
> (load this doc before dispatching).

---

## Phase 0 — Pre-flight: session isolation + deployment target (5 min)

The single biggest time-sink was sharing a checkout + a uvicorn port
between two Claude sessions. Fix that before anything else.

**Establish the deployment target FIRST.** Before any edit, answer:
- Which checkout is uvicorn serving from? (`Get-CimInstance Win32_Process -Filter "Name='python.exe'" | ? CommandLine -like '*uvicorn*'` shows the cwd)
- Which port? (`netstat -ano | grep LISTENING | grep 876`)
- What branch is that checkout on? (`git -C <path> branch --show-current`)

If I edit files in worktree A but uvicorn is serving from checkout B, my
edits will never appear in the user's browser. This was the #1 cause of
"I see no change, still broken" loops in session `37ffe476`.

```bash
# from the main checkout (parked on `server`):
git fetch origin server
git worktree add ../hw-<short-task-name> -b feat/<branch-name> origin/server
cd ../hw-<short-task-name>
```

**Port allocation (write into CLAUDE.md so all sessions see it):**

| Worktree | Port |
|---|---|
| main checkout | 8765 |
| worktree #1 | 8766 |
| worktree #2 | 8767 |
| worktree #3 | 8768 |

Before starting uvicorn:

```bash
netstat -ano | grep ":<MY_PORT>" | grep LISTENING
# if anything shows up → use the next free port; never kill a sibling's server
```

**Acceptance for Phase 0**: I'm in a fresh worktree, on a new branch
forked from `origin/server`, with my own uvicorn port reserved.

---

## Phase 1 — Read the reference (10 min)

The user gives a single HTML/JSX file. Read it **fully** (it's small —
usually <300 LOC). Extract:

- **Outer container width / padding**
- **CSS custom properties** (`--blue`, `--glass`, `--shadow`, etc. — and
  whether they map to existing tokens in our codebase)
- **All semantic landmarks** (header, sticky topbar, dock, toast, gate)
- **Per-state class toggles** (`.show`, `.wrong`, `.confirmed`, etc.)
- **All animations / `@keyframes`**
- **Media queries**
- **Any decorative pseudo-elements** (`::after` blobs, etc.)
- **Any backend interaction** (fetch calls, form submits — usually none in mockups)

**Output**: a 1-screen summary I can show the user before dispatching,
including which mockup features need backend wiring.

---

## Phase 2 — Map the current implementation (Explore agent, ~5 min)

Dispatch Explore (medium thoroughness). Brief it to deliver:

1. **Markup location**: file:line range of the current screen's HTML
2. **CSS rules**: file:line range of all selectors targeted (be exhaustive
   — include dark-mode overrides, animations, pseudo-elements)
3. **JS contract**: exact function names + file:line for `init`, `render`,
   `pickItem`, `submit`, `finish`, `capture`, `next` etc.
4. **Data source path**: e.g. `state.contentJson.gb_adaptive_quiz[i].prompt`
5. **i18n keys**: which ones are touched, where they're defined
6. **Phase lifecycle**: how the screen mounts (`nets:phase-change`) and unmounts
7. **Cross-screen shared selectors**: classes used by other phases that I
   must NOT break
8. **Answer-leak surface**: where the correct answer lives in memory and
   where it's allowed to enter the DOM

**Output**: a markdown table mapping each reference element → current
implementation equivalent → action needed (rename / replace / new / drop).

**DO NOT skip this phase even if I think I know the screen.** Today, the
agent thought it knew the AQ markup and missed:
- the `.gb-section-title` eyebrow above the panel (had to be removed
  separately, caught only via screenshot)
- the screenContext extractor at line 12396 referencing `#gb-aq-input`
- the visual-regression tests pinning the old selectors

---

## Phase 3 — Scope reconciliation (5 min, with the user)

The reference design will have features that have no backend (timer pill,
Sample/Focus buttons, file-upload drag-drop). Decide IN-or-OUT for each,
**explicitly written down**, before dispatch. Format:

```
KEEP visually + wire to current backend:
  - 3-dot progress indicator (use Stage-5 ordinal)
  - Status pill (states: step1 / upload_done / correct / review)
  - Result-box (replaces .gb-aq-feedback)
  - Multi-line textarea (replaces single-line input)
  - Toast (visual-only, useful UX)
  - Decorative blob :after on question card

KEEP visually but wire to CURRENT (limited) backend:
  - Upload-gate UI → tap-to-confirm gbAQCapture(); no real file upload yet

DROP entirely:
  - Timer pill (no backend timer)
  - Sample / Focus / character-counter helpers (not in current contract)
  - Real <input type="file"> (Wave K image-upload deferred)
```

**Show this to the user. Get a thumbs-up.** Today this was implicit and the
agent had to make scope calls mid-flight, leading to "is this in or out?"
ambiguity.

---

## Phase 4 — Dispatch contract (the brief)

The implementation agent's brief MUST include, verbatim:

### Mandatory rules

1. **VISUAL ONLY.** Backend wiring (data flow + state machine + i18n +
   scoring + logging) must remain functionally identical. **Do NOT replace
   dynamic content with hardcoded literals. Do NOT add `display: none` on
   body content. Do NOT strip existing render functions.**
2. **Don't leak the answer.** Never put the correct answer into a
   `data-*` attribute or any DOM node before submit. Cite the existing
   wrong-feedback line that's allowed to display it.
3. **Read with offset+limit.** Files like `perfect_homework.html` are
   >12k LOC. Grep first → narrow Read second. Never read whole.
4. **One coordinated commit.** Markup + CSS + JS in the same commit on
   the same branch.
5. **Don't rename i18n keys.** Reuse existing keys. If new copy is needed,
   add NEW keys for ALL languages (uz/ru/en) — never hardcode.
6. **Branch-aware.** `git branch --show-current` BEFORE every `git add` +
   `git commit` (parallel session may have drifted the checkout).

### Required deliverables

1. **Markup mapping table** (reference element → new ID/class → JS hooks
   needed) — embedded in the brief.
2. **Verification grep checks** the agent must run before reporting done:
   ```
   grep -c "<old-selector-1>" <file>  → 0 (renamed to new)
   grep -c "<old-selector-2>" <file>  → 0
   grep -c "<state-machine-fn-1>\|<fn-2>\|<fn-3>" <file> → ≥N (none deleted)
   grep -c "<backend-data-global>" <file> → unchanged from baseline
   grep -c "data-correct\|data-answer\|data-expected" <new-markup>  → 0
   ```
3. **Diff scope check**: `git diff --stat origin/server` should ONLY list
   the files the brief specified. Anything else → REVERT.
4. **Tests pass**: full `pytest -q` count cited in the report.
5. **Final report under 250 words** with:
   - Files touched + LOC delta per file
   - Deviations from brief and why
   - Which verification checks failed and what was done about them
   - Commit SHA(s)
   - Specific things for the orchestrator to double-check on smoke

### Forbidden

- Pushing to remote (orchestrator pushes after smoke)
- Opening a PR (orchestrator opens after smoke)
- Modifying CI files
- Adding new dependencies
- Touching files outside the brief's scope

---

## Phase 5 — Verify (do NOT skip ANY of these)

In this order. If any step fails, STOP and re-plan — don't paper over.

### 5a. Grep audit

Same checks the agent claimed to run. Re-run them yourself.

### 5b. Pytest

```bash
pytest -q
```

Cite exact count.

### 5c. uvicorn fresh restart (NOT --reload)

Jinja templates can be cached in memory by an old uvicorn even after the
file changes. **Always kill + restart** before browser smoke.

```bash
# Find and kill the existing uvicorn:
netstat -ano | grep ":<MY_PORT>" | grep LISTENING
# (PowerShell) Stop-Process -Id <PID> -Force
# Wait 2s, confirm port released:
netstat -ano | grep ":<MY_PORT>"
# Restart:
C:/Python314/python.exe -m uvicorn server.app:app --host 127.0.0.1 --port <MY_PORT> --log-level warning
```

If port is stuck in TIME_WAIT, just use the next port. Don't fight Windows.

### 5d. Curl smoke

Confirm new selectors are in the rendered HTML and old ones are gone:

```bash
curl -s http://127.0.0.1:<MY_PORT>/h/<some-homework-id> | grep -c "<new-selector>"  # → expected count
curl -s http://127.0.0.1:<MY_PORT>/h/<some-homework-id> | grep -c "<old-selector>"  # → 0
```

### 5e. Playwright screenshots

**Light + dark mode separately.** Light mode uses `prefers-color-scheme:
light` (default). Dark mode requires manually setting `data-theme="dark"`
on `<html>` (our app uses manual toggle, not OS preference).

```python
ctx = browser.new_context(
    viewport={'width': 420, 'height': 900},  # mobile size for runtime
    reduced_motion='reduce',                   # important: IntersectionObserver reveals
)
page.goto(url, wait_until='networkidle')
if dark:
    page.evaluate("() => document.documentElement.setAttribute('data-theme','dark')")
```

Take screenshots of:
- Initial state
- After interaction 1 (e.g., capture confirmed)
- After interaction 2 (e.g., wrong-answer feedback)
- Both themes

**Look at every screenshot.** Today's `.gb-section-title` duplicate was
caught only because I actually opened the screenshot.

### 5f. Real walkthrough on the deployed Mac mini (optional, recommended)

If the change is on a critical user-facing path, after merging into
`server`, walk through it in a real browser on the deployed instance.
Pytest verifies code correctness; the walkthrough verifies feature
correctness. They're not the same.

### 5g. Close the visual loop against the user's screenshot

If the user provided a screenshot of the BROKEN state at the start of
the task, that screenshot IS the regression test. Before declaring done:

1. Hit the same URL the user was on (or as close as possible — same
   homework ID, same lang query, same theme).
2. Take a fresh screenshot at the same viewport.
3. **Open both side-by-side and visually diff.** Did the broken element
   actually change? Or did the markup change but the user's view didn't?
4. If they don't match → STOP. Either the deployment target is wrong
   (Phase 0 failure), or the fix landed on the wrong layer.

In session `37ffe476`, this step was skipped twice. Each time the user
came back with "I see no change, still showing X." The fix was real but
applied in a worktree that uvicorn wasn't serving. A 30-second screenshot
diff would have caught it before the user did.

---

## Phase 6 — PR + coordinate

### Coordination check BEFORE pushing

```bash
git fetch origin server
git log --oneline origin/server ^HEAD | head -5  # has anyone landed something while I was working?
gh pr list --state open --base server --json number,title,headRefName | head
```

If a sibling session has an open PR touching the same file, COORDINATE
before opening yours. Today PR #128 superseded my PR #129 because the
parallel session combined work without telling me.

### PR body

Use the canonical format (saved as `reference_pr_body_format.md`):

```
## Why
## What
## Smoke / Test plan
## Silent-revert audit (only if drift)
## Files (table)
## Out of scope
🤖 footer
```

Heredoc the body via `gh pr create --body "$(cat <<'EOF' ... EOF)"`.

---

## When the user says "still broken" / "I see no change"

This phrase is a signal, not just a complaint. Before doing ANY new edit:

1. **Pause.** Do not start editing files again. The previous fix may have
   been correct — the issue might be deployment, not code.
2. **Verify the deployment target** (Phase 0): which uvicorn, which
   checkout, which branch, which port.
3. **Open the live page yourself** (Playwright or curl + Read). Confirm
   the user's claim before assuming it.
4. **If the live page agrees with the user**: diagnose the gap between
   "file on disk" (where my edit landed) and "what uvicorn is serving"
   (template cache? wrong worktree? old PID?). Fix the deployment, not
   the code.
5. **Only edit code if the live page proves the on-disk fix didn't
   actually do what I thought.**

The default failure mode: assume the code is wrong, edit again, push
again, declare done. Then the user comes back with "still broken" a
third time. Break the loop by checking deployment FIRST.

---

## When the user asks a quick "why?" question

Default to a 1-sentence answer + an offer to go deeper. Don't auto-launch
into a multi-turn diagnostic.

> User: "why is the rebase blocked?"
>
> ❌ Bad: 600-word reflog forensics + branch-recovery plan + safety
>    analysis.
> ✅ Good: "Another Claude session committed onto this branch in the
>    main checkout 4 minutes ago — your rebase needs their commit
>    first. Want me to dig into the reflog and propose a recovery, or
>    just wait for them to push?"

Estimate before responding: does the user need the reason, or the reason
+ a fix plan? When unclear, ask in one line, then act on the answer.

---

## Stop conditions — when to abort and re-plan

Don't paper over these. Stop, tell the user, re-plan.

- **Agent reports "done" but a verification grep fails.** Don't trust the
  prose summary. The grep is the contract.
- **Screenshot doesn't match the reference.** Don't ship and hope.
- **The diff scope expanded beyond what the brief allowed** (e.g., agent
  edited a CI file). REVERT, re-dispatch with a tighter scope.
- **Tests went from 1031 → 1026.** Five tests broke silently. Find them,
  fix them, re-run.
- **A sibling session has touched the same file in the last hour.** Talk
  to the user before pushing — silent reverts are how dual-PR merges
  destroy work.
- **The agent claims it ran 1031 tests but didn't say HOW LONG it took.**
  Probably mocked the test run. Re-run yourself.

---

## Audit — what went wrong on 2026-05-01 (adaptive-quiz day)

| # | What happened | What would have prevented it |
|---|---|---|
| 1 | Two sessions sharing one checkout + one uvicorn → branch drift, port collisions, template-cache cross-contamination | Phase 0: per-session worktree + per-session port |
| 2 | Codex stripped `gate_quotes` backend wiring + hardcoded "Bilarmidingiz?" pill (PR #112) | Phase 4 mandatory rule #1 stated explicitly in dispatch brief |
| 3 | Opus restoration agent reported "fixed" but the file still had `display: none` | Phase 5d (curl smoke) + Phase 5e (screenshots) before trusting the prose report |
| 4 | uvicorn at 8765 served stale `.gb-aq-input` markup AFTER the file was renamed | Phase 5c (kill + fresh restart, not --reload) |
| 5 | `.gb-section-title` "O'YIN 1 — ADAPTIVE QUIZ" eyebrow leaked through above the new topbar | Phase 5e (look at the screenshot, not just count selectors) |
| 6 | Sibling session opened PR #128 combining my work without telling me; my PR #129 closed mid-flight | Phase 6 coordination check before push |
| 7 | Implementation agent re-explored the whole file → token bloat | Phase 2 mapping pass delivered file:line refs the impl agent could go straight to |
| 8 | Dark-mode screenshot test used `color_scheme=dark` but our app uses manual `data-theme` attribute → false negative | Phase 5e: explicit data-theme attribute in Playwright eval |

### Audit — session 37ffe476 (gate-quote rendering loop)

| # | What happened | What would have prevented it |
|---|---|---|
| 1 | Claude edited files in a worktree but uvicorn was serving from the main checkout → user saw no change | Phase 0: establish deployment target (which uvicorn, which checkout, which branch) before any edit |
| 2 | Claude claimed "fixed" twice without visually verifying against the user's broken-state screenshot | Phase 5g: load the same URL, fresh screenshot, side-by-side diff |
| 3 | When user said "I see no change, still broken" Claude immediately edited again instead of checking the deployment gap | "When user says 'still broken'" protocol — pause, verify deployment, edit only if the live page proves on-disk fix is wrong |
| 4 | Two parallel Claude sessions corrupted each other's reflog on the shared main checkout | Phase 0 lane separation rule |
| 5 | User asked a quick "why is rebase blocked?" → Claude launched a 60-second diagnostic + recovery plan | "Quick why" protocol — 1-sentence answer + offer, don't auto-deep-dive |

---

## Quick checklist (print this)

- [ ] **0.** Worktree created. Port reserved. Branch forked from `origin/server`.
- [ ] **1.** Reference HTML read fully. Tokens, animations, copy extracted.
- [ ] **2.** Explore agent mapped current impl: file:line refs for markup, CSS, JS, data path, i18n, lifecycle, shared selectors.
- [ ] **3.** Scope reconciliation: every reference feature classified IN / IN-with-stub / OUT. User signed off.
- [ ] **4.** Dispatch brief includes: visual-only contract + answer-leak rule + grep audit checks + diff-scope check + final-report shape.
- [ ] **5a.** Grep audit re-run by orchestrator (not just agent).
- [ ] **5b.** `pytest -q` clean, count cited.
- [ ] **5c.** uvicorn killed + restarted from MY worktree on MY port.
- [ ] **5d.** curl smoke shows new selectors in HTML, old ones gone.
- [ ] **5e.** Playwright screenshots: light + dark, multiple states. Eyes on each.
- [ ] **5g.** If user provided a "broken state" screenshot, fresh screenshot at the same URL/viewport, side-by-side diff. Loop closed.
- [ ] **6.** Coordination check (`git fetch origin server` + `gh pr list`).
- [ ] **6b.** PR opened with canonical body.
- [ ] **6c.** Memory: append to `notes/MASTER_INDEX.md` + `notes/MASTER_MEMORY.md` after merge.
