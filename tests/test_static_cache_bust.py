"""
Test cache-busting for static assets.

Ensures that all script and link references include ?v=<version> query params
to prevent browser cache issues on new deploys.
"""
import re
import pytest


def test_index_html_has_version_query(client):
    """Index page must have cache-bust version on all static asset references."""
    r = client.get("/")
    assert r.status_code == 200
    body = r.text

    # Extract all src and href references to /js or /css
    refs = re.findall(r'(?:src|href)="(/(?:js|css)/[^"]+)"', body)
    assert len(refs) > 0, "No script/link refs found in index.html"

    for ref in refs:
        assert "?v=" in ref, f"missing cache-bust on: {ref}"


def test_builder_html_has_version_query(client):
    """Builder page must have cache-bust version on all static asset references."""
    r = client.get("/builder.html")
    assert r.status_code == 200
    body = r.text

    # Extract all src and href references to /js or /css
    refs = re.findall(r'(?:src|href)="(/(?:js|css)/[^"]+)"', body)
    assert len(refs) > 0, "No script/link refs found in builder.html"

    for ref in refs:
        assert "?v=" in ref, f"missing cache-bust on: {ref}"


def test_library_html_has_version_query(client):
    """Library page must have cache-bust version on all static asset references."""
    r = client.get("/library.html")
    assert r.status_code == 200
    body = r.text

    # Extract all src and href references to /js or /css
    refs = re.findall(r'(?:src|href)="(/(?:js|css)/[^"]+)"', body)
    assert len(refs) > 0, "No script/link refs found in library.html"

    for ref in refs:
        assert "?v=" in ref, f"missing cache-bust on: {ref}"


def test_version_query_is_not_dev_placeholder(client):
    """Version query should be substituted from git SHA, not the placeholder."""
    r = client.get("/")
    assert r.status_code == 200
    body = r.text

    # Should not contain the __VERSION__ placeholder
    assert "__VERSION__" not in body, "Placeholder __VERSION__ was not substituted"

    # Should contain actual version query params (e.g., ?v=abc1234 or ?v=dev)
    assert re.search(r'\?v=\w+', body), "No version query params found in HTML"


# ──────────────────────────────────────────────────────────────────
# Footgun guard: catch ANY new <script>/<link> tag added without
# the cache-bust suffix, not just /js/ and /css/ paths.
#
# Sigma flagged this in the PR #31 review: PR #32 added
# <script src="/js/editors/games/puzzle-lock.js"> with no ?v= and
# the existing /js-only regex wouldn't have caught a future tag
# under a different path. This stricter check fails on ANY
# internal asset reference missing ?v=.
# ──────────────────────────────────────────────────────────────────

_INTERNAL_ASSET_RE = re.compile(
    r"""<(?:script|link)[^>]+(?:src|href)=["']([^"']+)["']""",
    re.IGNORECASE,
)


def _internal_asset_refs(body: str) -> list[str]:
    """Return all <script src=...> / <link href=...> values that point at
    same-origin assets (skip http(s)://, data:, mailto:, fragment-only refs)."""
    refs = _INTERNAL_ASSET_RE.findall(body)
    return [
        r for r in refs
        if not r.startswith(("http://", "https://", "data:", "mailto:", "//", "#"))
    ]


@pytest.mark.parametrize("path", ["/", "/builder.html", "/library.html"])
def test_no_internal_script_or_link_tag_skips_cache_bust(client, path):
    """Strict variant: every same-origin <script src=> / <link href=> on
    every dashboard page must carry ?v=<sha>. Catches the footgun where a
    future PR adds a new tag under any path (not just /js/ or /css/) and
    forgets the suffix."""
    r = client.get(path)
    assert r.status_code == 200
    refs = _internal_asset_refs(r.text)
    assert refs, f"no internal asset refs found in {path}"
    for ref in refs:
        assert "?v=" in ref, (
            f"missing cache-bust on {path}: {ref}\n"
            f"add ?v=__VERSION__ to the tag, e.g. "
            f'<script src="{ref}?v=__VERSION__">'
        )
