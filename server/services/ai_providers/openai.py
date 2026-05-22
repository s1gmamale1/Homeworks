"""
OpenAI provider — `/v1/chat/completions` with `gpt-4o-mini` (or override).

Wired into the registry to serve a SUBSET of tasks (configured by
`TASK_PROVIDER_PREFERENCE` in ai_gateway) — notably the dynamic boss
question-generator + answer-checker on non-English homeworks, where Kimi's
Uzbek competence ceiling produces grammatically rough output and the
occasional Chinese-glyph leak. OpenAI is NOT the default for general traffic;
the global `AI_BACKEND_PREFERENCE` keeps Kimi as primary so tutor / answer
check / reflection stay on the cheaper provider.

Reads env vars via server.config:
  OPENAI_API_KEY        — required; empty → is_available() returns False
  OPENAI_BASE_URL       — defaults to https://api.openai.com/v1
  OPENAI_MODEL_FAST     — defaults to gpt-4o-mini
  OPENAI_MODEL_PRO      — defaults to gpt-4o-mini
  OPENAI_TIMEOUT        — defaults to 20 seconds

Vision is intentionally NOT enabled in v1. Notebook capture grading stays on
Kimi's k2.X vision model; if we ever route vision through OpenAI, set
`supports_vision = True` and add a `generate_vision_json` method using
`gpt-4o-mini`'s image_url content blocks.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import httpx

from .base import AIProvider
from . import register

_log = logging.getLogger("nets.openai")


class OpenAIProvider(AIProvider):
    """OpenAI provider using the official `/v1/chat/completions` endpoint."""

    _client: Optional[httpx.AsyncClient] = None

    @property
    def name(self) -> str:
        return "openai"

    def is_available(self) -> bool:
        return bool(os.environ.get("OPENAI_API_KEY", ""))

    @property
    def fast_model(self) -> str:
        return os.environ.get("OPENAI_MODEL_FAST", "gpt-4o-mini")

    @property
    def pro_model(self) -> str:
        return os.environ.get("OPENAI_MODEL_PRO", "gpt-4o-mini")

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            api_key = os.environ.get("OPENAI_API_KEY", "")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY not configured")
            base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
            # 20s leaves headroom over Kimi's 15s — gpt-4o-mini is usually
            # fast (sub-3s for boss-sized prompts), but cold-path tail
            # latency on OpenAI's side can spike. Falling through to Kimi
            # on timeout is preferable to the boss kickoff timer firing.
            timeout = float(os.environ.get("OPENAI_TIMEOUT", "20"))
            self._client = httpx.AsyncClient(
                base_url=base_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                timeout=timeout,
            )
        return self._client

    async def generate_json(self, prompt: str, model: str, **kw) -> dict:
        """Send *prompt* to OpenAI and return a normalised envelope.

        Matches the shape KimiProvider returns so the orchestrator's
        fallback walk can swap providers without callers noticing.
        """
        temperature: float = kw.get("temperature", 0.3)
        json_mode: bool = kw.get("json_mode", True)

        client = self._get_client()
        payload: dict = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        if json_mode:
            # gpt-4o-mini supports the OpenAI-compatible json_object response
            # format identically to Kimi. No magic prompt-word required:
            # the response_format alone enforces syntactically valid JSON.
            payload["response_format"] = {"type": "json_object"}

        try:
            r = await client.post("/chat/completions", json=payload)
            r.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # Surface a useful error body (without leaking credentials —
            # OpenAI response bodies never echo the API key back).
            body_excerpt = ""
            try:
                body_excerpt = exc.response.text[:300]
            except Exception:
                pass
            raise RuntimeError(
                f"OpenAI call failed (HTTP {exc.response.status_code}): {body_excerpt}"
            ) from None

        raw = r.json()
        try:
            text: str = raw["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                f"OpenAI returned unexpected envelope: {str(raw)[:300]}"
            ) from exc

        return {
            "text": text,
            "raw": raw,
            "provider": self.name,
            "model": model,
        }


# Auto-register singleton (mirrors the Kimi pattern). is_available() is
# checked lazily at routing time, so this is safe even when
# OPENAI_API_KEY is unset — select_provider() will just skip past us.
register("openai", OpenAIProvider())
