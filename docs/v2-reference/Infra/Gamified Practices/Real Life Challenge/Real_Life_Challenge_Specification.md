# Real-Life Challenge — Game Mechanic Specification

**Replaces:** Real-Life Challenge (11) — old "Phenomenon-Based Expert Scenario Edition"
**Type:** Game (position in flow determined by homework design, not by this spec)
**Audience:** Production team creating homework prompts and content.

---

## 1. What Real-Life Challenge Is

Real-Life Challenge is a first-person expert decision game. The student is not answering a question about a scenario — they ARE the expert inside the scenario. The fire safety inspector. The structural engineer. The lab technician. The historical advisor.

The game presents a real-world case, asks the student to predict, decide, and justify, then evaluates whether their reasoning would hold up if a real expert read it. The point is not "what's the right answer." The point is "did the student think like someone who could actually use this concept."

Real-Life Challenge stays a single standalone game. It does not merge with Boss or any other mechanic.

---

## 2. When Real-Life Challenge Fires

Real-Life Challenge is deployable wherever the homework flow places it. The spec does not pin it to a specific phase.

What Real-Life Challenge requires to function:

- The lesson concept must be applicable to a real-world decision context. Pure definition or naming chapters don't generate good Real-Life scenarios — those should use a different game.
- The student should have at least minimal exposure to the concept before encountering this game. Real-Life is decision-making, not first-time learning.

Real-Life can run once or multiple times in a session depending on flow design. Each run is one scenario.

---

## 3. The Student Experience (Flow)

The student enters Real-Life Challenge with a role assignment. The game then walks them through one scenario with multiple decision points.

Each scenario goes through this loop:

```
1. Role briefing screen — "You are a [role]. You've been asked to [task]."
2. Scenario presentation — context, constraints, stakeholders shown
3. Prediction checkpoint — "Before you decide, what do you expect will happen?"
4. Decision point — student picks an action from 3-4 options
5. Confidence rating — student rates how sure they are (Sure / Maybe / Guess)
6. Why prompt — student types 1-2 sentence justification
7. Expert feedback — system responds in-character as a senior expert
8. Next decision point (or scenario ends)
9. Final reasoning summary — student gets evaluated across all decisions
```

Scenarios are **linear**. The same student sees the same decision sequence regardless of earlier choices. Path variety comes from adaptation at the scenario-selection level (Section 5), not from branching within a scenario.

---

## 4. The Scenario Structure

Every Real-Life scenario must include these elements in order:

| Element | What it is | Required? |
|---|---|---|
| **Role** | The expert identity the student takes on. Named, specific. | Mandatory |
| **Task** | What the student has been called in to do. One sentence. | Mandatory |
| **Context** | The situation, constraints, available information. 2-4 sentences. | Mandatory |
| **Prediction prompt** | "Before you decide, what do you expect to find / happen?" | Mandatory |
| **Decision points** | 2-4 decisions across the scenario, each requiring concept application | Mandatory (count by grade band, Section 6) |
| **Why prompt** | At each decision: "Why is this the right call?" — 1-2 sentence justification | Mandatory |
| **Confidence rating** | Student taps Sure / Maybe / Guess before final decision | Mandatory |
| **Expert feedback** | In-character response after each decision | Mandatory |
| **Final summary** | What the student got right, what they missed, what an expert would have done differently | Mandatory |

### Example (Biology, Grade 8)

> **Role:** Siz mahalliy klinikada hamshira yordamchisisiz.
>
> **Task:** Bemorda nafas olish qiyinligi va lablari ko'kargan. Shifokorga xabar berishdan oldin asosiy sababini taxmin qilishingiz kerak.
>
> **Context:** Bemor 14 yoshda, kecha sportzalda mashq qilgan, hozir tinch o'tirgan. Yurak urishi tez. Tana harorati normal. Yo'tal yo'q.
>
> **Prediction:** Sizningcha bemorda nima bo'lgan? Taxmininingizni yozing.
>
> **Decision 1:** Hujayralarga yetarli kislorod yetib bormayotgan bo'lsa, asosiy sabab nimada bo'lishi mumkin?
> *(MC + Why text + Confidence)*
>
> **Decision 2:** Shifokorga xabar berishda qaysi ma'lumotni birinchi aytasiz?
> *(MC + Why text + Confidence)*
>
> **Final summary:** Strong reasoning if student connected cyanosis → low oxygen → cellular respiration concept from chapter. Missing if student only described symptoms without linking to lesson mechanism.

The student doesn't have to be right on every decision. Real-Life rewards good reasoning even when the final decision is imperfect.

---

## 5. Adaptation Logic

Real-Life Challenge adapts at the **scenario selection** level, not inside a scenario.

Before launching the game, the system checks upstream session telemetry:

- Which concepts has the student been shaky on this session?
- Which expert roles has the student already played recently?
- What PISA level fits the student's recent performance?

The system then selects a scenario from the pool that:

1. Tests one of the student's currently-shaky concepts (when possible)
2. Uses a role the student hasn't done recently (variety)
3. Matches the student's current PISA level, or one tier above if they've been succeeding

If no upstream telemetry exists, the system picks a scenario at the student's grade-band default PISA level.

There is no within-scenario branching. The path through one scenario is the same for all students.

---

## 6. Scenario Complexity by Grade Band

| Grade Band | Decisions | Concepts Required | PISA Target | Time Target |
|---|---|---|---|---|
| G1–3 | 1–2 | 1–2 | L2–3 | 3 minutes |
| G4–6 | 2–3 | 2–3 | L3–4 | 4 minutes |
| G7–9 | 3 (with red herring) | 3–4 | L4–5 | 5 minutes |
| G10–11 | 3–4 (with incomplete info) | 4+ | L5–6 | 5 minutes |

### Higher-grade variants

**Red herring (G7+):** One piece of information in the scenario is irrelevant. The student must identify it and explain why it didn't matter. Tests signal-vs-noise reasoning.

**Incomplete information (G10+):** The scenario doesn't include everything needed to decide. The student can request specific extra information (from a fixed list, each with a "cost" — time, access difficulty). Tests metacognition — knowing what you don't know.

**Creative Thinking variant (any grade, optional):** Instead of choosing from MC options, the student generates 3 different approaches to the scenario, evaluates strengths and weaknesses, and picks the best with justification. Tests divergent thinking followed by convergent evaluation. Uses different scoring (Section 7).

---

## 7. Scoring

Real-Life Challenge uses a 3-axis, 300-point scoring system.

| Criterion | Max XP | What It Measures |
|---|---|---|
| **Decision Quality** | 150 | Was the chosen action correct or optimal given the scenario constraints? Partial credit allowed. |
| **Reasoning Quality** | 100 | Is the justification logically sound? Does it reference the lesson concept? Does the Why text show actual thinking? |
| **Concept Identification** | 50 | Did the student correctly identify which lesson concepts apply to this scenario? |
| **Total** | **300** | |

### Confidence integration

Confidence ratings affect interpretation, not scoring directly:

| Pattern | Meaning |
|---|---|
| Sure + correct | Strong mastery signal |
| Sure + wrong | Misconception flag — student is confidently incorrect, needs targeted feedback |
| Maybe + correct | Moderate signal, may need reinforcement |
| Guess + correct | Lucky recall — not counted as mastery in downstream telemetry |
| Guess + wrong | Normal weak-concept signal |

Confidence data is exposed to downstream session components for adaptation and Reflection narrative.

### Scoring tiers

| Score Range | Rating | XP Awarded | Feedback Framing |
|---|---|---|---|
| 90-100% (270-300) | Expert Decision | Full XP + 50 bonus | "Siz haqiqiy mutaxassis darajasida fikrladingiz!" |
| 75-89% (225-269) | Strong Analysis | Full XP | "Yaxshi tahlil! Bir nechta jihatlarni hisobga oldingiz." |
| 60-74% (180-224) | Passing | 80% XP | "Asosiy g'oyani tushundingiz, lekin ba'zi detallarni o'tkazib yubordingiz." |
| Below 60% (<180) | Hali emas | 40% XP | "Hali emas — bu sizning mutaxassislik sayohatingizning bir qismi." Full expert walkthrough provided. |

### Creative Thinking variant scoring

When Creative Thinking variant is active:

| Criterion | Max XP | What It Measures |
|---|---|---|
| Solution Diversity | 75 | Are the 3 solutions genuinely different approaches? |
| Evaluation Quality | 100 | Does the student accurately assess strengths/weaknesses? |
| Justification Depth | 125 | Is the "why this is best" argument well-reasoned and conceptually grounded? |
| **Total** | **300** | |

---

## 8. Retry and Recovery

If the student scores below 60% on a Real-Life Challenge:

- The system provides a full expert walkthrough: what a real expert would notice, how they would reason, why.
- The scenario is flagged as "pending mastery."
- A different scenario testing the same concepts appears in a future session. The student does not see the same scenario twice — concept mastery is the goal, not memorization of answers.

The 60% session pass threshold from the interactivity standard applies here too.

---

## 9. Mistake Repair Signal

If the student got concept X wrong earlier in the session (in any game) and gets it right in a Real-Life decision involving concept X (without seeing the answer between the two attempts), that counts as a **mistake repair** event.

Real-Life Challenge feeds repair signal to downstream session components the same way Boss does. Production team should ensure scenarios test concepts that the student has likely encountered earlier in the session, so repair opportunities exist.

---

## 10. What the Production Team Outputs Per Scenario

Each Real-Life Challenge scenario in the homework JSON should include:

```
{
  "scenario_id": "rlc_bio_g8_001",
  "concept_tags": ["cellular_respiration", "oxygen_transport"],
  "role": "hamshira yordamchisi",
  "task": "Bemorda nafas olish qiyinligi sababini taxmin qilish",
  "grade_band": "G7-9",
  "pisa": "L4",
  "variant": "standard",
  "context": "Bemor 14 yoshda, kecha sportzalda mashq qilgan...",
  "prediction_prompt": "Sizningcha bemorda nima bo'lgan?",
  "decisions": [
    {
      "decision_id": "d1",
      "question": "Asosiy sabab nimada bo'lishi mumkin?",
      "options": ["...", "...", "...", "..."],
      "correct_option": 1,
      "why_required": true,
      "confidence_required": true,
      "expected_reasoning": ["low_oxygen", "cellular_respiration", "anaerobic"],
      "correct_feedback": "Mahalliy ekspert siz bilan rozi...",
      "partial_feedback": "Aniq sabab to'g'ri, lekin mexanizm haqida ko'proq fikrlash kerak.",
      "wrong_feedback": "Hali emas. Lablar nima uchun ko'karadi?"
    },
    {
      "decision_id": "d2",
      "question": "...",
      "options": [...],
      ...
    }
  ],
  "red_herring": null,
  "missing_info_pool": null,
  "final_summary_template": "..."
}
```

The pool size per concept depends on how often Real-Life can fire in a session. Minimum 5 scenarios per concept tag per grade band so adaptation has room to operate.

---

## 11. What NOT to Do

These are forbidden in Real-Life Challenge:

- **Decoration treated as learning evidence.** Color hooks, mood lighting, animated consequence webs, character portrait expressions changing — these are UI polish at most. They cannot be counted as interactivity or pedagogy.
- **Scenarios that work without the lesson concept.** If a student could answer correctly using general intuition rather than the chapter's concept, the scenario fails the Strip Test. Regenerate.
- **Generic role-play with no specific decisions.** "You are a scientist. What do you think?" is not a Real-Life Challenge. Roles must come with specific tasks and decisions.
- **Scenarios with one obvious right answer that requires no reasoning.** If the MC options are clearly correct/incorrect on surface, the Why prompt has nothing to evaluate.
- **Forced Uzbek context that fails the swap test.** If swapping "Chorsu Bazaar" for "the market" doesn't change the cognitive task, drop the local reference. (See Issue #27.)
- **Within-scenario branching.** Path variety comes from scenario selection (Section 5), not from divergent paths inside one scenario.
- **Fake misconception options.** MC distractors must be real wrong reasoning students actually use, not nonsense options.
- **Skipping the Prediction Checkpoint or Confidence Rating.** Both are mandatory per the interactivity standard.

---

## 12. Success Criteria

Real-Life Challenge is working correctly when:

- Every scenario has a Role, Task, Context, Prediction, at least one Decision with Why + Confidence, and Expert Feedback
- The student cannot complete a scenario without applying the lesson concept
- Confidence + correctness data is being read by downstream session components
- Mistake repair count from Real-Life is consumable by any session-level Reflection or Results component
- Scenarios test the same concept in different contexts across sessions (preventing memorization)
- The Strip Test passes — remove the lesson concept and the scenario stops working

If any of these fail, the scenario or adaptation logic needs review before that homework ships.
