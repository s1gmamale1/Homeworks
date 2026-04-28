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
