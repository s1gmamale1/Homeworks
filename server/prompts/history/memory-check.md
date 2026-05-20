You are generating the Flow v2 Memory Check for History.

Input source: the flashcards generated for this same homework. Test names, dates, causes, consequences, institutions, and historical meaning before practice opens.

Output JSON shape:
{
  "memory_check": {
    "pass_threshold_pct": 60,
    "modes_enabled": ["mcq", "fill_blank", "choose_explanation"],
    "items": []
  }
}

Create 5-8 items. Use at least two modes:
- "mcq": recognize the correct person, event, term, cause, or result.
- "fill_blank": blank one key historical name, place, date, or term with enough context.
- "choose_explanation": choose the explanation that correctly connects cause to consequence or institution to role.

Each item must include: type, prompt, options when needed, answer_spec, flashcard_ref, and a short explanation. Use plausible distractors from the same era or theme.

Do not use Match Mode, Write/Spell Mode, spaced review queues, or diagram cards in v1.
