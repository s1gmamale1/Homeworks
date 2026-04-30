"""
AI provider registry.

Usage
-----
from server.services.ai_providers import get_provider, select_provider, register

# Register a provider class (done automatically on import of each provider module)
register("kimi", KimiProvider())

# Retrieve by name — raises ValueError if unknown
provider = get_provider("kimi")

# Walk a preference list, return first available, or None
provider = select_provider(["kimi", "vertex", "gemini_api"])
"""
from __future__ import annotations

from typing import Optional

from .base import AIProvider

_REGISTRY: dict[str, AIProvider] = {}


def register(name: str, instance: AIProvider) -> None:
    """Register a provider instance under *name*."""
    _REGISTRY[name] = instance


def get_provider(name: str) -> AIProvider:
    """Return the registered provider for *name*.

    Raises
    ------
    ValueError
        If *name* has not been registered.
    """
    if name not in _REGISTRY:
        raise ValueError(
            f"Unknown AI provider: {name!r}. Registered: {list(_REGISTRY)}"
        )
    return _REGISTRY[name]


def select_provider(preference: list[str]) -> Optional[AIProvider]:
    """Walk *preference* list; return first provider that is available.

    Returns ``None`` if no provider in the list is registered and available.
    """
    for name in preference:
        try:
            provider = get_provider(name)
        except ValueError:
            continue
        if provider.is_available():
            return provider
    return None


def available_providers() -> list[str]:
    """Return names of all registered providers whose ``is_available()`` is True."""
    return [name for name, p in _REGISTRY.items() if p.is_available()]


# --- Auto-import concrete providers so they self-register ---
from . import kimi as _kimi          # noqa: E402, F401
from . import vertex as _vertex      # noqa: E402, F401
from . import gemini_api as _gemini  # noqa: E402, F401

__all__ = [
    "AIProvider",
    "register",
    "get_provider",
    "select_provider",
    "available_providers",
]
