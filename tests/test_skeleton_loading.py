"""
Skeleton loading regression tests.

These assert that:
  1. The shared skeleton CSS lives in app.css (one system, not duplicated).
  2. Each non-Homework-Preview tab (Dashboard / Library / Taskboard / Builder)
     paints a layout-matching skeleton with proper aria-busy + aria-hidden.
  3. prefers-reduced-motion suppresses shimmer.
  4. JS handlers flip aria-busy off once real content lands.
  5. Homework Preview (frontend/js/editors/preview.js + the preview-frame
     iframe in builder.html) is NOT wrapped in the new skeleton system.

Static-file style mirrors the existing tests in this repo
(see test_landing_phone_aspect_ratio.py, test_dashboard_select_a11y.py).
"""

from pathlib import Path
import re

import pytest


# ── Source files under test ────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
APP_CSS = ROOT / "frontend" / "css" / "app.css"

DASHBOARD_HTML = ROOT / "frontend" / "index.html"
LIBRARY_HTML = ROOT / "frontend" / "library.html"
TASKBOARD_HTML = ROOT / "frontend" / "taskboard.html"
BUILDER_HTML = ROOT / "frontend" / "builder.html"

DASHBOARD_JS = ROOT / "frontend" / "js" / "dashboard.js"
LIBRARY_JS = ROOT / "frontend" / "js" / "library.js"
TASKBOARD_JS = ROOT / "frontend" / "js" / "taskboard.js"
BUILDER_JS = ROOT / "frontend" / "js" / "builder.js"

PREVIEW_EDITOR_JS = ROOT / "frontend" / "js" / "editors" / "preview.js"


# ── 1. Shared skeleton system in app.css ───────────────────────────────────
def test_app_css_defines_shared_skeleton_classes():
    css = APP_CSS.read_text(encoding="utf-8")
    # Core reusable primitives.
    for cls in (
        ".skeleton-bar",
        ".skeleton-line",
        ".skeleton-pill",
        ".skeleton-orb",
        ".skeleton-card",
    ):
        assert cls in css, f"Missing skeleton primitive: {cls}"

    # Grid wrappers that mirror real layouts.
    for cls in (
        ".skeleton-grid--cards",
        ".skeleton-grid--tiles",
        ".skeleton-grid--columns",
        ".skeleton-grid--stats",
    ):
        assert cls in css, f"Missing skeleton grid wrapper: {cls}"


def test_app_css_skeleton_has_shimmer_animation():
    css = APP_CSS.read_text(encoding="utf-8")
    assert "@keyframes skeleton-shimmer" in css
    assert "skeleton-shimmer" in css  # animation: skeleton-shimmer …
    # The shimmer must be a subtle sweep, not a heavy flash.
    assert "background-position" in css


def test_app_css_skeleton_respects_reduced_motion():
    css = APP_CSS.read_text(encoding="utf-8")
    # Find a prefers-reduced-motion block that mentions skeleton.
    blocks = re.findall(
        r"@media \(prefers-reduced-motion: reduce\)\s*\{[^@]*?skeleton[^@]*?\}",
        css,
        flags=re.S,
    )
    assert blocks, (
        "Expected a prefers-reduced-motion block referencing skeleton-* "
        "rules so shimmer is suppressed for users who need it."
    )
    block = blocks[0]
    assert "animation: none" in block, (
        "Reduced-motion block must zero the shimmer animation."
    )


def test_app_css_provides_sr_only_helper():
    css = APP_CSS.read_text(encoding="utf-8")
    # Skeleton loaders rely on .sr-only to expose the "Loading…" copy to
    # assistive tech without painting visible noise on top of the layout.
    assert ".sr-only" in css


# ── 2. Per-page skeleton markup ────────────────────────────────────────────
SKELETON_PAGES = [
    pytest.param(DASHBOARD_HTML, "skeleton-grid--cards", id="dashboard"),
    pytest.param(LIBRARY_HTML, "skeleton-grid--tiles", id="library"),
    pytest.param(TASKBOARD_HTML, "skeleton-grid--columns", id="taskboard"),
    pytest.param(BUILDER_HTML, "skeleton-card--editor", id="builder"),
]


@pytest.mark.parametrize("path,marker_class", SKELETON_PAGES)
def test_each_tab_has_skeleton_markup(path, marker_class):
    html = path.read_text(encoding="utf-8")
    assert marker_class in html, (
        f"{path.name} is missing skeleton markup ({marker_class})."
    )
    # Skeleton must have multiple shimmer primitives — empty boxes don't
    # convey "the real layout is forming".
    primitive_count = sum(
        html.count(cls)
        for cls in ("skeleton-bar", "skeleton-line", "skeleton-pill", "skeleton-orb")
    )
    assert primitive_count >= 4, (
        f"{path.name} skeleton needs ≥4 shimmer primitives to read as a layout, "
        f"found {primitive_count}."
    )


@pytest.mark.parametrize("path,_marker", SKELETON_PAGES)
def test_each_skeleton_container_uses_aria_busy(path, _marker):
    html = path.read_text(encoding="utf-8")
    assert 'aria-busy="true"' in html, (
        f"{path.name} skeleton container must declare aria-busy=\"true\" "
        "while loading."
    )


@pytest.mark.parametrize("path,_marker", SKELETON_PAGES)
def test_skeleton_visuals_are_aria_hidden(path, _marker):
    html = path.read_text(encoding="utf-8")
    # The decorative shimmer grid must be marked aria-hidden so screen
    # readers do not narrate the fake layout.
    skel_grids = re.findall(
        r'<div[^>]*class="[^"]*\bskeleton-grid[^"]*"[^>]*>',
        html,
    )
    # Taskboard's #tb-board doubles as the aria-busy container, so look
    # for at least one inner skeleton grid that's aria-hidden.
    hidden_grids = [g for g in skel_grids if 'aria-hidden="true"' in g]
    # Builder uses skeleton-card directly (no grid wrapper around editor
    # block); accept aria-hidden on the immediate decorative card.
    if not hidden_grids:
        hidden_grids = re.findall(
            r'<div[^>]*class="[^"]*\bskeleton-card[^"]*"[^>]*aria-hidden="true"',
            html,
        )
    assert hidden_grids, (
        f"{path.name} must mark its decorative skeleton block aria-hidden=\"true\"."
    )


# ── 3. JS clears the loading state when data arrives ───────────────────────
def test_dashboard_setLoading_toggles_aria_busy():
    js = DASHBOARD_JS.read_text(encoding="utf-8")
    # setLoading must drive aria-busy in addition to the visual hidden flip.
    assert "setAttribute(\"aria-busy\", \"true\")" in js
    assert "setAttribute(\"aria-busy\", \"false\")" in js


def test_library_show_hide_toggle_aria_busy():
    js = LIBRARY_JS.read_text(encoding="utf-8")
    # The show()/hide() helpers route the loading container through aria-busy.
    assert "aria-busy" in js
    assert "loadingEl" in js


def test_taskboard_renderBoard_clears_aria_busy():
    js = TASKBOARD_JS.read_text(encoding="utf-8")
    assert "renderBoard" in js
    # On first render, the static loading skeleton is replaced — aria-busy
    # must flip false so AT stops announcing "busy".
    assert 'setAttribute("aria-busy", "false")' in js


def test_builder_renderActiveEditor_clears_aria_busy():
    js = BUILDER_JS.read_text(encoding="utf-8")
    assert "renderActiveEditor" in js
    assert "renderPhases" in js
    # Both targets — phase rail and editor surface — must clear aria-busy.
    assert js.count('setAttribute("aria-busy", "false")') >= 2


# ── 4. Layout parity: skeleton count ≈ real-content count ──────────────────
def test_dashboard_skeleton_card_count_reasonable():
    """6 skeleton hw-cards on the dashboard is enough rows to convey 'a grid
    is forming' without flooding the viewport."""
    html = DASHBOARD_HTML.read_text(encoding="utf-8")
    count = html.count("skeleton-card--hw")
    assert 3 <= count <= 12, f"Expected 3–12 skeleton hw-cards, got {count}"


def test_library_skeleton_tile_count_reasonable():
    html = LIBRARY_HTML.read_text(encoding="utf-8")
    count = html.count("skeleton-card--tile")
    # Library normally shows ~7 subjects → 4–8 tile skeletons is the right range.
    assert 4 <= count <= 10, f"Expected 4–10 skeleton tiles, got {count}"


def test_taskboard_skeleton_column_count_reasonable():
    html = TASKBOARD_HTML.read_text(encoding="utf-8")
    count = html.count("skeleton-card--column")
    # Kanban: pinned Issues column + a few user columns → 3–6.
    assert 3 <= count <= 8, f"Expected 3–8 skeleton columns, got {count}"


# ── 5. Homework Preview is UNTOUCHED ───────────────────────────────────────
def test_preview_editor_js_unchanged_by_skeleton_work():
    """Hard rule: do not modify Homework Preview behavior/files."""
    src = PREVIEW_EDITOR_JS.read_text(encoding="utf-8")
    # The preview editor must not reference the new skeleton classes — we
    # don't want shimmer leaking into the actual Preview phase rendering.
    for cls in ("skeleton-bar", "skeleton-line", "skeleton-card", "skeleton-grid"):
        assert cls not in src, (
            f"frontend/js/editors/preview.js must not reference {cls}; "
            "Homework Preview is out of scope for the skeleton system."
        )


def test_preview_iframe_in_builder_is_not_wrapped_by_skeleton():
    """The live preview iframe is Homework Preview — keep it as-is."""
    html = BUILDER_HTML.read_text(encoding="utf-8")
    # Locate the preview-frame element.
    m = re.search(r'<iframe[^>]*id="preview-frame"[^>]*>', html)
    assert m, "preview-frame iframe disappeared from builder.html"

    iframe_tag = m.group(0)
    # The iframe itself must NOT be wrapped in our skeleton system.
    assert "skeleton" not in iframe_tag

    # Make sure the surrounding preview-panel section isn't carrying
    # aria-busy / skeleton markup either.
    panel_match = re.search(
        r'<section class="preview-panel"[^>]*id="preview-panel"[^>]*>.*?</section>',
        html,
        flags=re.S,
    )
    assert panel_match, "preview-panel <section> disappeared from builder.html"
    panel_html = panel_match.group(0)
    assert "skeleton-grid" not in panel_html
    assert "skeleton-card" not in panel_html


def test_runtime_preview_iframe_target_not_skeleton_wrapped():
    """The preview-frame loads /api/preview/<id>/ HTML — sanity-check that
    builder.html doesn't accidentally inject skeleton markup inside it."""
    html = BUILDER_HTML.read_text(encoding="utf-8")
    # preview-frame is a self-closing iframe; there must be NO sibling DIV
    # with skeleton-card on the same line / adjacent to it.
    iframe_block = re.search(
        r'<section class="preview-panel".*?</section>', html, flags=re.S
    )
    assert iframe_block
    assert "skeleton" not in iframe_block.group(0)


# ── 6. 500ms minimum-display floor (prevents skeleton flash) ───────────────
SKELETON_FLOOR_JS = [
    pytest.param(DASHBOARD_JS, id="dashboard"),
    pytest.param(LIBRARY_JS, id="library"),
    pytest.param(TASKBOARD_JS, id="taskboard"),
    pytest.param(BUILDER_JS, id="builder"),
]


@pytest.mark.parametrize("path", SKELETON_FLOOR_JS)
def test_skeleton_min_floor_constant_present(path):
    """Every loading controller defines a SKELETON_MIN_MS constant so the
    skeleton stays on screen long enough to read as a loading state, even
    when the API resolves in <1 frame."""
    js = path.read_text(encoding="utf-8")
    assert "SKELETON_MIN_MS" in js, (
        f"{path.name} must declare a SKELETON_MIN_MS constant to floor "
        "the skeleton display time."
    )
    # The floor must be at least 250ms (less than that won't register
    # visually) and at most 1500ms (longer than that feels sluggish).
    m = re.search(r"SKELETON_MIN_MS\s*=\s*(\d+)", js)
    assert m, f"{path.name}: cannot extract SKELETON_MIN_MS numeric value"
    floor_ms = int(m.group(1))
    assert 250 <= floor_ms <= 1500, (
        f"{path.name}: SKELETON_MIN_MS={floor_ms} is outside the "
        "sensible 250–1500ms range."
    )


@pytest.mark.parametrize("path", SKELETON_FLOOR_JS)
def test_skeleton_floor_helper_present(path):
    """The floor must be implemented via an awaitable helper (not just a
    constant) so loaders can `await waitSkeletonFloor()` before swapping
    real content in."""
    js = path.read_text(encoding="utf-8")
    assert "waitSkeletonFloor" in js, (
        f"{path.name}: waitSkeletonFloor() helper missing. Define one that "
        "returns a Promise resolving once SKELETON_MIN_MS has elapsed."
    )
    # The helper must actually use the constant.
    assert "SKELETON_MIN_MS - elapsed" in js or "SKELETON_MIN_MS-elapsed" in js, (
        f"{path.name}: floor helper should compute remaining time via "
        "(SKELETON_MIN_MS - elapsed)."
    )


@pytest.mark.parametrize("path", SKELETON_FLOOR_JS)
def test_skeleton_floor_awaited_before_swap(path):
    """The loader must `await waitSkeletonFloor()` before flipping to
    real content; otherwise the floor is dead code."""
    js = path.read_text(encoding="utf-8")
    assert "await waitSkeletonFloor()" in js, (
        f"{path.name}: waitSkeletonFloor() is declared but never awaited."
    )


# ── 7. fade-up / scroll reveal still works for real content ────────────────
def test_existing_reveal_animation_still_present_dashboard():
    """The dashboard's IntersectionObserver-driven .is-visible reveal for
    .hw-card / .dash-stat-card must keep working after the skeleton refactor."""
    js = DASHBOARD_JS.read_text(encoding="utf-8")
    assert "IntersectionObserver" in js
    assert "is-visible" in js
    assert "_observeReveals" in js


def test_skeleton_does_not_use_is_visible_class():
    """Skeleton placeholders must NOT trigger the dashboard's fade-up
    IntersectionObserver — that observer keys on .hw-card / .dash-stat-card,
    neither of which is allowed on a skeleton placeholder."""
    for path in (DASHBOARD_HTML, LIBRARY_HTML, TASKBOARD_HTML, BUILDER_HTML):
        html = path.read_text(encoding="utf-8")
        # Find every skeleton-card occurrence; ensure none of those nodes
        # also carry .hw-card / .dash-stat-card.
        for m in re.finditer(r'class="([^"]*\bskeleton-card\b[^"]*)"', html):
            classes = m.group(1)
            assert "hw-card" not in classes, (
                f"{path.name}: skeleton-card must not also carry .hw-card "
                f"(would re-trigger fade-up observer)."
            )
            assert "dash-stat-card" not in classes, (
                f"{path.name}: skeleton-card must not also carry .dash-stat-card."
            )
