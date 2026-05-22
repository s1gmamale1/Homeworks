"""End-to-end gate-flow integration test for the v2 React runtime (F1+F2+F3).

Walks the server-authoritative unlock sequence at the API level:
  create v2 homework → answer CBP checkpoints → answer Memory Check items →
  assert gate-state transitions (cbp gate, mc gate, practice_arc_unlocked).

This guards the contract the React client renders against: the client can NEVER
flip practice_arc_unlocked on its own — only correct, server-graded answers do.
"""

from unittest.mock import patch

import pytest

import server.routes.ai as _ai_routes


def _make_v2_homework(client):
    hw = client.post(
        "/api/homeworks",
        json={"title": "Gate flow HW", "subject": "math-algebra", "grade": 6, "mode": "hard"},
    ).json()
    hw_id = hw["id"]
    content = {
        "flow_version": "v2",
        "meta": {"title": "Gate flow HW"},
        "case_based_preview": {
            "checkpoints": [
                {"question": "Q1", "options": ["a", "b"], "answer_spec": {"type": "option_index", "expected": 1, "option_count": 2}},
                {"question": "Q2", "options": ["a", "b"], "answer_spec": {"type": "option_index", "expected": 0, "option_count": 2}},
                {"question": "Q3", "options": ["a", "b"], "answer_spec": {"type": "option_index", "expected": 1, "option_count": 2}},
            ],
        },
        "memory_check": {
            "pass_threshold_pct": 60,
            "items": [
                {"type": "mcq", "prompt": "M1", "options": ["x", "y"], "answer_spec": {"type": "option_index", "expected": 0, "option_count": 2}},
                {"type": "mcq", "prompt": "M2", "options": ["x", "y"], "answer_spec": {"type": "option_index", "expected": 0, "option_count": 2}},
                {"type": "mcq", "prompt": "M3", "options": ["x", "y"], "answer_spec": {"type": "option_index", "expected": 0, "option_count": 2}},
            ],
        },
    }
    assert client.put(f"/api/homeworks/{hw_id}", json={"content_json": content}).status_code == 200
    return hw_id


def _gate(client, hw_id, sid):
    return client.get(f"/api/runtime/homeworks/{hw_id}/gate-state?session_id={sid}").json()


def _cbp(client, hw_id, sid, idx, answer):
    return client.post("/api/ai/check-answer", json={
        "phase": "case_based_preview", "homework_id": hw_id, "session_id": sid,
        "item_index": idx, "student_answer": answer,
    }).json()


def _mc(client, hw_id, sid, idx, answer):
    return client.post("/api/ai/check-answer", json={
        "phase": "memory_check", "homework_id": hw_id, "session_id": sid,
        "item_index": idx, "student_answer": answer,
    }).json()


def test_fresh_session_is_fully_locked(client):
    hw_id = _make_v2_homework(client)
    g = _gate(client, hw_id, "fresh-sess")
    assert g["cbp"]["passed"] is False
    assert g["mc"]["passed"] is False
    assert g["practice_arc_unlocked"] is False


def test_cbp_alone_does_not_unlock(client):
    hw_id = _make_v2_homework(client)
    sid = "cbp-only"
    # 3/3 CBP correct (expected indices 1,0,1)
    assert _cbp(client, hw_id, sid, 0, "1")["correct"] is True
    assert _cbp(client, hw_id, sid, 1, "0")["correct"] is True
    assert _cbp(client, hw_id, sid, 2, "1")["correct"] is True
    g = _gate(client, hw_id, sid)
    assert g["cbp"]["passed"] is True
    assert g["mc"]["passed"] is False
    assert g["practice_arc_unlocked"] is False  # MC still pending


def test_mc_alone_does_not_unlock(client):
    hw_id = _make_v2_homework(client)
    sid = "mc-only"
    for i in range(3):
        assert _mc(client, hw_id, sid, i, "0")["correct"] is True
    g = _gate(client, hw_id, sid)
    assert g["mc"]["passed"] is True
    assert g["cbp"]["passed"] is False
    assert g["practice_arc_unlocked"] is False  # CBP still pending


def test_both_sections_unlock_practice_arc(client):
    hw_id = _make_v2_homework(client)
    sid = "both"
    for i, a in [(0, "1"), (1, "0"), (2, "1")]:
        _cbp(client, hw_id, sid, i, a)
    for i in range(3):
        _mc(client, hw_id, sid, i, "0")
    g = _gate(client, hw_id, sid)
    assert g["cbp"]["passed"] is True
    assert g["mc"]["passed"] is True
    assert g["practice_arc_unlocked"] is True


def test_cbp_soft_retry_last_attempt_wins(client):
    """Soft-retry: a later WRONG answer on a checkpoint overrides an earlier correct."""
    hw_id = _make_v2_homework(client)
    sid = "retry"
    _cbp(client, hw_id, sid, 0, "1")  # correct
    _cbp(client, hw_id, sid, 1, "0")  # correct
    _cbp(client, hw_id, sid, 2, "1")  # correct → 3/3
    assert _gate(client, hw_id, sid)["cbp"]["passed"] is True
    _cbp(client, hw_id, sid, 0, "0")  # now WRONG on ckp0 → 2/3
    g = _gate(client, hw_id, sid)
    assert g["cbp"]["checkpoints_correct"] == 2
    assert g["cbp"]["passed"] is True  # still ≥2/3 threshold


def test_mc_below_threshold_does_not_pass(client):
    hw_id = _make_v2_homework(client)
    sid = "mc-fail"
    _mc(client, hw_id, sid, 0, "0")  # correct
    _mc(client, hw_id, sid, 1, "1")  # wrong
    _mc(client, hw_id, sid, 2, "1")  # wrong  → 1/3 = 33% < 60%
    g = _gate(client, hw_id, sid)
    assert g["mc"]["score_pct"] < 60
    assert g["mc"]["passed"] is False


# ---------------------------------------------------------------------------
# CBP "Decision Process Explanation" gate interaction
# ---------------------------------------------------------------------------

_DPE_REASONING = {
    "prompt": "Explain which concept applies, why this method, and the mistake to avoid.",
    "min_chars": 80,
    "concept_keywords": ["force"],
    "method_keywords": ["diagram"],
    "mistake_keywords": ["friction"],
    "pass_score": 60,
}

_REASONING_TEXT = (
    "The key concept is force balance and I would use a free body diagram to "
    "lay out every force acting on the block, avoiding the friction mistake."
)


def _make_v2_homework_with_reasoning(client):
    hw_id = _make_v2_homework(client)
    # Re-PUT the content with the reasoning block added to case_based_preview.
    content = {
        "flow_version": "v2",
        "meta": {"title": "Gate flow HW + reasoning"},
        "case_based_preview": {
            "case_setup": {"story": "block on a ramp"},
            "checkpoints": [
                {"question": "Q1", "options": ["a", "b"], "answer_spec": {"type": "option_index", "expected": 1, "option_count": 2}},
                {"question": "Q2", "options": ["a", "b"], "answer_spec": {"type": "option_index", "expected": 0, "option_count": 2}},
                {"question": "Q3", "options": ["a", "b"], "answer_spec": {"type": "option_index", "expected": 1, "option_count": 2}},
            ],
            "decision_process_explanation": _DPE_REASONING,
        },
        "memory_check": {
            "pass_threshold_pct": 60,
            "items": [
                {"type": "mcq", "prompt": "M1", "options": ["x", "y"], "answer_spec": {"type": "option_index", "expected": 0, "option_count": 2}},
                {"type": "mcq", "prompt": "M2", "options": ["x", "y"], "answer_spec": {"type": "option_index", "expected": 0, "option_count": 2}},
                {"type": "mcq", "prompt": "M3", "options": ["x", "y"], "answer_spec": {"type": "option_index", "expected": 0, "option_count": 2}},
            ],
        },
    }
    assert client.put(f"/api/homeworks/{hw_id}", json={"content_json": content}).status_code == 200
    return hw_id


def _post_reasoning(client, hw_id, sid, text):
    return client.post("/api/ai/check-answer", json={
        "phase": "case_based_preview_reasoning", "homework_id": hw_id,
        "session_id": sid, "reasoning_text": text,
    }).json()


def test_cbp_gate_requires_reasoning_pass_when_present(client):
    """When a decision_process_explanation is authored, 3/3 MCQ alone does NOT
    pass the CBP gate — a passing reasoning attempt is also required. The
    reasoning attempt must NOT inflate checkpoints_correct past the MCQ count."""
    hw_id = _make_v2_homework_with_reasoning(client)
    sid = "reasoning-gate"

    async def _fake_high(*a, **k):
        return (90, "Aniq izoh.")

    # 3/3 MCQ correct (expected indices 1,0,1) — but no reasoning yet.
    assert _cbp(client, hw_id, sid, 0, "1")["correct"] is True
    assert _cbp(client, hw_id, sid, 1, "0")["correct"] is True
    assert _cbp(client, hw_id, sid, 2, "1")["correct"] is True

    g = _gate(client, hw_id, sid)
    assert g["cbp"]["checkpoints_correct"] == 3
    assert g["cbp"]["reasoning_required"] is True
    assert g["cbp"]["reasoning_passed"] is False
    assert g["cbp"]["passed"] is False  # MCQ done, reasoning still pending

    # Now submit a passing reasoning explanation (mock grader high + keywords).
    with patch.object(_ai_routes, "_grade_cbp_reasoning", new=_fake_high):
        r = _post_reasoning(client, hw_id, sid, _REASONING_TEXT)
    assert r["passed"] is True, r

    g2 = _gate(client, hw_id, sid)
    # Reasoning must NOT inflate the MCQ count.
    assert g2["cbp"]["checkpoints_correct"] == 3
    assert g2["cbp"]["reasoning_passed"] is True
    assert g2["cbp"]["passed"] is True


def test_cbp_gate_unaffected_when_no_reasoning_authored(client):
    """A homework with NO decision_process_explanation keeps the legacy gate:
    3/3 (or ≥2/3) MCQ passes CBP outright, reasoning_required is False."""
    hw_id = _make_v2_homework(client)  # no reasoning block
    sid = "no-reasoning-gate"
    assert _cbp(client, hw_id, sid, 0, "1")["correct"] is True
    assert _cbp(client, hw_id, sid, 1, "0")["correct"] is True
    assert _cbp(client, hw_id, sid, 2, "1")["correct"] is True
    g = _gate(client, hw_id, sid)
    assert g["cbp"]["reasoning_required"] is False
    assert g["cbp"]["reasoning_passed"] is False
    assert g["cbp"]["passed"] is True  # MCQ alone gates when no reasoning authored
