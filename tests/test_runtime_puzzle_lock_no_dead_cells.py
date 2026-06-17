"""Regression for PL-01: the old 15-puzzle render padded a 5-item input into a
3×3 grid, producing 4 dead 'null' cells that students could not interact with
and that broke the win condition.

All three tests here are pure static assertions — no server, no Node required.
They pin the render contract: exactly N cards for N items, no empty padding.

Real-data anchor: HW-20260505-005 (geometriya G8, 5 PL items) was the bug
report; HW-20260505-009 (algebra, 5 PL items) confirmed the same pattern.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
_JS_PATH = ROOT / "server" / "template" / "js" / "perfect_homework.js"
_CSS_PATH = ROOT / "server" / "template" / "static" / "css" / "perfect_homework.css"
_HTML_PATH = ROOT / "server" / "template" / "perfect_homework.html"
RUNTIME = _HTML_PATH.read_text(encoding="utf-8") + "\n" + _JS_PATH.read_text(encoding="utf-8") + "\n" + _CSS_PATH.read_text(encoding="utf-8")


def _read() -> str:
    return RUNTIME


def _extract_gb_pl_render(html: str) -> str:
    """Return the gbPLRender function body."""
    m = re.search(
        r"function gbPLRender\(\)\s*\{(?P<body>.*?)\n\s{8}\}",
        html,
        re.DOTALL,
    )
    assert m, "gbPLRender function not found in perfect_homework.html"
    return m.group("body")


def _extract_gb_init_pl(html: str) -> str:
    """Return the gbInitPL function body."""
    m = re.search(
        r"function gbInitPL\(\)\s*\{(?P<body>.*?)\n\s{8}\}",
        html,
        re.DOTALL,
    )
    assert m, "gbInitPL function not found in perfect_homework.html"
    return m.group("body")


# ---------------------------------------------------------------------------
# PL-01 regression: render iterates tiles, not cells
# ---------------------------------------------------------------------------

def test_pl_render_emits_one_card_per_tile():
    """gbPLRender's forEach must iterate pl.tiles, not pl.cells.

    The old sliding-tile render looped over pl.cells (a padded N×N flat array
    including null entries for the empty slot). The new render loops over
    pl.tiles (the raw input list), so N items produce exactly N cards.
    """
    html = _read()
    body = _extract_gb_pl_render(html)

    # The loop must be over pl.tiles
    assert "pl.tiles.forEach" in body, (
        "PL-01 regression: gbPLRender does not iterate pl.tiles — "
        "make sure the loop is 'pl.tiles.forEach(...)' not pl.cells"
    )

    # There must be no branch that appends an 'empty' placeholder card
    # (the old code did: if (cell === null) { card.classList.add('empty') })
    assert "classList.add('empty')" not in body, (
        "PL-01 regression: gbPLRender still adds 'empty' class — "
        "this was the dead-cell padding artefact from the 15-puzzle era"
    )
    assert 'classList.add("empty")' not in body, (
        "PL-01 regression: gbPLRender still adds 'empty' class (double-quote form)"
    )

    # No null-cell guard branch
    assert "cell === null" not in body, (
        "PL-01 regression: gbPLRender still branches on 'cell === null' — "
        "null cells were only a concept in the padded grid; linear stepper has none"
    )


def test_pl_render_drops_empty_cell_class():
    """The JS render must not assign the 'empty' class anywhere in the template's
    PL code paths.

    A residual `.gb-pl-cell.empty { display: none }` CSS rule is permitted as
    a safety net for old cached HTML, but the JS must never generate it for
    new renders — otherwise dead invisible cells would silently appear.
    """
    html = _read()
    render_body = _extract_gb_pl_render(html)
    init_body = _extract_gb_init_pl(html)

    for body, label in ((render_body, "gbPLRender"), (init_body, "gbInitPL")):
        assert "classList.add('empty')" not in body, (
            f"PL-01 regression: {label} assigns classList 'empty' — "
            "JS must never generate dead empty cells"
        )
        assert 'classList.add("empty")' not in body, (
            f"PL-01 regression: {label} assigns classList 'empty' (double-quote form)"
        )


def test_pl_init_does_not_pad_with_null():
    """gbInitPL must not pad the tiles array with null to fill a grid shape.

    The old init called: pl.cells = new Array(pl.size * pl.size).fill(null)
    then overwrote positions with tile objects, leaving null in the empty slot.
    The new init builds pl.tiles directly from the input array — no padding.
    """
    html = _read()
    body = _extract_gb_init_pl(html)

    # Remove single-line JS comments so legacy-note comments don't false-positive
    body_no_comments = re.sub(r"//[^\n]*", "", body)

    assert "new Array(pl.size * pl.size).fill(null)" not in body_no_comments, (
        "PL-01 regression: gbInitPL still pads with null via pl.size * pl.size — "
        "this is the old sliding-tile grid-fill pattern"
    )

    # More general: no fill(null) anywhere in init (the only legitimate fill(null)
    # in the template is for Mystery Box and Map Pin, not PL)
    assert ".fill(null)" not in body_no_comments, (
        "PL-01 regression: gbInitPL still calls .fill(null) — "
        "linear stepper builds pl.tiles directly without null padding"
    )
