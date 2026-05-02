"""Regression tests for the SentenceFillItem Pydantic schema.

Pins:
- Valid word_bank and free_recall items are accepted.
- Blank count mismatch (passage blanks != answers length) is rejected.
- Zero blanks in passage is rejected.
- 7+ blanks is rejected.
- word_bank mode without word_bank field is rejected.
- word_bank not containing all answers is rejected.
- word_bank with no distractors is rejected.
- explanations length != answers length is rejected.
- extra="allow" means unknown future fields (e.g., audio_url) don't break load.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from server.schemas.content import SentenceFillItem


# ---------------------------------------------------------------------------
# Helper: minimal valid word_bank item
# ---------------------------------------------------------------------------

def _word_bank_item(**overrides):
    base = {
        "id": "sf-001",
        "mode": "word_bank",
        "passage": "Viyet teoremasi ___ tenglamaning ildizlari va ___ orasidagi bog'lanishni ko'rsatadi.",
        "answers": ["kvadrat", "koeffitsiyentlar"],
        "word_bank": ["kvadrat", "koeffitsiyentlar", "chiziqli", "formula"],
    }
    base.update(overrides)
    return base


def _free_recall_item(**overrides):
    base = {
        "id": "sf-002",
        "mode": "free_recall",
        "passage": "Kvadrat tenglama ___ darajali tenglama hisoblanadi.",
        "answers": ["ikkinchi"],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 1. Valid items
# ---------------------------------------------------------------------------


def test_valid_word_bank_item_is_accepted():
    item = SentenceFillItem(**_word_bank_item())
    assert item.id == "sf-001"
    assert item.mode == "word_bank"
    assert len(item.answers) == 2


def test_valid_free_recall_item_is_accepted():
    item = SentenceFillItem(**_free_recall_item())
    assert item.id == "sf-002"
    assert item.mode == "free_recall"
    assert item.word_bank is None


def test_valid_item_with_explanations_accepted():
    item = SentenceFillItem(**_word_bank_item(
        explanations=["Viyet teoremasi kvadrat tenglama uchun ishlaydi.", None],
    ))
    assert item.explanations[0] is not None
    assert item.explanations[1] is None


def test_valid_item_with_optional_metadata_accepted():
    item = SentenceFillItem(**_word_bank_item(
        pisa_level="L2",
        difficulty="medium",
        subject_hint="math",
        tags="[Bloom: L2 | PISA: L1]",
        tier="premium",
    ))
    assert item.pisa_level == "L2"
    assert item.tier == "premium"


# ---------------------------------------------------------------------------
# 2. Blank count mismatch (3 blanks, 2 answers)
# ---------------------------------------------------------------------------


def test_blank_count_mismatch_is_rejected():
    """3 ___ in passage but only 2 answers — validator must reject."""
    with pytest.raises(ValidationError, match="answers length 2 != blanks 3"):
        SentenceFillItem(**_word_bank_item(
            passage="___ va ___ va ___.",
            answers=["a", "b"],
            word_bank=["a", "b", "c", "d"],
        ))


# ---------------------------------------------------------------------------
# 3. Zero blanks
# ---------------------------------------------------------------------------


def test_zero_blanks_is_rejected():
    with pytest.raises(ValidationError, match="at least one"):
        SentenceFillItem(**_free_recall_item(
            passage="Bu passajda hech qanday bo'sh joy yo'q.",
            answers=[],
        ))


# ---------------------------------------------------------------------------
# 4. 7+ blanks
# ---------------------------------------------------------------------------


def test_seven_blanks_is_rejected():
    passage = " ".join(["___"] * 7)
    answers = [f"w{i}" for i in range(7)]
    word_bank = answers + ["distractor"]
    with pytest.raises(ValidationError, match="7 blanks; spec allows 1-6"):
        SentenceFillItem(**_word_bank_item(
            passage=passage,
            answers=answers,
            word_bank=word_bank,
        ))


# ---------------------------------------------------------------------------
# 5. word_bank mode without word_bank field
# ---------------------------------------------------------------------------


def test_word_bank_mode_missing_word_bank_field_is_rejected():
    with pytest.raises(ValidationError, match="word_bank required"):
        SentenceFillItem(
            id="sf-x",
            mode="word_bank",
            passage="Viyet ___ teoremasi.",
            answers=["kvadrat"],
            word_bank=None,
        )


# ---------------------------------------------------------------------------
# 6. word_bank not containing all answers
# ---------------------------------------------------------------------------


def test_word_bank_missing_answer_is_rejected():
    with pytest.raises(ValidationError, match="word_bank must contain every answer"):
        SentenceFillItem(**_word_bank_item(
            word_bank=["chiziqli", "formula", "distractor"],  # "kvadrat" missing
        ))


# ---------------------------------------------------------------------------
# 7. word_bank with no distractors (len(word_bank) == len(answers))
# ---------------------------------------------------------------------------


def test_word_bank_without_distractors_is_rejected():
    with pytest.raises(ValidationError, match="at least one distractor"):
        SentenceFillItem(**_word_bank_item(
            answers=["kvadrat"],
            passage="Viyet ___ teoremasi.",
            word_bank=["kvadrat"],  # exactly answers count — no distractor
        ))


# ---------------------------------------------------------------------------
# 8. explanations length != answers length
# ---------------------------------------------------------------------------


def test_explanations_length_mismatch_is_rejected():
    with pytest.raises(ValidationError, match="explanations length 1 != answers 2"):
        SentenceFillItem(**_word_bank_item(
            explanations=["Only one explanation for two answers"],
        ))


# ---------------------------------------------------------------------------
# 9. extra="allow" — unknown future fields pass through silently
# ---------------------------------------------------------------------------


def test_extra_allow_unknown_field_does_not_break_load():
    """A hypothetical future `audio_url` field must not cause a ValidationError."""
    item = SentenceFillItem(**_free_recall_item(audio_url="https://example.com/audio.mp3"))
    # The field is accepted (extra="allow") and accessible via model_extra
    assert item.model_extra.get("audio_url") == "https://example.com/audio.mp3"
