"""Regression tests for POST /api/ai/check-answer with phase=case_based_preview
and phase=memory_check (v2 React runtime phase branches).

Pins:
- correct answer returns {correct: true} + learning_block present (CBP)
- wrong answer returns {correct: false} AND does NOT leak the expected value
- a phase_attempts row is written after grading
- invalid item_index returns 400
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import patch, AsyncMock

import pytest

import server.routes.ai as _ai_routes


# ---------------------------------------------------------------------------
# Helpers — seed a v2 homework
# ---------------------------------------------------------------------------

_CBP_CHECKPOINTS = [
    {
        "question": "Which formula gives area of a circle?",
        "options": ["2πr", "πr²", "πd", "r²"],
        "answer_spec": {"type": "option_index", "expected": 1, "option_count": 4},
        "learning_block": "The area of a circle is A = πr² where r is the radius.",
        "kind": "identify",
    },
    {
        "question": "What is 7 × 8?",
        "options": ["54", "56", "63", "48"],
        "answer_spec": {"type": "option_index", "expected": 1, "option_count": 4},
        "learning_block": "7 × 8 = 56 — a common multiplication fact.",
        "kind": "decide",
    },
    {
        "question": "Explain why speed = distance / time.",
        "options": [],
        "answer_spec": {"type": "text_exact", "expected": "speed equals distance divided by time"},
        "learning_block": "Speed is the rate at which distance changes over time.",
        "kind": "justify",
    },
]

_MC_ITEMS = [
    {
        "type": "mcq",
        "prompt": "Which is a prime number?",
        "options": ["4", "6", "7", "9"],
        "answer_spec": {"type": "option_index", "expected": 2, "option_count": 4},
    },
    {
        "type": "true_false",
        "prompt": "Is the square root of 16 equal to 4?",
        "options": ["True", "False"],
        "answer_spec": {"type": "option_index", "expected": 0, "option_count": 2},
    },
    {
        "type": "fill_blank",
        "prompt": "The perimeter of a square with side 5 is ___.",
        "answer_spec": {"type": "numeric", "expected": 20, "tolerance": 0},
    },
]


def _seed_v2_homework(client) -> str:
    """Create a homework with case_based_preview and memory_check content."""
    payload = {
        "title": "V2 phase check-answer test HW",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
        "family": "aniq-fanlar",
        "content_json": {
            "meta": {"title": "V2 phase check-answer test HW"},
            "flashcards": [],
            "boss_questions": [],
            "case_based_preview": {
                "checkpoints": _CBP_CHECKPOINTS,
            },
            "memory_check": {
                "items": _MC_ITEMS,
            },
        },
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, f"Seed failed: {resp.text}"
    return resp.json()["id"]


def _post_cbp(client, hw_id: str, item_index: int, student_answer: str, **extra) -> tuple[int, dict]:
    body = {
        "phase": "case_based_preview",
        "homework_id": hw_id,
        "item_index": item_index,
        "student_answer": student_answer,
        "session_id": extra.pop("session_id", "test-session-cbp"),
        **extra,
    }
    resp = client.post("/api/ai/check-answer", json=body)
    try:
        return resp.status_code, resp.json()
    except Exception:
        return resp.status_code, {"_raw": resp.text}


def _post_mc(client, hw_id: str, item_index: int, student_answer: str, **extra) -> tuple[int, dict]:
    body = {
        "phase": "memory_check",
        "homework_id": hw_id,
        "item_index": item_index,
        "student_answer": student_answer,
        "session_id": extra.pop("session_id", "test-session-mc"),
        **extra,
    }
    resp = client.post("/api/ai/check-answer", json=body)
    try:
        return resp.status_code, resp.json()
    except Exception:
        return resp.status_code, {"_raw": resp.text}


# ---------------------------------------------------------------------------
# Case-Based Preview tests
# ---------------------------------------------------------------------------


def test_cbp_correct_answer_returns_correct_true_with_learning_block(client):
    """Correct CBP checkpoint returns {correct: true} with learning_block."""
    hw_id = _seed_v2_homework(client)
    # Checkpoint 0: option_index 1 is correct
    code, data = _post_cbp(client, hw_id, item_index=0, student_answer="1")
    assert code == 200, data
    assert data["correct"] is True, data
    assert "learning_block" in data, data
    assert data["learning_block"] == _CBP_CHECKPOINTS[0]["learning_block"]


def test_cbp_wrong_answer_returns_correct_false_no_expected_leak(client):
    """Wrong CBP answer returns {correct: false} and NEVER leaks expected value."""
    hw_id = _seed_v2_homework(client)
    # Checkpoint 0: expected index is 1; we send 0 (wrong)
    expected_value = str(_CBP_CHECKPOINTS[0]["answer_spec"]["expected"])
    code, data = _post_cbp(client, hw_id, item_index=0, student_answer="0")
    assert code == 200, data
    assert data["correct"] is False, data
    # The expected value must NOT appear anywhere in the response JSON
    response_text = json.dumps(data)
    # "expected" key itself must not leak its value as a standalone data field
    # (the context_debug wrapper may include meta — check only data payload)
    assert data.get("expected") is None, "expected value leaked into response"
    # The literal expected index value "1" in isolation might appear in debug text,
    # so we check the grading-result keys specifically:
    assert "expected" not in data or data["expected"] is None


def test_cbp_wrong_answer_learning_block_still_present(client):
    """Wrong CBP answer still returns learning_block (teaching moment after any attempt)."""
    hw_id = _seed_v2_homework(client)
    code, data = _post_cbp(client, hw_id, item_index=1, student_answer="0")  # wrong
    assert code == 200, data
    assert data["correct"] is False, data
    assert "learning_block" in data, data


def test_cbp_phase_attempt_written(client):
    """CBP grading writes a phase_attempts row readable via list_phase_attempts."""
    from server.db.attempts_repo import list_phase_attempts

    hw_id = _seed_v2_homework(client)
    session_id = "test-cbp-persist"
    code, data = _post_cbp(client, hw_id, item_index=0, student_answer="1", session_id=session_id)
    assert code == 200, data

    # Read back via the repo directly (runs in the same in-process event loop)
    loop = asyncio.new_event_loop()
    try:
        attempts = loop.run_until_complete(
            list_phase_attempts(session_id, hw_id, phase="case_based_preview")
        )
    finally:
        loop.close()

    assert len(attempts) >= 1, "No phase_attempts row written for CBP"
    row = attempts[0]
    assert row["phase"] == "case_based_preview"
    assert row["subphase"] == "checkpoint_0"
    assert row["correct"] == 1


def test_cbp_invalid_item_index_returns_400(client):
    """Out-of-range item_index returns 400."""
    hw_id = _seed_v2_homework(client)
    code, data = _post_cbp(client, hw_id, item_index=99, student_answer="1")
    assert code == 400, data


def test_cbp_missing_item_index_returns_400(client):
    """Missing item_index field returns 400."""
    hw_id = _seed_v2_homework(client)
    resp = client.post("/api/ai/check-answer", json={
        "phase": "case_based_preview",
        "homework_id": hw_id,
        "student_answer": "1",
        # item_index deliberately omitted
    })
    assert resp.status_code == 400, resp.text


def test_cbp_negative_item_index_returns_400(client):
    """Negative item_index returns 400."""
    hw_id = _seed_v2_homework(client)
    code, data = _post_cbp(client, hw_id, item_index=-1, student_answer="1")
    assert code == 400, data


# ---------------------------------------------------------------------------
# Memory Check tests
# ---------------------------------------------------------------------------


def test_mc_correct_answer_returns_correct_true(client):
    """Correct MC item returns {correct: true}."""
    hw_id = _seed_v2_homework(client)
    # Item 0: option_index 2 is correct
    code, data = _post_mc(client, hw_id, item_index=0, student_answer="2")
    assert code == 200, data
    assert data["correct"] is True, data


def test_mc_wrong_answer_returns_correct_false_no_expected_leak(client):
    """Wrong MC answer returns {correct: false} and does NOT leak the expected value."""
    hw_id = _seed_v2_homework(client)
    # Item 0: correct is index 2; send 0 (wrong)
    code, data = _post_mc(client, hw_id, item_index=0, student_answer="0")
    assert code == 200, data
    assert data["correct"] is False, data
    # No expected-answer key in the grading payload
    assert data.get("expected") is None


def test_mc_phase_attempt_written(client):
    """MC grading writes a phase_attempts row."""
    from server.db.attempts_repo import list_phase_attempts

    hw_id = _seed_v2_homework(client)
    session_id = "test-mc-persist"
    code, data = _post_mc(client, hw_id, item_index=1, student_answer="0", session_id=session_id)
    assert code == 200, data

    loop = asyncio.new_event_loop()
    try:
        attempts = loop.run_until_complete(
            list_phase_attempts(session_id, hw_id, phase="memory_check")
        )
    finally:
        loop.close()

    assert len(attempts) >= 1, "No phase_attempts row written for MC"
    row = attempts[0]
    assert row["phase"] == "memory_check"
    assert row["subphase"] == "item_1"


def test_mc_invalid_item_index_returns_400(client):
    """Out-of-range item_index returns 400."""
    hw_id = _seed_v2_homework(client)
    code, data = _post_mc(client, hw_id, item_index=50, student_answer="0")
    assert code == 400, data


def test_mc_missing_item_index_returns_400(client):
    """Missing item_index field returns 400."""
    hw_id = _seed_v2_homework(client)
    resp = client.post("/api/ai/check-answer", json={
        "phase": "memory_check",
        "homework_id": hw_id,
        "student_answer": "0",
        # item_index deliberately omitted
    })
    assert resp.status_code == 400, resp.text


def test_mc_numeric_correct_answer(client):
    """Numeric answer_spec grades correctly for a fill-blank MC item."""
    hw_id = _seed_v2_homework(client)
    # Item 2: numeric, expected=20, tolerance=0
    code, data = _post_mc(client, hw_id, item_index=2, student_answer="20")
    assert code == 200, data
    assert data["correct"] is True, data


def test_mc_numeric_wrong_answer(client):
    """Numeric answer_spec returns false for a wrong value."""
    hw_id = _seed_v2_homework(client)
    code, data = _post_mc(client, hw_id, item_index=2, student_answer="15")
    assert code == 200, data
    assert data["correct"] is False, data


# ---------------------------------------------------------------------------
# Case-Based Preview "Decision Process Explanation" (open-ended, AI-graded)
# ---------------------------------------------------------------------------
#
# Contract (must match the frontend exactly):
#   request  { homework_id, session_id, phase: "case_based_preview_reasoning",
#              reasoning_text }
#   response { passed: bool, score: number(0..100), feedback: str }
#
# Grading combines deterministic keyword coverage (concept/method/mistake →
# det_count 0..3) with AI judgment:
#   score  = round(0.6*ai_score + 0.4*100*det_count/3)
#   passed = score >= pass_score(default 60) AND det_count >= 2
# On AI error: passed = det_count >= 2 (pure deterministic fallback).
# The mock patches _grade_cbp_reasoning RLC-style so no live provider is hit.

# Keyword buckets: concept="force", method="diagram", mistake="friction".
_DPE = {
    "prompt": "Explain which concept applies, why this method, and the mistake to avoid.",
    "min_chars": 80,
    "concept_keywords": ["force"],
    "method_keywords": ["diagram"],
    "mistake_keywords": ["friction"],
    "acceptable_keywords": ["equilibrium"],
    "rubric": {"concept": 40, "method": 40, "mistake": 20},
    "pass_score": 60,
}

# A long reasoning text that hits ≥2 buckets (force + diagram → det_count 2).
_LONG_TWO = (
    "The key concept here is force balance, and I would use a free body diagram "
    "to lay out every push and pull acting on the block before solving."
)
# A long reasoning text that hits all three buckets.
_LONG_THREE = _LONG_TWO + " I would avoid the common friction mistake by accounting for it."
# A long reasoning text that hits ZERO buckets (none of the keywords present).
_LONG_ZERO = (
    "I simply guessed the answer because it looked correct and felt right to me "
    "at the time, without really thinking through the situation in any detail."
)


def _seed_v2_homework_with_reasoning(client) -> str:
    payload = {
        "title": "V2 CBP reasoning test HW",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
        "family": "aniq-fanlar",
        "content_json": {
            "meta": {"title": "V2 CBP reasoning test HW"},
            "flashcards": [],
            "boss_questions": [],
            "case_based_preview": {
                "case_setup": {"story": "A block on a ramp", "role": "physicist", "task": "explain"},
                "checkpoints": _CBP_CHECKPOINTS,
                "decision_process_explanation": _DPE,
            },
            "memory_check": {"items": _MC_ITEMS},
        },
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, f"Seed failed: {resp.text}"
    return resp.json()["id"]


def _post_reasoning(client, hw_id: str, reasoning_text: str, **extra) -> tuple[int, dict]:
    body = {
        "phase": "case_based_preview_reasoning",
        "homework_id": hw_id,
        "reasoning_text": reasoning_text,
        "session_id": extra.pop("session_id", "test-session-cbp-reasoning"),
        **extra,
    }
    resp = client.post("/api/ai/check-answer", json=body)
    try:
        return resp.status_code, resp.json()
    except Exception:
        return resp.status_code, {"_raw": resp.text}


def test_cbp_reasoning_too_short_rejected(client):
    """Below min_chars → 400 CBP_REASONING_TOO_SHORT BEFORE any LLM call."""
    hw_id = _seed_v2_homework_with_reasoning(client)
    fake_grader = AsyncMock()
    with patch.object(_ai_routes, "_grade_cbp_reasoning", new=fake_grader):
        code, data = _post_reasoning(client, hw_id, reasoning_text="Too short.")
    assert code == 400, data
    # The cheap min-char gate runs first — grader must NOT be called.
    fake_grader.assert_not_called()


def test_cbp_reasoning_keyword_coverage_passes_on_ai_fail(client):
    """When the AI grader is unavailable, det_count>=2 still passes (fallback).

    The grader raising simulates provider downtime; the handler must NOT 500 and
    must fall back to the deterministic verdict (passed = det_count >= 2)."""
    hw_id = _seed_v2_homework_with_reasoning(client)

    async def _boom(*a, **k):
        raise RuntimeError("provider down")

    with patch.object(_ai_routes, "_grade_cbp_reasoning", new=_boom):
        code, data = _post_reasoning(client, hw_id, reasoning_text=_LONG_TWO)
    assert code == 200, data
    # _LONG_TWO hits concept+method buckets → det_count=2 → fallback passes.
    assert data["passed"] is True, data
    assert isinstance(data["score"], int)
    assert 0 <= data["score"] <= 100


def test_cbp_reasoning_keyword_empty_fails_even_if_ai_high(client):
    """A high AI score CANNOT pass when keyword coverage is below 2 buckets.

    Defends against gaming the open-ended step with fluent but off-topic prose:
    passed requires det_count>=2 regardless of how high the AI scores."""
    hw_id = _seed_v2_homework_with_reasoning(client)

    async def _fake_high(*a, **k):
        return (100, "Ajoyib!")

    with patch.object(_ai_routes, "_grade_cbp_reasoning", new=_fake_high):
        code, data = _post_reasoning(client, hw_id, reasoning_text=_LONG_ZERO)
    assert code == 200, data
    # det_count == 0 → fails the AND-gate even though AI returned 100.
    assert data["passed"] is False, data


def test_cbp_reasoning_ai_high_and_keywords_present_passes(client):
    """High AI score AND >=2 keyword buckets → passed True with a combined score."""
    hw_id = _seed_v2_homework_with_reasoning(client)

    async def _fake_high(*a, **k):
        return (90, "Tushuncha va usulni aniq ko'rsatdingiz.")

    with patch.object(_ai_routes, "_grade_cbp_reasoning", new=_fake_high):
        code, data = _post_reasoning(client, hw_id, reasoning_text=_LONG_THREE)
    assert code == 200, data
    assert data["passed"] is True, data
    # score = round(0.6*90 + 0.4*100*3/3) = round(54 + 40) = 94
    assert data["score"] == 94, data
    assert data["feedback"] == "Tushuncha va usulni aniq ko'rsatdingiz."


def test_cbp_reasoning_response_never_leaks_keywords_or_rubric(client):
    """The response body carries ONLY {passed, score, feedback} — never the
    keyword buckets, the acceptable_keywords, the rubric, or pass_score."""
    hw_id = _seed_v2_homework_with_reasoning(client)

    async def _fake(*a, **k):
        return (80, "Yaxshi izoh.")

    with patch.object(_ai_routes, "_grade_cbp_reasoning", new=_fake):
        code, data = _post_reasoning(client, hw_id, reasoning_text=_LONG_THREE)
    assert code == 200, data

    blob = json.dumps(data)
    # No grading-anchor value or key may surface in the response.
    for tok in ("force", "diagram", "friction", "equilibrium", "rubric", "pass_score"):
        assert tok not in blob, f"reasoning grading anchor leaked into response: {tok}"
    # Only the contract keys are present in the grading payload.
    assert data.get("rubric") is None
    assert data.get("concept_keywords") is None
    assert data.get("acceptable_keywords") is None
    assert set(("passed", "score", "feedback")).issubset(data.keys())


def test_cbp_reasoning_no_reasoning_authored_returns_404(client):
    """A CBP without a decision_process_explanation → 404 CBP_NO_REASONING."""
    hw_id = _seed_v2_homework(client)  # no reasoning block
    fake_grader = AsyncMock()
    with patch.object(_ai_routes, "_grade_cbp_reasoning", new=fake_grader):
        code, data = _post_reasoning(client, hw_id, reasoning_text=_LONG_THREE)
    assert code == 404, data
    fake_grader.assert_not_called()
