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
async def test_generate_text_delegates_with_tier_and_preference():
    """Post per-task-routing refactor: generate_text passes `tier` +
    `preference_override` to the orchestrator instead of a pre-resolved
    model string. The orchestrator resolves model per-provider so a
    cross-provider fallback chain swaps model names as it walks.
    """
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
    # TUTOR_CHAT is pro-tier; no per-task override so preference falls to
    # the global default (kimi).
    assert call_kwargs["tier"] == "pro"
    assert call_kwargs["preference_override"] == ["kimi"]
    # Regression guard — the legacy `model=` kwarg must NOT be passed in
    # tier mode; that's what broke the cross-provider fallback walk.
    assert "model" not in call_kwargs


@pytest.mark.asyncio
async def test_generate_text_routes_boss_tasks_to_openai_preference():
    """Boss tasks must hand the orchestrator the per-task openai → kimi chain
    so OpenAI runs primary with Kimi as automatic fallback."""
    with patch("server.services.ai_gateway.ai_orchestrator.generate") as mock_gen:
        mock_gen.return_value = "{}"
        await ai_gateway.generate_text(
            task=ai_gateway.AITask.BOSS_QUESTION_GENERATE,
            prompt="test",
        )
    call_kwargs = mock_gen.call_args.kwargs
    assert call_kwargs["preference_override"] == ["openai", "kimi"]
    assert call_kwargs["tier"] == "pro"


@pytest.mark.asyncio
async def test_boss_persona_response_is_plaintext_generate_text_task():
    """BOSS_PERSONA_RESPONSE contract guard (hardening item 6).

    The task is intentionally a PLAIN-TEXT task: it is reserved for the (still
    deferred) boss hint / persona-reply surface and must be invoked through
    ``generate_text`` — never ``generate_structured``. Pins three properties so
    a future refactor can't silently break the reservation:

      1. It is a registered, fast-tier task (cheap, latency-sensitive replies).
      2. It is intentionally ABSENT from ``_TASK_SCHEMA`` — adding it there would
         imply structured output, which is the wrong shape for a persona reply.
      3. ``generate_text`` can route it to the orchestrator (fast tier, global
         preference) without error.
    """
    # 1. Registered + fast tier.
    assert ai_gateway.TASK_MODEL_POLICY[ai_gateway.AITask.BOSS_PERSONA_RESPONSE] == "fast"
    # 2. Plain-text → must NOT have a structured schema registered.
    assert ai_gateway._task_schema(ai_gateway.AITask.BOSS_PERSONA_RESPONSE) is None
    assert ai_gateway.AITask.BOSS_PERSONA_RESPONSE not in ai_gateway._TASK_SCHEMA
    # 3. Routable via generate_text (the plain-text entrypoint).
    with patch("server.services.ai_gateway.ai_orchestrator.generate") as mock_gen:
        mock_gen.return_value = "Sen mendan o'tolmaysan!"
        out = await ai_gateway.generate_text(
            task=ai_gateway.AITask.BOSS_PERSONA_RESPONSE,
            prompt="taunt the student",
        )
    assert out == "Sen mendan o'tolmaysan!"
    call_kwargs = mock_gen.call_args.kwargs
    assert call_kwargs["tier"] == "fast"
    # Not in the per-task override map → inherits the global preference.
    assert call_kwargs["preference_override"] == ["kimi"]


def test_task_provider_preference_includes_both_boss_tasks():
    """The two dynamic-boss tasks must be the only entries in the override
    map. If a future task wants OpenAI routing, it goes here; this test
    catches accidental drops."""
    assert set(ai_gateway.TASK_PROVIDER_PREFERENCE.keys()) == {
        ai_gateway.AITask.BOSS_QUESTION_GENERATE,
        ai_gateway.AITask.BOSS_ANSWER_CHECK,
    }
    for task, pref in ai_gateway.TASK_PROVIDER_PREFERENCE.items():
        assert pref == ["openai", "kimi"], (
            f"{task.value} should chain openai -> kimi but is {pref}"
        )


def test_resolve_task_provider_and_model_routes_boss_to_openai_when_key_set(monkeypatch):
    """With OPENAI_API_KEY set, boss tasks resolve to openai/gpt-4o-mini.
    This is the core routing contract the user requested."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-only-fake")
    monkeypatch.setenv("KIMI_API_KEY", "kimi-test-fake")

    provider, model, tier = ai_gateway._resolve_task_provider_and_model(
        ai_gateway.AITask.BOSS_QUESTION_GENERATE
    )
    assert provider == "openai"
    assert model == "gpt-4o-mini"
    assert tier == "pro"


def test_resolve_task_provider_and_model_falls_back_to_kimi_when_openai_unavailable(monkeypatch):
    """OPENAI_API_KEY unset → select_provider walks past openai to kimi.
    Boss still works on Kimi when OpenAI isn't configured."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("KIMI_API_KEY", "kimi-test-fake")

    provider, model, tier = ai_gateway._resolve_task_provider_and_model(
        ai_gateway.AITask.BOSS_QUESTION_GENERATE
    )
    assert provider == "kimi"
    assert model.startswith("moonshot-")  # Kimi's pro model
    assert tier == "pro"


def test_resolve_task_provider_and_model_keeps_tutor_on_kimi(monkeypatch):
    """Non-boss tasks must NEVER route through OpenAI — the user explicitly
    asked for OpenAI on boss only, Kimi for everything else."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-only-fake")  # available!
    monkeypatch.setenv("KIMI_API_KEY", "kimi-test-fake")

    for task in (
        ai_gateway.AITask.TUTOR_CHAT,
        ai_gateway.AITask.ANSWER_CHECK,
        ai_gateway.AITask.FINAL_REPORT,
        ai_gateway.AITask.SAFETY_GUARDRAIL,
        ai_gateway.AITask.BOSS_PERSONA_RESPONSE,
    ):
        provider, _, _ = ai_gateway._resolve_task_provider_and_model(task)
        assert provider == "kimi", (
            f"{task.value} must stay on kimi, got {provider!r}"
        )


def test_get_status_reports_per_task_provider_override(monkeypatch):
    """Status endpoint surfaces the openai → kimi chain for boss tasks so
    operators can verify routing live without grepping code."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-only-fake")
    monkeypatch.setenv("KIMI_API_KEY", "kimi-test-fake")

    status = ai_gateway.get_status()
    assert "task_overrides" in status
    assert "boss_question_generate" in status["task_overrides"]
    assert status["task_overrides"]["boss_question_generate"] == ["openai", "kimi"]

    boss_entry = status["tasks"]["boss_question_generate"]
    assert boss_entry["provider"] == "openai"
    assert boss_entry["model"] == "gpt-4o-mini"

    tutor_entry = status["tasks"]["tutor_chat"]
    assert tutor_entry["provider"] == "kimi"


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
