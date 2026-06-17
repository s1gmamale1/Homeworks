"""Dark-mode coverage regression tests for the runtime template.

User-flagged: Memory Sprint option buttons rendered as white-on-white in
dark mode, with text barely visible. This file checks that every runtime
control we know to be a candidate for white-bg-leak has a matching
[data-theme="dark"] override in the same template, and also walks every
selector with a hardcoded near-white background to make sure it's
either covered by an override or explicitly opted out (results-* are
already dark-tinted by design).
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


def _read(src) -> str:
    if isinstance(src, str):
        return src
    return src.read_text(encoding="utf-8")


def _css_block(source: str, selector: str) -> str:
    """Return the body of the first CSS rule matching `selector`."""
    match = re.search(re.escape(selector) + r"\s*\{(?P<body>[^}]*)\}", source)
    assert match, f"missing CSS block for {selector}"
    return match.group("body")


# Selectors that previously had hardcoded near-white backgrounds with no
# dark counterpart. These are the controls users actually click on, so a
# regression here means a button vanishes in dark mode.
DARK_MODE_REQUIRED_CONTROLS = [
    # Memory Sprint — the user-reported regression
    ".ms-question-box",
    ".ms-option-btn",
    ".ms-option-btn.correct",
    ".ms-option-btn.wrong",
    # Real Life input
    ".rl-input",
    # Wave V (PR #68) coverage — re-checked here so a future revert is caught
    ".boss-input",
    ".boss-hint-btn",
    ".screen-reading-input",
    ".screen-reading-btn",
    ".screen-cons-toggle",
    ".aq-textarea",
    ".aq-drop",
    ".gb-wc-textarea",
    ".gb-mb-label",
    ".gb-pl-cell",
    ".gb-mm-front-face",
    ".rl-capture-btn",
    ".quote-author-chip",
    ".quote-author-chip--global",
]


@pytest.mark.parametrize("selector", DARK_MODE_REQUIRED_CONTROLS)
def test_dark_mode_override_exists(selector: str):
    """Every interactive control must have a paired [data-theme=dark] rule."""
    html = _read(RUNTIME)
    dark_selector = f'[data-theme="dark"] {selector}'
    block = _css_block(html, dark_selector)
    # Must declare at least one of the visual properties that fix the
    # white-on-white bug (bg, color, or border).
    assert any(prop in block for prop in ("background:", "color:", "border-color:")), (
        f"{dark_selector} has no visual properties — control may be invisible"
    )


def test_memory_sprint_button_dark_bg_is_not_white():
    """The user-reported case: ms-option-btn must drop the rgba(255,255,255,*)
    in dark mode. The override should set a dark surface tone."""
    html = _read(RUNTIME)
    block = _css_block(html, '[data-theme="dark"] .ms-option-btn')
    # The dark surface must be a slate-tinted rgba (15, 23, 42) — anything
    # close to white means the regression came back.
    assert "rgba(15, 23, 42" in block, (
        ".ms-option-btn dark override must use a dark slate surface, not white"
    )
    assert "color: var(--text)" in block, (
        ".ms-option-btn dark override must reset text color so it tracks "
        "the dark theme's --text variable"
    )


def test_memory_sprint_correct_wrong_states_are_legible_on_dark():
    """correct / wrong tints brighten for dark so they don't disappear
    against the dark slate."""
    html = _read(RUNTIME)
    correct = _css_block(html, '[data-theme="dark"] .ms-option-btn.correct')
    wrong = _css_block(html, '[data-theme="dark"] .ms-option-btn.wrong')
    assert "#86efac" in correct, "correct text color must be a light green on dark"
    assert "#fca5a5" in wrong, "wrong text color must be a light red on dark"


def test_memory_sprint_state_glyphs_brighten_on_dark():
    """The ✓/✗ pseudo-elements use dark green/red in light mode; brighten
    them for dark or they fade on the same-tinted backgrounds."""
    html = _read(RUNTIME)
    block_after = _css_block(html, '[data-theme="dark"] .ms-option-btn.correct::after')
    assert "#86efac" in block_after
    block_after_wrong = _css_block(html, '[data-theme="dark"] .ms-option-btn.wrong::after')
    assert "#fca5a5" in block_after_wrong


def test_no_white_background_leaks_for_runtime_controls():
    """Any selector with a hardcoded near-white background must have a
    [data-theme=dark] override OR be explicitly part of the dark-only
    surfaces (results-* etc.). This guards against future regressions
    where someone adds a new white-bg control without thinking about
    dark mode."""
    html = _read(RUNTIME)

    # Find every ".class { ... background: rgba(255,255,255,...) ... }" rule.
    light_bg = set(re.findall(
        r"^\s*\.([a-zA-Z][\w\-]+)\s*\{[^}]*background:\s*rgba\("
        r"(?:255,\s*255,\s*255|235,\s*246,\s*255|227,\s*242,\s*255)",
        html,
        re.MULTILINE,
    ))

    # Gather every class that has a [data-theme=dark] override.
    dark_overrides = set(re.findall(r'\[data-theme="dark"\]\s+\.([a-zA-Z][\w\-]+)', html))

    # Selectors that are intentionally dark-only-styled (a low-alpha white
    # tint that reads only as a faint highlight on a dark surface; in
    # light mode they're invisible by design — see the results screen).
    DARK_ONLY_BY_DESIGN = {
        "screen-results-amr",
        "results-amr-empty",
        "results-amr-note",
        "results-phase-bar-track",
        "results-phase-row",
    }

    missing = (light_bg - dark_overrides) - DARK_ONLY_BY_DESIGN
    assert not missing, (
        f"These controls have hardcoded near-white backgrounds with no "
        f"[data-theme=dark] override and aren't on the dark-only allow-list: "
        f"{sorted(missing)}"
    )
