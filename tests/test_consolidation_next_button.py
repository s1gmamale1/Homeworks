"""Regression tests for PR #210 — dedicated #cons-next-btn in consolidation phase.

Background
----------
Before PR #210, the consolidation phase relied on the shared ``#action-button``
(a 4px invisible state-line bar) being repurposed via a ``playPhaseAnnouncement``
callback. If the announcement callback never fired — e.g. on low-end devices or
network-throttled sessions — students had no visible way to advance past
consolidation. PR #210 added a dedicated always-visible ``<button id="cons-next-btn"
class="screen-cons-next">`` inside ``<div id="screen-consolidation">`` as an
unconditional escape hatch.

What these tests pin
--------------------
1. The HTML element ``<button id="cons-next-btn" class="screen-cons-next">``
   exists in the template.
2. It carries the ``screen-cons-next`` CSS class.
3. The JS in ``renderConsolidation`` wires a click listener that calls
   ``consState.onContinue()``.
4. The button text is set via ``RT('btn.next_page')`` so it varies per locale
   (uz/ru/en) rather than being hardcoded.
5. The wiring lives inside ``renderConsolidation``, NOT inside a
   ``playPhaseAnnouncement`` callback — so it fires unconditionally.

Pre-fix baseline: all five tests fail on the commit immediately before #210
(``0fdd506``) because none of the markers exist there.
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


@pytest.fixture(scope="module")
def html() -> str:
    return RUNTIME


def _render_consolidation_body(html: str) -> str:
    """Return the source body of ``function renderConsolidation()`` by walking
    matched braces. Tests against the body — not the full file — so a marker
    placed outside this function would correctly fail the test.
    """
    pat = re.compile(r"function\s+renderConsolidation\s*\(\s*\)\s*\{")
    m = pat.search(html)
    assert m, "renderConsolidation() not found in perfect_homework.html"
    start = m.end()
    depth = 1
    i = start
    while i < len(html) and depth > 0:
        c = html[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    return html[start:i]


def _screen_consolidation_block(html: str) -> str:
    """Return the substring between ``<div id="screen-consolidation"``
    and its matching closing ``</div>`` so containment tests are scoped.
    """
    open_pat = re.compile(r'<div\s[^>]*id=["\']screen-consolidation["\']')
    m = open_pat.search(html)
    assert m, "<div id=\"screen-consolidation\"> not found in perfect_homework.html"
    # Walk forward counting <div … tags and </div> tags to find the matching close
    start = m.start()
    pos = m.end()
    depth = 1
    while pos < len(html) and depth > 0:
        open_tag = html.find("<div", pos)
        close_tag = html.find("</div>", pos)
        if close_tag == -1:
            break
        if open_tag != -1 and open_tag < close_tag:
            depth += 1
            pos = open_tag + 4
        else:
            depth -= 1
            pos = close_tag + 6
    return html[start:pos]


# ---------------------------------------------------------------------------
# Test 1 — HTML element exists with id="cons-next-btn"
# ---------------------------------------------------------------------------

def test_consolidation_screen_has_dedicated_next_button(html: str) -> None:
    """PR #210 regression: template must contain a button with id='cons-next-btn'."""
    assert re.search(
        r'<button\b[^>]*\bid=["\']cons-next-btn["\']',
        html,
    ), (
        "No <button id='cons-next-btn'> found in perfect_homework.html. "
        "PR #210 added this element — its absence means the consolidation "
        "phase has no unconditional next-page escape hatch."
    )


# ---------------------------------------------------------------------------
# Test 2 — Button carries the screen-cons-next CSS class
# ---------------------------------------------------------------------------

def test_consolidation_next_button_has_screen_cons_next_class(html: str) -> None:
    """PR #210 regression: #cons-next-btn must have class='screen-cons-next'."""
    # Locate the specific button element
    btn_pat = re.compile(
        r'<button\b[^>]*\bid=["\']cons-next-btn["\'][^>]*>',
        re.DOTALL,
    )
    m = btn_pat.search(html)
    assert m, "<button id='cons-next-btn'> not found — run test 1 first."
    btn_tag = m.group(0)

    assert "screen-cons-next" in btn_tag, (
        f"Expected class='screen-cons-next' on #cons-next-btn, got: {btn_tag!r}"
    )

    # Also verify the CSS rule itself has display:block and var(--accent)
    css_rule_pat = re.compile(
        r'\.screen-cons-next\s*\{[^}]*display\s*:\s*block[^}]*\}',
        re.DOTALL,
    )
    assert css_rule_pat.search(html), (
        ".screen-cons-next { display: block; … } rule not found in inline <style>."
    )

    accent_pat = re.compile(
        r'\.screen-cons-next\s*\{[^}]*background\s*:\s*var\(--accent\)[^}]*\}',
        re.DOTALL,
    )
    assert accent_pat.search(html), (
        ".screen-cons-next must use var(--accent) as background — rule not found."
    )


# ---------------------------------------------------------------------------
# Test 3 — renderConsolidation wires click → consState.onContinue
# ---------------------------------------------------------------------------

def test_consolidation_next_button_wired_to_cons_state_oncontinue(html: str) -> None:
    """PR #210 regression: renderConsolidation() must wire #cons-next-btn's click
    to consState.onContinue so advancing consolidation doesn't depend on the
    playPhaseAnnouncement callback firing.
    """
    body = _render_consolidation_body(html)

    assert "getElementById('cons-next-btn')" in body or 'getElementById("cons-next-btn")' in body, (
        "renderConsolidation() does not call getElementById('cons-next-btn'). "
        "The click handler must be registered inside renderConsolidation()."
    )

    assert "consState.onContinue" in body, (
        "renderConsolidation() does not reference consState.onContinue. "
        "The click listener must invoke consState.onContinue() to advance the phase."
    )

    assert "addEventListener('click'" in body or 'addEventListener("click"' in body, (
        "renderConsolidation() does not attach a 'click' event listener. "
        "Expected fresh.addEventListener('click', …) inside renderConsolidation()."
    )


# ---------------------------------------------------------------------------
# Test 4 — Button text uses RT('btn.next_page') i18n key
# ---------------------------------------------------------------------------

def test_consolidation_next_button_uses_btn_next_page_i18n(html: str) -> None:
    """PR #210 regression: button text must come from RT('btn.next_page') so
    it varies per locale (uz/ru/en) rather than being hardcoded Uzbek text.
    """
    body = _render_consolidation_body(html)

    assert "RT('btn.next_page')" in body or 'RT("btn.next_page")' in body, (
        "renderConsolidation() does not set button text via RT('btn.next_page'). "
        "Hardcoded text breaks Uzbek/Russian/English localisation."
    )


# ---------------------------------------------------------------------------
# Test 5 — Button is inside <div id="screen-consolidation">
# ---------------------------------------------------------------------------

def test_consolidation_next_button_inside_screen_consolidation_div(html: str) -> None:
    """PR #210 regression: #cons-next-btn must be a descendant of
    <div id='screen-consolidation'> — not floating in another screen.
    """
    block = _screen_consolidation_block(html)

    assert re.search(
        r'<button\b[^>]*\bid=["\']cons-next-btn["\']',
        block,
    ), (
        "#cons-next-btn was not found inside <div id='screen-consolidation'>. "
        "The button must be a direct descendant of the consolidation screen div."
    )
