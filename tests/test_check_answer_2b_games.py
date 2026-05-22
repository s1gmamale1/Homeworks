"""Regression — POST /api/ai/check-answer for the Phase-2B practice games.

Covers the three new server-side graders:
  - phase=adaptive-quiz  → content_json["gb_adaptive_quiz"]
  - phase=mystery-box    → content_json["gb_mystery_box"]
  - phase=puzzle-lock    → content_json["gb_puzzle_lock"]

For EACH phase this file pins:
  - correct answer            → 200, {correct: true}
  - wrong answer              → {correct: false} AND no expected value in body
  - locked Practice Arc       → 403 PRACTICE_LOCKED (server-enforced, not UI)
  - item_index out of range   → 400
  - no-leak                   → the distinctive expected string is NEVER echoed
    anywhere in the response body, even on a wrong answer.

All three are practice-arc games, so they share the BLOCKER #3 server gate.
The grading tests patch `server.routes.ai.is_practice_unlocked` to always-True
(matching tests/test_tile_match_endpoint.py) so they exercise the grader rather
than the 403 guard; the dedicated locked-gate tests leave the real gate in
place (a fresh homework has zero CBP/MC progress → arc locked).

Harness/seed pattern follows tests/test_check_answer_v2_phases.py and the
autouse-unlock fixture from tests/test_tile_match_endpoint.py.
"""
from __future__ import annotations

import asyncio
import json

import pytest


# A distinctive accepted-answer string we can grep the response body for to
# prove the expected value never leaks. Chosen so it cannot collide with the
# generic feedback strings.
_LEAK_SENTINEL = "Zxq_secret_answer_42"


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

def _seed_2b_homework(client) -> str:
    """Create a homework carrying all three Phase-2B game arrays.

    Each array's item 0 has an authored answer_spec; item 1 uses the bare
    answer-field path (`a` / accepted_answers) to exercise the on-the-fly
    text_fuzzy spec builder. The distinctive sentinel is the accepted answer
    for the bare-field items so a leak test can grep for it.
    """
    payload = {
        "title": "2B games check-answer test HW",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
        "family": "aniq-fanlar",
        "content_json": {
            "meta": {"title": "2B games check-answer test HW"},
            "flashcards": [],
            "boss_questions": [],
            "gb_adaptive_quiz": [
                {
                    "q": "What is 2 + 2?",
                    "answer_spec": {"type": "text_fuzzy", "expected": _LEAK_SENTINEL},
                },
                {
                    "q": "Capital of France?",
                    "accepted_answers": ["Paris", "paris"],
                },
            ],
            "gb_mystery_box": [
                {
                    "q": "Hidden value?",
                    "answer_spec": {"type": "text_fuzzy", "expected": _LEAK_SENTINEL},
                },
                {"q": "Mystery word?", "a": "banana"},
            ],
            "gb_puzzle_lock": [
                {
                    "q": "Unlock code?",
                    "answer_spec": {"type": "text_fuzzy", "expected": _LEAK_SENTINEL},
                },
                {"q": "Lock answer?", "a": "cipher"},
            ],
        },
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, f"Seed failed: {resp.text}"
    return resp.json()["id"]


def _post(client, phase: str, hw_id: str, item_index, student_answer: str, **extra):
    body = {
        "phase": phase,
        "homework_id": hw_id,
        "item_index": item_index,
        "student_answer": student_answer,
        "session_id": extra.pop("session_id", f"test-2b-{phase}"),
        **extra,
    }
    resp = client.post("/api/ai/check-answer", json=body)
    try:
        return resp.status_code, resp.json()
    except Exception:
        return resp.status_code, {"_raw": resp.text}


# ---------------------------------------------------------------------------
# Gate-unlock fixture for the GRADING tests (locked-gate tests opt out).
# ---------------------------------------------------------------------------

async def _always_unlocked(*a, **k):
    return True


@pytest.fixture
def unlock_practice(monkeypatch):
    """Patch the server-side Practice Arc gate to always pass.

    Patches the symbol AS IMPORTED into ai.py so the grader runs without the
    403 guard. Not autouse — the locked-gate tests need the real gate.
    """
    monkeypatch.setattr("server.routes.ai.is_practice_unlocked", _always_unlocked)


# Per-phase parametrize spec: (phase, correct_answer, wrong_answer).
# `correct_answer` matches item 0's authored answer_spec (the sentinel);
# `wrong_answer` is a value guaranteed to miss.
_PHASES = [
    ("adaptive-quiz", _LEAK_SENTINEL, "totally_wrong_xyz"),
    ("mystery-box", _LEAK_SENTINEL, "totally_wrong_xyz"),
    ("puzzle-lock", _LEAK_SENTINEL, "totally_wrong_xyz"),
]


# ---------------------------------------------------------------------------
# Correct answer → 200 / correct: true
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("phase,correct,wrong", _PHASES)
def test_2b_correct_answer_returns_correct_true(client, unlock_practice, phase, correct, wrong):
    hw_id = _seed_2b_homework(client)
    code, data = _post(client, phase, hw_id, item_index=0, student_answer=correct)
    assert code == 200, data
    assert data["correct"] is True, data
    assert "feedback" in data, data


@pytest.mark.parametrize("phase", ["adaptive-quiz", "mystery-box", "puzzle-lock"])
def test_2b_bare_answer_field_grades_correct(client, unlock_practice, phase):
    """Item 1 has NO authored answer_spec — the on-the-fly text_fuzzy spec
    (from `a` / accepted_answers) must still grade a correct answer."""
    hw_id = _seed_2b_homework(client)
    expected_by_phase = {
        "adaptive-quiz": "Paris",
        "mystery-box": "banana",
        "puzzle-lock": "cipher",
    }
    code, data = _post(client, phase, hw_id, item_index=1, student_answer=expected_by_phase[phase])
    assert code == 200, data
    assert data["correct"] is True, data


# ---------------------------------------------------------------------------
# Wrong answer → correct: false + NO expected value in body
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("phase,correct,wrong", _PHASES)
def test_2b_wrong_answer_returns_correct_false_no_leak(client, unlock_practice, phase, correct, wrong):
    hw_id = _seed_2b_homework(client)
    code, data = _post(client, phase, hw_id, item_index=0, student_answer=wrong)
    assert code == 200, data
    assert data["correct"] is False, data
    # The expected value (sentinel) must NEVER appear anywhere in the response.
    assert _LEAK_SENTINEL not in json.dumps(data), f"expected value leaked: {data}"
    assert data.get("expected") is None, data


@pytest.mark.parametrize("phase", ["adaptive-quiz", "mystery-box", "puzzle-lock"])
def test_2b_bare_field_wrong_answer_no_leak(client, unlock_practice, phase):
    """Wrong answer against the bare-answer-field item must not leak its value."""
    hw_id = _seed_2b_homework(client)
    code, data = _post(client, phase, hw_id, item_index=1, student_answer="definitely_not_it")
    assert code == 200, data
    assert data["correct"] is False, data
    body = json.dumps(data)
    for leaked in ("Paris", "banana", "cipher"):
        assert leaked not in body, f"{leaked} leaked into {phase} response: {data}"


# ---------------------------------------------------------------------------
# Locked Practice Arc → 403 PRACTICE_LOCKED (real gate, NOT patched)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("phase,correct,wrong", _PHASES)
def test_2b_locked_gate_returns_403_practice_locked(client, phase, correct, wrong):
    """A fresh homework has zero CBP/MC progress → arc locked → 403 BEFORE
    grading. No gate monkeypatch here (we want the real server enforcement)."""
    hw_id = _seed_2b_homework(client)
    code, data = _post(client, phase, hw_id, item_index=0, student_answer=correct)
    assert code == 403, data
    detail = data.get("detail", data)
    assert isinstance(detail, dict) and detail.get("code") == "PRACTICE_LOCKED", data


# ---------------------------------------------------------------------------
# item_index out of range → 400
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("phase,correct,wrong", _PHASES)
def test_2b_item_index_out_of_range_returns_400(client, unlock_practice, phase, correct, wrong):
    hw_id = _seed_2b_homework(client)
    code, data = _post(client, phase, hw_id, item_index=99, student_answer=correct)
    assert code == 400, data


@pytest.mark.parametrize("phase,correct,wrong", _PHASES)
def test_2b_negative_item_index_returns_400(client, unlock_practice, phase, correct, wrong):
    hw_id = _seed_2b_homework(client)
    code, data = _post(client, phase, hw_id, item_index=-1, student_answer=correct)
    assert code == 400, data


@pytest.mark.parametrize("phase", ["adaptive-quiz", "mystery-box", "puzzle-lock"])
def test_2b_missing_item_index_returns_400(client, unlock_practice, phase):
    hw_id = _seed_2b_homework(client)
    resp = client.post("/api/ai/check-answer", json={
        "phase": phase,
        "homework_id": hw_id,
        "student_answer": "x",
        # item_index deliberately omitted
    })
    assert resp.status_code == 400, resp.text


# ---------------------------------------------------------------------------
# Persistence — a phase_attempts row is written with the server-derived subphase
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("phase,correct,wrong", _PHASES)
def test_2b_phase_attempt_written_with_item_subphase(client, unlock_practice, phase, correct, wrong):
    from server.db.attempts_repo import list_phase_attempts

    hw_id = _seed_2b_homework(client)
    session_id = f"test-2b-persist-{phase}"
    code, data = _post(client, phase, hw_id, item_index=0, student_answer=correct, session_id=session_id)
    assert code == 200, data

    loop = asyncio.new_event_loop()
    try:
        attempts = loop.run_until_complete(
            list_phase_attempts(session_id, hw_id, phase=phase)
        )
    finally:
        loop.close()

    assert len(attempts) >= 1, f"No phase_attempts row written for {phase}"
    row = attempts[0]
    assert row["phase"] == phase
    assert row["subphase"] == "item_0"
    assert row["correct"] == 1
    # The persisted answer_spec marker for the on-the-fly path never carries
    # the expected value; for item 0 the authored spec DOES carry it in the
    # spec column (server-side audit only, never returned to the client).


# ---------------------------------------------------------------------------
# 404 — homework / array missing
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("phase", ["adaptive-quiz", "mystery-box", "puzzle-lock"])
def test_2b_unknown_homework_returns_404(client, unlock_practice, phase):
    code, data = _post(client, phase, "nonexistent-hw-id", item_index=0, student_answer="x")
    assert code == 404, data


@pytest.mark.parametrize("phase", ["adaptive-quiz", "mystery-box", "puzzle-lock"])
def test_2b_missing_array_returns_404(client, unlock_practice, phase):
    """A homework with no 2B arrays at all → 404 (array missing)."""
    payload = {
        "title": "2B empty HW",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
        "content_json": {"meta": {"title": "2B empty HW"}, "flashcards": []},
    }
    hw_id = client.post("/api/homeworks", json=payload).json()["id"]
    code, data = _post(client, phase, hw_id, item_index=0, student_answer="x")
    assert code == 404, data
