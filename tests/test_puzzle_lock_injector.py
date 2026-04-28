"""Regression tests for Puzzle Lock runtime injection.

PR #32 introduced the optional GB_PUZZLE_LOCK game-break payload. These tests
make sure the template constant, adapter aliases, and preview rendering stay
connected.
"""

import json
import re

from server.services.injector import _ARRAY_CONSTANTS, inject, verify_template


def _minimal_content_with_puzzle_lock():
    return {
        "meta": {
            "title": "Puzzle Lock Smoke",
            "subject_display": "Algebra",
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
        "gb_puzzle_lock": [
            {"content": "<b>3x</b>", "q": "x = ?", "a": "3"},
            {"text": "legacy tile", "question": "legacy q", "answer": "legacy a"},
        ],
        "boss_questions": [],
        "real_life": None,
        "reading": None,
        "consolidation": None,
        "reflection": None,
    }


def _extract_puzzle_lock_constant(html: str):
    match = re.search(r"const GB_PUZZLE_LOCK\s*=\s*(\[.*?\]);", html, re.DOTALL)
    assert match, "GB_PUZZLE_LOCK constant not found"
    return json.loads(match.group(1))


def test_verify_template_covers_puzzle_lock_constant():
    assert ("gb_puzzle_lock", "GB_PUZZLE_LOCK") in _ARRAY_CONSTANTS
    result = verify_template()
    assert result == {"ok": True, "missing": []}


def test_inject_adapts_puzzle_lock_items_and_legacy_aliases():
    html = inject(
        _minimal_content_with_puzzle_lock(),
        runtime_context={"hw_id": "HW-PL", "subject": "math-algebra", "grade": 8},
    )

    tiles = _extract_puzzle_lock_constant(html)
    assert tiles == [
        {"content": "<b>3x</b>", "q": "x = ?", "a": "3"},
        {"content": "legacy tile", "q": "legacy q", "a": "legacy a"},
    ]

    assert "gb-panel-pl" in html
    assert "gbInitPL" in html
    assert "Puzzle Lock" in html


def test_preview_renders_puzzle_lock_payload(client):
    create = client.post(
        "/api/homeworks",
        json={
            "title": "Puzzle Lock Preview",
            "subject": "math-algebra",
            "grade": 8,
            "mode": "hard",
            "content_json": _minimal_content_with_puzzle_lock(),
        },
    )
    assert create.status_code == 200, create.text
    hw_id = create.json()["id"]

    preview = client.get(f"/api/homeworks/{hw_id}/preview")
    assert preview.status_code == 200, preview.text

    tiles = _extract_puzzle_lock_constant(preview.text)
    assert tiles[0] == {"content": "<b>3x</b>", "q": "x = ?", "a": "3"}
    assert tiles[1] == {"content": "legacy tile", "q": "legacy q", "a": "legacy a"}
    assert "GB_PUZZLE_LOCK" in preview.text
    assert "gb-panel-pl" in preview.text
