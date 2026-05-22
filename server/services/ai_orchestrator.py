"""
AI client shim — thin wrapper over the provider registry.

Public API:
  - generate_json(prompt, context, model, schema_hint) -> dict
  - generate(prompt, context, model, json_mode, temperature) -> str
  - health_check() -> bool
  - ACTIVE_BACKEND: str   ("kimi" | "none")
  - FAST_MODEL, PRO_MODEL: str   (Kimi model identifiers)

All routing logic lives in server/services/ai_providers/.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Iterator, Optional

# Provider registry — concrete providers self-register on import
from .ai_providers import (  # noqa: F401
    AIProvider,
    available_providers,
    get_provider,
    select_provider,
)
# Server-side log channel for provider failures. Errors are recorded with full
# detail here while the public RuntimeError stays generic.
_log = logging.getLogger("nets.ai")


# ── Model name constants — Kimi's actual model identifiers ──────────────────
# Read from config so KIMI_MODEL_FAST / KIMI_MODEL_PRO env overrides flow through.
from ..config import KIMI_MODEL_FAST, KIMI_MODEL_PRO, KIMI_MODEL_VISION  # noqa: E402

FAST_MODEL: str = KIMI_MODEL_FAST  # default "moonshot-v1-32k"
PRO_MODEL: str = KIMI_MODEL_PRO    # default "moonshot-v1-128k"
VISION_MODEL: str = KIMI_MODEL_VISION  # default "kimi-k2.6"

# ── Preference parsing ────────────────────────────────────────────────────────
_DEFAULT_PREFERENCE = "kimi"

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


def _iter_available_providers(preference: list[str]) -> Iterator[AIProvider]:
    """Yield every available provider in preference order (not just the first).

    `select_provider` returns only the top-of-list provider, which is fine for
    "what's our primary backend?" reporting. The runtime fallback chain needs
    to walk the rest of the list when the primary fails, so we iterate here.
    """
    for name in preference:
        try:
            provider = get_provider(name)
        except ValueError:
            continue
        if provider.is_available():
            yield provider


def _iter_vision_providers(preference: list[str]) -> Iterator[AIProvider]:
    """Same as _iter_available_providers but only yields vision-capable providers."""
    for provider in _iter_available_providers(preference):
        if provider.supports_vision:
            yield provider


async def generate_vision(
    prompt: str,
    image_b64: str,
    mime: str = "image/jpeg",
    model: Optional[str] = None,
    json_mode: bool = True,
    temperature: float = 0.1,
) -> dict:
    """Walk vision-capable providers; return first non-error response.

    Returns a normalised envelope::

        { "text": str, "raw": dict, "provider": str, "model": str }

    Raises ``RuntimeError`` when no vision-capable provider is available or
    all available ones fail.
    """
    preference = os.environ.get("AI_BACKEND_PREFERENCE", _DEFAULT_PREFERENCE).split(",")
    last_error: Optional[BaseException] = None
    for provider in _iter_vision_providers([p.strip() for p in preference]):
        try:
            return await provider.generate_vision_json(  # type: ignore[attr-defined]
                prompt,
                image_b64,
                mime,
                model=model,
                temperature=temperature,
                json_mode=json_mode,
            )
        except Exception as exc:
            last_error = exc
            _log.warning(
                "Vision provider %s failed (%s); trying next",
                provider.name,
                exc.__class__.__name__,
                exc_info=True,
            )
            continue
    raise RuntimeError(f"No vision provider available; last error: {last_error}")


def __getattr__(name: str):  # noqa: N807
    """Module-level __getattr__ so `gemini.ACTIVE_BACKEND` stays dynamic."""
    if name == "ACTIVE_BACKEND":
        return _active_backend()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# ── Prompt input sanitization (PR 1 — AI grading bloat fix) ──────────────────
#
# Regression guard: HW-20260429-019 had 1.5MB of inline base64 PNG embedded in
# its boss_question text. The unsanitized payload blew past every provider's
# input cap → 500 silent-fail → "always wrong" UX. Helper centralises the strip
# + size guard so all 5 LLM call sites share one code path.


class PromptTooLargeError(RuntimeError):
    """Raised when a prompt payload exceeds the configured size cap.

    Carries the actual size + cap so callers can log exact numbers.
    """

    def __init__(self, size: int, cap: int):
        self.size = size
        self.cap = cap
        super().__init__(
            f"Prompt payload {size:,} chars exceeds cap {cap:,}; "
            "likely contains embedded media that should be stripped at "
            "authoring time."
        )


# <img …  src=data:…> — full tag, even if attributes wrap multiple lines
_IMG_DATA_URL_RE = re.compile(
    r"<img\b[^>]*\bsrc\s*=\s*[\"']?data:[^\"'>]+[\"']?[^>]*/?\s*>",
    re.IGNORECASE | re.DOTALL,
)
# <svg …>…</svg> — entire block (LLM doesn't need the geometry)
_SVG_BLOCK_RE = re.compile(r"<svg\b[^>]*>.*?</svg>", re.IGNORECASE | re.DOTALL)
# Bare data:image/...;base64,… URL not wrapped in an <img> tag
_INLINE_DATA_URL_RE = re.compile(
    r"data:[a-z]+/[a-z0-9+\-.]+;base64,[A-Za-z0-9+/=]+",
    re.IGNORECASE,
)

_PER_FIELD_CHAR_CAP = 5000
_PROMPT_INPUT_CHAR_CAP = 50000


def _strip_inline_media(text: str) -> str:
    """Remove inline ``<img data:…>``, ``<svg>…</svg>``, bare ``data:`` URLs.

    Replaces stripped content with ``[media]`` so structure is preserved but
    the LLM context isn't polluted.
    """
    if not isinstance(text, str):
        return text
    text = _IMG_DATA_URL_RE.sub("[media]", text)
    text = _SVG_BLOCK_RE.sub("[media]", text)
    text = _INLINE_DATA_URL_RE.sub("[media]", text)
    return text


def _sanitize_payload(obj: Any, max_per_field: int = _PER_FIELD_CHAR_CAP) -> Any:
    """Recursively sanitize string fields in a payload.

    - Strips inline-media bloat
    - Caps individual string fields at ``max_per_field`` chars (truncate +
      mark how many chars were dropped so the LLM sees the boundary)
    """
    if isinstance(obj, str):
        cleaned = _strip_inline_media(obj)
        if len(cleaned) > max_per_field:
            dropped = len(cleaned) - max_per_field
            cleaned = cleaned[:max_per_field] + f"\n... [truncated, {dropped} chars omitted]"
        return cleaned
    if isinstance(obj, dict):
        return {k: _sanitize_payload(v, max_per_field) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_payload(item, max_per_field) for item in obj]
    return obj  # numbers, bools, None — pass through


def build_input_section(payload: dict, max_chars: int = _PROMPT_INPUT_CHAR_CAP) -> str:
    """Sanitize + serialize a payload to the ``---\\n\\nINPUT:\\n{json}`` template.

    Raises ``PromptTooLargeError`` when the serialized result exceeds
    ``max_chars``. Callers should catch and fall back to a synthetic response
    rather than letting the exception bubble to the runtime as a 500.
    """
    sanitized = _sanitize_payload(payload)
    body = json.dumps(sanitized, ensure_ascii=False, indent=2)
    if len(body) > max_chars:
        raise PromptTooLargeError(size=len(body), cap=max_chars)
    return f"---\n\nINPUT:\n{body}"


# ── Public API ────────────────────────────────────────────────────────────────

async def generate(
    prompt: str,
    context: str = "",
    model: str = FAST_MODEL,
    json_mode: bool = False,
    temperature: float = 0.7,
    *,
    tier: Optional[str] = None,
    preference_override: Optional[list[str]] = None,
) -> str:
    """Return raw text from the first provider in the preference list that
    succeeds.

    Walks every available provider (not just the first). On any exception
    from a provider — network 5xx, auth failure, parse error, timeout — logs
    server-side and falls through to the next provider. Only raises
    ``RuntimeError`` when *all* available providers have failed, OR when no
    provider is available at all.

    The previous behaviour stopped at the first provider and surfaced the
    raw exception; that meant a single Vertex 5xx took the tutor down even
    when Kimi and the Gemini API were healthy. The chain advertised in
    `STATE.md` (Vertex → Gemini → Kimi → stock) is now actually wired.

    Tier-based per-provider model resolution
    ----------------------------------------
    ``tier`` (``"pro"`` or ``"fast"``) lets the gateway route across providers
    that use different model identifiers. When ``tier`` is set, each provider
    in the fallback walk picks its OWN model name from ``provider.pro_model``
    / ``provider.fast_model`` — so an ``openai → kimi`` chain swaps model
    strings as it walks instead of trying to send ``gpt-4o-mini`` to Moonshot
    or vice versa.

    Backward compatible: callers that pass ``model=`` (the old API) keep
    working unchanged. ``model=`` takes precedence over ``tier=``.

    ``preference_override`` lets a per-call preference list bypass the global
    ``AI_BACKEND_PREFERENCE`` env. Used by ``ai_gateway.TASK_PROVIDER_PREFERENCE``
    so boss tasks can route ``openai → kimi`` without changing the global
    default for tutor / answer-check / reflection.
    """
    full_prompt = f"{prompt}\n\n---\n\nCONTEXT:\n{context}" if context else prompt
    # Per-call preference takes precedence over env. Falls back to AI_BACKEND_PREFERENCE.
    preference = preference_override or _preference_list()
    available = list(_iter_available_providers(preference))
    if not available:
        raise RuntimeError(
            "No AI backend available. Set KIMI_API_KEY in .env."
        )

    # Detect whether the caller is using tier-based resolution. The legacy
    # default `model=FAST_MODEL` would be indistinguishable from an explicit
    # "fast-tier Kimi" request, so we only switch to tier mode when the
    # caller explicitly passes a `tier` kwarg.
    use_tier_mode = tier is not None

    tried: list[str] = []
    last_exc: Optional[BaseException] = None
    for provider in available:
        # In tier mode, ask each provider for its OWN model name so the
        # fallback walk can cross provider boundaries cleanly.
        if use_tier_mode:
            try:
                effective_model = (
                    provider.pro_model if tier == "pro" else provider.fast_model
                )
            except NotImplementedError as exc:
                # Provider doesn't expose tier models — skip it; let the walk
                # find one that does. Logged for ops visibility.
                _log.warning(
                    "AI provider %s missing %s_model; skipping in tier-mode walk",
                    provider.name, tier,
                )
                tried.append(provider.name)
                last_exc = exc
                continue
        else:
            effective_model = model
        try:
            envelope = await provider.generate_json(
                full_prompt,
                effective_model,
                json_mode=json_mode,
                temperature=temperature,
            )
            return envelope["text"]
        except Exception as exc:
            tried.append(provider.name)
            last_exc = exc
            _log.warning(
                "AI provider %s failed (%s); falling through to next provider",
                provider.name,
                exc.__class__.__name__,
                exc_info=True,
            )
            continue

    raise RuntimeError(
        f"All AI providers failed (tried: {', '.join(tried) or 'none'})"
    ) from last_exc


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
