"""Regression tests for the sentence-fill injector helper.

Pins:
- `answers` field is NOT in the output JSON for any item.
- `explanations` field is NOT in the output JSON for any item.
- `word_bank` field is NOT in output for free_recall items.
- `word_bank` field IS in output for word_bank items.
- `passage`, `mode`, and `id` ARE in output for all items.
- Ordering is preserved (word_bank item first, free_recall item second).
"""
from __future__ import annotations

import json

import pytest

from server.services.injector import _serialize_sentence_fill


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

WORD_BANK_ITEM = {
    "id": "sf-001",
    "mode": "word_bank",
    "passage": "Viyet teoremasi ___ tenglamaning ildizlari va ___ orasidagi bog'lanishni ko'rsatadi.",
    "answers": ["kvadrat", "koeffitsiyentlar"],
    "word_bank": ["kvadrat", "koeffitsiyentlar", "chiziqli", "formula"],
    "explanations": ["Viyet teoremasi kvadrat tenglama uchun ishlaydi.", None],
    "tags": "[Bloom: L2 | PISA: L1]",
    "pisa_level": "L1",
    "difficulty": "medium",
}

FREE_RECALL_ITEM = {
    "id": "sf-002",
    "mode": "free_recall",
    "passage": "Kvadrat tenglama ___ darajali tenglama hisoblanadi.",
    "answers": ["ikkinchi"],
    "word_bank": None,
    "explanations": ["Kvadrat tenglamalar ikkinchi darajali."],
    "subject_hint": "math",
}


def _parse(items):
    """Call _serialize_sentence_fill and parse result back to a list of dicts."""
    raw = _serialize_sentence_fill(items)
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Answer-leak guards
# ---------------------------------------------------------------------------


def test_answers_field_not_in_output_word_bank():
    result = _parse([WORD_BANK_ITEM])
    assert "answers" not in result[0], "answers must be stripped from word_bank items"


def test_answers_field_not_in_output_free_recall():
    result = _parse([FREE_RECALL_ITEM])
    assert "answers" not in result[0], "answers must be stripped from free_recall items"


def test_explanations_field_not_in_output_word_bank():
    result = _parse([WORD_BANK_ITEM])
    assert "explanations" not in result[0], "explanations must be stripped from word_bank items"


def test_explanations_field_not_in_output_free_recall():
    result = _parse([FREE_RECALL_ITEM])
    assert "explanations" not in result[0], "explanations must be stripped from free_recall items"


# ---------------------------------------------------------------------------
# word_bank stripping rules
# ---------------------------------------------------------------------------


def test_word_bank_present_for_word_bank_mode():
    """word_bank is client-visible in word_bank mode (student needs it to play)."""
    result = _parse([WORD_BANK_ITEM])
    assert "word_bank" in result[0], "word_bank must be present for word_bank mode items"
    assert result[0]["word_bank"] == WORD_BANK_ITEM["word_bank"]


def test_word_bank_stripped_for_free_recall_mode():
    """word_bank is null in free_recall mode and must be stripped from output."""
    result = _parse([FREE_RECALL_ITEM])
    assert "word_bank" not in result[0], "word_bank must be stripped for free_recall items"


# ---------------------------------------------------------------------------
# Safe fields ARE in output
# ---------------------------------------------------------------------------


def test_passage_present_in_output():
    result = _parse([WORD_BANK_ITEM, FREE_RECALL_ITEM])
    for item in result:
        assert "passage" in item, f"passage missing from item {item.get('id')}"


def test_mode_present_in_output():
    result = _parse([WORD_BANK_ITEM, FREE_RECALL_ITEM])
    for item in result:
        assert "mode" in item, f"mode missing from item {item.get('id')}"


def test_id_present_in_output():
    result = _parse([WORD_BANK_ITEM, FREE_RECALL_ITEM])
    assert result[0]["id"] == "sf-001"
    assert result[1]["id"] == "sf-002"


def test_optional_metadata_present_in_output():
    result = _parse([WORD_BANK_ITEM])
    assert result[0]["tags"] == WORD_BANK_ITEM["tags"]
    assert result[0]["pisa_level"] == WORD_BANK_ITEM["pisa_level"]
    assert result[0]["difficulty"] == WORD_BANK_ITEM["difficulty"]


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


def test_ordering_is_preserved():
    result = _parse([WORD_BANK_ITEM, FREE_RECALL_ITEM])
    assert len(result) == 2
    assert result[0]["id"] == "sf-001"
    assert result[1]["id"] == "sf-002"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_empty_list_returns_empty_json_array():
    raw = _serialize_sentence_fill([])
    assert json.loads(raw) == []


def test_none_input_returns_empty_json_array():
    raw = _serialize_sentence_fill(None)
    assert json.loads(raw) == []


def test_non_dict_item_skipped_gracefully():
    """Malformed items (non-dict) are silently skipped — no crash."""
    result = _parse(["not-a-dict", WORD_BANK_ITEM])
    assert len(result) == 1
    assert result[0]["id"] == "sf-001"
