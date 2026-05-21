"""Smoke tier — boot health, import sanity, /api/health.

Fast checks (<5s total) that verify nothing about the PR #1 changes broke
the server's ability to come up at all.
"""
from __future__ import annotations


def test_app_imports_without_error():
    from server.app import app
    assert app is not None


def test_cbp_schemas_importable():
    from server.schemas.content import (
        CaseBasedPreview,
        Checkpoint,
        ContentJSON,
        FinalSimulation,
        LearningBlock,
    )
    assert all([CaseBasedPreview, Checkpoint, ContentJSON, FinalSimulation, LearningBlock])


def test_injector_object_constants_importable():
    from server.services.injector import _OBJECT_CONSTANTS
    assert isinstance(_OBJECT_CONSTANTS, list)
    # 5 entries after PR #1: memory_check, case_based_preview, reading, consolidation, reflection
    assert len(_OBJECT_CONSTANTS) >= 5


def test_health_endpoint_returns_200(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("status") == "ok"


def test_frontend_index_serves(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "<html" in resp.text.lower() or "<!doctype" in resp.text.lower()
