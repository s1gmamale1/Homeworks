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
_JS_PATH = REPO_ROOT / "server" / "template" / "js" / "perfect_homework.js"
_CSS_PATH = REPO_ROOT / "server" / "template" / "static" / "css" / "perfect_homework.css"
_HTML_PATH = REPO_ROOT / "server" / "template" / "perfect_homework.html"
TEMPLATE = _HTML_PATH.read_text(encoding="utf-8") + "\n" + _JS_PATH.read_text(encoding="utf-8") + "\n" + _CSS_PATH.read_text(encoding="utf-8")
APP_CSS = REPO_ROOT / "frontend" / "css" / "app.css"


def _runtime() -> str:
    return TEMPLATE


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
    # CSS/JS are now in external files; combine response with static files for assertions
    body = r.text + "\n" + _JS_PATH.read_text(encoding="utf-8") + "\n" + _CSS_PATH.read_text(encoding="utf-8")
    assert 'role="progressbar"' in body
    assert "<main" in body and 'id="app"' in body
    assert ".ms-option-btn.is-hidden" in body
    assert "function msPositionsFor" in body
    # Glyph rules survive
    assert "\\2713" in body and "\\2717" in body


# ---------------------------------------------------------------------------
# 7. Bug #4 — Preview pagination drops metadata-only sub-pages
# ---------------------------------------------------------------------------


def test_preview_pagination_drops_metadata_only_pages():
    """`_previewChunkPageBlocks` must run a post-pass that merges
    metadata-only or too-short sub-pages into the previous page so the
    student never lands on a panel containing just `[Bloom: L3 | PISA: L3]`
    or a similar tag-line."""
    html = _runtime()
    # The post-pass helper must exist and the chunker must call into it.
    assert "_previewMergeMetadataOnlyPages" in html, (
        "missing _previewMergeMetadataOnlyPages — Bug #4 post-pass merge "
        "logic is gone"
    )
    # The merge logic must inspect tag-line metadata patterns. Pin the
    # canonical regex sentinel so a refactor can't silently drop the merge.
    assert re.search(
        r"\\\[\(\?:Bloom\|PISA\|Damage\|Tag\|Tags\)",
        html,
    ), (
        "the metadata-only regex (Bloom/PISA/Damage/Tags) must be present "
        "in the preview pagination post-pass"
    )
    # The threshold pin: a too-short page is ~80 chars or less. Either the
    # literal 80 or the SHORT_PAGE_THRESHOLD constant must appear so the
    # regression test catches a future tightening of the threshold.
    assert "SHORT_PAGE_THRESHOLD" in html, (
        "SHORT_PAGE_THRESHOLD constant for too-short page detection is "
        "missing — Bug #4 fix incomplete"
    )


def test_preview_pagination_post_pass_keeps_first_page():
    """The first page of a panel must not be merged into nothing — even
    if it's metadata-only, it stays its own page so the panel always has
    at least one rendered page."""
    html = _runtime()
    # The post-pass loop must start at i = 1 so pages[0] is always kept.
    body_match = re.search(
        r"function _previewMergeMetadataOnlyPages\([^)]*\)\s*\{[\s\S]*?\n\s{8}\}",
        html,
    )
    assert body_match, "_previewMergeMetadataOnlyPages function body not found"
    body = body_match.group(0)
    assert re.search(r"merged\s*=\s*\[\s*pages\[0\]\s*\]", body), (
        "the post-pass must seed `merged` with pages[0] so the first page "
        "is never merged away"
    )
    assert re.search(r"for\s*\(\s*let\s+i\s*=\s*1\s*;", body), (
        "the merge loop must start at i = 1 so pages[0] stays untouched"
    )


# ---------------------------------------------------------------------------
# 8. Bug #5 — Preview Panel dark fade readability
# ---------------------------------------------------------------------------


def test_preview_dark_fade_panel_readable():
    """The dark-mode override for `.panel-card::after` must use a softer
    gradient (max alpha <= 0.5) AND/OR a shorter fade height (<= 24px)
    so Panel 5's bottom-most line of text remains readable through the
    fade. Pin both — either condition alone is acceptable but together
    they guarantee a comfortable margin."""
    html = _runtime()
    # The dark-theme override block must exist.
    block = re.search(
        r'\[data-theme="dark"\]\s*\.panel-card::after\s*\{([^}]+)\}',
        html,
    )
    assert block, (
        "missing [data-theme=\"dark\"] .panel-card::after override — "
        "Bug #5 dark fade readability fix is gone"
    )
    body = block.group(1)
    # Height bound: <= 24px. The default light-mode height is 28px.
    height_match = re.search(r"height\s*:\s*(\d+)\s*px", body)
    assert height_match, "dark .panel-card::after must define a height"
    assert int(height_match.group(1)) <= 24, (
        f"dark fade height is {height_match.group(1)}px — must be <= 24px "
        "so the fade only covers the very last line, not the full bottom margin"
    )
    # Alpha bound: every rgba(...) alpha stop must be <= 0.5 so text
    # stays at >=70% readable through the gradient.
    alphas = re.findall(r"rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*([0-9.]+)\s*\)", body)
    assert alphas, "dark .panel-card::after must use rgba() so we can bound the alpha"
    assert max(float(a) for a in alphas) <= 0.5, (
        f"dark fade max alpha is {max(float(a) for a in alphas)} — must be "
        "<= 0.5 so the bottom line of text remains readable"
    )


# ---------------------------------------------------------------------------
# 9. Bug #6 — Flashcard carousel rapid-click animation guard
# ---------------------------------------------------------------------------


def test_flashcard_switch_has_animation_guard():
    """`switchCard` must early-return when a horizontal switch is already
    in flight. Pre-fix: rapid arrow / next-side-card clicks during the
    transition could leave the center face hidden because a second
    switch fired before the first cleared its inline opacity:0."""
    html = _runtime()
    # The guard variable must exist.
    assert "state.cardSwitching" in html, (
        "the state.cardSwitching guard for in-flight horizontal switches "
        "is missing — Bug #6 fix is gone"
    )
    # switchCard must early-return on the guard at entry.
    switch_card = re.search(
        r"function switchCard\(newIdx,\s*dir\)\s*\{([\s\S]*?)\n\s{8}\}",
        html,
    )
    assert switch_card, "switchCard function body not found"
    fn_body = switch_card.group(1)
    assert re.search(
        r"if\s*\(\s*state\.cardSwitching\s*\)\s*return",
        fn_body,
    ), (
        "switchCard must early-return on state.cardSwitching at entry so "
        "rapid clicks queue at most one switch in flight"
    )
    # Side-card click handlers must check the guard too.
    setup = re.search(
        r"function setupFlashcardCarouselControls\(\)\s*\{([\s\S]*?)\n\s{8}\}",
        html,
    )
    assert setup, "setupFlashcardCarouselControls function body not found"
    setup_body = setup.group(1)
    assert "state.cardSwitching" in setup_body, (
        "setupFlashcardCarouselControls click handlers must consult "
        "state.cardSwitching so side-card taps respect the guard"
    )


def test_flashcard_switch_releases_guard_via_transitionend_or_timeout():
    """The guard must be cleared by EITHER a transitionend handler OR a
    safety setTimeout fallback — never just one (the user's tab might
    lose focus and skip transitionend)."""
    html = _runtime()
    switch_card = re.search(
        r"function switchCard\(newIdx,\s*dir\)\s*\{([\s\S]*?)\n\s{8}\}",
        html,
    )
    assert switch_card
    fn_body = switch_card.group(1)
    # Two release paths: transitionend listener AND a setTimeout fallback.
    assert "transitionend" in fn_body, (
        "switchCard must wire a transitionend listener for the guard release"
    )
    # The safety fallback is a setTimeout that calls releaseGuard or directly
    # clears state.cardSwitching. Pin "releaseGuard" so the two paths share
    # one idempotent clear.
    assert "releaseGuard" in fn_body, (
        "switchCard must define a releaseGuard helper that both the "
        "transitionend handler and the safety setTimeout call into"
    )


# ---------------------------------------------------------------------------
# 10. Flashcard horizontal-slide of a flipped card uses a flat-back render
#     (2026-05-08): a flipped card sliding sideways must NOT animate an
#     unflip mid-slide and must NOT hide its back face. We swap to a
#     `.fc-sliding-flipped` flat representation (parent unrotated, back
#     un-rotated, front faded) so the slide is a clean 2D translate that
#     can't be mangled by browser matrix interpolation at 180°.
# ---------------------------------------------------------------------------


def test_flashcard_sliding_flipped_css_state_exists():
    """The .fc-sliding-flipped flat-back state must:
       - hide the front face (so it doesn't stack on top of the back), and
       - un-rotate the back face (so it faces the viewer when the parent
         is no longer at rotateY(180deg))."""
    html = _runtime()
    assert re.search(
        r"\.fc-inner\.fc-sliding-flipped\s+\.fc-front\s*\{[^}]*opacity\s*:\s*0",
        html,
    ), (
        "missing .fc-inner.fc-sliding-flipped .fc-front { opacity: 0 } — "
        "without it, the front face would stack on top of the back during "
        "a flipped card's horizontal slide"
    )
    assert re.search(
        r"\.fc-inner\.fc-sliding-flipped\s+\.fc-back\s*\{[^}]*transform\s*:\s*none",
        html,
    ), (
        "missing .fc-inner.fc-sliding-flipped .fc-back { transform: none } "
        "— without it, the back face would still have its own rotateY(180deg) "
        "and face away from the viewer once the parent rotation is removed"
    )


def test_flashcard_slide_out_uses_flat_back_when_flipped():
    """When the card is flipped at the start of switchCard, slide-out must:
       - gate on state.cardFlipped,
       - disable transition,
       - remove the .flipped class,
       - add .fc-sliding-flipped,
       - force a reflow so the un-flip is committed before the slide
         transition is re-enabled.
    The inline slide-out transform must NOT include rotateY (we want a
    flat 2D translate, not a 3D one that browsers can mangle at 180°)."""
    html = _runtime()
    switch_card = re.search(
        r"function switchCard\(newIdx,\s*dir\)\s*\{([\s\S]*?)\n\s{8}\}",
        html,
    )
    assert switch_card, "switchCard function body not found"
    fn_body = switch_card.group(1)

    # Split at the inner setTimeout that fires the slide-in.
    parts = fn_body.split("setTimeout(", 1)
    assert len(parts) == 2, (
        "switchCard's slide-in setTimeout boundary not found; can't isolate "
        "slide-out vs slide-in"
    )
    slide_out_section, slide_in_section = parts[0], parts[1]

    # The flipped-card swap block must exist and do all four moves.
    flipped_branch = re.search(
        r"if\s*\(\s*state\.cardFlipped\s*\)\s*\{([\s\S]*?)\}",
        slide_out_section,
    )
    assert flipped_branch, (
        "switchCard slide-out must have an `if (state.cardFlipped) { ... }` "
        "branch that swaps the card to a flat-back representation before "
        "animating"
    )
    branch = flipped_branch.group(1)
    assert "fcInner.style.transition = 'none'" in branch, (
        "flipped-card swap must disable transition before toggling classes "
        "so the un-flip is instant"
    )
    assert "classList.remove('flipped')" in branch, (
        "flipped-card swap must remove the .flipped class so the parent's "
        "rotateY(180deg) is gone for the slide"
    )
    assert "classList.add('fc-sliding-flipped')" in branch, (
        "flipped-card swap must add .fc-sliding-flipped so the back face "
        "un-rotates and the front fades out"
    )
    assert "offsetWidth" in branch or "offsetHeight" in branch, (
        "flipped-card swap must force a reflow before re-enabling transition "
        "so the un-flip commits separately from the slide animation"
    )

    # The slide-out transform itself must NOT include rotateY anywhere.
    transform_writes = re.findall(
        r"fcInner\.style\.transform\s*=\s*([^;]+);",
        slide_out_section,
    )
    assert transform_writes, "expected at least one slide-out transform write"
    for expr in transform_writes:
        assert "rotateY" not in expr, (
            "slide-out transform must NOT include rotateY (rely on the "
            f".fc-sliding-flipped CSS swap instead). Got: {expr!r}"
        )

    # Slide-in transforms must also be rotation-free — new card lands on
    # the front face.
    slide_in_writes = re.findall(
        r"fcInner\.style\.transform\s*=\s*([^;]+);",
        slide_in_section,
    )
    assert slide_in_writes
    for expr in slide_in_writes:
        assert "rotateY" not in expr, (
            "slide-in transform must NOT include rotateY — the new card "
            f"always lands on the front face. Got: {expr!r}"
        )


def test_flashcard_sliding_flipped_class_cleaned_up_on_render_and_release():
    """Both renderFlashcard (between slide-out and slide-in) and the
    releaseGuard (after slide-in completes) must clear the
    .fc-sliding-flipped class so it never leaks into the next card or
    sits on the element after the carousel settles."""
    html = _runtime()

    render = re.search(
        r"function renderFlashcard\([^)]*\)\s*\{([\s\S]*?)\n\s{8}\}",
        html,
    )
    assert render, "renderFlashcard function body not found"
    render_body = render.group(1)
    assert "classList.remove('flipped')" in render_body, (
        "renderFlashcard must still remove the .flipped class"
    )
    assert "classList.remove('fc-sliding-flipped')" in render_body, (
        "renderFlashcard must also remove .fc-sliding-flipped so the new "
        "card doesn't render through the flat-back overrides"
    )
    assert re.search(r"state\.cardFlipped\s*=\s*false", render_body), (
        "renderFlashcard must reset state.cardFlipped = false"
    )

    switch_card = re.search(
        r"function switchCard\(newIdx,\s*dir\)\s*\{([\s\S]*?)\n\s{8}\}",
        html,
    )
    assert switch_card
    fn_body = switch_card.group(1)
    release_guard = re.search(
        r"const releaseGuard\s*=\s*\(\)\s*=>\s*\{([\s\S]*?)\n\s{12}\};",
        fn_body,
    )
    assert release_guard, "releaseGuard helper not found in switchCard"
    rg_body = release_guard.group(1)
    assert "classList.remove('flipped')" in rg_body, (
        "releaseGuard must still remove the .flipped class"
    )
    assert "classList.remove('fc-sliding-flipped')" in rg_body, (
        "releaseGuard must also remove .fc-sliding-flipped so the class "
        "doesn't leak past the slide-in completion"
    )

