"""
Wave F0 — tests for the AI provider registry.

pytest tests/test_ai_providers.py -v
"""
from __future__ import annotations

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── 1. Registry ──────────────────────────────────────────────────────────────

def test_registry_get_known():
    from server.services.ai_providers import get_provider
    from server.services.ai_providers.kimi import KimiProvider

    provider = get_provider("kimi")
    assert isinstance(provider, KimiProvider)


def test_registry_get_unknown():
    from server.services.ai_providers import get_provider

    with pytest.raises(ValueError, match="Unknown AI provider"):
        get_provider("bogus")


# ── 2. Explicit preference — Kimi selected when key is present ───────────────

def test_explicit_preference_kimi(monkeypatch):
    monkeypatch.setenv("AI_BACKEND_PREFERENCE", "kimi,vertex")
    monkeypatch.setenv("KIMI_API_KEY", "test-key")
    # Unset vertex so it's definitely unavailable
    monkeypatch.delenv("VERTEX_CREDENTIALS_PATH", raising=False)

    from server.services.ai_providers import select_provider
    from server.services.ai_providers.kimi import KimiProvider

    provider = select_provider(["kimi", "vertex"])
    assert provider is not None
    assert isinstance(provider, KimiProvider)


# ── 3. (Deleted: test_fallback_to_vertex — Vertex provider no longer exists)


# ── 4. Status endpoint fields ─────────────────────────────────────────────────

def test_status_endpoint_fields(client):
    resp = client.get("/api/ai/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "active_provider" in data
    assert "preference_list" in data
    assert "available_providers" in data
    assert isinstance(data["preference_list"], list)
    assert isinstance(data["available_providers"], list)


def test_status_endpoint_matches_documented_plan6_shape(client):
    """Regression — Sigma #179 finding #2.

    docs/API.md documents `/ai/status` as emitting `provider_order` + a `tasks`
    dict (per-task provider/model/tier) for all 8 AITask values, plus the
    legacy `backend`/`model_fast`/`model_pro`/`preference_list` fields. This
    test asserts the implementation matches the docs so the two cannot drift
    silently.
    """
    from server.services.ai_gateway import AITask
    from server.services.ai_orchestrator import VISION_MODEL

    resp = client.get("/api/ai/status")
    assert resp.status_code == 200
    data = resp.json()

    # Plan 6 fields
    assert "provider_order" in data
    assert isinstance(data["provider_order"], list)
    assert "tasks" in data
    assert isinstance(data["tasks"], dict)

    # All 8 AITask values must be keys in `tasks`
    for task in AITask:
        assert task.value in data["tasks"], f"missing task {task.value}"
        entry = data["tasks"][task.value]
        assert set(entry.keys()) >= {"provider", "model", "tier"}
        assert entry["tier"] in ("max", "pro", "fast")

    assert data["tasks"][AITask.TUTOR_CHAT.value]["tier"] == "max"
    assert data["tasks"][AITask.TUTOR_CHAT.value]["model"] == VISION_MODEL

    # Legacy compat fields
    for legacy_key in ("backend", "model_fast", "model_pro", "preference_list"):
        assert legacy_key in data, f"legacy field {legacy_key} missing"


# ── 5. Malformed preference env — graceful fallback ───────────────────────────

def test_malformed_preference_env(monkeypatch):
    monkeypatch.setenv("AI_BACKEND_PREFERENCE", "!@#$%")

    from server.services import ai_orchestrator

    pref = ai_orchestrator._preference_list()
    # Should fall back to the default without crashing.
    # Default is "kimi" only after the soft-disable of Vertex + Gemini API
    # (see server/services/ai_orchestrator.py::_DEFAULT_PREFERENCE).
    assert pref == ["kimi"]


def test_provider_name_with_underscore_parses(monkeypatch):
    """gemini_api (and any future provider with underscores) must parse."""
    monkeypatch.setenv("AI_BACKEND_PREFERENCE", "gemini_api,kimi")

    from server.services import ai_orchestrator

    assert ai_orchestrator._preference_list() == ["gemini_api", "kimi"]


@pytest.mark.asyncio
async def test_no_backend_raises(monkeypatch):
    """generate() must raise RuntimeError when no provider is available."""
    monkeypatch.delenv("KIMI_API_KEY", raising=False)
    monkeypatch.delenv("VERTEX_CREDENTIALS_PATH", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    from server.services import ai_orchestrator

    with pytest.raises(RuntimeError, match="No AI backend available"):
        await ai_orchestrator.generate("hello")


# ── 6. Envelope shape from KimiProvider ──────────────────────────────────────

@pytest.mark.asyncio
async def test_kimi_envelope_shape(monkeypatch):
    monkeypatch.setenv("KIMI_API_KEY", "fake-key")

    from server.services.ai_providers.kimi import KimiProvider

    fake_response_body = {
        "choices": [
            {"message": {"content": '{"answer": 42}'}}
        ]
    }

    mock_response = MagicMock()
    mock_response.json.return_value = fake_response_body
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    provider = KimiProvider()
    provider._client = mock_client

    result = await provider.generate_json('{"answer": 42}', "moonshot-v1-32k")

    assert "text" in result
    assert "raw" in result
    assert "provider" in result
    assert "model" in result
    assert result["provider"] == "kimi"
    assert result["model"] == "moonshot-v1-32k"
    assert isinstance(result["raw"], dict)
    assert isinstance(result["text"], str)


@pytest.mark.asyncio
async def test_kimi_k2_generate_json_uses_native_json_mode(monkeypatch):
    """K2.X non-vision calls must request native JSON mode at the API layer."""
    monkeypatch.setenv("KIMI_API_KEY", "fake-key")

    from server.services.ai_providers.kimi import KimiProvider

    fake_response_body = {
        "choices": [
            {"message": {"content": '{"answer": 42}'}}
        ]
    }

    mock_response = MagicMock()
    mock_response.json.return_value = fake_response_body
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    provider = KimiProvider()
    provider._client = mock_client

    await provider.generate_json(
        '{"answer": 42}',
        "kimi-k2.6",
        temperature=0.3,
    )

    _, kwargs = mock_client.post.call_args
    payload = kwargs["json"]
    assert payload["model"] == "kimi-k2.6"
    assert payload["temperature"] == 1.0
    assert payload["response_format"] == {"type": "json_object"}
