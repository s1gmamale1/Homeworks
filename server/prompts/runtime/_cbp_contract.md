# Case-Based Preview — Shared Generation Contract

**Status:** Source-of-truth for any per-subject `case-based-preview.md` prompt.
**Companion files:** Per-subject prompts at `server/prompts/<subject>/case-based-preview.md` reference this file by name. Do not duplicate these rules in subject prompts — extend with subject-specific case patterns only.

This file owns:
- The 18-item validation checklist (CBP Generation Standard §14)
- The Uzbek language register contract
- Flow v2 forbid rules #3–#6 + #19 + #20 as they apply to CBP
- The canonical Markdown output schema

---

## 1. Identity

A Case-Based Preview is a short guided learning case that turns a textbook section into a student-facing decision situation. The student is the **decision-maker**, not the reader. They face exactly **three sequenced checkpoints** (Identify → Decide → Justify), then see a consequence simulation, then receive an AI feedback summary.

**Stakes:** low-to-medium. CBP is meaning-building, not final mastery. The Practice Arc (Real-Life Challenge, games, Boss Arena) is where mastery is tested.

---

## 2. Forbid rules (Flow v2 — applied to CBP)

These are non-negotiable. Generators that violate any of them must regenerate.

- **#3** — Forbid Case Study that loses the original textbook concept.
- **#4** — Forbid Case Study without checkpoint-based learning.
- **#5** — Forbid Case Study where the student is not the decision-maker / solver.
- **#6** — Forbid checkpoint decisions with no consequence.
- **#19** — Forbid exact-question retake farming. Regenerated retake variants must change ≥1 of {numbers, character names, scene} while preserving `core_concept`, `checkpoint.kind`, and `common_mistake`.
- **#20** — Forbid "Not Completed" as the only label after a real attempt. Use "Passed" / "Needs Retry" (Uz: "Topshirildi" / "Qayta urinish kerak").

Plus:
- Forbid invented textbook claims, facts, formulas, definitions, or dates (Standard §2.1).
- Forbid case stories where the math/science/language concept could be stripped and the story still works ("dragon trap"). The concept must be load-bearing.
- Forbid copying textbook artwork directly. Convert diagrams into fresh NETS visuals.

---

## 3. Uzbek language register

CBP is Uzbek-first (with English/Russian translations downstream).

- **System voice** (narration, instructions to the student, AI feedback) — always formal **Siz**.
- **In-case character dialogue** — role-natural. A student speaking to a young customer inside the case may use `sen` if the scene genuinely calls for it. A student addressing an adult or stranger uses `Siz`.
- Avoid `sen`/`san` in system voice. Avoid Russian/English calques. Avoid childish tone.
- Preserve subject accuracy first; simplification never changes formulas, numbers, units, calculation order, or source meaning.
- Mark output `language_status: "draft"` if Uzbek hasn't passed native linguist review.

---

## 4. Required structure (CBP Standard §5)

Output MUST contain, in order:

1. **Case setup** — `{story, role, task}`. The story sets a real-life scene. The role places the student. The task names what the student must decide or solve.
2. **Checkpoint 1: Identify** — recognition. "Which concept / rule / operation / evidence applies here?"
3. **Learning Block 1** — short explanation tied to Checkpoint 1's outcome. MUST include `consequence_preview` ("Agar boshqacha tanlasangiz, [X] bo'lardi") so per-checkpoint Forbid #6 holds.
4. **Checkpoint 2: Decide** — application. "Which method / formula / next step is correct?"
5. **Learning Block 2** — same shape as LB1.
6. **Checkpoint 3: Justify** — explanation. "Why is the correct choice correct, OR why does the common mistake fail?"
7. **Final simulation** — `{correct_path, wrong_path, visual_description}`. Text-only `visual_description` for v1; sanitized SVG is deferred.
8. **AI feedback summary** — `{student_understood, mistake_appeared, what_to_review}`.

Gate: ≥2 of 3 checkpoints correct → section passes.

On fail (CBP forbid #19): regenerate the failed checkpoint with a variant — same `core_concept`, same `kind`, same `common_mistake`; different scene OR different numbers (at minimum one).

---

## 5. 18-item validation checklist (Standard §14)

Before returning the generated CBP, the generator MUST be able to answer "yes" to every item below. If any answer is "no", regenerate.

1. ✅ Source topic is identified (in `source_extraction.core_concept`).
2. ✅ Required student skill is identified (in `metadata.required_skill`).
3. ✅ Case type matches subject (math = practical-problem, science = phenomenon/lab/observation, language = communication, history = decision/source).
4. ✅ Case is source-aligned — concept preserved.
5. ✅ Student is decision-maker / solver (verified by `case_setup.student_role` non-empty + each checkpoint question uses a 2nd-person Siz decision verb).
6. ✅ Exactly 3 checkpoints exist.
7. ✅ Checkpoint 1 identifies a concept.
8. ✅ Checkpoint 2 chooses a method / action.
9. ✅ Checkpoint 3 justifies or catches a mistake.
10. ✅ Final consequence / simulation exists.
11. ✅ Correct path AND common wrong path are both shown.
12. ✅ Visuals support learning, not decoration.
13. ✅ Image is used only for scene / context (not for formulas).
14. ✅ SVG would be used for math / model / state visuals (deferred to PR #6 — v1 emits text descriptions).
15. ✅ Uzbek is formal Siz in the system voice and clear.
16. ✅ Formulas / numbers / units / source meaning preserved.
17. ✅ No passive reading blob.
18. ✅ Completion / pass condition exists; retry state exists.

If any item fails, regenerate.

---

## 6. Output JSON schema (for the Pydantic envelope)

```json
{
  "title": "<case title>",
  "metadata": {
    "subject": "<subject>",
    "grade": <number>,
    "topic": "<lesson topic>",
    "source_concept": "<one-sentence concept>",
    "required_skill": "<the action the student must perform>",
    "case_type": "<from Standard §9>",
    "key_terms": ["<canonical lesson terms>"]
  },
  "source_extraction": {
    "core_concept": "<from textbook>",
    "main_rule": "<formula or process>",
    "key_terms": ["<must match flashcards if provided>"],
    "common_mistake": "<one common error students make>",
    "textbook_example": "<verbatim textbook excerpt where possible>",
    "source_alignment_note": "<how the case preserves the textbook concept>"
  },
  "case_setup": {
    "story": "<2-4 sentence real-life scene>",
    "role": "<the student's role>",
    "task": "<one-sentence task statement>"
  },
  "checkpoints": [
    {
      "kind": "identify",
      "question": "<MCQ or recognition prompt>",
      "options": ["<A>", "<B>", "<C>", "<D>"],
      "answer_spec": {"type": "option_index", "option_index": <0-3>},
      "learning_block_after": {
        "body": "<2-3 sentence explanation>",
        "consequence_preview": "Agar boshqacha tanlasangiz, [X] bo'lardi"
      }
    },
    { "kind": "decide", "...": "..." },
    { "kind": "justify", "...": "..." }
  ],
  "final_simulation": {
    "correct_path": "<what happens if all decisions are right>",
    "wrong_path": "<what happens if the common mistake is made>",
    "visual_description": "<text describing the visual; SVG deferred to PR #6>"
  },
  "feedback_summary": {
    "student_understood": "<concept>",
    "mistake_appeared": "<key fail point or null>",
    "what_to_review": "<flashcard ref or section pointer>"
  },
  "completion_rules": {
    "pass_condition": "ge_2_of_3",
    "retry_condition": "regenerated_variant_per_failed_checkpoint"
  }
}
```

---

## 7. Final rule (Standard §16)

A CBP is valid only if the student can say:

- I know what situation I was in.
- I know what decision I made.
- I know which textbook concept helped me.
- I saw what happened because of my choice.
- I understand the main mistake to avoid.

If any of these five claims aren't supported by the generated output, regenerate.
