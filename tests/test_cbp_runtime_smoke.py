"""Smoke tier — app boots, template renders, file size in expected range."""
from __future__ import annotations

from server.config import BASE_DIR


def test_app_still_imports():
    from server.app import app
    assert app is not None


def test_template_renders_via_index(client):
    resp = client.get("/")
    assert resp.status_code == 200


def test_health_endpoint_unchanged(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200


def test_template_size_grew_by_pr6_amount():
    """PR #6 adds ~283 LOC of HTML + JS. Template should now be ~1.09 MB."""
    path = BASE_DIR / "server" / "template" / "perfect_homework.html"
    size = path.stat().st_size
    assert 1_080_000 < size < 1_200_000, f"unexpected template size: {size}"
