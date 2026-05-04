"""
Regression: clicking the homework-card three-dot menu must not flash
the entire dashboard grid.

Earlier code in `frontend/js/dashboard.js`:

    function toggleCardMenu(homeworkId) {
        state.openMenuId = state.openMenuId === homeworkId ? null : homeworkId;
        renderHomeworks();
    }

    function closeAllMenus() {
        if (state.openMenuId !== null) {
            state.openMenuId = null;
            renderHomeworks();
        }
    }

`renderHomeworks()` wipes `#homework-grid` innerHTML and re-attaches
the IntersectionObserver-driven `.hw-card` opacity stagger reveal. So
every menu toggle re-played the entire grid's reveal animation — the
user saw the screen "flash / refresh" on every click of the
`.js-menu-toggle` dot button.

The fix is to flip the single affected card's `.is-open` + the toggle's
`aria-expanded` attribute in place via a small `_setCardMenuOpen`
helper, with no grid re-render. This file pins that behavior so the
flash can't be reintroduced.
"""
from pathlib import Path

import pytest


DASHBOARD_JS = Path(__file__).parent.parent / "frontend" / "js" / "dashboard.js"


@pytest.fixture(scope="module")
def dashboard_source() -> str:
    return DASHBOARD_JS.read_text(encoding="utf-8")


def _slice_function(src: str, name: str) -> str:
    """Return the body of a top-level `function <name>(...)` declaration.

    The parser is intentionally simple: find the function header, then
    walk braces to find the matching closing brace. Good enough for a
    static regression check on a hand-written, well-formatted file.
    """
    needle = f"function {name}("
    start = src.find(needle)
    assert start != -1, f"function {name} not found in dashboard.js"
    brace = src.find("{", start)
    assert brace != -1, f"opening brace not found for function {name}"
    depth = 0
    i = brace
    while i < len(src):
        ch = src[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return src[brace : i + 1]
        i += 1
    raise AssertionError(f"unterminated function body for {name}")


# ---------------------------------------------------------------------------
# Menu toggle must not trigger a full grid re-render.
# ---------------------------------------------------------------------------


def test_toggle_card_menu_does_not_call_render_homeworks(dashboard_source):
    body = _slice_function(dashboard_source, "toggleCardMenu")
    assert "renderHomeworks(" not in body, (
        "toggleCardMenu must not call renderHomeworks() — that wipes "
        "#homework-grid innerHTML and replays the IntersectionObserver "
        "reveal stagger, which the user perceives as a screen flash on "
        "every click of the three-dot menu."
    )


def test_close_all_menus_does_not_call_render_homeworks(dashboard_source):
    body = _slice_function(dashboard_source, "closeAllMenus")
    assert "renderHomeworks(" not in body, (
        "closeAllMenus must not call renderHomeworks() — clicking outside "
        "an open menu should just close the menu, not re-render the grid "
        "(which would flash all cards via the reveal stagger)."
    )


# ---------------------------------------------------------------------------
# The surgical helper must be wired up correctly.
# ---------------------------------------------------------------------------


def test_set_card_menu_open_helper_is_defined(dashboard_source):
    """The flash fix relies on a per-card class toggle helper. Pin its
    presence and shape so a future refactor can't drop it back to
    re-rendering the grid."""
    assert "function _setCardMenuOpen(" in dashboard_source, (
        "expected helper `_setCardMenuOpen(homeworkId, open)` that flips "
        "the .is-open class on a single .hw-card-menu and updates "
        "aria-expanded on .js-menu-toggle, without touching the grid"
    )


def test_toggle_card_menu_uses_set_card_menu_open(dashboard_source):
    body = _slice_function(dashboard_source, "toggleCardMenu")
    assert "_setCardMenuOpen(" in body, (
        "toggleCardMenu must drive the DOM update through _setCardMenuOpen "
        "so only the affected card's menu changes — no grid re-render"
    )
    # Both transitions must be handled — close the previously-open one,
    # then open the new one (or just close, if toggling off).
    assert body.count("_setCardMenuOpen(") >= 2, (
        "toggleCardMenu must call _setCardMenuOpen for both the previously "
        "open card (to close it) and the newly-clicked card (to open it)"
    )


def test_close_all_menus_uses_set_card_menu_open(dashboard_source):
    body = _slice_function(dashboard_source, "closeAllMenus")
    assert "_setCardMenuOpen(" in body, (
        "closeAllMenus must close the open menu via _setCardMenuOpen, not "
        "by re-rendering the whole grid"
    )


# ---------------------------------------------------------------------------
# State bookkeeping must still be in place — the helper is a UI-only
# update, but state.openMenuId still needs to track the current menu so
# re-renders triggered by other code paths (filter change, language
# change, etc.) restore the correct .is-open card.
# ---------------------------------------------------------------------------


def test_toggle_card_menu_still_updates_state_open_menu_id(dashboard_source):
    body = _slice_function(dashboard_source, "toggleCardMenu")
    assert "state.openMenuId" in body, (
        "toggleCardMenu must keep tracking state.openMenuId so renderHomeworks "
        "(triggered by filter/sort/language changes) still emits the "
        "correct .is-open class on the persisted card"
    )


def test_close_all_menus_still_clears_state_open_menu_id(dashboard_source):
    body = _slice_function(dashboard_source, "closeAllMenus")
    assert "state.openMenuId = null" in body, (
        "closeAllMenus must still clear state.openMenuId; otherwise a "
        "later renderHomeworks() would re-emit the stale .is-open class"
    )
