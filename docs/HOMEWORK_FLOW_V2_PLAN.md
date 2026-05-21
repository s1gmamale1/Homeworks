# Homework Cycle v2 — 3-Division Restructure (Approved Plan)

**Status:** Plan approved 2026-05-21. **Not yet implemented.** This document is the in-repo source-of-truth for the v2 arc. PRs reference it; reviewers cross-check against it.

**Source artifacts:**
- `Infra.zip` (Telegram → Downloads) — `Flow/New_Flow.md` + `Case-Based Preview/*` + `Flashcards/*` + `Gamified Practices/*`
- User confirmation diagram (homework cycle sketch)
- This session's design-decision Q&A

---

## Context

Today the homework runtime is a **9-phase linear pipeline** with no score gates: preview → flashcards → memory_sprint → game_break → real_life → consolidation → boss → reflection. Phases advance on button-click regardless of performance. The two persistent feedback themes — "content feels boring/raw", "no real gate between learning and practice" — both trace to this shape: students can blow through the learning surface without ever proving they learned anything before the games start.

The Infra spec pack ships a v2 design with three observations the codebase doesn't yet implement:

1. **Case-Based Preview** replaces passive Preview panels with a 3-checkpoint guided learning case (decision-maker role, real-life scenario, consequence/simulation at the end). The student *uses* the lesson before being tested on it.
2. **Memory Check** sits between Flashcards and Practice — Quizlet-style test (MCQ / Fill-in-blank / Choose-correct-explanation) that proves the anchors stuck.
3. **Unlock Gate** between Learning Sections and Practice Arc. Both learning sections (Case-Based Preview ≥2/3 checkpoints, Flashcards+Memory Check ≥60%) must clear before games + Real Life Challenge + Boss open. Sections are free-order — the student picks which to do first via a Learning Hub.

Intended outcome: new homeworks ship on a v2 engine that enforces "learn → prove → practice" with explicit gates. Old homeworks keep working unchanged (additive migration). The Boss stays as the Practice Arc peak with the Flow v2 Why → How → What reasoning skeleton.

---

## Locked design decisions

1. **Migration**: Additive. Old homeworks (no `flow_version`) keep the legacy 9-phase engine. New homeworks (`flow_version: "v2"`) use the new engine. No auto-migration of existing rows. Frozen-schema invariant preserved.
2. **Learning Section order**: Free order. Hub shows two tiles ("Case Study" + "Flashcards"); student picks either. Both must complete at least once AND ≥60% to unlock the Practice Arc.
3. **Gate fail**: Soft retry. Student stays on the failed section and retakes the failed checkpoints / test items. Retake rule (Flow v2 forbid #19): same concept, regenerated question variant — never the identical question.
4. **Real Life Challenge**: Kept as a Practice Arc game (one of N dynamic games), per the Infra zip's `Gamified Practices/Real Life Challenge/Real_Life_Challenge_Specification.md`. Case-Based Preview = guided low-stakes teaching; RLC game = higher-stakes applied test at mastery time. Pedagogically distinct.

---

## Current state (from recon)

| Area | State |
|---|---|
| Phase machine | `_phaseDotById` + `_phaseIdByStage` at `server/template/perfect_homework.html:10936-10952`; stages 0–8 with half-step interstitials (4.7 reading, 6.5 consolidation, 7.7 reflection). Transition via `setStage(n)` → fires `nets:phase-change` event. **No score gates anywhere.** |
| Tutor modes | Inferred from stage: PREVIEW (0–2, 7.7+) · PRACTICE (2.5–6.5) · BOSS (7–7.5). Redaction at `server/services/tutor.py:752-777` (`_redact_question_for_tutor`) — allow-list of safe keys, recursive scrub. 3 leak tests at `tests/test_tutor_chat.py:215, 255, 314` (PRACTICE only — no BOSS coverage). |
| Schema | Pydantic models at `server/schemas/content.py`; all `extra="allow"`. Frozen-key invariant enforced by regex substitution at `server/services/injector.py:58-80` + `:690-700`. **Adding new top-level keys is safe (additive); renaming existing keys is a breaking change.** |
| Prompts | 7 subject dirs × ~12 phase files at `server/prompts/<subject>/`. Boss prompt named `final-challenge.md` (legacy). History missing `flow.md` + `classify.md`. English missing `preview-easy.md`. |
| Persistence | `phase_attempts` table is per-question log we own (write at `server/db/attempts_repo.py:29`). `sessions.phase_scores` exists but is never written. `boss_xp_earned` absent (computed at `server/routes/ai.py:1672`, discarded). `tutor_attempts` owned by grading lane (we read, never write). |
| Tests for gates | **None.** No phase-order assertion test. No 60% / 2-of-3 / retake threshold test. |
| Case-based / Memory Check / Quizlet scaffolding | **Absent.** No model, no prompt, no DOM panel, no test. Pure greenfield. |

---

## Target shape (v2)

```
Homework Tab  (flow_version: "v2")
│
├─ Learning Hub  (#screen-hub)
│  │
│  ├─ Tile A → Case-Based Preview  (#screen-cbp)
│  │           [setup → ckp1 → lb1 → ckp2 → lb2 → ckp3 → simulation → feedback]
│  │           Gate: ≥2 of 3 checkpoints correct (≥66.7%, satisfies the ≥60% rule)
│  │           Fail → stay on section, retake failed checkpoint with regenerated variant
│  │
│  └─ Tile B → Flashcards (#screen-3, reused)  →  Memory Check (#screen-mc, new)
│              Gate: all flashcards viewed ≥1x  AND  ≥60% on Memory Check items
│              Fail → return to flashcards (weak cards highlighted), re-test
│
├─ Unlock Gate animation  (#screen-unlock)
│  Fires only when BOTH sections passed at ≥60%.
│  Chain-breaking animation; CTA: "Enter Practice Arc" (never "Start Homework").
│
├─ Practice Arc  (existing #screen-5, extended)
│  Dynamic game order (N games, configurable per homework)
│  Real Life Challenge included as a game, not a phase
│  Boss Arena = mastery peak, Why → How → What reasoning enforced
│
└─ Reflection / Debrief / Marking  (#screen-reflection, existing)
   Status: Passed | Needs Retry  (never "Not Completed" alone)
   Retake rule: same concepts, regenerated question variants
```

---

## content_json additions (additive, all `extra="allow"`)

Three new top-level keys + one marker. Old keys (`panels`, `memory_sprint`, `game_break`, `real_life`, `consolidation`, `final-challenge`, `reflection`) remain optional and continue to work on the legacy engine.

```python
class CaseBasedPreview(_Permissive):
    title: str
    metadata: dict          # subject, grade, topic, textbook_address, source_concept, required_skill, case_type, student_role
    source_extraction: dict # core_concept, main_rule, key_terms, common_mistake, textbook_example, source_alignment_note
    visual_plan: list[dict] # [{visual_type, purpose, where_used, alt_text, labels, source_alignment_note}]
    case_setup: dict        # story, role, task
    checkpoints: list[dict] # exactly 3 items: {kind: identify|decide|justify, question, options, answer_spec, learning_block}
    final_simulation: dict  # {correct_path, wrong_path, visual_description_or_svg}
    feedback_summary: dict  # student_understood, mistake_appeared, what_to_review
    completion_rules: dict  # {pass_condition: "ge_2_of_3", retry_condition: ...}

class MemoryCheckItem(_Permissive):
    type: Literal["mcq", "fill_blank", "choose_explanation", "true_false"]
    prompt: str
    options: Optional[list[str]]
    answer_spec: AnswerSpec      # reuses existing AnswerSpec from content.py:45-68
    flashcard_ref: Optional[str] # back-reference to source flashcard id

class MemoryCheck(_Permissive):
    items: list[MemoryCheckItem]   # ≥5 recommended for stable 60% gate
    pass_threshold_pct: int = 60   # author-overridable, default 60
    modes_enabled: list[str] = ["mcq", "fill_blank", "choose_explanation"]
    retake_pool_size: Optional[int] # if set, regenerated variants pulled from this pool

class ContentJSON(_Permissive):
    flow_version: Optional[Literal["v1", "v2"]] = None   # absent = "v1" = legacy
    case_based_preview: Optional[CaseBasedPreview] = None
    memory_check: Optional[MemoryCheck] = None
    # ... all existing fields unchanged
```

Why `flow_version` (not just "presence of case_based_preview"): explicit dispatcher signal at runtime; future-proofs against v3; lets us round-trip legacy homeworks without ambiguity.

---

## Critical files to modify

### Server
| File | Change | Approx LOC |
|---|---|---|
| `server/schemas/content.py` | Add `CaseBasedPreview`, `MemoryCheckItem`, `MemoryCheck` models; add 3 optional fields to `ContentJSON` | +120 |
| `server/services/injector.py` | Append `("case_based_preview", "CBP")`, `("memory_check", "MC")` to `_OBJECT_CONSTANTS` (line 58–80); add corresponding `const CBP = {};` / `const MC = {};` template stubs | +20 |
| `server/services/tutor.py` | Accept new phase value `'case_based'` (treat as PRACTICE for redaction). Extend `_TUTOR_CONTEXT_SAFE_KEYS` if needed for checkpoint shapes. Add boss-phase leak test parity. | +30 |
| `server/routes/homework.py` | No change — `content_json` validation already accepts additive keys via `extra="allow"` (lines 15–47) | 0 |
| `CONTRACTS.md` | Document new keys + `flow_version` semantics. Mark legacy keys as "kept for backward compat". | +80 |

### Prompts
| File | Change | Source |
|---|---|---|
| `server/prompts/<subject>/case-based-preview.md` (×7 subjects) | New per-subject CBP generation prompt (4 family templates available in Infra zip: math, sciences, languages, history) | `Infra/Case-Based Preview/nets_cbp_prompt_{math_family,sciences,languages}.md` + a History adaptation |
| `server/prompts/<subject>/memory-check.md` (×7 subjects) | New per-subject Memory Check generation prompt — takes flashcards[] as input, emits 5+ quizlet-style items spanning ≥2 modes | Derived from `Infra/Flashcards/Quzilet Learning/{Multiple Choice,Fill in the blank,Choose Correct Explanation}/*.md` |
| `server/prompts/<subject>/flow.md` (×7) | Rewrite to v2 narrative (3 divisions + unlock gate + reflection); also fills the missing `english/preview-easy.md` and `history/flow.md` gaps | `Infra/Flow/New_Flow.md` |

### Runtime template (`server/template/perfect_homework.html`)

**Additive — does not touch the legacy stage machine.** New code branches on `flow_version === "v2"` at boot.

| Section | Change | Approx LOC |
|---|---|---|
| Boot dispatcher | At runtime init, branch on `CONTENT.flow_version`. v1 → existing `setStage(0)`. v2 → call `setStageV2('hub')`. | +30 |
| `#screen-hub` (new) | Two-tile Learning Hub. Each tile shows section status (Not started / In progress / ✓ Passed). Clicking enters the section. | +80 HTML + 60 CSS |
| `#screen-cbp` (new) | Case-Based Preview engine. Internal sub-stages: setup → ckp1 → lb1 → ckp2 → lb2 → ckp3 → simulation → feedback. Uses existing `tutor.py` PRACTICE redaction via the new `case_based` phase value. Gate: ≥2 of 3 checkpoints correct. Soft-retry on fail. | +220 HTML/JS + 80 CSS |
| `#screen-mc` (new) | Memory Check engine. Renders quizlet items in randomized order, mixed types. Gate: ≥60%. Fail → re-route to flashcards with weak items highlighted. | +180 HTML/JS + 60 CSS |
| `#screen-unlock` (new) | Chain-breaking animation. CTA: "Enter Practice Arc" / "Practice Arc Unlocked". Fires only when both `state.cbp.passed && state.mc.passed`. | +60 HTML/JS + 100 CSS (keyframes) |
| `setStageV2()` (new) | Parallel state machine: hub, cbp.{setup,ck1,lb1,ck2,lb2,ck3,sim,fb}, fc, mc, unlock, practice.{game-1..N,boss}, reflection. Fires `nets:phase-change` events with `phase: "case_based" \| "practice" \| "boss"` for tutor coupling. | +200 |
| Reflection copy | Wave 2 reflection screen already exists. Add Pass / Needs Retry labels (3 langs). | +30 |

### DB / persistence

**No new tables for V1.** Reuse existing `phase_attempts` with new `phase` values:
- `phase: "case_based_preview"`, `subphase: "checkpoint_1"|"checkpoint_2"|"checkpoint_3"`
- `phase: "memory_check"`, `subphase: "item_<n>"`

Gate state derived on-read from attempt counts. If we discover this gets too chatty (>50 reads/min/session), V2 can add a `phase_gate_state` table.

`sessions.current_phase` already accepts arbitrary string values — no schema change.

---

## Tutor answer-leak: extending the invariant to v2

Current redaction at `server/services/tutor.py:752-777` strips answer-bearing keys recursively for `practice` and `boss` phases. The new `case_based` and `memory_check` phases ship gated questions with `answer_spec` — they MUST go through the same redaction path.

Changes:
1. `phase_change` event from runtime emits `phase: "case_based"` or `phase: "practice"` (for Memory Check). The tutor maps both to its existing PRACTICE redaction.
2. Add tests parallel to the existing 3:
   - `test_case_based_no_answer_leak` — assert checkpoint `answer_spec.expected` stripped from outbound prompt
   - `test_memory_check_no_answer_leak` — assert quizlet item `answer_spec.expected` + `accepted_answers` stripped
   - `test_boss_no_answer_leak` — close the existing BOSS-coverage gap that the recon flagged at `tests/test_tutor_chat.py`

---

## Test plan (new + extended)

| Test file | Purpose |
|---|---|
| `tests/test_flow_v2_dispatch.py` | `flow_version: "v2"` content_json enters new engine (state.flowVersion === "v2"); absence (or "v1") uses legacy engine. Asserts no cross-contamination. |
| `tests/test_case_based_preview_schema.py` | `CaseBasedPreview` Pydantic validation: rejects checkpoints != 3; accepts minimal valid shape; preserves `extra="allow"`. |
| `tests/test_case_based_preview_gate.py` | ≥2/3 checkpoints correct → `state.cbp.passed = true`. <2/3 → stays on section with failed checkpoint marked for retake. Retake question is regenerated variant (not identical). |
| `tests/test_memory_check_schema.py` | `MemoryCheck` Pydantic validation. |
| `tests/test_memory_check_gate.py` | ≥60% items correct → `state.mc.passed = true`. <60% → returns to flashcards with weak items highlighted. |
| `tests/test_learning_hub_free_order.py` | Either section can be done first. Hub renders both tiles. After both pass, Unlock Gate is reachable. |
| `tests/test_unlock_gate.py` | Practice Arc only reachable when `state.cbp.passed && state.mc.passed`. One passed alone → gate stays closed. |
| `tests/test_tutor_no_leak_case_based.py` | Mirror of `test_practice_no_answer_leak` but for the `case_based` phase. Asserts MAGIC_TOKEN_* not in prompt. |
| `tests/test_tutor_no_leak_memory_check.py` | Same, for memory_check items routed via PRACTICE redaction. |
| `tests/test_tutor_no_leak_boss.py` | Close the existing recon-flagged gap: BOSS phase answer-leak coverage. |
| `tests/test_legacy_homework_still_renders.py` | A homework without `flow_version` boots into the legacy stage machine, no regressions. |

Browser walkthrough (per the `local_smoke_before_pr` rule):
1. Author a new homework with `flow_version: "v2"`, populated CBP (3 checkpoints) + flashcards + memory_check (≥5 items)
2. Open `/h/{id}` → Learning Hub renders with both tiles
3. Click "Case Study" → CBP setup → fail checkpoint 2 → see soft-retry with regenerated variant → pass → return to Hub
4. Click "Flashcards" → flip all → Memory Check → score 40% → return to flashcards with weak items highlighted → re-test → pass 80% → back to Hub
5. Both tiles ✓ → Unlock Gate chain-breaking animation fires
6. Practice Arc → games (incl. RLC as one of them) → Boss → Reflection with "Passed" status
7. Open a legacy homework (`/h/{old_id}`) → confirm old 9-phase flow unchanged

---

## PR sequencing

Single arc, 5 PRs. Frontend PRs (PR-2, PR-3, PR-4) MUST serialize on `perfect_homework.html` to avoid merge collisions.

```
PR-1 — Schema + Injector + Tutor + Prompts (backend foundation)
   Sonnet 4.6
   Files: server/schemas/content.py, server/services/injector.py, server/services/tutor.py,
          server/prompts/*/case-based-preview.md, server/prompts/*/memory-check.md,
          server/prompts/*/flow.md, CONTRACTS.md
   Tests: test_flow_v2_dispatch, test_case_based_preview_schema, test_memory_check_schema,
          test_tutor_no_leak_case_based, test_tutor_no_leak_memory_check, test_tutor_no_leak_boss,
          test_legacy_homework_still_renders
   ~600 LOC code + ~400 LOC tests. Self-contained, no UI dependency.
   Worktree: ON. ~5-6 dev-days.
   │
   ▼
PR-2 — Runtime v2 dispatcher + Learning Hub + Case-Based Preview engine
   Opus 4.7 (heavy frontend per 2026-05-08 SWE flip)
   Files: server/template/perfect_homework.html (additive sections only, no legacy code touched)
   Tests: test_case_based_preview_gate, test_learning_hub_free_order (partial — only CBP tile working)
   ~330 LOC HTML/JS/CSS + ~250 LOC tests. ~4-5 dev-days.
   │
   ▼
PR-3 — Memory Check engine + flashcards weak-item reroute
   Opus 4.7
   Files: server/template/perfect_homework.html (Memory Check section; flashcards reroute hook)
   Tests: test_memory_check_gate, test_learning_hub_free_order (now full coverage)
   ~240 LOC + ~200 LOC tests. ~3 dev-days.
   │
   ▼
PR-4 — Unlock Gate animation + Practice Arc dynamic-order + Boss Why/How/What enforcement
   Opus 4.7
   Files: server/template/perfect_homework.html (unlock + practice arc), server/prompts/runtime/boss-tutor.md
   Tests: test_unlock_gate, boss reasoning-skeleton assertion
   ~360 LOC + ~250 LOC tests. ~3-4 dev-days.
   │
   ▼
PR-5 — Reflection terminology + retake rule + e2e walkthrough script
   Sonnet 4.6 (mechanical copy + e2e)
   Files: server/template/perfect_homework.html (reflection labels), frontend/js/i18n/strings.js,
          scripts/run_e2e.sh (+ new phase_walk_v2.cjs)
   Tests: extends e2e
   ~150 LOC + ~150 LOC tests. ~2 dev-days.

Total: 5 PRs · ~1,680 LOC code + ~1,250 LOC tests · 17–20 dev-days · serialized on the template file
```

**Builder UI editors** (`frontend/js/editors/case-based-preview.js`, `memory-check.js`) are **out of v1** — initial CBP + MC payloads are authored via the existing AI generation pipeline + `PUT /api/homeworks/{id}` JSON drop. Builder UI lands in a separate arc once the runtime is stable.

---

## Out of scope (V1)

Listed so PR bodies can point reviewers at the deferral, not flag them as gaps:

- Spaced review queue (Flashcard Engine doc §7.7) — V2
- Match Mode / Write+Spell Mode (Flashcard Engine doc §7.3, §7.4) — V2
- Diagram cards, audio cards, Q-Chat-style explain-card assistant — V3
- Auto-rewrite of existing legacy homeworks into v2 shape — explicitly rejected (additive migration locked)
- Builder UI editors for CBP + Memory Check — follow-up arc
- Per-school customization of pass thresholds (`pass_threshold_pct` is author-overridable on the homework but no admin UI for it)
- Real-time multi-client sync of section progress
- Mobile-first redesign of Learning Hub (desktop-first for v1, responsive but not optimized)
- Replacing legacy phase prompts (`memory-sprint.md`, `consolidation.md`, `final-challenge.md` rename → `boss.md`) — separate cleanup arc after v2 lands
- Boss XP persistence (`outcome_xp` → `sessions.boss_xp_earned`) — separate PR per the existing audit doc at `docs/audits/2026-05-09-engagement.md`. Independent, can land in parallel with v2 if desired but out of this plan's scope.

---

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| **Frozen-schema invariant violation** — accidental rename of an existing content_json key | All v2 additions are NEW keys (`flow_version`, `case_based_preview`, `memory_check`). Zero edits to existing key names. CONTRACTS.md update is additive (new sections). |
| **Template merge collisions** — `perfect_homework.html` is 1M-LOC and converges across PR-2 / PR-3 / PR-4 | Serialize PR-2 → PR-3 → PR-4 (not parallel). Each PR rebases on `origin/server` immediately before push. |
| **Tutor answer-leak regression** — new phase value (`case_based`) routed through wrong redactor | Map `case_based` + `memory_check` to PRACTICE redaction explicitly in `tutor.py`. Three new dedicated leak tests gate the PR. Existing 3 tests still pass. |
| **Uzbek grammar quality** on new CBP prompts | Per existing rule on native Uzbek linguist review (P7 from FLOW-DEBATE) — defer CBP Uzbek prompts to a follow-up linguist pass; v1 ships English/Russian, marks Uzbek as draft. |
| **CBP question quality variance** when LLM-generated | Validation checklist from Case-Based Preview Standard §14 (18 items) goes in the prompt; failed-generation → regenerate (no human-visible failure). Add a notebook smoke test that walks the 18-item checklist against generated CBP. |
| **Memory Check gate too easy/hard at 60%** | `pass_threshold_pct` is author-overridable; default 60% picked from spec. Telemetry on first 50 homeworks → adjust default. |
| **Legacy homeworks regress** when shipped runtime changes load | Branch at boot: `flow_version === "v2"` enters new engine; everything else falls through to existing `setStage(0)`. `test_legacy_homework_still_renders` is the regression fence. Local smoke walks at least one legacy homework on each PR. |
| **Sigma AI 3000 review threshold (≥85)** on a multi-PR arc | Each PR scoped to a single concern + has its own regression tests. PR-1 is the riskiest (schema + tutor + prompts) — prioritize Sigma alignment there. |

---

## Verification (end-to-end)

After PR-5 lands:

```bash
# Pytest full suite — expect ~1030 → ~1060 tests
python -m pytest tests/ -q

# v2-specific tests
python -m pytest tests/test_flow_v2_dispatch.py tests/test_case_based_preview_*.py \
                 tests/test_memory_check_*.py tests/test_learning_hub_*.py \
                 tests/test_unlock_gate.py tests/test_tutor_no_leak_*.py -v

# Legacy regression
python -m pytest tests/test_legacy_homework_still_renders.py -v

# E2E browser walk (extended in PR-5)
bash scripts/run_e2e.sh   # includes phase_walk_v2.cjs

# Local dev server smoke
python -m uvicorn server.app:app --host 127.0.0.1 --port 8765 --log-level warning
# Browser: author + walk a v2 homework; then walk a legacy homework; screenshots at each phase
```

Visual loop close:
- Screenshot Learning Hub (both tiles, both states)
- Screenshot CBP mid-checkpoint (state.cbp.ckp_idx = 2)
- Screenshot soft-retry indicator on failed checkpoint
- Screenshot Memory Check item (each of 3 question types)
- Screenshot Unlock Gate animation (mid-keyframe)
- Screenshot Practice Arc with RLC as one of the games
- Screenshot Reflection with "Passed" status
- Side-by-side legacy homework on same viewport — confirm no regression

---

## Frontend design language (aligned to `landing.html` / `landing.css`)

The v2 surfaces (Learning Hub, Case-Based Preview, Memory Check, Unlock Gate, refreshed Reflection) reuse the Apple-glass vocabulary already shipped in `frontend/landing.html` + `frontend/css/landing.css`. This keeps the student journey visually continuous: the landing page → library → builder → runtime should all feel like one product. Without this, the runtime's existing utilitarian styling would clash with the new entrypoints.

### Tokens to reuse (`landing.css:8-55`)

| Category | Tokens |
|---|---|
| Surface / type | `--landing-zinc-{950,900,800,700,500,400,300,200,100}`, `--landing-card`, `--landing-card-tinted`, `--landing-ring`, body font: SF Pro Display / Inter |
| Accent | `--landing-blue-{600,500,400}`, `--landing-cyan-{300,200}`, `--landing-fuchsia-500`, `--landing-emerald-700`, `--landing-indigo-500` |
| Elevation | `--landing-shadow-card`, `--landing-shadow-card-hover`, `--landing-shadow-deep` (for dark sections), `--landing-shadow-soft` |
| Motion | `--landing-spring: cubic-bezier(.16, 1, .3, 1)` (Apple no-overshoot), `--landing-dur-md: 480ms`, `--landing-dur-lg: 1050ms` |
| Shape | Pills (`border-radius: 999px`), cards (16–24px), section glows (radial-gradient + `filter: blur(40px)`) |

To avoid duplicating tokens inside `perfect_homework.html`, **link `landing.css` from the runtime template** OR **extract the tokens into `frontend/css/_tokens.css` and import from both**. The latter is cleaner; pick it if `app.css` doesn't already centralize tokens.

### Component vocabulary per v2 surface

| v2 surface | Landing component(s) to mirror | Why |
|---|---|---|
| **Learning Hub** (`#screen-hub`) | `.tutor-card-dark` + `.tutor-card-light` paired pattern (`landing.html:262-289`); section-inner grid (`tutor-grid`); `.eyebrow--blue` + `.section-title`; per-tile status uses `.pill` ("Not started" / "In progress" / "✓ Passed") | The hub is conceptually two big choice tiles. Landing's paired light/dark tutor cards are the exact shape. Dark tile = Case Study (case-based, more dramatic framing); light tile = Flashcards (mechanical, anchor-style). |
| **Case-Based Preview** (`#screen-cbp`) — case setup | `.dark-section` background + `.hero-bg-glow` clone for ambient; `.hero-title` typography (clamp(36px, 6vw, 72px), -0.025em) for the case title; `.eyebrow--cyan` for "Case Study" label | Case setup deserves a dramatic intro frame. Reuses the hero treatment without redrawing it. |
| **Case-Based Preview** — checkpoints | `.lesson-panel` rows (`landing.html:163-195`, `landing.css:649-706`) — left-aligned button rows with chevron, `.is-active` state on current checkpoint; `.lesson-panel__eyebrow` for "Checkpoint 1: Identify"; `.lesson-panel__title` for the question prompt | Lesson-panel is purpose-built for "pick one of N decision tiles" — exactly the checkpoint UX. Hover lift + chevron animation are already tuned. |
| **Case-Based Preview** — final simulation / feedback | `.feature-card` grid for correct-path / wrong-path / what-to-review (3-up); `.workflow-step` numbered cards if showing decision-trace timeline; `.tutor-card-light` for the AI feedback summary | Feature card is the cleanest "explanatory tile" surface on the landing. Workflow-step number badge naturally maps to "Decision 1 → Decision 2 → Decision 3" trace. |
| **Memory Check** (`#screen-mc`) | `.feature-grid` for the item list view; per-item `.pill` for question type ("MCQ" / "Fill" / "Choose"); `.btn-blue` for submit; on fail, weak items get `.feature-card` with a `.pill--dark` ("Weak — review") chip; the back-to-flashcards CTA uses `.btn-white-outline` | The item list mirrors landing's feature-grid layout. Weak-card highlighting reuses the dark pill for visual continuity with the existing landing tagging. |
| **Unlock Gate** (`#screen-unlock`) | `.launch-shell` pattern (`landing.html:351-366`, `landing.css:1273-1367`) — dark, centered, with `.launch-bg-glow` and `.launch-floating-icon`; `.launch-title` typography; CTA = `.btn-white-pill` ("Enter Practice Arc"); chain-breaking SVG animation layered above the glow | Launch-shell is the landing's signature "moment of arrival" surface. Repurpose for the gate-opening moment. Chain-breaking animation is the only new SVG keyframe we need. |
| **Practice Arc** (existing `#screen-5`, refresh) | Wrap existing game panels in `.section-inner` + `.eyebrow--blue` + `.section-title`; game-selection grid uses `.feature-card` hover lift; current-game indicator uses `.pill`; Boss intro is a small `.dark-section` interstitial mirroring `.launch-shell` mini | Existing game UI stays untouched (no rework risk), but the outer wrapper picks up the design language so Practice Arc stops looking like a different app. |
| **Boss Arena** | `.dark-section` background; Why → How → What labeled steps use `.workflow-step` (3-up numbered); HP bar keeps existing styling but border-radius + shadow tuned to match `--landing-shadow-deep` | Workflow-step naturally encodes 3-step reasoning. Why → How → What was the planned label rename per FLOW-DEBATE P2. |
| **Reflection** (`#screen-reflection`, refresh) | `.tutor-card-light` for the reflection form; `.pill--dark` for status ("Passed" / "Needs Retry"); `.btn-blue` for "Done" / `.btn-white-outline` for "Retake" | Reuses the same surface as the Learning Hub's light tile — closes the loop visually (student starts and ends on the same vocabulary). |

### Behavior to reuse from `landing.js`

The runtime template is a different JS architecture than the landing (no module system, no IntersectionObserver currently). We don't need to bring the whole `landing.js` engine — pick the three behaviors that matter:

1. **Stagger reveal on first paint of each screen** — copy the IntersectionObserver pattern from `frontend/js/landing.js:5-6, ~570-590` (search `stagger-parent` / `stagger-child`). Apply to `#screen-hub`, `#screen-cbp`, `#screen-mc`, `#screen-unlock` so each enters with a calm cascade rather than a hard cut. ~30 LOC inline; doesn't conflict with the existing stage machine.
2. **Spring curve + reduced-motion fallback** — all transitions and transforms in v2 sections must use `--landing-spring` AND honor `@media (prefers-reduced-motion: reduce)` (existing landing has this; mirror it). ~10 LOC of CSS.
3. **The "calm" hover lift** — `transform: translateY(-7px) scale(1.02)` on game tiles + section cards, 220ms spring. Matches `.feature-card:hover`, `.quick-card:hover` rhythm.

### Behaviors to NOT bring over

- **Hero parallax** (`data-hero-parallax`) — too much motion for an active homework screen; would compete with the tutor widget.
- **Multi-stat marquee** — the v2 screens have explicit progress (gate, checkpoint counter); they don't need landing-style hero stats.
- **Language toggle in-screen** — runtime inherits language from URL/session; no per-screen pills.
- **Sticky header w/ nav** — runtime already has the tutor widget docked; an extra sticky bar would compete.

### Dark-mode

`landing.css` is light-first but tokens render correctly on dark via `prefers-color-scheme`. Verify that the v2 surfaces don't hardcode `#fff` backgrounds or `#0f172a` text — bind to `--landing-zinc-100` / `--landing-zinc-950` so dark mode works automatically. Manual smoke pass on each v2 surface in dark mode before each PR ships.

### Reduced-motion + accessibility

- Every transform / transition is wrapped in `@media (prefers-reduced-motion: reduce)` → `transition: none; transform: none;` per the landing's existing pattern.
- Focus rings: reuse `:focus-visible { outline: 2px solid var(--landing-blue-500); outline-offset: 3px; }` from `landing.css:111-116`.
- Skip-link: the runtime already has phase navigation; add a skip-to-tutor link if not present.
- All new SVG icons must carry `aria-hidden="true"`; semantic labels go on the parent `<button>` / `<a>`.

### LOC impact (additive to original estimates)

| PR | Original | Design-aligned | Delta |
|---|---:|---:|---:|
| PR-2 Learning Hub + CBP | 330 | **430** | +100 (token plumbing, lesson-panel reuse, glow layers, dark-section intro) |
| PR-3 Memory Check | 240 | **300** | +60 (feature-grid wrap, pill tagging, weak-item card style) |
| PR-4 Unlock Gate + Practice Arc + Boss | 360 | **480** | +120 (launch-shell clone, chain-breaking SVG keyframe, workflow-step Boss skeleton, Practice Arc section wrappers) |
| PR-5 Reflection refresh + e2e | 150 | **210** | +60 (tutor-card-light reflection, status pill, screenshot-loop pass on each v2 surface in light + dark) |

**New total: ~2,030 LOC code + ~1,250 LOC tests (was 1,680 + 1,250). 18–22 dev-days (was 17–20).**

The design alignment is not a separate PR — it's woven into PR-2 through PR-5. The first PR-2 lands the token bridge (link `landing.css` or extract tokens) and the design language compounds from there.

### Visual loop close (extended)

Per the project's `local_smoke_before_pr` rule, every v2 PR must screenshot the new surface in BOTH light and dark mode, AND compare side-by-side to the landing's equivalent component. The screenshots are part of the PR body. If a v2 surface visually disagrees with the landing equivalent (different shadow depth, different pill radius, different hover lift) — flag it as a regression in the PR.

---

## Critical files referenced

- `server/template/perfect_homework.html:10892-10952` — phase machine, `setStage()`, `_phaseDotById`
- `server/template/perfect_homework.html:10210-19058` — existing content_json constants (PANELS, FLASHCARDS, etc.)
- `server/template/perfect_homework.html:8302-9099` — existing screen panels (#screen-break, #screen-3, #screen-ms, #screen-5, #screen-6, #screen-boss, #screen-reflection)
- `server/schemas/content.py:45-68` — `AnswerSpec` (reused by CBP + Memory Check)
- `server/services/injector.py:58-80` + `:690-700` — frozen-key invariant + `_replace_js_const`
- `server/services/tutor.py:726-749` — `_TUTOR_CONTEXT_SAFE_KEYS`
- `server/services/tutor.py:752-777` — `_redact_question_for_tutor` (recursive scrub)
- `server/db/migrations.py` — `phase_attempts`, `sessions` (no schema changes needed for v1)
- `server/db/attempts_repo.py:29` — `add_phase_attempt` (reused for CBP + MC subphases)
- `tests/test_tutor_chat.py:215, 255, 314` — existing leak tests (mirror these for new phases)
- `CONTRACTS.md:9-159` — frozen content_json contract (additive update)
- `frontend/landing.html:262-289, 163-195, 351-366` — paired light/dark tiles, lesson-panel rows, launch-shell (reused by v2 surfaces)
- `frontend/css/landing.css:8-55` — design tokens (zinc / blue / cyan / spring) shared into v2 runtime
- `frontend/css/landing.css:570-595, 649-706, 1273-1367` — feature-card, lesson-panel, launch-shell stylesheets reused
- `frontend/js/landing.js:5-6` — IntersectionObserver stagger-reveal pattern (~30 LOC port to runtime)
- `Infra.zip` → `Flow/New_Flow.md` (source-of-truth flow doc)
- `Infra.zip` → `Case-Based Preview/nets_case_based_preview_generation_standard_v1.md` (CBP standard)
- `Infra.zip` → `Case-Based Preview/nets_cbp_prompt_{math_family,sciences,languages}.md` (per-family prompts)
- `Infra.zip` → `Flashcards/Flashcard Prompts/flashcard_study_engine_documentation.md` (flashcard engine doc — informs Memory Check)
- `Infra.zip` → `Flashcards/Quzilet Learning/{Multiple Choice,Fill in the blank,Choose Correct Explanation}/*.md` (Memory Check item specs)
- `Infra.zip` → `Gamified Practices/Real Life Challenge/Real_Life_Challenge_Specification.md` (RLC retained as Practice Arc game)
- `Infra.zip` → `Gamified Practices/Boss Arena/Boss_Arena_Specification.md` (Boss Why → How → What)
