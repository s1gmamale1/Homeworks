"""
Regression guard: the unified search-bar redesign (lane: runtime UX
polish, 2026-04-30).

After this PR every search input across the frontend — dashboard,
library, and the gate-quote picker modal — must share the same
`.search-box` look. The CSS rule defines a smooth focus state that uses
`--accent-glow`, and a dark-mode override exists. If any of those
invariants regress, the bars will drift apart again.
"""
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).parent.parent
FRONTEND = ROOT / "frontend"
APP_CSS = FRONTEND / "css" / "app.css"
INDEX_HTML = FRONTEND / "index.html"
LIBRARY_HTML = FRONTEND / "library.html"
QUOTE_PICKER_JS = FRONTEND / "js" / "editors" / "_quote-picker.js"
SEARCH_BOX_JS = FRONTEND / "js" / "search-box.js"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _css_block(source: str, selector: str) -> str:
    """Return the body of the first CSS rule whose selector matches.

    The match is anchored on the literal selector followed by `{` so
    near-misses (e.g. ``.search-box:hover``) don't accidentally satisfy
    ``.search-box``.
    """
    pattern = re.escape(selector) + r"\s*\{(?P<body>[^}]*)\}"
    match = re.search(pattern, source)
    assert match, f"missing CSS block for {selector}"
    return match.group("body")


# ---------------------------------------------------------------------------
# 1) The dashboard, library, and quote picker all opt into `.search-box`.
# ---------------------------------------------------------------------------


def test_dashboard_search_uses_shared_search_box():
    html = _read(INDEX_HTML)
    # The pill wrapper must carry the shared class and the input keeps
    # its id + type=search so dashboard.js wiring still binds.
    assert 'class="search-box"' in html
    assert 'id="search-input"' in html
    assert 'type="search"' in html


def test_library_search_uses_shared_search_box():
    html = _read(LIBRARY_HTML)
    # `.lib-search` is a grid-stretch modifier on top of `.search-box`,
    # not a replacement — both classes must be present together.
    assert 'class="search-box lib-search"' in html
    assert 'id="lib-search"' in html
    assert 'type="search"' in html


def test_quote_picker_search_uses_shared_search_box():
    js = _read(QUOTE_PICKER_JS)
    # The quote-picker filter row now wraps the search field in the same
    # `.search-box` pill, so the modal inherits the unified look.
    assert "search-box quote-picker-search" in js
    assert "js-quote-search" in js
    # Old ad-hoc form-input search field must be gone — otherwise the
    # picker would render two competing inputs.
    assert "js-quote-search form-input" not in js


# ---------------------------------------------------------------------------
# 2) The shared CSS rule defines a focus state using --accent-glow.
# ---------------------------------------------------------------------------


def test_search_box_base_rule_exists():
    css = _read(APP_CSS)
    base = _css_block(css, ".search-box")
    # Premium pill: compact height + soft radius + transition for a
    # smooth focus animation (no jarring snap).
    assert "height: 38px" in base
    assert "border-radius: 11px" in base
    assert "transition" in base


def test_search_box_focus_state_uses_accent_glow():
    css = _read(APP_CSS)
    focus = _css_block(css, ".search-box:focus-within")
    # The focus ring is the user-facing signal that the bar is active.
    # It must be drawn with `box-shadow` referencing `--accent-glow`,
    # and the border must shift to `--accent` so the ring lines up.
    assert "box-shadow" in focus
    assert "--accent-glow" in focus
    assert "--accent" in focus


# ---------------------------------------------------------------------------
# 3) Dark-mode override exists and re-states the focus ring so the
#    glow doesn't get clobbered when [data-theme="dark"] redefines the
#    base shadow.
# ---------------------------------------------------------------------------


def test_search_box_has_dark_mode_override():
    css = _read(APP_CSS)
    dark_base = _css_block(css, '[data-theme="dark"] .search-box')
    assert "background" in dark_base or "box-shadow" in dark_base

    dark_focus = _css_block(css, '[data-theme="dark"] .search-box:focus-within')
    assert "--accent-glow" in dark_focus, (
        "dark-mode focus ring must still reference --accent-glow so the "
        "focus state matches the light-mode bar."
    )


# ---------------------------------------------------------------------------
# 4) The shared clear button + wiring script ship together.
# ---------------------------------------------------------------------------


def test_search_box_clear_button_styled():
    css = _read(APP_CSS)
    clear = _css_block(css, ".search-box .search-box__clear")
    # Hidden until the wrapper picks up `.is-filled` from the wiring JS.
    assert "display: none" in clear
    visible = _css_block(css, ".search-box.is-filled .search-box__clear")
    assert "display: inline-flex" in visible


def test_search_box_empty_state_matches_filled_right_inset():
    """SEARCH-PAD-01: when the input has no `.is-filled` class the
    wrapper's effective right inset should match the filled state's
    inset (8px), so the bar doesn't look like it has dead space on
    the right when empty.

    The base `.search-box` keeps its `padding: 0 10px 0 12px` for the
    filled state (the X button's `margin-right: -2px` shaves the right
    inset down to 8px). For the empty state, an explicit
    `:not(.is-filled)` rule must drop padding-right to 8px so both
    states feel balanced."""
    css = _read(APP_CSS)
    empty = _css_block(css, ".search-box:not(.is-filled)")
    assert re.search(r"padding-right\s*:\s*8px", empty), (
        "expected `.search-box:not(.is-filled) { padding-right: 8px; }` "
        "to balance the empty-state right inset against the filled-state "
        "inset (which is 8px after the X button's negative margin)."
    )


def test_search_box_input_overrides_global_input_styles():
    """SEARCH-INNER-BOX-01: the global `input[type="search"]` rule (and
    its `[data-theme="dark"]` override further down the file) tie on
    specificity with `.search-box input` and win by source order. Without
    an explicit `[type=…]` qualifier on the wrapper-scoped rule, the
    inner input paints its own 1px border + background + border-radius
    inside the wrapper pill — visible as a "second box" near the right
    edge of the bar.

    This guard locks in the fix on two axes:
      1. The light-mode rule must qualify `[type="search"]` /
         `[type="text"]` so its specificity climbs from (0,1,1) to
         (0,2,1) and beats the global input rule.
      2. A dark-mode rule scoped to `[data-theme="dark"] .search-box
         input[type="search"]` must exist (specificity (0,3,1)) so it
         beats `[data-theme="dark"] input[type="search"]` (0,2,1).
    Both rules must zero `background` and `border` for the input."""
    css = _read(APP_CSS)

    # 1. Light-mode rule: the wrapper-scoped selector list must include
    #    the typed selector so the rule wins over `input[type="search"]`.
    light_pattern = re.compile(
        r"\.search-box input\[type=[\"']search[\"']\]"
        r"[^{}]*\{[^}]*background\s*:\s*transparent[^}]*\}",
        re.DOTALL,
    )
    assert light_pattern.search(css), (
        "expected a `.search-box input[type=\"search\"]` rule with "
        "`background: transparent` so the typed selector beats the "
        "global `input[type=\"search\"]` rule (without the type qualifier "
        "they tie on specificity and source order wins)."
    )

    # 2. Dark-mode tail: the wrapper-scoped dark override must reset
    #    background so the global dark override doesn't paint a second
    #    box inside the pill.
    dark_pattern = re.compile(
        r"\[data-theme=[\"']dark[\"']\]\s+\.search-box\s+input\[type=[\"']search[\"']\]"
        r"[^{}]*\{[^}]*background\s*:\s*transparent[^}]*\}",
        re.DOTALL,
    )
    assert dark_pattern.search(css), (
        "expected `[data-theme=\"dark\"] .search-box input[type=\"search\"]` "
        "override that resets `background: transparent` so the global "
        "`[data-theme=\"dark\"] input[type=\"search\"]` rule doesn't "
        "repaint an opaque inner box on top of the wrapper pill."
    )


def test_search_box_wiring_script_is_loaded_by_pages():
    assert SEARCH_BOX_JS.exists(), "frontend/js/search-box.js is missing"
    js = _read(SEARCH_BOX_JS)
    # The wiring must dispatch a synthetic input event so each page's
    # debounced filter handler still runs after a clear.
    assert "data-search-clear" in js
    assert "is-filled" in js
    assert 'new Event("input"' in js

    for html_path in (INDEX_HTML, LIBRARY_HTML, FRONTEND / "builder.html"):
        html = _read(html_path)
        assert "/js/search-box.js" in html, (
            f"{html_path.name} must include /js/search-box.js for the shared "
            "search-bar wiring to fire."
        )
