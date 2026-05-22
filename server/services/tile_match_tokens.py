"""Opaque per-side tile-match tokens — the no-shared-id leak fix.

The legacy tile-match hydration shipped `gb_tile_match` as
`[{id, left, right}]` where BOTH sides of a pair carry the SAME `id`, and the
grade is `left_id == right_id`. That means the client DOM literally encodes
every answer (which left matches which right). The legacy injector's
"side-disjoint" serializer kept the shared id too, so it never fixed this.

The real fix: hand the browser opaque per-side tokens (`L<mac>` / `R<mac>`)
that DON'T reveal pairing, and keep the index→token mapping server-side. The
grader recovers the pair index from each token via HMAC and grades by
`left_index == right_index`.

Contract: the grader route (`server/routes/ai.py`) imports `resolve_tm_pairs`
and `build_token_maps` from here. The canonical pair ORDERING produced by
`resolve_tm_pairs` MUST match `ai.py._resolve_tm_pairs` exactly, because the
token index is that ordinal — drift would mis-map every answer.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import random

_log = logging.getLogger("nets.tile_match_tokens")

# Dev-only fallback. NEVER reached in production: `_resolve_secret` raises if
# `NETS_ENV == "production"` and no real secret is configured, so a prod deploy
# that forgot to set the secret fails loud instead of signing tokens any other
# instance (sharing the literal below) could forge.
_DEV_FALLBACK_SECRET = "nets-tile-match-fallback-secret"


def _resolve_secret() -> bytes:
    """Resolve the HMAC secret for tile-match tokens.

    Order:
      1. ``TILE_MATCH_SECRET`` or ``SECRET_KEY`` env → use it (the real secret).
      2. else if ``NETS_ENV == "production"`` → raise RuntimeError (fail loud —
         a prod instance must never sign with the well-known dev fallback).
      3. else (dev/test) → log a warning and use the dev fallback.

    Called once at module load, so a misconfigured production process refuses to
    start rather than silently degrading token security.
    """
    configured = os.environ.get("TILE_MATCH_SECRET") or os.environ.get("SECRET_KEY")
    if configured:
        return configured.encode()
    if os.getenv("NETS_ENV") == "production":
        raise RuntimeError(
            "TILE_MATCH_SECRET (or SECRET_KEY) must be set in production — "
            "refusing to sign tile-match tokens with the well-known dev fallback."
        )
    _log.warning(
        "TILE_MATCH_SECRET/SECRET_KEY unset; using the dev fallback secret. "
        "This is fine for local/dev/test but MUST NOT happen in production."
    )
    return _DEV_FALLBACK_SECRET.encode()


_SECRET = _resolve_secret()


def _tok(hw_id: str, idx: int, side: str) -> str:
    mac = hmac.new(
        _SECRET, f"{hw_id}:{idx}:{side}".encode(), hashlib.sha256
    ).hexdigest()[:12]
    return f"{side}{mac}"


def left_token(hw_id: str, idx: int) -> str:
    return _tok(hw_id, idx, "L")


def right_token(hw_id: str, idx: int) -> str:
    return _tok(hw_id, idx, "R")


def resolve_tm_pairs(content_json: dict) -> list[dict]:
    """Canonical ordered pair list: gb_tile_match wins, else gb_memory_match shim.

    Returns ``[{'left': str, 'right': str}, ...]`` in the SAME order as
    ``ai.py._resolve_tm_pairs`` (gb_tile_match items in authored order, else
    gb_memory_match ``[[a, b], ...]`` shimmed). Server-only fields
    (``explanation`` and friends) are stripped — only the display sides remain.
    """
    if not isinstance(content_json, dict):
        return []

    items = content_json.get("gb_tile_match")
    pairs: list[dict] = []
    if isinstance(items, list) and items:
        for item in items:
            if isinstance(item, dict):
                src = item
            else:
                # Pydantic model fallback — mirrors _resolve_tm_pairs.
                try:
                    src = dict(item)
                except Exception:
                    continue
            pairs.append({
                "left": str(src.get("left", "")),
                "right": str(src.get("right", "")),
            })
        return pairs

    legacy = content_json.get("gb_memory_match")
    if isinstance(legacy, list):
        for pair in legacy:
            if not (isinstance(pair, (list, tuple)) and len(pair) >= 2):
                continue
            pairs.append({"left": str(pair[0]), "right": str(pair[1])})
    return pairs


def build_token_maps(hw_id: str, num_pairs: int) -> tuple[dict, dict]:
    """Returns ``(lid_map, rid_map)`` = ``{token: pair_index}`` for the grader."""
    lid = {left_token(hw_id, i): i for i in range(num_pairs)}
    rid = {right_token(hw_id, i): i for i in range(num_pairs)}
    return lid, rid


def _seeded_shuffle(items: list, seed: int) -> list:
    """Deterministic Fisher–Yates shuffle (stable per seed)."""
    out = list(items)
    rng = random.Random(seed)
    rng.shuffle(out)
    return out


def build_hydration_tiles(hw_id: str, content_json: dict) -> dict:
    """Student-safe tile-match payload — sides independently shuffled, NO shared id.

    Returns ``{'lefts': [{'lid': str, 'text': str}, ...],
               'rights': [{'rid': str, 'text': str}, ...]}``.

    Each tile carries only an opaque per-side token + its display text. There is
    no field on any tile that links a left to its right, so the client DOM
    cannot recover the pairing. Both columns are shuffled deterministically per
    ``hw_id`` so re-hydration is stable (same student sees the same board).
    """
    pairs = resolve_tm_pairs(content_json)
    lefts = [
        {"lid": left_token(hw_id, i), "text": p.get("left", "")}
        for i, p in enumerate(pairs)
    ]
    rights = [
        {"rid": right_token(hw_id, i), "text": p.get("right", "")}
        for i, p in enumerate(pairs)
    ]
    base_seed = int(hashlib.sha256(hw_id.encode()).hexdigest()[:8], 16)
    return {
        "lefts": _seeded_shuffle(lefts, base_seed),
        # +31 so the two sides shuffle independently (no positional pairing).
        "rights": _seeded_shuffle(rights, base_seed + 31),
    }
