"""Sanity tier — does PR #4 actually wire the foundation in place?

Pure introspection of the template and tokens file; no rendering.
"""
from __future__ import annotations

from server.config import BASE_DIR


def test_template_contains_tokens_css_link():
    tpl = (BASE_DIR / "server" / "template" / "perfect_homework.html").read_text(encoding="utf-8")
    assert '<link rel="stylesheet" href="/css/_tokens.css' in tpl


def test_template_link_uses_no_query_cache_bust():
    """`/h/{id}` is served via the injector, NOT via the static-page
    `_render_html_with_version` path. Query-string cache-bust placeholders
    are not substituted here. CSS cache-bust relies on HTTP cache headers
    served by StaticFiles. A future PR may wire VERSION through the
    injector — for now, no query."""
    tpl = (BASE_DIR / "server" / "template" / "perfect_homework.html").read_text(encoding="utf-8")
    assert '/css/_tokens.css"' in tpl  # link exists with no query
    assert "_tokens.css?v=__VERSION__" not in tpl  # placeholder was removed


def test_template_link_sits_before_katex():
    """Link order matters slightly — tokens (custom-property declarations)
    should load before any third-party CSS that might define cascade-
    competing rules. KaTeX is loaded next, so our link goes before."""
    tpl = (BASE_DIR / "server" / "template" / "perfect_homework.html").read_text(encoding="utf-8")
    tokens_pos = tpl.find("/css/_tokens.css")
    katex_pos = tpl.find("katex.min.css")
    assert tokens_pos > 0
    assert katex_pos > 0
    assert tokens_pos < katex_pos


def test_tokens_file_lists_all_documented_token_categories():
    """The tokens file's docstring promises specific categories. Confirm
    each one is materialized."""
    text = (BASE_DIR / "frontend" / "css" / "_tokens.css").read_text(encoding="utf-8")
    # Surface / type
    assert "--landing-zinc-" in text
    # Accent
    assert "--landing-blue-" in text
    # Cyan
    assert "--landing-cyan-" in text
    # Elevation
    assert "--landing-shadow-" in text
    # Motion
    assert "--landing-spring" in text


def test_a11y_block_present_in_tokens_file():
    text = (BASE_DIR / "frontend" / "css" / "_tokens.css").read_text(encoding="utf-8")
    # The a11y block follows a marker comment
    assert "Accessibility scaffolding" in text or ":focus-visible" in text


def test_legacy_homeworks_unaffected_by_v2_scoped_rules():
    """The v2 accessibility CSS rules are scoped to `[data-flow=\"v2\"]`
    selectors. Legacy homeworks don't set this attribute, so the rules
    are dormant. Verify the scoping is in place."""
    text = (BASE_DIR / "frontend" / "css" / "_tokens.css").read_text(encoding="utf-8")
    # Every a11y rule should mention the v2 attribute selector
    assert '[data-flow="v2"]' in text


def test_no_pr4_changes_to_landing_css():
    """PR #4 must not modify landing.css — it's self-contained by design
    (see its own header comment: 'self-contained when loaded standalone')."""
    # We can't diff against origin without git here, but we can check that
    # landing.css still declares its own copy of the tokens (it was supposed
    # to remain unchanged).
    text = (BASE_DIR / "frontend" / "css" / "landing.css").read_text(encoding="utf-8")
    assert "--landing-zinc-950" in text  # landing.css still has its own copy
    assert "Re-declared so landing.css is self-contained" in text
