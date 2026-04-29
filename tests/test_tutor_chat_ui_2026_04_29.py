"""
Regression guards for the 2026-04-29 tutor chat UI cleanup.

Two scope-bounded changes (no chat redesign yet — that lands in a
follow-up once the user provides design references):

1. The tutor's per-chat light/dark toggle is removed. The navbar
   toggle (frontend/js/theme.js) is the single source of truth; the
   runtime player consumes the saved value at boot and resyncs via
   the cross-document `storage` event.

2. Open / close is now class-driven (`.nets-tutor-collapsed` on the
   wrapper) with a real outbound transition + `prefers-reduced-motion`
   honoured. The pre-fix code toggled `panel.hidden` on/off which
   meant the panel just disappeared with no animation.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parent.parent
TEMPLATE = REPO_ROOT / "server" / "template" / "perfect_homework.html"


def _runtime() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Theme toggle removal
# ---------------------------------------------------------------------------


def test_tutor_theme_toggle_button_is_gone():
    """The static `<button id="nets-tutor-theme-toggle">` and the JS
    `themeToggle` ref + click handler must all be gone."""
    html = _runtime()
    assert 'id="nets-tutor-theme-toggle"' not in html, (
        "tutor still ships its own theme toggle button"
    )
    assert "nets-tutor-theme-toggle" not in html, (
        "all references (id, JS getElementById, CSS selector) to the "
        "tutor-local theme toggle must be removed"
    )
    # The orphan ref pattern that used to exist in the JS DOM block.
    assert "themeToggle" not in html, (
        "leftover `themeToggle` JS ref means the click handler may "
        "still be wired to a now-missing element"
    )


def test_tutor_storage_sync_still_present():
    """The CROSS-DOCUMENT theme sync must survive the cleanup —
    that's how the navbar toggle reaches the runtime player. The
    audit explicitly called this out as worth keeping."""
    html = _runtime()
    assert "function applyStoredTheme" in html, (
        "tutor must keep applyStoredTheme() — the read-only theme "
        "mirror that consumes the navbar toggle's localStorage value"
    )
    # Must subscribe to the storage event so a toggle in a sibling
    # tab updates the runtime player.
    assert re.search(
        r"addEventListener\(\s*['\"]storage['\"]",
        html,
    ), "tutor must still listen for the cross-document `storage` event"
    # And the saved value must drive `data-theme` on <html>.
    assert "setAttribute('data-theme'" in html, (
        "tutor must still apply `data-theme` from the saved value at boot"
    )


def test_tutor_close_button_still_pinned_right():
    """Removing the toggle stole `margin-left: auto` from the header
    layout. Close button needs to inherit it so the close affordance
    stays at the right edge."""
    html = _runtime()
    block = re.search(
        r"#nets-tutor-close\s*\{([^}]+)\}",
        html,
    )
    assert block, "missing #nets-tutor-close CSS block"
    assert "margin-left: auto" in block.group(1), (
        "#nets-tutor-close must claim `margin-left: auto` now that "
        "the theme toggle is no longer pushing it to the right edge"
    )


# ---------------------------------------------------------------------------
# Open / close animation
# ---------------------------------------------------------------------------


def test_open_close_uses_class_based_transition():
    """The wrapper's `.nets-tutor-collapsed` class is now the source
    of truth for open/closed. A CSS rule on
    `:not(.nets-tutor-collapsed) #nets-tutor-panel` must define the
    open state so the panel transitions in/out instead of snapping."""
    html = _runtime()
    assert re.search(
        r"#nets-ai-tutor:not\(\.nets-tutor-collapsed\)\s+#nets-tutor-panel\s*\{",
        html,
    ), (
        "missing the `:not(.nets-tutor-collapsed) #nets-tutor-panel` "
        "selector that drives the open transition"
    )
    assert re.search(
        r"\.nets-tutor-collapsed\s+#nets-tutor-panel\s*\{",
        html,
    ), (
        "missing the `.nets-tutor-collapsed #nets-tutor-panel` "
        "selector that drives the closed state"
    )


def test_panel_has_open_close_transition_props():
    """The closed-state block must transition opacity+transform+
    visibility so the close direction animates rather than snapping."""
    html = _runtime()
    closed = re.search(
        r"\.nets-tutor-collapsed\s+#nets-tutor-panel\s*\{([^}]+)\}",
        html,
    )
    assert closed, "missing closed-state rule"
    body = closed.group(1)
    assert "opacity: 0" in body
    assert "transform: scale" in body, (
        "closed panel must scale down (matches open's transform-origin)"
    )
    assert "transition" in body, (
        "closed-state must declare a `transition` so the close "
        "direction animates"
    )


def test_tutor_panel_keeps_fab_corner_anchor():
    """The panel is absolutely positioned from the fixed tutor wrapper.
    A later `position: relative` override lets the panel/FAB drift away
    from the bottom-right anchor and can make the widget appear in the
    middle of the screen."""
    html = _runtime()
    panel = re.search(r"#nets-tutor-panel\s*\{([^}]+)\}", html)
    assert panel, "missing #nets-tutor-panel base CSS block"
    assert "position: absolute" in panel.group(1)
    assert "#nets-tutor-panel { position: relative; }" not in html


def test_panel_respects_prefers_reduced_motion():
    """A11y: users with motion sensitivity see no scale animation."""
    html = _runtime()
    assert re.search(
        r"@media\s*\(\s*prefers-reduced-motion:\s*reduce\s*\)\s*\{[^}]*#nets-tutor-panel",
        html,
        re.DOTALL,
    ), (
        "tutor panel must collapse its transitions inside a "
        "`@media (prefers-reduced-motion: reduce)` block"
    )


def test_open_close_js_no_longer_toggles_panel_hidden():
    """The pre-fix code wrote `panel.hidden = true/false` inside
    open/closePanel. That short-circuits CSS transitions because
    `[hidden]` removes the element from layout instantly. The post-
    fix code drops the attribute once on first open and lets class
    state drive everything afterwards."""
    html = _runtime()
    # Forbid the runtime assignments that nuke the close transition.
    assert "panel.hidden = true" not in html, (
        "panel.hidden = true short-circuits the close transition"
    )
    assert "panel.hidden = false" not in html, (
        "panel.hidden = false short-circuits the open transition"
    )
    # The one-time `removeAttribute('hidden')` is fine because that's
    # how we shed the static fallback on first user interaction.
    assert "panel.removeAttribute('hidden')" in html, (
        "open path must drop the `hidden` attribute exactly once "
        "so it can't keep overriding the class-based cascade"
    )


def test_open_close_class_remains_source_of_truth():
    """Both functions must keep flipping `nets-tutor-collapsed` on
    the wrapper — that's the class the new CSS rules key off of."""
    html = _runtime()
    assert "root.classList.remove('nets-tutor-collapsed')" in html, (
        "openPanel must remove .nets-tutor-collapsed"
    )
    assert "root.classList.add('nets-tutor-collapsed')" in html, (
        "closePanel must add .nets-tutor-collapsed"
    )
    # The `aria-expanded` semantics must follow.
    assert "aria-expanded', 'true'" in html
    assert "aria-expanded', 'false'" in html


# ---------------------------------------------------------------------------
# End-to-end: served preview keeps the right shape
# ---------------------------------------------------------------------------


def test_served_preview_drops_theme_toggle_keeps_panel_anchors(client, sample_homework):
    r = client.get(f"/api/homeworks/{sample_homework['id']}/preview")
    assert r.status_code == 200
    body = r.text

    # Toggle gone
    assert 'id="nets-tutor-theme-toggle"' not in body

    # Anchor + control elements still present
    for el_id in ("nets-tutor-fab",
                  "nets-tutor-panel",
                  "nets-tutor-close",
                  "nets-tutor-avatar",
                  "nets-tutor-phase-badge"):
        assert f'id="{el_id}"' in body, f"missing #{el_id} after cleanup"
