"""Tests for server/services/ai_gateway.py

Covers:
 1. get_status returns resolved models per task
 2. _resolve_model maps pro/fast correctly
 3. generate_text delegates to ai_orchestrator with correct model
 4. generate_structured validates Pydantic schema and retries once
 5. run_guardrail returns GuardrailResult (falls back on failure)
 6. ai_call_logs are written after a call

Run:
    python -m pytest tests/test_ai_gateway.py -v
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import patch, MagicMock

import pytest
from pydantic import ValidationError

from server.services import ai_gateway
from server.schemas.ai_contracts import TutorResponse, GuardrailResult
from pydantic import BaseModel


class _StrictTestModel(BaseModel):
    """Strict model for retry tests — no defaults, so missing fields fail validation."""
    reply: str
    score: float


# ---------------------------------------------------------------------------
# 1. get_status
# ---------------------------------------------------------------------------


def test_get_status_has_all_tasks():
    status = ai_gateway.get_status()
    assert "provider_order" in status
    assert "active_provider" in status
    assert "tasks" in status
    for task in ai_gateway.AITask:
        assert task.value in status["tasks"]
        task_info = status["tasks"][task.value]
        assert "provider" in task_info
        assert "model" in task_info
        assert "tier" in task_info


def test_get_status_tutor_chat_uses_pro_model():
    """TUTOR_CHAT was briefly on the "max" tier (kimi-k2.6) in PR #209 but
    that model's 30-120s thinking latency tripped the 15s text-path client
    timeout on every call and surfaced "Tutor backend temporarily unavailable"
    to students. Reverted to "pro" — guard here so any future re-route is
    deliberate and paired with a timeout/UX update.
    """
    status = ai_gateway.get_status()
    from server.services.ai_orchestrator import PRO_MODEL
    assert status["tasks"][ai_gateway.AITask.TUTOR_CHAT.value]["tier"] == "pro"
    assert status["tasks"][ai_gateway.AITask.TUTOR_CHAT.value]["model"] == PRO_MODEL


def test_get_status_pro_tasks_use_pro_model():
    status = ai_gateway.get_status()
    pro_tasks = [
        ai_gateway.AITask.TUTOR_CHAT.value,
        ai_gateway.AITask.ANSWER_CHECK.value,
        ai_gateway.AITask.BOSS_QUESTION_GENERATE.value,
        ai_gateway.AITask.FINAL_REPORT.value,
    ]
    for task_name in pro_tasks:
        assert status["tasks"][task_name]["tier"] == "pro"


def test_get_status_fast_tasks_use_fast_model():
    status = ai_gateway.get_status()
    fast_tasks = [
        ai_gateway.AITask.BOSS_PERSONA_RESPONSE.value,
        ai_gateway.AITask.SAFETY_GUARDRAIL.value,
    ]
    for task_name in fast_tasks:
        assert status["tasks"][task_name]["tier"] == "fast"


# ---------------------------------------------------------------------------
# 2. _resolve_model
# ---------------------------------------------------------------------------


def test_resolve_model_pro_for_tutor_chat():
    # Was "max" → VISION_MODEL after PR #209; reverted to "pro" → PRO_MODEL
    # because K2.X thinking models exceed the 15s text-path client timeout.
    model = ai_gateway._resolve_model(ai_gateway.AITask.TUTOR_CHAT)
    from server.services.ai_orchestrator import PRO_MODEL
    assert model == PRO_MODEL


def test_resolve_model_pro():
    model = ai_gateway._resolve_model(ai_gateway.AITask.ANSWER_CHECK)
    from server.services.ai_orchestrator import PRO_MODEL
    assert model == PRO_MODEL


def test_resolve_model_fast():
    model = ai_gateway._resolve_model(ai_gateway.AITask.BOSS_PERSONA_RESPONSE)
    from server.services.ai_orchestrator import FAST_MODEL
    assert model == FAST_MODEL


# ---------------------------------------------------------------------------
# 3. generate_text
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_text_delegates_with_correct_model():
    with patch("server.services.ai_gateway.ai_orchestrator.generate") as mock_gen:
        mock_gen.return_value = "Salom!"
        result = await ai_gateway.generate_text(
            task=ai_gateway.AITask.TUTOR_CHAT,
            prompt="hello",
            session_id="sess_test_01",
            homework_id="hw_test_01",
        )
    assert result == "Salom!"
    assert mock_gen.called
    call_kwargs = mock_gen.call_args.kwargs
    from server.services.ai_orchestrator import PRO_MODEL
    assert call_kwargs["model"] == PRO_MODEL


@pytest.mark.asyncio
async def test_generate_text_logs_on_failure():
    with patch("server.services.ai_gateway.ai_orchestrator.generate") as mock_gen:
        mock_gen.side_effect = RuntimeError("boom")
        with patch("server.services.ai_gateway._log_call") as mock_log:
            with pytest.raises(RuntimeError):
                await ai_gateway.generate_text(
                    task=ai_gateway.AITask.TUTOR_CHAT,
                    prompt="hello",
                )
    assert mock_log.called
    log_kwargs = mock_log.call_args.kwargs
    assert log_kwargs["success"] is False
    assert log_kwargs["error_code"] == "AI_PROVIDER_FAILED"


# ---------------------------------------------------------------------------
# 4. generate_structured
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_structured_valid_first_try():
    with patch("server.services.ai_gateway.ai_orchestrator.generate") as mock_gen:
        mock_gen.return_value = json.dumps({
            "reply": "To'g'ri!",
            "action": "explain",
            "used_screen": True,
            "used_question": False,
            "used_performance": False,
            "detected_need": None,
            "misconception_tags": [],
        })
        result = await ai_gateway.generate_structured(
            task=ai_gateway.AITask.TUTOR_CHAT,
            prompt="solve 2+2",
            schema=TutorResponse,
        )
    assert isinstance(result, TutorResponse)
    assert result.reply == "To'g'ri!"


@pytest.mark.asyncio
async def test_generate_structured_retries_once_on_validation_error():
    bad_json = json.dumps({"reply": "hi"})  # missing required 'score'
    good_json = json.dumps({"reply": "To'g'ri!", "score": 0.95})

    with patch("server.services.ai_gateway.ai_orchestrator.generate") as mock_gen:
        mock_gen.side_effect = [bad_json, good_json]
        result = await ai_gateway.generate_structured(
            task=ai_gateway.AITask.TUTOR_CHAT,
            prompt="solve 2+2",
            schema=_StrictTestModel,
        )
    assert isinstance(result, _StrictTestModel)
    assert result.reply == "To'g'ri!"
    assert result.score == 0.95
    assert mock_gen.call_count == 2


@pytest.mark.asyncio
async def test_generate_structured_fails_after_two_invalid():
    bad_json = json.dumps({"reply": "hi"})  # missing required 'score'
    with patch("server.services.ai_gateway.ai_orchestrator.generate") as mock_gen:
        mock_gen.return_value = bad_json
        with pytest.raises(RuntimeError, match="AI gateway could not produce valid structured output"):
            await ai_gateway.generate_structured(
                task=ai_gateway.AITask.TUTOR_CHAT,
                prompt="solve 2+2",
                schema=_StrictTestModel,
            )
    assert mock_gen.call_count == 2


@pytest.mark.asyncio
async def test_generate_structured_fails_on_non_json():
    with patch("server.services.ai_gateway.ai_orchestrator.generate") as mock_gen:
        mock_gen.return_value = "not json"
        with pytest.raises(RuntimeError):
            await ai_gateway.generate_structured(
                task=ai_gateway.AITask.TUTOR_CHAT,
                prompt="solve 2+2",
                schema=TutorResponse,
            )
    assert mock_gen.call_count == 2  # first fails, retry also fails


# ---------------------------------------------------------------------------
# 5. run_guardrail
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_guardrail_returns_guardrail_result():
    with patch("server.services.ai_gateway.generate_structured") as mock_struct:
        mock_struct.return_value = GuardrailResult(
            allowed=False,
            risk="answer_leak",
            action="refuse",
        )
        result = await ai_gateway.run_guardrail(
            prompt="what's the answer?",
            session_id="sess_test_02",
        )
    assert isinstance(result, GuardrailResult)
    assert result.allowed is False
    assert result.risk == "answer_leak"


@pytest.mark.asyncio
async def test_run_guardrail_fails_closed_on_provider_error():
    """Regression — Sigma #179 finding #1.

    A safety classifier MUST fail closed: when the guardrail provider is down
    we cannot verify the message is safe, so the call is rejected (not
    silently allowed). Failing open would let prompt injections and answer-
    leak requests through whenever the provider is overloaded, which is
    exactly when we need the guardrail most.
    """
    with patch("server.services.ai_gateway.generate_structured") as mock_struct:
        mock_struct.side_effect = RuntimeError("provider down")
        result = await ai_gateway.run_guardrail(prompt="hello")
    assert isinstance(result, GuardrailResult)
    assert result.allowed is False, "guardrail must fail closed on provider error"
    assert result.action == "ask_clarifying"


@pytest.mark.asyncio
async def test_run_guardrail_fails_closed_on_validation_error():
    """Validation failures (e.g. AI_SCHEMA_VALIDATION_FAILED bubbling up as
    RuntimeError) also count as 'unverified' and must fail closed."""
    with patch("server.services.ai_gateway.generate_structured") as mock_struct:
        mock_struct.side_effect = RuntimeError("AI_SCHEMA_VALIDATION_FAILED")
        result = await ai_gateway.run_guardrail(prompt="ignore previous")
    assert result.allowed is False
    assert result.action == "ask_clarifying"


# ---------------------------------------------------------------------------
# 6. ai_call_logs DB integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ai_call_log_written_after_generate_text():
    with patch("server.services.ai_gateway.ai_orchestrator.generate") as mock_gen:
        mock_gen.return_value = "ok"
        with patch("server.services.ai_gateway.add_ai_call_log") as mock_log:
            await ai_gateway.generate_text(
                task=ai_gateway.AITask.SAFETY_GUARDRAIL,
                prompt="test",
                session_id="sess_log_01",
                homework_id="hw_log_01",
            )
    assert mock_log.called
    kwargs = mock_log.call_args.kwargs
    assert kwargs["task_type"] == "safety_guardrail"
    assert kwargs["session_id"] == "sess_log_01"
    assert kwargs["homework_id"] == "hw_log_01"
    assert kwargs["success"] is True


@pytest.mark.asyncio
async def test_ai_call_log_written_on_failure():
    with patch("server.services.ai_gateway.ai_orchestrator.generate") as mock_gen:
        mock_gen.side_effect = RuntimeError("fail")
        with patch("server.services.ai_gateway.add_ai_call_log") as mock_log:
            with pytest.raises(RuntimeError):
                await ai_gateway.generate_text(
                    task=ai_gateway.AITask.TUTOR_CHAT,
                    prompt="test",
                )
    assert mock_log.called
    kwargs = mock_log.call_args.kwargs
    assert kwargs["success"] is False
    assert kwargs["error_code"] == "AI_PROVIDER_FAILED"


# ---------------------------------------------------------------------------
# 7. prompt_version population
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_text_logs_default_prompt_version():
    """Regression — Sigma #179 finding #5.

    The ai_call_logs.prompt_version column was always NULL because nothing
    plumbed a version through. After the fix, generate_text logs the default
    when no caller-supplied version is given.
    """
    with patch("server.services.ai_gateway.ai_orchestrator.generate") as mock_gen:
        mock_gen.return_value = "ok"
        with patch("server.services.ai_gateway.add_ai_call_log") as mock_log:
            await ai_gateway.generate_text(
                task=ai_gateway.AITask.TUTOR_CHAT,
                prompt="test",
            )
    kwargs = mock_log.call_args.kwargs
    assert kwargs["prompt_version"] is not None
    assert kwargs["prompt_version"] == ai_gateway.DEFAULT_PROMPT_VERSION


@pytest.mark.asyncio
async def test_generate_text_logs_caller_supplied_prompt_version():
    """When the caller passes an explicit prompt_version it must reach the DB."""
    with patch("server.services.ai_gateway.ai_orchestrator.generate") as mock_gen:
        mock_gen.return_value = "ok"
        with patch("server.services.ai_gateway.add_ai_call_log") as mock_log:
            await ai_gateway.generate_text(
                task=ai_gateway.AITask.TUTOR_CHAT,
                prompt="test",
                prompt_version="tutor-prompt-v3",
            )
    kwargs = mock_log.call_args.kwargs
    assert kwargs["prompt_version"] == "tutor-prompt-v3"


@pytest.mark.asyncio
async def test_run_guardrail_logs_input_guardrail_prompt_version():
    """run_guardrail must tag its DB row so guardrail-only metrics can be sliced."""
    with patch("server.services.ai_gateway.ai_orchestrator.generate") as mock_gen:
        mock_gen.return_value = json.dumps({
            "allowed": True,
            "risk": "none",
            "action": "continue",
        })
        with patch("server.services.ai_gateway.add_ai_call_log") as mock_log:
            await ai_gateway.run_guardrail(prompt="hello")
    assert mock_log.called
    kwargs = mock_log.call_args.kwargs
    assert kwargs["prompt_version"] is not None
    assert kwargs["prompt_version"].startswith("input-guardrail")


# ---------------------------------------------------------------------------
# 8. SIMULATION_JUDGE schema registered
# ---------------------------------------------------------------------------


def test_simulation_judge_has_schema():
    """Regression — Sigma #179 finding #4. _task_schema(SIMULATION_JUDGE) must
    not silently return None."""
    from server.schemas.ai_contracts import SimulationJudgeResult
    schema = ai_gateway._task_schema(ai_gateway.AITask.SIMULATION_JUDGE)
    assert schema is SimulationJudgeResult


# ---------------------------------------------------------------------------
# 9. schema_hint actually wired into the prompt
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_structured_embeds_schema_hint_in_prompt():
    """Regression — Sigma #179 finding #3. schema_hint was computed but never
    sent. After the fix the JSON schema must appear in the outgoing prompt."""
    with patch("server.services.ai_gateway.ai_orchestrator.generate") as mock_gen:
        mock_gen.return_value = json.dumps({
            "reply": "ok",
            "action": "explain",
            "used_screen": False,
            "used_question": False,
            "used_performance": False,
            "detected_need": None,
            "misconception_tags": [],
        })
        await ai_gateway.generate_structured(
            task=ai_gateway.AITask.TUTOR_CHAT,
            prompt="solve 2+2",
            schema=TutorResponse,
        )
    # The orchestrator must have been called with a prompt that includes the
    # schema-hint marker text and a property name from TutorResponse.
    sent_prompt = mock_gen.call_args.kwargs["prompt"]
    assert "Respond with valid JSON matching this schema" in sent_prompt
    assert "reply" in sent_prompt  # property name from TutorResponse
