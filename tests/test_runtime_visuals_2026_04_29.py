"""
Regression guards for the 2026-04-29 runtime / visual / a11y audit
fixes (Claude lane — branch `claude/audit-runtime-visuals-2026-04-29`).

Each test below is designed to FAIL on the pre-fix code and pass on
the post-fix code, so a future merge conflict resolution cannot
silently re-introduce the same bugs.

Lane scope (Codex owns tutor.py / injector.py / answer-checker — those
are NOT touched here): runtime player template, visual CSS, and pure
client-side a11y wiring.

Coverage:
1. Memory Sprint dynamic options
   - YNNG (3) and TF (2) questions render the correct number of
     buttons; spare static buttons are hidden via `.is-hidden`,
     not left rendering literal "undefined".
   - MC questions with >4 options grow the button pool dynamically.

2. Runtime accent contrast
   - `--accent` in the runtime template has been darkened away from
     the WCAG-AA-failing #007AFF / #0A84FF blues.
   - Inline `#007aff` literals (the tutor CTA at :3219) have been
     replaced with the var fallback.

3. Color-only correctness affordances
   - boss-feedback / aq-result-box / gb-mb-feedback / ms-option-btn
     all carry a glyph (✓ / ✗ / ◐) via ::before|::after CSS so a
     red-green colorblind student can distinguish correct from wrong.

4. Player a11y
   - `#phase-progress` is a real progressbar landmark.
   - `<main id="app">` survives (PR #57 introduced; pin it).
   - Mode-pill text colors meet AA (no #FF3B30 / #34C759 raw text).

5. Dark-theme leaks
   - `.preview-frame`, `.js-remove-card`, `.quote-chip-origin-national`
     all have explicit `[data-theme="dark"]` overrides.

6. Lang-pill keyboard focus
   - `.lang-pill:focus-visible` has an outline rule (was missing).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parent.parent
TEMPLATE = REPO_ROOT / "server" / "template" / "perfect_homework.html"
APP_CSS = REPO_ROOT / "frontend" / "css" / "app.css"


def _runtime() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def _app_css() -> str:
    return APP_CSS.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Memory Sprint dynamic options
# ---------------------------------------------------------------------------


def test_ms_render_loop_hides_spare_buttons_not_undefined():
    """Pre-fix: the loop did `b.textContent = item.options[i]` with no
    bounds check, so for a 2-option TF or 3-option YNNG question the
    extra static buttons rendered the literal string "undefined" and
    were still clickable. The fix gates the assignment on
    `i < opts.length` and tags the spares with `.is-hidden`.
    """
    html = _runtime()
    # The forbidden pattern is the unguarded textContent assignment
    # without the new `.is-hidden` branch.
    assert re.search(
        r"if\s*\(\s*i\s*<\s*opts\.length\s*\)\s*\{",
        html,
    ), "msRenderQuestion must guard option assignment with i < opts.length"
    assert "classList.add('is-hidden')" in html, (
        "the render loop must mark spare buttons with .is-hidden"
    )


def test_ms_is_hidden_class_actually_hides():
    html = _runtime()
    assert ".ms-option-btn.is-hidden" in html, (
        "is-hidden class must have a CSS rule"
    )
    # The rule must actually take buttons out of layout — `display: none`
    # is the simplest correct approach.
    assert re.search(
        r"\.ms-option-btn\.is-hidden\s*\{[^}]*display\s*:\s*none",
        html,
    ), "is-hidden must apply `display: none`"


def test_ms_position_and_button_helpers_exist():
    """The fix introduces `msPositionsFor(n)` and
    `msEnsureOptionButtons(zone, count)` helpers. Without these MC
    questions with 5+ options would silently truncate at 4 because the
    static HTML only ships four `<button>` elements."""
    html = _runtime()
    assert "function msPositionsFor" in html, (
        "missing msPositionsFor — MC truncation regression risk"
    )
    assert "function msEnsureOptionButtons" in html, (
        "missing msEnsureOptionButtons — MC truncation regression risk"
    )
    # Sanity: msPositionsFor must handle the canonical counts.
    for n in ("n <= 1", "n === 2", "n === 3", "n === 4"):
        assert n in html, f"msPositionsFor missing branch for {n}"


def test_ms_handle_answer_skips_hidden_buttons():
    """Once a TF/YNNG question hides slots 3-4 / 4, msHandleAnswer
    must NOT add `.wrong` to those hidden buttons (otherwise the
    `.wrong` glyph would render off-layout / inconsistently)."""
    html = _runtime()
    assert re.search(
        r"if\s*\(\s*i\s*>=\s*optsLen\s*\)\s*return;",
        html,
    ), "msHandleAnswer must short-circuit on hidden slots"


# ---------------------------------------------------------------------------
# 2. Runtime accent contrast
# ---------------------------------------------------------------------------


def test_runtime_accent_no_longer_uses_failing_blues():
    """Pre-fix the runtime declared `--accent: #007AFF;` (~4.0:1
    white-on-blue) in :root and `--accent: #0A84FF;` (~3.6:1) in
    [data-theme="dark"]. Both fail WCAG AA. The fix darkens to
    #0066CC / #006FE0. Forbid the failing values *as accent
    declarations* — decorative cluster fixtures may still reference
    the legacy hex (intentional)."""
    html = _runtime()
    accent_decls = re.findall(
        r"--accent\s*:\s*(#[0-9A-Fa-f]{6})\s*;",
        html,
    )
    assert accent_decls, "no --accent declarations found in runtime"
    forbidden = {"#007AFF", "#007aff", "#0A84FF", "#0a84ff"}
    bad = [v for v in accent_decls if v in forbidden]
    assert not bad, (
        f"runtime --accent reverted to {bad} — fails WCAG AA white-on-blue"
    )


def test_runtime_no_bare_007aff_literal():
    """The Wave-F4 tutor CTA at :3219 used to write
    `background: #007aff;` directly. After the fix every styled
    surface should consume `var(--accent, ...)` instead."""
    html = _runtime()
    # Allow the legacy hex to survive in: cluster-dot JS fixtures
    # (FC_CLUSTER_DOT / --fc-names-from / --fc-names-to), and
    # in code comments. Forbid it as a `background:` or `color:`
    # value in CSS rules.
    bare = re.findall(
        r"\n\s*(?:background|color)\s*:\s*#0[07]7[Aa][Ff][Ff]\b",
        html,
    )
    assert not bare, (
        "found bare #007aff as background/color in runtime CSS — "
        "should consume var(--accent, ...) instead"
    )


# ---------------------------------------------------------------------------
# 3. Color-only correctness affordances
# ---------------------------------------------------------------------------


def test_correct_wrong_have_glyph_pseudo_elements():
    """Color-only correct/wrong fails WCAG 1.4.1. Each game-break
    feedback channel must carry a non-color affordance. The fix adds
    ::before / ::after pseudo-elements with ✓ / ✗ glyphs."""
    html = _runtime()
    pairs = [
        ("ms-option-btn", "::after"),
        ("boss-feedback", "::before"),
        ("aq-result-box", "::before"),
        ("gb-mb-feedback", "::before"),
        ("gb-mb-label", "::after"),
        ("gb-tm-tile", "::after"),
        ("gb-mm-card", "::after"),
        ("gb-pl-cell", "::after"),
    ]
    for klass, pseudo in pairs:
        # Look for any rule in the class family that uses this pseudo.
        pattern = rf"\.{re.escape(klass)}[^{{]*{re.escape(pseudo)}\s*[,{{]"
        assert re.search(pattern, html), (
            f"{klass} must have a {pseudo} glyph rule for non-color "
            f"correctness affordance"
        )
    # And the actual glyph characters (escaped in CSS) must appear:
    assert "\\2713" in html, "missing ✓ glyph (\\2713) in runtime CSS"
    assert "\\2717" in html, "missing ✗ glyph (\\2717) in runtime CSS"


def test_feedback_containers_are_live_regions():
    """boss/AQ/MB feedback elements must be aria-live regions so the
    text announcement reaches assistive tech."""
    html = _runtime()
    for el_id in ("boss-feedback", "aq-result-box",
                  "gb-mb-id-feedback", "gb-mb-solve-feedback"):
        m = re.search(rf'id=["\']{el_id}["\'][^>]*>', html)
        assert m, f"missing element #{el_id}"
        assert 'aria-live="polite"' in m.group(0), (
            f"#{el_id} must be aria-live=\"polite\""
        )


# ---------------------------------------------------------------------------
# 4. Player a11y — progressbar + main + mode-pill contrast
# ---------------------------------------------------------------------------


def test_phase_progress_is_a_real_progressbar():
    html = _runtime()
    m = re.search(
        r'<div[^>]*id=["\']phase-progress["\'][^>]*>',
        html,
    )
    assert m, "missing #phase-progress element"
    tag = m.group(0)
    assert 'role="progressbar"' in tag
    assert 'aria-valuemin="0"' in tag
    assert 'aria-valuemax="7"' in tag
    assert 'aria-valuenow=' in tag
    assert "aria-label=" in tag

    # And updatePhaseProgress must keep aria-valuenow in sync.
    assert re.search(
        r"setAttribute\(\s*['\"]aria-valuenow['\"]",
        html,
    ), "updatePhaseProgress must update aria-valuenow as the runtime advances"


def test_main_landmark_pinned_after_pr57():
    html = _runtime()
    assert re.search(r'<main\b[^>]*id=["\']app["\']', html), (
        "perfect_homework.html lost its <main id=\"app\"> landmark"
    )


def test_mode_pill_text_meets_wcag_aa():
    css = _app_css()
    # The pre-fix CSS used `.mode-pill[data-mode="easy"] color: #34C759`
    # (≈2.0:1 on white) and `data-mode="hard"] color: #FF3B30`
    # (≈3.2:1). The fix darkens both. Forbid the failing values as
    # `.mode-pill[data-mode=...] color`.
    for mode in ("easy", "hard"):
        block = re.search(
            rf'\.mode-pill\[data-mode="{mode}"\]\s*\{{([^}}]+)\}}',
            css,
        )
        assert block, f"missing .mode-pill[data-mode={mode}] rule"
        body = block.group(1)
        m = re.search(r"color\s*:\s*(#[0-9A-Fa-f]{6})", body)
        assert m, f".mode-pill[data-mode={mode}] missing color"
        bad = {"#FF3B30", "#ff3b30", "#34C759", "#34c759"}
        assert m.group(1) not in bad, (
            f".mode-pill[data-mode={mode}] reverted to "
            f"{m.group(1)} — fails WCAG AA on tinted background"
        )


# ---------------------------------------------------------------------------
# 5. Dark-theme leaks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("selector", [
    ".preview-frame",
    ".flashcard-builder-card .fc-card-head .js-remove-card",
    ".quote-chip-origin-national",
])
def test_dark_theme_overrides_exist(selector):
    css = _app_css()
    pattern = (
        r'\[data-theme="dark"\]\s*'
        + re.escape(selector)
        + r"\s*\{"
    )
    assert re.search(pattern, css), (
        f"missing [data-theme=\"dark\"] {selector} override — "
        "the light-only color leaks into dark mode and fails contrast"
    )


# ---------------------------------------------------------------------------
# 6. Lang-pill keyboard focus
# ---------------------------------------------------------------------------


def test_lang_pill_has_focus_visible_outline():
    css = _app_css()
    block = re.search(
        r"\.lang-pill:focus-visible\s*\{([^}]+)\}",
        css,
    )
    assert block, ".lang-pill is missing a :focus-visible rule"
    body = block.group(1)
    assert "outline" in body, (
        ".lang-pill:focus-visible must define an outline so keyboard "
        "users can see which pill is focused"
    )


# ---------------------------------------------------------------------------
# Bonus: rendered preview still serves and contains the new affordances.
# ---------------------------------------------------------------------------


def test_rendered_preview_contains_new_affordances(client, sample_homework):
    """End-to-end: hit /api/homeworks/{id}/preview and assert the
    audit fixes survive the injector pass."""
    r = client.get(f"/api/homeworks/{sample_homework['id']}/preview")
    assert r.status_code == 200
    body = r.text
    assert 'role="progressbar"' in body
    assert "<main" in body and 'id="app"' in body
    assert ".ms-option-btn.is-hidden" in body
    assert "function msPositionsFor" in body
    # Glyph rules survive
    assert "\\2713" in body and "\\2717" in body
