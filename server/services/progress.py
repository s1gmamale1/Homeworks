"""
Honest dashboard progress computation.

Earlier, dashboard cards showed a hardcoded 35% for every "draft" homework
because there was no real signal to compute against. The user pushed back:
"it should show real progress no matter which subject — by the content done
and the full requirement, compute and give a real progress line."

This module computes a 0..100 progress value per homework based on what
fraction of the canonical content sections have actually been authored.
The signal varies by homework (different drafts read differently), is
content-driven (not status-driven), and is independent of subject.

Pipeline status overrides the content ratio for the two terminal states:
  * status == "ready" → 100  (build complete by definition)
  * status == "error" → 0    (build failed)

For "draft" and "generating", we count how many of the canonical 9
sections are present and non-empty in `content_json`. "generating" is
capped at 90 so it can't read as fully done before status flips to ready.

The 9 canonical sections were derived by scanning every fixture in
fixtures/ — every fully-built fixture carries exactly this set:
  meta + quotes + panels + flashcards + memory_sprint + real_life +
  at least one gb_* + boss_questions + reflection.

Reading and consolidation are Wave-2 add-ons, optional in fixtures, so
they are not counted in the requirement (counting them would tax every
draft for content the original spec doesn't require).
"""
from __future__ import annotations

import json
from typing import Any


# Game-break list keys — at least ONE must be non-empty for the
# "game_breaks" requirement to count as filled.
_GB_KEYS = (
    "gb_adaptive_quiz",
    "gb_why_chain",
    "gb_memory_match",
    "gb_puzzle_lock",
    "gb_mystery_box",
    "gb_ttt",
    "gb_sentence_fill",
    "gb_tile_match",
    # Error Detection (MARK) — see schemas/content.ErrorDetectionItem.
    "gb_error_detection",
)

# The 9 canonical content milestones a fully-authored homework hits.
CANONICAL_SECTIONS: tuple[str, ...] = (
    "title",          # meta.title or top-level title
    "quotes",         # gate-quote pool
    "panels",         # preview reading panels
    "flashcards",     # vocab cards
    "memory_sprint",  # practice multi-choice
    "real_life",      # scenario story + at least one question
    "game_breaks",    # at least one of the gb_* lists is non-empty
    "boss_questions", # final boss questions
    "reflection",     # closing reflection
)


def _coerce_content(content: Any) -> dict:
    """content_json may be already-parsed (dict) or stringified JSON.
    Anything else → empty dict (treated as 'no sections filled')."""
    if isinstance(content, dict):
        return content
    if isinstance(content, str) and content:
        try:
            parsed = json.loads(content)
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError, ValueError):
            return {}
    return {}


def _has_title(hw_row: dict, content: dict) -> bool:
    title = (hw_row.get("title") or "").strip()
    if title:
        return True
    meta = content.get("meta") if isinstance(content.get("meta"), dict) else {}
    return bool((meta.get("title") or "").strip())


def _nonempty_list(content: dict, key: str) -> bool:
    val = content.get(key)
    return isinstance(val, list) and len(val) > 0


def _has_panels(content: dict) -> bool:
    panels = content.get("panels")
    if not isinstance(panels, list) or not panels:
        return False
    # A panel is meaningful only if it carries pages/blocks of content.
    for p in panels:
        if isinstance(p, dict) and p.get("pages"):
            return True
    return False


def _has_real_life(content: dict) -> bool:
    # New `real_life_challenge` (RLC) case satisfies the section as well.
    rlc = content.get("real_life_challenge")
    if isinstance(rlc, dict):
        steps = rlc.get("steps")
        if isinstance(steps, list) and len(steps) >= 1:
            # any step with a prompt counts as authored
            for s in steps:
                if isinstance(s, dict) and (s.get("prompt") or "").strip():
                    return True
    rl = content.get("real_life")
    if not isinstance(rl, dict):
        return False
    if (rl.get("story") or "").strip():
        return True
    # Or any of the q1..q6 slots populated.
    for i in range(1, 7):
        q = rl.get(f"q{i}")
        if isinstance(q, dict) and (q.get("prompt") or q.get("ans")):
            return True
    return False


def _has_ttt(content: dict) -> bool:
    """Return True if content carries at least one authored TTT item.

    A TTT item is considered authored when it is a dict with a non-empty `q`
    field.  This mirrors the shape check used by `_has_real_life` and
    `_has_final_boss` — the list must exist AND contain at least one meaningful
    entry so that callers can test for TTT presence independently of the
    broader `_has_game_breaks` gate.

    Note: `_has_game_breaks` already counts `gb_ttt` via `_GB_KEYS` — do not
    modify that function.  `_has_ttt` is an explicit, per-mechanic accessor for
    future per-mechanic readiness gates.
    """
    ttt = content.get("gb_ttt")
    if not isinstance(ttt, list) or not ttt:
        return False
    for item in ttt:
        if isinstance(item, dict) and (item.get("q") or "").strip():
            return True
    return False


def _has_memory_palace(content: dict) -> bool:
    """Return True if content carries a non-trivially authored Memory Palace game.

    `gb_memory_palace` is an OBJECT (not a list), so `_nonempty_list` would
    always return False for it.  We check the object directly: it must be a
    non-empty dict whose `palaces` list contains at least one entry with a
    non-empty `key` AND whose `concepts` list contains at least one entry with
    a non-empty `term`.

    Note: `_has_game_breaks` calls this explicitly alongside `_GB_KEYS` so that
    the list-typed and object-typed game-break shapes are handled correctly.
    """
    mp = content.get("gb_memory_palace")
    if not isinstance(mp, dict) or not mp:
        return False
    palaces = mp.get("palaces")
    if not isinstance(palaces, list) or not palaces:
        return False
    has_valid_palace = any(
        isinstance(p, dict) and (p.get("key") or "").strip()
        for p in palaces
    )
    if not has_valid_palace:
        return False
    concepts = mp.get("concepts")
    if not isinstance(concepts, list) or not concepts:
        return False
    return any(
        isinstance(c, dict) and (c.get("term") or "").strip()
        for c in concepts
    )


def _has_game_breaks(content: dict) -> bool:
    return any(_nonempty_list(content, k) for k in _GB_KEYS) or _has_memory_palace(content)


def _has_reflection(content: dict) -> bool:
    refl = content.get("reflection")
    if not isinstance(refl, dict):
        return False
    return bool(
        (refl.get("summary") or "").strip()
        or (refl.get("question") or "").strip()
        or (refl.get("closing") or "").strip()
    )


def filled_sections(hw_row: dict) -> list[str]:
    """Return the subset of CANONICAL_SECTIONS that are filled for this hw.

    Used by both compute_progress() and the dashboard tooltip / debugger so
    we can name *which* sections still need authoring."""
    content = _coerce_content(hw_row.get("content_json"))
    out: list[str] = []
    if _has_title(hw_row, content):                       out.append("title")
    if _nonempty_list(content, "quotes"):                 out.append("quotes")
    if _has_panels(content):                              out.append("panels")
    if _nonempty_list(content, "flashcards"):             out.append("flashcards")
    if _nonempty_list(content, "memory_sprint"):          out.append("memory_sprint")
    if _has_real_life(content):                           out.append("real_life")
    if _has_game_breaks(content):                         out.append("game_breaks")
    if _nonempty_list(content, "boss_questions"):         out.append("boss_questions")
    if _has_reflection(content):                          out.append("reflection")
    return out


def compute_progress(hw_row: dict) -> int:
    """Honest 0..100 progress for the dashboard card progress bar.

    `hw_row` must be a dict with at least `status` and (when the row
    came from a query that included it) `content_json`. Missing
    content_json → progress is computed against zero filled sections.

    Status overrides:
      * "ready"      → 100
      * "error"      → 0
      * "generating" → cap at 90 (still building)
      * other        → fraction of canonical sections * 100
    """
    if not isinstance(hw_row, dict):
        return 0

    status = hw_row.get("status")
    if status == "error":
        return 0
    if status == "ready":
        return 100

    filled = filled_sections(hw_row)
    pct = round(len(filled) / len(CANONICAL_SECTIONS) * 100)

    # generating is transient — never let content-fill alone read as fully
    # done. Status will flip to ready at the actual end of the build.
    if status == "generating":
        pct = min(pct, 90)

    # Clamp defensively.
    return max(0, min(100, pct))
