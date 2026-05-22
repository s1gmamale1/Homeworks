"""Server-side redaction boundary for the React runtime hydration payload.

`GET /api/runtime/homeworks/{id}` returns the student-safe content_json. This
module strips every answer-bearing field BEFORE the JSON ever reaches the
browser — the delivery-mechanism replacement for the legacy injector's
per-game stripping (which only happened because the injector built the client
JS globals).

Fail-closed design:
  - The entire `answer_spec` subtree is deleted wherever it appears.
  - Every key in ANSWER_BEARING_KEYS is deleted at every nesting depth.
  - Recursion covers dicts + lists, so nested options/checkpoints/steps are
    all scrubbed.

This is intentionally a DENY-list over a sprawling display schema (titles,
prompts, options, story, front/back, etc. must pass through), backed by the
ANSWER_BEARING_KEYS single-source set + a regression test that asserts no
answer substrings survive.
"""

from __future__ import annotations

import copy
import hashlib
import random
from typing import Any

from .redaction_constants import ANSWER_BEARING_KEYS
from .tile_match_tokens import build_hydration_tiles


def build_hydration_ttt(items: Any, hw_id: str = "") -> list[dict]:
    """Build the student-safe gb_ttt wire shape the React Ttt.tsx component reads.

    The component reads ``Array<{id, q, options: string[]}>`` and crashes
    (``Cannot read properties of undefined (reading 'map')``) when ``options`` is
    absent. The raw authored item carries ``{q, correct, distractors[]}`` — but
    the generic scrub strips ``correct`` + ``distractors`` (both ANSWER_BEARING),
    leaving only ``{id, q}`` with no ``options``. This builds the missing display
    shape from the RAW item BEFORE the scrub.

    Mirrors ``injector._serialize_ttt`` exactly so the produced ``item_id`` and
    the options set line up with the legacy render path / answer-key scheme:
      - ``options = [correct, *distractors[:?]]`` shuffled (the correct ANSWER
        TEXT is a visible MCQ option — not a leak; there is NO flag marking which
        one is correct, and grading is server-side text-match in
        ``ai._check_answer_ttt``).
      - ``id`` autoassigns to ``"ttt-{idx+1}"`` (1-based) when absent.
      - Items with empty ``q`` or empty ``correct`` are silently dropped.

    Determinism: the per-item option order is seeded off ``hw_id`` + ``item_id``
    so re-hydration is stable (a student always sees the same board), while two
    homeworks that share an item_id still shuffle differently.
    """
    out: list[dict] = []
    for idx, raw in enumerate(items or []):
        if not isinstance(raw, dict):
            continue
        item_id = (raw.get("id") or "").strip() or f"ttt-{idx + 1}"
        q = (raw.get("q") or "").strip()
        correct = (raw.get("correct") or "").strip()
        if not q or not correct:
            continue
        distractors = [
            d.strip()
            for d in (raw.get("distractors") or [])
            if isinstance(d, str) and d.strip()
        ]
        options = [correct, *distractors]
        # Stable shuffle keyed on hw_id + item_id (independent of any answer key).
        seed = int(
            hashlib.sha256(f"{hw_id}:{item_id}".encode()).hexdigest()[:8], 16
        )
        random.Random(seed).shuffle(options)
        out.append({"id": item_id, "q": q, "options": options})
    return out


def _scrub(node: Any) -> Any:
    """Recursively remove answer-bearing keys from a dict/list tree (in place)."""
    if isinstance(node, dict):
        for key in list(node.keys()):
            if key in ANSWER_BEARING_KEYS:
                del node[key]
                continue
            node[key] = _scrub(node[key])
        return node
    if isinstance(node, list):
        return [_scrub(item) for item in node]
    return node


def redact_for_runtime(content_json: dict | None, hw_id: str = "") -> dict:
    """Return a deep-copied, student-safe view of content_json.

    The input is never mutated (the DB row + builder read path keep the full
    answers). Safe to call on any flow_version — it only removes answer fields,
    leaving all display content intact.

    Tile-match special-case: the legacy `gb_tile_match` shape leaks the pairing
    (both sides share a pair `id`). After the generic scrub we REPLACE it with
    opaque per-side tokens (`tile_match_tokens.build_hydration_tiles`) so the
    DOM can't recover which left matches which right. `gb_memory_match` (the
    legacy shim source) is deleted from the hydration payload entirely. `hw_id`
    seeds the token HMAC + the stable per-side shuffle.
    """
    if not content_json:
        return {}
    safe = copy.deepcopy(content_json)
    safe = _scrub(safe)

    # Tile-match: replace the leaky pair list with opaque per-side tokens.
    if isinstance(safe, dict) and (safe.get("gb_tile_match") or safe.get("gb_memory_match")):
        safe["gb_tile_match"] = build_hydration_tiles(hw_id, content_json)
        safe.pop("gb_memory_match", None)

    # TTT: the scrub stripped `correct` + `distractors`, leaving items with no
    # `options` — which crashes Ttt.tsx (`reading 'map'` on undefined). Rebuild
    # the {id, q, options} display shape from the RAW (pre-scrub) gb_ttt items,
    # mirroring injector._serialize_ttt. The correct ANSWER TEXT rides as one
    # visible MCQ option (standard quiz, server grades by text-match); the
    # correct/distractors KEYS stay deleted, and nothing flags which option is
    # right.
    if isinstance(safe, dict) and isinstance(content_json.get("gb_ttt"), list):
        safe["gb_ttt"] = build_hydration_ttt(content_json["gb_ttt"], hw_id)

    return safe
