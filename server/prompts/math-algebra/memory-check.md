You are generating the Flow v2 Memory Check for Algebra.

Input source: the flashcards generated for this same homework. Test formulas, definitions, sign rules, method choices, and quick recognition anchors before practice opens.

Output JSON shape:
{
  "memory_check": {
    "pass_threshold_pct": 60,
    "modes_enabled": ["mcq", "fill_blank", "choose_explanation"],
    "items": []
  }
}

Create 5-8 items. Use at least two modes:
- "mcq": recognize the correct formula, definition, or method choice.
- "fill_blank": blank one term, number, operator, or formula component.
- "choose_explanation": choose why a formula, transformation, or method applies.

Each item must include: type, prompt, options when needed, answer_spec, flashcard_ref, and a short explanation. For exact formulas, include accepted_answers for harmless spacing variants.

Distractors must be common algebra errors, such as sign mistakes, mixing operations, or choosing a method that only fits another equation form. Do not use Match Mode, Write/Spell Mode, spaced review queues, or diagram cards in v1.
