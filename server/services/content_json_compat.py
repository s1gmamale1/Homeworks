"""In-memory ``content_json`` compatibility / normalization layer.

The ``content_json`` blob is the long-lived contract between the builder,
the database, the API, the renderer, and every downstream service. Once a
homework is stored, that blob outlives every server release. This module
exists so server changes never break a homework that was authored months
ago — the runtime gets the shape it expects today, while the stored blob
keeps every legacy key intact.

Design rules
------------
1. **Additive only.** Existing keys are NEVER renamed or deleted. Legacy
   keys remain present after normalization; new keys are filled alongside
   them with safe defaults.
2. **Idempotent.** ``normalize(normalize(x)) == normalize(x)`` for every
   input. Tested explicitly.
3. **In-memory only.** This module is called on the read path (API GET,
   preview render, runtime injection). It does NOT rewrite database rows.
   Bulk DB rewrites belong to ``scripts/migrate_content_json.py``.
4. **Permissive.** Unknown keys, malformed sub-trees, and missing optional
   sections are tolerated — the normalizer never raises on unrecognized
   shapes.

Legacy drift cases handled
--------------------------
Each case below is hit by at least one current production fixture or
stored row. The normalizer surfaces the modern key while leaving the
legacy key in place so authoring tools and offline migrations can still
see the original source.

  L1. ``quotes: [...]`` → ``gate_quote`` envelope absent.
      Default to ``gate_quote = {"mode": "auto"}`` so downstream code
      that reads ``content_json.gate_quote`` gets a non-None envelope.
      ``quotes`` is left untouched (the injector still consumes it as
      the fallback corpus).

  L2. ``reading.text`` instead of ``reading.passage``.
      Older fixtures (e.g. english-g11-b2.json) name the passage body
      ``text``. The injector reads ``passage`` and renders empty otherwise.
      We mirror ``text`` → ``passage`` while keeping ``text``.

  L3. ``boss`` instead of ``boss_questions``.
      Pre-v2 authoring used the bare ``boss`` array; the schema now
      pins ``boss_questions``. We mirror ``boss`` → ``boss_questions``
      so downstream code reading the canonical key sees the same items.

  L4. Boss questions missing stable ``id``.
      Mirrors the write-side ``_normalize_boss_question_ids`` so old DB
      rows that were stored before id normalization get their ids on
      read — without rewriting the stored row.

  L5. Boss questions with ``q`` only, no ``prompt``.
      Both the schema and the injector accept either, but several
      downstream consumers (boss_context_builder, AI gateway prompts)
      read ``prompt`` first. We mirror ``q`` → ``prompt`` so consumers
      stop having to special-case.

  L6. ``boss_meta`` block missing.
      Newer code reads ``boss_meta.boss_type`` for HP / attempts /
      anti-cheat decisions. Default to ``{"boss_type": "sub"}`` so the
      lookup always succeeds.

  L7. ``gb_*`` arrays missing.
      The injector handles this via ``content_json.get(key, [])``, but
      the runtime registry walk (``gbActiveGameOrder``) and downstream
      AI extractors read these keys directly. Default missing arrays to
      ``[]`` so a ``len()`` / iteration never raises.

  L8. Reading checkpoints with ``q`` only, no ``prompt``.
      Mirrors the legacy alias the injector's
      ``_normalize_reading_checkpoint`` resolves at render time so any
      consumer that runs before injection sees a ``prompt``.

  L9. Flashcards with ``def`` only, no ``definition``.
      Pydantic resolves the alias both ways via ``populate_by_name``.
      We additionally surface a plain ``definition`` key on the dict so
      consumers that work on raw dicts (without the Pydantic model) can
      read either name.

The normalizer is intentionally conservative: shape-adapters that the
injector already runs (e.g., ``_rl_adapt_to_template``,
``_serialize_tile_match``, the memory-sprint label remap) are NOT
duplicated here — those convert authoring shape into render shape and
belong at the render boundary. The compat layer fixes shape *gaps*
(missing keys, legacy aliases) that would otherwise leak nulls through
the read path.
"""
from __future__ import annotations

from typing import Any, Mapping


__all__ = [
    "normalize_content_json_for_runtime",
]


# Set of `gb_*` array keys the runtime / AI layer iterate over by name.
# Missing entries default to ``[]`` so callers can use ``len()`` /
# ``for x in cj["gb_..."]`` without a None guard.
_GB_ARRAY_KEYS: tuple[str, ...] = (
    "gb_adaptive_quiz",
    "gb_why_chain",
    "gb_memory_match",
    "gb_puzzle_lock",
    "gb_mystery_box",
    "gb_ttt",
    "gb_sentence_fill",
    "gb_tile_match",
)


def _is_dict(x: Any) -> bool:
    return isinstance(x, dict)


def _is_list(x: Any) -> bool:
    return isinstance(x, list)


def _normalize_gate_quote(cj: dict) -> None:
    """L1 — derive a ``gate_quote`` envelope when only ``quotes`` is present.

    The injector ALREADY does ``content_json.get("gate_quote") or
    content_json.get("quotes")`` for legacy fallback, but AI services
    and downstream consumers read ``cj["gate_quote"]`` directly and
    need the envelope shape regardless of which shape the row was
    authored in.

    Critical detail: a legacy row with ``quotes: ["Eski iqtibos"]`` and
    no ``gate_quote`` MUST keep that custom quote visible after
    normalization. ``quotes_service.migrate_legacy`` already lifts a
    legacy quotes array into the proper ``{mode: "custom", custom: {...}}``
    envelope; we delegate to it so all the legacy-shape rules
    (string array, ``{t, a}`` row array, demo-text filter, etc.) live
    in one place.
    """
    existing = cj.get("gate_quote")
    if _is_dict(existing):
        # Author-supplied envelope wins. Just make sure ``mode`` isn't
        # blank — older builders shipped ``{}`` placeholder envelopes.
        if not existing.get("mode"):
            existing["mode"] = "auto"
        return
    # No authored envelope. Lift the legacy ``quotes`` array (if any)
    # through the canonical migration helper. When ``quotes`` is empty /
    # missing, this returns ``{"mode": "auto"}`` so downstream lookups
    # always see a non-None envelope. ``quotes`` itself is left in place
    # — additive only.
    from .quotes import migrate_legacy as _quotes_migrate_legacy
    cj["gate_quote"] = _quotes_migrate_legacy(cj.get("quotes"))


def _normalize_reading(cj: dict) -> None:
    """L2 — mirror ``reading.text`` → ``reading.passage`` for legacy fixtures.

    L8 — mirror checkpoint ``q`` → ``prompt``.

    Both directions of the alias remain present after normalization. The
    schema's ``ReadingPhase`` retains ``text`` as a permissive optional;
    the injector reads ``passage``. Without this, English G11 fixtures
    render an empty passage frame.
    """
    rd = cj.get("reading")
    if not _is_dict(rd):
        return
    text = rd.get("text")
    passage = rd.get("passage")
    if (passage is None or passage == "") and isinstance(text, str) and text:
        rd["passage"] = text
    cps = rd.get("checkpoints")
    if _is_list(cps):
        for cp in cps:
            if not _is_dict(cp):
                continue
            if (cp.get("prompt") is None or cp.get("prompt") == "") and cp.get("q"):
                cp["prompt"] = cp["q"]


def _normalize_boss(cj: dict) -> None:
    """L3 / L4 / L5 — mirror ``boss`` → ``boss_questions``, stamp ids,
    and mirror ``q`` → ``prompt`` on each question.

    All legacy keys are preserved. ``boss_questions`` becomes the
    canonical surface every downstream consumer can rely on.
    """
    bq = cj.get("boss_questions")
    legacy_boss = cj.get("boss")
    if not _is_list(bq) and _is_list(legacy_boss):
        # L3: lift the legacy ``boss`` array into ``boss_questions`` while
        # keeping ``boss`` in place (additive). We deep-copy each question
        # dict so subsequent id / prompt mirroring on ``boss_questions``
        # does NOT mutate the legacy ``boss`` array — additive means the
        # legacy view stays exactly as the author wrote it.
        cj["boss_questions"] = [
            dict(q) if _is_dict(q) else q for q in legacy_boss
        ]
        bq = cj["boss_questions"]
    if not _is_list(bq):
        return
    # L4: stamp stable ids on questions that lack them (read-side mirror
    # of the write-boundary _normalize_boss_question_ids). Author ids are
    # preserved; only missing/empty/None gets the synthetic fallback.
    # L5: mirror ``q`` → ``prompt`` so downstream prompt-builders never
    # have to fall through alias chains.
    for i, item in enumerate(bq):
        if not _is_dict(item):
            continue
        if not item.get("id"):
            item["id"] = f"bq_{i}"
        if (item.get("prompt") is None or item.get("prompt") == "") and item.get("q"):
            item["prompt"] = item["q"]


def _normalize_boss_meta(cj: dict) -> None:
    """L6 — surface a default ``boss_meta`` when the row predates the schema.

    Newer code paths (boss_context_builder, ai_plan5 boss session start)
    read ``boss_meta.boss_type`` to decide HP / attempts limits. Without
    a default, those lookups crash on legacy rows.
    """
    if cj.get("boss_meta") is None:
        cj["boss_meta"] = {"boss_type": "sub"}


def _normalize_gb_arrays(cj: dict) -> None:
    """L7 — fill in missing ``gb_*`` arrays as empty lists.

    The runtime registry (``gbActiveGameOrder`` in the homework template)
    skips every gb_* key whose array is empty, so adding empty defaults
    does NOT introduce new game-break panels — it just removes the None-
    guard burden from every consumer.
    """
    for key in _GB_ARRAY_KEYS:
        v = cj.get(key)
        if v is None:
            cj[key] = []


def _normalize_flashcards(cj: dict) -> None:
    """L9 — mirror ``def`` → ``definition`` on flashcard items.

    The Pydantic schema resolves the alias both ways, but the injector
    and several consumers operate on raw dicts. Mirroring the alias
    keeps both keys present so neither side has to know about the
    historical naming choice.
    """
    fcs = cj.get("flashcards")
    if not _is_list(fcs):
        return
    for card in fcs:
        if not _is_dict(card):
            continue
        if (card.get("definition") is None or card.get("definition") == "") and card.get("def"):
            card["definition"] = card["def"]


# Public API ---------------------------------------------------------------


def normalize_content_json_for_runtime(content_json: Any) -> dict:
    """Return a copy of ``content_json`` with legacy aliases mirrored
    onto the modern keys, missing optional sections defaulted to safe
    empty values, and boss-question ids stamped.

    Properties:
      * Idempotent — running twice is a no-op vs. running once.
      * Additive — every key in the input dict survives unchanged on
        the output (no key is renamed or removed).
      * Non-mutating — the caller's dict is never modified in place;
        a shallow copy is returned. Sub-dicts/sub-lists are deep-
        traversed only where mutation is needed.
      * Tolerant — non-dict input returns ``{}`` so downstream callers
        always receive a dict.

    This function is the canonical compatibility surface. Wire it into
    every read path that hands content_json to the runtime / template /
    AI layer; do NOT call it on the write path (write-time normalization
    happens at the route boundary via ``_normalize_boss_question_ids``).

    Args:
        content_json: raw blob loaded from the database, a fixture, or
            an HTTP body. May be malformed or partial.

    Returns:
        A normalized dict with the same top-level keys as the input,
        plus any defaults this layer added.
    """
    if not _is_dict(content_json):
        return {}

    # Shallow copy + selective deep-copy of the sub-structures we mutate.
    # Avoids surprise mutations of the caller's row dict (which the FastAPI
    # response model would otherwise see as the canonical body).
    out: dict = dict(content_json)

    # Sub-dicts / sub-lists we may mutate get their own copies first so
    # the caller's source object stays pristine.
    if _is_dict(out.get("reading")):
        out["reading"] = dict(out["reading"])
        if _is_list(out["reading"].get("checkpoints")):
            out["reading"]["checkpoints"] = [
                dict(cp) if _is_dict(cp) else cp
                for cp in out["reading"]["checkpoints"]
            ]
    if _is_dict(out.get("meta")):
        out["meta"] = dict(out["meta"])
    if _is_dict(out.get("gate_quote")):
        out["gate_quote"] = dict(out["gate_quote"])
    if _is_dict(out.get("boss_meta")):
        out["boss_meta"] = dict(out["boss_meta"])
    if _is_list(out.get("boss_questions")):
        out["boss_questions"] = [
            dict(q) if _is_dict(q) else q for q in out["boss_questions"]
        ]
    if _is_list(out.get("boss")) and not _is_list(out.get("boss_questions")):
        # Will be lifted in _normalize_boss; deep-copy first so the legacy
        # ``boss`` array doesn't share question dicts with the new mirror.
        out["boss"] = [
            dict(q) if _is_dict(q) else q for q in out["boss"]
        ]
    if _is_list(out.get("flashcards")):
        out["flashcards"] = [
            dict(c) if _is_dict(c) else c for c in out["flashcards"]
        ]

    # Apply each normalization step. Order matters only for boss: the
    # ``boss`` → ``boss_questions`` lift runs before id stamping so the
    # synthetic ids land on the new canonical array.
    _normalize_gate_quote(out)
    _normalize_reading(out)
    _normalize_boss(out)
    _normalize_boss_meta(out)
    _normalize_gb_arrays(out)
    _normalize_flashcards(out)

    return out


def normalize_homework_row_for_runtime(row: Mapping[str, Any]) -> dict:
    """Convenience wrapper: normalize the ``content_json`` field on a
    homework row dict and return a new row with the rest preserved.

    Used by the API GET / preview / shareable-URL routes so the
    response body / rendered template both see the normalized blob
    without each route having to remember to call the helper itself.
    """
    if not isinstance(row, Mapping):
        return dict(row) if row else {}
    out = dict(row)
    cj = row.get("content_json")
    if cj is not None:
        out["content_json"] = normalize_content_json_for_runtime(cj)
    return out
