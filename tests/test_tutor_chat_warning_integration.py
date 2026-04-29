"""Wave J — tutor chat warning integration tests.

Uses FastAPI TestClient with mocked gemini.generate and slur_filter.classify
to verify the full request→warning→tutor→response pipeline.

Covers:
 1. casual_safe message → no warning record, LLM response returned
 2. profanity_strong first time → warning level=1, no deduction
 3. 9th profanity_strong → returns homework_failed=True, no LLM call
 4. recent_assistant_phrases field accepted without error
 5. response always includes warning_level + cumulative_deduction_pct + homework_failed
"""
from __future__ import annotations

import asyncio
import os
import tempfile
from unittest.mock import patch, MagicMock

import aiosqlite
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _db_path() -> str:
    from server.config import DB_PATH
    return str(DB_PATH)


def _wipe_warning_tables() -> None:
    async def _do() -> None:
        async with aiosqlite.connect(_db_path()) as conn:
            await conn.execute("DELETE FROM tutor_warnings")
            await conn.execute("DELETE FROM tutor_conversations")
            await conn.commit()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_do())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def _count_warnings(hw_id: str) -> int:
    async def _do() -> int:
        async with aiosqlite.connect(_db_path()) as conn:
            cur = await conn.execute(
                "SELECT COUNT(*) FROM tutor_warnings WHERE hw_id = ?",
                (hw_id,),
            )
            row = await cur.fetchone()
            return row[0] if row else 0

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_do())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def _seed_warnings(hw_id: str, session_id: str, count: int) -> None:
    """Seed `count` profanity_strong warning rows directly into the DB."""
    async def _do() -> None:
        async with aiosqlite.connect(_db_path()) as conn:
            for i in range(count):
                await conn.execute(
                    "INSERT INTO tutor_warnings "
                    "(session_id, hw_id, severity, category, matched_term, "
                    "warning_level, deduction_pct, is_big_warning, is_fail, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))",
                    (
                        session_id, hw_id,
                        "profanity_strong", "en_profanity",
                        "seed",
                        i + 1,
                        5 if (i + 1) == 7 else (10 if (i + 1) == 8 else 0),
                        1 if (i + 1) == 8 else 0,
                        1 if (i + 1) >= 9 else 0,
                    ),
                )
            await conn.commit()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_do())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def _make_homework(client) -> str:
    resp = client.post(
        "/api/homeworks",
        json={
            "title": "Warning integration HW",
            "subject": "math-algebra",
            "grade": 8,
            "mode": "hard",
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


@pytest.fixture(autouse=True)
def clean_tables():
    _wipe_warning_tables()
    yield


# ---------------------------------------------------------------------------
# Helper to create a mock SlurClassification
# ---------------------------------------------------------------------------

def _make_slur_classification(severity: str, is_clean: bool = False):
    from server.services.slur_filter import SlurClassification
    return SlurClassification(
        severity=severity,
        category="en_profanity" if not is_clean else "clean",
        lang="en",
        matched_terms=[] if is_clean else ["testword"],
        is_clean=is_clean,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@patch("server.services.gemini.generate")
@patch("server.routes.ai.classify")
def test_casual_safe_no_warning_record(mock_classify, mock_generate, client):
    """casual_safe message → no warning record stored, LLM response returned."""
    mock_classify.return_value = _make_slur_classification("casual_safe", is_clean=True)
    mock_generate.return_value = "Great question about polynomials!"

    hw_id = _make_homework(client)
    resp = client.post(
        "/api/ai/tutor/chat",
        json={
            "session_id": "sess-safe-001",
            "hw_id": hw_id,
            "phase": "preview",
            "message": "salom, savol bor",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["response"] == "Great question about polynomials!"
    assert data["homework_failed"] is False
    assert data["warning_level"] == 0
    assert _count_warnings(hw_id) == 0


@patch("server.services.gemini.generate")
@patch("server.routes.ai.classify")
def test_profanity_strong_first_time_level_1(mock_classify, mock_generate, client):
    """First profanity_strong → warning level=1 in response, no deduction."""
    mock_classify.return_value = _make_slur_classification("profanity_strong")
    mock_generate.return_value = "Let's focus on the problem."

    hw_id = _make_homework(client)
    resp = client.post(
        "/api/ai/tutor/chat",
        json={
            "session_id": "sess-strong-001",
            "hw_id": hw_id,
            "phase": "preview",
            "message": "what the fuck is this question",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["homework_failed"] is False
    assert data["warning_level"] == 1
    assert data["cumulative_deduction_pct"] == 0
    assert _count_warnings(hw_id) == 1


@patch("server.services.gemini.generate")
@patch("server.routes.ai.classify")
def test_ninth_profanity_strong_returns_homework_failed(
    mock_classify, mock_generate, client
):
    """9th profanity_strong → homework_failed=True, no LLM call."""
    mock_classify.return_value = _make_slur_classification("profanity_strong")
    mock_generate.return_value = "should not be called"

    hw_id = _make_homework(client)
    sess = "sess-ninth-001"

    # Seed 8 warnings directly so the 9th call triggers fail
    _seed_warnings(hw_id, sess, 8)

    resp = client.post(
        "/api/ai/tutor/chat",
        json={
            "session_id": sess,
            "hw_id": hw_id,
            "phase": "preview",
            "message": "worst word ever",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["homework_failed"] is True
    assert data["warning_level"] == 9
    assert data["message_id"] is None

    # LLM must NOT have been called
    mock_generate.assert_not_called()


@patch("server.services.gemini.generate")
@patch("server.routes.ai.classify")
def test_recent_assistant_phrases_accepted(mock_classify, mock_generate, client):
    """recent_assistant_phrases field is accepted by the endpoint without error."""
    mock_classify.return_value = _make_slur_classification("casual_safe", is_clean=True)
    mock_generate.return_value = "Here is the formula."

    hw_id = _make_homework(client)
    resp = client.post(
        "/api/ai/tutor/chat",
        json={
            "session_id": "sess-phrases-001",
            "hw_id": hw_id,
            "phase": "preview",
            "message": "help",
            "recent_assistant_phrases": ["Ey,", "OK,", "Ha,"],
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["response"] == "Here is the formula."


@patch("server.services.gemini.generate")
@patch("server.routes.ai.classify")
def test_response_always_has_warning_fields(mock_classify, mock_generate, client):
    """Every non-fail response includes warning_level, cumulative_deduction_pct,
    and homework_failed."""
    mock_classify.return_value = _make_slur_classification("casual_safe", is_clean=True)
    mock_generate.return_value = "Answer here."

    hw_id = _make_homework(client)
    resp = client.post(
        "/api/ai/tutor/chat",
        json={
            "session_id": "sess-fields-001",
            "hw_id": hw_id,
            "phase": "preview",
            "message": "normal message",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "warning_level" in data
    assert "cumulative_deduction_pct" in data
    assert "homework_failed" in data
