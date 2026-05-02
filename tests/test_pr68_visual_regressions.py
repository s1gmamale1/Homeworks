from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).parent.parent
RUNTIME = ROOT / "server" / "template" / "perfect_homework.html"
APP_CSS = ROOT / "frontend" / "css" / "app.css"
AQ_EDITOR = ROOT / "frontend" / "js" / "editors" / "games" / "adaptive-quiz.js"
INDEX_HTML = ROOT / "frontend" / "index.html"
I18N = ROOT / "frontend" / "js" / "i18n" / "strings.js"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _css_block(source: str, selector: str) -> str:
    match = re.search(re.escape(selector) + r"\s*\{(?P<body>[^}]*)\}", source)
    assert match, f"missing CSS block for {selector}"
    return match.group("body")


def test_preview_panel_hugs_content_instead_of_forcing_blank_scroll():
    html = _read(RUNTIME)

    panel = _css_block(html, ".panel-card")
    assert "height: auto" in panel
    assert "min-height: min(360px, 70vh)" in panel
    assert "max-height: 82vh" in panel
    assert re.search(r"(?m)^\s*height:\s*82vh\s*;", panel) is None

    content = _css_block(html, ".content-area")
    assert "flex: 1 1 auto" in content
    assert "padding-bottom: 8px" in content
    assert "overscroll-behavior: contain" in content

    assert "function updatePanelOverflowHint()" in html
    assert "card.classList.toggle('has-overflow', overflow)" in html
    assert "container.addEventListener('scroll', updatePanelOverflowHint" in html
    assert "window.addEventListener('resize', updatePanelOverflowHint)" in html
    assert "container.addEventListener('load', updatePanelOverflowHint, true)" in html


def test_preview_overflow_hint_is_css_gated_by_real_overflow():
    html = _read(RUNTIME)

    hint = _css_block(html, ".panel-card::after")
    assert 'content: ""' in hint
    assert "pointer-events: none" in hint
    assert "opacity: 0" in hint
    assert "linear-gradient(180deg, transparent, var(--surface))" in hint

    active_hint = _css_block(html, ".panel-card.has-overflow::after")
    assert "opacity: 0.85" in active_hint


def test_runtime_dark_mode_controls_have_visibility_overrides():
    html = _read(RUNTIME)
    selectors = [
        '[data-theme="dark"] .boss-input',
        '[data-theme="dark"] .boss-hint-btn',
        '[data-theme="dark"] .screen-reading-input',
        '[data-theme="dark"] .screen-reading-btn',
        '[data-theme="dark"] .screen-cons-toggle',
        '[data-theme="dark"] .aq-textarea',
        '[data-theme="dark"] .aq-drop',
        '[data-theme="dark"] .gb-wc-textarea',
        '[data-theme="dark"] .gb-mb-label',
        '[data-theme="dark"] .gb-pl-cell',
        '[data-theme="dark"] .gb-mm-front-face',
        '[data-theme="dark"] .rl-capture-btn',
        '[data-theme="dark"] .quote-author-chip',
        '[data-theme="dark"] .quote-author-chip--global',
    ]

    for selector in selectors:
        block = _css_block(html, selector)
        assert any(prop in block for prop in ("background:", "color:", "border-color:")), selector


def test_runtime_caps_tall_preview_media_inside_panels():
    html = _read(RUNTIME)

    img_block = _css_block(html, ".block-image img")
    svg_block = _css_block(html, ".block-svg svg")
    assert "max-height: 56vh" in img_block
    assert "object-fit: contain" in img_block
    assert "max-height: 56vh" in svg_block


def test_reading_runtime_paginates_and_requires_checkpoint_answer():
    html = _read(RUNTIME)

    assert 'id="reading-progress"' in html
    assert 'id="reading-status"' in html
    assert "function readingBuildPages" in html
    assert "function readingIsComplete" in html
    assert "function updateReadingContinueState" in html
    assert "READING.passage || READING.text || ''" in html
    assert "readingState.answered[i] = true" in html
    # Updated for the segment-aware reading refactor (PR #127 Bug #3): the
    # checkpoint-completeness guard inside finishReading now takes a `force`
    # parameter so edge-swipe phase-skip can bypass the lock. The guard is
    # still in place — just gated on `!force && ...` — and the geometric
    # checkpoint→page mapping is still called as a legacy fallback when the
    # segment-aware lookup misses.
    assert "if (!force && !readingIsComplete(checkpoints))" in html
    assert "readingCheckpointPage(firstMissing" in html
    assert "tier: 'HARD'" in html
    assert "tier: 'EASY'" not in html[html.index("function renderReading"):html.index("function renderConsolidation")]


def test_adaptive_quiz_builder_has_grouped_grading_ui():
    js = _read(AQ_EDITOR)
    css = _read(APP_CSS)

    assert "function renderGradingBlock" in js
    # Wave V.2 (PR runtime-ux-polish 2026-04-30): the grading block
    # moved from a standalone <section class="aq-grading"> to a
    # <div class="aq-grading"> nested inside the outer
    # <section class="aq-section aq-section--answer"> wrapper.
    assert 'class="aq-grading"' in js
    assert 'aq-section--answer' in js
    assert "Allow AI fallback" in js
    assert "Custom rubric copy" in js
    assert "Accepted examples" in js
    assert "aq-preview-tag" in js
    assert "aq-preview-empty" in js
    assert "answer grading below" not in js.lower()

    assert ".aq-grading" in css
    assert ".aq-grid" in css
    assert ".aq-toggle" in css
    assert ".aq-preview" in css
    assert ".aq-card .fc-meta-row.aq-meta-row" in css
    # Numbered sections must each be styled.
    assert ".aq-section" in css
    assert ".aq-section-eyebrow" in css


def test_adaptive_quiz_question_host_is_not_a_paragraph():
    # RichField wraps prompt content in <p>...</p>. Hosting that inside a
    # <p id="gb-aq-question"> triggers HTML5 auto-closing of the outer <p>
    # and hoists the prompt out of .aq-problem, hiding the answer textarea
    # (regression 2026-05-02).
    html = _read(RUNTIME)

    paragraph_host = re.search(
        r"<p\s[^>]*\bid\s*=\s*['\"]gb-aq-question['\"][^>]*>",
        html,
    )
    assert paragraph_host is None, (
        "AQ question host must not be a <p>; RichField's <p> output "
        "is not a legal child of <p>."
    )

    div_host = re.search(
        r"<div\s[^>]*\bid\s*=\s*['\"]gb-aq-question['\"][^>]*>",
        html,
    )
    assert div_host is not None, "missing <div id='gb-aq-question'> host"

    wrapped = re.search(
        r"<div\s[^>]*\bclass\s*=\s*['\"][^'\"]*\baq-problem\b[^'\"]*['\"][^>]*>"
        r"[\s\S]*?<div\s[^>]*\bid\s*=\s*['\"]gb-aq-question['\"][^>]*>"
        r"[\s\S]*?</div>\s*</div>",
        html,
    )
    assert wrapped is not None, (
        "<div id='gb-aq-question'> must remain inside <div class='aq-problem'>"
    )


def test_every_screen_div_carries_the_screen_class():
    # Every <div id="screen-..."> must carry the `screen` class so the
    # runtime's many `document.querySelectorAll('.screen')` cleanup loops
    # actually find it. Missing the class on screen-5 left the game-break
    # screen un-deactivated when navigation moved past it, allowing it to
    # overlap subsequent phases and swallow pointer events from the AQ
    # answer textarea inside (regression 2026-05-02).
    html = _read(RUNTIME)

    matches = re.findall(
        r'<div\s+id\s*=\s*"(screen-[\w-]+)"\s*([^>]*)>',
        html,
    )
    assert matches, "no screen div definitions found in runtime template"

    missing = []
    for screen_id, attrs in matches:
        cls = re.search(r'\bclass\s*=\s*"([^"]*)"', attrs)
        classes = (cls.group(1).split() if cls else [])
        if "screen" not in classes:
            missing.append(screen_id)

    assert not missing, (
        f"these screen divs are missing the `screen` class: {missing}; "
        "runtime navigation cleanup uses .screen as the enumeration selector"
    )


def test_aq_answer_card_padding_clicks_focus_the_textarea():
    # The ~10px gap between the "Javob" heading and the textarea border
    # used to land clicks on the parent <section class="aq-answer-card">,
    # not the textarea — students felt this as a dead band at the top of
    # the input (regression 2026-05-02). The runtime now forwards padding-
    # area clicks to the textarea while skipping interactive children.
    html = _read(RUNTIME)

    # The forwarder must be wired up on DOMContentLoaded so it is present
    # before the AQ phase first activates.
    assert "querySelector('.aq-answer-card')" in html, (
        "click forwarder must look up the answer card by class"
    )
    assert "getElementById('gb-aq-textarea')" in html, (
        "click forwarder must focus the AQ textarea"
    )

    # Skip clicks that already hit an interactive child so the upload
    # drop-zone, buttons, and the textarea itself keep working normally.
    skip = re.search(
        r"closest\(\s*['\"][^'\"]*\brole\s*=\s*\\?[\"']?button\\?[\"']?",
        html,
    )
    assert skip is not None, (
        "forwarder must bail on clicks that hit an interactive descendant "
        "(upload drop-zone uses role='button')"
    )


def test_wave2_slides_become_pointer_inert_when_parent_screen_is_inactive():
    # `.wave2-slide-page.wave2-active` declares its own `pointer-events: auto`
    # so the visible reading/consolidation page stays interactive. CSS
    # pointer-events doesn't cascade — when the parent screen is deactivated
    # (e.g. user navigates past reading into AQ), the slide is visually
    # hidden by the parent's opacity:0 but remains a click target at
    # position:absolute/inset:0, swallowing clicks meant for the now-active
    # screen's inputs (regression 2026-05-03 — surfaced as the AQ answer
    # textarea silently rejecting clicks on prod).
    html = _read(RUNTIME)

    # The defensive override must exist and target slides whose parent
    # screen lacks the `active` class.
    pattern = re.search(
        r"\.screen\s*:not\(\s*\.active\s*\)\s+\.wave2-slide-page\s*\{[^}]*"
        r"pointer-events\s*:\s*none\s*;",
        html,
    )
    assert pattern is not None, (
        ".screen:not(.active) .wave2-slide-page must force pointer-events:none "
        "so reading/consolidation slides cannot intercept clicks meant for the "
        "active screen's inputs"
    )


def test_adaptive_quiz_mobile_layout_stacks_at_640px():
    css = _read(APP_CSS)
    media = re.search(
        r"@media\s*\(max-width:\s*640px\)\s*\{(?P<body>[\s\S]*?)\n\}",
        css,
    )
    assert media, "missing 640px responsive block"
    body = media.group("body")
    assert ".aq-card .fc-meta-row.aq-meta-row" in body
    assert ".aq-grid" in body
    assert "grid-template-columns: 1fr" in body
    assert ".aq-card .aq-card-summary" in body
    assert "white-space: normal" in body


def test_dashboard_demo_copy_was_removed():
    text = _read(INDEX_HTML) + "\n" + _read(I18N)
    forbidden = [
        "Working demo",
        "Ishchi demo",
        "Рабочее демо",
        "Wave 3 lands",
        "Wave 1 stub",
    ]
    for phrase in forbidden:
        assert phrase not in text


def test_reading_gate_blocks_empty_and_whitespace_answers():
    """Submit handler must early-return on falsy/whitespace-only studentAnswer
    so answered[i] stays false and the page-next button stays disabled."""
    template_text = _read(RUNTIME)
    # The handler trims input before checking
    assert "const studentAnswer = (input.value || '').trim()" in template_text, (
        "checkpoint submit must assign studentAnswer as trimmed input value"
    )
    # The handler bails on empty/whitespace-only input
    assert "if (!studentAnswer)" in template_text, (
        "checkpoint submit must early-return on empty/whitespace input"
    )
    # answered[i] is only set inside the handler after the early-return guard
    assert "readingState.answered[i] = true" in template_text, (
        "checkpoint submit must set readingState.answered[i] = true on valid submit"
    )


def test_reading_continue_button_disabled_until_complete():
    """Forward progression past an unanswered checkpoint must be blocked.

    Pre-wave2: a `pageNextBtn` button at the bottom of each chunker page
    was disabled while `hasBlockingCheckpoint` was true.

    Post-wave2: the bottom nav button is gone — navigation is via swipe
    through the shared wave2 stream. The same guard moved into the
    `canAdvance` hook passed to wave2SlideInit, which blocks forward
    movement when the current question panel is unanswered. The intent
    (no advancing while checkpoints remain unanswered) is preserved.
    """
    template_text = _read(RUNTIME)
    assert "readingIsComplete" in template_text, (
        "readingIsComplete function must exist in the reading runtime"
    )
    # canAdvance hook is the new gate. It must check
    # `!readingState.answered[fromPage.cpIndex]` and return false to block.
    assert "canAdvance:" in template_text and "fromPage.cpIndex" in template_text, (
        "the wave2 canAdvance hook must reference fromPage.cpIndex so it can "
        "tell which checkpoint blocks forward movement"
    )
    assert "!readingState.answered[fromPage.cpIndex]" in template_text, (
        "canAdvance must block forward movement when the current question's "
        "checkpoint hasn't been answered yet"
    )
