"""
Wave A2 — AI runtime smoke tests.

Verifies that all 4 AI tutor endpoints plus the status endpoint:
  1. Accept the exact request bodies sent by runtime.js
  2. Return HTTP 200
  3. Return valid JSON
  4. Contain the top-level keys that runtime.js destructures

Shape contracts are taken from runtime.js FALLBACK objects and JSDoc
return annotations, NOT from tutor.py — so any divergence between Python
output and JS expectations is flagged as a bug here.

Run:
    # No-AI tests only (no creds needed):
    pytest tests/test_ai_runtime.py -v -m "not requires_ai"

    # Full suite (requires Vertex / Gemini / Kimi):
    VERTEX_CREDENTIALS_PATH=/path/to/key.json pytest tests/test_ai_runtime.py -v

After a run, tests/last_run_report.json is written with per-test latency.
"""
import json
import os
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"
REPORT_PATH = Path(__file__).parent / "last_run_report.json"

_report: dict[str, Any] = {}


def _load_payloads() -> dict:
    with open(FIXTURES_DIR / "ai_payloads.json", encoding="utf-8") as f:
        return json.load(f)


def _record(name: str, status_code: int, elapsed_ms: float, notes: str = "") -> None:
    _report[name] = {
        "status_code": status_code,
        "elapsed_ms": round(elapsed_ms, 1),
        "notes": notes,
    }


def _flush_report() -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(_report, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# No-AI tests (run without any credentials)
# ---------------------------------------------------------------------------


def test_ai_status_no_creds(client):
    """
    GET /api/ai/status must return 200 and the required top-level keys
    regardless of whether any AI backend is configured.

    runtime.js does NOT call this endpoint, but the builder's "Test Tutor"
    button reads: backend, model_fast, model_pro.
    """
    t0 = time.perf_counter()
    resp = client.get("/api/ai/status")
    elapsed = (time.perf_counter() - t0) * 1000

    _record("status", resp.status_code, elapsed)
    _flush_report()

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert isinstance(data, dict), "Response must be a JSON object"

    required_keys = {"backend", "model_fast", "model_pro"}
    missing = required_keys - data.keys()
    assert not missing, f"/api/ai/status missing keys: {missing}"

    valid_backends = {"vertex", "gemini_api", "kimi", "none"}
    assert data["backend"] in valid_backends, (
        f"backend '{data['backend']}' not in {valid_backends}"
    )


# ---------------------------------------------------------------------------
# Hybrid Routing tests (No real AI required, uses mocking)
# ---------------------------------------------------------------------------

@patch("server.services.gemini.generate_json")
def test_check_answer_deterministic(mock_generate, client):
    """
    Deterministic path should not call AI and return immediately.
    """
    payload = {
        "question_id": "test-1",
        "question": "2+2",
        "student_answer": "4",
        "answer_spec": {"type": "numeric", "expected": 4.0},
        "subject": "math",
        "grade": 8
    }
    resp = client.post("/api/ai/check-answer", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["correct"] is True
    assert data["source"] == "deterministic"
    mock_generate.assert_not_called()

@patch("server.services.gemini.generate_json")
def test_check_answer_ai_fallback_high_confidence(mock_generate, client):
    """
    AI path high confidence -> source='ai', cached
    """
    mock_generate.return_value = {
        "correct": False,
        "score": 0.0,
        "feedback": "No, it is 5.",
        "matched_expected": None,
        "confidence": 0.95
    }
    payload = {
        "question_id": "test-2",
        "question": "2+3",
        "student_answer": "4",
        "answer_spec": {"type": "text_exact", "expected": "5"}, 
        "subject": "math",
        "grade": 8
    }
    resp = client.post("/api/ai/check-answer", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["correct"] is False
    assert data["source"] == "ai"
    mock_generate.assert_called_once()
    
    # Second call should hit cache
    mock_generate.reset_mock()
    resp2 = client.post("/api/ai/check-answer", json=payload)
    assert resp2.status_code == 200
    assert resp2.json()["source"] == "ai"
    mock_generate.assert_not_called()

@patch("server.services.gemini.generate_json")
def test_check_answer_ai_fallback_low_confidence(mock_generate, client):
    """
    AI path low confidence -> source='ai_unsure', correct based on phase, needs_review=True, queued
    """
    mock_generate.return_value = {
        "correct": False,
        "score": 0.0,
        "feedback": "I am not sure.",
        "matched_expected": None,
        "confidence": 0.8
    }
    # Test boss phase
    payload = {
        "question_id": "boss-1",
        "question": "Explain quantum mechanics",
        "student_answer": "It is hard",
        "answer_spec": {"type": "semantic"}, 
        "subject": "physics",
        "grade": 11
    }
    resp = client.post("/api/ai/check-answer", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["correct"] is True
    assert data["score"] == 0.7
    assert data["source"] == "ai_unsure"
    assert data["needs_review"] is True
    
    # Check review queue
    q_resp = client.get("/api/review-queue")
    assert q_resp.status_code == 200
    queue = q_resp.json()
    assert len(queue) > 0
    item = [x for x in queue if x["question_id"] == "boss-1"][0]
    
    # Resolve it
    res_resp = client.post(f"/api/review-queue/{item['id']}/decide", json={"correct": False, "score": 0.0, "feedback": "Bad"})
    assert res_resp.status_code == 200
    
    q_resp2 = client.get("/api/review-queue")
    assert len([x for x in q_resp2.json() if x["question_id"] == "boss-1"]) == 0

# ---------------------------------------------------------------------------
# AI-requiring tests
# ---------------------------------------------------------------------------


@pytest.mark.requires_ai
def test_check_answer(client):
    """
    POST /api/ai/check-answer

    runtime.js expects: { correct, score, feedback, matched_expected }
    (from FALLBACK.answer and JSDoc on checkAnswer)

    Bug watch: tutor.py schema uses `matched_expected` (snake_case) —
    runtime.js also uses `matched_expected`. These match — no divergence.
    """
    payloads = _load_payloads()
    body = payloads["check_answer"]

    t0 = time.perf_counter()
    resp = client.post("/api/ai/check-answer", json=body)
    elapsed = (time.perf_counter() - t0) * 1000

    notes = ""
    try:
        data = resp.json()
    except Exception as e:
        data = {}
        notes = f"JSON parse error: {e}"

    _record("check_answer", resp.status_code, elapsed, notes)
    _flush_report()

    assert resp.status_code == 200, (
        f"check-answer returned {resp.status_code}: {resp.text}"
    )
    assert isinstance(data, dict), "Response must be a JSON object"

    # runtime.js FALLBACK.answer shape: { correct, score, feedback, matched_expected }
    required_keys = {"correct", "score", "feedback", "matched_expected"}
    missing = required_keys - data.keys()
    assert not missing, (
        f"BUG: /api/ai/check-answer missing keys expected by runtime.js: {missing}\n"
        f"Got keys: {set(data.keys())}"
    )

    # Type checks
    assert isinstance(data["correct"], bool), (
        f"'correct' must be bool, got {type(data['correct'])}"
    )
    assert isinstance(data["score"], (int, float)), (
        f"'score' must be numeric, got {type(data['score'])}"
    )
    assert 0.0 <= float(data["score"]) <= 1.0, (
        f"'score' must be 0–1, got {data['score']}"
    )
    assert isinstance(data["feedback"], str) and data["feedback"], (
        "'feedback' must be a non-empty string"
    )
    # matched_expected may be null
    assert data["matched_expected"] is None or isinstance(data["matched_expected"], str), (
        f"'matched_expected' must be str or null, got {type(data['matched_expected'])}"
    )


@pytest.mark.requires_ai
def test_boss_turn(client):
    """
    POST /api/ai/boss-turn

    runtime.js expects: { correct, damage_dealt, boss_response, hint, score }
    (from FALLBACK.boss and JSDoc on bossTurn)

    Bug watch: tutor.py schema matches runtime.js exactly — no divergence detected.
    """
    payloads = _load_payloads()
    body = payloads["boss_turn"]

    t0 = time.perf_counter()
    resp = client.post("/api/ai/boss-turn", json=body)
    elapsed = (time.perf_counter() - t0) * 1000

    notes = ""
    try:
        data = resp.json()
    except Exception as e:
        data = {}
        notes = f"JSON parse error: {e}"

    _record("boss_turn", resp.status_code, elapsed, notes)
    _flush_report()

    assert resp.status_code == 200, (
        f"boss-turn returned {resp.status_code}: {resp.text}"
    )
    assert isinstance(data, dict), "Response must be a JSON object"

    # runtime.js FALLBACK.boss shape: { correct, damage_dealt, boss_response, hint, score }
    required_keys = {"correct", "damage_dealt", "boss_response", "hint", "score"}
    missing = required_keys - data.keys()
    assert not missing, (
        f"BUG: /api/ai/boss-turn missing keys expected by runtime.js: {missing}\n"
        f"Got keys: {set(data.keys())}"
    )

    assert isinstance(data["correct"], bool), (
        f"'correct' must be bool, got {type(data['correct'])}"
    )
    assert isinstance(data["damage_dealt"], int), (
        f"'damage_dealt' must be int, got {type(data['damage_dealt'])}"
    )
    assert data["damage_dealt"] in (0, body["damage_value"]), (
        f"'damage_dealt' must be 0 or damage_value ({body['damage_value']}), got {data['damage_dealt']}"
    )
    assert isinstance(data["boss_response"], str) and data["boss_response"], (
        "'boss_response' must be a non-empty string"
    )
    # hint is null on attempt_number=1 or when correct
    assert data["hint"] is None or isinstance(data["hint"], str), (
        f"'hint' must be str or null, got {type(data['hint'])}"
    )
    assert isinstance(data["score"], (int, float)), (
        f"'score' must be numeric, got {type(data['score'])}"
    )
    assert 0.0 <= float(data["score"]) <= 1.0, (
        f"'score' must be 0–1, got {data['score']}"
    )


@pytest.mark.requires_ai
def test_reflection(client):
    """
    POST /api/ai/reflection

    runtime.js expects: { feedback, next_steps, encouragement }
    (from FALLBACK.reflection and JSDoc on reflectionFeedback)

    Bug watch: tutor.py returns `next_steps` as list[str]. runtime.js FALLBACK
    seeds it as []. Shapes match — no divergence.
    """
    payloads = _load_payloads()
    body = payloads["reflection"]

    t0 = time.perf_counter()
    resp = client.post("/api/ai/reflection", json=body)
    elapsed = (time.perf_counter() - t0) * 1000

    notes = ""
    try:
        data = resp.json()
    except Exception as e:
        data = {}
        notes = f"JSON parse error: {e}"

    _record("reflection", resp.status_code, elapsed, notes)
    _flush_report()

    assert resp.status_code == 200, (
        f"reflection returned {resp.status_code}: {resp.text}"
    )
    assert isinstance(data, dict), "Response must be a JSON object"

    # runtime.js FALLBACK.reflection: { feedback, next_steps, encouragement }
    required_keys = {"feedback", "next_steps", "encouragement"}
    missing = required_keys - data.keys()
    assert not missing, (
        f"BUG: /api/ai/reflection missing keys expected by runtime.js: {missing}\n"
        f"Got keys: {set(data.keys())}"
    )

    assert isinstance(data["feedback"], str) and data["feedback"], (
        "'feedback' must be a non-empty string"
    )
    assert isinstance(data["next_steps"], list), (
        f"'next_steps' must be a list, got {type(data['next_steps'])}"
    )
    assert 1 <= len(data["next_steps"]) <= 5, (
        f"'next_steps' should have 1–5 items, got {len(data['next_steps'])}"
    )
    assert all(isinstance(s, str) for s in data["next_steps"]), (
        "'next_steps' items must all be strings"
    )
    assert isinstance(data["encouragement"], str) and data["encouragement"], (
        "'encouragement' must be a non-empty string"
    )


@pytest.mark.requires_ai
def test_tutor(client):
    """
    POST /api/ai/tutor

    runtime.js expects: { response, guidance_type }
    (from FALLBACK.tutor and JSDoc on tutor)

    Bug watch: tutor.py schema uses `guidance_type` with values
    hint|explanation|encouragement|correction. runtime.js FALLBACK seeds
    `guidance_type: 'encouragement'`. Shapes match — no divergence.
    """
    payloads = _load_payloads()
    body = payloads["tutor"]

    t0 = time.perf_counter()
    resp = client.post("/api/ai/tutor", json=body)
    elapsed = (time.perf_counter() - t0) * 1000

    notes = ""
    try:
        data = resp.json()
    except Exception as e:
        data = {}
        notes = f"JSON parse error: {e}"

    _record("tutor", resp.status_code, elapsed, notes)
    _flush_report()

    assert resp.status_code == 200, (
        f"tutor returned {resp.status_code}: {resp.text}"
    )
    assert isinstance(data, dict), "Response must be a JSON object"

    # runtime.js FALLBACK.tutor: { response, guidance_type }
    required_keys = {"response", "guidance_type"}
    missing = required_keys - data.keys()
    assert not missing, (
        f"BUG: /api/ai/tutor missing keys expected by runtime.js: {missing}\n"
        f"Got keys: {set(data.keys())}"
    )

    assert isinstance(data["response"], str) and data["response"], (
        "'response' must be a non-empty string"
    )
    valid_guidance = {"hint", "explanation", "encouragement", "correction"}
    assert data["guidance_type"] in valid_guidance, (
        f"'guidance_type' must be one of {valid_guidance}, got '{data['guidance_type']}'"
    )


# ---------------------------------------------------------------------------
# Latency / report summary test (always runs last)
# ---------------------------------------------------------------------------


def test_report_written():
    """
    Verify that last_run_report.json was written.
    This test always passes but ensures the artifact is present.
    """
    # Write whatever we have collected so far (may be partial if AI tests skipped)
    _flush_report()
    assert REPORT_PATH.exists(), f"Expected {REPORT_PATH} to exist after test run"
    with open(REPORT_PATH, encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict)
    # Print a summary for CI logs
    print("\n=== Wave A2 latency report ===")
    for name, entry in data.items():
        print(
            f"  {name:20s}  HTTP {entry.get('status_code', '---')}  "
            f"{entry.get('elapsed_ms', 0):.0f} ms"
            + (f"  [{entry['notes']}]" if entry.get("notes") else "")
        )
