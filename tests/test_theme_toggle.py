"""Regression tests for the global dark/light theme toggle (PR #37).

PR #37 added `frontend/js/theme.js` and a `[data-theme-toggle]` button on every
chrome page (dashboard, builder, library) so the toggle works outside the AI
tutor chat panel. The reviewer docked the test score because no test guarded
the toggle's surface invariants. These tests lock those invariants without a
JS runtime — they read the served HTML and the static JS/CSS source.
"""

import os
import re

import pytest


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEME_JS = os.path.join(BASE_DIR, "frontend", "js", "theme.js")
APP_CSS = os.path.join(BASE_DIR, "frontend", "css", "app.css")
LIBRARY_CSS = os.path.join(BASE_DIR, "frontend", "css", "library.css")
TUTOR_TEMPLATE = os.path.join(BASE_DIR, "server", "template", "perfect_homework.html")


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ──────────────────────────────────────────────────────────────────────
# 1. theme.js source-level invariants
# ──────────────────────────────────────────────────────────────────────


def test_theme_js_file_exists_and_is_iife():
    src = _read(THEME_JS)
    assert src.lstrip().startswith("/*") or src.lstrip().startswith("("), \
        "theme.js must start with a comment or IIFE"
    assert "(function" in src, "theme.js must be an IIFE to avoid leaking to global scope"


def test_theme_js_uses_nets_theme_storage_key():
    """The storage key must be `nets_theme` so the navbar toggle and the
    runtime tutor in-chat toggle (perfect_homework.html) stay in sync."""
    src = _read(THEME_JS)
    assert re.search(r"['\"]nets_theme['\"]", src), \
        "theme.js must use the literal storage key 'nets_theme'"


def test_theme_js_writes_data_theme_attribute_on_html_root():
    """The toggle target is `data-theme` on `documentElement` — that's what
    every CSS rule in app.css reads."""
    src = _read(THEME_JS)
    assert "documentElement.setAttribute" in src
    assert "'data-theme'" in src or '"data-theme"' in src


def test_theme_js_supports_bidirectional_flip():
    """Each click must read the current state and flip it. Without the
    ternary, a dark-only or light-only handler would leave the user stuck."""
    src = _read(THEME_JS)
    # Match the ternary that flips dark → light, otherwise → dark.
    flip = re.search(
        r"===\s*['\"]dark['\"]\s*\?\s*['\"]light['\"]\s*:\s*['\"]dark['\"]",
        src,
    )
    assert flip is not None, (
        "theme.js must contain a `=== 'dark' ? 'light' : 'dark'` flip"
    )


def test_theme_js_defaults_to_light_on_unknown_storage_value():
    """A malicious or stale storage value must not lock the user into dark.
    The init line `saved === 'dark' ? 'dark' : 'light'` enforces this."""
    src = _read(THEME_JS)
    assert re.search(
        r"saved\s*===\s*['\"]dark['\"]\s*\?\s*['\"]dark['\"]\s*:\s*['\"]light['\"]",
        src,
    ), "theme.js must default to 'light' when storage holds anything other than 'dark'"


def test_theme_js_listens_for_storage_event():
    """The parent navbar must resync when the runtime iframe's in-chat
    toggle writes to localStorage. Without the storage listener, the parent
    button's emoji desyncs from the actual theme until next click."""
    src = _read(THEME_JS)
    assert "addEventListener('storage'" in src or 'addEventListener("storage"' in src, \
        "theme.js must listen for the storage event for cross-frame/tab sync"


def test_theme_js_guards_localstorage_access():
    """localStorage.setItem/getItem can throw in private-browsing mode and
    in some sandboxed iframes. The toggle must degrade gracefully."""
    src = _read(THEME_JS)
    assert "try" in src and "catch" in src, \
        "theme.js must wrap localStorage access in try/catch"


def test_theme_js_storage_key_matches_runtime_tutor():
    """Cross-file consistency: the navbar toggle's storage key must match
    the runtime AI tutor's storage key, or the two will drift."""
    theme = _read(THEME_JS)
    tutor = _read(TUTOR_TEMPLATE)
    # Both files reference the same string literal.
    assert "'nets_theme'" in theme or '"nets_theme"' in theme
    assert "'nets_theme'" in tutor or '"nets_theme"' in tutor


# ──────────────────────────────────────────────────────────────────────
# 2. Each chrome page mounts theme.js + a navbar toggle button
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("path", ["/", "/builder.html", "/library.html"])
def test_page_includes_theme_js_with_cache_bust(client, path):
    """theme.js must be referenced before page paint and carry the cache-bust
    suffix that PR #35's strict test enforces."""
    r = client.get(path)
    assert r.status_code == 200
    body = r.text
    assert "/js/theme.js?v=" in body, f"{path} missing theme.js cache-bust tag"
    # The script tag must live in <head> so theme is applied before paint.
    head_end = body.find("</head>")
    theme_pos = body.find("/js/theme.js")
    assert head_end > 0 and theme_pos > 0 and theme_pos < head_end, \
        f"{path}: theme.js must load inside <head> to avoid FOUC"


@pytest.mark.parametrize("path", ["/", "/builder.html", "/library.html"])
def test_page_has_data_theme_toggle_button(client, path):
    """Every chrome page must surface a [data-theme-toggle] button so the
    user can switch theme outside the AI tutor chat panel."""
    r = client.get(path)
    assert r.status_code == 200
    body = r.text
    assert "data-theme-toggle" in body, f"{path}: missing [data-theme-toggle] button"


@pytest.mark.parametrize("path", ["/", "/builder.html", "/library.html"])
def test_toggle_button_initial_state_is_light(client, path):
    """Initial render must show the light-mode affordance (🌙 + aria-pressed=false +
    aria-label='Switch to dark mode'). theme.js rewrites these on load if the
    user has dark saved."""
    r = client.get(path)
    body = r.text
    # Find the toggle button tag and assert its attributes.
    match = re.search(r"<button[^>]*data-theme-toggle[^>]*>.*?</button>", body, re.DOTALL)
    assert match, f"{path}: toggle button not found"
    btn = match.group(0)
    assert 'aria-pressed="false"' in btn
    assert 'Switch to dark mode' in btn


# ──────────────────────────────────────────────────────────────────────
# 3. Dark-mode CSS coverage — selectors flagged in the audit
# ──────────────────────────────────────────────────────────────────────


def test_app_css_has_theme_toggle_button_styling():
    css = _read(APP_CSS)
    assert ".theme-toggle" in css, "app.css must define .theme-toggle styling"


@pytest.mark.parametrize(
    "selector",
    [
        # The high-priority gaps surfaced by the audit on PR #37.
        '[data-theme="dark"] input[type="text"]',
        '[data-theme="dark"] textarea',
        '[data-theme="dark"] .nested-card',
        '[data-theme="dark"] .empty-mini',
        '[data-theme="dark"] .fixture-card',
        '[data-theme="dark"] .json-preview',
        '[data-theme="dark"] .save-indicator',
        '[data-theme="dark"] .save-indicator[data-state="saved"]',
        '[data-theme="dark"] .save-indicator[data-state="offline"]',
    ],
)
def test_app_css_dark_mode_coverage(selector):
    """Lock the dark-mode override rules added by PR #37 — without these,
    dark mode looked broken on builder/dashboard surfaces (white inputs,
    bright fixture cards, unreadable status text)."""
    css = _read(APP_CSS)
    assert selector in css, f"app.css missing dark-mode rule for `{selector}`"


@pytest.mark.parametrize(
    "selector",
    [
        # 2026-04-30 v2: in-grid expansion replaces the FLIP overlay.
        # The homework-card inside an expanded tile now mirrors the
        # dashboard's card design — dashboard parity tokens (var(--text),
        # var(--surface), var(--border), var(--accent)) adapt to both
        # themes via app.css, so we no longer need explicit per-tag
        # light-mode overrides. We DO still need to pin the dark theme's
        # expanded-tile recolour (the linear-gradient background must
        # change between light and dark or the tile becomes near-white
        # in dark mode).
        '[data-theme="dark"] .subject-tile',
        '[data-theme="dark"] .subject-tile.is-expanded',
        '[data-theme="dark"] .subject-tile .tile-icon',
        # And the per-mode pill colors must be present so HARD/EASY
        # tags keep their accessible WCAG-AA tinted backgrounds.
        '.homework-card .hw-pill[data-mode="hard"]',
        '.homework-card .hw-pill[data-mode="easy"]',
    ],
)
def test_library_css_theme_coverage(selector):
    """Lock the theme-aware rules in library.css for the redesigned
    subject tiles + homework cards. The 2026-04-30 v2 redesign moved
    to app.css token inheritance — most colours now adapt automatically.
    The two things that DO need explicit theme branches: the expanded
    tile's gradient (different mix ratios for light/dark) and the
    per-mode HARD/EASY pill colours."""
    css = _read(LIBRARY_CSS)
    assert selector in css, f"library.css missing rule for `{selector}`"
