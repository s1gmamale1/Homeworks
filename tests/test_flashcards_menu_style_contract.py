from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_flashcards_uses_menu_path_visual_language_without_rewriting_hub():
    css = (ROOT / "frontend/app/src/runtime/Flashcards.module.css").read_text()
    compact_css = " ".join(css.split())
    hub_css = (ROOT / "frontend/app/src/runtime/LearningHub.module.css").read_text()

    assert "--fc-blue" in css
    assert "--fc-blue-edge" in css
    assert "light-blue wash" in css
    assert "box-shadow: 0 9px 0 var(--fc-blue-edge)" in compact_css
    assert ".actions :global(.v2-btn)" in css

    # Flashcard-only work should not replace the Hub's current menu/path shell.
    assert "Duolingo-flavored winding PATH" in hub_css
