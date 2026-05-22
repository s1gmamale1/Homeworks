"""Regression fence: the practice-arc gate cannot be inflated via a
client-controlled `question_id` (SECURITY BLOCKER #2).

The CBP/MC handlers persist a SERVER-DERIVED `subphase` (`checkpoint_{idx}` /
`item_{idx}`, idx range-validated) but accept a CLIENT-supplied `question_id`.
The gate aggregation used to key on `question_id`, so a student could resubmit
the SAME item under different `question_id`s and inflate `checkpoints_correct`
/ `mc.correct` (MC could even exceed 100%).

The fix keys aggregation on `subphase` only. These tests submit the same item
index under 3 different `question_id`s (all correct) and assert the gate counts
the item exactly ONCE and score_pct never exceeds 100.

Harness mirrors tests/test_v2_gate_flow.py (drive everything through the real
/api/ai/check-answer + /gate-state endpoints against the temp DB).
"""

import pytest


def _make_v2_homework(client):
    hw = client.post(
        "/api/homeworks",
        json={"title": "No-inflation HW", "subject": "math-algebra", "grade": 6, "mode": "hard"},
    ).json()
    hw_id = hw["id"]
    content = {
        "flow_version": "v2",
        "meta": {"title": "No-inflation HW"},
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


def _submit(client, phase, hw_id, sid, idx, answer, question_id):
    """Submit one answer carrying a CLIENT-CONTROLLED question_id."""
    return client.post("/api/ai/check-answer", json={
        "phase": phase, "homework_id": hw_id, "session_id": sid,
        "item_index": idx, "student_answer": answer, "question_id": question_id,
    }).json()


def test_mc_question_id_spam_counts_item_once(client):
    hw_id = _make_v2_homework(client)
    sid = "mc-inflate"
    # Same item_index=0 (correct = "0"), submitted under 3 DIFFERENT question_ids.
    for qid in ("mc_item0", "spoofed-A", "spoofed-B"):
        res = _submit(client, "memory_check", hw_id, sid, 0, "0", qid)
        assert res["correct"] is True, res
    g = _gate(client, hw_id, sid)
    assert g["mc"]["correct"] == 1, f"item counted {g['mc']['correct']}× — gate inflated"
    assert g["mc"]["score_pct"] <= 100
    assert g["mc"]["total"] == 3


def test_cbp_question_id_spam_counts_checkpoint_once(client):
    hw_id = _make_v2_homework(client)
    sid = "cbp-inflate"
    # Same checkpoint idx=0 (correct = "1"), 3 different question_ids.
    for qid in ("cbp_ck0", "spoof-1", "spoof-2"):
        res = _submit(client, "case_based_preview", hw_id, sid, 0, "1", qid)
        assert res["correct"] is True, res
    g = _gate(client, hw_id, sid)
    assert g["cbp"]["checkpoints_correct"] == 1, (
        f"checkpoint counted {g['cbp']['checkpoints_correct']}× — gate inflated"
    )


def test_mc_full_spam_cannot_exceed_total_or_unlock(client):
    """Spam every item under many ids — score caps at 100, count never exceeds total."""
    hw_id = _make_v2_homework(client)
    sid = "mc-flood"
    for idx in range(3):
        for n in range(4):
            _submit(client, "memory_check", hw_id, sid, idx, "0", f"q-{idx}-{n}")
    g = _gate(client, hw_id, sid)
    assert g["mc"]["correct"] == 3       # exactly the 3 distinct items
    assert g["mc"]["score_pct"] == 100   # not >100
    assert g["mc"]["passed"] is True


def test_gate_state_rejects_trashed_homework(client):
    """Codex nit: gate-state must 409 a trashed homework like hydrate does."""
    hw_id = _make_v2_homework(client)
    assert client.delete(f"/api/homeworks/{hw_id}").status_code in (200, 204)
    resp = client.get(f"/api/runtime/homeworks/{hw_id}/gate-state?session_id=x")
    assert resp.status_code == 409, resp.text
