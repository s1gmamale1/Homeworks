"""
Regression tests for PR — dropdown / builder i18n / FAB label.

Covers three bugs fixed together:

  1. Index dropdown options ("All subjects", "All statuses", "All modes")
     showed gray-on-light text in dark theme because the bare `<option>`
     popup never picked up the dark-theme overrides.

  2. Builder sidebar phase tabs ("Ko'rib chiqish", "Flesh-kartalar", …)
     were stuck in Uzbek because PHASE_NAMES is a hardcoded literal in
     builder.js and the i18n.onChange callback never re-rendered phases.

  3. The floating "+ Panel" action button rendered lowercase and was stuck
     in English because syncFab() derives its label from the source
     "Add panel" button text (which is itself hardcoded English).

These are static asserts on the shipped CSS/JS/strings — they don't need
a JS runtime, just regex over the source files.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


ROOT = Path(__file__).parent.parent
APP_CSS = ROOT / "frontend" / "css" / "app.css"
BUILDER_JS = ROOT / "frontend" / "js" / "builder.js"
STRINGS_JS = ROOT / "frontend" / "js" / "i18n" / "strings.js"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# ── #1: dark-mode <option> styling ──────────────────────────────────────────


def test_dark_mode_select_option_has_solid_bg_and_readable_color():
    """The native <option> popup ignores rgba transparency, so dark mode
    must set a solid background and a readable color on `select option`."""
    css = _read(APP_CSS)
    # Find the rule body that targets `[data-theme="dark"] select option`.
    match = re.search(
        r'\[data-theme="dark"\]\s+select\s+option\s*\{(?P<body>[^}]*)\}',
        css,
    )
    assert match, (
        "No `[data-theme=\"dark\"] select option { ... }` rule found — "
        "dropdown items will inherit OS defaults and look gray on white."
    )
    body = match.group("body")
    assert "background-color" in body or "background:" in body, (
        "Dark-mode `select option` must set a solid background-color so the "
        "popup is readable, got: " + body
    )
    assert "color" in body, (
        "Dark-mode `select option` must set color so text isn't system-default"
    )
    # Must NOT use rgba/transparent — native option popups ignore those.
    assert "rgba(" not in body, (
        "Dark-mode `select option` background must be a solid color, not rgba "
        "(native dropdown popups do not honor transparency)"
    )


# ── #2: builder phase tab i18n ──────────────────────────────────────────────


PHASE_KEYS = (
    "preview",
    "flashcards",
    "memory_sprint",
    "reading",
    "game_breaks",
    "real_life",
    "real_life_challenge",
    "consolidation",
    "final_challenge",
    "reflection",
)


@pytest.mark.parametrize("phase", PHASE_KEYS)
@pytest.mark.parametrize("lang", ("en", "uz", "ru"))
def test_builder_phase_label_present_in_every_lang(phase: str, lang: str):
    """Every PHASE_NAMES key in builder.js must have a matching i18n entry
    in every language so the sidebar tabs respond to language changes."""
    src = _read(STRINGS_JS)
    # Locate the lang block by brace-balancing.
    marker = re.search(rf"\b{lang}\s*:\s*\{{", src)
    assert marker, f"could not find `{lang}:` block in strings.js"
    start = marker.end()
    depth = 1
    i = start
    while i < len(src) and depth > 0:
        ch = src[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                break
        i += 1
    body = src[start:i]
    key = f"builder.phase_{phase}"
    assert f"'{key}'" in body or f'"{key}"' in body, (
        f"strings.js[{lang}] is missing required key {key!r} — "
        "builder sidebar tab will not localise on language switch"
    )


def test_builder_get_phase_names_uses_i18n():
    """getPhaseNames() must consult window.i18n.t (via the local t() helper)
    so phase tab labels follow the active language."""
    src = _read(BUILDER_JS)
    # Pull out the function body by brace-balancing from the signature.
    sig = re.search(r"function\s+getPhaseNames\s*\(\)\s*\{", src)
    assert sig, "getPhaseNames not defined in builder.js"
    start = sig.end()
    depth = 1
    i = start
    while i < len(src) and depth > 0:
        ch = src[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                break
        i += 1
    body = src[start:i]
    assert "builder.phase_" in body, (
        "getPhaseNames() must read `builder.phase_*` i18n keys so the sidebar "
        "tracks language changes"
    )


def test_builder_onchange_callback_rerenders_phases():
    """The i18n.onChange handler must re-render the phase sidebar — without
    this, the tab labels stay in the previous language until phase swap."""
    src = _read(BUILDER_JS)
    onchange = re.search(
        r"window\.i18n\.onChange\s*\(\s*\(\)\s*=>\s*\{(?P<body>.*?)\}\s*\);",
        src,
        re.DOTALL,
    )
    assert onchange, "i18n.onChange callback not found in builder.js"
    assert "renderPhases" in onchange.group("body"), (
        "i18n.onChange callback must call renderPhases() so sidebar tabs "
        "refresh on language switch"
    )


# ── #3: + Panel FAB label uppercase + i18n ──────────────────────────────────


def test_fab_label_is_rendered_uppercase():
    """The .fab-label element must use text-transform:uppercase so phase
    nouns (Panel, Card, Question…) read as capitals after the + icon."""
    css = _read(APP_CSS)
    match = re.search(
        r"\.fab-add\s+\.fab-label\s*\{(?P<body>[^}]*)\}",
        css,
    )
    assert match, "No `.fab-add .fab-label` rule found in app.css"
    body = match.group("body")
    assert re.search(r"text-transform\s*:\s*uppercase", body), (
        "`.fab-add .fab-label` must set text-transform:uppercase, got: " + body
    )


@pytest.mark.parametrize("noun", (
    "panel", "card", "question", "checkpoint", "field", "bullet", "boss_question",
))
@pytest.mark.parametrize("lang", ("en", "uz", "ru"))
def test_fab_short_keys_present_in_every_lang(noun: str, lang: str):
    """Every FAB phase noun must have a translation in every lang so the
    label switches when the user toggles UZ/RU/EN."""
    src = _read(STRINGS_JS)
    marker = re.search(rf"\b{lang}\s*:\s*\{{", src)
    assert marker
    start = marker.end()
    depth = 1
    i = start
    while i < len(src) and depth > 0:
        ch = src[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                break
        i += 1
    body = src[start:i]
    key = f"builder.fab_short_{noun}"
    assert f"'{key}'" in body or f'"{key}"' in body, (
        f"strings.js[{lang}] is missing required FAB key {key!r}"
    )


def test_syncfab_prefers_phase_i18n_over_text_strip():
    """syncFab must consult builder.fab_short_* i18n keys before falling
    back to deriving the label from the source button text — otherwise
    the FAB label stays English regardless of language."""
    src = _read(BUILDER_JS)
    sig = re.search(r"function\s+syncFab\s*\(\)\s*\{", src)
    assert sig, "syncFab not defined in builder.js"
    start = sig.end()
    depth = 1
    i = start
    while i < len(src) and depth > 0:
        ch = src[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                break
        i += 1
    body = src[start:i]
    assert "builder.fab_short_" in body or "FAB_PHASE_I18N" in body, (
        "syncFab must look up `builder.fab_short_*` i18n keys (or use "
        "FAB_PHASE_I18N map) so the label tracks language changes"
    )
