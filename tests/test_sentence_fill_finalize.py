"""Regression tests for `/api/ai/check-answer/finalize` (sentence-fill perfect-fill bonus).

Pins:
- All blanks correct on attempt 1 → perfect_fill: True, xp_bonus: 100.
- Any 2nd-attempt-correct or any locked blank → perfect_fill: False, xp_bonus: 0.
- Cold call (no prior attempts logged) → graceful default with summary zeros.
- Phase enforcement + 404 for unknown ids.
"""
from __future__ import annotations

import pytest

import server.routes.ai as _ai_routes


@pytest.fixture(autouse=True)
def _wipe_sf_attempts():
    _ai_routes._SF_ATTEMPTS.clear()
    yield
    _ai_routes._SF_ATTEMPTS.clear()


def _seed_three_blank_homework(client) -> str:
    payload = {
        "title": "SF finalize test HW",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
        "family": "aniq-fanlar",
        "content_json": {
            "meta": {"title": "SF finalize test HW"},
            "panels": [],
            "flashcards": [],
            "boss_questions": [],
            "memory_sprint": [],
            "gb_sentence_fill": [
                {
                    "id": "sf-001",
                    "mode": "word_bank",
                    "passage": "A ___ B ___ C ___",
                    "answers": ["one", "two", "three"],
                    "word_bank": ["one", "two", "three", "four"],
                    "explanations": ["why-1", "why-2", "why-3"],
                }
            ],
        },
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _submit(client, hw_id: str, blank_idx: int, value: str, attempt: int):
    return client.post("/api/ai/check-answer", json={
        "phase": "sentence-fill",
        "homework_id": hw_id,
        "item_id": "sf-001",
        "blank_idx": blank_idx,
        "student_value": value,
        "attempt_number": attempt,
    })


def _finalize(client, hw_id: str, item_id: str = "sf-001"):
    return client.post("/api/ai/check-answer/finalize", json={
        "phase": "sentence-fill",
        "homework_id": hw_id,
        "item_id": item_id,
    })


# ---------------------------------------------------------------------------
# All blanks correct on attempt 1 → perfect fill
# ---------------------------------------------------------------------------


def test_all_blanks_correct_attempt_1_is_perfect_fill(client):
    hw_id = _seed_three_blank_homework(client)
    assert _submit(client, hw_id, 0, "one", 1).status_code == 200
    assert _submit(client, hw_id, 1, "two", 1).status_code == 200
    assert _submit(client, hw_id, 2, "three", 1).status_code == 200

    resp = _finalize(client, hw_id)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["perfect_fill"] is True
    assert data["xp_bonus"] == 100
    assert data["summary"] == {
        "blanks_correct": 3,
        "blanks_total": 3,
        "first_attempt_correct": 3,
    }


# ---------------------------------------------------------------------------
# Any 2nd-attempt correct → not perfect fill
# ---------------------------------------------------------------------------


def test_one_blank_correct_on_attempt_2_blocks_perfect_fill(client):
    hw_id = _seed_three_blank_homework(client)
    # Blank 0: wrong on 1, correct on 2.
    assert _submit(client, hw_id, 0, "zzz", 1).status_code == 200
    assert _submit(client, hw_id, 0, "one", 2).status_code == 200
    # Blanks 1+2: correct on 1.
    assert _submit(client, hw_id, 1, "two", 1).status_code == 200
    assert _submit(client, hw_id, 2, "three", 1).status_code == 200

    data = _finalize(client, hw_id).json()
    assert data["perfect_fill"] is False
    assert data["xp_bonus"] == 0
    assert data["summary"] == {
        "blanks_correct": 3,
        "blanks_total": 3,
        "first_attempt_correct": 2,
    }


# ---------------------------------------------------------------------------
# Any locked-wrong blank → not perfect fill
# ---------------------------------------------------------------------------


def test_one_blank_locked_wrong_blocks_perfect_fill(client):
    hw_id = _seed_three_blank_homework(client)
    # Blank 0: wrong twice → locked, never correct.
    assert _submit(client, hw_id, 0, "zzz", 1).status_code == 200
    assert _submit(client, hw_id, 0, "qqq", 2).status_code == 200
    # Blanks 1+2: correct on 1.
    assert _submit(client, hw_id, 1, "two", 1).status_code == 200
    assert _submit(client, hw_id, 2, "three", 1).status_code == 200

    data = _finalize(client, hw_id).json()
    assert data["perfect_fill"] is False
    assert data["xp_bonus"] == 0
    assert data["summary"]["blanks_correct"] == 2
    assert data["summary"]["blanks_total"] == 3
    assert data["summary"]["first_attempt_correct"] == 2


# ---------------------------------------------------------------------------
# Cold call — no prior attempts → graceful default
# ---------------------------------------------------------------------------


def test_no_prior_attempts_returns_graceful_default(client):
    hw_id = _seed_three_blank_homework(client)
    data = _finalize(client, hw_id).json()
    assert data["perfect_fill"] is False
    assert data["xp_bonus"] == 0
    assert data["summary"] == {
        "blanks_correct": 0,
        "blanks_total": 3,
        "first_attempt_correct": 0,
    }


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_finalize_rejects_non_sentence_fill_phase(client):
    hw_id = _seed_three_blank_homework(client)
    resp = client.post("/api/ai/check-answer/finalize", json={
        "phase": "adaptive-quiz",
        "homework_id": hw_id,
        "item_id": "sf-001",
    })
    assert resp.status_code == 400


def test_finalize_unknown_homework_returns_404(client):
    resp = _finalize(client, "HW-DOES-NOT-EXIST")
    assert resp.status_code == 404


def test_finalize_unknown_item_returns_404(client):
    hw_id = _seed_three_blank_homework(client)
    resp = _finalize(client, hw_id, item_id="sf-999")
    assert resp.status_code == 404
