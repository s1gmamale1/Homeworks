You are generating the Flow v2 Memory Check for Chemistry.

Input source: the flashcards generated for this same homework. Test symbols, formulas, observable properties, classifications, reaction ideas, and safety anchors before practice opens.

Output JSON shape:
{
  "memory_check": {
    "pass_threshold_pct": 60,
    "modes_enabled": ["mcq", "fill_blank", "choose_explanation"],
    "items": []
  }
}

Create 5-8 items. Use at least two modes:
- "mcq": recognize the correct formula, class, property, or reaction meaning.
- "fill_blank": blank one concept-bearing chemical term, symbol, formula, or category.
- "choose_explanation": choose why a property, formula, or classification is correct.

Each item must include: type, prompt, options when needed, answer_spec, flashcard_ref, and a short explanation. Use answer_spec.option_index for options and accepted_answers for formulas with valid spacing/case variants.

Distractors must be chemically plausible near-misses. Do not use Match Mode, Write/Spell Mode, spaced review queues, or diagram cards in v1.
