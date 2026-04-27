"""
Public Gemini API provider — uses google-genai SDK with an API key.

Reads env vars:
  GEMINI_API_KEY — required; empty or "your_api_key_here" → unavailable
"""
from __future__ import annotations

import asyncio
import os

from .base import AIProvider
from . import register

_PLACEHOLDER = "your_api_key_here"


class GeminiAPIProvider(AIProvider):
    """Public Gemini API (not Vertex) via google-genai SDK."""

    _client = None  # google.genai.Client, lazy-initialised

    @property
    def name(self) -> str:
        return "gemini"

    def is_available(self) -> bool:
        key = os.environ.get("GEMINI_API_KEY", "")
        return bool(key and key != _PLACEHOLDER)

    def _get_client(self):
        if self._client is not None:
            return self._client
        from google import genai  # lazy import

        api_key = os.environ.get("GEMINI_API_KEY", "")
        self._client = genai.Client(api_key=api_key)
        return self._client

    async def generate_json(self, prompt: str, model: str, **kw) -> dict:
        """Send *prompt* to the public Gemini API and return a normalised envelope."""
        from google.genai import types  # lazy import

        temperature: float = kw.get("temperature", 0.3)
        json_mode: bool = kw.get("json_mode", True)

        client = self._get_client()
        config = types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type="application/json" if json_mode else "text/plain",
        )
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            ),
        )
        text: str = response.text
        raw = {"text": text, "_source": "gemini_api"}
        return {
            "text": text,
            "raw": raw,
            "provider": self.name,
            "model": model,
        }


# Auto-register singleton
register("gemini", GeminiAPIProvider())
