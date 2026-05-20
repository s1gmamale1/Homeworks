# NETS Homework Builder — Combined Issues Inventory

**Purpose:** Brief issue inventory compiled from the user’s complaints, ChatGPT review, Claude audit notes, and Kimi review.  
**Focus:** Prompt flow, interactivity, content quality, Uzbek grammar, runtime alignment, and product gaps.

---

## 1. Prompt Architecture & Flow Issues

### Issue: Prompt system is too template-driven
- Fixed panel structures force every topic into the same shape.
- Some topics need comparison, experiment, proof, process, or misconception panels instead.

### Issue: Flow is mostly linear, not adaptive
- Strong and weak students mostly follow the same path.
- EASY/HARD is decided once, then the cycle stays fixed.

### Issue: No continuous mastery-based branching
- Memory Sprint/Game results do not sufficiently change the next phase.
- No clear remediation loop or acceleration path.

### Issue: No central interaction-beat contract
- Phases do not consistently require prediction, choice, micro-checks, error detection, or reflection.

### Issue: No single master prompt contract
- Similar rules are repeated across subjects.
- Updates can drift because there are no shared modules for games, Uzbek QA, register, or interaction rules.

### Issue: Prompt files are too duplicated
- Language rules, visual rules, game rules, and phase rules are repeated in many files.
- This increases maintenance cost and inconsistency.

### Issue: Prompt files reference old or wrong paths
- Some instructions reference old `06-prompts/...` paths.
- Some Russian prompt references appear broken or missing.

### Issue: English has no `flow.md`
- English uses `instruction.md` as its flow source, unlike other subjects.
- This makes English easier to drift from the intended cycle.

---

## 2. Interactivity Issues

### Issue: Interactivity is shallow
- Most student actions are tap, select, match, or answer.
- Students rarely construct, drag, draw, manipulate, explain, or decide.

### Issue: Preview is too passive
- Preview mostly delivers explanations.
- It lacks mandatory prediction, reveal, micro-check, and mistake-trap steps.

### Issue: Flashcards are weak recall tools
- Many cards are term → definition.
- They do not use enough blanks, diagrams, incomplete processes, or scenario prompts.

### Issue: Flashcards lack confidence tracking
- No `Bildim / Bilmadim` style self-check.
- Weak cards are not reused in Reflection or Boss.

### Issue: Memory Sprint lacks meaningful feedback
- Wrong answers often do not explain the misconception.
- No consistent “Why was I wrong?” expansion.

### Issue: Memory Sprint is too tap-only
- MC/TF/YNNG limits construction.
- It mostly tests recognition, not deeper understanding.

### Issue: Real-Life Challenge is often text-only
- It can become a professional-flavored word problem.
- It lacks decision trees, simulations, messy data, and consequence chains.

### Issue: Static SVGs are not interactive
- Students view diagrams but do not manipulate them.
- No default sliders, draggable labels, live graphs, or adjustable variables.

### Issue: Student choice is limited
- Students rarely choose path, role, game type, challenge style, or explanation depth.

### Issue: Student-generated artifacts are underused
- Students rarely upload, draw, caption, label, or explain.
- Their own work is not reused enough in feedback or reflection.

---

## 3. Game Design Issues

### Issue: Games are quiz variants wearing game skins
- Adaptive Quiz, Tile Match, Memory Match, and Sentence Fill are mostly assessment formats.
- They lack strategy, discovery, branching, and meaningful consequences.

### Issue: Game schemas do not match game descriptions
- Prompts describe rich games like Puzzle Lock, Mystery Box, Reaction Chain, Notebook Capture, and Lab Capture.
- Many output schemas still only expose legacy keys like `adaptive_quiz`, `why_chain`, and `memory_match`.

### Issue: Game inventory is inconsistent
- Some subjects use or ban mechanics differently.
- No canonical active/deprecated/future game list exists.

### Issue: Why → How → What is semantically broken
- The mechanic’s label and schema are inconsistent.
- It is sometimes hidden behind `why_chain` or Sentence Fill style naming.

### Issue: Boss Fight is not game-like enough
- HP can be cosmetic.
- Boss often feels like a final quiz with a health bar.

### Issue: Boss phases are not clearly defined
- No strong Probe → Adapt → Climax structure.
- Boss behavior does not clearly evolve based on student performance.

### Issue: Static/dynamic boss boundary is unclear
- Subject prompts still generate static boss questions.
- Runtime has dynamic boss generation.
- Fallback and builder controls need a clearer contract.

### Issue: Mystery Box can become low-value
- It risks becoming casino-style visual reward.
- It needs a clear educational mechanic, not random reward animation.

### Issue: Tic Tac Toe has gimmick risk
- TTT can distract from learning.
- It is only suitable for simple closed recognition, not deep reasoning.

### Issue: Memory Match may duplicate flashcards
- Useful only for genuinely pair-based content.
- Should not be revived broadly unless runtime support and learning value are clear.

### Issue: Game Breaks framing may be weak
- “Break” implies pause from learning.
- The phase should communicate skill practice, not side entertainment.

---

## 4. Content Quality Issues

### Issue: Content can feel raw/generated
- Some sections feel like textbook text rewritten by AI.
- There is not enough surprise, contrast, conflict, or student action.

### Issue: Origin panels are repetitive
- Origin often follows the same scientist/problem/discovery/impact template.
- It underuses rivalry, debate, failure, accident, rediscovery, and controversy.

### Issue: Uzbek context can feel forced
- Local references like Tashkent metro or Navoi GES may be inserted unnaturally.
- Local context should be meaningful, not quota-filling.

### Issue: Industry Application is often generic
- Roles repeat across subjects.
- Tasks and consequences are not always concrete or memorable.

### Issue: Professional scenarios lack vivid details
- Few named workplaces, quantified stakes, or realistic professional decisions.
- This makes “real-world” content feel decorative.

### Issue: Reflection is formulaic
- It often follows the same summary → question → spaced repetition → closing pattern.
- It does not always reference actual mistakes or student goals.

### Issue: Results screen underuses learning signals
- Weak topics, XP, boss performance, and growth moments are not summarized strongly enough.

### Issue: Content freshness is limited
- Content is mostly tied to textbook input.
- No default current-events or recent Uzbekistan/global examples.

### Issue: Living content pipeline is missing
- No standard step to enrich content with current, verified context.
- Freshness-sensitive examples can become outdated.

### Issue: Final homework lacks strong narrative arc
- Phases are assembled in order, but may not build into one mission.
- Preview, games, Real-Life, Boss, and Reflection should connect more tightly.

### Issue: Some sections are too long for mobile
- Hard previews and Real-Life sections can become text-heavy.
- Phone-first UX needs tighter pacing and more interaction instead of more prose.

---

## 5. Uzbek Language & Register Issues

### Issue: Uzbek grammar quality is not enforced
- “Use Uzbek formal Siz” is only an instruction, not a validation layer.
- Grammar, morphology, and naturalness errors can slip through.

### Issue: No Uzbek grammar validator
- No dedicated post-generation check for Uzbek agreement, suffixes, word order, or calques.

### Issue: `Siz` / `sen` register inconsistency
- Generated homework uses formal `Siz`.
- Tutor or boss may mirror casual `sen`, causing register whiplash.

### Issue: Formal `Siz` agreement can be wrong
- AI may produce incorrect forms like mismatched verb agreement.
- Formal Uzbek requires consistent conjugation.

### Issue: Code-switching rules are risky
- Students mix Uzbek, Russian, and English.
- Tutor can overreact to English terms or feature names and switch language unnecessarily.

### Issue: Scientific terminology is inconsistent
- Terms like Newton/Nyuton/N’yuton may vary.
- Units and transliterations can drift across subjects.

### Issue: No central Uzbek scientific glossary
- Terms, units, and transliterations are not enforced through one canonical file.

### Issue: Apostrophe style is inconsistent
- `o'`, `g'`, `oʻ`, `gʻ`, `o‘`, and `g‘` may mix.
- This affects readability and answer normalization.

### Issue: Uzbek sentence style can become unnatural
- English or Russian syntax can leak into Uzbek.
- Scientific explanations can become choppy or stiff.

### Issue: Sentence length rules can hurt Uzbek style
- Very short sentence caps may make scientific Uzbek robotic or telegraphic.

### Issue: Too-formal wording can overappear
- Words like `mazkur` and `ushbu` may make content feel bureaucratic.

### Issue: No human/native review loop
- Automated QA will not catch every naturalness or cultural issue.
- Native review may be needed for high-quality production content.

---

## 6. English-Specific Issues

### Issue: English lacks speaking/listening interaction
- Current English flow mostly supports reading and writing.
- Dialogue, listening, pronunciation, and speaking tasks are missing.

### Issue: English-Uzbek bridge is underdeveloped
- English grammar is taught too separately from Uzbek.
- Articles, tense/aspect, prepositions, and register need Uzbek-speaker-specific explanations.

### Issue: English cultural relevance is weak
- Examples can feel generic or global instead of grounded in Uzbek learner reality.

### Issue: Pronunciation and stress practice are missing
- Vocabulary may mention stress traps, but no real stress/pronunciation game exists.

### Issue: Dialogue simulation is missing
- English needs branching conversations, register choices, and practical speaking scenarios.

---

## 7. Subject-Specific Issues

### Issue: History flow is thinner than STEM subjects
- History has no easy/hard split.
- It lacks a separate Real-Life phase.
- Game options are limited.

### Issue: History lacks enough source/evidence work
- Source evaluation is underused in games.
- Needs Source Detective, claim checks, and perspective-taking.

### Issue: Chemistry safety is prompt-level, not system-level
- Safety is required by prompts but not enforced by a validator.
- Hazard terms and safety notes need standardization.

### Issue: Chemistry equation validation may rely too much on AI
- Balanced equations need atom-count checks.
- Student-facing chemistry output should be validated more strictly.

### Issue: Geometry needs stronger visual runtime support
- Prompt asks for progressive diagrams and proof states.
- Runtime must support step-by-step visual proof rendering.

### Issue: Geometry proof metadata is insufficient
- Theorem-before-use and diagram marks need consistent structure.
- Text-only fallback damages geometry learning.

### Issue: Biology “no calculations” rule may be too broad
- Upper-grade biology includes graphs, ratios, populations, and data.
- Biology should support quantitative reasoning where appropriate.

### Issue: Math/Algebra grade range is incomplete
- Current math/algebra focus is mostly G5–9.
- G10–11 math needs distinct prompt coverage.

### Issue: History always-hard mode may overburden lower grades
- G5–7 history may need lighter flow variants.

### Issue: Reading/literacy subjects are underdeveloped
- Uzbek, Russian, and Literature prompt systems are missing.
- Reading inference/evidence skills are not broadly supported.

---

## 8. Coverage & Product Scope Issues

### Issue: Missing subject prompt directories
- Russian, Uzbek, and Literature may appear in UI/routes but lack prompt directories.

### Issue: Unsupported subject/grade combos may be accepted
- Teachers may select subjects or grades that backend cannot properly generate.

### Issue: Grades 1–4 are absent
- Lower grades need different pedagogy and cannot reuse G5+ prompts directly.

### Issue: Russian-medium support is incomplete
- Russian-language textbooks need dedicated terminology and style prompts.

### Issue: Video/media infrastructure is missing
- No strong video/audio block schema or renderer exists.
- Video and listening features cannot be solved by prompts alone.

### Issue: Teacher-facing materials are missing
- No teacher view, lesson-plan export, or PPTX export pipeline.

### Issue: Some desired features are new product verticals
- Audio, video, PPTX, new subjects, and G1–4 are not small prompt fixes.

---

## 9. Runtime, Backend & Maintenance Issues

### Issue: Backend has dead or duplicated code
- `ai_plan4.py` appears to be unregistered/dead duplicate code.
- `final_report.py` may be unused.
- Multiple tutor/boss/orchestrator paths increase confusion.

### Issue: AI service architecture is partially migrated
- Some paths use `ai_orchestrator`; others use `ai_gateway`.
- Migration lifecycle is unclear.

### Issue: Tutor paths are duplicated
- `tutor_chat` and `tutor_chat_v2` both exist.
- Different paths can behave inconsistently.

### Issue: Legacy and dynamic boss systems coexist
- Both old and new boss paths exist.
- This increases drift and testing burden.

### Issue: Runtime constants are hardcoded
- Prompt caps, message caps, boss framing limits, persona traits, and registry order are hardcoded.

### Issue: Async/sync inconsistencies may affect latency
- Logging and health checks may run in request path.
- Some health checks may trigger real LLM calls.

### Issue: Cache and compatibility layers hide schema drift
- Old content shapes still work.
- This makes it harder to enforce new contracts.

### Issue: Generated assembly can hide phase mismatch
- Runtime may silently degrade when phase schemas are wrong.
- Different subjects have different phase counts and progress needs.

### Issue: Progress mapping can drift
- English, History, and STEM flows differ.
- UI progress dots must match each subject’s real flow.

---

## 10. Security, Anti-Cheat & Grading Issues

### Issue: Answer-leak security mostly works but needs more tests
- No major answer leak found.
- Missing regression tests still leave risk.

### Issue: Boss answer stripping needs regression coverage
- Need tests proving expected answers never enter boss persona prompts.

### Issue: Provider fallback stripping needs consistency tests
- Answer hiding should remain safe across all provider fallback paths.

### Issue: AMR grading is strong but narrow
- Real-Life/Boss require reasoning, but earlier phases often train recall.
- Practice should prepare students for AMR-style reasoning.

### Issue: Bloom/PISA tags may be superficial
- Tags may not reflect actual task difficulty.
- Tap-only questions can be mislabeled as high-level.

### Issue: Post-generation validation is incomplete
- Need validation for grammar, renderable games, valid SVG, Bloom/PISA match, and interaction beats.

### Issue: Chemistry/lab safety validation is incomplete
- Hazard-related items need enforced safety context.

---

## 11. Rewards, XP & Motivation Issues

### Issue: XP is mostly cosmetic
- XP is not strongly persisted or summarized.
- Closing tab can lose reward values.

### Issue: Boss XP is underused
- Boss performance should appear in results more clearly.
- XP should reward mastery, not clicking.

### Issue: XP persistence creates anti-grind risk
- Repeated checks/replays could farm rewards if sequencing is weak.

### Issue: Leaderboards/streaks can harm learning incentives
- They may reward attendance or grinding instead of mastery.

### Issue: Reward design can become casino-like
- Mystery Box and random rewards must avoid lootbox-style learning distraction.

### Issue: Progress/growth visibility is weak
- Students need clearer “you improved here” feedback.

---

## 12. Data, Metadata & Adaptation Issues

### Issue: Prompt outputs lack rich metadata
- Need concept IDs, skill tags, misconception IDs, source references, renderability hints, and game target skills.

### Issue: Content lacks a mistake model
- Common misconceptions are not always captured.
- Feedback and games do not consistently target known mistakes.

### Issue: Source confidence is missing
- If extraction is weak, generation may still proceed confidently.
- Need low-confidence fallback behavior.

### Issue: Fallback behavior is not clearly defined
- Missing rules for invalid SVG, unsupported games, failed Uzbek QA, weak source extraction, and dynamic boss failure.

### Issue: Live tutor context can be weak
- Tutor depends on screen and question context.
- Better metadata would make tutor help more precise.

### Issue: BOST goal is underused
- Student goal is not always captured, stored, and resurfaced meaningfully.

---

## 13. Mobile & UX Issues

### Issue: Visual accessibility needs stricter enforcement
- SVGs may be too small or complex for phones.
- Mobile-first diagram rules need stronger checks.

### Issue: Drag/drop games need phone-first design
- New interactivity must work well on mobile, not just desktop.

### Issue: Long text blocks hurt mobile experience
- Interaction should replace some prose, not simply add more content.

### Issue: Formal tone can conflict with engagement
- Generated content should stay respectful.
- Live tutor may be more casual.
- The boundary between content voice and tutor voice needs clarity.

---

## 14. Scope & Roadmap Issues

### Issue: Scope creep risk is high
- Many ideas are attractive but not all are prompt fixes.
- Audio, video, new subjects, G1–4, PPTX, and simulations require larger product work.

### Issue: Prompt redesign must happen before adding many games
- Adding games without shared contracts repeats current mismatch.

### Issue: Some proposed games have feasibility risks
- Interactive simulations, audio, heatmaps, and cross-session memory need backend/frontend support.

### Issue: Improvements need prioritization
- Issues should be separated into prompt-only, frontend, backend, QA, and new product verticals.

---

## 15. High-Level Root Problems

### Issue: The system behaves like an AI worksheet generator
- It has structure, but not enough adaptive interaction.

### Issue: Prompt logic and runtime rendering are not fully aligned
- Prompts describe experiences that UI/schema may not support.

### Issue: Uzbek quality relies too much on model obedience
- Grammar/style needs validation, glossary, and register protocol.

### Issue: Learning design is not yet skill-based enough
- Game choice and phase behavior should depend on skill type and student performance.

### Issue: Personalization is underused
- Student goals, mistakes, confidence, and performance do not drive enough of the experience.

---

## 16. Core Files / Contracts Missing

### Issue: Missing shared prompt modules
- `_shared/interaction_beats.md`
- `_shared/game_contract.md`
- `_shared/uzbek_style_qa.md`
- `_shared/register_protocol.md`
- `_shared/pisa_skill_map.md`
- `_shared/boss_blueprint.md`
- `_shared/panel_selector.md`
- `_shared/origin_archetypes.md`
- `_shared/active_flashcard_patterns.md`

### Issue: Missing data contracts
- `data/uzbek_scientific_glossary.json`
- canonical supported game matrix
- supported subject/grade matrix
- deprecated/frozen game list

---

## 17. Highest-Priority Issue Cluster

### Issue: Prompt contracts are not ready for advanced games
- Current game schemas must be fixed before adding more mechanics.

### Issue: Interactivity needs phase-level design, not only new games
- Every phase should require student action.

### Issue: Uzbek QA must be system-level
- Prompt wording alone cannot fix grammar quality.

### Issue: Runtime cleanup should happen before expansion
- Dead/duplicated AI paths increase drift.

### Issue: Subject gaps should be separated from prompt-flow redesign
- Missing subjects, video/audio, PPTX, and G1–4 are major product work, not small prompt edits.
