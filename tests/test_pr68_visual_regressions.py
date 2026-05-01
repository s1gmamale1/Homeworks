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
    assert "if (!readingIsComplete(checkpoints))" in html
    assert "readingGoToPage(readingCheckpointPage(firstMissing" in html
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
    """Page-next button must be disabled while unanswered checkpoints remain
    on the current page — not just structurally present but wired via
    hasBlockingCheckpoint."""
    template_text = _read(RUNTIME)
    assert "readingIsComplete" in template_text, (
        "readingIsComplete function must exist in the reading runtime"
    )
    # The page-next disable guard uses hasBlockingCheckpoint
    assert "const hasBlockingCheckpoint = pageCheckpointIndexes.some(i => !readingState.answered[i])" in template_text, (
        "page-next button gate must derive hasBlockingCheckpoint from unanswered checkpoints"
    )
    assert "pageNextBtn.disabled = hasBlockingCheckpoint" in template_text, (
        "page-next button must be disabled when hasBlockingCheckpoint is true"
    )
