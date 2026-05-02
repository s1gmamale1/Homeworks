"""Regression tests for the sentence-fill runtime panel + JS global.

Pins:
- Rendered homework HTML contains the gb-panel-sf DOM hook.
- Rendered HTML contains the GB_SENTENCE_FILL JS global declaration.
- The literal string "answers" does NOT appear inside the rendered
  GB_SENTENCE_FILL array (answer-leak guard).
- The literal string "explanations" does NOT appear inside the rendered
  GB_SENTENCE_FILL array (explanation-leak guard).
"""
from __future__ import annotations

import json
import re

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sf_homework(client):
    """Create a homework that includes one word_bank and one free_recall
    sentence-fill item, so the rendered page has a populated GB_SENTENCE_FILL."""
    payload = {
        "title": "Sentence Fill smoke",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
        "family": "aniq-fanlar",
        "content_json": {
            "meta": {
                "title": "Sentence Fill smoke",
                "subject_display": "Algebra",
            },
            "panels": [],
            "flashcards": [],
            "boss_questions": [],
            "memory_sprint": [],
            "gb_sentence_fill": [
                {
                    "id": "sf-001",
                    "mode": "word_bank",
                    "passage": "Viyet teoremasi ___ tenglamaning ildizlari va ___ orasidagi bog'lanishni ko'rsatadi.",
                    "answers": ["kvadrat", "koeffitsiyentlar"],
                    "word_bank": ["kvadrat", "koeffitsiyentlar", "chiziqli", "formula"],
                    "explanations": [
                        "Viyet teoremasi kvadrat tenglama uchun ishlaydi.",
                        None,
                    ],
                    "pisa_level": "L1",
                    "difficulty": "medium",
                },
                {
                    "id": "sf-002",
                    "mode": "free_recall",
                    "passage": "Kvadrat tenglama ___ darajali tenglama hisoblanadi.",
                    "answers": ["ikkinchi"],
                    "explanations": ["Kvadrat tenglamalar ikkinchi darajali."],
                },
            ],
        },
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, resp.text
    hw_id = resp.json()["id"]
    r = client.get(f"/h/{hw_id}")
    assert r.status_code == 200
    return r.text


# ---------------------------------------------------------------------------
# DOM hook
# ---------------------------------------------------------------------------


def test_gb_panel_sf_dom_hook_present(sf_homework):
    """Rendered HTML must contain the placeholder panel id gb-panel-sf."""
    assert 'id="gb-panel-sf"' in sf_homework, (
        "gb-panel-sf panel hook missing from rendered HTML — "
        "frontend agent needs this to mount the Sentence Fill UI"
    )


# ---------------------------------------------------------------------------
# JS global declaration
# ---------------------------------------------------------------------------


def test_gb_sentence_fill_js_global_present(sf_homework):
    """Rendered HTML must contain the GB_SENTENCE_FILL JS global declaration."""
    assert "const GB_SENTENCE_FILL = " in sf_homework, (
        "GB_SENTENCE_FILL JS global not found in rendered HTML"
    )


# ---------------------------------------------------------------------------
# Answer-leak guard — answers must NOT be in the rendered GB_SENTENCE_FILL array
# ---------------------------------------------------------------------------


def _extract_gb_sentence_fill_array(html: str) -> str:
    """Extract the literal array string from the GB_SENTENCE_FILL = [...]; declaration."""
    match = re.search(r"const GB_SENTENCE_FILL\s*=\s*(\[[\s\S]*?\]);", html)
    if not match:
        return ""
    return match.group(1)


def test_answers_field_not_in_rendered_gb_sentence_fill(sf_homework):
    """The literal key 'answers' must NOT appear in the GB_SENTENCE_FILL array.

    This is the critical answer-leak guard: if the injector forgets to strip
    answers, students can find correct values in devtools.
    """
    array_str = _extract_gb_sentence_fill_array(sf_homework)
    assert array_str, "GB_SENTENCE_FILL array not found in rendered HTML"
    # Parse as JSON to verify shape and check key absence
    items = json.loads(array_str)
    for item in items:
        assert "answers" not in item, (
            f"item {item.get('id')} has 'answers' key in rendered GB_SENTENCE_FILL — "
            "injector must strip this field before sending to client"
        )


def test_explanations_field_not_in_rendered_gb_sentence_fill(sf_homework):
    """The literal key 'explanations' must NOT appear in the GB_SENTENCE_FILL array.

    Explanations are revealed server-side after a blank is locked — pre-shipping
    them to the client allows devtools snooping.
    """
    array_str = _extract_gb_sentence_fill_array(sf_homework)
    assert array_str, "GB_SENTENCE_FILL array not found in rendered HTML"
    items = json.loads(array_str)
    for item in items:
        assert "explanations" not in item, (
            f"item {item.get('id')} has 'explanations' key in rendered GB_SENTENCE_FILL — "
            "injector must strip this field before sending to client"
        )


# ---------------------------------------------------------------------------
# word_bank visibility rules
# ---------------------------------------------------------------------------


def test_word_bank_present_for_word_bank_mode_item(sf_homework):
    """word_bank IS visible to the client for word_bank mode (student picks from it)."""
    array_str = _extract_gb_sentence_fill_array(sf_homework)
    items = json.loads(array_str)
    wb_items = [i for i in items if i.get("mode") == "word_bank"]
    assert wb_items, "No word_bank mode items in rendered GB_SENTENCE_FILL"
    for item in wb_items:
        assert "word_bank" in item, (
            f"word_bank missing for word_bank-mode item {item.get('id')} — "
            "student needs it to play"
        )


def test_word_bank_stripped_for_free_recall_mode_item(sf_homework):
    """word_bank is NOT in free_recall items (null + stripped by injector)."""
    array_str = _extract_gb_sentence_fill_array(sf_homework)
    items = json.loads(array_str)
    fr_items = [i for i in items if i.get("mode") == "free_recall"]
    assert fr_items, "No free_recall mode items in rendered GB_SENTENCE_FILL"
    for item in fr_items:
        assert "word_bank" not in item, (
            f"word_bank present on free_recall item {item.get('id')} — "
            "injector must strip it for free_recall items"
        )


# ---------------------------------------------------------------------------
# Safe fields are visible
# ---------------------------------------------------------------------------


def test_passage_and_mode_and_id_present_in_rendered_array(sf_homework):
    """passage, mode, and id must all be present in the rendered GB_SENTENCE_FILL items."""
    array_str = _extract_gb_sentence_fill_array(sf_homework)
    items = json.loads(array_str)
    assert len(items) == 2, f"expected 2 items, got {len(items)}"
    for item in items:
        assert "passage" in item, f"passage missing from item {item.get('id')}"
        assert "mode" in item, f"mode missing from item {item.get('id')}"
        assert "id" in item, "id missing from item"


# ---------------------------------------------------------------------------
# Homework without sentence-fill still renders cleanly (empty array case)
# ---------------------------------------------------------------------------


def test_homework_without_sf_renders_empty_array(client):
    """A homework without gb_sentence_fill must render GB_SENTENCE_FILL = [];
    — no crash, no literal __GB_SENTENCE_FILL__ placeholder leaking through."""
    create = client.post("/api/homeworks", json={
        "title": "No SF homework",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
        "content_json": {
            "meta": {"title": "No SF homework"},
            "panels": [],
            "flashcards": [],
            "boss_questions": [],
            "memory_sprint": [],
        },
    })
    assert create.status_code == 200, create.text
    hw_id = create.json()["id"]
    r = client.get(f"/h/{hw_id}")
    assert r.status_code == 200
    body = r.text
    # The placeholder must be replaced (not leaked to client)
    assert "__GB_SENTENCE_FILL__" not in body, (
        "literal __GB_SENTENCE_FILL__ found in rendered HTML — "
        "injector did not substitute the constant"
    )
    # Must declare the global (even if empty)
    assert "const GB_SENTENCE_FILL = " in body
    # Must be an empty array
    array_str = _extract_gb_sentence_fill_array(body)
    assert array_str, "GB_SENTENCE_FILL array declaration not found"
    items = json.loads(array_str)
    assert items == [], f"expected empty array, got {items}"
