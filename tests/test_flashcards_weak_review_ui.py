from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_flashcards_retry_highlights_cards_linked_from_memory_check():
    src = (ROOT / "frontend/app/src/runtime/Flashcards.tsx").read_text()

    assert "flashcard_ref" in src
    assert "weakCardIndices" in src
    assert "Weak — review" in src
    assert "s.dotWeak" in src
