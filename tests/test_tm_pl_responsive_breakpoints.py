"""Regression tests for Tile Match + Puzzle Lock responsive breakpoints.

User report (2026-05-06): in the builder preview iframe (~360–440px wide),
both the Tile Match panel and the Puzzle Lock (qulf ochish) panel were
non-adaptive — the 3-stat grid, sticky topbar, and hero card overlapped
unfinished content; Puzzle Lock had **no** responsive rules at all so
its cells, question box, and win banner all stuck to desktop padding.

Pre-fix:
- Tile Match had only `@media (max-width: 370px)` — too narrow to cover
  the iframe range, so widths between 371–480px got the full desktop
  layout crammed into a phone-sized iframe.
- Puzzle Lock had zero `@media` rules — desktop-only forever.

Fix:
- Tile Match: new `@media (max-width: 480px)` tier covers the builder
  iframe range. The existing 370px tier kept (and tightened) for true
  mobile portrait.
- Puzzle Lock: new `@media (max-width: 480px)` + `(max-width: 370px)`
  tiers — first set of responsive rules ever for this panel.

These tests pin the breakpoint contract so a future "let me clean up
this CSS" PR can't re-open the leak.
"""

from __future__ import annotations

import re
from pathlib import Path

_JS_PATH = Path(__file__).resolve().parent.parent / "server" / "template" / "js" / "perfect_homework.js"
_CSS_PATH = Path(__file__).resolve().parent.parent / "server" / "template" / "static" / "css" / "perfect_homework.css"
_HTML_PATH = Path(__file__).resolve().parent.parent / "server" / "template" / "perfect_homework.html"
TEMPLATE = _HTML_PATH.read_text(encoding="utf-8") + "\n" + _JS_PATH.read_text(encoding="utf-8") + "\n" + _CSS_PATH.read_text(encoding="utf-8")


def _find_media_blocks(template: str, query: str) -> list[str]:
    """Return ALL bodies of `@media (...) { ... }` matching `query`.
    Brace-balanced. The template can contain multiple @media blocks
    with the same query (e.g. one for Tile Match, one for Puzzle Lock).
    """
    needle = f"@media {query} {{"
    blocks: list[str] = []
    pos = 0
    while True:
        idx = template.find(needle, pos)
        if idx < 0:
            return blocks
        depth = 0
        started = False
        end = -1
        for i in range(idx + len(needle) - 1, len(template)):
            ch = template[i]
            if ch == "{":
                depth += 1
                started = True
            elif ch == "}":
                depth -= 1
                if started and depth == 0:
                    end = i + 1
                    break
        if end < 0:
            return blocks
        blocks.append(template[idx:end])
        pos = end


def _find_media_block(template: str, query: str) -> str:
    """Concatenated bodies of every `@media query` block — convenient for
    `... in block` containment checks across all matching blocks."""
    return "\n".join(_find_media_blocks(template, query))


# ---------------------------------------------------------------------------
# Tile Match — 480px tier must exist and cover the builder iframe range.
# ---------------------------------------------------------------------------


def test_tile_match_has_480px_breakpoint() -> None:
    """The 480px tier must contain Tile Match selectors so the builder
    iframe (~360–440px) gets the responsive layout."""
    block = _find_media_block(TEMPLATE, "(max-width: 480px)")
    assert block, "no @media (max-width: 480px) block found in template"
    assert "#gb-panel-tm" in block or ".gb-tm-" in block, (
        "the 480px @media block does not target Tile Match selectors. "
        "The builder preview iframe at ~360–440px wide will use the "
        "desktop layout and the 3-stat grid + sticky topbar will overlap."
    )


def test_tile_match_480px_drops_stats_to_two_columns() -> None:
    """At <=480px the 3-stat row must collapse to 2 columns + a spanning
    last cell — matches the 370px rule but at the iframe-relevant width."""
    block = _find_media_block(TEMPLATE, "(max-width: 480px)")
    assert ".gb-tm-stats" in block, "gb-tm-stats not addressed in 480px tier"
    # Look for either 'grid-template-columns: 1fr 1fr' or any 2-col pattern
    # near the .gb-tm-stats selector.
    stats_idx = block.find(".gb-tm-stats")
    nearby = block[stats_idx : stats_idx + 400]
    assert "1fr 1fr" in nearby, (
        "gb-tm-stats in 480px tier doesn't switch to 2 columns. The "
        "third stat card will wrap awkwardly under the first two and "
        "the user sees uneven heights."
    )
    assert ".gb-tm-stat:last-child" in block and "grid-column" in block, (
        "the 480px tier doesn't span the third stat card across the row "
        "(grid-column rule missing). Without it the third card sits "
        "alone on the right with empty space next to it."
    )


def test_tile_match_370px_breakpoint_still_present() -> None:
    """The original 370px tier must still exist for true mobile portrait —
    it tightens further than the 480px tier."""
    block = _find_media_block(TEMPLATE, "(max-width: 370px)")
    assert block, "the 370px breakpoint was removed — true mobile portrait will regress"
    # At least one Tile Match selector must remain in the 370px block.
    assert "#gb-panel-tm" in block or ".gb-tm-" in block, (
        "the 370px tier no longer targets Tile Match. Mobile portrait "
        "(<=370px wide phones) will fall back to the 480px tier which "
        "is too loose for that width."
    )


# ---------------------------------------------------------------------------
# Puzzle Lock — must now have at least one responsive tier (it had zero).
# ---------------------------------------------------------------------------


def test_puzzle_lock_has_480px_breakpoint() -> None:
    """Puzzle Lock had zero @media rules pre-fix. The 480px tier must
    address at least one .gb-pl- selector."""
    block = _find_media_block(TEMPLATE, "(max-width: 480px)")
    assert block, "no @media (max-width: 480px) block found"
    assert ".gb-pl-" in block, (
        "the 480px @media block does not target Puzzle Lock (.gb-pl-) "
        "selectors. The builder preview iframe will render the qulf "
        "ochish grid with desktop padding/font-size and cells will "
        "overflow / overlap the question box."
    )


def test_puzzle_lock_480px_tightens_grid_padding() -> None:
    """At <=480px the grid padding/gap and cell padding must shrink so
    the 3×N grid actually fits in the iframe."""
    block = _find_media_block(TEMPLATE, "(max-width: 480px)")
    cell_idx = block.find(".gb-pl-cell")
    assert cell_idx >= 0, "gb-pl-cell not addressed in 480px tier"
    cell_block = block[cell_idx : cell_idx + 300]
    # The cell padding/font-size must be smaller than the desktop value.
    # Desktop is `padding: 6px; font-size: 13px`. Any reduction is fine
    # as long as the rule exists.
    assert "padding" in cell_block, (
        "gb-pl-cell padding is not adjusted at <=480px — desktop 6px "
        "padding leaves text overlapping the cell border in narrow widths"
    )
    assert "font-size" in cell_block, (
        "gb-pl-cell font-size is not adjusted at <=480px — 13px text "
        "wraps inside small cells and overflows the aspect-ratio box"
    )


def test_puzzle_lock_480px_tightens_question_box() -> None:
    """The question box (`gb-pl-question-box`) must also shrink so it
    doesn't stack tall and push the win banner / button off-screen."""
    block = _find_media_block(TEMPLATE, "(max-width: 480px)")
    qbox_idx = block.find(".gb-pl-question-box")
    assert qbox_idx >= 0, (
        ".gb-pl-question-box not addressed in 480px tier. Desktop padding "
        "(14px 16px) makes the box tall enough to push the win banner "
        "below the fold in the iframe."
    )


def test_puzzle_lock_has_370px_breakpoint_for_mobile() -> None:
    """For true mobile portrait, an even tighter tier exists for cells
    (the smallest iframes still need to fit a 4×2 or 5×3 grid)."""
    block = _find_media_block(TEMPLATE, "(max-width: 370px)")
    assert block, "no @media (max-width: 370px) block found"
    # Puzzle Lock cells must be addressed here at least.
    assert ".gb-pl-cell" in block or ".gb-pl-grid" in block, (
        "the 370px tier doesn't tighten Puzzle Lock cells/grid further. "
        "On a 360px-wide phone the 480px tier is still too loose."
    )


# ---------------------------------------------------------------------------
# Sanity guards on the original layout (so the responsive tier doesn't
# accidentally remove the desktop selectors it overrides).
# ---------------------------------------------------------------------------


def test_tile_match_desktop_layout_keeps_two_column_stats() -> None:
    """Outside any @media block, .gb-tm-stats must declare a 2-column grid
    for desktop. The timer card was removed in PR #178 follow-up (the timer
    was server-tick-only, not real-time, so it misled users); the remaining
    matched + wrong stats fill a 2-column row.

    The responsive tier may override for very narrow widths; the base rule
    must stay 2 columns post-removal."""
    base_idx = TEMPLATE.find(".gb-tm-stats {")
    assert base_idx >= 0, ".gb-tm-stats base rule missing entirely"
    base_block = TEMPLATE[base_idx : base_idx + 600]
    assert "1fr 1fr" in base_block and "1fr 1fr 1fr" not in base_block, (
        "base .gb-tm-stats rule should declare a 2-column grid (matched + wrong) "
        "after the fake-realtime timer was removed. Found: "
        + base_block.split("}")[0]
    )


def test_puzzle_lock_desktop_grid_max_width_preserved() -> None:
    """The base .gb-pl-grid rule must keep max-width cap so the grid
    doesn't stretch past readable width on wide screens. (Updated to
    max-width: 560px as part of the linear-stepper rewrite, PR 2026-05-07.)"""
    base_rule_idx = TEMPLATE.find(".gb-pl-grid {")
    assert base_rule_idx >= 0
    base_rule = TEMPLATE[base_rule_idx : base_rule_idx + 400]
    assert "max-width: 560px" in base_rule, (
        "base .gb-pl-grid lost its max-width: 560px cap — on wide "
        "viewports the puzzle grid will stretch full-width and cells "
        "become too large."
    )
