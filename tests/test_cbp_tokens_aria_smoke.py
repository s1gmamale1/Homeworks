"""Smoke tier — file existence + app boots + minimum size."""
from __future__ import annotations

from server.config import BASE_DIR


def test_tokens_css_file_exists():
    path = BASE_DIR / "frontend" / "css" / "_tokens.css"
    assert path.exists()
    assert path.is_file()


def test_tokens_css_non_empty():
    path = BASE_DIR / "frontend" / "css" / "_tokens.css"
    assert path.stat().st_size > 500


def test_landing_css_unchanged_in_pr4():
    """PR #4 explicitly does NOT touch landing.css (kept self-contained
    per its own header comment). Sanity-check it still imports."""
    path = BASE_DIR / "frontend" / "css" / "landing.css"
    assert path.exists()
    assert path.stat().st_size > 5000  # landing.css is large


def test_template_still_renders_after_link_addition(client):
    """Adding a stylesheet <link> should not break the runtime template."""
    resp = client.get("/")
    assert resp.status_code == 200


def test_app_still_imports():
    from server.app import app
    assert app is not None
