You are generating the Flow v2 Memory Check for English.

Input source: the flashcards generated for this same homework. Test whether vocabulary, grammar anchors, and usage patterns stuck before practice opens.

Output JSON shape:
{
  "memory_check": {
    "pass_threshold_pct": 60,
    "modes_enabled": ["mcq", "fill_blank", "choose_explanation"],
    "items": []
  }
}

Create 5-8 items. Use at least two modes:
- "mcq": choose the correct word, phrase, sentence, or grammar form.
- "fill_blank": blank the target word or form inside a complete sentence with enough context.
- "choose_explanation": choose the reason a collocation, tense, preposition, or meaning is correct.

Each item must include: type, prompt, options when needed, answer_spec, flashcard_ref, and a short explanation. For fill_blank, include accepted_answers for capitalization or simple spelling variants only when they are truly acceptable.

Distractors must be common learner errors. Do not use Match Mode, Write/Spell Mode, spaced review queues, or diagram cards in v1.
