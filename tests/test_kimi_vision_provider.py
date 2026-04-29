"""
Wave K — tests for KimiProvider vision extension.

pytest tests/test_kimi_vision_provider.py -v
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_ok_response(content: str = '{"result": "ok"}', model: str = "kimi-k2.6") -> MagicMock:
    """Return a mock httpx.Response that looks like a successful Kimi API reply."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": content}}],
        "model": model,
    }
    mock_resp.raise_for_status = MagicMock()  # no-op
    return mock_resp


def _make_404_response() -> MagicMock:
    """Return a mock httpx.Response that simulates a 404 Model Not Found."""
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    # Simulate raise_for_status raising HTTPStatusError
    err = httpx.HTTPStatusError(
        "404 Not Found",
        request=MagicMock(),
        response=mock_resp,
    )
    mock_resp.raise_for_status.side_effect = err
    return mock_resp


# ── 1. generate_vision_json builds correct OpenAI-compatible message ──────────

@pytest.mark.asyncio
async def test_vision_message_format(monkeypatch):
    """generate_vision_json must send a multimodal content array to the API."""
    monkeypatch.setenv("KIMI_API_KEY", "test-key")

    from server.services.ai_providers.kimi import KimiProvider

    provider = KimiProvider()
    provider._client = None  # ensure fresh client; we'll monkey-patch post

    captured_payload: dict = {}

    async def mock_post(path, *, json=None, **kw):
        nonlocal captured_payload
        captured_payload = json or {}
        return _make_ok_response()

    mock_client = MagicMock()
    mock_client.post = mock_post
    provider._client = mock_client

    result = await provider.generate_vision_json(
        prompt="Extract formulas",
        image_b64="AAAA",
        mime="image/jpeg",
        model="kimi-k2.6",
    )

    # Verify envelope shape
    assert result["provider"] == "kimi"
    assert result["model"] == "kimi-k2.6"
    assert "text" in result
    assert "raw" in result

    # Verify the sent payload has the multimodal content array
    messages = captured_payload.get("messages", [])
    assert len(messages) == 1
    content = messages[0]["content"]
    assert isinstance(content, list), "content must be a list for vision calls"

    types = [item["type"] for item in content]
    assert "image_url" in types, "must include an image_url block"
    assert "text" in types, "must include a text block"

    image_block = next(item for item in content if item["type"] == "image_url")
    url = image_block["image_url"]["url"]
    assert url.startswith("data:image/jpeg;base64,"), f"unexpected url prefix: {url[:40]}"
    assert "AAAA" in url


# ── 2. Default model is kimi-k2.6; env-var override works ────────────────────

def test_vision_model_default(monkeypatch):
    """vision_model property must default to kimi-k2.6."""
    monkeypatch.delenv("KIMI_MODEL_VISION", raising=False)

    from server.services.ai_providers.kimi import KimiProvider

    provider = KimiProvider()
    assert provider.vision_model == "kimi-k2.6"
    assert provider.supports_vision is True


def test_vision_model_env_override(monkeypatch):
    """KIMI_MODEL_VISION env var must override the default model."""
    monkeypatch.setenv("KIMI_MODEL_VISION", "moonshot-v1-128k-vision-preview")

    from server.services.ai_providers.kimi import KimiProvider

    provider = KimiProvider()
    assert provider.vision_model == "moonshot-v1-128k-vision-preview"


# ── 3. 404 fallback to moonshot-v1-128k-vision-preview ───────────────────────

@pytest.mark.asyncio
async def test_vision_404_fallback(monkeypatch):
    """When primary vision model returns 404, must retry with fallback model."""
    monkeypatch.setenv("KIMI_API_KEY", "test-key")
    monkeypatch.delenv("KIMI_MODEL_VISION", raising=False)  # ensure default kimi-k2.6

    from server.services.ai_providers.kimi import KimiProvider

    provider = KimiProvider()

    call_log: list[dict] = []

    async def mock_post(path, *, json=None, **kw):
        payload = json or {}
        call_log.append({"model": payload.get("model")})
        if payload.get("model") == "kimi-k2.6":
            # Simulate 404 on primary
            return _make_404_response()
        # Fallback succeeds
        return _make_ok_response(model=payload.get("model", "fallback"))

    mock_client = MagicMock()
    mock_client.post = mock_post
    provider._client = mock_client

    result = await provider.generate_vision_json(
        prompt="parse this",
        image_b64="BASE64DATA",
        mime="image/png",
    )

    # Two calls: primary (404) then fallback (200)
    assert len(call_log) == 2
    assert call_log[0]["model"] == "kimi-k2.6"
    assert call_log[1]["model"] == "moonshot-v1-128k-vision-preview"
    assert result["model"] == "moonshot-v1-128k-vision-preview"


# ── 4. Error scrubbing: API errors don't leak credentials ────────────────────

@pytest.mark.asyncio
async def test_vision_error_scrubbing(monkeypatch):
    """HTTPStatusError must not surface the Authorization header in exception text."""
    secret_key = "super-secret-api-key-12345"
    monkeypatch.setenv("KIMI_API_KEY", secret_key)
    monkeypatch.setenv("KIMI_MODEL_VISION", "kimi-k2.6")

    from server.services.ai_providers.kimi import KimiProvider

    provider = KimiProvider()

    async def mock_post(path, *, json=None, **kw):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        err = httpx.HTTPStatusError(
            f"500 Internal Server Error — Authorization: Bearer {secret_key}",
            request=MagicMock(),
            response=mock_resp,
        )
        mock_resp.raise_for_status.side_effect = err
        return mock_resp

    mock_client = MagicMock()
    mock_client.post = mock_post
    provider._client = mock_client

    with pytest.raises(RuntimeError) as exc_info:
        await provider.generate_vision_json(
            prompt="test",
            image_b64="data",
            mime="image/jpeg",
        )

    error_text = str(exc_info.value)
    assert secret_key not in error_text, (
        f"API key leaked in exception message: {error_text!r}"
    )
