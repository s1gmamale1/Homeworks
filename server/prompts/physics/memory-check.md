You are generating the Flow v2 Memory Check for Physics.

Input source: the flashcards generated for this same homework. Test quantities, units, formulas, law meanings, cause-effect reasoning, and model assumptions before practice opens.

Output JSON shape:
{
  "memory_check": {
    "pass_threshold_pct": 60,
    "modes_enabled": ["mcq", "fill_blank", "choose_explanation"],
    "items": []
  }
}

Create 5-8 items. Use at least two modes:
- "mcq": recognize the correct quantity, formula, unit, or law.
- "fill_blank": blank one concept-bearing term, unit, variable, or formula part.
- "choose_explanation": choose why a law, relationship, or prediction is correct.

Each item must include: type, prompt, options when needed, answer_spec, flashcard_ref, and a short explanation. Use accepted_answers for valid unit/formula formatting variants.

Distractors must be physics near-misses, such as confusing mass/weight, speed/velocity, force/energy, or proportional/inverse relationships. Do not use Match Mode, Write/Spell Mode, spaced review queues, or diagram cards in v1.
