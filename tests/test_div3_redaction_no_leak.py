"""Division-3 Practices — hydration redaction fence (per _DIV3_CONTRACT.md).

GET /api/runtime/homeworks/{id} must NEVER ship any ⛔ server-only field for the
8 new practice games. This guards the same boundary as
test_runtime_hydration_redaction.py, extended to the Division-3 games.

⛔ server-only keys (contract §"Redaction"):
  correct_index, expected_components, correction_answer_spec, is_broken,
  expected_order, meter_deltas, best_cell_id, answer_case_id, breaks_rule,
  final_answer  (+ Ibo's correction)

If any assertion fails, every Division-3 homework leaks its answer key to every
student. Treat a failure here as a release blocker.
"""
from __future__ import annotations

import json

import pytest

from server.services.runtime_redactor import redact_for_runtime


# Every ⛔ server-only key from the contract + Ibo's merged keys.
DIV3_SERVER_ONLY_KEYS = [
    "correct_index",
    "expected_components",
    "correction_answer_spec",
    "is_broken",
    "expected_order",
    "meter_deltas",
    "best_cell_id",
    "answer_case_id",
    "breaks_rule",
    "final_answer",
    "correction",
]

# Unique sentinel values planted on every server-only field below.
LEAK_TOKENS = [
    "LEAK_ED_CORR_SPEC",
    "LEAK_MM_COMPONENTS",
    "LEAK_JM_COMPONENTS",
    "LEAK_SR_COMPONENTS",
    "LEAK_TG_BEST_CELL",
]


def _div3_homework_content() -> dict:
    """A homework carrying EVERY Division-3 game with every ⛔ field populated."""
    return {
        "flow_version": "v2",
        "meta": {"title": "Div3 redaction fence"},
        "gb_error_detection": [{
            "id": "ed1",
            "instructions": "Find the broken step.",
            "work_blocks": [
                {"id": "b0", "text": "step zero", "is_broken": False},
                {"id": "b1", "text": "step one", "is_broken": True},
            ],
            "correction_answer_spec": {"type": "text_exact", "expected": "LEAK_ED_CORR_SPEC"},
        }],
        "gb_memory_matching": [{
            "id": "mm1",
            "case_setup": "Case text visible to student.",
            "checkpoints": [
                {"question": "Q1 visible", "options": ["A", "B"], "correct_index": 1},
            ],
            "expected_components": ["LEAK_MM_COMPONENTS"],
            "dpe_prompt": "DPE prompt visible.",
        }],
        "gb_jigsaw_matching": [{
            "id": "jm1",
            "case_setup": "Jigsaw case visible.",
            "pieces": [{"id": "a", "label": "piece A visible", "role": "source"}],
            "checkpoints": [
                {"q": "JQ visible", "options": ["X", "Y"], "correct_index": 0},
            ],
            "expected_components": ["LEAK_JM_COMPONENTS"],
        }],
        "gb_assembly": [{
            "id": "as1",
            "instructions": "Order visible.",
            "pieces": [{"id": "s1", "label": "Given visible"}, {"id": "s2", "label": "QED visible"}],
            "expected_order": ["s1", "s2"],
        }],
        "gb_sentence_repair": [{
            "id": "sr1",
            "broken_sentence": "Broken sentence visible.",
            "checkpoints": [
                {"q": "Phrase? visible", "options": ["P", "Q"], "correct_index": 0},
            ],
            "expected_components": ["LEAK_SR_COMPONENTS"],
            "dpe_prompt": "Repair DPE visible.",
        }],
        "gb_ttt_grid": [{
            "id": "tg1",
            "grid_size": "3x3",
            "concept_checkpoint": {"q": "Concept? visible", "options": ["A", "B"], "correct_index": 1},
            "cells": [
                {"id": "c0", "label": "Cell0 visible", "type": "choice",
                 "meter_deltas": {"Accuracy": -1, "Risk": 2}},
                {"id": "c1", "label": "Cell1 visible", "type": "choice",
                 "meter_deltas": {"Accuracy": 3}},
            ],
            "best_cell_id": "LEAK_TG_BEST_CELL",
            "justify_checkpoint": {"q": "Why? visible", "options": ["P", "Q"], "correct_index": 0},
            "meters": ["Accuracy", "Risk"],
        }],
        "gb_problem_trace": [{
            "id": "pt1",
            "problem": "Problem visible.",
            "steps": [
                {"id": "st0", "reveal_text": "Reveal visible",
                 "predict": {"q": "Predict? visible", "options": ["a", "b"], "correct_index": 0}},
            ],
            "final_answer": "x = 99",
        }],
        "gb_counterexample": [{
            "id": "ce1",
            "claim": "Claim visible.",
            "prompt": "Prompt visible.",
            "cases": [{"id": "k0", "label": "Case0 visible"}, {"id": "k1", "label": "Case1 visible"}],
            "answer_case_id": "k1",
            "breaks_rule": "Rule-break text.",
            "explanation_checkpoint": {"q": "Why? visible", "options": ["a", "b"], "correct_index": 0},
        }],
    }


# ---------------------------------------------------------------------------
# Unit-level: redact_for_runtime strips every ⛔ key + sentinel at all depths.
# ---------------------------------------------------------------------------

def _walk_keys(node, keys: set):
    if isinstance(node, dict):
        for k, v in node.items():
            keys.add(k)
            _walk_keys(v, keys)
    elif isinstance(node, list):
        for item in node:
            _walk_keys(item, keys)


def test_redactor_strips_all_div3_server_only_keys():
    raw = _div3_homework_content()
    safe = redact_for_runtime(raw, hw_id="HW-DIV3")
    keys: set = set()
    _walk_keys(safe, keys)
    leaked = [k for k in DIV3_SERVER_ONLY_KEYS if k in keys]
    assert not leaked, f"server-only keys survived redaction: {leaked}"


def test_redactor_strips_all_div3_sentinel_values():
    raw = _div3_homework_content()
    safe = redact_for_runtime(raw, hw_id="HW-DIV3")
    blob = json.dumps(safe)
    leaked = [t for t in LEAK_TOKENS if t in blob]
    assert not leaked, f"answer sentinel values survived redaction: {leaked}"


def test_redactor_preserves_div3_display_content():
    """Student-visible content (questions, options, labels, prompts) survives —
    the deny-list must never over-strip a display field the component reads."""
    raw = _div3_homework_content()
    safe = redact_for_runtime(raw, hw_id="HW-DIV3")
    blob = json.dumps(safe)
    for text in (
        "Q1 visible", "Case text visible to student.", "DPE prompt visible.",
        "piece A visible", "Given visible", "Broken sentence visible.",
        "Cell0 visible", "Problem visible.", "Reveal visible",
        "Claim visible.", "Case1 visible",
    ):
        assert text in blob, f"display content was stripped: {text!r}"
    # MCQ options still ship — they are rendered; only correct_index is hidden.
    assert '"options"' in blob


def test_redactor_does_not_mutate_div3_input():
    raw = _div3_homework_content()
    redact_for_runtime(raw, hw_id="HW-DIV3")
    # The DB-side object still carries the answer keys (deep-copied, not mutated).
    assert raw["gb_ttt_grid"][0]["best_cell_id"] == "LEAK_TG_BEST_CELL"
    assert raw["gb_error_detection"][0]["work_blocks"][1]["is_broken"] is True
    assert raw["gb_counterexample"][0]["answer_case_id"] == "k1"


# ---------------------------------------------------------------------------
# Endpoint-level: the full hydration path (PUT → GET) leaks nothing.
# ---------------------------------------------------------------------------

@pytest.fixture
def div3_homework(client):
    hw = client.post(
        "/api/homeworks",
        json={"title": "Div3 fence HW", "subject": "math-algebra", "grade": 8, "mode": "hard"},
    ).json()
    hw_id = hw["id"]
    resp = client.put(f"/api/homeworks/{hw_id}", json={"content_json": _div3_homework_content()})
    assert resp.status_code == 200, resp.text
    return hw_id


def test_hydration_endpoint_strips_div3_keys(client, div3_homework):
    resp = client.get(f"/api/runtime/homeworks/{div3_homework}")
    assert resp.status_code == 200, resp.text
    blob = json.dumps(resp.json())
    present = [k for k in DIV3_SERVER_ONLY_KEYS if f'"{k}"' in blob]
    assert not present, f"hydration payload exposed server-only keys: {present}"
    leaked_tokens = [t for t in LEAK_TOKENS if t in blob]
    assert not leaked_tokens, f"hydration payload leaked answer values: {leaked_tokens}"


def test_hydration_endpoint_preserves_div3_display(client, div3_homework):
    resp = client.get(f"/api/runtime/homeworks/{div3_homework}")
    blob = json.dumps(resp.json())
    assert "Broken sentence visible." in blob
    assert "Problem visible." in blob
    assert "Claim visible." in blob
