"""Static regression for NAV-01 + NAV-02: the preview-stage action button
must stay reachable on every page of every panel.

Real-data baseline:
  HW-20260505-005 (geometriya G8) chunks to 19 pages × 7 panels with the
  current PREVIEW_PAGE_BUDGET_PX=760. Before the fix updatePanelButton put
  the button into pointer-events:none `.state-line` on every non-last page
  — students could only advance via swipe.

This test pins three properties of the post-fix template:
  1. updatePanelButton always adds 'state-pill' (clickable) — never just
     'state-line' on its own.
  2. The stage-2 click handler calls switchPage on intermediate pages
     (advancing one page) and nextPanel only on the last page of a panel.
  3. PREVIEW_PAGE_BUDGET_PX is *unchanged* at 760 — chunking behavior must
     not regress for non-math subjects.
  4. A 'btn.next_page' translation exists in all three locales (uz/ru/en).
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


def test_updatePanelButton_always_pill():
    """The function must not leave the button in a pointer-events:none state-line."""
    html = _read()
    m = re.search(
        r"function updatePanelButton\(\)\s*\{(?P<body>.*?)\n\s{8}\}",
        html,
        re.DOTALL,
    )
    assert m, "updatePanelButton function not found"
    body = m.group("body")
    # Always add state-pill regardless of branch.
    assert "btn.classList.add('state-pill')" in body, (
        "NAV-01 regression: updatePanelButton no longer adds 'state-pill' unconditionally"
    )
    # The non-last branch must NOT silently set the button as a thin state-line
    # (the prior bug). It may still mention 'state-line' in remove() — that's
    # fine; the regression is adding it back exclusively.
    bad_pattern = re.search(
        r"else\s*\{[^}]*btn\.classList\.add\(['\"]state-line['\"]\)",
        body,
    )
    assert bad_pattern is None, (
        "NAV-01 regression: updatePanelButton fell back to state-line on intermediate pages"
    )


def test_stage_2_click_advances_one_page_then_panel():
    """On click: advance one page if not last, else next panel."""
    html = _read()
    # The handler block lives inside handleAction(). We grep for the stage===2
    # branch and assert the new logic is wired.
    m = re.search(
        r"else if \(state\.stage === 2\) \{(?P<body>.*?)\}\s*else if \(state\.stage === 2\.5",
        html,
        re.DOTALL,
    )
    assert m, "stage-2 handleAction branch not found"
    body = m.group("body")
    assert "switchPage(state.pageIndex + 1)" in body, (
        "NAV-02 regression: clicking the CTA on an intermediate page no longer advances by one page"
    )
    assert "nextPanel()" in body, (
        "NAV-02 regression: clicking the CTA on the last page no longer advances to next panel"
    )


def test_preview_page_budget_unchanged():
    """Conservative-on-NAV-01: the chunking budget stays 760 so non-math
    subjects do not silently see a different page rhythm."""
    html = _read()
    m = re.search(
        r"const PREVIEW_PAGE_BUDGET_PX\s*=\s*(\d+);",
        html,
    )
    assert m, "PREVIEW_PAGE_BUDGET_PX constant not found"
    assert m.group(1) == "760", (
        f"NAV-01 conservative-fix regression: PREVIEW_PAGE_BUDGET_PX changed from 760 to {m.group(1)}; "
        "raising the budget affects ALL subjects and was explicitly out-of-scope for this PR."
    )


@pytest.mark.parametrize("locale_marker", ["uz: {", "ru: {", "en: {"])
def test_btn_next_page_translation_exists(locale_marker):
    """All three locales must have btn.next_page so the new copy never falls
    through to a missing-key placeholder."""
    html = _read()
    # Pull the locale block: `<marker> ... }` — naive but works for the flat
    # i18n table in this template.
    start = html.index(locale_marker)
    # Find the closing `}` for the locale block by counting depth.
    depth = 0
    end = start
    for i, c in enumerate(html[start:], start=start):
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    block = html[start:end]
    assert "'btn.next_page'" in block, (
        f"NAV-02 regression: btn.next_page translation missing in {locale_marker} block"
    )
