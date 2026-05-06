"""
Regression tests for the Taskboard mobile/tablet responsive overhaul.

Why these checks:
  - taskboard.html shipped without a `<meta name="viewport">` tag, so mobile
    browsers fell back to a 980-1024 px desktop layout and zoomed out — the
    page was unreadable on phones and tablets without pinch-zoom.
  - taskboard.css had a single @media query (560 px, hides dock labels) and
    no tablet/mobile sizing, so the kanban board, header buttons, and modal
    grid all rendered with desktop dimensions on touch devices.
  - Touch-target hit areas (.tb-card-action, .tb-col-action, .tb-color-swatch)
    were ~22-30 px which is below WCAG-recommended 44 px minimum on mobile.

Static-asserts only — no JS runtime needed in CI.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


ROOT = Path(__file__).parent.parent
HTML = ROOT / "frontend" / "taskboard.html"
CSS = ROOT / "frontend" / "css" / "taskboard.css"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# ── HTML viewport meta ──────────────────────────────────────────────────────


def test_taskboard_html_has_viewport_meta():
    """The page must declare a viewport meta or mobile browsers fall back to
    a 980-px desktop layout. This was the root cause of every unreadable-on-
    phone symptom on the Taskboard."""
    html = _read(HTML)
    assert re.search(
        r'<meta\s+name="viewport"\s+content="[^"]*width=device-width[^"]*"',
        html,
    ), "taskboard.html is missing <meta name=\"viewport\" content=\"width=device-width…\">"


def test_viewport_meta_includes_initial_scale_and_safe_area():
    """initial-scale=1 prevents auto-zoom on input focus; viewport-fit=cover
    lets safe-area inset env() values populate on iOS notch devices."""
    html = _read(HTML)
    m = re.search(r'<meta\s+name="viewport"\s+content="([^"]+)"', html)
    assert m, "viewport meta not found"
    content = m.group(1)
    assert "initial-scale=1" in content, (
        "viewport meta should pin initial-scale=1 to avoid focus-zoom on form inputs"
    )
    assert "viewport-fit=cover" in content, (
        "viewport-fit=cover required so env(safe-area-inset-*) populates on iOS"
    )


# ── CSS: responsive breakpoints ─────────────────────────────────────────────


def test_taskboard_css_has_tablet_and_mobile_breakpoints():
    """The legacy stylesheet had a single @media (max-width: 560px) hiding
    dock labels. The fix needs at least three breakpoints — tablet (1023),
    phone (720), and the existing 560 — plus a small-phone tightening
    around 420 px."""
    css = _read(CSS)
    breakpoints = sorted(set(int(m) for m in re.findall(r"@media\s+\([^)]*max-width:\s*(\d+)px", css)))
    assert any(b in (1024,) for b in breakpoints), (
        f"Need a tablet breakpoint at exactly 1024 px so iPad landscape "
        f"(1024×768) gets the responsive treatment. Found: {breakpoints}"
    )
    assert any(720 <= b <= 768 for b in breakpoints), (
        f"Need a phone-portrait breakpoint near 720-768 px. Found: {breakpoints}"
    )
    assert len(breakpoints) >= 3, (
        f"Expected at least 3 max-width breakpoints, got {breakpoints}"
    )


# ── CSS: column sizing safe for touch + dynamic viewport ───────────────────


def test_tb_column_uses_dvh_with_vh_fallback():
    """`.tb-column { max-height: calc(100vh - 240px) }` is cropped by the
    iOS Safari dynamic toolbar. Below 1023 px we now declare both 100dvh
    (preferred) and 100vh (fallback)."""
    css = _read(CSS)
    assert "100dvh" in css, (
        "Expected 100dvh in responsive .tb-column max-height (iOS Safari "
        "dynamic toolbar fix)"
    )
    # Both lines should appear, dvh first then vh (CSS cascade keeps the last
    # declaration the browser understands).
    dvh_idx = css.find("100dvh")
    vh_after = css.find("100vh", dvh_idx)
    assert vh_after > dvh_idx, (
        "100vh fallback must follow the 100dvh declaration so older browsers "
        "still get a sensible value"
    )


def test_columns_become_swipe_friendly_on_phone():
    """Trello mobile UX: each column nearly fills the viewport so the user
    swipes between them. We assert the responsive rule sets a viewport-based
    flex-basis (e.g. min(88vw, 340px)) instead of the desktop fixed 290 px."""
    css = _read(CSS)
    # The desktop rule keeps `flex: 0 0 290px;`. The phone media query must
    # override it with a vw-based basis.
    phone_block = re.search(
        r"@media\s*\(max-width:\s*(?:720|768)px\)\s*\{(?P<body>.*?)\}\s*(?=@media|\Z)",
        css,
        re.DOTALL,
    )
    assert phone_block, "Phone breakpoint block not found"
    body = phone_block.group("body")
    assert re.search(r"\.tb-column\s*\{[^}]*\bflex:\s*0\s+0\s+min\(\s*\d+vw", body), (
        "Phone breakpoint should reset .tb-column flex-basis to a vw-based "
        "min() so each column nearly fills the viewport (Trello mobile pattern)"
    )


# ── CSS: touch-target floors ───────────────────────────────────────────────


@pytest.mark.parametrize("selector", [
    ".tb-card-action",
    ".tb-col-action",
    ".tb-color-swatch",
    ".taskboard-actions .btn",
    ".tb-add-card",
    ".tb-dock-btn",
])
def test_touch_targets_are_tap_friendly(selector: str):
    """Every interactive element on touch must end up with at least a 36-44 px
    hit target inside a phone/tablet @media block. We don't require it on the
    desktop rule (those use mouse) — only that the responsive blocks bump it."""
    css = _read(CSS)
    # Search the post-`/* Responsive` portion of the stylesheet.
    tail_idx = css.find("Responsive: tablet + mobile")
    assert tail_idx > 0, "Responsive section header not found in taskboard.css"
    tail = css[tail_idx:]
    # Look for a rule on this selector that declares min-width or min-height ≥ 36 px,
    # OR sets explicit width/height ≥ 36 px (color swatches go that route).
    pattern = re.escape(selector) + r"\s*[,{][^}]*?(?:min-width|min-height|width|height)\s*:\s*(\d+)px"
    sizes = [int(m) for m in re.findall(pattern, tail)]
    assert sizes, (
        f"No min-width/min-height/width/height declaration found for {selector!r} "
        f"inside the responsive blocks — touch target may stay tiny"
    )
    assert max(sizes) >= 36, (
        f"{selector} touch target too small in responsive rules (largest "
        f"declared dimension is {max(sizes)}px, need ≥36 px)"
    )


# ── CSS: header / modal / dock layout reflow on phone ─────────────────────


def test_header_stacks_on_phone():
    """At ≤720 px the title block + action buttons should stack vertically
    so '+ New task' / '+ New person' aren't cut off the right edge."""
    css = _read(CSS)
    phone = re.search(
        r"@media\s*\(max-width:\s*720px\)\s*\{(?P<body>.*?)\}\s*(?=@media|\Z)",
        css,
        re.DOTALL,
    )
    assert phone
    body = phone.group("body")
    assert re.search(r"\.taskboard-header\s*\{[^}]*flex-direction\s*:\s*column", body), (
        "Phone breakpoint must stack .taskboard-header (flex-direction: column)"
    )


def test_modal_collapses_three_up_grid_on_phone():
    """The 3-up Sub-tasks/Done/Attachments row needs to drop to single column
    below ~480 px, otherwise inputs get unusably narrow."""
    css = _read(CSS)
    phone = re.search(
        r"@media\s*\(max-width:\s*720px\)\s*\{(?P<body>.*?)\}\s*(?=@media|\Z)",
        css,
        re.DOTALL,
    )
    assert phone
    body = phone.group("body")
    assert re.search(r"\.tb-modal-row\s*\{[^}]*grid-template-columns\s*:\s*1fr", body), (
        "Phone breakpoint must drop .tb-modal-row to a single column"
    )


def test_dock_uses_safe_area_on_phone():
    """The fixed bottom dock must respect env(safe-area-inset-bottom) so it
    doesn't sit under the home-indicator on iOS."""
    css = _read(CSS)
    phone = re.search(
        r"@media\s*\(max-width:\s*720px\)\s*\{(?P<body>.*?)\}\s*(?=@media|\Z)",
        css,
        re.DOTALL,
    )
    assert phone
    body = phone.group("body")
    assert "safe-area-inset-bottom" in body, (
        "Phone bottom dock must read env(safe-area-inset-bottom) for iOS safe-area"
    )


# ── CSS: long-content guard ────────────────────────────────────────────────


def test_card_text_breaks_long_strings_on_phone():
    """Long URLs / math formulas inside card titles or descriptions blow out
    the column width without overflow-wrap:anywhere."""
    css = _read(CSS)
    tail_idx = css.find("Responsive: tablet + mobile")
    assert tail_idx > 0
    tail = css[tail_idx:]
    assert "overflow-wrap" in tail and "anywhere" in tail, (
        "Responsive rules must apply overflow-wrap:anywhere to .tb-card-title "
        "and .tb-card-desc so long unbreakable strings don't overflow the column"
    )


# ── Desktop rule UNCHANGED guard ───────────────────────────────────────────


def test_desktop_column_basis_is_still_290px():
    """The user explicitly asked: do NOT change the PC interface. The base
    .tb-column rule (outside any @media) must still say `flex: 0 0 290px`."""
    css = _read(CSS)
    # Find the FIRST .tb-column rule in the file (before any @media block).
    pre_media = css.split("@media", 1)[0]
    block = re.search(r"\.tb-column\s*\{(?P<body>[^}]*)\}", pre_media)
    assert block, "Base .tb-column rule not found above the @media blocks"
    body = block.group("body")
    assert re.search(r"flex\s*:\s*0\s+0\s+290px", body), (
        "Desktop .tb-column base rule must still be `flex: 0 0 290px` — the "
        "responsive overhaul must not modify the desktop layout"
    )


def test_desktop_taskboard_shell_padding_unchanged():
    """Desktop shell padding (1.5rem 1.5rem 6rem) untouched."""
    css = _read(CSS)
    pre_media = css.split("@media", 1)[0]
    block = re.search(r"\.taskboard-shell\s*\{(?P<body>[^}]*)\}", pre_media)
    assert block
    body = block.group("body")
    assert re.search(r"padding\s*:\s*1\.5rem\s+1\.5rem\s+6rem", body), (
        "Desktop .taskboard-shell padding must remain 1.5rem 1.5rem 6rem"
    )
