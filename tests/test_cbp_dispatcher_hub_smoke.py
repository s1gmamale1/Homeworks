"""Smoke tier — app boots, template is healthy, no regression on /."""
from __future__ import annotations

from server.config import BASE_DIR


def test_app_still_imports():
    from server.app import app
    assert app is not None


def test_template_renders_in_static_path(client):
    """`/` serves index.html via the static-page render path. Verify it
    didn't break."""
    resp = client.get("/")
    assert resp.status_code == 200


def test_template_health_endpoint_intact(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200


def test_template_file_size_grew_modestly():
    """PR #5 adds ~112 LOC. Sanity check the file isn't suddenly huge or
    tiny."""
    path = BASE_DIR / "server" / "template" / "perfect_homework.html"
    size = path.stat().st_size
    assert 1_050_000 < size < 1_200_000, f"unexpected template size: {size}"
