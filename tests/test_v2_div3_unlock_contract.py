"""Regression contract: Division-3 frontend unlock choreography.

These tests pin the server-side contract that the new hub-based unlock flow
depends on after the UnlockGate screen is deleted and unlock is moved onto the
Learning Hub node itself.

Contract summary (must NOT change without updating the frontend):
  - practice_arc_unlocked = cbp_passed AND mc_passed  (AND gate, server-computed)
  - CBP threshold: max(2, ceil(0.6 * total_checkpoints)) correct
  - MC  threshold: score_pct >= pass_threshold_pct (default 60%)
  - Aggregation keys on server-derived subphase, never client question_id
  - Practice-arc graders (tile-match, etc.) return HTTP 403 PRACTICE_LOCKED
    for any session that is not yet unlocked — the server enforces the gate
    independently of the frontend routing change.

Fixtures/patterns mirror tests/test_v2_gate_flow.py and
tests/test_practice_gate_server_enforced.py (the two sibling suites).
"""
from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from server.routes import ai as ai_routes


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_v2_homework(client) -> str:
    """Create a minimal v2 homework with 3 CBP checkpoints + 3 MC items."""
    hw = client.post(
        "/api/homeworks",
        json={"title": "Div3 unlock contract HW", "subject": "math-algebra",
              "grade": 6, "mode": "hard"},
    ).json()
    hw_id = hw["id"]
    content = {
        "flow_version": "v2",
        "meta": {"title": "Div3 unlock contract HW"},
        "case_based_preview": {
            "checkpoints": [
                {"question": "Q1", "options": ["a", "b"],
                 "answer_spec": {"type": "option_index", "expected": 1, "option_count": 2}},
                {"question": "Q2", "options": ["a", "b"],
                 "answer_spec": {"type": "option_index", "expected": 0, "option_count": 2}},
                {"question": "Q3", "options": ["a", "b"],
                 "answer_spec": {"type": "option_index", "expected": 1, "option_count": 2}},
            ],
        },
        "memory_check": {
            "pass_threshold_pct": 60,
            "items": [
                {"type": "mcq", "prompt": "M1", "options": ["x", "y"],
                 "answer_spec": {"type": "option_index", "expected": 0, "option_count": 2}},
                {"type": "mcq", "prompt": "M2", "options": ["x", "y"],
                 "answer_spec": {"type": "option_index", "expected": 0, "option_count": 2}},
                {"type": "mcq", "prompt": "M3", "options": ["x", "y"],
                 "answer_spec": {"type": "option_index", "expected": 0, "option_count": 2}},
            ],
        },
        # Minimal tile-match board so practice-arc entry guard has a real HW.
        "gb_tile_match": [
            {"id": "p0", "left": "2+2", "right": "4", "tier": "basic"},
            {"id": "p1", "left": "3+3", "right": "6", "tier": "basic"},
        ],
    }
    assert client.put(f"/api/homeworks/{hw_id}", json={"content_json": content}).status_code == 200
    return hw_id


def _gate(client, hw_id: str, sid: str) -> dict:
    return client.get(f"/api/runtime/homeworks/{hw_id}/gate-state?session_id={sid}").json()


def _cbp(client, hw_id: str, sid: str, idx: int, answer: str) -> dict:
    return client.post("/api/ai/check-answer", json={
        "phase": "case_based_preview", "homework_id": hw_id, "session_id": sid,
        "item_index": idx, "student_answer": answer,
    }).json()


def _mc(client, hw_id: str, sid: str, idx: int, answer: str) -> dict:
    return client.post("/api/ai/check-answer", json={
        "phase": "memory_check", "homework_id": hw_id, "session_id": sid,
        "item_index": idx, "student_answer": answer,
    }).json()


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _locked_gate(session_id, hw_id):
    return False


# ---------------------------------------------------------------------------
# 1. Fresh session — both sections locked, arc locked
# ---------------------------------------------------------------------------

def test_div3_fresh_session_practice_arc_locked(client):
    """Before any answers, practice_arc_unlocked must be False.

    The hub node renders locked; the frontend unlock choreography hasn't
    triggered because no answers have been submitted.
    """
    hw_id = _make_v2_homework(client)
    g = _gate(client, hw_id, "div3-fresh")
    assert g["cbp"]["passed"] is False
    assert g["mc"]["passed"] is False
    assert g["practice_arc_unlocked"] is False


# ---------------------------------------------------------------------------
# 2. Only CBP passed — arc still locked (AND gate, not OR)
# ---------------------------------------------------------------------------

def test_div3_cbp_only_arc_remains_locked(client):
    """Passing CBP alone must NOT flip practice_arc_unlocked.

    Frontend must not trigger the unlock animation based on cbp.passed alone.
    """
    hw_id = _make_v2_homework(client)
    sid = "div3-cbp-only"
    # Answer all 3 CBP checkpoints correctly (expected: 1, 0, 1)
    assert _cbp(client, hw_id, sid, 0, "1")["correct"] is True
    assert _cbp(client, hw_id, sid, 1, "0")["correct"] is True
    assert _cbp(client, hw_id, sid, 2, "1")["correct"] is True
    g = _gate(client, hw_id, sid)
    assert g["cbp"]["passed"] is True
    assert g["mc"]["passed"] is False
    assert g["practice_arc_unlocked"] is False


# ---------------------------------------------------------------------------
# 3. Only MC passed — arc still locked (AND gate, not OR)
# ---------------------------------------------------------------------------

def test_div3_mc_only_arc_remains_locked(client):
    """Passing MC alone must NOT flip practice_arc_unlocked.

    Frontend must not trigger the unlock animation based on mc.passed alone.
    """
    hw_id = _make_v2_homework(client)
    sid = "div3-mc-only"
    # All 3 MC items correct (expected: 0)
    for i in range(3):
        assert _mc(client, hw_id, sid, i, "0")["correct"] is True
    g = _gate(client, hw_id, sid)
    assert g["mc"]["passed"] is True
    assert g["cbp"]["passed"] is False
    assert g["practice_arc_unlocked"] is False


# ---------------------------------------------------------------------------
# 4. Both passed — arc unlocked (AND gate flips True)
# ---------------------------------------------------------------------------

def test_div3_both_passed_arc_unlocked(client):
    """When BOTH CBP and MC pass, practice_arc_unlocked becomes True.

    This is the trigger for the hub unlock choreography (chain-break animation
    + fireworks on the hub node). The shape returned must contain all three
    top-level keys the frontend reads.
    """
    hw_id = _make_v2_homework(client)
    sid = "div3-both"
    for idx, ans in [(0, "1"), (1, "0"), (2, "1")]:
        _cbp(client, hw_id, sid, idx, ans)
    for i in range(3):
        _mc(client, hw_id, sid, i, "0")
    g = _gate(client, hw_id, sid)
    assert g["cbp"]["passed"] is True
    assert g["mc"]["passed"] is True
    assert g["practice_arc_unlocked"] is True
    # Verify required top-level keys are present for frontend consumption
    assert "cbp" in g
    assert "mc" in g
    assert "practice_arc_unlocked" in g


# ---------------------------------------------------------------------------
# 5. CBP threshold is max(2, ceil(0.6 * total)) — not a raw count
# ---------------------------------------------------------------------------

def test_div3_cbp_threshold_is_server_computed(client):
    """CBP threshold for a 3-checkpoint board is max(2, ceil(0.6*3)) = 2.

    Passing exactly 2 of 3 checkpoints must flip cbp.passed True.
    Frontend cannot compute or override this value.
    """
    hw_id = _make_v2_homework(client)
    sid = "div3-cbp-threshold"
    # Answer only Q1 + Q2 correctly; skip Q3
    assert _cbp(client, hw_id, sid, 0, "1")["correct"] is True
    assert _cbp(client, hw_id, sid, 1, "0")["correct"] is True
    # Q3 is not answered — defaults to 0 correct attempts
    g = _gate(client, hw_id, sid)
    assert g["cbp"]["threshold"] == 2          # server computed max(2, ceil(1.8))
    assert g["cbp"]["checkpoints_correct"] == 2
    assert g["cbp"]["passed"] is True          # 2 >= threshold=2


# ---------------------------------------------------------------------------
# 6. MC threshold is configurable; below threshold = not passed
# ---------------------------------------------------------------------------

def test_div3_mc_below_threshold_not_passed(client):
    """Scoring below the MC pass_threshold_pct keeps mc.passed False.

    1 of 3 correct = 33%, which is < 60%. The hub node stays locked.
    """
    hw_id = _make_v2_homework(client)
    sid = "div3-mc-below"
    _mc(client, hw_id, sid, 0, "0")   # correct
    _mc(client, hw_id, sid, 1, "1")   # wrong
    _mc(client, hw_id, sid, 2, "1")   # wrong  -> 33% < 60%
    g = _gate(client, hw_id, sid)
    assert g["mc"]["score_pct"] < 60
    assert g["mc"]["passed"] is False
    assert g["practice_arc_unlocked"] is False


# ---------------------------------------------------------------------------
# 7. Practice-arc grader (tile-match) returns 403 PRACTICE_LOCKED for locked
#    sessions — the server enforces the gate independently of frontend routing.
# ---------------------------------------------------------------------------

def test_div3_tile_match_locked_returns_403_practice_locked(client, monkeypatch):
    """A locked session calling the tile-match grader must receive 403 PRACTICE_LOCKED.

    After the frontend re-routes to the hub at unlock, the server-side entry
    guard is the last line of defence. A student who directly calls the grading
    endpoint without having unlocked the arc must be refused.
    """
    hw_id = _make_v2_homework(client)
    monkeypatch.setattr(ai_routes, "is_practice_unlocked", _locked_gate)

    req = ai_routes.CheckAnswerRequest(
        phase="tile-match",
        homework_id=hw_id,
        session_id="div3-tm-locked",
        left_id="L0",
        right_id="R0",
    )
    with pytest.raises(HTTPException) as exc_info:
        _run(ai_routes._check_answer_tile_match(req))

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "PRACTICE_LOCKED"
