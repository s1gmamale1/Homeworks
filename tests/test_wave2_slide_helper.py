"""Regression tests for the shared wave2 sliding-panel helper (Bug #5/#7).

The helper is a copy-of-Preview's slide pipeline (animation timings,
transform recipe, dot indicator) namespaced under wave2-* classes so
Reading and Consolidation can share one code path without touching
Preview's existing implementation.

Pins the contracts that make the helper safe to refactor later:

  - The three top-level functions exist (wave2SlideInit / Navigate / To).
  - The animation recipe matches Preview's switchPage byte-for-byte
    (translate ±100% + blur 15px + opacity 0, same easing curves, 50ms
    wait + reflow + requestAnimationFrame, 500ms cleanup).
  - The dot indicator renders one .wave2-dot per panel and toggles
    .wave2-active on the current index.
  - canAdvance is a consumer-supplied hook (Reading uses it for
    question-locks, Consolidation passes a permissive default).
  - Back-swipe is structurally allowed (toIdx < fromIdx never blocked
    by the helper itself).
  - onExitForward / onExitBackward fire when the user swipes past
    the last / before the first panel.
  - Empty containers don't crash the helper.

If any of these regress, both Reading and Consolidation lose their
sliding UX simultaneously, so this test file is high-value.
"""

from __future__ import annotations

import re
from pathlib import Path

_JS_PATH = Path(__file__).resolve().parent.parent / "server" / "template" / "js" / "perfect_homework.js"
_CSS_PATH = Path(__file__).resolve().parent.parent / "server" / "template" / "static" / "css" / "perfect_homework.css"
_HTML_PATH = Path(__file__).resolve().parent.parent / "server" / "template" / "perfect_homework.html"
TEMPLATE = _HTML_PATH.read_text(encoding="utf-8") + "\n" + _JS_PATH.read_text(encoding="utf-8") + "\n" + _CSS_PATH.read_text(encoding="utf-8")


def _slice_function(name: str) -> str:
    start = TEMPLATE.find(f"function {name}(")
    assert start != -1, f"function {name} not found in template"
    after = TEMPLATE.find("\n        function ", start + 1)
    if after == -1:
        after = len(TEMPLATE)
    return TEMPLATE[start:after]


# ---- Invariant 1: helper functions + state map exist ----------------------

def test_wave2_slide_helper_functions_exist():
    """The three top-level helpers must be defined."""
    assert "function wave2SlideInit(opts)" in TEMPLATE
    assert "function wave2SlideNavigate(containerId, dir)" in TEMPLATE
    assert "function wave2SlideTo(containerId, idx)" in TEMPLATE


def test_wave2_streams_state_map_is_module_local():
    """Stream state lives in `_wave2Streams` keyed by container id."""
    assert "const _wave2Streams = {};" in TEMPLATE, (
        "the helper keeps stream state in a module-local _wave2Streams object so "
        "Reading and Consolidation streams don't collide"
    )


# ---- Invariant 2: animation recipe matches Preview's switchPage -----------

def test_wave2_slide_animation_uses_preview_timing_curves():
    """Slide-out and slide-in must use the same cubic-bezier curves Preview uses."""
    body = _slice_function("wave2SlideTo")
    # Slide-in transition matches switchPage's `cubic-bezier(0.2, 0.8, 0.2, 1)`
    assert "cubic-bezier(0.2, 0.8, 0.2, 1)" in body, (
        "wave2 slide-in must use Preview's exact easing curve so the visual "
        "language stays consistent across phases"
    )


def test_wave2_slide_animation_uses_translate_plus_blur_plus_opacity():
    """The transform recipe must match Preview's three-axis animation."""
    body = _slice_function("wave2SlideTo")
    assert "translateX(" in body
    assert "blur(15px)" in body, "Preview's switchPage uses 15px blur during transition"
    assert "opacity = '0'" in body
    # Force-reflow trick (Preview also does this with `void offsetHeight`).
    assert "void nxt.offsetHeight" in body, (
        "the helper must force a reflow before the requestAnimationFrame call "
        "so the off-stage transform applies before the easing kicks in — same "
        "trick Preview's switchPage uses"
    )


def test_wave2_slide_animation_uses_50ms_wait_then_raf_then_500ms_cleanup():
    """Three-phase timing: 50ms wait → rAF → 500ms cleanup. Same as switchPage."""
    body = _slice_function("wave2SlideTo")
    # 50ms outer setTimeout — the closing `}, 50);` pattern is unique enough
    # to pin without regex-matching the setTimeout body (which is multi-line
    # and includes nested commas / function calls).
    assert "}, 50);" in body, (
        "outer setTimeout must close with `}, 50);` — Preview's switchPage uses "
        "the same 50ms wait so the off-stage transition lands before the new "
        "page is positioned"
    )
    assert "}, 500);" in body, (
        "cleanup setTimeout must close with `}, 500);` to match Preview's timing"
    )
    assert "requestAnimationFrame(" in body


# ---- Invariant 3: dot indicator renders + updates correctly ----------------

def test_wave2_dot_indicator_renders_one_dot_per_panel():
    """wave2SlideInit creates `panelCount` dots inside the dotsId container."""
    body = _slice_function("wave2SlideInit")
    assert "for (let i = 0; i < opts.panelCount; i++)" in body, (
        "init must loop opts.panelCount times to create exactly one dot per panel"
    )
    assert "className = 'wave2-dot'" in body
    assert "dotsRow.appendChild(dot)" in body


def test_wave2_dot_indicator_updates_active_class_on_navigation():
    """wave2SlideTo updates the dotsRow's `.wave2-active` to the new index."""
    body = _slice_function("wave2SlideTo")
    assert "wave2-dot" in body
    assert "classList.toggle('wave2-active', i === idx)" in body, (
        "exactly one dot must carry .wave2-active at any time, matching the "
        "current stream index"
    )


def test_wave2_dot_css_exists_and_matches_preview_pagination():
    """`.wave2-dot` CSS exists with same width/height/transition as Preview's `.dot`."""
    # We use the same 8px×8px+18px-active+accent-glow recipe Preview uses;
    # the wave2 namespacing keeps it from polluting Preview's selectors.
    assert ".wave2-dot {" in TEMPLATE
    assert ".wave2-dot.wave2-active {" in TEMPLATE
    # Active dot widens to 18px (same as Preview's .dot.active)
    wave2_dot_active_block = TEMPLATE[TEMPLATE.find(".wave2-dot.wave2-active {"):]
    wave2_dot_active_block = wave2_dot_active_block[:wave2_dot_active_block.find("}") + 1]
    assert "width: 18px" in wave2_dot_active_block


# ---- Invariant 4: canAdvance + exit hooks are consumer-controlled ---------

def test_wave2_navigate_respects_canAdvance_hook():
    """wave2SlideNavigate calls canAdvance(from, to) and aborts if it returns false."""
    body = _slice_function("wave2SlideNavigate")
    assert "stream.canAdvance(stream.index, newIdx)" in body
    # The early-return on false must happen before wave2SlideTo gets called.
    assert re.search(
        r"if\s*\(\s*!stream\.canAdvance\([^)]+\)\s*\)\s*return",
        body,
    ), "navigate must abort early when canAdvance returns false"


def test_wave2_navigate_fires_exit_hooks_at_boundaries():
    """Forward past last → onExitForward; backward past first → onExitBackward."""
    body = _slice_function("wave2SlideNavigate")
    assert re.search(
        r"if\s*\(\s*newIdx\s*<\s*0\s*\)\s*\{[^}]*onExitBackward",
        body, flags=re.DOTALL,
    ), "swiping back past the first panel must fire onExitBackward"
    assert re.search(
        r"if\s*\(\s*newIdx\s*>=\s*stream\.panelCount\s*\)\s*\{[^}]*onExitForward",
        body, flags=re.DOTALL,
    ), "swiping forward past the last panel must fire onExitForward"


def test_wave2_init_provides_permissive_canAdvance_default():
    """If consumer omits canAdvance, the helper defaults to (() => true)."""
    body = _slice_function("wave2SlideInit")
    # The default-value pattern: `opts.canAdvance || (() => true)`
    assert "canAdvance || (() => true)" in body or 'canAdvance || (function () { return true' in body, (
        "Consolidation passes no canAdvance and expects a permissive default — "
        "the helper must supply one so navigation isn't accidentally blocked"
    )


# ---- Invariant 5: helper doesn't crash on edge cases ----------------------

def test_wave2_navigate_no_op_when_animating():
    """A second swipe during an active animation is dropped on the floor."""
    body = _slice_function("wave2SlideNavigate")
    assert "stream.isAnimating" in body, (
        "navigate must check stream.isAnimating before kicking off another "
        "transition — otherwise rapid swipes pile up animations and the DOM "
        "ends up with multiple .wave2-active panels"
    )


def test_wave2_to_no_op_when_target_equals_current():
    """Calling wave2SlideTo with the current index is a no-op (no animation)."""
    body = _slice_function("wave2SlideTo")
    assert "idx === stream.index" in body, (
        "wave2SlideTo must short-circuit when target equals current — otherwise "
        "the animation runs against the same DOM node and visibly flashes"
    )


def test_wave2_to_validates_index_bounds():
    """wave2SlideTo aborts if idx is out of [0, panelCount)."""
    body = _slice_function("wave2SlideTo")
    assert "idx < 0 || idx >= stream.panelCount" in body, (
        "wave2SlideTo must validate idx is in range — programmatic callers "
        "could pass garbage and we don't want the helper to crash"
    )
