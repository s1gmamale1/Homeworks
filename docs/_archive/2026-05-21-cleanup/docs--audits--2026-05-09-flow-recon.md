# Flow Recon — 2026-05-09

*(For Agents B + C. Pure facts, no opinions.)*

---

## 1. Common Phase Backbone

All subjects share this skeleton (subset varies by difficulty tier and subject):

- classify (Easy/Hard gate — all except History, English always-Hard)
- preview (easy: 4-5 panels; hard: 6-7 panels)
- flashcards
- memory-sprint (Easy: 5 items; Hard: 7-20 items depending on subject)
- game-breaks (Easy: 2 games; Hard: 3 games)
- real-life (Hard only; skipped in History)
- consolidation (Hard only; conditional on ≥2 interlocking concepts)
- final-challenge / boss fight (Hard only; skipped in Easy)
- reflection (all)

Reading phase exists only in English (no flow.md found; confirmed via instruction.md which calls reading.md in step 3).

---

## 2. Per-Subject Flow

| Subject | Easy/Hard | Phases (Easy/Hard) | Mandatory game | Skipped phases (Easy) | Skipped phases (Hard) | Notes |
|---|---|---|---|---|---|---|
| math-algebra | both | 5 / 8 | Adaptive Quiz | Real-Life, Consolidation, Final Challenge | consolidation conditional | CPA method; Notebook Capture built into AQ |
| history | hard-only | — / 6 (always) | Tile Match | n/a | Reading, Real-Life | Narrative IS content; no AQ ever |
| english | hard-only (CEFR-leveled) | — / 9 | none specified | n/a | consolidation conditional | Adds Reading phase unique to English; no flow.md file exists — derived from instruction.md |
| geometriya-g7-11 | both | 5 / 8 | Puzzle Lock | Real-Life, Consolidation, Final Challenge | consolidation conditional | Notebook Capture mandatory Hard ≥ every 2 sessions |
| kimyo-g7-11 | both | 5 / 8 | Equation Balance Puzzle Lock | Real-Life, Consolidation, Final Challenge | consolidation conditional | Lab Report Capture mandatory Hard lab chapters |
| physics | both | 5 / 8 | Adaptive Quiz | Real-Life, Consolidation, Final Challenge | consolidation conditional | Team-conflict narrative in real-life |
| biology | both | 5 / 8 | Adaptive Quiz | Real-Life, Consolidation, Final Challenge | consolidation conditional | No Notebook Capture (TF-1 exempt); narrative-process real-life format |

---

## 3. Runtime Shared Prompts (server/prompts/runtime/)

- `_shared_context_contract.md` — defines the 6-section context payload every AI prompt receives (session_id, phase, performance snapshot, recent history, untrusted student message)
- `answer-checker.md` — generic answer checking (correctness gate)
- `answer-checker-boss.md` — boss-phase answer checking
- `answer-checker-language.md` — 2-axis LMR rubric for language subjects (Grammatical Accuracy + Lexical Quality, 1-4 scale)
- `answer-checker-math.md` — math-specific answer checking (likely sympy path)
- `boss-answer-checker.md` — separate boss-fight answer evaluation prompt
- `boss-question-generator.md` — generates next boss question based on student performance
- `boss-tutor.md` — in-character boss voice for post-answer reactions
- `input-guardrail.md` — input safety screening
- `notebook-grader.md` — grades Notebook Capture photo submissions
- `real-life-challenge-grader.md` — grades Real-Life typed responses
- `reflection-coach.md` — generates personalized Uzbek coaching after reflection
- `tutor-assistant.md` — live chat tutor (Opus 4.7 tone, Uzbek/Russian/English language switching)
- `tutor-boss-plan.md` — planning prompt for boss-mode tutor strategy

---

## 4. Game-Break Inventory

| Game | Runtime panel ID | Registered in gbActiveGameOrder | Used in (per flow.md) | Mandatory in | UI complexity (1-5) |
|---|---|---|---|---|---|
| Adaptive Quiz | gb-panel-aq | yes (slot 0) | math, physics, biology, kimyo (optional), geometriya (optional) | math, physics, biology | 3 |
| Why Chain (legacy Sentence Fill wc) | gb-panel-wc | yes (slot 1, label "Sentence Fill") | legacy — wired as GB_WHY_CHAIN | none specified in flow.md | 2 |
| Tile Match | gb-panel-tm | yes (slot 2) | math, history, biology, physics, kimyo, geometriya, english | history (mandatory slot 1) | 3 |
| Puzzle Lock | gb-panel-pl | yes (slot 3) | geometriya (mandatory), kimyo (mandatory) | geometriya, kimyo | 3 |
| Mystery Box | gb-panel-mb | yes (slot 4) | geometriya (optional) | none | 2 |
| Tic Tac Toe | gb-panel-ttt | yes (slot 5) | not in any current flow.md | none | 4 |
| Sentence Fill (sf) | gb-panel-sf | yes (slot 6) | math, history, biology, physics, kimyo, geometriya, english | history | 2 |
| Memory Palace | gb-panel-mp | yes (slot 7) | history (consolidation), biology (consolidation) | none (content-gated) | 4 |
| Memory Match (mm) | NO dedicated panel in HTML | JS init function exists (gbInitMM), GB_MEMORY_MATCH constant injected | math, history, biology, physics, english | history (listed in flow.md) | 2 |

**Key discrepancy:** Memory Match has JS logic and a legacy data constant (`GB_MEMORY_MATCH`) but has NO entry in `gbActiveGameOrder()`. It is not routed by the runtime game-ordering function even though flow.md specs for history, biology, math, and physics list it as an available game.

---

## 5. Where Uzbek Content Is Generated / Surfaced

- All 7 subject `instruction.md` files mandate Uzbek, formal "Siz" (zero "sen") — confirmed for math-algebra, history, english (55/45 national/global balance rule), biology, geometriya, kimyo, physics
- All preview panels (easy + hard) — AI-generated Uzbek text, no post-processing filter
- Flashcards — AI-generated Uzbek term/definition pairs, no post-processing
- Memory-sprint items — AI-generated Uzbek MC/TF/YNNG questions
- Game-break item text (all games) — AI-generated Uzbek labels/questions
- Real-Life scenario text — AI-generated Uzbek narrative
- Consolidation mnemonics — AI-generated Uzbek memory aids
- Final Boss question text — generated by `boss-question-generator.md` (Uzbek)
- Boss in-character reactions — generated by `boss-tutor.md` (language mirrors student register)
- Reflection coaching — generated by `reflection-coach.md` (explicitly "formal Siz throughout")
- Live tutor chat — `tutor-assistant.md` (Kimi K2.6 since PR #209; language-detection routing: Uzbek Latin / Cyrillic / Russian / English)
- **No subject prompt explicitly addresses Uzbek grammar quality of the AI's own output.** There is a rule in `tutor-assistant.md` to NOT correct the student's grammar; there is no inbound quality-check pass on LLM-generated Uzbek content before it is stored or rendered.

---

## 6. Where the Cycle Is Currently Interactive vs Passive

| Phase | Interaction mode |
|---|---|
| preview (all panels) | read-only (swipe/tap to advance panels; no answer required) |
| flashcards | tap to flip (front→back); swipe to advance; no graded input |
| memory-sprint | tap MC / tap TF / tap YNNG — single tap, no typing |
| game-breaks: Adaptive Quiz | typed answer + optional photo upload (Notebook Capture) |
| game-breaks: Tile Match | drag-and-drop pairs |
| game-breaks: Sentence Fill (sf) | drag/select missing piece |
| game-breaks: Puzzle Lock | typed input per step |
| game-breaks: Memory Match | tap to flip card pairs |
| game-breaks: Tic Tac Toe | tap grid cell; server-authoritative grading |
| game-breaks: Memory Palace | 4-step: pick palace (tap) → place concepts (tap/drag) → walkthrough (read) → recall MC (tap) |
| game-breaks: Mystery Box | tap to open box; likely tap to select |
| real-life | typed free-response answer (AMR-graded, 2-axis rubric) |
| consolidation | read-only walkthrough + optional self-check prompt (engagement-only, ungraded per grading.py) |
| final-challenge (boss) | typed answer per boss question; HP overlay visual |
| reflection | typed free-text (student writes reflection); ungraded (grading.py: "ungraded") |

---

## 7. "Raw / Generated" Content Surfaces

- All preview panel text goes from LLM → `content_json` → injector → rendered HTML with no intermediate validation pass for content quality
- Flashcard term/definition text: same pipeline — LLM → stored → rendered
- Memory-sprint question text: same pipeline
- Game-break item text (all games): same pipeline
- Boss questions: generated at runtime by `boss-question-generator.md` via AI route, then cached; no post-validation on Uzbek quality
- Tutor responses: real-time, not stored in content_json; no grammar post-filter

**Validation tools that DO exist and the phases they guard:**

- `server/services/answer_checker.py` — guards answer correctness at submission time (student answers vs answer_spec); does not validate AI-generated content
- `server/services/grading.py` — aggregates scores; no content validation role
- `server/services/latex_validator.py` — validates LaTeX in equations; only applies to math formulas in content, not Uzbek prose
- `server/services/math_normalize.py` — normalizes math answer strings for comparison; no Uzbek role
- `answer-checker-language.md` (LMR rubric) — evaluates student's written English/language-subject answers; does NOT check the quality of the AI-authored Uzbek question text

**Net:** No validation layer exists between LLM output and student-facing Uzbek text.

---

## 8. Open Factual Gaps

- **English flow.md is absent.** No `server/prompts/english/flow.md` file exists. English phase structure was derived from `instruction.md` only; the 9-phase sequence (including Reading) is listed there but no authoritative flow diagram was found.
- **Memory Match routing gap is unclear.** `GB_MEMORY_MATCH` is injected and `gbInitMM` runs, but Memory Match has no slot in `gbActiveGameOrder()` — it is unknown whether this game is silently skipped at runtime for all current content, or whether there is a separate routing path not captured here.
- **"Uzbek grammar mistakes" in the complaint cannot be traced to a specific generation step** without seeing live homework content. The claim is plausible given zero post-generation grammar filter, but this recon cannot confirm frequency or locus.
- **Reaction Chain and Notebook Capture** appear in some flow.md notes as available games but are absent from `gbActiveGameOrder()` — their runtime status (removed, legacy, partially wired) was not fully resolved in this pass.
- **Mystery Box interaction model** was not confirmed; the panel HTML exists but the tap-to-reveal mechanic details were not read.
