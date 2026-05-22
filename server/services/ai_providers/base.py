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

    # ── Per-provider model identifiers ────────────────────────────────────────
    #
    # Providers expose their OWN pro/fast model names so the orchestrator can
    # walk a multi-provider fallback chain without each provider needing to
    # accept another provider's model string. The gateway resolves
    # `(provider, model)` together: gateway asks the chosen provider for its
    # pro/fast model name, never the other way around.
    #
    # Defaults raise NotImplementedError so a provider that forgets to expose
    # these fails loud when first routed via tier mode. Providers that only
    # serve legacy callers passing explicit `model=` kwargs are unaffected.

    @property
    def pro_model(self) -> str:
        """Model ID this provider uses for the 'pro' tier (deeper/longer ctx)."""
        raise NotImplementedError(
            f"{type(self).__name__} does not expose a pro_model. "
            "Either define one or only call it with an explicit model= kwarg."
        )

    @property
    def fast_model(self) -> str:
        """Model ID this provider uses for the 'fast' tier (cheaper/quicker)."""
        raise NotImplementedError(
            f"{type(self).__name__} does not expose a fast_model. "
            "Either define one or only call it with an explicit model= kwarg."
        )

    # ── Vision extension (optional — default: not supported) ─────────────────

    @property
    def supports_vision(self) -> bool:
        """Return True when the provider accepts image inputs."""
        return False

    @property
    def vision_model(self) -> Optional[str]:
        """Default model ID to use for vision calls, or None if not supported."""
        return None
