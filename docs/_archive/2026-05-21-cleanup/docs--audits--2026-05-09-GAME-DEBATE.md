# Game + Gamification Proposals — Synthesis — 2026-05-09

3-agent swarm: Inventor (Sonnet) → Pedagogy Critic (Sonnet) + Feasibility Realist (Opus). 15 proposals debated. **No code changed.**

Sub-docs: [Inventor's slate](2026-05-09-game-proposals.md) · [Pedagogy review](2026-05-09-game-pedagogy.md) · [Feasibility review](2026-05-09-game-feasibility.md)

---

## TL;DR

- **15 proposals** → **6 ship · 3 ship modified · 3 deferred · 3 rejected**
- **Highest leverage:** **G9** (Why Was I Wrong tap, XS) is the single cheapest highest-pedagogy win in the slate — corrective feedback is the most-evidenced cognitive-science intervention; data already exists in `explain` field; pure runtime fix
- **Critical cross-cutting risk:** **overjustification effect.** Cat 3+4 reward stack (G10–G13 shipped together) shifts student motivation from "I want to understand" to "I want my numbers to go up." Ship at most ONE of G10/G11/G12/G13 in v1.
- **Pedagogy critic disagreed sharpest with:** G6 (Flashcard Confidence Tap) — Dunning-Kruger problem: lowest-knowledge students self-assess worst. Ship-as-is acceptable IF paired with G9 corrective-feedback so the cycle doesn't only have an unreliable signal
- **Feasibility critic caught:** G7 (Preview Curiosity) is S not XS; G2 drag-rank is M-high not M; G14 reads a `phase_scores` column that **has zero writes anywhere in the codebase**

---

## Verdict matrix

| # | Title | Cat | A est. | Real cost | Pedagogy | Verdict |
|---|---|---|---|---|---|---|
| **G9** | Why Was I Wrong tap | 2 | XS | XS ✓ | **5/5 top** | ✅ **SHIP** — highest impact-per-effort in slate |
| **G10** | Boss XP Persistence | 3 | S | S ✓ | infra | ✅ **SHIP** — ONLY if any persistence ships |
| **G8** | Reflection Prompt Ladder | 2 | XS | XS ✓ | strong | ✅ **SHIP** |
| **G6** | Flashcard Confidence Tap | 2 | XS | XS ✓ | flagged | ✅ **SHIP** w/ G9 paired |
| **G5** | Caption It | 1 | M | M ✓ | **5/5 top** | ✅ **SHIP** — only production mechanic, PISA L3-4 |
| **G4** | Number Line Sprint | 1 | S | S ✓ | mid | ✅ **SHIP** — math/phys/kimyo only |
| **G2** | Evidence Relay | 1 | M | M-high (off) | **5/5 top** | 🛠️ **MODIFY** — drop drag-rank, use 3-tap pick-best |
| **G3** | Analogy Bridge | 1 | S | S ✓ | 3/5 mid | 🛠️ **MODIFY** — gate on builder-author content quality |
| **G13** | "You've Grown" echo | 4 | XS | XS ✓ | overjust risk | 🛠️ **MODIFY** — ship as ONLY Cat 4, drop streak/heatmap |
| **G1** | Sorting Hat | 1 | M | M ✓ | mid | ⏳ **DEFER** — overlaps Tile Match; ship after cheaper wins |
| **G12** | Mastery Heatmap | 4 | S (post-G10) | S ✓ | overjust risk | ⏳ **DEFER** — adds to reward stack |
| **G14** | Topic Revisit Nudge | 4 | XS | S (off) | mid | ⏳ **DEFER** — `phase_scores` column has 0 writes; not free |
| **G11** | Cycle Streak | 3 | XS (post-G10) | XS ✓ | **bottom-3** | 🚫 **REJECT** — rewards attendance not mastery |
| **G7** | Preview Curiosity | 2 | XS | S (off) | **bottom-3** | 🚫 **REJECT** — wrong-guess+answer+advance ≠ learning; bypasses tutor redaction |

---

## Cross-cutting risks (must read before sequencing)

### 1. Overjustification effect (B's strongest cross-cutting catch)

Cat 3 + Cat 4 (G10/G11/G12/G13) shipped TOGETHER create a layered reward stack:
- XP persists → Streak counts → Heatmap shows history → "You've grown" phrase → student optimizes for the numbers, not the learning.

Each individually is defensible. Stacked, they crowd out the intrinsic motivation already present in the boss mechanic.

**Recommendation: ship at most ONE of G10/G11/G12/G13 in v1.** G10 is the right pick because it's pure infrastructure — it ENABLES the others without activating the full reward stack yet. Decide which (if any) of G11/G12/G13 to add only after measuring G10's actual effect on completion + boss-replay rates.

### 2. Schema vs runtime-contract distinction (C's finding)

Frozen-schema invariant covers `content_json` only. Several proposals don't add `content_json` keys but DO extend other contracts:
- **G10** — adds `sessions.boss_xp_earned` column (DB schema change, but OUTSIDE content_json — allowed)
- **G7** — would inject memory_sprint content into preview-phase tutor context, **bypassing `_redact_question_for_tutor`** (the answer-leak invariant). Reject as proposed.
- **G3/G6/G8** all touch the runtime payload contract subtly — must include regression tests per CONTRIBUTING rule

### 3. The "free reads existing X" trap (C's catch on G14)

A claimed G14 reads existing `phase_scores`. Truth: that column has **zero writes anywhere in `server/`**. Reading it returns null. So G14's "XS — reads existing data" is wrong; real cost is S+ because `phase_scores` writes need to be wired first (a separate non-trivial task).

---

## Detailed verdicts

### ✅ G9 — Memory-Sprint "Why Was I Wrong?" Tap (TOP PICK)

- **What:** wrong-answer pill expands `explain` field inline. ~25 LOC total. Zero schema, zero backend.
- **B's pedagogy:** **5/5 genuine learning.** Corrective feedback + elaboration is the highest-evidence single intervention in cognitive science.
- **C's feasibility:** XS verified — `explain` already in MS_QUESTIONS injection.
- **Why ship first:** lowest cost in slate, highest pedagogy score, zero risk.

### ✅ G10 — Boss XP Persistence

- **What:** `sessions.boss_xp_earned` column + persist `outcome_xp` at boss defeat + display once on results screen. ~40 LOC.
- **C's feasibility:** S verified — `outcome_xp` computed at `ai.py:1672` and discarded today. Pure gap-fill.
- **B's pedagogy:** infrastructure, no direct pedagogy score. WARNING: enables Cat 4 reward stack.
- **Verdict:** ship as the ONE persistence move. **Don't ship G11/G12 unless measurement justifies later.** G13 OK as a single soft echo if any Cat 4 ships.

### ✅ G8 — Reflection Prompt Ladder

- **What:** 3-rung scaffold (BOST goal echo + "hardest thing today" + "I'll try next time") replaces blank textarea. ~35 LOC. Zero backend.
- **Verdict:** ships in same PR as FLOW-DEBATE P3 (BOST goal capture); one extends the other naturally.

### ✅ G6 — Flashcard Confidence Tap (PAIRED WITH G9)

- **B's flag:** "self-assessment accuracy is lowest among lowest-knowledge students" — Dunning-Kruger. Ships a tool that systematically misleads the students most needing corrective feedback.
- **My response:** B's concern is real but informational-only signal (no XP, no grade, no public surface) limits damage. **Mitigation: G6 SHIPS PAIRED with G9** — corrective feedback (G9) catches the wrong self-grades flashcards (G6) misses. Ship them in the same PR so the cycle has BOTH self-signal AND truth-signal.
- FLOW-DEBATE already approved P5 as SHIP — keeping that decision but tightening the pairing.

### ✅ G5 — Caption It (only production mechanic)

- **What:** student writes a caption for a flashcard image; AI grader returns 1-3 stars + model caption.
- **B's pedagogy:** **5/5 genuine learning** — only image-to-language production mechanic; PISA Level 3-4 reading literacy.
- **C's feasibility:** M verified — uses existing AI grader pattern, new content_json key + route + panel.
- **Verdict:** ship in second sprint after G9/G6/G8/G10 ship.

### ✅ G4 — Number Line Sprint

- **What:** drag-marker estimation game on a number line, 20s clock as engagement scaffold. Subject-gated math/phys/kimyo only.
- **A's mitigation:** use `<input type="range">` slider instead of raw SVG drag — solves mobile finickiness.
- **Verdict:** SHIP — kinesthetic + PISA math L2 estimation skill; no current mechanic does this.

### 🛠️ G2 — Evidence Relay (MODIFY)

- **A's design:** drag-rank 3 cards 1→3.
- **C's catch:** drag-rank UI on mobile is M-high not M. Replace with **3-tap pick-best**: student taps the SINGLE most convincing card (not full ordering). Still trains evidence judgment. Ranking can come back v2.
- **B's pedagogy:** **5/5 — only mechanic explicitly training scientific reasoning.** Worth shipping with the simplification.
- **Verdict:** SHIP MODIFIED.

### 🛠️ G3 — Analogy Bridge (MODIFY)

- **B's flag:** Genuine Learning = 3/5. MC analogy is recognition, not transfer-generation. Score moves to 4 ONLY IF builder author writes genuinely novel analogy pairs where elimination is hard.
- **Verdict:** SHIP MODIFIED — gate the implementation on a **content-quality checklist** for builders (every analogy pair must include 4 plausible distractors, not 1 right + 3 obvious wrong). Without that, G3 ships as engagement theatre.

### 🛠️ G13 — "You've Grown" echo (MODIFY — ship as ONLY Cat 4)

- **What:** if current boss XP ≥ previous +10%, show one personalized line: "O'tgan safarga nisbatan yaxshilandingiz!"
- **Why this over G11/G12:** compares ONLY to self, no number, no streak counter, no visible historical trail. Lowest overjustification risk in Cat 4.
- **Verdict:** SHIP MODIFIED — ONLY if you want any Cat 4 surface. Don't pair with streak (G11) or heatmap (G12).

### ⏳ G1 — Sorting Hat (DEFER)

- Overlap with Tile Match (1:1 pairing) is real even if classification ≠ association at cognitive level. M effort. Ship after G2/G4/G5 land.

### ⏳ G12 — Mastery Heatmap (DEFER)

- Compelling visual. Compounds reward stack. Hold until G10 has shipped + been observed for 2-4 weeks.

### ⏳ G14 — Topic Revisit Nudge (DEFER)

- C caught the trap: depends on `phase_scores` writes that don't exist. Ship `phase_scores` writing as a prerequisite first (separate S task), THEN G14 becomes XS as A claimed.

### 🚫 G11 — Cycle Streak (REJECT)

- B's bottom-3 verdict: "Beginner-tier daily player earns streak-7 without improvement." Rewards attendance, not mastery. Directly anti-PISA.
- **Verdict:** DON'T SHIP. If any cross-session signal ships, use G13 (compares to self) not G11 (compares to attendance).

### 🚫 G7 — Preview Curiosity Unlock (REJECT)

- B's bottom-3: wrong guess + immediate answer + advance = no consolidation. The proposal calls itself a "warm-up not learning" — that's accurate.
- C's escalation: A says XS, real is S because it couples to preview state machine AND would inject memory_sprint content into preview-phase tutor context, **bypassing `_redact_question_for_tutor`** — answer-leak risk.
- **Verdict:** REJECT. Triple-negative (pedagogy weak + cost wrong + contract risk).

---

## Final ship plan — 4 PRs in order

### PR-A — "Cycle signal" (XS+XS = ~1 day)
- ✅ **G9** Why-Was-I-Wrong tap
- ✅ **G6** Flashcard Confidence Tap (paired with G9 for Dunning-Kruger mitigation)
- + 2 regression tests

### PR-B — "Reflection bookend" (XS+XS, builds on FLOW-DEBATE P3 = ~1.5 days)
- ✅ **G8** Reflection Prompt Ladder (extends FLOW-DEBATE P3's BOST input)
- + regression test

### PR-C — "Boss XP foundation + soft growth signal" (S+XS = ~1.5-2 days)
- ✅ **G10** Boss XP Persistence (DB column + write + display)
- ✅ **G13 modified** "You've Grown" echo (compares to SELF only)
- + 3 tests including the streak/heatmap regression-locked-out (no G11/G12 in v1)

### PR-D — "New game-break mechanics" (S+S+M = ~3-4 days)
- ✅ **G4** Number Line Sprint
- 🛠️ **G2 modified** Evidence Relay (3-tap pick-best, no drag-rank)
- ✅ **G5** Caption It (image production)
- + content-quality checklist for **G3 modified** Analogy Bridge (decide ship/skip after writing 5 sample analogy pairs)

**Total: ~7-8 dev-days across 4 PRs, fully sequenced.**

**Deferred for measurement / prerequisite work:** G1 (Sorting Hat), G12 (Heatmap), G14 (Revisit Nudge — needs phase_scores wired first)

**Killed:** G7 (Preview Curiosity), G11 (Streak)

---

## 3 open questions for you

1. **Which Cat 4 (if any)?** My recommendation is G13 alone (compares to self). If you want NO cross-session signal in v1 — also valid; ship just G10 as silent infrastructure and revisit in 4 weeks.
2. **G3 Analogy Bridge — ship or skip?** Depends on whether you (or a builder author) will hand-write the analogy pairs to the quality bar. If LLM-generated at runtime, B says skip — recognition theatre. If hand-curated, ship.
3. **Sequence the 4 PRs strictly, or parallelize PR-A and PR-B?** They touch different runtime sections (memory-sprint + flashcards vs. reflection screen) and could go in parallel. Saves a day. Risk: small if both PRs include their own regression tests.
