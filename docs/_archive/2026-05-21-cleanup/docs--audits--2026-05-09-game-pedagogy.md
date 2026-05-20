# Game Proposals — Pedagogy Review — 2026-05-09

## Verdict matrix

| # | Title | Retention | Genuine | PISA | Cheat-resist | Boredom-risk-LOW | Pedagogy verdict |
|---|---|---|---|---|---|---|---|
| G1 | Sorting Hat | 4 | 4 | 3 | 4 | 4 | strong |
| G2 | Evidence Relay | 5 | 5 | 5 | 4 | 4 | strong — top-tier |
| G3 | Analogy Bridge | 4 | 3 | 5 | 3 | 4 | strong with caveat |
| G4 | Number Line Sprint | 3 | 3 | 4 | 4 | 5 | mixed — math-only |
| G5 | Caption It | 4 | 4 | 5 | 5 | 4 | strong |
| G6 | Flashcard Confidence Tap | 2 | 1 | 2 | 5 | 3 | weak — metacognitive only |
| G7 | Preview Curiosity Unlock | 2 | 1 | 2 | 5 | 3 | weak — warm-up theatre |
| G8 | Reflection Prompt Ladder | 3 | 2 | 3 | 5 | 3 | mixed — input quality, not learning |
| G9 | Memory-Sprint "Why Was I Wrong?" | 5 | 4 | 4 | 5 | 4 | strong — highest leverage |
| G10 | Boss XP Persistence | 2 | 2 | 2 | 3 | 3 | infrastructure — not a learning mechanic |
| G11 | Cycle Streak Counter | 1 | 1 | 1 | 5 | 2 | weak — ships wrong incentive |
| G12 | Mastery Heatmap Tile | 3 | 2 | 3 | 5 | 3 | mixed — visual only |
| G13 | "You've Grown" Phrase Echo | 3 | 2 | 3 | 5 | 2 | weak — effort praise, not learning |
| G14 | Topic Revisit Nudge | 4 | 3 | 4 | 5 | 3 | strong with caveat |

---

## Per-proposal pedagogy notes

### G1. Sorting Hat (Tartiblash)
- **What I love:** Classification is genuinely Bloom L3; no existing mechanic covers it; all-or-nothing server validation forces actual knowledge.
- **What's pedagogically weak:** 6–8 cards across 3 buckets caps cognitive load at shallow categorisation — student can eliminate by exclusion (put everything that doesn't fit bucket A into B/C) without understanding bucket B or C.
- **Concrete improvement:** Add one distractor card that belongs to NONE of the buckets; student must identify and leave it un-sorted. Forces positive identification, not just exclusion logic.

---

### G2. Evidence Relay (Dalil Zanjiri)
- **What I love:** Ranking-as-reasoning is a genuine epistemic skill. Partial-credit XP (30/60/100) rewards productive struggle rather than binary pass/fail.
- **What's pedagogically weak:** The `explain` field shown post-submit may short-circuit consolidation — student sees the correct reasoning before independently producing any. Explanation before self-explanation is a known retrieval inhibitor.
- **Concrete improvement:** Require student to type a one-sentence reason for their top-ranked choice BEFORE submitting the rank order; show the model explanation only after. Turns a recognition task into a generation task.

---

### G3. Analogy Bridge (O'xshashlik Ko'prigi)
- **What I love:** Directly targets PISA transfer; analogical reasoning is the most under-served skill in the existing slate.
- **What's pedagogically weak:** Four-option MC means ~25 % chance of correct answer by guessing alone; with 3 implausible distractors that number is closer to 50 %. Student who can't form the analogy mentally can still succeed by elimination.
- **Concrete improvement:** Drop to 3 options but require student to tap the answer AND complete a partial sentence: "X is like Y because ___" (short fill-in, even one word) before submission scores.

---

### G4. Number Line Sprint (Raqamlar Yo'li)
- **What I love:** Kinesthetic estimation is genuinely absent from the slate; ±15 % window is educationally sound (estimation, not precision).
- **What's pedagogically weak:** Estimation with immediate correct-position reveal teaches correct values but not the reasoning behind them. Student learns "troposfera is ~12 km" as a fact, not as a derived magnitude. Also, a 20-second timer with no penalty creates urgency without depth — panic-dragging is still engagement-adjacent behaviour.
- **Concrete improvement:** After the correct position reveals, require one tap on a "Why this range?" pill that shows a one-sentence derivation (e.g., "highest weather systems reach ~12 km") — 5-second mandatory display before advance. Turns recall into understanding.

---

### G5. Caption It (Sarlavha Ber)
- **What I love:** First image-to-language production mechanic in the system; AI grader on free text means no gaming by elimination; directly serves PISA "integrating and interpreting" at Level 3-4.
- **What's pedagogically weak:** Model caption shown post-grade may be more memorable than the student's own production (worked example effect); if the model caption is verbose and technically precise, low-performing students may disengage rather than compare.
- **Concrete improvement:** Show model caption in redacted form (blanks for the two most important technical terms) and require student to fill those blanks from memory before viewing the full caption.

---

### G6. Flashcard Confidence Tap (Ishonch Tugmasi)
- **What I love:** Metacognitive awareness has evidence-backed correlation with learning outcomes; near-zero cost.
- **What's pedagogically weak:** Self-assessment on flashcards has a well-documented accuracy problem: students who least understand material are most confident (Dunning-Kruger). "Bildim" taps from low-knowledge students produce misleading signals and no corrective loop. The proposal's own self-criticism correctly identifies this — it calls the signal unreliable — but then ships it anyway.
- **Concrete improvement:** After "Bilmadim" tap, auto-queue that card to re-appear at the END of the flashcard stack (lightweight spaced repetition). This converts a passive self-label into an active retrieval action.

---

### G7. Preview Curiosity Unlock (Qiziqarli Savol)
- **What I love:** Reuses existing `memory_sprint[0]` data — almost zero implementation cost.
- **What's pedagogically weak:** The proposal's own defence is "even guessing requires reading the question, which is the goal" — but a student who guesses incorrectly and sees the answer then advances immediately. There is no consolidation moment; incorrect guessing teaches nothing. This is engagement theatre dressed as a learning mechanic.
- **Concrete improvement:** On a wrong guess, instead of just revealing the answer, display the sentence from the preview panel that contains the answer (highlight it) and add a 3-second mandatory display. Anchors the correction to the source text.

---

### G8. Reflection Prompt Ladder (Takrorlash Eslatmasi)
- **What I love:** Structured reflection prompts reliably produce richer AI coaching input; rungs 2–3 force students to name difficulty explicitly (which is itself metacognitive).
- **What's pedagogically weak:** The 3-rung structure feeds richer text to the AI coach but does NOT guarantee the student reflects genuinely — "qiyin bo'lgan narsa: hech narsa" is a valid submission. The improvement in AI output quality is real; the improvement in student learning is uncertain. This is pipeline quality, not learning quality.
- **Concrete improvement:** Rung 2 ("hardest thing") should be pre-populated with the student's worst-scoring phase from `__sessionLog` (e.g., "Memory Sprint: 2/5 correct") so the student must respond to a concrete data point, not an open blank.

---

### G9. Memory-Sprint "Why Was I Wrong?" Tap
- **What I love:** Surfaces already-present `explain` data; wrong-answer correction with elaboration is the single most evidence-backed intervention in the cognitive science literature (corrective feedback + explanation > corrective feedback alone). Highest learning return per LOC in the entire slate.
- **What's pedagogically weak:** Expand is cosmetic — student can tap the pill, scan it for 0.5 seconds, and advance. No active processing required.
- **Concrete improvement:** Replace the pill-expand with a "type one word from the explanation" micro-input before the correct answer text is revealed in full. Forces encoding, not just exposure.

---

### G10. Boss XP Persistence
- **What I love:** Correctly noted as infrastructure; boss defeat is the highest-quality learning gate in the system (HP + hints + attempt count).
- **What's pedagogically weak:** Persisting a number does not produce learning. XP is an extrinsic reward; if the boss is already the intrinsically motivating mechanic, adding a persisted score may actually undermine intrinsic motivation (overjustification effect). The engagement audit advocates for this strongly but it is not a learning mechanic — it is a retention-via-motivation mechanic. Different.
- **Concrete improvement:** If shipping, do NOT show cumulative XP anywhere outside the results screen. Visible wallet during play = farming incentive; results-only = celebration signal.

---

### G11. Cycle Streak Counter (Davomiylik)
- **What I love:** Nothing. This is the weakest proposal on learning grounds.
- **What's pedagogically weak:** Counting consecutive boss defeats rewards consistency of attendance, not depth of understanding. A student can defeat a Beginner boss (low difficulty) on 5 consecutive sessions and accumulate a streak-5 without improvement. Streak mechanics are well-documented engagement drivers — and equally well-documented learning mis-aligners. PISA rewards transfer and application; streak counters reward repetition.
- **Concrete improvement:** Replace streak with a "difficulty progression" indicator: show the highest boss tier (Novice/Apprentice/Expert/Mythical) achieved on this homework across sessions. Rewards actual mastery growth, not attendance.

---

### G12. Mastery Heatmap Tile (Bilim Xaritasi)
- **What I love:** Visual longitudinal progress signal is genuinely motivating and is not common in EdTech in Uzbekistan.
- **What's pedagogically weak:** Green/amber/grey based on boss defeat is a completion signal, not a mastery signal. A student who defeats a Beginner-tier boss gets the same green as one who defeats a Mythical boss. The heatmap is a streak counter with visual polish.
- **Concrete improvement:** Colour the squares by boss tier achieved (e.g., grey = incomplete, blue = Novice, amber = Apprentice, green = Expert, gold = Mythical). Now the visual strip encodes actual mastery depth, not just completion.

---

### G13. "You've Grown" Phrase Echo
- **What I love:** Effort-based praise is better than ability-based praise (Dweck); single conditional sentence is appropriately minimal.
- **What's pedagogically weak:** Comparing `boss_xp_earned` across sessions is noisy — boss difficulty tier varies, meaning more XP this session may reflect an easier boss, not better performance. "You've grown" based on XP-delta may be factually false and teaches students that XP = progress (it doesn't).
- **Concrete improvement:** Gate the message on boss TIER improvement (defeated a harder tier than last time) rather than raw XP delta. This way "you've grown" is semantically accurate.

---

### G14. Topic Revisit Nudge (Takrorlash Eslatmasi)
- **What I love:** Spaced repetition is the single most replicated finding in learning science; surfacing it even as a nudge is more than any current mechanic does.
- **What's pedagogically weak:** The nudge is not spaced — it fires on the SAME session results screen if score < 60 %. True spaced repetition requires a TIME delay (return in 24 h, 48 h, 1 week). Without the time delay, "revisit" just means "replay immediately" — which is massed practice, not spaced retrieval, and is substantially less effective.
- **Concrete improvement:** Store the nudge target and surface it on the NEXT homework's results screen (cross-session, same subject), not the current one. "Last session on this topic: 58 % — revisit before your next test." That is actual spaced retrieval scheduling.

---

## Cross-cutting pedagogy patterns I see in the slate

- **Engagement and learning are conflated in 8 of 14 proposals.** Interactivity (dragging, tapping, timing) is used as a proxy for learning. A drag action that requires no reasoning (G4 number line, G6 confidence tap, G3 MC tap) is kinesthetic novelty, not retrieval practice.
- **Extrinsic reward inflation risk.** G10/G11/G12/G13 form a cluster that layers XP → streak → heatmap → praise on top of the boss mechanic. Each individually is defensible; together they shift the motivational frame from "I want to understand this" to "I want to see my numbers go up." Overjustification effect is additive across signals.
- **Missing production gap.** Only G2 (ranking with rationale), G5 (captioning), and G9 (wrong-answer explanation) require the student to PRODUCE something. All other proposals are recognition or selection tasks. PISA consistently penalises curricula heavy on recognition and light on production.
- **Post-answer explanation timing is wrong in 4 proposals.** G2, G3, G4, G7 all reveal the correct answer or explanation immediately after submission, before the student has attempted any self-explanation. This is the most consistent failure mode in the slate — it shortcuts the generation effect.

---

## My pedagogy ranking (top 5 — by genuine learning value)

1. **G9 — Memory-Sprint "Why Was I Wrong?" Tap** — corrective feedback with elaboration is the highest-evidence single intervention; zero infrastructure cost; surfaces data that already exists.
2. **G2 — Evidence Relay** — only mechanic in the slate that explicitly trains scientific reasoning (evidence hierarchy); ranking under uncertainty is a genuine epistemic skill; partial credit rewards productive struggle.
3. **G5 — Caption It** — only production mechanic in the game-break slot; image-to-language is PISA Level 3-4; AI grader eliminates pattern-matching.
4. **G1 — Sorting Hat** — classification (Bloom L3) is the one genuine cognitive gap in the game-break inventory; all-at-once server validation prevents elimination cheating.
5. **G14 — Topic Revisit Nudge** — the only proposal that touches spaced retrieval, the most replicated finding in learning science; even a weak implementation has directional value.

---

## My pedagogy bottom 3 (would NOT ship even if cheap)

1. **G11 — Cycle Streak Counter** — rewards attendance, not learning; a student who repeatedly completes Beginner-difficulty sessions earns a streak while making zero progress; directly mis-aligned with PISA mastery goals.
2. **G7 — Preview Curiosity Unlock** — a wrong guess followed by immediate answer reveal with no consolidation teaches nothing; the mechanic's own author concedes it is a "warm-up, not a gate" — that framing is engagement design, not learning design.
3. **G6 — Flashcard Confidence Tap** — self-assessment accuracy is lowest precisely among students who most need corrective feedback; ships a tool that will systematically mislead the highest-risk learners; the proposal's self-criticism is correct and was not acted on.

---

## A pedagogically-stronger alternative (for G7 — Preview Curiosity Unlock)

The engagement goal is correct: make the last preview panel active instead of passive.

- **Counter-design — "Predict Before You Know":** Instead of a MC question drawn from `memory_sprint[0]` (something already covered in the preview), show a one-sentence scenario that the student has NOT yet seen and ask them to predict the answer. No correct/incorrect feedback is given — the prediction is stored to `sessionStorage`. At the END of the homework cycle, on the results screen, the original prediction is displayed alongside what the student now knows. This is a "generation before instruction" technique (Kapur's productive failure model): the failed prediction primes the student for the content, and the end-of-cycle echo creates a memorable "I was wrong, now I know why" moment. Zero new schema needed (prediction stored client-side only for v1); same XS effort; substantially higher learning impact than a guessable warm-up MC.
