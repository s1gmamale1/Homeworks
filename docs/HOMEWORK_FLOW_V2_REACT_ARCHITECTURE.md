# NETS Homeworks — React SPA Runtime + Builder: Architecture Design

**Status:** Approved design (autonomous build authorized 2026-05-21). Backbone for the React re-platform.
**Companion to:** `docs/HOMEWORK_FLOW_V2_PLAN.md` (the 3-division flow this renders).
**Working branch:** `DaddysBranch` (NOT `server` — server is frozen).

---

## Locked decisions (from owner + adopted agent recommendations)

1. **Backend:** Keep FastAPI + SQLite. Restructure routes + add JSON API + serve React bundle. Reuse all hard-won logic (grading, tutor, redaction, schemas, DB).
2. **Runtime:** React SPA (Vite + TypeScript), served as static by FastAPI. Hydrates from a JSON API. No Node in production.
3. **Coexistence:** `/h/{id}` forks — React for `flow_version: "v2"`, legacy HTML injector for everything else. Both runtimes live; React supersedes at parity.
4. **Contract:** `content_json` stays frozen + is the API boundary. Answer-leak redaction stays server-side.

**Adopted agent recommendations (no further confirmation needed):**
- Hydration endpoint is **NEW** (`GET /api/runtime/homeworks/{id}`), redacted — NOT the existing unredacted builder GET.
- Post-submit feedback comes from **interaction-endpoint responses**, not the hydration payload (keeps answers server-side).
- **TypeScript yes**; types **generated from Pydantic** (`model_json_schema()` → `json-schema-to-typescript`), not hand-written.
- **CSS Modules + shared CSS-variable tokens** (extract `landing.css:8-55` → `frontend/css/_tokens.css`). Not Tailwind/CSS-in-JS.
- **Two builders coexist**; React builder authors **v2 net-new only**. No legacy-editor port, no auto-convert.
- **Commit `frontend/app/dist/`** to the repo for launchd-friendly deploy (Mac mini never runs Vite).
- **Server-side OG/skeleton injection** in the SPA shell is mandatory (Telegram/social share cards matter).

---

## Critical recon facts

- Runtime template is **~21,670 LOC** (`server/template/perfect_homework.html`) — a faithful v2-only React build is tractable because **React renders ONLY v2** (no legacy 9-phase behavior to reproduce).
- The runtime **already** talks to a JSON API: `server/template/runtime.js` reads `window.NETS_CTX` and POSTs to `/api/ai/*`. The React app **generalizes this exact bridge**.
- **`GET /api/homeworks/{id}` returns FULL unredacted content_json** (`server/routes/homework.py:332-341`) — it's the Builder's authoring endpoint. **Must NOT be reused for student hydration.**
- Answer-leak redaction lives in **two** places:
  1. `server/services/tutor.py:808-833` `_redact_question_for_tutor` (LLM prompt context).
  2. The **injector** per-game strip: `_BOSS_SERVER_ONLY`/`_TM_SERVER_ONLY`/`_SF_SERVER_ONLY`/`_RLC_SERVER_ONLY` (`injector.py:98-114`). **This second one is what the JSON API must replace when we stop injecting.**
- Per-interaction grading is **already clean JSON API**: `/api/ai/check-answer` (phase-dispatched), `/api/ai/runtime/submit-answer`, `/api/ai/boss-turn`, `/api/ai/tutor/chat`, `/api/ai/reflection`. **React reuses all of them.**

**The gap:** a redacted **read/hydration API** + a **server-authoritative gate-state API**. That's the heart of the new work.

---

## A. Repo + build structure

React app at **`frontend/app/`** (Vite, TS), building into **`frontend/app/dist/`** (committed). Legacy `frontend/{index,builder,library,landing}.html` untouched — zero file overlap.

```
frontend/
├── index.html, builder.html, library.html, landing.html   # legacy, untouched
├── css/landing.css                                          # token donor (:8-55)
├── css/_tokens.css                                          # NEW — extracted shared tokens
├── js/                                                      # legacy vanilla, untouched
└── app/                                                     # NEW Vite + React workspace
    ├── index.html  package.json  vite.config.ts  tsconfig.json
    ├── src/{main.tsx, runtime/, builder/, shared/, styles/}
    └── dist/                                                # build output (committed)
```

- **Dev:** Vite on :5173 proxying `/api` + `/static` → uvicorn :8765. HMR against real backend.
- **Prod:** `vite build` → `dist/`; FastAPI adds one static mount `app.mount("/app", StaticFiles(dist, html=True))` **before** the `/` catch-all. `base: '/app/'` in vite config.
- Vite content-hashes assets → the repo's `?v=__VERSION__` cache-bust system does NOT apply to the SPA (no `_HTML_PAGES` row, no `test_static_cache_bust.py` row).

### `/h/{id}` fork (`server/routes/homework_page.py:145`)

```python
content = hw.get("content_json") or {}
if content.get("flow_version") == "v2":
    return HTMLResponse(_render_spa_shell(hw_id))   # ~15-line shell: sets NETS_CTX, OG tags, loads /app bundle
return HTMLResponse(render_homework(hw))             # legacy injector path, UNCHANGED
```

---

## B. JSON API design

### B.1 Hydration — NEW + redacted
`GET /api/runtime/homeworks/{id}` → student-safe content_json. Redaction in NEW `server/services/runtime_redactor.py`:
- Reuse the **same deny-lists** from `injector.py:98-114` — **extract to `server/services/redaction_constants.py`** so injector + redactor can't drift.
- **Allow-list fails closed** (model on `_redact_question_for_tutor`): new answer-bearing fields fail safe by default.
- v2 additions: strip `case_based_preview.checkpoints[].answer_spec`, `.final_simulation.correct_path`, `memory_check.items[].answer_spec`.

**Feedback rule:** post-submit feedback (CBP consequence, MC correct/incorrect) comes from the **interaction endpoint's response**, never the hydration payload. React treats feedback as server-returned, never client-derived.

### B.2 Gate-state — NEW + server-authoritative
`GET /api/runtime/homeworks/{id}/gate-state?session_id=...` →
```json
{ "cbp": {"passed": true, "checkpoints_correct": 2, "checkpoints_total": 3},
  "mc": {"passed": false, "score_pct": 40, "threshold_pct": 60},
  "practice_arc_unlocked": false }
```
Computed server-side from `phase_attempts`. The client **renders** gate state, never **decides** it (it can't — it has no answers).

### B.3 Per-interaction — reuse, invent nothing
| Interaction | Endpoint | Change |
|---|---|---|
| CBP checkpoint | `POST /api/ai/check-answer` | + `phase: "case_based_preview"` branch |
| Memory Check item | `POST /api/ai/check-answer` | + `phase: "memory_check"` branch |
| Generic runtime answer | `POST /api/ai/runtime/submit-answer` | reuse resolver pattern (ideal for CBP/MC) |
| Practice games | `POST /api/ai/check-answer` | unchanged per-game branches |
| Boss turn | `POST /api/ai/boss-turn` | unchanged |
| Gate-state | `GET /api/runtime/homeworks/{id}/gate-state` | NEW |
| Reflection | `POST /api/ai/reflection` | unchanged |
| Tutor chat | `POST /api/ai/tutor/chat` | unchanged (redaction stays in tutor.py) |

**New surface = 2 GET endpoints + 2 check-answer branches.** New router `server/routes/runtime.py`.

### B.4 Redaction regression test
Assert the hydration response JSON contains NONE of: `expected`, `ans`, `accepted_answers`, `correct`, `option_index`, `is_correct`, `acceptable_keywords`, `consequence`, `correct_path` — for any v2 homework. The fence for the new boundary.

---

## C. React app architecture

### C.1 Component tree
```
<App> (Router; reads hwId+token from URL)
 └─ <RuntimeBoot> (fetch /api/runtime/homeworks/{id} + gate-state)
     └─ <V2FlowController> (Zustand store)
         ├─ <LearningHub> → <SectionTile kind="cbp"|"fc">
         ├─ <CaseBasedPreview>
         │    CaseSetup → Checkpoint×3 → [ReasoningStep?] → FinalSimulation → CbpFeedback
         │    (ReasoningStep only when decision_process_explanation authored)
         ├─ <Flashcards> → <MemoryCheck> → <MemoryItem type=mcq|fill|choose|tf|tile|term>
         ├─ <UnlockGate> (chain-break; gated on practice_arc_unlocked)
         ├─ <PracticeArc> → <GameHost registry> → games + <BossArena> (Why→How→What)
         ├─ <Reflection> (Passed | Needs Retry)
         └─ <TutorWidget> (docked, persistent; leak-safe)
```

### C.1.1 Case-Based Preview — immersive redesign + reasoning step (commit 92824a3)

#### Sub-stage flow

```
case_setup
  → checkpoint_0   (MCQ, graded: phase="case_based_preview")
  → checkpoint_1
  → checkpoint_2
  → [reasoning_step]   ← only when decision_process_explanation authored
  → final_simulation
  → cbp_feedback
```

The reasoning step is **non-blocking**. Unlock gate logic:
- Practice Arc unlocks when MCQ checkpoints ≥ `threshold` (≥2 of 3) — unchanged.
- `gate_state` additionally exposes `reasoning_required` / `reasoning_passed`
  and folds `reasoning_passed` into `cbp.passed`, but the MCQ count drives the
  arc gate. Students who skip or fail reasoning still progress.

#### Key components

| Component | File | Role |
|---|---|---|
| `CaseBasedPreview` | `frontend/app/src/runtime/CaseBasedPreview.tsx` | Sub-stage state machine, data orchestration |
| `CbpBackdrop` | `frontend/app/src/runtime/CbpBackdrop.tsx` | Full-bleed living backdrop (brand-blue Apple-glass) |
| `CbpJourney` | `frontend/app/src/runtime/CbpJourney.tsx` | Winding 9-node journey rail; nodes illuminate as student advances |

Visual language: 3D press-buttons, staged before/after consequence reveal. Matches
the Hub's brand-blue palette.

#### Shared `useColorTrail` hook

`frontend/app/src/runtime/hooks/useColorTrail.ts` — the Hub's pointer/touch
color-trail (eased smoothed head, destination-out fade, click burst) extracted
into a reusable hook. Consumed by both `<LearningHub>` and `<CaseBasedPreview>`;
zero regression on the Hub.

#### Reasoning-step grading

Endpoint: `POST /api/ai/check-answer` with `phase="case_based_preview_reasoning"`.

Request additions beyond the base check-answer shape:
```json
{
  "phase": "case_based_preview_reasoning",
  "homework_id": "string",
  "session_id": "string",
  "reasoning_text": "string"
}
```

Response: `{ "passed": bool, "score": int (0–100), "feedback": "string" }`.

Grading order: keyword-coverage deterministic check → AI judgment
(`server/prompts/runtime/cbp-reasoning-checker.md`, cloned from the RLC grader)
→ deterministic fallback on AI failure.

Redaction guarantee: `concept_keywords`, `method_keywords`, `mistake_keywords`,
`acceptable_keywords`, `rubric`, and `pass_score` are in `ANSWER_BEARING_KEYS`
and are stripped at hydration. Only `prompt` and `min_chars` reach the client.

### C.2 State: **Zustand** (~1KB) — selector subscriptions so TutorWidget re-render doesn't churn PracticeArc. Server-authoritative `gate.*` hydrated from API, never optimistic.

### C.3 Routing: `react-router-dom` v6. Single route `/h/:hwId`. Legacy-vs-v2 fork is **server-side** (React never sees v1). Flow screens are **store-driven state, not URL routes** (prevents gate-skipping). Optional read-only `?screen=` for refresh-resilience.

### C.4 Design system: **CSS Modules + CSS-variable tokens**. Extract `landing.css:8-55` → `frontend/css/_tokens.css`, import into both legacy + SPA. Build `src/shared/ui/`: `<Pill> <DarkSection> <FeatureCard> <LessonPanel> <LaunchShell> <TutorCard>` = React embodiment of the landing components the v2 plan maps per surface. Lean on `design-taste-frontend` / `ui-ux-pro-max` skills. `--landing-spring` + `prefers-reduced-motion` port directly.

### C.5 Tutor widget: thin client over `POST /api/ai/tutor/chat`. **Redaction stays in `tutor.py`** — server rebuilds question context + redacts. React never has the answer (B.1), so it's *stronger* than the HTML runtime. Must emit correct `phase` (`case_based`/`practice`/`boss`).

### C.6 Games: **rewrite all 9 as React, reuse zero JS, reuse 100% grading + content shapes.** Tractable because each game is small and grading/leak/XP are server-side. Sequence rewrites by frequency-of-use. Code-split per game via `React.lazy` in `<GameHost>`.

---

## D. Builder rebuild

- `frontend/app/src/builder/` — authors **v2 net-new only**: CBP 3-checkpoint editor, Memory Check item editor, Practice Arc game composer, Boss Why→How→What editor.
- **No legacy-editor port.** Legacy homeworks stay in the existing vanilla `builder.html`. Two builders coexist (selected by a v2 toggle on creation). Default: net-new v2 only; legacy builder reachable for legacy rows.
- **Live preview** imports the runtime's React components directly (same Vite app) — author sees exactly what the student sees, no iframe. Preview renders **full draft** (answers visible — authoring context); student runtime renders **redacted**. Redaction strictly at API boundary, never in components.
- **Save:** reuse `PUT /api/homeworks/{id}` + `PATCH /api/homeworks/{id}/content` unchanged. Read via existing **unredacted** GET (correct — authoring needs answers).

---

## E. Reuse vs rebuild

| Layer | Disposition | Cite |
|---|---|---|
| Pydantic schemas (+ v2 additive) | **Keep** | `server/schemas/content.py` |
| Grading / answer checker / hybrid+review | **Keep** | `answer_checker.py`, `grading.py`, `ai.py:361-377` |
| Tutor + answer-leak redaction | **Keep** | `tutor.py:808-833` |
| DB, migrations, attempts repo | **Keep** | `server/db/*` |
| Per-interaction endpoints | **Keep** | check-answer / boss-turn / tutor / reflection |
| Injector (legacy `/h/{id}`) | **Keep** | `injector.py` — serves all v1 |
| `/h/{id}` route | **Add v2 fork** | `homework_page.py:145` |
| Static mounts | **Add `/app`** | `app.py:157-169` |
| Per-game deny-lists | **Extract to shared module** | `injector.py:98-114` → `redaction_constants.py` |
| Runtime redactor | **NEW** | `server/services/runtime_redactor.py` |
| Runtime read router (2 GETs) | **NEW** | `server/routes/runtime.py` |
| check-answer branches (CBP, MC) | **NEW (additive)** | `ai.py:2106` dispatch |
| React SPA (runtime + builder) | **NEW** | `frontend/app/` |
| TS types from Pydantic | **NEW (CI)** | `src/shared/types/content.gen.ts` |
| Design-token bridge | **NEW (extract)** | `frontend/css/_tokens.css` |
| Legacy pages + editors | **Keep** | `frontend/index.html` etc. |

**Net backend new code: ~1 service + 1 router (2 GETs) + 2 dispatch branches.** Additive — matches the proven migration pattern.

---

## D.1 Builder / Authoring — shipped (DaddysBranch, 2026-05-21)

This section documents the authoring surface that shipped alongside the v2 runtime.

### Dashboard routing

The **legacy dashboard** (`frontend/index.html` + `frontend/js/dashboard.js`) stays the homework list at `/`. The dashboard reads the `flow_version` field now returned on every `GET /api/homeworks` list row and routes card-open by version:

| `flow_version` value | Builder opened |
|---|---|
| `"v2"` | React builder at `/app/builder?id=<id>` |
| absent / `"v1"` | Vanilla builder at `/builder.html?id=<id>` (unchanged) |

New homework creation no longer prompts for Easy/Hard. `POST /api/homeworks` stamps `flow_version: "v2"` and opens the React builder directly.

### React builder shell (`frontend/app/src/builder/BuilderApp.tsx`)

The React builder is reskinned to the legacy builder's left-sidebar design. It loads the unredacted `GET /api/homeworks/{id}` payload (authoring needs answers), and debounce-saves via `PUT /api/homeworks/{id}`.

**Section editors (left sidebar → right panel):**

| Sidebar entry | Editor component | Authors |
|---|---|---|
| Metadata | MetadataEditor | `meta.*` |
| Case Preview | CbpEditor | `case_based_preview` |
| Memory Check + Flashcards | MemoryCheckEditor | `memory_check`, `flashcards` |
| Practice Arc | PracticeArcSection | `practice_arc.games[]` ordering + per-game `gb_*` arrays |
| — Tile Match | TileMatchEditor | `gb_tile_match` |
| — Sentence Fill | SentenceFillEditor | `gb_sentence_fill` |
| — Mystery Box | MysteryBoxEditor | `gb_mystery_box` |
| — Puzzle Lock | PuzzleLockEditor | `gb_puzzle_lock` |
| — Adaptive Quiz | AdaptiveQuizEditor | `gb_adaptive_quiz` |
| — Memory Palace | MemoryPalaceEditor | `gb_memory_palace` |
| — Tic-Tac-Toe | TttEditor | `gb_ttt` |
| — Real Life Challenge | RealLifeChallengeEditor | `real_life_challenge` |
| Boss | BossEditor | `boss_questions` |
| Reflection | ReflectionEditor | `reflection` |

### Live preview

The builder's preview panel imports the **same runtime React components** used by the student flow (`frontend/app/src/runtime/`). Authors see exactly what the student sees from their current draft. Answers are visible in the preview (authoring context) — redaction only applies at the `GET /api/runtime/homeworks/{id}` API boundary, not in the shared components themselves.

### Backend support for authoring

- `GET /api/homeworks` list returns `flow_version` per row so the dashboard can route without fetching the full record.
- `POST /api/homeworks` accepts an optional `content_json` body field on create (used to stamp the v2 scaffold and `flow_version: "v2"` in one call).

---

## F. Phasing

| Phase | Deliverable |
|---|---|
| **F0 Foundation** | Vite+TS scaffold `frontend/app/`; `/app` mount; TS type-gen from Pydantic; `_tokens.css`; `/h/{id}` v2 fork → empty SPA shell; design primitives. |
| **F1 Hydration + redaction** | `runtime_redactor.py`; `GET /api/runtime/homeworks/{id}`; gate-state endpoint; the **leak regression test** (§B.4). Highest-risk — land + over-test first. |
| **F2 Runtime shell + Learning Hub + CBP** | `<RuntimeBoot>`, Zustand store, `<LearningHub>`, full `<CaseBasedPreview>`; `check-answer phase=case_based_preview`; CBP gate. |
| **F3 Flashcards + Memory Check + Unlock Gate** | `<Flashcards>` viewed-tracking, `<MemoryCheck>` 6 item types, `check-answer phase=memory_check`, both-passed → `<UnlockGate>` animation. |
| **F4 Practice Arc + games + Boss** | `<GameHost>` registry; rewrite games in frequency order; `<BossArena>` Why→How→What. Longest phase. |
| **F5 Reflection + tutor polish** | `<Reflection>`; docked `<TutorWidget>`; reduced-motion + dark-mode pass. |
| **F6 React Builder** | CBP/MC/PracticeArc/Boss editors; live preview via shared components; save via PUT/PATCH. |
| **F7 Parity + cutover** | Parity audit; flip new-homework default to React; legacy stays for v1. |

F1 is the analog of the v2 plan's "PR-1 foundation" — self-contained, highest-risk, everything depends on it.

---

## Implementation status — COMPLETE (DaddysBranch, 2026-05-21)

**All phases F0–F7 are shipped on `DaddysBranch`.** The React SPA runtime renders
every v2 screen + the 8 built Practice-Arc games; the redacted hydration API and
the server-authoritative gate-state API are live; the full light-glass redesign
is applied. `server` stays on the legacy HTML runtime; v2 rows fork to React in
`server/routes/homework_page.py`.

### Wave-B security blockers (4 closed)

A `codex` security pass surfaced and closed four answer-leak / gate-integrity
blockers, each now fenced by the redaction/gate regression suite:

1. **Redaction completeness** — the deny-list is the single-source
   `ANSWER_BEARING_KEYS` (`server/services/redaction_constants.py`), deleted
   fail-closed at every nesting depth; injector + hydration redactor share it so
   they cannot drift. (+ tutor preview-escape fix below.)
2. **Tile-match opaque tokens** — hydration ships independently-shuffled per-side
   tokens (`{lefts:[{lid}], rights:[{rid}]}`) instead of the leaky shared-`id`
   pair list; the grader recovers the pair index from each HMAC token
   (`server/services/tile_match_tokens.py`). `gb_memory_match` is dropped from
   hydration.
3. **Gate inflation** — `gate_state.py` aggregates on the SERVER-DERIVED
   `subphase` key (`checkpoint_{idx}` / `item_{idx}`), never the client
   `question_id`, so a student can't resubmit under fresh ids to inflate the
   correct count past 100%.
4. **Practice-gate enforcement** — all 8 practice-arc phases call
   `_enforce_practice_unlocked(req)` and return `403 PRACTICE_LOCKED` until the
   arc unlocks (defense in depth — the frontend gate is presentation-only).
   Bonus: the tutor preview-escape was closed (practice/boss phases strip
   answer-bearing keys before the LLM prompt).

### Design language

Full **light Apple-glass redesign** of all screens + games, driven by the
extracted `landing.css` token set (`frontend/css/_tokens.css`, imported into both
legacy + SPA). CSS Modules + CSS-variable tokens throughout (no Tailwind /
CSS-in-JS); `--landing-spring` + `prefers-reduced-motion` honored.

### Five DDD domains

The backend v2 surface organizes into five bounded domains:

| Domain | Responsibility | Key files |
|---|---|---|
| **Hydration & Redaction** | Student-safe read payload; fail-closed answer stripping; tile-match tokens. | `routes/runtime.py`, `services/runtime_redactor.py`, `services/redaction_constants.py`, `services/tile_match_tokens.py` |
| **Gating & Unlock** | Server-authoritative Practice-Arc unlock from `phase_attempts`. | `services/gate_state.py` |
| **Grading & Resolvers** | Per-phase `/check-answer` dispatch; deterministic-first grading; `{correct, feedback}` contract. | `routes/ai.py` (phase resolvers), `services/answer_checker.py` |
| **Runtime-Flow SPA** | React screens, Zustand store, `<GameHost>` registry, game order. | `frontend/app/src/runtime/` (incl. `gameOrder.ts`, `GameHost.tsx`) |
| **Tutor** | Docked leak-safe chat; server-side question redaction. | `services/tutor.py`, `POST /api/ai/tutor/chat` |

### Game build status

8 of 9 keys built and registered in `GameHost.tsx`: `tile_match`,
`sentence_fill`, `real_life_challenge`, `ttt`, `memory_palace`, `adaptive_quiz`,
`mystery_box`, `puzzle_lock` (+ `boss`). The 9th key, **`story_mode`**
(`gb_story_mode`), is unbuilt (greenfield) and falls through to the "coming soon"
skip card.

---

## G. Risks

1. **Answer-leak boundary moving to JSON API (highest).** Mitigate: extract deny-lists to one shared module; allow-list-fails-closed; §B.4 regression test; TS `StudentSafeQuestion` type that can't hold answer fields.
2. **Dual-runtime drift.** Mitigate: gating + grading are server-authoritative + shared; rules can't drift even if pixels do.
3. **Reproducing 21.7k LOC of HTML behavior.** Mitigate: React renders **v2 only** — a new flow with no legacy behavior to reproduce. v1 stays on HTML forever.
4. **SPA first-paint / SEO of share links.** Mitigate: inline skeleton + `meta.title` + OG tags server-side in `_render_spa_shell`. Full SSR out of scope (no Node in prod). OG injection mandatory for Telegram cards.
5. **Build/deploy on launchd Mac mini.** Mitigate: build in CI/dev box, **commit `dist/`**; Mac mini only serves static. Never runs Vite.
6. **Bundle size.** Mitigate: route + game-level code-split (`React.lazy`); target initial chunk <150KB gz.
7. **CSP.** React loads hashed external bundles → v2 path is more CSP-friendly. Don't change shared CSP (breaks legacy); note the long-term win.

---

## Anchor files (all under repo root)

- `server/app.py` (mounts + page routing 112-169)
- `server/routes/homework_page.py:145` (the `/h/{id}` fork point)
- `server/routes/homework.py` (unredacted CRUD GET 332; PUT/PATCH 409/439)
- `server/routes/ai.py` (per-interaction; check-answer dispatch 2106-2205)
- `server/services/injector.py:98-114` (per-game deny-lists — extract)
- `server/services/tutor.py:808-833` (redaction — model for fail-closed)
- `server/services/content_json_compat.py` (read-path normalization 261/340)
- `server/schemas/content.py` (contract in code; v2 additive models)
- `server/template/runtime.js` (the JSON-API bridge React generalizes)
- `frontend/css/landing.css:8-55` (design tokens — extract to `_tokens.css`)
- `docs/HOMEWORK_FLOW_V2_PLAN.md` (the flow + design-language mapping)
