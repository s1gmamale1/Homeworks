"""Tests for tutor_chat_v2 and context-builder route integration.

Covers:
 1. Route accepts optional phase and falls back to session/preview
 2. Route builds context packet and passes it to tutor_chat_v2
 3. tutor_chat_v2 includes SCREEN_CONTEXT and MISSING_CONTEXT_FLAGS in prompt
 4. tutor_chat_v2 respects the 60-message cap
 5. Legacy tutor_chat wrapper still works

Run:
    python -m pytest tests/test_tutor_chat_v2.py -v
"""
from __future__ import annotations

import asyncio
from unittest.mock import patch, MagicMock

import pytest

from server.services import ai_context, ai_gateway, tutor


# ---------------------------------------------------------------------------
# 1. Route accepts optional phase and new fields
# ---------------------------------------------------------------------------


def test_route_accepts_optional_phase_and_ui_state(client):
    with patch("server.services.ai_orchestrator.generate") as mock_gen:
        mock_gen.return_value = "Salom!"
        resp = client.post(
            "/api/ai/tutor/chat",
            json={
                "session_id": "sess_v2_1",
                "hw_id": "hw_v2_1",
                "message": "hello",
                "screen_context": "Visible text",
                "student_work_text": "my answer",
                "subphase": "sentence-fill",
                "ui_state": {"has_active_element": True},
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["response"] == "Salom!"
    assert data["message_id"] is not None


# ---------------------------------------------------------------------------
# 2. Context builder resolves phase from session when omitted
# ---------------------------------------------------------------------------


def test_route_resolves_phase_from_session_when_omitted(client):
    # Create a homework via API so we know the real ID
    hw_resp = client.post(
        "/api/homeworks",
        json={
            "title": "Boss HW",
            "subject": "math-algebra",
            "grade": 8,
            "mode": "hard",
            "family": "aniq-fanlar",
            "content_json": {},
        },
    )
    assert hw_resp.status_code == 200
    hw_id = hw_resp.json()["id"]

    # Seed session row directly since there's no start-session endpoint yet
    import aiosqlite
    from server.config import DB_PATH

    async def _seed():
        async with aiosqlite.connect(str(DB_PATH)) as conn:
            await conn.execute(
                "INSERT INTO sessions (id, homework_id, student_name, started_at, status, current_phase) VALUES (?, ?, ?, datetime('now'), 'active', ?)",
                ("sess_boss_1", hw_id, "Test", "boss"),
            )
            await conn.commit()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_seed())
    finally:
        loop.close()
        asyncio.set_event_loop(None)

    with patch("server.services.ai_orchestrator.generate") as mock_gen:
        mock_gen.return_value = "Boss time!"
        resp = client.post(
            "/api/ai/tutor/chat",
            json={
                "session_id": "sess_boss_1",
                "hw_id": hw_id,
                "message": "ready",
            },
        )
    assert resp.status_code == 200
    # Verify the prompt included PHASE: boss
    prompt = mock_gen.call_args.args[0] if mock_gen.call_args.args else mock_gen.call_args.kwargs["prompt"]
    assert "PHASE: boss" in prompt


# ---------------------------------------------------------------------------
# 3. tutor_chat_v2 includes context fields in prompt
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tutor_chat_v2_includes_screen_context_in_prompt():
    ctx = ai_context.TutorContextPacket(
        session_id="sess_v2_01",
        hw_id="hw_v2_01",
        phase="practice",
        current_question_id="q1",
        subject="math-algebra",
        grade=8,
        current_question_text="Solve for x",
        visible_screen_text="2x + 3 = 7",
        student_work_text="x = 2",
        missing_context_flags=[],
    )

    with patch("server.services.tutor.db.count_session_messages", return_value=0):
        with patch("server.services.tutor.db.add_tutor_turn", return_value=1):
            with patch("server.services.tutor.db.list_tutor_turns", return_value=[]):
                with patch("server.services.tutor.ai_gateway.generate_text") as mock_gen:
                    mock_gen.return_value = "Good start!"
                    result = await tutor.tutor_chat_v2(
                        context=ctx,
                        message="I got 2",
                    )

    assert result["response"] == "Good start!"
    assert mock_gen.call_args.kwargs["task"] == ai_gateway.AITask.TUTOR_CHAT
    assert mock_gen.call_args.kwargs["session_id"] == "sess_v2_01"
    assert mock_gen.call_args.kwargs["homework_id"] == "hw_v2_01"
    assert mock_gen.call_args.kwargs["prompt_version"] == "tutor-assistant:v2"
    prompt = mock_gen.call_args.kwargs["prompt"]
    assert "SCREEN_CONTEXT:" in prompt
    assert "2x + 3 = 7" in prompt
    assert "STUDENT_ATTEMPT:" in prompt
    assert "x = 2" in prompt
    assert "QUESTION_TEXT:" in prompt
    assert "Solve for x" in prompt


@pytest.mark.asyncio
async def test_tutor_chat_v2_blocks_visible_option_echo_in_practice():
    ctx = ai_context.TutorContextPacket(
        session_id="sess_v2_option_echo",
        hw_id="hw_v2_option_echo",
        phase="practice",
        current_question_id="q1",
        subject="geometriya-g7-11",
        grade=8,
        current_question_text="Uchburchak yuzi formulasi qaysi?",
        visible_screen_text="Savol: Uchburchak yuzi formulasi? Variantlar: a*h/2, a+h, a*h, 2a",
        missing_context_flags=[],
    )

    with patch("server.services.tutor.db.count_session_messages", return_value=0):
        with patch("server.services.tutor.db.add_tutor_turn", return_value=1):
            with patch("server.services.tutor.db.list_tutor_turns", return_value=[]):
                with patch("server.services.tutor.ai_gateway.generate_text") as mock_gen:
                    mock_gen.return_value = (
                        "Uchburchak yuzi = asos * balandlik / 2. Qaysi variant a*h/2?"
                    )
                    result = await tutor.tutor_chat_v2(
                        context=ctx,
                        message="Menga usulni tushuntir",
                    )

    assert "a*h/2" not in result["response"]
    assert "asos * balandlik / 2" not in result["response"]
    assert "Javob, bo'sh joy yoki variantni aytmayman" in result["response"]
    assert mock_gen.call_count == 2
    first_prompt = mock_gen.call_args_list[0].kwargs["prompt"]
    assert "SCREEN_CONTEXT_AVAILABLE_BUT_HIDDEN_FOR_INTEGRITY: True" in first_prompt
    assert "a*h/2" not in first_prompt


@pytest.mark.asyncio
async def test_tutor_chat_v2_fails_closed_without_practice_screen_context():
    ctx = ai_context.TutorContextPacket(
        session_id="sess_v2_missing_context",
        hw_id="hw_v2_missing_context",
        phase="practice",
        subject="geometriya-g7-11",
        grade=8,
        visible_screen_text="",
        missing_context_flags=["empty_screen_context"],
    )

    with patch("server.services.tutor.db.count_session_messages", return_value=0):
        with patch("server.services.tutor.db.add_tutor_turn", return_value=1):
            with patch("server.services.tutor.db.list_tutor_turns", return_value=[]):
                with patch("server.services.tutor.ai_gateway.generate_text") as mock_gen:
                    mock_gen.return_value = "The formula = 2."
                    result = await tutor.tutor_chat_v2(
                        context=ctx,
                        message="Nega 2 ga bo'lamiz?",
                    )

    assert "formula = 2" not in result["response"]
    assert "Javob, bo'sh joy yoki variantni aytmayman" in result["response"]
    assert mock_gen.call_count == 2


@pytest.mark.asyncio
async def test_tutor_chat_v2_includes_missing_context_flags():
    ctx = ai_context.TutorContextPacket(
        session_id="sess_v2_02",
        hw_id="hw_v2_02",
        phase="practice",
        missing_context_flags=["empty_screen_context", "missing_question_id"],
    )

    with patch("server.services.tutor.db.count_session_messages", return_value=0):
        with patch("server.services.tutor.db.add_tutor_turn", return_value=1):
            with patch("server.services.tutor.db.list_tutor_turns", return_value=[]):
                with patch("server.services.tutor.ai_gateway.generate_text") as mock_gen:
                    mock_gen.return_value = "Which question do you mean?"
                    result = await tutor.tutor_chat_v2(
                        context=ctx,
                        message="help",
                    )

    prompt = mock_gen.call_args.kwargs["prompt"]
    assert "MISSING_CONTEXT_FLAGS:" in prompt
    assert "empty_screen_context" in prompt
    assert "missing_question_id" in prompt


# ---------------------------------------------------------------------------
# 4. tutor_chat_v2 respects the 60-message cap
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tutor_chat_v2_cap_returns_429():
    ctx = ai_context.TutorContextPacket(
        session_id="sess_cap",
        hw_id="hw_cap",
        phase="practice",
    )

    with patch("server.services.tutor.db.count_session_messages", return_value=60):
        with pytest.raises(Exception) as exc_info:
            await tutor.tutor_chat_v2(context=ctx, message="hi")

    assert exc_info.value.status_code == 429
    assert "TUTOR_SESSION_CAP" in str(exc_info.value.detail)


# ---------------------------------------------------------------------------
# 5. Legacy tutor_chat wrapper delegates to v2
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_legacy_tutor_chat_wrapper_delegates_to_v2():
    with patch("server.services.tutor.tutor_chat_v2") as mock_v2:
        mock_v2.return_value = {"response": "Wrapped!", "message_id": 42}
        result = await tutor.tutor_chat(
            session_id="sess_wrap",
            hw_id="hw_wrap",
            phase="preview",
            question_id="q1",
            message="hello",
            hw_meta={
                "subject": "biology",
                "grade": 9,
                "question": {"q": "What is DNA?", "answer_spec": {"expected": "deoxyribonucleic acid"}},
            },
        )

    assert result["response"] == "Wrapped!"
    assert result["message_id"] == 42
    # Verify it was called with a context packet
    call_kwargs = mock_v2.call_args.kwargs
    assert "context" in call_kwargs
    ctx = call_kwargs["context"]
    assert ctx.subject == "biology"
    assert ctx.grade == 9
    assert ctx.current_question_text == "What is DNA?"
