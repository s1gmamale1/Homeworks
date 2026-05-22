"""Division-3 Practices — gate-state is UNCHANGED by a practice sequence.

The two Learning-Section gates (case_based_preview + memory_check) determine
`practice_arc_unlocked`. The 8 new practice games persist their attempts under
their OWN phase names (error-detection / memory-matching / ...), never under
CBP_PHASE / MC_PHASE — so running a full practice sequence MUST NOT move the
gate. This guards against a future handler accidentally writing a CBP/MC
attempt and inflating the unlock.

We assert two things across a full practice run:
  1. GET /gate-state is BYTE-IDENTICAL before and after.
  2. The practice attempts WERE persisted (phase_attempts only grew) — so the
     no-change-to-gate result isn't a false pass from the handlers no-op'ing.

The practice gate is monkeypatched UNLOCKED so the handlers actually grade
(server-enforcement of the gate is covered by test_practice_gate_server_enforced).
"""
from __future__ import annotations

import asyncio
import json

import pytest

from server.routes import ai as ai_routes
from server.db.attempts_repo import list_phase_attempts


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _unlocked_gate(session_id, hw_id):
    return True


SESSION = "div3-gate-sess"

PRACTICE_CONTENT = {
    "flow_version": "v2",
    "meta": {"title": "Div3 gate-unchanged HW"},
    # A small CBP + MC so the gate-state structure is well-defined (and starts
    # locked for a fresh session). We never submit to these in this test.
    "case_based_preview": {
        "checkpoints": [
            {"question": "Q1", "options": ["a", "b"], "answer_spec": {"type": "text_exact", "expected": "a"}},
            {"question": "Q2", "options": ["a", "b"], "answer_spec": {"type": "text_exact", "expected": "b"}},
            {"question": "Q3", "options": ["a", "b"], "answer_spec": {"type": "text_exact", "expected": "a"}},
        ],
    },
    "memory_check": {
        "pass_threshold_pct": 60,
        "items": [
            {"prompt": "MC1", "options": ["a", "b"], "answer_spec": {"type": "text_exact", "expected": "a"}},
        ],
    },
    "gb_error_detection": [{
        "id": "ed1",
        "instructions": "Find it.",
        "work_blocks": [{"id": "b0", "text": "ok", "is_broken": False},
                        {"id": "b1", "text": "bad", "is_broken": True}],
        "correction_answer_spec": {"type": "text_exact", "expected": "fixed"},
    }],
    "gb_memory_matching": [{
        "id": "mm1", "case_setup": "case",
        "checkpoints": [{"question": "q", "options": ["a", "b"], "correct_index": 0}],
        "dpe_prompt": "explain", "expected_components": ["x"],
    }],
    "gb_assembly": [{
        "id": "as1", "instructions": "order",
        "pieces": [{"id": "s1", "label": "1"}, {"id": "s2", "label": "2"}],
        "expected_order": ["s1", "s2"],
    }],
    "gb_ttt_grid": [{
        "id": "tg1", "grid_size": "2x2",
        "concept_checkpoint": {"q": "c", "options": ["a", "b"], "correct_index": 0},
        "cells": [{"id": "c0", "label": "0", "type": "x", "meter_deltas": {"A": 1}},
                  {"id": "c1", "label": "1", "type": "x", "meter_deltas": {"A": 2}}],
        "best_cell_id": "c1",
        "justify_checkpoint": {"q": "j", "options": ["a", "b"], "correct_index": 1},
        "meters": ["A"],
    }],
    "gb_problem_trace": [{
        "id": "pt1", "problem": "p",
        "steps": [{"id": "st0", "reveal_text": "r",
                   "predict": {"q": "q", "options": ["a", "b"], "correct_index": 0}}],
        "final_answer": "done",
    }],
    "gb_counterexample": [{
        "id": "ce1", "claim": "claim", "prompt": "pick",
        "cases": [{"id": "k0", "label": "0"}, {"id": "k1", "label": "1"}],
        "answer_case_id": "k1", "breaks_rule": "rule",
    }],
}


@pytest.fixture
def gate_homework(client):
    hw = client.post(
        "/api/homeworks",
        json={"title": "Div3 gate HW", "subject": "math-algebra", "grade": 6, "mode": "hard"},
    ).json()
    hw_id = hw["id"]
    resp = client.put(f"/api/homeworks/{hw_id}", json={"content_json": PRACTICE_CONTENT})
    assert resp.status_code == 200, resp.text
    return hw_id


def _gate_state(client, hw_id: str) -> dict:
    resp = client.get(f"/api/runtime/homeworks/{hw_id}/gate-state", params={"session_id": SESSION})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _run_full_practice_sequence(hw_id: str):
    """Drive one submission through every Division-3 phase handler."""
    def req(**kw):
        return ai_routes.CheckAnswerRequest(session_id=SESSION, homework_id=hw_id, **kw)

    _run(ai_routes._check_answer_error_detection(
        req(phase="error-detection", item_id="ed1", stage="spot", block_id="b1")))
    _run(ai_routes._check_answer_memory_matching(
        req(phase="memory-matching", item_id="mm1", checkpoint_index=0, selected_index=0)))
    _run(ai_routes._check_answer_assembly(
        req(phase="assembly", item_id="as1", order=["s1", "s2"])))
    _run(ai_routes._check_answer_ttt_grid(
        req(phase="ttt-grid", item_id="tg1", cell_id="c1")))
    _run(ai_routes._check_answer_problem_trace(
        req(phase="problem-trace", item_id="pt1", step_index=0, selected_index=0)))
    _run(ai_routes._check_answer_counterexample(
        req(phase="counterexample", item_id="ce1", selected_case_id="k1")))


def test_gate_state_byte_identical_after_practice_sequence(client, monkeypatch, gate_homework):
    monkeypatch.setattr(ai_routes, "is_practice_unlocked", _unlocked_gate)

    before = _gate_state(client, gate_homework)
    before_blob = json.dumps(before, sort_keys=True)

    # Sanity: a fresh session starts LOCKED (so an accidental unlock would show).
    assert before["practice_arc_unlocked"] is False

    _run_full_practice_sequence(gate_homework)

    after = _gate_state(client, gate_homework)
    after_blob = json.dumps(after, sort_keys=True)

    assert after_blob == before_blob, (
        "gate-state changed after a practice sequence — a practice handler is "
        f"writing CBP/MC attempts.\nbefore={before_blob}\nafter={after_blob}"
    )
    assert after["practice_arc_unlocked"] is False


def test_practice_attempts_were_persisted(client, monkeypatch, gate_homework):
    """The no-change-to-gate result must not be a false pass from no-op handlers:
    confirm phase_attempts GREW for the practice phases."""
    monkeypatch.setattr(ai_routes, "is_practice_unlocked", _unlocked_gate)

    practice_phases = ["error-detection", "memory-matching", "assembly",
                       "ttt-grid", "problem-trace", "counterexample"]

    def total_practice_attempts() -> int:
        return sum(
            len(_run(list_phase_attempts(SESSION, gate_homework, phase=p)))
            for p in practice_phases
        )

    before = total_practice_attempts()
    _run_full_practice_sequence(gate_homework)
    after = total_practice_attempts()

    assert after > before, "practice handlers persisted no attempts (no-op?)"
    # And CBP/MC attempt counts stayed at zero (we never submitted to them).
    assert len(_run(list_phase_attempts(SESSION, gate_homework, phase="case_based_preview"))) == 0
    assert len(_run(list_phase_attempts(SESSION, gate_homework, phase="memory_check"))) == 0
