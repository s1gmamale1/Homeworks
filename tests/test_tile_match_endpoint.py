"""Regression tests for `/api/ai/check-answer` with phase=tile-match.

Pins the per-pair grading branch added in Chunk B:
- Correct match: base XP 100, speed bonus by timer tier, streak bonus on 3rds,
  palace bonus on Memory Palace tile, branch bonus on family complete.
- Wrong match: hint = LEFT-side text of the wrongly-picked right_id's TRUE
  partner; timer -5s; no XP.
- Outcome tiers on completion: perfect_clear (200) / flawless (100) / cleared (0).
- Back-compat gate: phase=tile-match WITHOUT homework_id falls through to
  legacy tutor.check_answer (no regression).
- Answer-leak guard: response on a CORRECT match never includes any other
  pair's right-side text.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

import server.routes.ai as _ai_routes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _wipe_tm_attempts():
    """Reset the in-memory tile-match attempt tracker between tests."""
    _ai_routes._TM_ATTEMPTS.clear()
    yield
    _ai_routes._TM_ATTEMPTS.clear()


def _seed_homework(
    client,
    *,
    pairs: list[dict] | None = None,
    grade: int = 8,
) -> str:
    """Insert a homework with a tile-match game and return its hw_id.

    Default `grade=8` (math-algebra band → 120s starting timer; well above the
    +50 speed-bonus threshold so the first match always lands in tier 50).
    Tests that need a smaller starting timer pre-seed `_TM_ATTEMPTS` directly.
    The endpoint uses `total_pairs = len(pairs)` regardless of the grade band.
    """
    if pairs is None:
        pairs = [
            {"id": "tm_001", "left": "F = ma", "right": "Newton's 2nd"},
            {"id": "tm_002", "left": "F1 = -F2", "right": "Newton's 3rd"},
            {"id": "tm_003", "left": "v = d/t", "right": "Velocity"},
            {"id": "tm_004", "left": "E = mc^2", "right": "Mass-energy"},
        ]
    payload = {
        "title": "TM check-answer test HW",
        "subject": "math-algebra",
        "grade": grade,
        "mode": "hard",
        "family": "aniq-fanlar",
        "content_json": {
            "meta": {"title": "TM check-answer test HW"},
            "panels": [],
            "flashcards": [],
            "boss_questions": [],
            "memory_sprint": [],
            "gb_tile_match": pairs,
        },
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _post_check(client, hw_id: str, **overrides) -> tuple[int, dict]:
    body = {
        "phase": "tile-match",
        "homework_id": hw_id,
        "left_id": overrides.pop("left_id", "tm_001"),
        "right_id": overrides.pop("right_id", "tm_001"),
        "session_id": overrides.pop("session_id", "sess-A"),
    }
    body.update(overrides)
    resp = client.post("/api/ai/check-answer", json=body)
    try:
        return resp.status_code, resp.json()
    except Exception:
        return resp.status_code, {"_raw": resp.text}


# ---------------------------------------------------------------------------
# 1. Correct + 2. Wrong baseline
# ---------------------------------------------------------------------------


def test_tm_check_answer_correct_pair_returns_correct_true_and_xp(client):
    hw_id = _seed_homework(client)
    code, data = _post_check(
        client, hw_id, left_id="tm_001", right_id="tm_001",
    )
    assert code == 200, data
    assert data["correct"] is True
    assert data["xp"]["base"] == 100
    assert data["xp"]["speed_bonus"] in (10, 30, 50)
    assert data["timer"]["delta_seconds"] == 3
    assert data["matched_count"] == 1
    assert data["total_pairs"] == 4


def test_tm_check_answer_same_pair_isolated_by_session_id(client):
    """A pair solved in one Tile Match run must still be correct in another run."""
    hw_id = _seed_homework(client)
    code, data = _post_check(
        client, hw_id, left_id="tm_001", right_id="tm_001", session_id="sess-A",
    )
    assert code == 200, data
    assert data["correct"] is True

    code, data = _post_check(
        client, hw_id, left_id="tm_001", right_id="tm_001", session_id="sess-B",
    )
    assert code == 200, data
    assert data["correct"] is True
    assert data["matched_count"] == 1


def test_tm_check_answer_wrong_pair_returns_correct_false_and_hint(client):
    hw_id = _seed_homework(client)
    code, data = _post_check(
        client, hw_id, left_id="tm_001", right_id="tm_002",
    )
    assert code == 200, data
    assert data["correct"] is False
    # The wrong-picked right-tile is tm_002 → its true partner's LEFT text.
    assert data["hint"] == "F1 = -F2"
    assert data["timer"]["delta_seconds"] == -5
    assert data["xp"]["base"] == 0
    assert data["xp"]["total"] == 0


# ---------------------------------------------------------------------------
# 3-5. Speed bonus tiers
# ---------------------------------------------------------------------------


def _seed_state(hw_id: str, *, remaining_seconds: int, session_id: str = "sess-A") -> None:
    """Pre-populate `_TM_ATTEMPTS` so a single match lands at the desired
    POST-delta timer threshold.

    Note: speed bonus is computed on the post-delta (+3 on correct) timer.
    To hit tier T after a correct match, seed the timer to T - 3.
    """
    _ai_routes._TM_ATTEMPTS[(hw_id, session_id)] = {
        "matched_pair_ids": set(),
        "wrong_count": 0,
        "streak": 0,
        "completed_families": set(),
        "remaining_seconds": remaining_seconds,
        "tier": "basic",
        "grade": 8,
        "total_pairs": 4,
    }


def test_tm_check_answer_speed_bonus_tier_50(client):
    hw_id = _seed_homework(client)  # default 180s → first match lands ≥50.
    code, data = _post_check(
        client, hw_id, left_id="tm_001", right_id="tm_001",
    )
    assert code == 200
    assert data["xp"]["speed_bonus"] == 50


def test_tm_check_answer_speed_bonus_tier_30(client):
    hw_id = _seed_homework(client)
    # Seed timer such that post-delta lands in [30, 49] → 35-3 = 32.
    _seed_state(hw_id, remaining_seconds=32)
    code, data = _post_check(
        client, hw_id, left_id="tm_001", right_id="tm_001",
    )
    assert code == 200
    # Post-delta remaining = 35 → tier 30.
    assert data["timer"]["remaining_seconds"] == 35
    assert data["xp"]["speed_bonus"] == 30


def test_tm_check_answer_speed_bonus_tier_10(client):
    hw_id = _seed_homework(client)
    # Seed timer to 10 → post-delta = 13 → tier 10.
    _seed_state(hw_id, remaining_seconds=10)
    code, data = _post_check(
        client, hw_id, left_id="tm_001", right_id="tm_001",
    )
    assert code == 200
    assert data["timer"]["remaining_seconds"] == 13
    assert data["xp"]["speed_bonus"] == 10


# ---------------------------------------------------------------------------
# 6-8. Streak bonus
# ---------------------------------------------------------------------------


def test_tm_check_answer_streak_bonus_basic_at_3(client):
    hw_id = _seed_homework(client)
    # Three correct matches in a row, all basic tier.
    for pid in ("tm_001", "tm_002", "tm_003"):
        code, data = _post_check(client, hw_id, left_id=pid, right_id=pid)
        assert code == 200
    # Last response is the 3rd correct.
    assert data["xp"]["streak_bonus"] == 50


def test_tm_check_answer_streak_bonus_premium_at_3(client):
    pairs = [
        {"id": "tm_001", "left": "F = ma", "right": "Newton's 2nd", "tier": "premium"},
        {"id": "tm_002", "left": "F1 = -F2", "right": "Newton's 3rd", "tier": "premium"},
        {"id": "tm_003", "left": "v = d/t", "right": "Velocity", "tier": "premium"},
        {"id": "tm_004", "left": "E = mc^2", "right": "Mass-energy", "tier": "premium"},
    ]
    hw_id = _seed_homework(client, pairs=pairs)
    for pid in ("tm_001", "tm_002", "tm_003"):
        code, data = _post_check(client, hw_id, left_id=pid, right_id=pid)
        assert code == 200
    assert data["xp"]["streak_bonus"] == 75


def test_tm_check_answer_streak_resets_on_wrong(client):
    hw_id = _seed_homework(client)
    # correct, correct, WRONG, correct, correct, correct → streak=3 only on
    # the final attempt.
    sequences = [
        ("tm_001", "tm_001", True),
        ("tm_002", "tm_002", True),
        ("tm_003", "tm_004", False),  # wrong → reset streak
        ("tm_003", "tm_003", True),   # streak now 1
        ("tm_004", "tm_004", True),   # streak now 2
    ]
    for left_id, right_id, expect_correct in sequences:
        code, data = _post_check(client, hw_id, left_id=left_id, right_id=right_id)
        assert code == 200, data
        assert data["correct"] is expect_correct
        # Pre-final attempts must NOT have streak bonus.
        assert data["xp"]["streak_bonus"] == 0


# ---------------------------------------------------------------------------
# 9. Palace bonus
# ---------------------------------------------------------------------------


def test_tm_check_answer_palace_bonus(client):
    pairs = [
        {
            "id": "tm_001", "left": "F = ma", "right": "Newton's 2nd",
            "tier": "premium", "is_palace_tile": True,
        },
        {"id": "tm_002", "left": "F1 = -F2", "right": "Newton's 3rd"},
        {"id": "tm_003", "left": "v = d/t", "right": "Velocity"},
        {"id": "tm_004", "left": "E = mc^2", "right": "Mass-energy"},
    ]
    hw_id = _seed_homework(client, pairs=pairs)
    code, data = _post_check(client, hw_id, left_id="tm_001", right_id="tm_001")
    assert code == 200
    assert data["xp"]["palace_bonus"] == 50


# ---------------------------------------------------------------------------
# 10. Branch bonus on concept_family complete
# ---------------------------------------------------------------------------


def test_tm_check_answer_branch_bonus_on_family_complete(client):
    pairs = [
        {"id": "tm_001", "left": "1/2", "right": "half", "concept_family": "fractions"},
        {"id": "tm_002", "left": "1/3", "right": "third", "concept_family": "fractions"},
        {"id": "tm_003", "left": "v = d/t", "right": "Velocity"},
        {"id": "tm_004", "left": "E = mc^2", "right": "Mass-energy"},
    ]
    hw_id = _seed_homework(client, pairs=pairs)
    # First fraction match — family not yet drained, no branch bonus.
    code, data = _post_check(client, hw_id, left_id="tm_001", right_id="tm_001")
    assert code == 200
    assert data["xp"]["branch_bonus"] == 0
    # Second fraction match — drains the family, branch bonus fires.
    code, data = _post_check(client, hw_id, left_id="tm_002", right_id="tm_002")
    assert code == 200
    assert data["xp"]["branch_bonus"] == 100


# ---------------------------------------------------------------------------
# 11-13. Outcome tiers on completion
# ---------------------------------------------------------------------------


def test_tm_check_answer_perfect_clear_outcome(client):
    hw_id = _seed_homework(client)
    pids = ["tm_001", "tm_002", "tm_003", "tm_004"]
    last = None
    for pid in pids:
        code, last = _post_check(client, hw_id, left_id=pid, right_id=pid)
        assert code == 200
    assert last["complete"] is True
    assert last["outcome"] == "perfect_clear"
    assert last["completion_bonus_xp"] == 200
    assert last["matched_count"] == 4
    assert last["total_pairs"] == 4


def test_tm_check_answer_flawless_outcome(client):
    hw_id = _seed_homework(client)
    # One wrong attempt up front, then clear all 4.
    _post_check(client, hw_id, left_id="tm_001", right_id="tm_002")  # wrong
    pids = ["tm_001", "tm_002", "tm_003", "tm_004"]
    last = None
    for pid in pids:
        code, last = _post_check(client, hw_id, left_id=pid, right_id=pid)
        assert code == 200
    assert last["complete"] is True
    assert last["outcome"] == "flawless"
    assert last["completion_bonus_xp"] == 100


def test_tm_check_answer_cleared_outcome(client):
    hw_id = _seed_homework(client)
    # Two wrong attempts, then clear.
    _post_check(client, hw_id, left_id="tm_001", right_id="tm_002")  # wrong
    _post_check(client, hw_id, left_id="tm_002", right_id="tm_003")  # wrong
    pids = ["tm_001", "tm_002", "tm_003", "tm_004"]
    last = None
    for pid in pids:
        code, last = _post_check(client, hw_id, left_id=pid, right_id=pid)
        assert code == 200
    assert last["complete"] is True
    assert last["outcome"] == "cleared"
    assert last["completion_bonus_xp"] == 0


# ---------------------------------------------------------------------------
# 14. Back-compat — phase=tile-match without homework_id falls through.
# ---------------------------------------------------------------------------


@patch("server.services.ai_orchestrator.generate_json")
def test_tm_check_answer_legacy_route_back_compat(mock_generate, client):
    """phase=tile-match WITHOUT homework_id flows through tutor.check_answer
    (legacy AMR-shape path) — guards against the new branch swallowing
    pre-existing callers.
    """
    payload = {
        "phase": "tile-match",
        # NO homework_id — must fall through to legacy.
        "question_id": "q-legacy-tm",
        "question": "What is 2+2?",
        "student_answer": "4",
        "answer_spec": {"type": "numeric", "expected": 4.0},
        "subject": "math-algebra",
        "grade": 8,
    }
    resp = client.post("/api/ai/check-answer", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # Legacy shape — no `xp.speed_bonus`, no `timer`, etc.
    assert "speed_bonus" not in (data.get("xp") or {})
    assert "timer" not in data
    assert data.get("source") == "deterministic"
    mock_generate.assert_not_called()


# ---------------------------------------------------------------------------
# 15. Answer-leak guard
# ---------------------------------------------------------------------------


def test_tm_check_answer_no_answer_leak_in_response(client):
    """Response on a CORRECT match must never echo other pairs' right-side text."""
    pairs = [
        {"id": "tm_001", "left": "F = ma", "right": "Newton's 2nd"},
        {"id": "tm_002", "left": "F1 = -F2", "right": "ZebraJellyZap"},  # distinctive
        {"id": "tm_003", "left": "v = d/t", "right": "QuokkaPineNebula"},  # distinctive
        {"id": "tm_004", "left": "E = mc^2", "right": "VelvetIceTroika"},  # distinctive
    ]
    hw_id = _seed_homework(client, pairs=pairs)
    resp = client.post("/api/ai/check-answer", json={
        "phase": "tile-match",
        "homework_id": hw_id,
        "left_id": "tm_001",
        "right_id": "tm_001",
        "session_id": "sess-leak",
    })
    body = resp.text
    for leak_token in ("ZebraJellyZap", "QuokkaPineNebula", "VelvetIceTroika"):
        assert leak_token not in body, (
            f"answer leak: {leak_token!r} appeared in response body: {body!r}"
        )
    # The matched pair's own RIGHT text is also not in the response (it was
    # already in the DOM as a tile, but the endpoint shouldn't re-echo it).
    assert "Newton's 2nd" not in body
