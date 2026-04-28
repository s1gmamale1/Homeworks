"""
AI client shim — thin wrapper over the provider registry.

Public API (unchanged from Wave C):
  - generate_json(prompt, context, model, schema_hint) -> dict
  - generate(prompt, context, model, json_mode, temperature) -> str
  - health_check() -> bool
  - ACTIVE_BACKEND: str   ("kimi" | "vertex" | "gemini" | "none")
  - FAST_MODEL, PRO_MODEL: str

All routing logic has moved to server/services/ai_providers/.
This module exists purely to keep existing call-sites (tutor.py etc.) unchanged.
"""
from __future__ import annotations

import json
import os
from typing import Optional

# Keep for backward compat — ai.py status endpoint reads these
from ..config import VERTEX_CREDENTIALS_PATH, VERTEX_LOCATION  # noqa: F401

# Provider registry — concrete providers self-register on import
from .ai_providers import get_provider, select_provider, available_providers  # noqa: F401
from .ai_providers.kimi import KimiProvider
from .ai_providers.vertex import VertexProvider

# ── Compatibility helper used by routes/ai.py ─────────────────────────────────
def _resolve_vertex_project(creds_path: str) -> str:
    return VertexProvider()._resolve_project(creds_path)


# ── Model name constants ───────────────────────────────────────────────────────
FAST_MODEL: str = "gemini-2.5-flash"
PRO_MODEL: str = "gemini-2.5-pro"

# ── Preference parsing ────────────────────────────────────────────────────────
_DEFAULT_PREFERENCE = "kimi,vertex,gemini_api"

# Provider-name regex: lowercase letters with optional underscores. Permits
# "gemini_api" / "kimi" / future "openai" without dropping valid names.
import re as _re

_PROVIDER_NAME_RE = _re.compile(r"^[a-z][a-z0-9_]*$")


def _parse_preference(raw: str) -> list[str]:
    """Parse comma-separated provider names; fall back to default on garbage input."""
    try:
        parts = [p.strip() for p in raw.split(",") if _PROVIDER_NAME_RE.match(p.strip())]
        if not parts:
            raise ValueError("empty after sanitisation")
        return parts
    except Exception:
        return _DEFAULT_PREFERENCE.split(",")


def _preference_list() -> list[str]:
    raw = os.environ.get("AI_BACKEND_PREFERENCE", _DEFAULT_PREFERENCE)
    return _parse_preference(raw)


# ── Active backend ────────────────────────────────────────────────────────────
def _active_backend() -> str:
    p = select_provider(_preference_list())
    return p.name if p else "none"


def __getattr__(name: str):  # noqa: N807
    """Module-level __getattr__ so `gemini.ACTIVE_BACKEND` stays dynamic."""
    if name == "ACTIVE_BACKEND":
        return _active_backend()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# ── Model resolution ──────────────────────────────────────────────────────────
def _resolve_model(model: str, provider) -> str:
    """Map gemini-native model names to provider-specific equivalents.

    Takes the provider INSTANCE (already resolved by select_provider) instead
    of re-fetching by name — avoids a redundant registry lookup per request.
    """
    if isinstance(provider, KimiProvider):
        if model == FAST_MODEL:
            return provider.fast_model
        if model == PRO_MODEL:
            return provider.pro_model
    return model


# ── Public API ────────────────────────────────────────────────────────────────

async def generate(
    prompt: str,
    context: str = "",
    model: str = FAST_MODEL,
    json_mode: bool = False,
    temperature: float = 0.7,
) -> str:
    """Return raw text from the active provider."""
    full_prompt = f"{prompt}\n\n---\n\nCONTEXT:\n{context}" if context else prompt
    provider = select_provider(_preference_list())
    if provider is None:
        raise RuntimeError(
            "No AI backend available. Set KIMI_API_KEY, VERTEX_CREDENTIALS_PATH, "
            "or GEMINI_API_KEY in .env"
        )
    resolved_model = _resolve_model(model, provider)
    envelope = await provider.generate_json(
        full_prompt, resolved_model, json_mode=json_mode, temperature=temperature
    )
    return envelope["text"]


async def generate_json(
    prompt: str,
    context: str = "",
    model: str = FAST_MODEL,
    schema_hint: Optional[dict] = None,
) -> dict:
    """Force JSON output; parse and return a plain dict.

    Return shape matches the old implementation so all callers in tutor.py
    remain unchanged.
    """
    full_prompt = prompt
    if schema_hint:
        full_prompt += (
            "\n\n---\n\nRespond with valid JSON matching this schema exactly:\n"
            + json.dumps(schema_hint, indent=2)
        )

    raw_text = await generate(full_prompt, context, model, json_mode=True, temperature=0.3)

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as e:
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            raise RuntimeError(
                f"AI backend ({_active_backend()}) returned invalid JSON: {raw_text[:200]}..."
            ) from e


async def health_check() -> bool:
    """Quick round-trip test. Returns True on success."""
    if _active_backend() == "none":
        return False
    try:
        await generate("Say 'ok'", model=FAST_MODEL, temperature=0)
        return True
    except Exception:
        return False
