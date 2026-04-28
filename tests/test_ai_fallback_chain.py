"""PR B — runtime provider fallback chain regression tests.

Locks audit finding C6: `gemini.generate` was calling `select_provider` once
at request time and surfacing the raw exception on any failure. The chain
advertised in STATE.md (Vertex → Gemini → Kimi → stock) was not actually
wired at runtime — only at startup selection. These tests assert that
`gemini.generate` now walks every available provider in preference order on
exception, only raising RuntimeError when all have failed.

Each test uses MagicMock providers registered into the registry so the chain
can be exercised without real credentials, and asserts the bad pre-fix state
("first provider's exception propagates immediately") cannot return.
"""
from __future__ import annotations

import asyncio
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.services import gemini
from server.services.ai_providers import _REGISTRY, register


# ---------------------------------------------------------------------------
# Helpers — install/uninstall fake providers in the registry
# ---------------------------------------------------------------------------


class _FakeProvider:
    """Minimal AIProvider stub. `is_available()` is True; `generate_json`
    behaviour is set per-test by assigning to `.generate_json` directly.
    """

    def __init__(self, name: str):
        self._name = name
        self.calls: list[str] = []

    @property
    def name(self) -> str:
        return self._name

    def is_available(self) -> bool:
        return True

    async def generate_json(self, prompt: str, model: str, **kw) -> dict:
        # Default: track call + return a stub envelope. Tests can replace
        # this method per-instance to simulate failure.
        self.calls.append(prompt[:32])
        return {
            "text": f"reply from {self._name}",
            "raw": {},
            "provider": self._name,
            "model": model,
        }


@pytest.fixture
def fake_chain(monkeypatch):
    """Install three fake providers under the names the preference list uses,
    snapshot+restore the registry around the test so other suites are not
    polluted."""
    snapshot = dict(_REGISTRY)
    fakes = {
        "vertex": _FakeProvider("vertex"),
        "gemini_api": _FakeProvider("gemini_api"),
        "kimi": _FakeProvider("kimi"),
    }
    for name, provider in fakes.items():
        _REGISTRY[name] = provider

    monkeypatch.setenv(
        "AI_BACKEND_PREFERENCE", "vertex,gemini_api,kimi"
    )

    yield fakes

    # Restore the live registry — IMPORTANT so subsequent tests still see the
    # real KimiProvider / VertexProvider singletons.
    _REGISTRY.clear()
    _REGISTRY.update(snapshot)


# ---------------------------------------------------------------------------
# 1. Happy path — first provider succeeds, others not called
# ---------------------------------------------------------------------------


def test_first_provider_success_short_circuits(fake_chain):
    async def _run():
        return await gemini.generate("hello")

    text = asyncio.run(_run())
    assert text == "reply from vertex"
    assert len(fake_chain["vertex"].calls) == 1
    assert fake_chain["gemini_api"].calls == []
    assert fake_chain["kimi"].calls == []


# ---------------------------------------------------------------------------
# 2. First fails → second succeeds (the actual regression we're guarding)
# ---------------------------------------------------------------------------


def test_first_provider_failure_falls_through_to_second(fake_chain):
    """Pre-fix: a Vertex 5xx blew up the request even when Gemini was healthy.
    Post-fix: the chain walks to the next provider on exception."""

    async def _vertex_5xx(prompt, model, **kw):
        raise RuntimeError("Vertex 503 Service Unavailable")

    fake_chain["vertex"].generate_json = _vertex_5xx

    async def _run():
        return await gemini.generate("hello")

    text = asyncio.run(_run())
    assert text == "reply from gemini_api", (
        "When the primary provider raises, the chain MUST fall through to "
        "the next available provider. Pre-fix code re-raised."
    )
    assert len(fake_chain["gemini_api"].calls) == 1
    assert fake_chain["kimi"].calls == [], "third provider should not be touched"


# ---------------------------------------------------------------------------
# 3. First two fail → third succeeds (full chain exercise)
# ---------------------------------------------------------------------------


def test_chain_walks_to_third_provider_on_double_failure(fake_chain):
    async def _boom(prompt, model, **kw):
        raise RuntimeError("upstream is sad")

    fake_chain["vertex"].generate_json = _boom
    fake_chain["gemini_api"].generate_json = _boom

    async def _run():
        return await gemini.generate("hello")

    text = asyncio.run(_run())
    assert text == "reply from kimi"


# ---------------------------------------------------------------------------
# 4. All providers fail → single RuntimeError with provider list
# ---------------------------------------------------------------------------


def test_all_providers_fail_raises_runtime_error_with_list(fake_chain):
    async def _boom(prompt, model, **kw):
        raise RuntimeError("nope")

    for fake in fake_chain.values():
        fake.generate_json = _boom

    async def _run():
        await gemini.generate("hello")

    with pytest.raises(RuntimeError) as excinfo:
        asyncio.run(_run())

    msg = str(excinfo.value)
    assert "All AI providers failed" in msg
    # Every attempted provider should appear in the error string so on-call
    # can see exactly what was tried.
    assert "vertex" in msg
    assert "gemini_api" in msg
    assert "kimi" in msg


# ---------------------------------------------------------------------------
# 5. Provider error string is NOT echoed to the caller's RuntimeError
# ---------------------------------------------------------------------------


def test_provider_error_strings_do_not_leak_into_runtime_error(fake_chain):
    """The original exception is preserved as `__cause__` (so on-call can
    inspect via the exception chain), but the public RuntimeError message
    must NOT inline provider error text — that's how API-key fragments and
    GCP project IDs would leak to clients via tutor.py's HTTP 500 path.
    """
    sensitive = "Vertex AI 401: invalid bearer token sk-SECRET-LEAK-TOKEN-9000"

    async def _leaky(prompt, model, **kw):
        raise RuntimeError(sensitive)

    for fake in fake_chain.values():
        fake.generate_json = _leaky

    async def _run():
        await gemini.generate("hello")

    with pytest.raises(RuntimeError) as excinfo:
        asyncio.run(_run())

    assert sensitive not in str(excinfo.value), (
        "Sensitive provider error text leaked into RuntimeError message"
    )


# ---------------------------------------------------------------------------
# 6. Order in preference list controls fallback order
# ---------------------------------------------------------------------------


def test_preference_order_drives_fallback_order(fake_chain, monkeypatch):
    """Override the preference to put kimi first; the chain should try kimi
    first, then gemini_api, then vertex — matching the preference order, not
    the registration order."""
    monkeypatch.setenv("AI_BACKEND_PREFERENCE", "kimi,gemini_api,vertex")

    async def _boom(prompt, model, **kw):
        raise RuntimeError("fail")

    fake_chain["kimi"].generate_json = _boom
    fake_chain["gemini_api"].generate_json = _boom
    # vertex stays as the default success stub

    async def _run():
        return await gemini.generate("hello")

    text = asyncio.run(_run())
    assert text == "reply from vertex"


# ---------------------------------------------------------------------------
# 7. Unavailable providers in the preference are skipped, not retried
# ---------------------------------------------------------------------------


def test_unavailable_providers_skipped(fake_chain):
    """If a provider in the preference list reports `is_available() == False`,
    it must be skipped silently — not counted as a failure, not in the
    "tried" list."""
    fake_chain["vertex"].is_available = lambda: False  # type: ignore[assignment]

    async def _run():
        return await gemini.generate("hello")

    text = asyncio.run(_run())
    assert text == "reply from gemini_api"
    # vertex was skipped → no call recorded
    assert fake_chain["vertex"].calls == []


# ---------------------------------------------------------------------------
# 8. tutor.tutor_chat surfaces a friendly error when the whole chain fails
# ---------------------------------------------------------------------------


def test_tutor_chat_returns_scrubbed_500_when_whole_chain_fails(
    fake_chain, client
):
    """End-to-end: simulate every provider failing; tutor.tutor_chat must
    catch the RuntimeError, scrub it, and return HTTP 500 with the
    TUTOR_BACKEND_ERROR code (PR #47 wired the scrub)."""

    async def _boom(prompt, model, **kw):
        raise RuntimeError("everything is on fire")

    for fake in fake_chain.values():
        fake.generate_json = _boom

    # Create a homework so the route doesn't 404
    create = client.post(
        "/api/homeworks",
        json={
            "title": "Chain failure test",
            "subject": "math-algebra",
            "grade": 8,
            "mode": "hard",
        },
    )
    assert create.status_code == 200
    hw_id = create.json()["id"]

    resp = client.post(
        "/api/ai/tutor/chat",
        json={
            "session_id": "sess-chain-fail",
            "hw_id": hw_id,
            "phase": "preview",
            "message": "anything",
        },
    )
    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert detail["code"] == "TUTOR_BACKEND_ERROR"
    # The scrubbed message reaches the browser; the raw error stays in logs.
    assert "everything is on fire" not in detail["error"]
