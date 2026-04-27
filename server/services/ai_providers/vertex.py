"""
Vertex AI (Google) provider — uses google-genai SDK.

Reads env vars via server.config:
  VERTEX_CREDENTIALS_PATH — path to service-account JSON; empty/missing → unavailable
  VERTEX_PROJECT          — GCP project ID (derived from creds file if absent)
  VERTEX_LOCATION         — defaults to us-central1
"""
from __future__ import annotations

import asyncio
import json
import os
from typing import Optional

from .base import AIProvider
from . import register


class VertexProvider(AIProvider):
    """Google Vertex AI via the google-genai SDK."""

    _client = None  # google.genai.Client, lazy-initialised

    @property
    def name(self) -> str:
        return "vertex"

    def is_available(self) -> bool:
        path = os.environ.get("VERTEX_CREDENTIALS_PATH", "")
        return bool(path and os.path.exists(path))

    def _resolve_project(self, creds_path: str) -> str:
        project = os.environ.get("VERTEX_PROJECT", "")
        if project:
            return project
        try:
            with open(creds_path, "r", encoding="utf-8") as f:
                return json.load(f).get("project_id", "")
        except Exception:
            return ""

    def _get_client(self):
        if self._client is not None:
            return self._client
        from google import genai  # lazy import — optional dependency

        creds_path = os.environ.get("VERTEX_CREDENTIALS_PATH", "")
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
        project = self._resolve_project(creds_path)
        if not project:
            raise RuntimeError(
                f"Vertex project not set and could not be read from {creds_path}"
            )
        location = os.environ.get("VERTEX_LOCATION", "us-central1")
        self._client = genai.Client(
            vertexai=True,
            project=project,
            location=location,
        )
        return self._client

    async def generate_json(self, prompt: str, model: str, **kw) -> dict:
        """Send *prompt* to Vertex AI and return a normalised envelope."""
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
        raw = {"text": text, "_source": "vertex"}
        return {
            "text": text,
            "raw": raw,
            "provider": self.name,
            "model": model,
        }


# Auto-register singleton
register("vertex", VertexProvider())
