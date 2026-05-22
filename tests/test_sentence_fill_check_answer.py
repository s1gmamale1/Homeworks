"""Regression tests for `/api/ai/check-answer` with phase=sentence-fill.

Pins the per-blank grading branch added in Chunk B:
- Word-bank mode: deterministic equality after normalize.
- Free-recall mode: routes through the AI semantic grader (mocked).
- Lock-on-2nd-wrong + reveal-on-lock semantics.
- XP breakdown: base 100 if correct, +25 first-attempt bonus only on attempt 1.
- Validation: missing fields → 422 / 400, out-of-range blank_idx → 400.
- Answer-leak guard: the literal key `"answers"` never appears in the response body.
"""
from __future__ import annotations

import re
import pytest
from unittest.mock import patch

import server.routes.ai as _ai_routes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _always_unlocked(*a, **k):
    return True


@pytest.fixture(autouse=True)
def _unlock_practice_arc(monkeypatch):
    """Sentence-Fill is now a server-gated practice-arc game (BLOCKER #3).
    These are grading unit tests, not gating tests — patch the unlock check
    always-True so they exercise the grader, not the 403 PRACTICE_LOCKED guard.
    The gate itself is pinned by tests/test_practice_gate_server_enforced.py."""
    monkeypatch.setattr("server.routes.ai.is_practice_unlocked", _always_unlocked)


@pytest.fixture(autouse=True)
def _wipe_sf_attempts():
    """Reset the in-memory sentence-fill attempt tracker between tests."""
    _ai_routes._SF_ATTEMPTS.clear()
    yield
    _ai_routes._SF_ATTEMPTS.clear()


def _seed_homework(client, *, mode: str = "word_bank") -> str:
    """Insert a homework with one sentence-fill item and return its hw_id."""
    item: dict
    if mode == "word_bank":
        item = {
            "id": "sf-001",
            "mode": "word_bank",
            "passage": "A ___ B ___ C ___",
            "answers": ["one", "two", "three"],
            "word_bank": ["one", "two", "three", "four"],
            "explanations": ["why-1", None, "why-3"],
        }
    else:
        item = {
            "id": "sf-001",
            "mode": "free_recall",
            "passage": "Capital of France is ___",
            "answers": ["Paris"],
            "explanations": ["Paris is the capital."],
            "subject_hint": "history",
        }
    payload = {
        "title": "SF check-answer test HW",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
        "family": "aniq-fanlar",
        "content_json": {
            "meta": {"title": "SF check-answer test HW"},
            "panels": [],
            "flashcards": [],
            "boss_questions": [],
            "memory_sprint": [],
            "gb_sentence_fill": [item],
        },
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _post_check(client, **overrides) -> tuple[int, dict]:
    body = {
        "phase": "sentence-fill",
        "homework_id": overrides.pop("homework_id"),
        "item_id": overrides.pop("item_id", "sf-001"),
        "blank_idx": overrides.pop("blank_idx", 0),
        "student_value": overrides.pop("student_value", ""),
        "attempt_number": overrides.pop("attempt_number", 1),
    }
    body.update(overrides)
    resp = client.post("/api/ai/check-answer", json=body)
    try:
        return resp.status_code, resp.json()
    except Exception:
        return resp.status_code, {"_raw": resp.text}


# ---------------------------------------------------------------------------
# Word-bank mode — deterministic
# ---------------------------------------------------------------------------


def test_word_bank_attempt1_correct(client):
    hw_id = _seed_homework(client, mode="word_bank")
    code, data = _post_check(
        client,
        homework_id=hw_id,
        blank_idx=0,
        student_value="one",
        attempt_number=1,
    )
    assert code == 200, data
    assert data["correct"] is True
    assert data["lock"] is True
    assert data["correct_answer"] is None
    assert data["explanation"] is None
    assert data["xp"] == {"base": 100, "first_attempt_bonus": 25, "total": 125}


def test_word_bank_attempt1_wrong_no_lock(client):
    hw_id = _seed_homework(client, mode="word_bank")
    code, data = _post_check(
        client,
        homework_id=hw_id,
        blank_idx=0,
        student_value="four",
        attempt_number=1,
    )
    assert code == 200, data
    assert data["correct"] is False
    assert data["lock"] is False
    assert data["correct_answer"] is None
    assert data["explanation"] is None
    assert data["xp"] == {"base": 0, "first_attempt_bonus": 0, "total": 0}


def test_word_bank_attempt2_wrong_locks_and_reveals(client):
    hw_id = _seed_homework(client, mode="word_bank")
    # First attempt: wrong (no lock).
    _post_check(
        client,
        homework_id=hw_id,
        blank_idx=0,
        student_value="four",
        attempt_number=1,
    )
    # Second attempt: also wrong → lock + reveal answer + reveal explanation.
    code, data = _post_check(
        client,
        homework_id=hw_id,
        blank_idx=0,
        student_value="five",
        attempt_number=2,
    )
    assert code == 200, data
    assert data["correct"] is False
    assert data["lock"] is True
    assert data["correct_answer"] == "one"
    assert data["explanation"] == "why-1"
    assert data["xp"] == {"base": 0, "first_attempt_bonus": 0, "total": 0}


def test_word_bank_attempt2_correct_no_first_attempt_bonus(client):
    hw_id = _seed_homework(client, mode="word_bank")
    _post_check(
        client,
        homework_id=hw_id,
        blank_idx=0,
        student_value="four",
        attempt_number=1,
    )
    code, data = _post_check(
        client,
        homework_id=hw_id,
        blank_idx=0,
        student_value="one",
        attempt_number=2,
    )
    assert code == 200, data
    assert data["correct"] is True
    assert data["lock"] is True
    assert data["correct_answer"] is None
    # No first-attempt bonus on attempt 2 even when correct.
    assert data["xp"] == {"base": 100, "first_attempt_bonus": 0, "total": 100}


def test_word_bank_locked_blank_with_null_explanation_returns_null(client):
    """Blank index 1 has explanations[1] == None — locked-and-wrong should still
    surface correct_answer but explanation stays null (graceful)."""
    hw_id = _seed_homework(client, mode="word_bank")
    _post_check(
        client,
        homework_id=hw_id,
        blank_idx=1,
        student_value="zzz",
        attempt_number=1,
    )
    code, data = _post_check(
        client,
        homework_id=hw_id,
        blank_idx=1,
        student_value="qqq",
        attempt_number=2,
    )
    assert code == 200
    assert data["correct"] is False
    assert data["lock"] is True
    assert data["correct_answer"] == "two"
    assert data["explanation"] is None


def test_word_bank_normalize_lowercase_and_whitespace(client):
    hw_id = _seed_homework(client, mode="word_bank")
    code, data = _post_check(
        client,
        homework_id=hw_id,
        blank_idx=0,
        student_value="  ONE  ",
        attempt_number=1,
    )
    assert code == 200
    assert data["correct"] is True


# ---------------------------------------------------------------------------
# Free-recall mode — AI grader path
# ---------------------------------------------------------------------------


def test_free_recall_correct_via_ai(client):
    hw_id = _seed_homework(client, mode="free_recall")

    async def _fake_correct(student_value, expected, *, subject_hint, passage):
        # Confirm routing args.
        assert expected == "Paris"
        assert subject_hint == "history"
        assert passage == "Capital of France is ___"
        return True

    with patch.object(_ai_routes, "_ai_grade_sentence_fill", new=_fake_correct):
        code, data = _post_check(
            client,
            homework_id=hw_id,
            blank_idx=0,
            student_value="paris",
            attempt_number=1,
        )
    assert code == 200, data
    assert data["correct"] is True
    assert data["xp"]["total"] == 125


def test_free_recall_wrong_via_ai(client):
    hw_id = _seed_homework(client, mode="free_recall")

    async def _fake_wrong(*a, **k):
        return False

    with patch.object(_ai_routes, "_ai_grade_sentence_fill", new=_fake_wrong):
        code, data = _post_check(
            client,
            homework_id=hw_id,
            blank_idx=0,
            student_value="London",
            attempt_number=1,
        )
    assert code == 200
    assert data["correct"] is False
    assert data["lock"] is False


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_missing_item_id_returns_400(client):
    hw_id = _seed_homework(client, mode="word_bank")
    resp = client.post("/api/ai/check-answer", json={
        "phase": "sentence-fill",
        "homework_id": hw_id,
        "blank_idx": 0,
        "student_value": "one",
        "attempt_number": 1,
    })
    assert resp.status_code == 400


def test_missing_blank_idx_returns_400(client):
    hw_id = _seed_homework(client, mode="word_bank")
    resp = client.post("/api/ai/check-answer", json={
        "phase": "sentence-fill",
        "homework_id": hw_id,
        "item_id": "sf-001",
        "student_value": "one",
        "attempt_number": 1,
    })
    assert resp.status_code == 400


def test_blank_idx_out_of_range_returns_400(client):
    hw_id = _seed_homework(client, mode="word_bank")
    code, data = _post_check(
        client,
        homework_id=hw_id,
        blank_idx=99,
        student_value="x",
        attempt_number=1,
    )
    assert code == 400, data


def test_unknown_homework_id_returns_404(client):
    code, data = _post_check(
        client,
        homework_id="HW-DOES-NOT-EXIST",
        blank_idx=0,
        student_value="x",
        attempt_number=1,
    )
    assert code == 404, data


def test_unknown_item_id_returns_404(client):
    hw_id = _seed_homework(client, mode="word_bank")
    code, data = _post_check(
        client,
        homework_id=hw_id,
        item_id="sf-999",
        blank_idx=0,
        student_value="x",
        attempt_number=1,
    )
    assert code == 404, data


# ---------------------------------------------------------------------------
# Answer-leak guard — never echo the "answers" field key in the response body
# ---------------------------------------------------------------------------


def test_response_body_never_contains_answers_field(client):
    hw_id = _seed_homework(client, mode="word_bank")
    # Hit every state combination once; assert the literal key never leaks.
    for atype, value, atn in [
        ("correct", "one", 1),
        ("wrong-1", "zzz", 1),
        ("wrong-2", "qqq", 2),
    ]:
        resp = client.post("/api/ai/check-answer", json={
            "phase": "sentence-fill",
            "homework_id": hw_id,
            "item_id": "sf-001",
            "blank_idx": 0,
            "student_value": value,
            "attempt_number": atn,
        })
        body = resp.text
        # No JSON object key "answers" should appear in the response.
        assert not re.search(r'"answers"\s*:', body), (
            f"answers key leaked in response for {atype}: {body}"
        )


# ---------------------------------------------------------------------------
# Backward compat — non-sentence-fill phases unchanged
# ---------------------------------------------------------------------------


@patch("server.services.ai_orchestrator.generate_json")
def test_legacy_phase_path_still_works(mock_generate, client):
    """Smoke: a legacy phase request (no sentence-fill fields) still routes to
    tutor.check_answer and returns the deterministic shape."""
    payload = {
        "question_id": "q-legacy",
        "question": "2+2",
        "student_answer": "4",
        "answer_spec": {"type": "numeric", "expected": 4.0},
        "subject": "math-algebra",
        "grade": 8,
    }
    resp = client.post("/api/ai/check-answer", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["correct"] is True
    assert data.get("source") == "deterministic"
    mock_generate.assert_not_called()
