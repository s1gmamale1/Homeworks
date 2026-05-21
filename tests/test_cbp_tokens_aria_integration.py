"""Integration tier — server serves `_tokens.css` and the runtime template
includes the link tag.
"""
from __future__ import annotations


def test_tokens_css_served_with_200(client):
    resp = client.get("/css/_tokens.css")
    assert resp.status_code == 200
    assert "text/css" in resp.headers.get("content-type", "").lower() or "css" in resp.headers.get("content-type", "").lower()


def test_tokens_css_response_contains_root_block(client):
    resp = client.get("/css/_tokens.css")
    assert ":root" in resp.text


def test_tokens_css_response_contains_zinc_tokens(client):
    resp = client.get("/css/_tokens.css")
    assert "--landing-zinc-950" in resp.text


def test_tokens_css_response_contains_a11y_rules(client):
    resp = client.get("/css/_tokens.css")
    assert ":focus-visible" in resp.text
    assert "@media (prefers-reduced-motion: reduce)" in resp.text
