from __future__ import annotations

from scripts.oneoff.polish_g8_math_demo_flashcards import (
    ALGEBRA_HW_ID,
    GEOMETRY_HW_ID,
    polish_content,
)


def test_algebra_demo_flashcards_get_textbook_media_and_replace_off_topic_card():
    content = {
        "flashcards": [
            {"term": "Aniq qiymat (x)", "def": "actual", "cluster": "TAHLIL"},
            {"term": "Bobil ildizi", "def": "off topic", "cluster": "MISOL"},
            {"term": "Yer va o'q misoli", "def": "comparison", "cluster": "MISOL"},
        ],
        "panels": [{"id": 1}],
    }

    updated = polish_content(ALGEBRA_HW_ID, content)
    cards = updated["flashcards"]

    assert updated["panels"] == [{"id": 1}]
    assert [card["term"] for card in cards] == [
        "Aniq qiymat (x)",
        "Aniqlik chegarasi",
        "Yer va o'q misoli",
    ]
    assert all(card["media"]["type"] == "svg" for card in cards)
    assert all("<svg viewBox='0 0 200 150'" in card["media"]["html"] for card in cards)
    assert "Bobil ildizi" not in str(updated)


def test_geometry_demo_adds_only_missing_required_media():
    existing_svg = {"type": "svg", "html": "<svg viewBox='0 0 200 150'></svg>"}
    content = {
        "flashcards": [
            {"term": "sin(90° − α) = cos α", "def": "formula", "media": existing_svg},
            {"term": "Asosiy ayniyat (eslatma)", "def": "identity"},
            {"term": "Co-funksiya almashinuvi (mnemonik)", "def": "swap"},
        ],
        "gb_memory_match": [{"left": "sin", "right": "cos"}],
    }

    updated = polish_content(GEOMETRY_HW_ID, content)
    cards = updated["flashcards"]

    assert cards[0]["media"] == existing_svg
    assert cards[1]["media"]["type"] == "svg"
    assert cards[2]["media"]["type"] == "svg"
    assert "sin^2 a + cos^2 a = 1" in cards[1]["media"]["html"]
    assert "sin" in cards[2]["media"]["html"]
    assert "ctg" in cards[2]["media"]["html"]
    assert updated["gb_memory_match"] == [{"left": "sin", "right": "cos"}]


def test_unrelated_homework_content_is_unchanged():
    content = {"flashcards": [{"term": "Bobil ildizi", "def": "keep"}]}

    assert polish_content("HW-OTHER", content) == content
