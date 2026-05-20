You are generating the Flow v2 Memory Check for Biology.

Input source: the flashcards generated for this same homework. Do not introduce facts the student has not seen in the lesson anchors.

Output JSON shape:
{
  "memory_check": {
    "pass_threshold_pct": 60,
    "modes_enabled": ["mcq", "fill_blank", "choose_explanation"],
    "items": []
  }
}

Create 5-8 items. Use at least two modes, and prefer all three when the flashcard set supports them:
- "mcq": recognition of a term, function, stage, or classification.
- "fill_blank": one concept-bearing biology term in a sentence. Never blank a function word.
- "choose_explanation": choose the explanation that correctly links structure to function, process to outcome, or evidence to conclusion.

Each item must include: type, prompt, options when needed, answer_spec, flashcard_ref, and a short explanation. answer_spec should use expected, accepted_answers, or option_index so deterministic grading can work before AI fallback.

Distractors must be plausible biology misconceptions, not jokes. Do not use Match Mode, Write/Spell Mode, spaced review queues, or diagram cards in v1.
