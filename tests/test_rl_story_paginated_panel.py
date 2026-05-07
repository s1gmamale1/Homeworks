"""Real-Life Challenge story-panel pagination regression tests.

Guards: pre-fix, the RL story panel was a fixed-height vertical-scroll
container that got `display: none`'d when the student moved from the
"Boshlash" (Start) screen to question 1. Result on `HW-20260505-006`:
the lab quality-control passage students needed for reference was
hidden the moment they began answering. Two paths force-set
`display: none` (rlShowQuestion + rlHandleAction) and one force-set
`flex: 1` on phase entry (overriding any CSS sizing).

Each test asserts the BAD pre-fix state cannot return:
- Story panel must NOT be hidden via inline `style.display = 'none'`
  on the question or start-button transitions.
- Story panel CSS must declare bounded height + horizontal scroll-snap
  (paginated layout) instead of vertical scroll.
- Page-indicator container must exist in the rendered template.
- Pagination JS (page-builder + drag handler + dot updater) must be
  wired so the runtime turns a single passage into a swipable
  multi-page panel.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "server" / "template" / "perfect_homework.html"


@pytest.fixture(scope="module")
def template_html() -> str:
    return TEMPLATE_PATH.read_text(encoding="utf-8")


# ── Negative assertions: pre-fix code cannot return ─────────────────────────


def test_story_panel_no_display_none_on_question_show(template_html):
    """rlShowQuestion previously had:
        const story = document.getElementById('rl-story-section');
        if (story) story.style.display = 'none';
    That broke the "passage stays alongside question" contract.
    """
    # Cover both single- and double-quoted JS strings.
    bad_patterns = [
        r"story\.style\.display\s*=\s*'none'",
        r'story\.style\.display\s*=\s*"none"',
    ]
    for pat in bad_patterns:
        assert not re.search(pat, template_html), (
            f"Pre-fix line `story.style.display = 'none'` is back. "
            f"The story panel must remain visible alongside the question."
        )


def test_story_panel_no_force_flex_one_on_phase_entry(template_html):
    """Phase-entry code previously force-set `story.style.flex = '1'` which
    overrode the new bounded-height CSS (`flex: 0 0 220px`) and let the
    story expand to fill the card again.
    """
    assert not re.search(
        r"story\.style\.flex\s*=\s*['\"]1['\"]",
        template_html,
    ), (
        "Pre-fix line `story.style.flex = '1'` is back. The CSS now bounds "
        "the panel via `flex: 0 0 220px`; do not override inline."
    )


# ── Positive assertions: post-fix layout is in place ────────────────────────


def test_story_panel_has_horizontal_pagination_css(template_html):
    """Story panel must declare horizontal scroll-snap and bounded width
    (each .rl-story-page = one snap target = one page)."""
    # Bounded panel height — the wrap uses `flex: 0 0 <bounded>` (no longer
    # `flex: 1`). Accept any explicit unit OR a clamp() expression so a
    # future tuning pass can adjust the value without breaking the test.
    assert re.search(
        r"\.rl-story-wrap\s*\{[^}]*flex:\s*0\s+0\s+(?:\d+(?:px|vh|%)|clamp\()",
        template_html,
    ), (
        ".rl-story-wrap must declare a bounded `flex: 0 0 <NNNpx|NNvh|NN%|clamp(...)>` "
        "(panel height must NOT be `flex: 1` — that lets it expand to fill "
        "the card and breaks the paginated panel layout)."
    )
    # Horizontal scroll-snap container.
    assert "scroll-snap-type: x mandatory" in template_html, (
        ".rl-story-body must declare `scroll-snap-type: x mandatory` "
        "for paginated swipe behavior."
    )
    # Each page snaps to start of the viewport.
    assert "scroll-snap-align: start" in template_html, (
        ".rl-story-page must declare `scroll-snap-align: start`."
    )
    # Pages are full-width flex children — exactly one fills the panel.
    assert re.search(r"\.rl-story-page\s*\{[^}]*flex:\s*0\s+0\s+100%", template_html), (
        ".rl-story-page must use `flex: 0 0 100%` so each snaps to fill."
    )


def test_story_panel_has_page_indicator_dots_html(template_html):
    """The `<div id="rl-story-dots">` indicator container must be present
    between the story panel and the question stack."""
    assert re.search(
        r'<div\s+class="rl-story-dots"\s+id="rl-story-dots"[^>]*>',
        template_html,
    ), (
        "Page-indicator container `<div class=\"rl-story-dots\" id=\"rl-story-dots\">` "
        "must exist in the RL card."
    )
    # Dots CSS hides the row when there's only one page (or zero).
    assert re.search(
        r'\.rl-story-dots\[data-pages="1"\]',
        template_html,
    ), "Single-page dot suppression CSS must be present."


def test_story_renderer_has_pagination_js(template_html):
    """rlRenderStory() must build pages incrementally and bind drag + dot
    handlers. Smoke-level check — Playwright would test runtime behavior;
    this guards the wiring."""
    # Pagination algorithm — paragraph-based with overflow check.
    assert "startNewPage" in template_html, (
        "rlRenderStory must define an internal startNewPage() helper."
    )
    assert "scrollHeight > panelHeight" in template_html, (
        "Pagination must compare scrollHeight to panel height to decide breaks."
    )
    # Dot updater binds to the scroll event exactly once.
    assert "__rlDotsBound" in template_html, (
        "Dot-updater scroll listener must be guarded by __rlDotsBound flag "
        "(prevents duplicate listeners on re-entry)."
    )
    # Drag-to-pan handler (mouse) wired and idempotent.
    assert "__rlDragBound" in template_html, (
        "Drag handler must be guarded by __rlDragBound flag."
    )
    # The drag handler must NOT swallow text selection — verify cursor css
    # toggles from grab to grabbing during a drag.
    assert ".rl-story-body.rl-dragging" in template_html, (
        "Dragging state CSS class .rl-dragging must be defined."
    )


def test_rl_handle_action_no_longer_hides_story_on_start(template_html):
    """rlHandleAction's start-button branch previously fade-out'd and
    display:none'd the story before showing question 1. New design just
    calls rlShowQuestion(0) directly — the story stays put."""
    # Find the rlHandleAction function's story-screen branch.
    m = re.search(
        r"function\s+rlHandleAction\s*\(\)\s*\{(.{0,1500}?)\bif\s*\(stage6State\.screen\s*===\s*['\"]closure['\"]",
        template_html,
        re.DOTALL,
    )
    assert m, (
        "Couldn't locate rlHandleAction's story-screen branch — test needs "
        "an update if the function was renamed/restructured."
    )
    body = m.group(1)
    # The branch must NOT toggle story display/opacity anymore.
    assert "story.style.display" not in body, (
        "rlHandleAction's story branch must not touch story.style.display "
        "(panel must remain visible)."
    )
    assert "rlShowQuestion(0)" in body, (
        "rlHandleAction's story branch must transition to rlShowQuestion(0)."
    )


# ── Integration via injector — render path produces all of the above ───────


def test_injector_renders_template_with_pagination_classes(tmp_path, monkeypatch):
    """End-to-end: feed an RL story through the injector and confirm the
    rendered HTML carries the pagination markers. Mirrors how a live
    /h/{id} render would behave."""
    from server.services import injector

    sample_content = {
        "meta": {"title": "Stress test", "subject_display": "math"},
        "real_life": {
            "badge": "VAZIFA",
            "story": "Para one.\n\nPara two.\n\nPara three.",
            "q1": {"prompt": "?", "ans": "1", "fb": ""},
            "q2": {"prompt": "?", "ans": "2", "fb": ""},
            "q3": {"prompt": "?", "ans": "3", "fb": ""},
            "q4": {"prompt": "?", "ans": "4", "fb": ""},
            "q5": {"prompt": "?", "ans": "5", "fb": "", "open": True},
            "q6": {"prompt": "?", "ans": "6", "fb": ""},
            "endTitle": "Done",
            "endSub": "Done",
        },
    }
    rendered = injector.inject(
        sample_content,
        runtime_context={"hw_id": "HW-TEST-001"},
    )
    assert "rl-story-page" in rendered
    assert 'id="rl-story-dots"' in rendered
    assert "scroll-snap-type: x mandatory" in rendered
    assert "Para one." in rendered  # story actually injected
