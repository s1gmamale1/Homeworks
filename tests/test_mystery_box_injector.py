"""Regression tests for Mystery Box runtime injection.

Mystery Box is the optional GB_MYSTERY_BOX game-break payload added after
Puzzle Lock. These tests pin the wiring so that:

- the template constant is registered for replacement,
- the shape adapter pre-computes the shared picker label list across
  sibling boxes (the runtime doesn't have to derive it on the client),
- the labels list preserves first-occurrence order and dedupes,
- the preview endpoint stamps the payload through end-to-end.
"""

import json
import re

from server.services.injector import _ARRAY_CONSTANTS, inject, verify_template


def _minimal_content_with_mystery_box():
    return {
        "meta": {
            "title": "Mystery Box Smoke",
            "subject_display": "Geometriya",
            "section": "",
            "cefr_level": "",
        },
        "gate_quote": {"mode": "auto"},
        "panels": [],
        "flashcards": [],
        "memory_sprint": [],
        "gb_adaptive_quiz": [],
        "gb_why_chain": [],
        "gb_memory_match": [],
        "gb_puzzle_lock": [],
        "gb_mystery_box": [
            {"category": "Algebra", "q": "Solve 3x+5=14", "a": "3"},
            {"category": "Geometry", "q": "Area of 3x4 rect?", "a": "12"},
            {"category": "Reading", "q": "Main idea of passage?", "a": "diversity"},
        ],
        "boss_questions": [],
        "real_life": None,
        "reading": None,
        "consolidation": None,
        "reflection": None,
    }


def _extract_mystery_box_constant(html: str):
    match = re.search(r"const GB_MYSTERY_BOX\s*=\s*(\[.*?\]);", html, re.DOTALL)
    assert match, "GB_MYSTERY_BOX constant not found"
    return json.loads(match.group(1))


def test_verify_template_covers_mystery_box_constant():
    assert ("gb_mystery_box", "GB_MYSTERY_BOX") in _ARRAY_CONSTANTS
    result = verify_template()
    assert result == {"ok": True, "missing": []}


def test_inject_stamps_picker_labels_onto_every_box():
    html = inject(
        _minimal_content_with_mystery_box(),
        runtime_context={"hw_id": "HW-MB", "subject": "geometriya-g7-11", "grade": 8},
    )

    boxes = _extract_mystery_box_constant(html)
    assert len(boxes) == 3
    expected_labels = ["Algebra", "Geometry", "Reading"]
    for box in boxes:
        assert box["labels"] == expected_labels, (
            "Adapter must stamp the same picker label list onto every box "
            "so the runtime renders consistent options across sibling items."
        )

    assert "gb-panel-mb" in html
    assert "gbInitMB" in html
    assert "Mystery Box" in html


def test_inject_dedupes_and_preserves_first_occurrence_order():
    payload = {
        "meta": {"title": "Dedupe", "subject_display": "X", "section": "", "cefr_level": ""},
        "gate_quote": {"mode": "auto"},
        "panels": [], "flashcards": [], "memory_sprint": [],
        "gb_adaptive_quiz": [], "gb_why_chain": [], "gb_memory_match": [], "gb_puzzle_lock": [],
        "gb_mystery_box": [
            {"category": "B", "q": "q1", "a": "a"},
            {"category": "A", "q": "q2", "a": "a"},
            {"category": "B", "q": "q3", "a": "a"},  # duplicate of first
            {"category": "  ", "q": "q4", "a": "a"},  # whitespace-only → dropped
            {"category": "C", "q": "q5", "a": "a"},
        ],
        "boss_questions": [], "real_life": None,
        "reading": None, "consolidation": None, "reflection": None,
    }
    html = inject(payload, runtime_context={"hw_id": "HW-D", "subject": "math-algebra", "grade": 8})
    boxes = _extract_mystery_box_constant(html)
    assert boxes[0]["labels"] == ["B", "A", "C"], (
        "Labels must dedupe AND preserve the order each unique category first appears."
    )
    # whitespace-only category should be dropped from picker but the box stays.
    assert len(boxes) == 5


def test_inject_handles_empty_mystery_box():
    payload = _minimal_content_with_mystery_box()
    payload["gb_mystery_box"] = []
    html = inject(payload, runtime_context={"hw_id": "HW-E", "subject": "math-algebra", "grade": 8})
    boxes = _extract_mystery_box_constant(html)
    assert boxes == [], "Empty mystery box payload must produce empty constant — runtime skips the sub-game."


def test_preview_renders_mystery_box_payload(client):
    create = client.post(
        "/api/homeworks",
        json={
            "title": "Mystery Box Preview",
            "subject": "geometriya-g7-11",
            "grade": 8,
            "mode": "hard",
            "content_json": _minimal_content_with_mystery_box(),
        },
    )
    assert create.status_code == 200, create.text
    hw_id = create.json()["id"]

    preview = client.get(f"/api/homeworks/{hw_id}/preview")
    assert preview.status_code == 200, preview.text

    boxes = _extract_mystery_box_constant(preview.text)
    assert len(boxes) == 3
    assert boxes[0]["category"] == "Algebra"
    assert boxes[0]["q"] == "Solve 3x+5=14"
    assert boxes[0]["a"] == "3"
    assert boxes[0]["labels"] == ["Algebra", "Geometry", "Reading"]
    assert "GB_MYSTERY_BOX" in preview.text
    assert "gb-panel-mb" in preview.text


def test_inject_drops_non_dict_items_silently():
    payload = _minimal_content_with_mystery_box()
    payload["gb_mystery_box"] = [
        {"category": "Real", "q": "q", "a": "a"},
        "not a dict",
        ["also", "not", "a", "dict"],
        None,
        {"category": "Other", "q": "q2", "a": "b"},
    ]
    html = inject(payload, runtime_context={"hw_id": "HW-N", "subject": "math-algebra", "grade": 8})
    boxes = _extract_mystery_box_constant(html)
    assert len(boxes) == 2, "Non-dict items must be silently dropped — runtime can't shape them."
    assert [b["category"] for b in boxes] == ["Real", "Other"]
