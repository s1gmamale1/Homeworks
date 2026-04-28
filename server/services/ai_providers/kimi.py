"""
Kimi (Moonshot AI) provider — OpenAI-compatible chat completions.

Reads env vars via server.config:
  KIMI_API_KEY    — required; empty → is_available() returns False
  KIMI_BASE_URL   — defaults to https://api.moonshot.ai/v1
  KIMI_MODEL_FAST — defaults to moonshot-v1-32k
  KIMI_MODEL_PRO  — defaults to moonshot-v1-128k
"""
from __future__ import annotations

import os
from typing import Optional

import httpx

from .base import AIProvider
from . import register


class KimiProvider(AIProvider):
    """Moonshot / Kimi provider using the OpenAI-compatible endpoint."""

    _client: Optional[httpx.AsyncClient] = None

    @property
    def name(self) -> str:
        return "kimi"

    def is_available(self) -> bool:
        return bool(os.environ.get("KIMI_API_KEY", ""))

    @property
    def fast_model(self) -> str:
        return os.environ.get("KIMI_MODEL_FAST", "moonshot-v1-32k")

    @property
    def pro_model(self) -> str:
        return os.environ.get("KIMI_MODEL_PRO", "moonshot-v1-128k")

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            api_key = os.environ.get("KIMI_API_KEY", "")
            if not api_key:
                raise RuntimeError("KIMI_API_KEY not configured")
            base_url = os.environ.get("KIMI_BASE_URL", "https://api.moonshot.ai/v1")
            self._client = httpx.AsyncClient(
                base_url=base_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                timeout=60.0,
            )
        return self._client

    async def generate_json(self, prompt: str, model: str, **kw) -> dict:
        """Send *prompt* to Kimi and return a normalised envelope."""
        temperature: float = kw.get("temperature", 0.3)
        json_mode: bool = kw.get("json_mode", True)

        client = self._get_client()
        payload: dict = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        r = await client.post("/chat/completions", json=payload)
        r.raise_for_status()
        raw = r.json()
        text: str = raw["choices"][0]["message"]["content"]
        return {
            "text": text,
            "raw": raw,
            "provider": self.name,
            "model": model,
        }


# Auto-register singleton
register("kimi", KimiProvider())
