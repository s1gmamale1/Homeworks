from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parent.parent
ENGLISH_PROMPTS = ROOT / "server" / "prompts" / "english"


def _read(name: str) -> str:
    return (ENGLISH_PROMPTS / name).read_text(encoding="utf-8")


def test_english_instruction_is_hard_only_and_direct_prompt_order():
    text = _read("instruction.md")

    assert "Mode:** always HARD for English" in text
    assert "preview-easy.md" not in text
    assert "If EASY" not in text
    assert "flow.md" not in text
    assert "preview-hard.md" in text


def test_english_classifier_schema_cannot_return_easy_mode():
    text = _read("classify.md")

    assert '"mode": "hard"' in text
    assert '"mode": "easy|hard"' not in text


def test_english_game_prompt_only_names_supported_games():
    text = _read("game-breaks.md")

    supported = [
        "Adaptive Quiz",
        "Sentence Fill",
        "Tile Match",
        "Puzzle Lock",
        "Mystery Box",
        "Tic Tac Toe vs AI",
    ]
    for game in supported:
        assert game in text

    assert "Speed Sort" not in text
    assert "Memory Match" not in text
    assert "EASY (2 games)" not in text
    assert "Exactly 3 games" in text
