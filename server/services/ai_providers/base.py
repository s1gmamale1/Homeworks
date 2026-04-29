"""
Abstract base class for all AI providers.

Each provider must implement:
  - name: str                                    — registry key (e.g. "kimi")
  - is_available() -> bool                       — True if credentials are present
  - generate_json(prompt, model, **kw) -> dict   — returns normalised envelope:
      { text: str, raw: dict, provider: str, model: str }

Optional vision extension:
  - supports_vision: bool                        — True when the provider can process images
  - vision_model: Optional[str]                  — default model ID for vision calls
  - generate_vision_json(prompt, image_b64, mime, **kw) -> dict
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class AIProvider(ABC):
    """Abstract AI provider. Subclass and register via the registry."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique registry key, e.g. 'kimi', 'vertex', 'gemini'."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True when the required credentials / files are present."""

    @abstractmethod
    async def generate_json(self, prompt: str, model: str, **kw) -> dict:
        """
        Call the provider and return a normalised envelope::

            {
                "text":     str,   # parsed JSON string from the model
                "raw":      dict,  # full provider response payload
                "provider": str,   # self.name
                "model":    str,   # model identifier actually used
            }
        """

    # ── Vision extension (optional — default: not supported) ─────────────────

    @property
    def supports_vision(self) -> bool:
        """Return True when the provider accepts image inputs."""
        return False

    @property
    def vision_model(self) -> Optional[str]:
        """Default model ID to use for vision calls, or None if not supported."""
        return None
