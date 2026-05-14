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

    # Full suite (requires Kimi):
    KIMI_API_KEY=... pytest tests/test_ai_runtime.py -v

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


def _wipe_tables() -> None:
    import asyncio
    import os
    import aiosqlite

    db_path = os.environ.get("NETS_DB_PATH")
    if not db_path:
        return

    async def _do() -> None:
        async with aiosqlite.connect(db_path) as db:
            await db.execute("DELETE FROM answer_cache")
            await db.execute("DELETE FROM review_queue")
            await db.execute("DELETE FROM responses")
            await db.commit()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_do())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


@pytest.fixture(autouse=True)
def clean_db():
    _wipe_tables()
    yield


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

@patch("server.services.ai_orchestrator.generate_json")
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

@patch("server.services.ai_orchestrator.generate_json")
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
        "answer_spec": {"type": "semantic", "expected": "5"}, 
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

@patch("server.services.ai_orchestrator.generate_json")
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
    # Test boss phase — must pass phase="boss" explicitly. The legacy
    # question_id.startswith("boss") fallback was removed because it allowed
    # callers to bypass practice-grading by crafting the question_id.
    payload = {
        "question_id": "boss-1",
        "question": "Explain quantum mechanics",
        "student_answer": "It is hard",
        "answer_spec": {"type": "semantic"},
        "subject": "physics",
        "grade": 11,
        "phase": "boss",
    }
    resp = client.post("/api/ai/check-answer", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["correct"] is True
    assert data["score"] == 0.7
    assert data["source"] == "ai_unsure"
    assert data["needs_review"] is True
    
    # Check review queue
    q_resp = client.get("/api/ai/review-queue")
    assert q_resp.status_code == 200
    queue = q_resp.json()
    assert len(queue) > 0
    item = [x for x in queue if x["question_id"] == "boss-1"][0]

    # Resolve it
    res_resp = client.post(f"/api/ai/review-queue/{item['id']}/decide", json={"correct": False, "score": 0.0, "feedback": "Bad"})
    assert res_resp.status_code == 200

    q_resp2 = client.get("/api/ai/review-queue")
    assert len([x for x in q_resp2.json() if x["question_id"] == "boss-1"]) == 0


def test_review_queue_decide_404(client):
    """Resolving a non-existent or already-resolved review item must return 404."""
    resp = client.post(
        "/api/ai/review-queue/999999/decide",
        json={"correct": True, "score": 1.0, "feedback": "ok"},
    )
    assert resp.status_code == 404


@patch("server.services.ai_orchestrator.generate_json")
def test_review_queue_decision_persists(mock_generate, client):
    """The teacher's decision must be stored on the row, not silently discarded.

    Regression guard for the round-3 reviewer finding: resolve_review_item used
    to only flip status='resolved'; {correct, score, feedback} were dropped.
    """
    import asyncio
    import json
    from server import db

    mock_generate.return_value = {
        "correct": False,
        "score": 0.0,
        "feedback": "I am not sure.",
        "matched_expected": None,
        "confidence": 0.7,
    }
    # Drive an answer into the review queue (boss phase, low-confidence AI).
    queue_resp = client.post(
        "/api/ai/check-answer",
        json={
            "question_id": "boss-decide-persist",
            "question": "Why?",
            "student_answer": "Dunno",
            "answer_spec": {"type": "semantic"},
            "subject": "physics",
            "grade": 11,
        },
    )
    assert queue_resp.status_code == 200
    assert queue_resp.json().get("needs_review") is True

    queue = client.get("/api/ai/review-queue").json()
    item = next(x for x in queue if x["question_id"] == "boss-decide-persist")

    decision = {"correct": True, "score": 0.85, "feedback": "Acceptable answer; format off."}
    res = client.post(f"/api/ai/review-queue/{item['id']}/decide", json=decision)
    assert res.status_code == 200

    # Read the row directly so we verify what's on disk, not what the API returns.
    async def fetch_row():
        conn = await db.connect()
        try:
            cur = await conn.execute(
                "SELECT status, decision_json, resolved_at FROM review_queue WHERE id = ?",
                (item["id"],),
            )
            return await cur.fetchone()
        finally:
            await conn.close()

    row = asyncio.run(fetch_row())
    assert row["status"] == "resolved"
    assert row["resolved_at"] is not None and row["resolved_at"] != ""
    stored = json.loads(row["decision_json"])
    assert stored == decision  # full payload survived round-trip


@patch("server.services.ai_orchestrator.generate_json")
def test_check_answer_no_ai_fallback(mock_generate, client):
    """allow_ai_fallback=False on an unsure deterministic verdict must short-circuit."""
    payload = {
        "question_id": "test-no-ai",
        "question": "Free-form answer",
        "student_answer": "something",
        "answer_spec": {"type": "semantic"},
        "allow_ai_fallback": False,
        "subject": "history",
        "grade": 8,
    }
    resp = client.post("/api/ai/check-answer", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "deterministic"
    assert data["correct"] is False
    mock_generate.assert_not_called()


@patch("server.services.ai_orchestrator.generate_json")
def test_check_answer_always_returns_matched_expected_key(mock_generate, client):
    """
    Regression: every check_answer return path MUST include matched_expected
    key (even if None). runtime.js destructures it unconditionally; missing
    key broke prod (see triage 2026-04-29).

    This test parametrizes over three critical paths:
      1. deterministic_success: verdict={correct,incorrect}
      2. no_fallback: allow_ai_fallback=False on unsure verdict
      3. ai_unsure: high-quality AI but low confidence (<0.90)
    """
    # Test 1: Deterministic success path
    payload_det = {
        "question_id": "test-matched-det",
        "question": "2+2",
        "student_answer": "4",
        "answer_spec": {"type": "numeric", "expected": 4.0},
        "subject": "math",
        "grade": 8
    }
    resp = client.post("/api/ai/check-answer", json=payload_det)
    assert resp.status_code == 200
    data = resp.json()
    assert "matched_expected" in data, (
        "deterministic_success path dropped matched_expected key — "
        "this regressed prod once already, see PR #50"
    )
    assert data["source"] == "deterministic"
    mock_generate.assert_not_called()

    # Test 2: No-fallback path (allow_ai_fallback=False on unsure verdict)
    payload_no_fallback = {
        "question_id": "test-matched-nofb",
        "question": "Free-form answer",
        "student_answer": "something",
        "answer_spec": {"type": "semantic"},
        "allow_ai_fallback": False,
        "subject": "history",
        "grade": 8,
    }
    resp = client.post("/api/ai/check-answer", json=payload_no_fallback)
    assert resp.status_code == 200
    data = resp.json()
    assert "matched_expected" in data, (
        "no_fallback path dropped matched_expected key — "
        "this regressed prod once already, see PR #50"
    )
    assert data["source"] == "deterministic"
    mock_generate.assert_not_called()

    # Test 3: AI unsure path (low confidence)
    mock_generate.return_value = {
        "correct": False,
        "score": 0.0,
        "feedback": "I am not sure.",
        "matched_expected": None,
        "confidence": 0.8  # Low confidence triggers ai_unsure branch
    }
    payload_unsure = {
        "question_id": "test-matched-unsure",
        "question": "Explain concept",
        "student_answer": "my answer",
        "answer_spec": {"type": "semantic"},
        "subject": "physics",
        "grade": 11
    }
    resp = client.post("/api/ai/check-answer", json=payload_unsure)
    assert resp.status_code == 200
    data = resp.json()
    assert "matched_expected" in data, (
        "ai_unsure path dropped matched_expected key — "
        "this regressed prod once already, see PR #50"
    )
    assert data["source"] == "ai_unsure"
    mock_generate.assert_called_once()


@patch("server.services.ai_orchestrator.generate_json")
def test_cache_key_namespaced_by_spec(mock_generate, client):
    """Same question_id + same student_answer but different answer_spec MUST NOT collide."""
    mock_generate.side_effect = [
        {"correct": True, "score": 1.0, "feedback": "ok-A", "matched_expected": "A", "confidence": 0.95},
        {"correct": False, "score": 0.0, "feedback": "no-B", "matched_expected": None, "confidence": 0.95},
    ]
    base = {
        "question_id": "shared-q1",
        "question": "Capital?",
        "student_answer": "Toshkent",
        "subject": "history",
        "grade": 8,
    }
    a = client.post("/api/ai/check-answer", json={**base, "answer_spec": {"type": "semantic", "expected": "A"}})
    b = client.post("/api/ai/check-answer", json={**base, "answer_spec": {"type": "semantic", "expected": "B"}})
    assert a.status_code == 200 and b.status_code == 200
    # Both went through AI (no cache collision).
    assert a.json()["correct"] is True
    assert b.json()["correct"] is False
    assert mock_generate.call_count == 2


# ---------------------------------------------------------------------------
# Sentence Fill semantic-grade tests
# ---------------------------------------------------------------------------
# Sentence Fill (gb_why_chain runtime constant) used to grade with a local
# keyword-overlap heuristic in gbWCEvaluate that rejected paraphrases and
# grammatical variants ("ayirmasi" vs "ayirmasining"). The runtime now
# POSTs to /api/ai/check-answer with answer_spec.type == "semantic" so
# the deterministic checker returns "unsure" and the AI grades for
# meaning. These tests pin that contract so a future refactor can't
# silently revert to text_fuzzy (which bails at ratio<75 without
# escalating, re-introducing the synonym-rejection bug).


@patch("server.services.ai_orchestrator.generate_json")
def test_check_answer_semantic_always_routes_through_ai(mock_generate, client):
    """type=semantic must NEVER short-circuit the deterministic path —
    even an exact-string match has to go through AI for meaning checks."""
    mock_generate.return_value = {
        "correct": True, "score": 1.0,
        "feedback": "To'g'ri!", "matched_expected": "ayirmasining",
        "confidence": 0.95,
    }
    payload = {
        "question_id": "wc-1-1",
        "question": "Yoylar bir-biridan ___ qiladi.",
        "student_answer": "ayirmasining",  # exact match would short-circuit text_fuzzy
        "expected_answers": ["ayirmasining"],
        "answer_spec": {
            "type": "semantic",
            "expected": "ayirmasining",
            "canonical_display": "ayirmasining",
            "allow_ai_fallback": True,
        },
        "phase": "sentence-fill",
        "subject": "geometriya-g7-11",
        "grade": 8,
    }

    resp = client.post("/api/ai/check-answer", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "ai", (
        f"semantic must route through AI even on exact match; got source={data['source']!r}"
    )
    mock_generate.assert_called_once()


@patch("server.services.ai_orchestrator.generate_json")
def test_sentence_fill_closed_semantic_exact_blank_short_circuits_ai(mock_generate, client):
    """Closed Sentence Fill blanks use semantic fallback for variants, but exact
    blank values must not be rejected by a full-sentence language rubric."""
    payload = {
        "question_id": "wc-homework-1",
        "question": 'We always say "do homework" — never "make ___".',
        "student_answer": "homework",
        "expected_answers": ["homework"],
        "answer_spec": {
            "type": "semantic",
            "expected": "homework",
            "canonical_display": "homework",
            "allow_ai_fallback": True,
            "amr": False,
        },
        "phase": "sentence-fill",
        "subject": "english",
        "grade": 8,
    }

    resp = client.post("/api/ai/check-answer", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["correct"] is True
    assert data["source"] == "deterministic"
    assert data["score"] == 1.0
    mock_generate.assert_not_called()


@patch("server.services.ai_orchestrator.generate_json")
def test_sentence_fill_amr_flag_extends_schema(mock_generate, client):
    """When the SF runtime sends answer_spec.amr=true, the grader must
    accept and surface axis_1 / axis_2 in the response so the
    end-of-session AMR scorecard has axis values to aggregate."""
    mock_generate.return_value = {
        "correct": True, "score": 1.0,
        "feedback": "Mukammal!", "matched_expected": "ayirmasining",
        "confidence": 0.95,
        "axis_1": 4, "axis_2": 4,
        "axis_1_label": "Mastered", "axis_2_label": "Mastered",
    }
    payload = {
        "question_id": "wc-1-1",
        "question": "Yoylar bir-biridan ___ qiladi.",
        "student_answer": "ayirmasining",
        "expected_answers": ["ayirmasining"],
        "answer_spec": {
            "type": "semantic",
            "expected": "ayirmasining",
            "canonical_display": "ayirmasining",
            "allow_ai_fallback": True,
            "amr": True,
        },
        "phase": "sentence-fill",
        "subject": "geometriya-g7-11",
        "grade": 8,
    }

    resp = client.post("/api/ai/check-answer", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["correct"] is True
    # Axes must round-trip so the scorecard aggregator can read them.
    assert data.get("axis_1") == 4
    assert data.get("axis_2") == 4
    assert data.get("axis_1_label") == "Mastered"
    assert data.get("axis_2_label") == "Mastered"

    # Inspect the prompt that was actually sent to the AI — the schema
    # hint should include axis_1/axis_2 fields so Kimi knows to emit them.
    call_args = mock_generate.call_args
    schema_hint = call_args.kwargs.get("schema_hint") or (call_args.args[1] if len(call_args.args) > 1 else None)
    assert schema_hint is not None, "generate_json must receive a schema hint"
    assert "axis_1" in schema_hint and "axis_2" in schema_hint, (
        "AMR-mode schema must request axis_1/axis_2 from the AI"
    )


@patch("server.services.ai_orchestrator.generate_json")
def test_sentence_fill_unsure_path_preserves_axes(mock_generate, client):
    """Low-confidence AI verdicts must still pass axis values through
    to the response — the scorecard depends on them even when the
    grade itself is uncertain."""
    mock_generate.return_value = {
        "correct": False, "score": 0.4,
        "feedback": "Unsure but partially correct.",
        "matched_expected": None,
        "confidence": 0.7,  # below the 0.9 threshold → ai_unsure path
        "axis_1": 2, "axis_2": 3,
        "axis_1_label": "Apprentice", "axis_2_label": "Proficient",
    }
    payload = {
        "question_id": "wc-2-1",
        "question": "Tashqaridagi burchak — yoylar ___.",
        "student_answer": "ayirib bo'lib chiqishi",
        "expected_answers": ["ayirmasining"],
        "answer_spec": {
            "type": "semantic", "expected": "ayirmasining",
            "canonical_display": "ayirmasining", "allow_ai_fallback": True, "amr": True,
        },
        "phase": "sentence-fill",
        "subject": "geometriya-g7-11",
        "grade": 8,
    }

    resp = client.post("/api/ai/check-answer", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "ai_unsure"
    # Axes survive the unsure-path normalization in tutor.check_answer.
    assert data.get("axis_1") == 2
    assert data.get("axis_2") == 3


# ---------------------------------------------------------------------------
# D3 coverage tests (cache-hit / queue-insert / boss-soft-fail / dedup)
# ---------------------------------------------------------------------------


@patch("server.services.ai_orchestrator.generate_json")
def test_cache_hit_skips_ai_call(mock_generate, client):
    """Same (question_id, normalized_student_answer, answer_spec) submitted twice
    via POST /api/ai/check-answer.  The mocked generate_json must be called
    exactly once — the second request must hit the cache.
    """
    mock_generate.return_value = {
        "correct": True,
        "score": 1.0,
        "feedback": "Cache test feedback.",
        "matched_expected": "42",
        "confidence": 0.95,
    }
    payload = {
        "question_id": "cache-hit-q1",
        "question": "What is 6x7?",
        "student_answer": "42",
        "answer_spec": {"type": "semantic", "expected": "42"},
        "subject": "math",
        "grade": 7,
    }
    resp1 = client.post("/api/ai/check-answer", json=payload)
    assert resp1.status_code == 200
    assert resp1.json()["source"] == "ai"

    # Second request — must be a cache hit, no new AI call.
    resp2 = client.post("/api/ai/check-answer", json=payload)
    assert resp2.status_code == 200
    assert mock_generate.call_count == 1, (
        f"generate_json called {mock_generate.call_count} times; expected 1 (cache hit)"
    )


@patch("server.services.ai_orchestrator.generate_json")
def test_review_queue_insert_on_low_confidence(mock_generate, client):
    """A boss-phase request that triggers an AI fallback with confidence < 0.90
    must insert exactly one row into the review_queue table.
    """
    import asyncio
    import aiosqlite
    import os

    mock_generate.return_value = {
        "correct": True,
        "score": 0.6,
        "feedback": "Partially correct.",
        "matched_expected": None,
        "confidence": 0.5,
    }
    payload = {
        "question_id": "boss-queue-insert-q1",
        "question": "Explain Newton's third law.",
        "student_answer": "Action reaction",
        "answer_spec": {"type": "semantic"},
        "subject": "physics",
        "grade": 10,
        "phase": "boss",
    }
    resp = client.post("/api/ai/check-answer", json=payload)
    assert resp.status_code == 200
    assert resp.json().get("needs_review") is True

    db_path = os.environ.get("NETS_DB_PATH", "")
    assert db_path, "NETS_DB_PATH must be set for this test"

    async def count_rows():
        async with aiosqlite.connect(db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cur = await conn.execute(
                "SELECT COUNT(*) AS cnt FROM review_queue WHERE question_id = ?",
                ("boss-queue-insert-q1",),
            )
            row = await cur.fetchone()
            return row["cnt"]

    count = asyncio.run(count_rows())
    assert count == 1, f"Expected 1 review_queue row, got {count}"


@patch("server.services.ai_orchestrator.generate_json")
def test_boss_soft_fail_returns_correct_true(mock_generate, client):
    """Boss-phase + deterministic 'unsure' + AI confidence 0.7:
      - Response must be {correct: True, score: 0.7, source: 'ai_unsure', needs_review: True}

    Same scenario with phase='memory_sprint' (non-boss) must return correct: False
    (strict path, no soft-fail).
    """
    mock_generate.return_value = {
        "correct": False,
        "score": 0.0,
        "feedback": "Unsure about this.",
        "matched_expected": None,
        "confidence": 0.7,
    }

    boss_payload = {
        "question_id": "soft-fail-q1",
        "question": "Describe osmosis.",
        "student_answer": "Water moves across membrane",
        "answer_spec": {"type": "semantic"},
        "subject": "biology",
        "grade": 9,
        "phase": "boss",
    }
    resp = client.post("/api/ai/check-answer", json=boss_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["correct"] is True, f"Boss phase should soft-fail to correct=True, got {data}"
    assert data["score"] == 0.7
    assert data["source"] == "ai_unsure"
    assert data["needs_review"] is True

    # Non-boss phase — strict path — must return correct: False.
    mock_generate.return_value = {
        "correct": False,
        "score": 0.0,
        "feedback": "Unsure about this.",
        "matched_expected": None,
        "confidence": 0.7,
    }
    strict_payload = {
        "question_id": "soft-fail-q2",
        "question": "Describe osmosis.",
        "student_answer": "Water moves across membrane",
        "answer_spec": {"type": "semantic"},
        "subject": "biology",
        "grade": 9,
        "phase": "memory_sprint",
    }
    resp2 = client.post("/api/ai/check-answer", json=strict_payload)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["correct"] is False, (
        f"memory_sprint phase must NOT soft-fail; expected correct=False, got {data2}"
    )


@patch("server.services.ai_orchestrator.generate_json")
def test_review_queue_dedup(mock_generate, client):
    """Submitting the same low-confidence answer twice must produce only one
    row in review_queue (idempotent insert).
    """
    import asyncio
    import aiosqlite
    import os

    mock_generate.return_value = {
        "correct": False,
        "score": 0.0,
        "feedback": "Not sure.",
        "matched_expected": None,
        "confidence": 0.4,
    }
    payload = {
        "question_id": "dedup-boss-q1",
        "question": "Explain photosynthesis.",
        "student_answer": "Plants use sunlight",
        "answer_spec": {"type": "semantic"},
        "subject": "biology",
        "grade": 8,
        "phase": "boss",
    }
    resp1 = client.post("/api/ai/check-answer", json=payload)
    assert resp1.status_code == 200

    # Reset mock so second call goes through AI again (cache miss because confidence < 0.90)
    mock_generate.return_value = {
        "correct": False,
        "score": 0.0,
        "feedback": "Still not sure.",
        "matched_expected": None,
        "confidence": 0.4,
    }
    resp2 = client.post("/api/ai/check-answer", json=payload)
    assert resp2.status_code == 200

    db_path = os.environ.get("NETS_DB_PATH", "")
    assert db_path, "NETS_DB_PATH must be set for this test"

    async def count_rows():
        async with aiosqlite.connect(db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cur = await conn.execute(
                "SELECT COUNT(*) AS cnt FROM review_queue WHERE question_id = ?",
                ("dedup-boss-q1",),
            )
            row = await cur.fetchone()
            return row["cnt"]

    count = asyncio.run(count_rows())
    assert count == 1, (
        f"Dedup failed: expected 1 review_queue row for dedup-boss-q1, got {count}"
    )


# ---------------------------------------------------------------------------
# AI-requiring tests
# ---------------------------------------------------------------------------


def test_check_answer_numeric_string_tolerance_does_not_500(client):
    resp = client.post(
        "/api/ai/check-answer",
        json={
            "question_id": "numeric-string-tolerance",
            "question": "What is x?",
            "student_answer": "10.4",
            "expected_answers": [],
            "answer_spec": {
                "type": "numeric",
                "expected": "10",
                "tolerance": "0.5",
                "canonical_display": "10",
            },
            "allow_ai_fallback": False,
            "subject": "math-algebra",
            "grade": 8,
            "phase": "boss",
        },
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["correct"] is True
    assert body["source"] == "deterministic"


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
# Wave F3 — boss-turn persona_traits integration tests (mocked LLM)
# ---------------------------------------------------------------------------


@patch("server.services.ai_orchestrator.generate_json")
def test_boss_turn_accepts_persona_traits(mock_generate, client):
    """POST /api/ai/boss-turn with persona_traits must be accepted (no 422) and the
    captured prompt must contain the trait string so the boss-tutor prompt adapts tone.
    """
    mock_generate.return_value = {
        "correct": True,
        "damage_dealt": 20,
        "boss_response": "Ajoyib zarba!",
        "hint": None,
        "score": 1.0,
    }
    payload = {
        "boss_question": "Yeching: x² = 25",
        "student_answer": "±5",
        "expected_answers": ["±5", "x=±5"],
        "damage_value": 20,
        "hp_remaining": 80,
        "attempt_number": 1,
        "subject": "math-algebra",
        "grade": 8,
        "persona_traits": ["challenger"],
    }
    resp = client.post("/api/ai/boss-turn", json=payload)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    # The mock was called — verify the prompt forwarded the trait.
    mock_generate.assert_called_once()
    call_args = mock_generate.call_args
    # First positional arg is the assembled prompt string.
    prompt_str = call_args[0][0] if call_args[0] else str(call_args)
    assert "challenger" in prompt_str, (
        f"Expected 'challenger' in prompt sent to LLM; got:\n{prompt_str[:500]}"
    )


@patch("server.services.ai_orchestrator.generate_json")
def test_boss_turn_backward_compat_no_traits(mock_generate, client):
    """POST /api/ai/boss-turn WITHOUT persona_traits must still work (no 422, shape
    unchanged).  This guards backward-compat for callers that pre-date F3.
    """
    mock_generate.return_value = {
        "correct": False,
        "damage_dealt": 0,
        "boss_response": "Urinib ko'ring!",
        "hint": None,
        "score": 0.0,
    }
    payload = {
        "boss_question": "Yeching: x² + 7x + 12 = 0",
        "student_answer": "-3",
        "expected_answers": ["-3va-4", "-4va-3"],
        "damage_value": 20,
        "hp_remaining": 100,
        "attempt_number": 1,
        "subject": "math-algebra",
        "grade": 8,
        # persona_traits deliberately omitted
    }
    resp = client.post("/api/ai/boss-turn", json=payload)
    assert resp.status_code == 200, f"Backward-compat failed: {resp.status_code}: {resp.text}"
    data = resp.json()
    # Shape must be identical to pre-F3 shape.
    required_keys = {"correct", "damage_dealt", "boss_response", "hint", "score"}
    missing = required_keys - data.keys()
    assert not missing, f"Response missing keys: {missing}"
    mock_generate.assert_called_once()
    # The JSON INPUT section must NOT contain a "persona_traits" key when none were supplied.
    # We check the section after "---\n\nINPUT:" to avoid a false-positive from the system
    # prompt text (which legitimately mentions "persona_traits" as documentation).
    prompt_str = mock_generate.call_args[0][0] if mock_generate.call_args[0] else ""
    input_section = prompt_str.split("INPUT:", 1)[-1] if "INPUT:" in prompt_str else prompt_str
    assert "persona_traits" not in input_section, (
        "Backward-compat breach: 'persona_traits' appeared in INPUT payload when none supplied"
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
