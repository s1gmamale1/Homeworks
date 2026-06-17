"""DM-01 + DM-02 regression coverage extension.

Pre-existing tests/test_runtime_dark_mode_coverage.py already covers Memory
Sprint, AQ, Boss, and Reading interactive controls. The math-geometriya
demo audit added bottom-action-button and state-line as regression risks
because their bg/text colors are reachable from every preview/flashcard/AQ
phase students touch.

Pin the dark-mode counterparts so a future light-mode-only style sweep
(e.g. raising .btn-text contrast) cannot silently land without the dark
side moving with it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


ROOT = Path(__file__).parent.parent
_JS_PATH = ROOT / "server" / "template" / "js" / "perfect_homework.js"
_CSS_PATH = ROOT / "server" / "template" / "static" / "css" / "perfect_homework.css"
_HTML_PATH = ROOT / "server" / "template" / "perfect_homework.html"
RUNTIME = _HTML_PATH.read_text(encoding="utf-8") + "\n" + _JS_PATH.read_text(encoding="utf-8") + "\n" + _CSS_PATH.read_text(encoding="utf-8")


def _read() -> str:
    return RUNTIME


def _css_block(source: str, selector: str) -> str:
    pattern = re.escape(selector) + r"\s*(?:,\s*[^{}]+)?\s*\{(?P<body>[^}]*)\}"
    match = re.search(pattern, source)
    assert match, f"missing CSS block for {selector}"
    return match.group("body")


# DM-01: bottom action button visibility in dark mode. .btn-text and .state-line
# are reachable from every preview/flashcard/AQ/Boss phase, so any white-on-white
# regression here breaks every demo flow.
DARK_MODE_BUTTON_CONTROLS = [
    '[data-theme="dark"] .btn-text',
    '[data-theme="dark"] .state-line',
]


@pytest.mark.parametrize("dark_selector", DARK_MODE_BUTTON_CONTROLS)
def test_dark_mode_action_button_override_exists(dark_selector):
    """Each control must define at least one of: background, color, border-color."""
    html = _read()
    block = _css_block(html, dark_selector)
    assert any(prop in block for prop in ("background:", "color:", "border-color:")), (
        f"DM-01 regression: {dark_selector} has no visual properties"
    )


def test_btn_text_dark_color_is_near_white():
    """Defensive: .btn-text in dark must stay light (>=#e0e0e0 grayscale floor)."""
    html = _read()
    body = _css_block(html, '[data-theme="dark"] .btn-text')
    m = re.search(r"color:\s*(#[0-9a-fA-F]{3,8})", body)
    assert m, "DM-01 regression: dark .btn-text has no explicit color"
    color = m.group(1).lower()
    # Strip leading # and parse RGB. Accept #rgb shorthand too.
    hex_part = color[1:]
    if len(hex_part) == 3:
        rgb = [int(c * 2, 16) for c in hex_part]
    elif len(hex_part) >= 6:
        rgb = [int(hex_part[i:i + 2], 16) for i in (0, 2, 4)]
    else:
        pytest.fail(f"unsupported color format: {color}")
    assert min(rgb) >= 220, (
        f"DM-01 regression: dark .btn-text color {color} is not near-white (min channel {min(rgb)} < 220)"
    )


def test_state_line_dark_uses_accent_not_white():
    """state-line must use the accent token in dark, not a white-ish fallback."""
    html = _read()
    body = _css_block(html, '[data-theme="dark"] .state-line')
    m = re.search(r"background:\s*([^;]+);", body)
    assert m, "DM-01 regression: dark .state-line has no explicit background"
    bg = m.group(1).strip().lower()
    assert "var(--accent)" in bg or "rgba(0,122,255" in bg or "rgba(0,113,227" in bg, (
        f"DM-01 regression: dark .state-line bg {bg!r} is not the accent token"
    )
