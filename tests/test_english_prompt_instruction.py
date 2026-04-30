"""Focused regression tests for English prompt guardrails.

These tests verify that:
- instruction.md does not reference flow.md and lists the 9 phase prompts in order
- flashcards.md has no-answer-leak hint rules
- flashcards.md locks to textbook-only content
- flashcards.md requires concept-related SVG media
"""
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "server" / "prompts" / "english"


def test_instruction_no_flow_md_and_phase_order():
    """instruction.md must not reference flow.md, must declare always-HARD mode,
    and must list the 9 phase prompts in strictly increasing order."""
    text = (PROMPTS_DIR / "instruction.md").read_text(encoding="utf-8")

    # Must NOT contain flow.md reference
    assert "flow.md" not in text, "instruction.md must not reference flow.md"

    # Must declare always-HARD mode
    assert "**Mode:** always HARD for English." in text, (
        "instruction.md must contain '**Mode:** always HARD for English.'"
    )

    # 9 phase-prompt filenames must appear in strictly increasing order
    phase_prompts = [
        "preview-hard.md",
        "flashcards.md",
        "memory-sprint.md",
        "reading.md",
        "game-breaks.md",
        "real-life.md",
        "consolidation.md",
        "final-challenge.md",
        "reflection.md",
    ]
    positions = []
    for name in phase_prompts:
        idx = text.find(name)
        assert idx != -1, f"instruction.md must contain '{name}'"
        positions.append(idx)

    for i in range(1, len(positions)):
        assert positions[i] > positions[i - 1], (
            f"Phase prompts must appear in order: '{phase_prompts[i]}' "
            f"(pos {positions[i]}) must come after '{phase_prompts[i-1]}' "
            f"(pos {positions[i-1]})"
        )


def test_flashcards_no_answer_leak_hint_rules():
    """flashcards.md must contain all no-answer-leak hint rules."""
    text = (PROMPTS_DIR / "flashcards.md").read_text(encoding="utf-8")

    required = [
        "Hint must never expose the answer",
        "Hint cannot repeat the target term",
        "Hint cannot include the exact definition",
        "Hint cannot translate the target into Uzbek",
        "Hint cannot give a sentence where the target word is the obvious missing answer",
    ]
    for phrase in required:
        assert phrase in text, f"flashcards.md must contain: {phrase!r}"


def test_flashcards_textbook_only_fidelity():
    """flashcards.md must lock content to textbook-only sources."""
    text = (PROMPTS_DIR / "flashcards.md").read_text(encoding="utf-8")

    required = [
        "Textbook fidelity",
        "No invented examples",
        "No dictionary padding",
        "No out-of-topic facts",
    ]
    for phrase in required:
        assert phrase in text, f"flashcards.md must contain: {phrase!r}"


def test_flashcards_concept_related_media_rules():
    """flashcards.md must require concept-related SVG media and ban decorative media."""
    text = (PROMPTS_DIR / "flashcards.md").read_text(encoding="utf-8")

    required = [
        "concept-related visual",
        "inline SVG",
        "200",  # loose check that 200×150 size guidance is present
        "No decorative, generic, stock-like, or out-of-topic media",
        "omit `media`",  # literal backtick-quoted media
    ]
    for phrase in required:
        assert phrase in text, f"flashcards.md must contain: {phrase!r}"
