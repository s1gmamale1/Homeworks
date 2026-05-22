"""Regression — BLOCKER #3: Practice Arc is SERVER-enforced, not just UI-gated.

The practice-arc games (phase `tile-match`, `final-boss`, future games) used to
grade an answer without verifying the student actually unlocked the arc. A
tampered client could call the check-answer endpoints directly after hydrating
display content.

The fix calls `is_practice_unlocked(session_id, homework_id)` BEFORE grading in
the practice-arc check-answer branches; a locked session gets
HTTPException(403, code="PRACTICE_LOCKED"). The CBP/MC learning phases (the
unlock path itself) are NOT gated.

These tests monkeypatch the gate (and the opaque tile-match token helpers) in
the `server.routes.ai` namespace so they are independent of the parallel agent's
module internals — they only require the imports to resolve. Harness/monkeypatch
pattern follows tests/test_check_answer_v2_phases.py + tests/test_v2_gate_flow.py.
"""
from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from server.routes import ai as ai_routes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    """Drive an async grader to completion in a fresh event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _locked_gate(session_id, hw_id):
    return False


async def _unlocked_gate(session_id, hw_id):
    return True


def _seed_tile_match_hw(client) -> str:
    """Create a homework carrying a simple tile-match board."""
    hw = client.post(
        "/api/homeworks",
        json={"title": "TM gate HW", "subject": "math-algebra", "grade": 6, "mode": "hard"},
    ).json()
    hw_id = hw["id"]
    content = {
        "flow_version": "v2",
        "meta": {"title": "TM gate HW"},
        "gb_tile_match": [
            {"id": "p0", "left": "2+2", "right": "4", "tier": "basic"},
            {"id": "p1", "left": "3+3", "right": "6", "tier": "basic"},
        ],
    }
    assert client.put(f"/api/homeworks/{hw_id}", json={"content_json": content}).status_code == 200
    return hw_id


def _tm_req(hw_id: str):
    return ai_routes.CheckAnswerRequest(
        phase="tile-match",
        homework_id=hw_id,
        session_id="tm-locked-sess",
        left_id="L0",
        right_id="R0",
    )


def _fb_req(hw_id: str):
    return ai_routes.CheckAnswerRequest(
        phase="final-boss",
        homework_id=hw_id,
        session_id="fb-locked-sess",
        question_id="bq_0",
        student_answer="x = 3",
    )


# ---------------------------------------------------------------------------
# Tile Match — locked session is refused before grading
# ---------------------------------------------------------------------------

def test_tile_match_locked_session_raises_403_practice_locked(client, monkeypatch):
    hw_id = _seed_tile_match_hw(client)
    monkeypatch.setattr(ai_routes, "is_practice_unlocked", _locked_gate)

    with pytest.raises(HTTPException) as ei:
        _run(ai_routes._check_answer_tile_match(_tm_req(hw_id)))

    assert ei.value.status_code == 403
    assert ei.value.detail["code"] == "PRACTICE_LOCKED"


def test_tile_match_unlocked_session_proceeds_to_grading(client, monkeypatch):
    """With the gate stubbed True + opaque-token maps stubbed, grading proceeds.

    We stub `resolve_tm_pairs` / `build_token_maps` so this test does not depend
    on the parallel agent's resolver internals — it verifies the gate no longer
    blocks and the opaque-token lookup path produces a graded result.
    """
    hw_id = _seed_tile_match_hw(client)
    monkeypatch.setattr(ai_routes, "is_practice_unlocked", _unlocked_gate)

    pairs = [
        {"left": "2+2", "right": "4", "tier": "basic"},
        {"left": "3+3", "right": "6", "tier": "basic"},
    ]
    monkeypatch.setattr(ai_routes, "resolve_tm_pairs", lambda content: pairs)
    # Opaque tokens → pair index. L0/R0 both map to index 0 (a correct match).
    lid_map = {"L0": 0, "L1": 1}
    rid_map = {"R0": 0, "R1": 1}
    monkeypatch.setattr(
        ai_routes, "build_token_maps", lambda hw, n: (lid_map, rid_map)
    )

    result = _run(ai_routes._check_answer_tile_match(_tm_req(hw_id)))
    assert result["correct"] is True, result
    assert result["xp"]["base"] == 100, result


def test_tile_match_unlocked_wrong_match_hint_is_true_partner_left(client, monkeypatch):
    """On a WRONG match the hint is the wrongly-picked right tile's TRUE partner
    left text — already on screen, not a new leak."""
    hw_id = _seed_tile_match_hw(client)
    monkeypatch.setattr(ai_routes, "is_practice_unlocked", _unlocked_gate)

    pairs = [
        {"left": "2+2", "right": "4", "tier": "basic"},
        {"left": "3+3", "right": "6", "tier": "basic"},
    ]
    monkeypatch.setattr(ai_routes, "resolve_tm_pairs", lambda content: pairs)
    # left tile of pair 0, but right tile of pair 1 → wrong.
    monkeypatch.setattr(
        ai_routes, "build_token_maps", lambda hw, n: ({"L0": 0}, {"R1": 1})
    )

    req = ai_routes.CheckAnswerRequest(
        phase="tile-match", homework_id=hw_id, session_id="tm-wrong-sess",
        left_id="L0", right_id="R1",
    )
    result = _run(ai_routes._check_answer_tile_match(req))
    assert result["correct"] is False, result
    assert result["hint"] == "3+3", result  # pair 1's left text


# ---------------------------------------------------------------------------
# Final Boss — locked session is refused before grading
# ---------------------------------------------------------------------------

def test_final_boss_locked_session_raises_403_practice_locked(client, monkeypatch):
    # The 403 gate fires immediately after the homework_id presence check and
    # BEFORE any content/board resolution, so a bare existing homework suffices.
    hw = client.post(
        "/api/homeworks",
        json={"title": "FB gate HW", "subject": "math-algebra", "grade": 6, "mode": "hard"},
    ).json()
    hw_id = hw["id"]

    monkeypatch.setattr(ai_routes, "is_practice_unlocked", _locked_gate)

    with pytest.raises(HTTPException) as ei:
        _run(ai_routes._check_answer_final_boss(_fb_req(hw_id)))

    assert ei.value.status_code == 403
    assert ei.value.detail["code"] == "PRACTICE_LOCKED"


# ---------------------------------------------------------------------------
# Gate consistency — the OTHER practice-arc games are now server-gated too.
#
# Each game's check-answer branch must raise 403 PRACTICE_LOCKED for a locked
# session BEFORE grading. The gate is placed after the 400 field-presence
# checks and before homework resolution, so each request below populates the
# minimum fields required to clear validation but supplies a bare (existing)
# homework — the gate fires regardless of its content.
# ---------------------------------------------------------------------------

def _bare_hw(client, title: str) -> str:
    return client.post(
        "/api/homeworks",
        json={"title": title, "subject": "math-algebra", "grade": 6, "mode": "hard"},
    ).json()["id"]


def test_sentence_fill_locked_session_raises_403_practice_locked(client, monkeypatch):
    hw_id = _bare_hw(client, "SF gate HW")
    monkeypatch.setattr(ai_routes, "is_practice_unlocked", _locked_gate)
    req = ai_routes.CheckAnswerRequest(
        phase="sentence-fill", homework_id=hw_id, session_id="sf-locked-sess",
        item_id="sf_0", blank_idx=0, student_value="x",
    )
    with pytest.raises(HTTPException) as ei:
        _run(ai_routes._check_answer_sentence_fill(req))
    assert ei.value.status_code == 403
    assert ei.value.detail["code"] == "PRACTICE_LOCKED"


def test_real_life_challenge_locked_session_raises_403_practice_locked(client, monkeypatch):
    hw_id = _bare_hw(client, "RLC gate HW")
    monkeypatch.setattr(ai_routes, "is_practice_unlocked", _locked_gate)
    req = ai_routes.CheckAnswerRequest(
        phase="real-life-challenge", homework_id=hw_id, session_id="rlc-locked-sess",
        step_id="step_1", selected_option_id="opt_a",
    )
    with pytest.raises(HTTPException) as ei:
        _run(ai_routes._check_answer_real_life_challenge(req))
    assert ei.value.status_code == 403
    assert ei.value.detail["code"] == "PRACTICE_LOCKED"


def test_ttt_locked_session_raises_403_practice_locked(client, monkeypatch):
    hw_id = _bare_hw(client, "TTT gate HW")
    monkeypatch.setattr(ai_routes, "is_practice_unlocked", _locked_gate)
    req = ai_routes.CheckAnswerRequest(
        phase="ttt", homework_id=hw_id, session_id="ttt-locked-sess",
        item_id="ttt_0", picked="42",
    )
    with pytest.raises(HTTPException) as ei:
        _run(ai_routes._check_answer_ttt(req))
    assert ei.value.status_code == 403
    assert ei.value.detail["code"] == "PRACTICE_LOCKED"


def test_ttt_session_locked_session_raises_403_practice_locked(client, monkeypatch):
    hw_id = _bare_hw(client, "TTT-session gate HW")
    monkeypatch.setattr(ai_routes, "is_practice_unlocked", _locked_gate)
    req = ai_routes.CheckAnswerRequest(
        phase="ttt-session", homework_id=hw_id, session_id="ttts-locked-sess",
        results=[{"outcome": "win"}, {"outcome": "draw"}, {"outcome": "loss"}],
    )
    with pytest.raises(HTTPException) as ei:
        _run(ai_routes._check_answer_ttt_session(req))
    assert ei.value.status_code == 403
    assert ei.value.detail["code"] == "PRACTICE_LOCKED"


def test_memory_palace_locked_session_raises_403_practice_locked(client, monkeypatch):
    hw_id = _bare_hw(client, "MP gate HW")
    monkeypatch.setattr(ai_routes, "is_practice_unlocked", _locked_gate)
    req = ai_routes.CheckAnswerRequest(
        phase="memory-palace", homework_id=hw_id, session_id="mp-locked-sess",
        palace_key="route_0",
        placements=[{"location_idx": 0, "concept_id": "c0"}],
        recall_results=[{"location_idx": 0, "picked_concept_id": "c0", "elapsed_ms": 100}],
    )
    with pytest.raises(HTTPException) as ei:
        _run(ai_routes._check_answer_memory_palace(req))
    assert ei.value.status_code == 403
    assert ei.value.detail["code"] == "PRACTICE_LOCKED"


# ---------------------------------------------------------------------------
# The three NEW Phase-2B games are server-gated as well.
# ---------------------------------------------------------------------------

def test_adaptive_quiz_locked_session_raises_403_practice_locked(client, monkeypatch):
    hw_id = _bare_hw(client, "AQ gate HW")
    monkeypatch.setattr(ai_routes, "is_practice_unlocked", _locked_gate)
    req = ai_routes.CheckAnswerRequest(
        phase="adaptive-quiz", homework_id=hw_id, session_id="aq-locked-sess",
        item_index=0, student_answer="x",
    )
    with pytest.raises(HTTPException) as ei:
        _run(ai_routes._check_answer_adaptive_quiz(req))
    assert ei.value.status_code == 403
    assert ei.value.detail["code"] == "PRACTICE_LOCKED"


def test_mystery_box_locked_session_raises_403_practice_locked(client, monkeypatch):
    hw_id = _bare_hw(client, "MB gate HW")
    monkeypatch.setattr(ai_routes, "is_practice_unlocked", _locked_gate)
    req = ai_routes.CheckAnswerRequest(
        phase="mystery-box", homework_id=hw_id, session_id="mb-locked-sess",
        item_index=0, student_answer="x",
    )
    with pytest.raises(HTTPException) as ei:
        _run(ai_routes._check_answer_mystery_box(req))
    assert ei.value.status_code == 403
    assert ei.value.detail["code"] == "PRACTICE_LOCKED"


def test_puzzle_lock_locked_session_raises_403_practice_locked(client, monkeypatch):
    hw_id = _bare_hw(client, "PL gate HW")
    monkeypatch.setattr(ai_routes, "is_practice_unlocked", _locked_gate)
    req = ai_routes.CheckAnswerRequest(
        phase="puzzle-lock", homework_id=hw_id, session_id="pl-locked-sess",
        item_index=0, student_answer="x",
    )
    with pytest.raises(HTTPException) as ei:
        _run(ai_routes._check_answer_puzzle_lock(req))
    assert ei.value.status_code == 403
    assert ei.value.detail["code"] == "PRACTICE_LOCKED"
