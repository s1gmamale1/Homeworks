"""PR B — runtime provider fallback chain regression tests.

Locks audit finding C6: `ai_orchestrator.generate` was calling `select_provider` once
at request time and surfacing the raw exception on any failure. The chain
advertised in STATE.md (Vertex → Gemini → Kimi → stock) was not actually
wired at runtime — only at startup selection. These tests assert that
`ai_orchestrator.generate` now walks every available provider in preference order on
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

from server.services import ai_orchestrator
from server.services.ai_providers import _REGISTRY, register


# ---------------------------------------------------------------------------
# Helpers — install/uninstall fake providers in the registry
# ---------------------------------------------------------------------------


class _FakeProvider:
    """Minimal AIProvider stub. `is_available()` is True; `generate_json`
    behaviour is set per-test by assigning to `.generate_json` directly.

    Optional ``pro_model_name`` / ``fast_model_name`` ctor args expose the
    tier-mode interface; tier tests rely on each fake provider returning a
    DIFFERENT model name so a cross-provider walk verifies the model swap.
    """

    def __init__(
        self,
        name: str,
        *,
        pro_model_name: str = "fake-pro",
        fast_model_name: str = "fake-fast",
    ):
        self._name = name
        self._pro_model = pro_model_name
        self._fast_model = fast_model_name
        self.calls: list[str] = []
        # Each provider also records the MODEL string it was called with, so
        # tier-mode tests can assert each provider got its OWN model name
        # rather than the previous provider's leftover string.
        self.models_received: list[str] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def pro_model(self) -> str:
        return self._pro_model

    @property
    def fast_model(self) -> str:
        return self._fast_model

    def is_available(self) -> bool:
        return True

    async def generate_json(self, prompt: str, model: str, **kw) -> dict:
        # Default: track call + return a stub envelope. Tests can replace
        # this method per-instance to simulate failure.
        self.calls.append(prompt[:32])
        self.models_received.append(model)
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
    # real KimiProvider singleton.
    _REGISTRY.clear()
    _REGISTRY.update(snapshot)


# ---------------------------------------------------------------------------
# 1. Happy path — first provider succeeds, others not called
# ---------------------------------------------------------------------------


def test_first_provider_success_short_circuits(fake_chain):
    async def _run():
        return await ai_orchestrator.generate("hello")

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
        return await ai_orchestrator.generate("hello")

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
        return await ai_orchestrator.generate("hello")

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
        await ai_orchestrator.generate("hello")

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
        await ai_orchestrator.generate("hello")

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
        return await ai_orchestrator.generate("hello")

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
        return await ai_orchestrator.generate("hello")

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


# ---------------------------------------------------------------------------
# 9. Tier-mode resolves model PER PROVIDER during the walk
#
# Regression for the cross-provider model bug surfaced by the GPT-integration
# stress test (2026-05-13). Pre-fix: orchestrator captured ONE model string
# up front and reused it across every provider it tried, so an
# `openai → kimi` fallback chain would send `gpt-4o-mini` to Moonshot and
# get a 400 "unknown model" instead of cleanly falling over.
# ---------------------------------------------------------------------------


@pytest.fixture
def two_provider_chain(monkeypatch):
    """openai + kimi fakes with DIFFERENT pro/fast model names so tests can
    assert each provider was called with its own model string, not the
    other's."""
    snapshot = dict(_REGISTRY)
    fakes = {
        "openai": _FakeProvider(
            "openai",
            pro_model_name="gpt-4o-mini",
            fast_model_name="gpt-4o-mini",
        ),
        "kimi": _FakeProvider(
            "kimi",
            pro_model_name="moonshot-v1-128k",
            fast_model_name="moonshot-v1-32k",
        ),
    }
    for name, provider in fakes.items():
        _REGISTRY[name] = provider
    monkeypatch.setenv("AI_BACKEND_PREFERENCE", "kimi")  # global default
    yield fakes
    _REGISTRY.clear()
    _REGISTRY.update(snapshot)


def test_tier_mode_picks_each_providers_own_pro_model(two_provider_chain):
    """When tier="pro" is passed, the orchestrator must ask EACH provider
    for its own pro_model — never reuse the previous provider's model."""

    async def _run():
        return await ai_orchestrator.generate(
            "hello",
            tier="pro",
            preference_override=["openai", "kimi"],
        )

    text = asyncio.run(_run())
    assert text == "reply from openai"
    # openai got called with its own pro model
    assert two_provider_chain["openai"].models_received == ["gpt-4o-mini"]
    # kimi never touched (openai succeeded)
    assert two_provider_chain["kimi"].calls == []


def test_tier_mode_swaps_model_on_cross_provider_fallback(two_provider_chain):
    """THE critical regression — openai fails, fallback walks to kimi, and
    kimi must receive moonshot-v1-128k (its own model), NOT gpt-4o-mini
    inherited from openai's request. Without per-provider resolution this
    would 400 on Kimi."""

    async def _openai_5xx(prompt, model, **kw):
        raise RuntimeError("OpenAI 503 Service Unavailable")

    two_provider_chain["openai"].generate_json = _openai_5xx

    async def _run():
        return await ai_orchestrator.generate(
            "hello",
            tier="pro",
            preference_override=["openai", "kimi"],
        )

    text = asyncio.run(_run())
    assert text == "reply from kimi"
    # The actual proof: kimi got its OWN model name, not openai's.
    assert two_provider_chain["kimi"].models_received == ["moonshot-v1-128k"], (
        "Cross-provider fallback must pass each provider its own model. "
        "Pre-fix bug: kimi received gpt-4o-mini and 400'd."
    )


def test_tier_mode_uses_fast_model_when_tier_fast(two_provider_chain):
    """`tier='fast'` walks fast_model on each provider, not pro_model."""

    async def _run():
        return await ai_orchestrator.generate(
            "hello",
            tier="fast",
            preference_override=["kimi"],
        )

    text = asyncio.run(_run())
    assert text == "reply from kimi"
    assert two_provider_chain["kimi"].models_received == ["moonshot-v1-32k"]


def test_legacy_model_kwarg_still_works_without_tier(two_provider_chain):
    """Backward-compat — callers that pass explicit `model=` keep working
    (the orchestrator skips tier resolution entirely)."""

    async def _run():
        return await ai_orchestrator.generate(
            "hello",
            model="legacy-explicit-model",
            preference_override=["kimi"],
        )

    text = asyncio.run(_run())
    assert text == "reply from kimi"
    # The model passed via kwarg was used verbatim (no tier resolution).
    assert two_provider_chain["kimi"].models_received == ["legacy-explicit-model"]
