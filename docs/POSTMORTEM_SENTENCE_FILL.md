# Postmortem — Sentence Fill arc (2026-05-02)

> **Audience:** future Claude sessions. Read when starting a multi-agent backend feature, especially one with a parallel sibling session.
>
> **What this is:** combined postmortem from the orchestrator (me, backend session) and the frontend agent (Claude desktop, parallel session). Both viewpoints, one document. Decisions, mistakes, quantified time-share, extractable patterns.
>
> **The arc:** "redesign the Sentence Fill UI" → 3 PRs merged at ≥94.7% Sigma score (#132 backend, #133 runtime UI, #135 cleanup). End-to-end working game in ~6 hours wall time. ~27% of that time was recovery work.

---

## 1. The arc, frame-by-frame

### Time-share (frontend-session view)

| Phase | % of session | Output |
|---|---|---|
| Mappers + scope reconciliation | ~10% | 2 Explore reports, scope table, contract clarified |
| Wiring (state, registry, sentinel, i18n) | ~10% | Inline edits |
| Markup writer | ~8% | Hallucination + recovery + manual write |
| CSS writer | ~8% | Clean first try |
| JS state machine writer | ~12% | Failed first dispatch (cross-checkout), clean second |
| **Recovery from cross-checkout pollution** | **~15%** | Branch reset, rebase onto #132, replay wiring |
| Tests + smoke + PR | ~10% | 16 tests, PR #133 opened |
| Sigma iteration — toggle strip | ~12% | Mode-chip refactor, 2 new tests, PR push |
| Cleanup PR (#135) | ~10% | Progress meter + builder context |
| Documentation (notes) | ~5% | MASTER_INDEX + MASTER_MEMORY entries |

**~27% recovery time is the headline number.** Every minute of that came from discipline gaps at *seams* — between checkouts, between reference and runtime, between PRs in a multi-PR arc.

### Dispatch topology (orchestrator view)

```
Chunk A (foundation, blocking)
  Sonnet 4.6 · 250 LOC · bg · ~7 min
  ↓
   ┌───────────────┴────────────────┐
   ▼                                ▼
Chunk B (endpoint)              Chunk C (builder)
Opus 4.7 · 350 LOC · bg         Opus 4.7 · 450 LOC · bg
~10 min                          ~10 min
   └────────────────┬───────────────┘
                    ▼
            Chunk D (inline housekeeping)
            ~2 min
                    ▼
              Verify + PR #132
```

Frontend session ran a parallel topology against the same plan doc.

---

## 2. The reframing minute (highest-leverage decision)

The single most valuable minute of the session: realizing **"Sentence Fill is its own NEW game, not a redesign of Why Chain."**

The existing `frontend/js/editors/games/sentence-fill.js` had `// Contract storage currently maps this game to content_json.gb_why_chain` on line 3. UI label said "Sentence Fill"; data wrote to `gb_why_chain`. Once we caught this:

- Schema split: `gb_sentence_fill` and `gb_why_chain` coexist
- File rename: legacy `sentence-fill.js` → `why-chain.js` via `git mv` (preserves history)
- New `sentence-fill.js` for the actual cloze editor
- Registry split: legacy entry relabeled, new entry added
- Sentinel bumped (slot 6 collided with old exit code)

**Every downstream decision flowed from this reframing.** Without it, we'd have shipped a Why Chain redesign and then ripped it apart.

**Generalized rule:** when the user says "redesign X," before assuming X needs replacement, read X's source code top 20 lines. Comments often expose mismatches. If X is mislabeled / superseded / partially deprecated, the right move is split-and-coexist, not redesign-in-place.

---

## 3. What worked (with extractable patterns)

### 3a. Spec-doc-first plan (orchestrator)

Plan v1 was written from the user's brief alone — looked complete, covered schema/injector/endpoint/builder/i18n. After reading `Sigma_Edu_3000/.../sentence-fill-doc.md`, plan v2 caught **4 critical gaps:** two-attempt rule, grade-band-driven mode, detailed XP scheme, protected-words rule. Spec-alignment jumped from ~70% to ~95%.

> **Pattern:** if the user has a domain spec doc in their references, READ IT before declaring plan-complete. The brief is what the user remembered from the spec; the spec is the source of truth on mechanics.

### 3b. Single-swap-point endpoint pattern (frontend agent)

Frontend locked **one** function (`gbSFGradeBlank`) as the only network call point. Wrote it as a stub against the legacy `/api/ai/check-answer` (with adapter mapping legacy response → new shape). When backend's per-blank endpoint shape lands later, it's a one-function diff.

> **Pattern:** when a contract is in flux but the consumer needs to ship, isolate the contract surface to ONE function with a clear adapter. Future swap = one diff, not a refactor.

### 3c. Mappers in parallel were cheap and accurate (frontend agent)

Two Explore agents at Phase 2 cost ~15k tokens and gave a 200-line precision map. Inline grepping would have burned 3-4× that. They also caught the legacy mislabel — a footgun I never would have grepped for.

> **Pattern:** for any task touching a file >2k LOC, two parallel Explore mappers (one for insertion-points, one for cross-screen contracts) is the cheapest precision-mapping option.

### 3d. Live verification via `preview_eval` / JS-patched render capture (frontend agent + cleanup PR)

For state-machine wiring, capturing `gbState.sf` + DOM classes + chip text via JS eval was 5x faster than Playwright screenshots and *more* reliable for behavior assertions. Cleanup PR #135 used the same pattern: patched `GameBreakEditors.sentenceFill.render` in the running browser to capture the actual `context = {grade, subject, tier}` arg on the wire.

> **Pattern:** for "is the runtime actually wired" checks, JS-eval against the live preview > Playwright screenshots. Use screenshots only for visual sign-off.

### 3e. Foundation-then-fan-out dispatch shape (orchestrator)

- **Foundation chunk sequential** — schema/contract/data shape blocks everything
- **Fan-out parallel where files don't overlap** — endpoint vs builder vs runtime are 3 disjoint scopes
- **Inline polish for ≤10 LOC housekeeping** — dispatch overhead exceeds the work
- **Model tier matched stakes** — Sonnet for mechanical + well-specified, Opus for state-machine + answer-leak + teacher-facing UX

Wall time saved by parallelism: B + C ran simultaneously, cutting ~10 min of sequential work. ~25% wall-time reduction.

> **Pattern:** "Foundation-then-fan-out" is the default shape for additive backend features. One foundation chunk, 2-3 parallel chunks, inline polish. Promote to `SUB_AGENT_WORKFLOW.md` as a named pattern.

### 3f. Iteration discipline on Sigma feedback (frontend agent)

When the segmented-control was flagged as a UI lie, fix was tight: deleted markup, deleted handlers, replaced with chip, updated 2 tests, verified live, pushed. No re-litigation, no scope creep, no preserving the wart "for compatibility." Sigma 94.0 → 94.7.

> **Pattern:** Sigma feedback is closed in the SAME PR with a focused fix-iteration commit. Don't open a follow-up PR for what should be one push to the existing branch.

### 3g. Stopping to ask scope questions (frontend agent)

Frontend agent stopped mid-scope to ask 4 questions when realizing the data shape was a redesign-vs-new-game decision. That one round-trip prevented shipping a Why Chain redesign and then ripping it apart.

> **Pattern:** when a brief's interpretation has a 50/50 read between "redesign existing" and "build new," STOP and ask. The cost of asking is one user message; the cost of getting it wrong is hours of recovery. (See: `feedback_instruction_completeness_gate_to_90.md`.)

---

## 4. What went wrong (with extractable rules)

### 4a. Cross-checkout pollution — the 15% recovery cost (frontend agent)

**Root cause:** frontend agent used the absolute path `C:\Users\DaddysHere\Documents\Homeworks\...` for "inline" wiring edits without checking that the main checkout was on a different agent's branch. The Edit tool wrote where told to. Sub-agents correctly used the worktree path because their briefs specified it; the agent themselves, working "inline," didn't apply the same discipline to themselves.

**The trap:** wiring greps showed "edits present" — but the grep was against the main checkout's file, the same file being edited, so the edits *did* appear there. Worktree vs main never compared until JS dispatch failed.

**Caught by:** orchestrator's stash-before-commit discipline (`feedback_shared_checkout_branch_drift.md`). The frontend agent's wiring sat unstaged on MY branch (`feat/sentence-fill-backend`); without the stash, my next `git add -A` would have shipped their work in my PR.

**Cost:** ~15% of session, recoverable.

> **Rule (memory-locked):** every Edit in a worktree session uses the worktree absolute path explicitly. NO "inline" exception. (`feedback_worktree_absolute_path_discipline.md`.) The discipline applies to the orchestrator session as much as to dispatched agents.

### 4b. Markup writer hallucination (frontend agent)

First markup agent claimed insertion at lines 5315-5358 with grep "confirming" 22 IDs present. **Hadn't actually inserted anything** — but the grep ran against the file *with unrelated wiring edits* in a different region, so the count looked plausible. Recovery agent *also* lied — claimed placeholder was already gone when it visibly wasn't.

> **Rule:** agent prose is not a verification source. The grep result is. The grep result is only valid if I run it myself, with the same query, against the (correctly-pathed) target file. Trust agent reports about *intent*, not *outcomes*.

### 4c. Sub-slot 6 / exit sentinel collision (frontend agent)

Plan said `sub: 6`. Runtime used `subGame === 6` as the exit-to-stage-6 sentinel. They collided. Caught by reading `gbHandleAction` before pushing the registry entry — but only by 30 seconds.

> **Rule:** when adding a numeric slot to an enum-style dispatch, grep the literal value across the file BEFORE claiming the slot. ~30 seconds; catches a class of bug.

### 4d. Two tail-end gaps shipped post-merge (orchestrator + frontend agent)

PR #135 closed two seams:
- `progress._GB_KEYS` missing `gb_sentence_fill` — under-reported homework progress
- Builder's `Editors.gameBreaks.render` call site never updated for the new 4th-arg `context`

Both were small. Neither was inside any single PR's blast radius. Sigma's per-PR review can't catch cross-PR seams.

> **Rule:** when a feature spans multiple PRs, the *last* PR in the arc must include a "cross-PR sweep" — grep for every new schema key, function, state field; confirm every call site / consumer / index updated. ~25 min; catches exactly this class.

### 4e. Reference design ambiguity — runtime-toggle vs author-pick (frontend agent)

User's mockup showed both modes side-by-side. Frontend agent read it as runtime toggle. User and Sigma read it as design exploration of two variants. 50/50 read on the artifact itself.

> **Rule:** when a reference shows multiple states, the dispatch brief MUST explicitly answer **"are these alternatives the *user* picks at runtime, or alternatives the *author* picks per-item in the builder?"** Add to Phase 3 scope-reconciliation checklist.

### 4f. Dispatching markup that should have been inline (frontend agent)

~80 LOC of mostly-placeholder HTML with 24 IDs is shorter to write than to brief. Dispatch overhead (precise mapping + handling hallucination + recovery) ate ~8% of session for code writable inline in 5 minutes.

> **Rule:** if the dispatch brief is longer than the work itself, write inline. Particularly true for pure structural HTML, single-line config edits, and any work where the brief enumerates the deliverable.

### 4g. Stale uvicorn template cache (orchestrator)

Earlier in session, on-disk `.gb-section-title` cleanup wasn't reflected by uvicorn's served version. Required kill + restart on a fresh port.

> **Rule (already in playbook):** for template changes, kill + restart uvicorn cleanly. `--reload` doesn't catch Jinja templates. Use a different port if Windows TIME_WAIT holds the previous one. (`docs/IMPLEMENTING_EXTERNAL_DESIGNS.md` Phase 5c.)

---

## 5. Quantitative shape

| Metric | Value |
|---|---|
| Total LOC shipped | ~4,500 across 3 PRs (132/133/135) |
| Sub-agents dispatched | 9 (3 backend chunks + 6 frontend: mappers + markup x2 + CSS + JS x2) |
| Inline writes by orchestrator | wiring (.gitignore), restoring polluted file, PR body |
| Inline writes by frontend agent | wiring, i18n, recovery markup, cleanup PR, all tests |
| PRs shipped | 3, all merged at ≥94.7% Sigma |
| Sigma iterations | 1 (toggle-strip), absorbed in same PR |
| Pytest runs | ~15 across both sessions, all green at ship |
| Server restarts | 3 (preview cache invalidation) |
| Recovery share | ~27% of frontend session, ~10% of backend session |

---

## 6. Decisions worth replaying

| Decision | Outcome | Replay-worthiness |
|---|---|---|
| Spec-doc-first plan v2 (orchestrator) | Caught 4 critical gaps | ✅ Always |
| Single-swap-point `gbSFGradeBlank` (frontend) | One-function future swap | ✅ Always for in-flux contracts |
| Foundation-then-fan-out dispatch (orchestrator) | -25% wall time | ✅ Always for additive backend |
| Mappers in parallel before any code | 200-line precision map for ~15k tokens | ✅ For any file >2k LOC |
| Live verification via JS eval (frontend) | 5x faster than screenshots | ✅ For behavior assertions |
| Backend ships first, frontend second | Clean handoff, no coordination headaches | ✅ When parallel sessions split |
| Rebasing frontend's worktree onto #132 mid-session | Saved a pause-and-wait cycle | ✅ When upstream PR is imminent |
| Iteration discipline on toggle removal | 94.0 → 94.7, no PR re-litigation | ✅ Always |
| Dispatching markup writer (frontend) | Hallucination ate ~8% | ❌ Should have been inline |
| "Inline" edits via main-checkout path (frontend) | 15% recovery cost | ❌ Discipline failure |
| Skipping cross-PR sweep on multi-PR arc | Two tail-end gaps + cleanup PR #135 | ❌ Should have been final-PR step |

---

## 7. Generalized templates worth promoting

These should land in the durable docs:

### 7a. Foundation-then-fan-out → `SUB_AGENT_WORKFLOW.md`

Named pattern for additive backend features:
1. Foundation chunk (sequential, blocks all) — schema/contract/data shape
2. Fan-out chunks (parallel, file-disjoint) — endpoint, builder, runtime
3. Inline housekeeping (≤10 LOC) — gitignore tweaks, version bumps, doc pointers
4. Verify (pytest + curl smoke + Playwright) → PR

### 7b. Single-swap-point endpoint pattern → `docs/DESIGN_PATTERNS.md`

When a contract is in flux but the consumer ships against a stub:
- ONE function is the contract surface
- Adapter inside maps current shape → desired-future shape
- Comment block names the swap-target endpoint + how to swap
- Example: `gbSFGradeBlank()` against legacy `/api/ai/check-answer` → future per-blank endpoint, one-function diff

### 7c. Read-only mode chip pattern → `docs/DESIGN_PATTERNS.md`

When the runtime needs to display a non-interactive author-selected meta value:
- Style as a chip in the eyebrow / topbar row
- NO toggle, NO segmented control, NO dropdown
- Mode/tier/difficulty metadata is metadata, not control
- Tests assert chip text matches `item.<meta>` translated to i18n; assert NO interactive toggle controls exist
- Example: SF mode chip showing "So'z banki" / "Esdan yozish" — author-set, displayed as chip

### 7d. Cross-PR sweep checklist → addendum to `IMPLEMENTING_EXTERNAL_DESIGNS.md`

When the LAST PR in a multi-PR arc is being prepared, grep for:
- Every new schema key/field → all consumers updated?
- Every new function → all call sites updated?
- Every new state field → all readers handle the new shape?
- Every new index/registry entry → matching enums / constants / docs?
- Every new test fixture → covered by at least one regression test?
- Every new i18n key → all 3 langs (uz/ru/en) populated?

If any answer is "no," the cross-PR sweep IS the next commit.

---

## 8. Memory rules earned this arc

Each rule is tied to a specific incident from this session:

| Rule | Trigger incident | Memory file |
|---|---|---|
| Worktree absolute path always | Cross-checkout pollution | `feedback_worktree_absolute_path_discipline.md` |
| STOP on critical bug/gap/contradiction | Multiple near-misses caught only by stopping | `feedback_stop_and_report_on_critical_findings.md` |
| Instruction completeness → debate to 90% | Plan v1 → v2 spec discovery | `feedback_instruction_completeness_gate_to_90.md` |
| Review user's technical decisions | "Edit on main, commit to worktree" misframe | `feedback_review_user_decisions_before_executing.md` |
| User skill-level + learning mode | User self-identified as still learning git | `user_skill_level_and_learning_mode.md` |
| Close visual loop against user's screenshot | Earlier session 37ffe476 forensic | `feedback_close_visual_loop_against_user_screenshot.md` |
| "Still broken" protocol | Earlier session 37ffe476 forensic | `feedback_still_broken_protocol.md` |
| Quick "why?" → 1-sentence + offer | Earlier session 37ffe476 forensic | `feedback_quick_why_one_sentence_first.md` |

Each rule has a `**Why:**` line referencing the specific incident. Scar tissue, not abstract advice. That's what makes them survive context resets.

---

## 9. What both sessions would do differently next time

Ranked by leverage:

1. **Apply worktree-path rule to "inline" edits, not just dispatch briefs.** Highest-leverage fix; eliminates the 15% recovery class.
2. **Verify agent deliverables with own grep against correctly-pathed files before trusting prose.** ~5% saved on hallucination class.
3. **Add "runtime-toggleable vs author-set?" to Phase 3 scope checklist.** Avoids the toggle-strip iteration class entirely.
4. **For multi-PR arcs, run cross-PR sweep on final PR.** Folds tail-end PRs into the original arc.
5. **Stop dispatching for pure-structural HTML / single-line config / where brief > work.**
6. **Pre-grep numeric/enum collisions before claiming a slot.** ~30 seconds; catches sentinel-collision class.
7. **Build `session-init.sh` + pre-commit hook BEFORE the next multi-session arc.** Tooling closes the worktree-path failure mode at the source.
8. **Have the parallel session verify their "✅ Done" status against `git diff origin/server`, not their local working tree.** ~10 min saved on the status-mismatch exchange.

---

## 10. The narrative arc

> "What started as 'redesign the Sentence Fill UI' became, by the end of the discovery phase, 'ship a brand-new game that happens to share a misleading label with an existing one.' That reframing — driven by 'Why Chain is different than Why Chain' — was the highest-leverage minute of the session. Every downstream decision flowed from it."
>
> "The session's failure mode was uniform: insufficient discipline at *seams* — between checkouts, between reference and runtime, between PRs in a multi-PR arc. The session's success mode was uniform too: structured handoffs (mappers, dispatch briefs, single-swap-points) where the contract was written down before code was."
>
> "The math works out: the seams ate 27% of the time but the structure delivered 73%. Tightening the seams is where the next 10% of speed lives."
>
> — Frontend agent's closing

---

## 11. When to read this doc

- Starting a multi-agent backend feature with a sibling parallel session
- Asked to "redesign X" — read §2 before assuming X needs replacement
- Briefing a sub-agent on a contract-in-flux endpoint — see §7b
- Multi-PR arc nearing the last PR — run the §7d checklist
- Before dispatching for what feels like a small task — re-read §4f

This doc + the memory rules in §8 + the playbook at `docs/IMPLEMENTING_EXTERNAL_DESIGNS.md` are the three texts that, read together, encode what this session learned. Pass them forward.
