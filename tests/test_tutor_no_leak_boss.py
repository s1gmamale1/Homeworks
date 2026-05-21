"""Regression — tutor chat in BOSS phase must NOT leak the answer.

Mirrors the existing PRACTICE leak tests at tests/test_tutor_chat.py:215,
255, 314. Recon flagged that those three tests cover PRACTICE only and
left BOSS without parallel coverage — even though _redact_question_for_tutor
at server/services/tutor.py:810 routes both phases through the same
allow-list scrub (only "preview" bypasses redaction).

The redaction code path is identical between PRACTICE and BOSS today, but
without explicit BOSS tests a future refactor could silently add a
phase-specific branch (e.g. "boss gets richer context") that re-introduces
the leak for boss-shape content. These tests fail closed against that.

Three coverage shapes, each mirroring the equivalent PRACTICE test:

  1. Basic answer leak — `accepted_answers` / `ans` / `answer_spec.expected`
     containing a magic token must not reach the LLM prompt.
  2. Answer-spec alias leak — `canonical_display`, `matched_expected`,
     `answer`, and the top-level `a` field also stripped.
  3. Nested leak — answer-bearing keys inside `options[]` / `fields[]` /
     `rubric{}` recursively scrubbed.

The chat endpoint accepts any string for `phase` (TutorChatRequest.phase
is Optional[str] with no enum); production uses "boss" for in-fight tutor
help during a Final Boss session. We test with `phase="boss"` to match.
"""
from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import patch

import aiosqlite
import pytest


# ---------------------------------------------------------------------------
# Helpers (duplicated from test_tutor_chat.py for test-file independence;
# the helpers there are module-level, not in conftest, and the duplication
# is cheap)
# ---------------------------------------------------------------------------


def _db_path() -> str:
    from server.config import DB_PATH
    return str(DB_PATH)


def _wipe_tutor_tables() -> None:
    async def _do() -> None:
        async with aiosqlite.connect(_db_path()) as conn:
            await conn.execute("DELETE FROM tutor_conversations")
            await conn.commit()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_do())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def _create_then_set_content(client, content_json: dict) -> str:
    create_resp = client.post(
        "/api/homeworks",
        json={
            "title": "Boss leak test HW",
            "subject": "math-algebra",
            "grade": 8,
            "mode": "hard",
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    hw_id = create_resp.json()["id"]
    put_resp = client.put(f"/api/homeworks/{hw_id}", json={"content_json": content_json})
    assert put_resp.status_code == 200, put_resp.text
    return hw_id


@pytest.fixture(autouse=True)
def clean_tutor_tables():
    _wipe_tutor_tables()
    yield


# ---------------------------------------------------------------------------
# 1. Basic answer leak — BOSS phase
# ---------------------------------------------------------------------------


@patch("server.services.ai_orchestrator.generate")
def test_boss_no_answer_leak(mock_generate, client):
    """Set expected="MAGIC_TOKEN_BOSS" on the boss question. Capture the
    prompt the tutor service hands to ai_orchestrator.generate and assert
    MAGIC_TOKEN_BOSS is NOT in it.

    We also stub ai_orchestrator.generate's return value to contain
    MAGIC_TOKEN_BOSS — the test passes because we only protect *input*
    (the prompt is the safety surface). Output filtering is intentionally
    out of scope, matching the PRACTICE-phase contract.
    """
    captured: dict[str, str] = {}

    def _fake_generate(prompt: str, *args, **kwargs):
        captured["prompt"] = prompt
        return "The boss says: try harder. (intentional output leak: MAGIC_TOKEN_BOSS)"

    mock_generate.side_effect = _fake_generate

    content = {
        "boss_questions": [
            {
                "question_id": "qb-basic",
                "q": "Solve: x + 5 = 12",
                "answer_spec": {"type": "numeric", "expected": "MAGIC_TOKEN_BOSS"},
                "ans": ["MAGIC_TOKEN_BOSS"],
                "accepted_answers": ["MAGIC_TOKEN_BOSS"],
                "dmg": 10,
                "tags": "[Bloom: L2]",
            }
        ],
    }
    hw_id = _create_then_set_content(client, content)

    resp = client.post(
        "/api/ai/tutor/chat",
        json={
            "session_id": "sess-boss-leak",
            "hw_id": hw_id,
            "phase": "boss",
            "question_id": "qb-basic",
            "message": "Hint please?",
        },
    )
    assert resp.status_code == 200, resp.text

    captured_prompt = captured.get("prompt", "")
    assert captured_prompt, "ai_orchestrator.generate was never called"
    assert "MAGIC_TOKEN_BOSS" not in captured_prompt, (
        "Answer-leak guard failed for BOSS phase: MAGIC_TOKEN_BOSS reached the LLM prompt.\n"
        f"Prompt:\n{captured_prompt[:1000]}"
    )

    # The (deliberately leaky) response is returned untouched — this is the
    # documented behavior. Output filtering is not the redactor's job.
    assert "MAGIC_TOKEN_BOSS" in resp.json()["response"]


# ---------------------------------------------------------------------------
# 2. Answer-spec alias leak — BOSS phase
# ---------------------------------------------------------------------------


@patch("server.services.ai_orchestrator.generate")
def test_boss_no_answer_alias_leak_from_answer_spec(mock_generate, client):
    """Some editor/importer shapes store the answer in `canonical_display`,
    `answer`, or `matched_expected` instead of (or alongside) `expected`.
    Boss-phase prompts must strip ALL of those aliases — the allow-list at
    _TUTOR_CONTEXT_SAFE_KEYS doesn't include any of them, so they fail
    closed by default. This test pins that boss-shape content
    (boss_questions[]) gets the same protection."""
    captured: dict[str, str] = {}

    def _fake_generate(prompt: str, *args, **kwargs):
        captured["prompt"] = prompt
        return "I can guide the method."

    mock_generate.side_effect = _fake_generate

    content = {
        "boss_questions": [
            {
                "question_id": "qb-alias",
                "q": "Solve the equation.",
                "answer_spec": {
                    "type": "text_fuzzy",
                    "expected": "BOSS_LEAK_EXPECTED",
                    "canonical_display": "BOSS_LEAK_CANONICAL",
                    "answer": "BOSS_LEAK_ANSWER",
                    "matched_expected": "BOSS_LEAK_MATCHED",
                },
                "answer": "BOSS_LEAK_TOPLEVEL",
                "a": "BOSS_LEAK_A",
                "accepted_answers": ["BOSS_LEAK_ACCEPTED"],
                "dmg": 20,
            }
        ],
    }
    hw_id = _create_then_set_content(client, content)

    resp = client.post(
        "/api/ai/tutor/chat",
        json={
            "session_id": "sess-boss-alias-leak",
            "hw_id": hw_id,
            "phase": "boss",
            "question_id": "qb-alias",
            "message": "Help me solve it.",
        },
    )
    assert resp.status_code == 200, resp.text

    prompt = captured.get("prompt", "")
    assert prompt, "ai_orchestrator.generate was never called"
    for token in (
        "BOSS_LEAK_EXPECTED",
        "BOSS_LEAK_CANONICAL",
        "BOSS_LEAK_ANSWER",
        "BOSS_LEAK_MATCHED",
        "BOSS_LEAK_TOPLEVEL",
        "BOSS_LEAK_A",
        "BOSS_LEAK_ACCEPTED",
    ):
        assert token not in prompt, (
            f"{token} leaked into BOSS-phase prompt:\n{prompt[:1000]}"
        )


# ---------------------------------------------------------------------------
# 3. Nested answer leak — BOSS phase
# ---------------------------------------------------------------------------


@patch("server.services.ai_orchestrator.generate")
def test_boss_no_nested_answer_leak(mock_generate, client):
    """Redaction must be recursive: answers can appear in nested lists/dicts
    such as options[] / fields[] / rubric{} on boss questions imported from
    older editor shapes. The scrub() helper inside _redact_question_for_tutor
    recurses through both dicts and lists; this test pins that contract for
    BOSS phase (parallel to test_practice_no_nested_answer_leak)."""
    captured: dict[str, str] = {}

    def _fake_generate(prompt: str, *args, **kwargs):
        captured["prompt"] = prompt
        return "Think about the structure first."

    mock_generate.side_effect = _fake_generate

    content = {
        "boss_questions": [
            {
                "question_id": "qb-nested",
                "q": "Pick the correct option.",
                "options": [
                    {"label": "A", "text": "Wrong option"},
                    {"label": "B", "text": "Visible option B", "correct": True},
                ],
                "fields": [
                    {"label": "Step", "acceptable": ["BOSS_NESTED_FIELD"]},
                ],
                "rubric": {"answer": "BOSS_NESTED_RUBRIC"},
                "dmg": 30,
            }
        ],
    }
    hw_id = _create_then_set_content(client, content)

    resp = client.post(
        "/api/ai/tutor/chat",
        json={
            "session_id": "sess-boss-nested-leak",
            "hw_id": hw_id,
            "phase": "boss",
            "question_id": "qb-nested",
            "message": "Which option is right?",
        },
    )
    assert resp.status_code == 200, resp.text

    prompt = captured.get("prompt", "")
    assert prompt, "ai_orchestrator.generate was never called"

    # Visible context must still reach the prompt — option text + step labels
    # are inside the allow-list, so the tutor can reason about the question.
    assert "QUESTION_CONTEXT:" in prompt
    assert "Pick the correct option." in prompt
    assert "Wrong option" in prompt
    assert "Visible option B" in prompt
    assert "Step" in prompt

    # Answer-bearing leaves must be scrubbed.
    for token in ("BOSS_NESTED_FIELD", "BOSS_NESTED_RUBRIC"):
        assert token not in prompt, (
            f"{token} leaked into BOSS-phase prompt via nested structure:\n{prompt[:1000]}"
        )
    # The KEYS themselves (which signal answer-bearing values) must also be
    # absent — the allow-list strips them whether or not the value is
    # populated. Without this guard, an empty-value `"answer": ""` could
    # still telegraph the existence of an answer field.
    assert '"correct"' not in prompt
    assert '"acceptable"' not in prompt
    assert '"answer"' not in prompt
