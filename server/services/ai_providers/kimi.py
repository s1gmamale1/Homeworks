"""
Kimi (Moonshot AI) provider — OpenAI-compatible chat completions.

Reads env vars via server.config:
  KIMI_API_KEY          — required; empty → is_available() returns False
  KIMI_BASE_URL         — defaults to https://api.moonshot.ai/v1
  KIMI_MODEL_FAST       — defaults to moonshot-v1-32k
  KIMI_MODEL_PRO        — defaults to moonshot-v1-128k
  KIMI_MODEL_VISION     — defaults to kimi-k2.6 (vision-capable)
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import httpx

from .base import AIProvider
from . import register

_log = logging.getLogger("nets.kimi")


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

    # ── Vision extension ──────────────────────────────────────────────────────

    @property
    def supports_vision(self) -> bool:
        return True

    @property
    def vision_model(self) -> str:  # type: ignore[override]
        return os.environ.get("KIMI_MODEL_VISION", "kimi-k2.6")

    @staticmethod
    def _is_k2x_model(model_id: str) -> bool:
        mid_lower = model_id.lower()
        return mid_lower.startswith("kimi-k2") or "k2." in mid_lower

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
        is_k2x = self._is_k2x_model(model)
        effective_temperature = 1.0 if is_k2x else temperature

        client = self._get_client()
        payload: dict = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": effective_temperature,
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

    async def generate_vision_json(
        self,
        prompt: str,
        image_b64: str,
        mime: str = "image/jpeg",
        model: Optional[str] = None,
        **kw,
    ) -> dict:
        """Send an image + prompt to a vision-capable Kimi model.

        Builds an OpenAI-compatible multimodal content array. Falls back from
        the configured vision model to ``moonshot-v1-128k-vision-preview`` when
        the primary returns HTTP 404 (model not found on this endpoint).

        Returns the standard normalised envelope::

            { "text": str, "raw": dict, "provider": "kimi", "model": str }
        """
        temperature: float = kw.get("temperature", 0.1)
        json_mode: bool = kw.get("json_mode", True)

        primary_model: str = model or self.vision_model
        fallback_model: str = "moonshot-v1-128k-vision-preview"

        content = [
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{image_b64}"},
            },
            {"type": "text", "text": prompt},
        ]

        async def _call(model_id: str) -> dict:
            client = self._get_client()
            # K2.X agentic/thinking models pin temperature=1; only the
            # `moonshot-v1-*` line accepts arbitrary temperatures. Passing 0.1
            # to K2.X yields HTTP 400 "only 1 is allowed for this model".
            is_k2x = self._is_k2x_model(model_id)
            effective_temperature = 1.0 if is_k2x else temperature
            payload: dict = {
                "model": model_id,
                "messages": [{"role": "user", "content": content}],
                "temperature": effective_temperature,
            }
            # response_format=json_object is supported on moonshot-v1-* but
            # rejected by some K2.X variants; only set it for the older line.
            if json_mode and not is_k2x:
                payload["response_format"] = {"type": "json_object"}
            # K2.X thinking models can take 30-120s; the default 60s client
            # timeout is too tight for vision. Override per-call.
            vision_timeout = float(os.environ.get("KIMI_VISION_TIMEOUT", "180"))
            r = await client.post(
                "/chat/completions", json=payload, timeout=vision_timeout
            )
            r.raise_for_status()
            raw = r.json()
            text: str = raw["choices"][0]["message"]["content"]
            return {
                "text": text,
                "raw": raw,
                "provider": self.name,
                "model": model_id,
            }

        try:
            return await _call(primary_model)
        except httpx.HTTPStatusError as exc:
            # Capture body for debugging (sanitize-free: response body never
            # contains our credentials, only API error message).
            body_excerpt = ""
            try:
                body_excerpt = exc.response.text[:300]
            except Exception:
                pass
            if exc.response.status_code == 404 and primary_model != fallback_model:
                _log.warning(
                    "Vision model %r returned 404; falling back to %r",
                    primary_model,
                    fallback_model,
                )
                return await _call(fallback_model)
            # 400 on K2.X often means temperature/format mismatch we should
            # have prevented above; surface the body so future debugging is
            # not silenced.
            raise RuntimeError(
                f"Kimi vision call failed (HTTP {exc.response.status_code}): {body_excerpt}"
            ) from None


# Auto-register singleton
register("kimi", KimiProvider())
