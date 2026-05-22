"""Division-3 Practices — per-phase handler + schema round-trip tests.

Covers all 8 new practice games (per _DIV3_CONTRACT.md):
  error-detection, memory-matching, jigsaw-matching, assembly,
  sentence-repair, ttt-grid, problem-trace, counterexample.

For EACH phase:
  - schema round-trip: a homework carrying the gb_* field PUTs + GETs cleanly
    (the permissive ContentJSON model accepts the authored shape).
  - handler MCQ correct / incorrect: the deterministic branch grades
    selected_index == correct_index (or the game's deterministic equivalent).
  - DPE / open-ended: the LOCKED seam response { pending_ai: true, ... }.

The practice gate is monkeypatched to "unlocked" so the handlers proceed to
grading — the SERVER-enforcement of the gate itself is covered by
test_practice_gate_server_enforced.py (and re-asserted in
test_div3_gate_unchanged.py via a REAL unlock).

Harness/monkeypatch pattern follows test_practice_gate_server_enforced.py.
"""
from __future__ import annotations

import asyncio

import pytest

from server.routes import ai as ai_routes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _unlocked_gate(session_id, hw_id):
    return True


@pytest.fixture(autouse=True)
def _unlock(monkeypatch):
    """Every test in this file grades through an UNLOCKED practice gate."""
    monkeypatch.setattr(ai_routes, "is_practice_unlocked", _unlocked_gate)


def _seed_hw(client, title: str, content: dict) -> str:
    hw = client.post(
        "/api/homeworks",
        json={"title": title, "subject": "math-algebra", "grade": 6, "mode": "hard"},
    ).json()
    hw_id = hw["id"]
    full = {"flow_version": "v2", "meta": {"title": title}, **content}
    resp = client.put(f"/api/homeworks/{hw_id}", json={"content_json": full})
    assert resp.status_code == 200, resp.text
    return hw_id


def _roundtrip(client, hw_id: str, field: str) -> list:
    """GET the stored homework via the builder read path and return the field."""
    resp = client.get(f"/api/homeworks/{hw_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()["content_json"][field]


def _req(**kw):
    return ai_routes.CheckAnswerRequest(session_id="div3-sess", **kw)


# ===========================================================================
# Authored content fixtures (one per game)
# ===========================================================================

ERROR_DETECTION = {
    "gb_error_detection": [{
        "id": "ed1",
        "instructions": "Find the broken step.",
        "pattern": "math",
        "work_blocks": [
            {"id": "b0", "text": "2x = 10", "is_broken": False},
            {"id": "b1", "text": "x = 10 + 2", "is_broken": True},
            {"id": "b2", "text": "check answer", "is_broken": False},
        ],
        "correction_answer_spec": {"type": "text_exact", "expected": "x = 5"},
        "hint": "Re-check the operation.",
        "why_prompt": "Explain why the step is wrong.",
    }]
}

MEMORY_MATCHING = {
    "gb_memory_matching": [{
        "id": "mm1",
        "case_setup": "A patient presents with...",
        "pairs": [{"id": "p1", "left": "fever", "right": "infection"}],
        "checkpoints": [
            {"question": "Identify the cause", "options": ["A", "B"], "correct_index": 1},
            {"question": "Decide treatment", "options": ["X", "Y"], "correct_index": 0},
            {"question": "Justify", "options": ["P", "Q"], "correct_index": 1},
        ],
        "dpe_prompt": "Walk through your reasoning.",
        "expected_components": ["cause", "evidence", "treatment"],
        "consequence": {"correct_path": "good", "wrong_path": "bad"},
    }]
}

JIGSAW_MATCHING = {
    "gb_jigsaw_matching": [{
        "id": "jm1",
        "case_setup": "Two events relate...",
        "pieces": [{"id": "a", "label": "cause", "role": "source"},
                   {"id": "b", "label": "effect", "role": "target"}],
        "checkpoints": [
            {"q": "Which two fit?", "options": ["A", "B"], "correct_index": 0},
            {"q": "Relationship type?", "options": ["X", "Y"], "correct_index": 1},
            {"q": "Justify", "options": ["P", "Q"], "correct_index": 0},
        ],
        "dpe_prompt": "Explain the link.",
        "expected_components": ["relationship", "evidence"],
    }]
}

ASSEMBLY = {
    "gb_assembly": [{
        "id": "as1",
        "instructions": "Order the proof steps.",
        "pieces": [{"id": "s1", "label": "Given"}, {"id": "s2", "label": "Therefore"},
                   {"id": "s3", "label": "QED"}],
        "expected_order": ["s1", "s2", "s3"],
    }]
}

SENTENCE_REPAIR = {
    "gb_sentence_repair": [{
        "id": "sr1",
        "broken_sentence": "Me and him goes to school.",
        "checkpoints": [
            {"q": "Which phrase breaks it?", "options": ["Me and him", "to school"], "correct_index": 0},
            {"q": "Best repair?", "options": ["He and I go", "Me goes"], "correct_index": 0},
            {"q": "Which explanation?", "options": ["subject case", "tense"], "correct_index": 0},
        ],
        "dpe_prompt": "Explain the grammar rule.",
        "expected_components": ["subject", "pronoun case", "agreement"],
    }]
}

TTT_GRID = {
    "gb_ttt_grid": [{
        "id": "tg1",
        "grid_size": "3x3",
        "concept_checkpoint": {"q": "Which principle?", "options": ["A", "B"], "correct_index": 1},
        "cells": [
            {"id": "c0", "label": "Option A", "type": "choice",
             "meter_deltas": {"Accuracy": -1, "Risk": 2}},
            {"id": "c1", "label": "Option B", "type": "choice",
             "meter_deltas": {"Accuracy": 3, "Risk": -1}},
            {"id": "c2", "label": "Option C", "type": "choice",
             "meter_deltas": {"Accuracy": 0, "Risk": 0}},
        ],
        "best_cell_id": "c1",
        "justify_checkpoint": {"q": "Why best?", "options": ["P", "Q"], "correct_index": 0},
        "dpe_prompt": "Justify your grid choice.",
        "meters": ["Accuracy", "Risk"],
    }]
}

PROBLEM_TRACE = {
    "gb_problem_trace": [{
        "id": "pt1",
        "problem": "Solve 3x + 2 = 11.",
        "steps": [
            {"id": "st0", "reveal_text": "Subtract 2: 3x = 9",
             "predict": {"q": "Next step?", "options": ["divide", "add"], "correct_index": 0}},
            {"id": "st1", "reveal_text": "Divide by 3: x = 3",
             "predict": {"q": "Result?", "options": ["3", "9"], "correct_index": 0}},
        ],
        "final_answer": "x = 3",
    }]
}

COUNTEREXAMPLE = {
    "gb_counterexample": [{
        "id": "ce1",
        "claim": "All primes are odd.",
        "prompt": "Pick the case that breaks the claim.",
        "cases": [{"id": "k0", "label": "7"}, {"id": "k1", "label": "2"}, {"id": "k2", "label": "9"}],
        "answer_case_id": "k1",
        "breaks_rule": "2 is an even prime.",
        "explanation_checkpoint": {"q": "Why?", "options": ["2 is even", "9 is odd"], "correct_index": 0},
        "dpe_prompt": "Explain the counterexample.",
    }]
}


# ===========================================================================
# Schema round-trips — the permissive model stores+returns each authored shape
# ===========================================================================

@pytest.mark.parametrize("field,content", [
    ("gb_error_detection", ERROR_DETECTION),
    ("gb_memory_matching", MEMORY_MATCHING),
    ("gb_jigsaw_matching", JIGSAW_MATCHING),
    ("gb_assembly", ASSEMBLY),
    ("gb_sentence_repair", SENTENCE_REPAIR),
    ("gb_ttt_grid", TTT_GRID),
    ("gb_problem_trace", PROBLEM_TRACE),
    ("gb_counterexample", COUNTEREXAMPLE),
])
def test_schema_roundtrip(client, field, content):
    hw_id = _seed_hw(client, f"RT {field}", content)
    stored = _roundtrip(client, hw_id, field)
    assert isinstance(stored, list) and len(stored) == 1
    # The authored item id survives the round-trip.
    assert stored[0]["id"] == content[field][0]["id"]


# ===========================================================================
# error-detection
# ===========================================================================

def test_error_detection_spot_correct(client):
    hw_id = _seed_hw(client, "ED spot ok", ERROR_DETECTION)
    res = _run(ai_routes._check_answer_error_detection(
        _req(phase="error-detection", homework_id=hw_id, item_id="ed1",
             stage="spot", block_id="b1")))
    assert res["correct"] is True


def test_error_detection_spot_incorrect(client):
    hw_id = _seed_hw(client, "ED spot wrong", ERROR_DETECTION)
    res = _run(ai_routes._check_answer_error_detection(
        _req(phase="error-detection", homework_id=hw_id, item_id="ed1",
             stage="spot", block_id="b0")))
    assert res["correct"] is False


def test_error_detection_correction_deterministic(client):
    hw_id = _seed_hw(client, "ED correction", ERROR_DETECTION)
    ok = _run(ai_routes._check_answer_error_detection(
        _req(phase="error-detection", homework_id=hw_id, item_id="ed1",
             stage="correction", correction="x = 5")))
    assert ok["correct"] is True
    bad = _run(ai_routes._check_answer_error_detection(
        _req(phase="error-detection", homework_id=hw_id, item_id="ed1",
             stage="correction", correction="x = 12")))
    assert bad["correct"] is False


def test_error_detection_why_is_dpe_seam(client):
    hw_id = _seed_hw(client, "ED why", ERROR_DETECTION)
    res = _run(ai_routes._check_answer_error_detection(
        _req(phase="error-detection", homework_id=hw_id, item_id="ed1",
             stage="why", reasoning_text="The inverse operation was applied wrong.")))
    assert res["pending_ai"] is True
    assert res["passed"] is None and res["score"] is None and res["correct"] is False


# ===========================================================================
# memory-matching / jigsaw-matching / sentence-repair (shared shape)
# ===========================================================================

@pytest.mark.parametrize("phase,field,content,item_id", [
    ("memory-matching", "gb_memory_matching", MEMORY_MATCHING, "mm1"),
    ("jigsaw-matching", "gb_jigsaw_matching", JIGSAW_MATCHING, "jm1"),
    ("sentence-repair", "gb_sentence_repair", SENTENCE_REPAIR, "sr1"),
])
def test_checkpoints_then_dpe_mcq_correct(client, phase, field, content, item_id):
    hw_id = _seed_hw(client, f"{phase} ok", content)
    handler = ai_routes._DIV3_PHASE_HANDLERS[phase]
    # checkpoint 0 — correct_index is 1 for memory/jigsaw, 0 for sentence-repair.
    expected_ci = content[field][0]["checkpoints"][0]["correct_index"]
    res = _run(handler(_req(phase=phase, homework_id=hw_id, item_id=item_id,
                            checkpoint_index=0, selected_index=expected_ci)))
    assert res["correct"] is True
    assert res["advance"] is False  # not the last checkpoint


@pytest.mark.parametrize("phase,field,content,item_id", [
    ("memory-matching", "gb_memory_matching", MEMORY_MATCHING, "mm1"),
    ("jigsaw-matching", "gb_jigsaw_matching", JIGSAW_MATCHING, "jm1"),
    ("sentence-repair", "gb_sentence_repair", SENTENCE_REPAIR, "sr1"),
])
def test_checkpoints_then_dpe_mcq_incorrect(client, phase, field, content, item_id):
    hw_id = _seed_hw(client, f"{phase} wrong", content)
    handler = ai_routes._DIV3_PHASE_HANDLERS[phase]
    expected_ci = content[field][0]["checkpoints"][0]["correct_index"]
    wrong = 1 - expected_ci  # the 2-option flip
    res = _run(handler(_req(phase=phase, homework_id=hw_id, item_id=item_id,
                            checkpoint_index=0, selected_index=wrong)))
    assert res["correct"] is False


@pytest.mark.parametrize("phase,field,content,item_id", [
    ("memory-matching", "gb_memory_matching", MEMORY_MATCHING, "mm1"),
    ("jigsaw-matching", "gb_jigsaw_matching", JIGSAW_MATCHING, "jm1"),
    ("sentence-repair", "gb_sentence_repair", SENTENCE_REPAIR, "sr1"),
])
def test_checkpoints_last_advances(client, phase, field, content, item_id):
    hw_id = _seed_hw(client, f"{phase} last", content)
    handler = ai_routes._DIV3_PHASE_HANDLERS[phase]
    last_idx = len(content[field][0]["checkpoints"]) - 1
    expected_ci = content[field][0]["checkpoints"][last_idx]["correct_index"]
    res = _run(handler(_req(phase=phase, homework_id=hw_id, item_id=item_id,
                            checkpoint_index=last_idx, selected_index=expected_ci)))
    assert res["advance"] is True


@pytest.mark.parametrize("phase,content,item_id", [
    ("memory-matching", MEMORY_MATCHING, "mm1"),
    ("jigsaw-matching", JIGSAW_MATCHING, "jm1"),
    ("sentence-repair", SENTENCE_REPAIR, "sr1"),
])
def test_checkpoints_dpe_seam(client, phase, content, item_id):
    hw_id = _seed_hw(client, f"{phase} dpe", content)
    handler = ai_routes._DIV3_PHASE_HANDLERS[phase]
    res = _run(handler(_req(phase=phase, homework_id=hw_id, item_id=item_id,
                            reasoning_text="A".rjust(120, "x"))))
    assert res["pending_ai"] is True
    assert res["passed"] is None and res["score"] is None


# ===========================================================================
# assembly
# ===========================================================================

def test_assembly_correct_order(client):
    hw_id = _seed_hw(client, "ASM ok", ASSEMBLY)
    res = _run(ai_routes._check_answer_assembly(
        _req(phase="assembly", homework_id=hw_id, item_id="as1",
             order=["s1", "s2", "s3"])))
    assert res["correct"] is True and res["complete"] is True


def test_assembly_wrong_order(client):
    hw_id = _seed_hw(client, "ASM wrong", ASSEMBLY)
    res = _run(ai_routes._check_answer_assembly(
        _req(phase="assembly", homework_id=hw_id, item_id="as1",
             order=["s2", "s1", "s3"])))
    assert res["correct"] is False and res["complete"] is True


# ===========================================================================
# ttt-grid
# ===========================================================================

def test_ttt_grid_concept_checkpoint(client):
    hw_id = _seed_hw(client, "TG concept", TTT_GRID)
    ok = _run(ai_routes._check_answer_ttt_grid(
        _req(phase="ttt-grid", homework_id=hw_id, item_id="tg1",
             checkpoint_index=0, selected_index=1)))
    assert ok["correct"] is True and ok["advance"] is False
    bad = _run(ai_routes._check_answer_ttt_grid(
        _req(phase="ttt-grid", homework_id=hw_id, item_id="tg1",
             checkpoint_index=0, selected_index=0)))
    assert bad["correct"] is False


def test_ttt_grid_justify_checkpoint_advances(client):
    hw_id = _seed_hw(client, "TG justify", TTT_GRID)
    res = _run(ai_routes._check_answer_ttt_grid(
        _req(phase="ttt-grid", homework_id=hw_id, item_id="tg1",
             checkpoint_index=1, selected_index=0)))
    assert res["correct"] is True and res["advance"] is True


def test_ttt_grid_cell_pick(client):
    hw_id = _seed_hw(client, "TG cell", TTT_GRID)
    ok = _run(ai_routes._check_answer_ttt_grid(
        _req(phase="ttt-grid", homework_id=hw_id, item_id="tg1", cell_id="c1")))
    assert ok["correct"] is True
    bad = _run(ai_routes._check_answer_ttt_grid(
        _req(phase="ttt-grid", homework_id=hw_id, item_id="tg1", cell_id="c0")))
    assert bad["correct"] is False


def test_ttt_grid_dpe_seam(client):
    hw_id = _seed_hw(client, "TG dpe", TTT_GRID)
    res = _run(ai_routes._check_answer_ttt_grid(
        _req(phase="ttt-grid", homework_id=hw_id, item_id="tg1",
             reasoning_text="x".rjust(120, "y"))))
    assert res["pending_ai"] is True


# ===========================================================================
# problem-trace
# ===========================================================================

def test_problem_trace_predict_correct(client):
    hw_id = _seed_hw(client, "PT ok", PROBLEM_TRACE)
    res = _run(ai_routes._check_answer_problem_trace(
        _req(phase="problem-trace", homework_id=hw_id, item_id="pt1",
             step_index=0, selected_index=0)))
    assert res["correct"] is True and res["advance"] is False


def test_problem_trace_predict_incorrect(client):
    hw_id = _seed_hw(client, "PT wrong", PROBLEM_TRACE)
    res = _run(ai_routes._check_answer_problem_trace(
        _req(phase="problem-trace", homework_id=hw_id, item_id="pt1",
             step_index=0, selected_index=1)))
    assert res["correct"] is False


def test_problem_trace_last_step_advances(client):
    hw_id = _seed_hw(client, "PT last", PROBLEM_TRACE)
    res = _run(ai_routes._check_answer_problem_trace(
        _req(phase="problem-trace", homework_id=hw_id, item_id="pt1",
             step_index=1, selected_index=0)))
    assert res["advance"] is True


# ===========================================================================
# counterexample
# ===========================================================================

def test_counterexample_case_pick_correct(client):
    hw_id = _seed_hw(client, "CE ok", COUNTEREXAMPLE)
    res = _run(ai_routes._check_answer_counterexample(
        _req(phase="counterexample", homework_id=hw_id, item_id="ce1",
             selected_case_id="k1")))
    assert res["correct"] is True


def test_counterexample_case_pick_incorrect(client):
    hw_id = _seed_hw(client, "CE wrong", COUNTEREXAMPLE)
    res = _run(ai_routes._check_answer_counterexample(
        _req(phase="counterexample", homework_id=hw_id, item_id="ce1",
             selected_case_id="k0")))
    assert res["correct"] is False


def test_counterexample_explanation_mcq(client):
    hw_id = _seed_hw(client, "CE expl", COUNTEREXAMPLE)
    res = _run(ai_routes._check_answer_counterexample(
        _req(phase="counterexample", homework_id=hw_id, item_id="ce1",
             checkpoint_index=0, selected_index=0)))
    assert res["correct"] is True


def test_counterexample_dpe_seam(client):
    hw_id = _seed_hw(client, "CE dpe", COUNTEREXAMPLE)
    res = _run(ai_routes._check_answer_counterexample(
        _req(phase="counterexample", homework_id=hw_id, item_id="ce1",
             reasoning_text="z".rjust(120, "w"))))
    assert res["pending_ai"] is True


# ===========================================================================
# No-leak: handler responses never carry a ⛔ server-only field.
# ===========================================================================

def test_handler_responses_never_leak_server_only_fields(client):
    import json
    hw_id = _seed_hw(client, "leak check", {**ERROR_DETECTION, **TTT_GRID,
                                            **COUNTEREXAMPLE, **PROBLEM_TRACE,
                                            **MEMORY_MATCHING, **ASSEMBLY})
    forbidden = ("correct_index", "expected_components", "correction_answer_spec",
                 "meter_deltas", "best_cell_id", "answer_case_id", "breaks_rule",
                 "final_answer", "is_broken", "expected_order")
    responses = [
        _run(ai_routes._check_answer_error_detection(
            _req(phase="error-detection", homework_id=hw_id, item_id="ed1",
                 stage="spot", block_id="b1"))),
        _run(ai_routes._check_answer_ttt_grid(
            _req(phase="ttt-grid", homework_id=hw_id, item_id="tg1", cell_id="c1"))),
        _run(ai_routes._check_answer_counterexample(
            _req(phase="counterexample", homework_id=hw_id, item_id="ce1",
                 selected_case_id="k1"))),
        _run(ai_routes._check_answer_assembly(
            _req(phase="assembly", homework_id=hw_id, item_id="as1",
                 order=["s1", "s2", "s3"]))),
    ]
    for res in responses:
        blob = json.dumps(res)
        for key in forbidden:
            assert f'"{key}"' not in blob, f"handler leaked {key}: {res}"
