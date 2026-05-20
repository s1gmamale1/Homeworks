You are generating the Flow v2 Memory Check for Geometry.

Input source: the flashcards generated for this same homework. Test notation, definitions, theorem conditions, and visual reasoning anchors before practice opens.

Output JSON shape:
{
  "memory_check": {
    "pass_threshold_pct": 60,
    "modes_enabled": ["mcq", "fill_blank", "choose_explanation"],
    "items": []
  }
}

Create 5-8 items. Use at least two modes:
- "mcq": recognize the correct definition, theorem condition, notation meaning, or next step.
- "fill_blank": blank one mathematical term, symbol, or number that was anchored in the flashcards.
- "choose_explanation": choose why a geometric property or theorem applies.

Each item must include: type, prompt, options when needed, answer_spec, flashcard_ref, and a short explanation. Use answer_spec.option_index for option questions and accepted_answers for text blanks.

Distractors must be common geometry confusions, such as mixing radius/diameter, parallel/perpendicular, congruent/similar, or condition/conclusion. Do not use Match Mode, Write/Spell Mode, spaced review queues, or diagram cards in v1.
