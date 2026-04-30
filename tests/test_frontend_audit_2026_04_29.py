"""
Regression guards for the 2026-04-29 frontend / runtime audit fixes.

Each test below was designed to FAIL on the pre-fix code and pass on the
post-fix code, so the same bugs cannot silently re-appear via a future
merge conflict resolution. Surfaces covered:

1. Boss editor (frontend/js/editors/boss.js)
   Fixtures supply ``answer_spec`` without ``rubric``; the previous
   ``spec = question.answer_spec || default`` swap dropped the default
   rubric and the editor crashed on ``spec.rubric.correct``. The fix
   merges the default with the provided spec/rubric instead of
   replacing the whole default.

2. Mobile overflow (frontend/css/app.css, frontend/css/library.css)
   At iPhone widths (~390px) the dashboard and library produced
   horizontal scroll. Fix: explicit @media (max-width: 640px) rules
   collapse both grids to 1 column and harden topbar / gamebreak.

3. Blue button contrast (frontend/css/app.css)
   ``--accent: #007AFF`` produced ~4.0:1 white-on-blue, below WCAG AA's
   4.5:1 threshold. Fix: darken to ``#0066CC`` (light) / ``#006FE0``
   (dark). The old hex MUST NOT come back.

4. API error message extraction (frontend/js/api.js)
   FastAPI returns ``{"detail": {"error": "...", "code": "..."}}`` but
   the old code only inspected ``payload.error`` at the top level, so
   users saw ``Request failed with 4xx`` instead of the real message.
   Fix: an ``extractErrorMessage`` helper that handles
   ``detail`` (string or object) before falling back.

5. Accessibility — main landmark + game button labels
   The runtime player (server/template/perfect_homework.html) had no
   ``<main>`` landmark and the four ``ms-option-btn`` Memory Sprint
   buttons rendered with no accessible name in static HTML.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
TEMPLATE_DIR = REPO_ROOT / "server" / "template"


# ---------------------------------------------------------------------------
# 1. Boss editor: default rubric must merge in even when answer_spec is given
# ---------------------------------------------------------------------------


def _boss_js() -> str:
    return (FRONTEND_DIR / "js" / "editors" / "boss.js").read_text(encoding="utf-8")


def test_boss_editor_does_not_or_swap_answer_spec_with_default():
    """The buggy form was ``const spec = question?.answer_spec || {...};``.

    That line means: if the fixture provided ``answer_spec`` *at all*,
    the default object — including its ``rubric`` — is discarded. Then
    rendering ``spec.rubric.correct`` crashes when the fixture omitted
    rubric. The fix replaces the OR-swap with a merge that always
    layers in the default rubric.
    """
    src = _boss_js()
    # Forbid the buggy form specifically: an OR with an inline object
    # literal containing the rubric defaults. The post-fix code uses
    # ``|| {}`` which is fine — the merge happens after.
    assert not re.search(
        r"question\?\.answer_spec\s*\|\|\s*\{[^}]*rubric\s*:",
        src,
        flags=re.DOTALL,
    ), (
        "boss.js still uses ``question?.answer_spec || {full default with rubric}`` — "
        "that drops fixture rubrics and crashes on spec.rubric.correct when "
        "the fixture provides a partial answer_spec without rubric."
    )


def test_boss_editor_merges_default_rubric():
    """Post-fix: a default-rubric merge is performed so spec.rubric.* is
    always defined regardless of fixture shape."""
    src = _boss_js()
    # The fix introduces a defaults() factory and spreads its rubric.
    assert "defaultAnswerSpec" in src or "DEFAULT_SPEC" in src, (
        "boss.js should expose a default-spec factory the merge can rely on"
    )
    # Spread of default rubric — guards against a future refactor that
    # collapses back into the OR-swap.
    assert re.search(
        r"rubric:\s*\{\s*\.\.\.\s*\w+\.rubric", src
    ), "boss.js should spread the default rubric into the merged spec"


# ---------------------------------------------------------------------------
# 2. Mobile overflow — explicit ≤640px rules on both grids
# ---------------------------------------------------------------------------


def _app_css() -> str:
    return (FRONTEND_DIR / "css" / "app.css").read_text(encoding="utf-8")


def _library_css() -> str:
    return (FRONTEND_DIR / "css" / "library.css").read_text(encoding="utf-8")


def test_app_css_collapses_homework_grid_at_640px():
    """The dashboard grid must drop to 1 column at iPhone widths and
    the shell must be guarded against horizontal scroll.

    The pre-fix CSS had a 639px rule but no overflow guard on the shell
    or topbar. The fix ships a dedicated mobile-overflow guard block.
    """
    css = _app_css()
    # The 640px-or-less surface must (somewhere across all matching
    # blocks) collapse the homework grid AND clamp horizontal overflow.
    blocks = re.findall(
        r"@media\s*\(max-width:\s*64[0-9]px\)\s*\{(.+?)\n\}",
        css,
        flags=re.DOTALL,
    )
    assert blocks, "expected at least one @media (max-width: ≤640px) block"

    has_grid_collapse = any(
        re.search(r"\.homework-grid\b[^{]*\{[^}]*1fr", b, flags=re.DOTALL)
        for b in blocks
    )
    assert has_grid_collapse, (
        "no ≤640px @media block collapses .homework-grid to 1 column"
    )

    has_overflow_guard = any("overflow-x" in b for b in blocks)
    assert has_overflow_guard, (
        "no ≤640px @media block guards against horizontal overflow "
        "(overflow-x: hidden on the shell or html/body)"
    )


def test_library_css_collapses_subject_grid_at_650px():
    css = _library_css()
    # Apple-redesign breakpoint is 650px (was 640px under the old <details>
    # layout; new mobile cutoff aligns with the iPhone-portrait + small-tablet
    # span used elsewhere in the redesign). The new contract uses
    # `.lib-subject-grid` instead of the removed `.lib-grid`.
    assert re.search(
        r"@media\s*\(max-width:\s*650px\)[^{]*\{[^}]*\.lib-subject-grid[^}]*1fr",
        css,
        flags=re.DOTALL,
    ), (
        "library.css must collapse .lib-subject-grid to 1 column at ≤650px "
        "(Apple-redesign breakpoint)"
    )


# ---------------------------------------------------------------------------
# 3. Blue button contrast — old #007AFF / #0A84FF must not return
# ---------------------------------------------------------------------------


# WCAG-AA-failing values that previously shipped. These exact hexes
# under ``--accent: ...`` would silently re-introduce the contrast
# regression, so we forbid them at the variable declaration site.
_FORBIDDEN_ACCENTS = ("#007AFF", "#007aff", "#0A84FF", "#0a84ff")


def test_app_css_accent_meets_wcag_aa():
    css = _app_css()
    # Match only the *primary* --accent declaration in :root and
    # [data-theme="dark"], not every place the hex appears (gradient
    # decorations, family colors, etc.).
    accent_lines = re.findall(
        r"--accent\s*:\s*(#[0-9A-Fa-f]{6})\s*;",
        css,
    )
    assert accent_lines, "no --accent declarations found in app.css"
    for hex_val in accent_lines:
        assert hex_val not in _FORBIDDEN_ACCENTS, (
            f"--accent reverted to {hex_val} which gives ~4.0:1 white-on-blue "
            "(below WCAG AA 4.5:1). Use #0066CC (light) / #006FE0 (dark)."
        )


# ---------------------------------------------------------------------------
# 4. API error extraction — must read FastAPI's ``detail.error`` shape
# ---------------------------------------------------------------------------


def _api_js() -> str:
    return (FRONTEND_DIR / "js" / "api.js").read_text(encoding="utf-8")


def test_api_js_extracts_fastapi_detail_error():
    src = _api_js()
    # The fix introduces an extractErrorMessage helper and references
    # payload.detail. Without these, the frontend can only ever surface
    # the generic ``Request failed with 4xx`` text.
    assert "extractErrorMessage" in src, (
        "api.js must define an extractErrorMessage helper that handles "
        "FastAPI's {detail: ...} envelope"
    )
    assert re.search(r"payload\.detail|\.detail\b", src), (
        "api.js must inspect payload.detail (FastAPI's error envelope)"
    )


def test_api_js_no_longer_only_inspects_top_level_error():
    """Pre-fix shape was a one-liner ternary that *only* looked at
    ``payload.error``. Forbid that exact shape so a future cleanup
    cannot silently regress."""
    src = _api_js()
    # The exact pre-fix snippet, including whitespace.
    forbidden = (
        "payload && typeof payload === \"object\" && payload.error\n"
        "          ? payload.error\n"
        "          : `Request failed with"
    )
    assert forbidden not in src, (
        "api.js still uses the pre-fix ternary that only reads "
        "payload.error and never reaches FastAPI's detail.error"
    )


# ---------------------------------------------------------------------------
# 5. A11y — <main> landmark + named game option buttons in the runtime
# ---------------------------------------------------------------------------


def _runtime_html() -> str:
    return (TEMPLATE_DIR / "perfect_homework.html").read_text(encoding="utf-8")


def test_runtime_has_main_landmark():
    html = _runtime_html()
    # The pre-fix template used <div id="app"> with no ARIA landmark, so
    # screen readers had no skip target. The fix promotes the wrapper
    # to <main id="app">.
    assert re.search(r'<main\b[^>]*id=["\']app["\']', html), (
        "perfect_homework.html should wrap the player in <main id=\"app\">"
    )
    # And the dual close.
    assert "</main>" in html, "missing </main> close tag in runtime template"


def test_runtime_memory_sprint_options_have_accessible_names():
    """The four ``ms-option-btn`` buttons used to render as empty
    ``<button>`` elements (text was injected via JS). In static HTML —
    and during the brief window before JS hydrates — they had no
    accessible name. Fix: aria-label fallback in the static markup."""
    html = _runtime_html()
    matches = re.findall(
        r'<button\b[^>]*class="ms-option-btn[^"]*"[^>]*>',
        html,
    )
    assert len(matches) == 4, (
        f"expected 4 ms-option-btn buttons, got {len(matches)}"
    )
    for tag in matches:
        assert "aria-label=" in tag, (
            f"ms-option-btn rendered without aria-label fallback: {tag}"
        )


def test_runtime_memory_sprint_js_keeps_aria_label_synced_with_text():
    """The static aria-label is just a fallback; once JS sets the real
    option text we must also update aria-label so screen readers
    announce the actual answer, not ``Variant 1``.

    The 2026-04-29 dynamic-options follow-up renamed the local from
    ``item.options[i]`` to ``opts[i]`` (after introducing the bounds
    guard for TF/YNNG questions); the invariant under test is that
    aria-label is set in the same loop iteration as textContent — not
    the exact variable name."""
    html = _runtime_html()
    # Match either the original `item.options[i]` form or the post-
    # fix `opts[i]` form, with optional comments between the two
    # statements. The aria-label assignment must follow inside the
    # same block.
    assert re.search(
        r"b\.textContent\s*=\s*(?:item\.options|opts)\[i\];\s*"
        r"(?://[^\n]*\n\s*)*"
        r"(?:b\.setAttribute\(\s*['\"]aria-label['\"]|b\.ariaLabel\s*=)",
        html,
    ), (
        "ms option render must update aria-label alongside textContent so "
        "the accessible name follows the visible text"
    )


# ---------------------------------------------------------------------------
# Bonus: rendered HTML invariant — the dashboard / library / builder
# pages still serve correctly after these edits.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", ["/", "/library.html", "/builder.html"])
def test_pages_still_serve_after_audit_fixes(client, path):
    r = client.get(path)
    assert r.status_code == 200, f"{path} returned {r.status_code}"
    assert "<main" in r.text, f"{path} missing <main> landmark"
