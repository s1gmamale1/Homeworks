"""Division-3 Practices — 2 MORE games (Dependency Chain + Confidence Check).

Covers the two new practice games added on top of the original 8
(per _DIV3_CONTRACT.md conventions):
  - dependency-chain  (gb_dependency_chain) — multi-step TRANSFER; each linked
    step grades selected_index == steps[i].correct_index; a CORRECT answer
    surfaces the step's `carry_label` so it can feed the next step.
  - confidence-check  (gb_confidence_check) — metacognition; grades the MCQ
    only; the calibration verdict is CLIENT-derived from {correct, confidence}.

For EACH game:
  - schema round-trip: a homework carrying the gb_* field PUTs + GETs cleanly
    (the permissive ContentJSON model accepts the authored shape).
  - handler MCQ correct / incorrect (selected_index == correct_index).
  - the game's distinctive contract: dependency-chain surfaces `carry` only on
    a correct answer + sets advance on the last step; confidence-check echoes
    `confidence` + always advances; neither leaks correct_index.
  - redaction no-leak: correct_index + carry_label are stripped at hydration
    (both the unit-level redactor and the GET endpoint).

The practice gate is monkeypatched to "unlocked" so handlers proceed to grading
— SERVER-enforcement of the gate is covered by
test_practice_gate_server_enforced.py. Harness/monkeypatch pattern follows
test_div3_practice_phases.py.
"""
from __future__ import annotations

import asyncio
import json

import pytest

from server.routes import ai as ai_routes
from server.services.runtime_redactor import redact_for_runtime


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
        json={"title": title, "subject": "math-algebra", "grade": 9, "mode": "hard"},
    ).json()
    hw_id = hw["id"]
    full = {"flow_version": "v2", "meta": {"title": title}, **content}
    resp = client.put(f"/api/homeworks/{hw_id}", json={"content_json": full})
    assert resp.status_code == 200, resp.text
    return hw_id


def _roundtrip(client, hw_id: str, field: str) -> list:
    resp = client.get(f"/api/homeworks/{hw_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()["content_json"][field]


def _req(**kw):
    return ai_routes.CheckAnswerRequest(session_id="div3-more-sess", **kw)


# ===========================================================================
# Authored content fixtures (one per new game) — AP/IB/Cambridge flavored.
# ===========================================================================

DEPENDENCY_CHAIN = {
    "gb_dependency_chain": [{
        "id": "dc1",
        "scenario": (
            "A projectile is launched at 20 m/s from a 15 m cliff (g = 10 m/s²). "
            "Work through to its time of flight, then its horizontal range."
        ),
        "steps": [
            {
                "id": "s0",
                "prompt": "Vertical component if launched at 30° above horizontal?",
                "options": ["10 m/s", "17.3 m/s", "20 m/s"],
                "correct_index": 0,
                "carry_label": "v_y = 10 m/s →",
            },
            {
                "id": "s1",
                "prompt": "Using v_y = 10 m/s, time to the peak?",
                "options": ["0.5 s", "1.0 s", "2.0 s"],
                "correct_index": 1,
                "carry_label": "t_peak = 1.0 s →",
            },
            {
                "id": "s2",
                "prompt": "Horizontal range over the full 3.0 s flight (v_x = 17.3 m/s)?",
                "options": ["17.3 m", "34.6 m", "51.9 m"],
                "correct_index": 2,
            },
        ],
    }]
}

CONFIDENCE_CHECK = {
    "gb_confidence_check": [
        {
            "id": "cc1",
            "question": "In a perfectly competitive market in long-run equilibrium, economic profit is:",
            "options": ["positive", "zero", "negative"],
            "correct_index": 1,
        },
        {
            "id": "cc2",
            "question": "The derivative of ln(x) with respect to x is:",
            "options": ["1/x", "x", "ln(x)/x"],
            "correct_index": 0,
        },
    ]
}


# ===========================================================================
# Schema round-trips — the permissive model stores+returns each authored shape
# ===========================================================================

@pytest.mark.parametrize("field,content", [
    ("gb_dependency_chain", DEPENDENCY_CHAIN),
    ("gb_confidence_check", CONFIDENCE_CHECK),
])
def test_schema_roundtrip(client, field, content):
    hw_id = _seed_hw(client, f"RT {field}", content)
    stored = _roundtrip(client, hw_id, field)
    assert isinstance(stored, list) and len(stored) == len(content[field])
    assert stored[0]["id"] == content[field][0]["id"]


def test_schema_roundtrip_preserves_chain_steps(client):
    """The dependency-chain step shape (prompt/options + ⛔ keys) survives the
    permissive builder round-trip (answers are NOT stripped on the builder read
    path — only at the runtime hydration boundary)."""
    hw_id = _seed_hw(client, "DC steps", DEPENDENCY_CHAIN)
    stored = _roundtrip(client, hw_id, "gb_dependency_chain")
    steps = stored[0]["steps"]
    assert [s["id"] for s in steps] == ["s0", "s1", "s2"]
    assert steps[0]["carry_label"] == "v_y = 10 m/s →"
    assert steps[2].get("carry_label") is None  # final step has no carry


# ===========================================================================
# dependency-chain — handler grading
# ===========================================================================

def test_dependency_chain_step_correct(client):
    hw_id = _seed_hw(client, "DC ok", DEPENDENCY_CHAIN)
    res = _run(ai_routes._check_answer_dependency_chain(
        _req(phase="dependency-chain", homework_id=hw_id, item_id="dc1",
             step_index=0, selected_index=0)))
    assert res["correct"] is True
    assert res["advance"] is False  # not the last step


def test_dependency_chain_step_incorrect(client):
    hw_id = _seed_hw(client, "DC wrong", DEPENDENCY_CHAIN)
    res = _run(ai_routes._check_answer_dependency_chain(
        _req(phase="dependency-chain", homework_id=hw_id, item_id="dc1",
             step_index=0, selected_index=2)))
    assert res["correct"] is False


def test_dependency_chain_correct_surfaces_carry(client):
    """A CORRECT answer surfaces the step's carry_label (so it can feed the next
    step). The carry is delivered ONLY in the response — never at hydration."""
    hw_id = _seed_hw(client, "DC carry", DEPENDENCY_CHAIN)
    res = _run(ai_routes._check_answer_dependency_chain(
        _req(phase="dependency-chain", homework_id=hw_id, item_id="dc1",
             step_index=1, selected_index=1)))
    assert res["correct"] is True
    assert res["carry"] == "t_peak = 1.0 s →"


def test_dependency_chain_wrong_withholds_carry(client):
    """A WRONG answer must NOT surface the carry (it would leak the answer)."""
    hw_id = _seed_hw(client, "DC no-carry", DEPENDENCY_CHAIN)
    res = _run(ai_routes._check_answer_dependency_chain(
        _req(phase="dependency-chain", homework_id=hw_id, item_id="dc1",
             step_index=1, selected_index=0)))
    assert res["correct"] is False
    assert "carry" not in res


def test_dependency_chain_last_step_advances(client):
    hw_id = _seed_hw(client, "DC last", DEPENDENCY_CHAIN)
    res = _run(ai_routes._check_answer_dependency_chain(
        _req(phase="dependency-chain", homework_id=hw_id, item_id="dc1",
             step_index=2, selected_index=2)))
    assert res["correct"] is True
    assert res["advance"] is True
    # Final step authored no carry_label → no carry surfaced.
    assert "carry" not in res


def test_dependency_chain_step_index_out_of_range(client):
    from fastapi import HTTPException
    hw_id = _seed_hw(client, "DC oob", DEPENDENCY_CHAIN)
    with pytest.raises(HTTPException) as ei:
        _run(ai_routes._check_answer_dependency_chain(
            _req(phase="dependency-chain", homework_id=hw_id, item_id="dc1",
                 step_index=9, selected_index=0)))
    assert ei.value.status_code == 400
    assert ei.value.detail["code"] == "DC_BAD_STEP_INDEX"


def test_dependency_chain_registered_in_dispatch_map():
    assert "dependency-chain" in ai_routes._DIV3_PHASE_HANDLERS
    assert (ai_routes._DIV3_PHASE_HANDLERS["dependency-chain"]
            is ai_routes._check_answer_dependency_chain)


# ===========================================================================
# confidence-check — handler grading
# ===========================================================================

def test_confidence_check_correct(client):
    hw_id = _seed_hw(client, "CC ok", CONFIDENCE_CHECK)
    res = _run(ai_routes._check_answer_confidence_check(
        _req(phase="confidence-check", homework_id=hw_id, item_id="cc1",
             selected_index=1, confidence="sure")))
    assert res["correct"] is True
    assert res["advance"] is True  # one MCQ per item
    assert res["confidence"] == "sure"


def test_confidence_check_incorrect(client):
    hw_id = _seed_hw(client, "CC wrong", CONFIDENCE_CHECK)
    res = _run(ai_routes._check_answer_confidence_check(
        _req(phase="confidence-check", homework_id=hw_id, item_id="cc1",
             selected_index=0, confidence="guess")))
    assert res["correct"] is False
    assert res["confidence"] == "guess"


def test_confidence_check_grade_independent_of_confidence(client):
    """Confidence must NOT change the grade — the server grades the MCQ only."""
    hw_id = _seed_hw(client, "CC indep", CONFIDENCE_CHECK)
    for conf in ("sure", "maybe", "guess"):
        res = _run(ai_routes._check_answer_confidence_check(
            _req(phase="confidence-check", homework_id=hw_id, item_id="cc2",
                 selected_index=0, confidence=conf)))
        assert res["correct"] is True, conf  # cc2 correct_index == 0 regardless


def test_confidence_check_confidence_optional(client):
    """A missing confidence still grades cleanly (no echoed confidence)."""
    hw_id = _seed_hw(client, "CC noconf", CONFIDENCE_CHECK)
    res = _run(ai_routes._check_answer_confidence_check(
        _req(phase="confidence-check", homework_id=hw_id, item_id="cc1",
             selected_index=1)))
    assert res["correct"] is True
    assert "confidence" not in res


def test_confidence_check_registered_in_dispatch_map():
    assert "confidence-check" in ai_routes._DIV3_PHASE_HANDLERS
    assert (ai_routes._DIV3_PHASE_HANDLERS["confidence-check"]
            is ai_routes._check_answer_confidence_check)


# ===========================================================================
# No-leak: handler responses never carry a ⛔ server-only field.
# ===========================================================================

def test_handler_responses_never_leak_server_only_fields(client):
    hw_id = _seed_hw(client, "more leak check",
                     {**DEPENDENCY_CHAIN, **CONFIDENCE_CHECK})
    forbidden = ("correct_index", "carry_label")
    responses = [
        _run(ai_routes._check_answer_dependency_chain(
            _req(phase="dependency-chain", homework_id=hw_id, item_id="dc1",
                 step_index=0, selected_index=0))),
        _run(ai_routes._check_answer_dependency_chain(
            _req(phase="dependency-chain", homework_id=hw_id, item_id="dc1",
                 step_index=0, selected_index=2))),  # wrong
        _run(ai_routes._check_answer_confidence_check(
            _req(phase="confidence-check", homework_id=hw_id, item_id="cc1",
                 selected_index=1, confidence="sure"))),
    ]
    for res in responses:
        blob = json.dumps(res)
        for key in forbidden:
            assert f'"{key}"' not in blob, f"handler leaked {key}: {res}"
    # The correct dependency-chain response DOES carry the result, but under the
    # neutral `carry` key (the value, never the answer-bearing `carry_label` key).
    assert responses[0]["carry"] == "v_y = 10 m/s →"


# ===========================================================================
# Redaction fence — correct_index + carry_label stripped at hydration.
# ===========================================================================

def _walk_keys(node, keys: set):
    if isinstance(node, dict):
        for k, v in node.items():
            keys.add(k)
            _walk_keys(v, keys)
    elif isinstance(node, list):
        for item in node:
            _walk_keys(item, keys)


def _more_games_content() -> dict:
    return {
        "flow_version": "v2",
        "meta": {"title": "Div3 more redaction fence"},
        **DEPENDENCY_CHAIN,
        **CONFIDENCE_CHECK,
    }


def test_redactor_strips_correct_index_and_carry_label():
    raw = _more_games_content()
    safe = redact_for_runtime(raw, hw_id="HW-DIV3-MORE")
    keys: set = set()
    _walk_keys(safe, keys)
    assert "correct_index" not in keys, "correct_index survived redaction"
    assert "carry_label" not in keys, "carry_label survived redaction"


def test_redactor_preserves_more_games_display_content():
    raw = _more_games_content()
    safe = redact_for_runtime(raw, hw_id="HW-DIV3-MORE")
    blob = json.dumps(safe)
    for text in (
        "A projectile is launched",            # dependency-chain scenario
        "Vertical component if launched",      # step prompt
        "perfectly competitive market",        # confidence-check question
    ):
        assert text in blob, f"display content was stripped: {text!r}"
    # MCQ options + step prompts still ship; only the answer keys are hidden.
    assert '"options"' in blob
    assert '"steps"' in blob


def test_redactor_does_not_mutate_more_games_input():
    raw = _more_games_content()
    redact_for_runtime(raw, hw_id="HW-DIV3-MORE")
    # The DB-side object still carries the answer keys (deep-copied, not mutated).
    assert raw["gb_dependency_chain"][0]["steps"][0]["correct_index"] == 0
    assert raw["gb_dependency_chain"][0]["steps"][0]["carry_label"] == "v_y = 10 m/s →"
    assert raw["gb_confidence_check"][0]["correct_index"] == 1


@pytest.fixture
def more_games_homework(client):
    hw = client.post(
        "/api/homeworks",
        json={"title": "Div3 more fence HW", "subject": "math-algebra", "grade": 9, "mode": "hard"},
    ).json()
    hw_id = hw["id"]
    resp = client.put(f"/api/homeworks/{hw_id}", json={"content_json": _more_games_content()})
    assert resp.status_code == 200, resp.text
    return hw_id


def test_hydration_endpoint_strips_more_games_keys(client, more_games_homework):
    resp = client.get(f"/api/runtime/homeworks/{more_games_homework}")
    assert resp.status_code == 200, resp.text
    blob = json.dumps(resp.json())
    for key in ("correct_index", "carry_label"):
        assert f'"{key}"' not in blob, f"hydration payload exposed server-only key: {key}"
    # The carry_label VALUES (the "… →" result tokens) are answer-revealing and
    # must be gone. NOTE: an author may legitimately embed a *prior* carry inside
    # a *later step's prompt* (that's the carry-forward design), so we assert on
    # the full "→"-suffixed carry tokens — which only ever appear as carry_label
    # values, never inside a prompt — and on a value never echoed in any prompt.
    assert "v_y = 10 m/s →" not in blob
    assert "t_peak = 1.0 s →" not in blob
    assert "t_peak = 1.0 s" not in blob  # this value is in no prompt → must be gone


def test_hydration_endpoint_preserves_more_games_display(client, more_games_homework):
    resp = client.get(f"/api/runtime/homeworks/{more_games_homework}")
    blob = json.dumps(resp.json())
    assert "A projectile is launched" in blob
    assert "perfectly competitive market" in blob
