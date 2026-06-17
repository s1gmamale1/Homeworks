"""Static-template regression for PR A 2026-05-07: Puzzle Lock linear-stepper.

Pins the structure introduced when the sliding-tile grid was replaced with a
vertical solve-stepper. All assertions are content-only (no server, no Node)
so this file always runs in CI.

Real-data anchor: HW-20260505-005 (geometriya G8) and HW-20260505-009
(algebra) both carry 5-item GB_PUZZLE_LOCK arrays — the render contract
below must hold for any N in 1..15.
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


# ---------------------------------------------------------------------------
# CSS layout assertions
# ---------------------------------------------------------------------------

def test_pl_grid_no_aspect_ratio():
    """PL-03 fix: .gb-pl-cell must not contain aspect-ratio — it was clipping
    multi-line step content inside the old square tile geometry."""
    html = _read()
    m = re.search(r"\.gb-pl-cell\s*\{(?P<body>[^}]*)\}", html)
    assert m, ".gb-pl-cell { } rule not found"
    body = m.group("body")
    # Strip CSS block comments (/* … */) before checking — the rule body
    # intentionally includes a comment explaining aspect-ratio was removed;
    # we must not count that comment text as a live declaration.
    body_stripped = re.sub(r"/\*.*?\*/", "", body, flags=re.DOTALL)
    assert "aspect-ratio:" not in body_stripped, (
        "PL-03 regression: .gb-pl-cell still has aspect-ratio declaration — "
        "removes vertical growth and clips long step text"
    )


def test_pl_grid_uses_flex_column():
    """The grid container uses flex-direction: column to stack steps vertically."""
    html = _read()
    m = re.search(r"\.gb-pl-grid\s*\{(?P<body>[^}]*)\}", html)
    assert m, ".gb-pl-grid { } rule not found"
    body = m.group("body")
    assert re.search(r"flex-direction\s*:\s*column", body), (
        ".gb-pl-grid must contain 'flex-direction: column' for linear stacking"
    )


def test_pl_cell_has_step_num_pseudo():
    """Step-number circle badge is generated via ::before + data-step-num."""
    html = _read()
    m = re.search(
        r"\.gb-pl-cell::before\s*\{(?P<body>.*?)\}",
        html,
        re.DOTALL,
    )
    assert m, ".gb-pl-cell::before rule not found"
    body = m.group("body")
    assert re.search(r"content\s*:\s*attr\s*\(\s*data-step-num\s*\)", body), (
        ".gb-pl-cell::before must use content: attr(data-step-num) to render the step number"
    )


def test_pl_cell_states_locked_active_solved():
    """All three state CSS selectors must exist in the template."""
    html = _read()
    for selector in (".gb-pl-cell.locked", ".gb-pl-cell.active", ".gb-pl-cell.solved"):
        assert selector in html, (
            f"CSS selector '{selector}' missing from template — "
            "gbPLRender assigns exactly one of these three classes"
        )


def test_pl_locked_glyph_is_lock_not_check():
    """PL cell glyphs: locked steps show 🔒 (U+1F512), solved steps show ✓ (U+2713)."""
    html = _read()
    # locked::after glyph
    m_locked = re.search(
        r"\.gb-pl-cell\.locked::after\s*\{(?P<body>.*?)\}",
        html,
        re.DOTALL,
    )
    assert m_locked, ".gb-pl-cell.locked::after rule not found"
    assert re.search(r"\\01[Ff]512", m_locked.group("body")), (
        ".gb-pl-cell.locked::after must use codepoint \\01F512 (🔒) "
        "— do not reuse the ✓ check glyph on future/locked steps"
    )

    # solved::after glyph — may live in a shared selector block
    m_solved = re.search(
        r"\.gb-pl-cell\.solved::after\s*\{(?P<body>.*?)\}",
        html,
        re.DOTALL,
    )
    assert m_solved, ".gb-pl-cell.solved::after rule not found"
    assert re.search(r"\\2713", m_solved.group("body")), (
        ".gb-pl-cell.solved::after must use codepoint \\2713 (✓)"
    )


# ---------------------------------------------------------------------------
# JS: init model
# ---------------------------------------------------------------------------

def test_pl_init_uses_currentStep_model():
    """gbInitPL must initialise the linear-stepper state, not the old sliding grid."""
    html = _read()
    m = re.search(
        r"function gbInitPL\(\)\s*\{(?P<body>.*?)\n\s{8}\}",
        html,
        re.DOTALL,
    )
    assert m, "gbInitPL function not found"
    body = m.group("body")

    assert "pl.currentStep = 0" in body, (
        "gbInitPL must set pl.currentStep = 0 for the linear stepper"
    )
    assert "pl.emptyIdx = pl.size * pl.size - 1" not in body, (
        "gbInitPL still contains the sliding-tile emptyIdx initialisation — "
        "this is a vestigial artefact of the old 15-puzzle mechanic"
    )


# ---------------------------------------------------------------------------
# JS: render — no per-cell click handler
# ---------------------------------------------------------------------------

def test_pl_render_no_click_handler_per_cell():
    """gbPLRender must not attach per-cell click listeners — the CTA drives all input."""
    html = _read()
    m = re.search(
        r"function gbPLRender\(\)\s*\{(?P<body>.*?)\n\s{8}\}",
        html,
        re.DOTALL,
    )
    assert m, "gbPLRender function not found"
    body = m.group("body")

    assert "gbPLClickTile" not in body, (
        "gbPLRender still references gbPLClickTile — "
        "per-cell click handlers are obsolete in the linear stepper"
    )
    assert "addEventListener('click'" not in body, (
        "gbPLRender still attaches 'click' event listeners per cell — "
        "the CTA button drives all input in the linear stepper"
    )


# ---------------------------------------------------------------------------
# JS: dispatch — no pl.selected gate
# ---------------------------------------------------------------------------

def test_pl_dispatch_no_pl_selected_gate():
    """gbHandleAction subGame===3 branch must not gate on pl.selected."""
    html = _read()
    # Extract just the subGame===3 block
    m = re.search(
        r"if \(gbState\.subGame === 3\) \{(?P<body>.*?)\n\s{12}\}",
        html,
        re.DOTALL,
    )
    assert m, "gbHandleAction subGame===3 block not found"
    body = m.group("body")

    # Strip single-line JS comments before checking — the template contains a
    # comment that mentions 'pl.selected gate' to explain why it was removed;
    # we must not count that comment as live code.
    body_no_comments = re.sub(r"//[^\n]*", "", body)
    assert "pl.selected" not in body_no_comments, (
        "gbHandleAction subGame===3 still gates on pl.selected — "
        "this was the old 'wait for tile click' guard; linear stepper doesn't need it"
    )


# ---------------------------------------------------------------------------
# JS: no legacy sliding artefacts in the entire template
# ---------------------------------------------------------------------------

def test_pl_no_scramble_loop():
    """Legacy sliding-puzzle artefacts must be fully removed from the template."""
    html = _read()
    assert "200 random valid moves" not in html, (
        "Template still contains '200 random valid moves' — "
        "the scramble loop is obsolete in the linear stepper"
    )
    assert "gbPLNeighbors" not in html, (
        "Template still contains gbPLNeighbors — "
        "sliding-tile neighbour logic is obsolete in the linear stepper"
    )


# ---------------------------------------------------------------------------
# JS: status update key
# ---------------------------------------------------------------------------

def test_pl_status_uses_step_status_key():
    """gbPLUpdateStatus must use the i18n key 'pl.step_status'."""
    html = _read()
    m = re.search(
        r"function gbPLUpdateStatus\(\)\s*\{(?P<body>.*?)\n\s{8}\}",
        html,
        re.DOTALL,
    )
    assert m, "gbPLUpdateStatus function not found"
    body = m.group("body")
    assert "RT('pl.step_status')" in body, (
        "gbPLUpdateStatus must call RT('pl.step_status') to render localised step counter"
    )
