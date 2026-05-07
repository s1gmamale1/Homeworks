"""NAV-06 regression — html { overflow: hidden } + .panel-card { overflow: hidden }.

Mobile bug context (2026-05-07):
  When `nextPanel()` runs `renderPanel()` then briefly sets `#panel-content`
  to `transform: translateX(100%)` to slide the new panel in from the right,
  the box overflows its parent `.panel-card`. With `.panel-card` overflow
  visible AND `<html>` overflow visible (default), the horizontal overflow
  bubbles to `<html>`. Chrome mobile then grows the *layout viewport*
  (`window.innerWidth/Height`) to fit `html.scrollWidth/Height`. Every
  `position: fixed; bottom: …` element (action button + AI tutor FAB)
  re-anchors to the now-ballooned layout viewport — visually below the
  visible viewport. Resizing the window forces a relayout that snaps the
  layout viewport back to the visual viewport — which is exactly the
  "switch PC↔phone fixes it" workaround students reported.

The fix is two CSS rules in server/template/perfect_homework.html:

  1. `html { height: 100%; overflow: hidden; }` — matches the existing
     body rule so the layout viewport can never balloon.

  2. `.panel-card { … overflow: hidden; … }` — defense-in-depth so the
     `translateX(100%)` slide-in never leaks past the card box.

This test pins both rules. It is a pure-static parse — no HTTP client,
no homework row, no JS execution — so it runs in the same fast lane as
``tests/test_runtime_preview_cta_always_clickable.py``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


ROOT = Path(__file__).parent.parent
RUNTIME = ROOT / "server" / "template" / "perfect_homework.html"


def _read() -> str:
    return RUNTIME.read_text(encoding="utf-8")


def _block_for_selector(html: str, selector: str) -> str:
    """Return the body of the FIRST CSS rule whose selector matches.

    `selector` must match the literal opening of a rule (e.g. ``html``,
    ``body``, ``.panel-card``). The body returned is everything between
    the first ``{`` after the selector and its matching ``}``.
    """
    pattern = re.compile(
        r"(^|\n)\s*" + re.escape(selector) + r"\s*\{",
        re.MULTILINE,
    )
    m = pattern.search(html)
    assert m, f"selector {selector!r} not found in template"
    start = html.index("{", m.start()) + 1
    depth = 1
    for i in range(start, len(html)):
        c = html[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return html[start:i]
    raise AssertionError(f"unbalanced braces for selector {selector!r}")


def test_html_element_overflow_hidden_present():
    """The html element must clamp overflow.

    Without this, a panel-switch transition (which briefly sets
    #panel-content to translateX(100%)) inflates html.scrollWidth past the
    viewport. Chrome mobile then balloons window.innerHeight, dropping the
    fixed-positioned action button + AI tutor FAB below the visible area.
    """
    html = _read()
    block = _block_for_selector(html, "html")
    # Tolerate property re-ordering and other unrelated rules — the only
    # thing we care about is that overflow is set to hidden.
    assert re.search(r"overflow\s*:\s*hidden\s*;", block), (
        "NAV-06 regression: `html { overflow: hidden; }` is missing — the "
        "layout viewport will balloon during nextPanel() and push the "
        "action button + AI tutor FAB below the visible viewport on mobile."
    )


def test_html_element_height_full():
    """The html element must be height-locked so 100vh children can fill it.

    Without `html { height: 100% }` (or 100vh), `body { height: 100vh }`
    can be larger than the html box on mobile dynamic-toolbar browsers,
    creating a similar root-level overflow / balloon condition.
    """
    html = _read()
    block = _block_for_selector(html, "html")
    assert re.search(r"height\s*:\s*100%\s*;", block) or re.search(
        r"height\s*:\s*100vh\s*;", block
    ), (
        "NAV-06 regression: `html` must declare `height: 100%` (or 100vh) "
        "so the layout viewport stays pinned to the visual viewport."
    )


def test_panel_card_overflow_hidden_present():
    """Defense-in-depth: the panel card itself must clip its descendants.

    nextPanel() sets `#panel-content.style.transform = 'translateX(100%)'`
    for one frame. If `.panel-card` doesn't clip, that frame's overflow
    leaks toward the body/html and re-triggers the layout-viewport
    balloon on Chrome mobile even with the html-level guard above. Pin it
    so any future translate-based panel transition cannot regress the fix.
    """
    html = _read()
    block = _block_for_selector(html, ".panel-card")
    assert re.search(r"overflow\s*:\s*hidden\s*;", block), (
        "NAV-06 regression: `.panel-card { overflow: hidden; }` is missing "
        "— the panel-content slide-in animation will leak past the card "
        "box and can re-trigger the layout-viewport balloon."
    )


def test_body_overflow_hidden_unchanged():
    """Sanity-check: the existing body overflow:hidden rule is preserved.

    The fix is to ADD the html rule, not replace anything on body. If
    someone refactors `body { overflow: hidden }` away while editing this
    area, the bug re-opens at the body level on browsers that ignore the
    html-level clamp.
    """
    html = _read()
    block = _block_for_selector(html, "body")
    assert re.search(r"overflow\s*:\s*hidden\s*;", block), (
        "Pre-existing `body { overflow: hidden; }` was removed — keep it."
    )


@pytest.mark.parametrize(
    "fixed_selector,expected_position",
    [
        ("#action-button", "fixed"),
        ("#nets-ai-tutor", "fixed"),
    ],
)
def test_fixed_anchors_unchanged(fixed_selector, expected_position):
    """Both bottom-anchored controls must remain `position: fixed`.

    The NAV-06 fix relies on the layout viewport staying pinned to the
    visual viewport so `position: fixed; bottom: …` controls stay above
    the fold. If a future refactor ever switches them to `absolute` or
    `sticky`, the visual contract changes and this test should fail loudly
    so the change can be reviewed.
    """
    html = _read()
    block = _block_for_selector(html, fixed_selector)
    assert re.search(
        rf"position\s*:\s*{expected_position}\s*;", block
    ), (
        f"NAV-06 regression: {fixed_selector} is no longer "
        f"`position: {expected_position}` — the layout-viewport contract "
        "is broken."
    )
