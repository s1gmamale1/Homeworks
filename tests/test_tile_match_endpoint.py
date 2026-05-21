"""Regression tests for `/api/ai/check-answer` with phase=tile-match.

Pins the per-pair grading branch (Chunk B) AFTER the opaque-token rewrite:
- The board no longer ships shared pair ids; the client sends opaque per-side
  tokens (`left_token`/`right_token`) and the grader recovers the pair index
  via HMAC and grades by `left_index == right_index`. These tests therefore
  address pairs by INDEX (tm_001→0 … tm_004→3) and translate to tokens.
- Correct match: base XP 100, speed bonus by timer tier, streak bonus on 3rds,
  palace bonus on Memory Palace tile, branch bonus on family complete.
- Wrong match: hint = LEFT-side text of the wrongly-picked right-token's TRUE
  partner; timer -5s; no XP.
- Outcome tiers on completion: perfect_clear (200) / flawless (100) / cleared (0).
- Back-compat gate: phase=tile-match WITHOUT homework_id falls through to
  legacy tutor.check_answer (no regression) — never reaches the practice gate.
- Answer-leak guard: response on a CORRECT match never includes any other
  pair's right-side text.

The practice-arc unlock check is patched always-True here (these are XP/streak/
outcome unit tests, not gating tests; the gate itself is pinned by
tests/test_practice_gate_server_enforced.py).
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

import server.routes.ai as _ai_routes
from server.services.tile_match_tokens import left_token, right_token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# The default board orders tm_001..tm_004 at indices 0..3. The grader keys off
# the canonical pair index (resolve_tm_pairs ordering), so tests address pairs
# by their authored ordinal and translate to opaque tokens at the boundary.
_PID_INDEX = {"tm_001": 0, "tm_002": 1, "tm_003": 2, "tm_004": 3}


async def _always_unlocked(*a, **k):
    return True


@pytest.fixture(autouse=True)
def _unlock_practice_arc(monkeypatch):
    """These are grading unit tests, not gating tests — make the server-side
    Practice Arc unlock check always pass so they exercise the grader, not the
    403 PRACTICE_LOCKED guard. Patches the symbol as imported into ai.py."""
    monkeypatch.setattr("server.routes.ai.is_practice_unlocked", _always_unlocked)


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
    """POST a tile-match check.

    Accepts either authored pair ids (`tm_00X`, translated to opaque tokens) or
    explicit integer indices via `left_idx`/`right_idx`. Defaults to a correct
    match on pair index 0.
    """
    left_idx = overrides.pop("left_idx", None)
    right_idx = overrides.pop("right_idx", None)
    if left_idx is None:
        left_idx = _PID_INDEX[overrides.pop("left_id", "tm_001")]
    else:
        overrides.pop("left_id", None)
    if right_idx is None:
        right_idx = _PID_INDEX[overrides.pop("right_id", "tm_001")]
    else:
        overrides.pop("right_id", None)

    body = {
        "phase": "tile-match",
        "homework_id": hw_id,
        "left_id": left_token(hw_id, left_idx),
        "right_id": right_token(hw_id, right_idx),
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
    # The wrong-picked right-tile is pair 1 (tm_002) → its true partner's LEFT
    # text (pairs[1]['left']).
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
    `matched_pair_ids` is now keyed by canonical pair INDEX (int), not id.
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
    # correct, correct, WRONG, correct, correct → streak resets on the wrong
    # match, so no pre-final attempt earns a streak bonus.
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
    pre-existing callers. This path never reaches the practice gate.
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
        "left_id": left_token(hw_id, 0),
        "right_id": right_token(hw_id, 0),
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


# ---------------------------------------------------------------------------
# 16. matched_tokens + already_matched (PR-5 rehydrate-on-response fix)
# ---------------------------------------------------------------------------


def test_tm_response_echoes_matched_tokens_after_each_correct_match(client):
    """The grader echoes the per-side tokens of every currently-matched pair on
    every response, so the React component can re-sync its display state in one
    round-trip after a page reload (where the in-memory _TM_ATTEMPTS dict
    survives but React's local matched-set remounts empty)."""
    hw_id = _seed_homework(client)

    # Match tm_001 first.
    code, data = _post_check(client, hw_id, left_id="tm_001", right_id="tm_001")
    assert code == 200, data
    assert data["correct"] is True
    assert data["already_matched"] is False
    tokens = data["matched_tokens"]
    assert isinstance(tokens, list) and len(tokens) == 1
    assert tokens[0] == {
        "lid": left_token(hw_id, 0),
        "rid": right_token(hw_id, 0),
    }

    # Match tm_002 next — response now lists BOTH matched pairs.
    code, data = _post_check(client, hw_id, left_id="tm_002", right_id="tm_002")
    assert code == 200, data
    assert data["correct"] is True
    tokens = sorted(data["matched_tokens"], key=lambda t: t["lid"])
    assert len(tokens) == 2
    assert {t["lid"] for t in tokens} == {
        left_token(hw_id, 0),
        left_token(hw_id, 1),
    }
    assert {t["rid"] for t in tokens} == {
        right_token(hw_id, 0),
        right_token(hw_id, 1),
    }


def test_tm_replay_against_already_matched_pair_flags_already_matched(client):
    """A second submit against a pair already in matched_pair_ids must return
    `already_matched: true` (distinguishes from a true wrong-pair miss so the
    React UI doesn't flash the wrong-state for what is effectively a no-op).
    The matched_tokens list stays stable across the replay."""
    hw_id = _seed_homework(client)

    # First submit on tm_001: correct.
    code, data = _post_check(client, hw_id, left_id="tm_001", right_id="tm_001")
    assert code == 200, data
    assert data["correct"] is True
    assert data["already_matched"] is False
    first_tokens = data["matched_tokens"]

    # Second submit on the SAME pair (simulates a reload-after-match where
    # React's local state was empty but the server still holds the match).
    code, data = _post_check(client, hw_id, left_id="tm_001", right_id="tm_001")
    assert code == 200, data
    # The pair was already matched server-side → not a "new" correct match.
    assert data["correct"] is False
    assert data["already_matched"] is True
    # Token echo is stable — the React component can re-sync from this list.
    assert data["matched_tokens"] == first_tokens


def test_tm_matched_tokens_emits_only_opaque_tokens_no_answer_leak(client):
    """The new matched_tokens field must NOT smuggle right-side text or pair
    indices into the response. Only the per-side HMAC tokens (`L<mac>`/`R<mac>`)
    are allowed — those carry no information beyond what was already in the
    hydration payload."""
    pairs = [
        {"id": "tm_001", "left": "F = ma", "right": "Newton's 2nd"},
        {"id": "tm_002", "left": "F1 = -F2", "right": "ZebraJellyZap"},
        {"id": "tm_003", "left": "v = d/t", "right": "QuokkaPineNebula"},
        {"id": "tm_004", "left": "E = mc^2", "right": "VelvetIceTroika"},
    ]
    hw_id = _seed_homework(client, pairs=pairs)
    # Match two distinct pairs so matched_tokens has 2 entries to inspect.
    _post_check(client, hw_id, left_id="tm_001", right_id="tm_001")
    code, data = _post_check(client, hw_id, left_id="tm_002", right_id="tm_002")
    assert code == 200, data
    tokens = data["matched_tokens"]
    assert len(tokens) == 2
    for t in tokens:
        # Shape is exactly the two opaque-token fields, nothing else.
        assert set(t.keys()) == {"lid", "rid"}
        assert t["lid"].startswith("L") and len(t["lid"]) == 13  # L + 12-char hmac
        assert t["rid"].startswith("R") and len(t["rid"]) == 13
    # Distinctive right-side text from OTHER pairs must not appear anywhere.
    body_str = str(data)
    for leak_token in ("ZebraJellyZap", "QuokkaPineNebula", "VelvetIceTroika"):
        assert leak_token not in body_str
