"""
Wave A2 — conftest.py
Shared fixtures for the NETS AI runtime smoke tests.
"""
import os
import tempfile
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Skip marker: tests that call the real AI model
# ---------------------------------------------------------------------------

def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "requires_ai: mark test as needing a live AI backend (Vertex / Gemini / Kimi). "
        "Auto-skipped when no credentials are available.",
    )


def _ai_available() -> bool:
    """Return True if at least one AI backend credential is configured and reachable."""
    vertex_path = os.environ.get("VERTEX_CREDENTIALS_PATH", "")
    if vertex_path and os.path.exists(vertex_path):
        return True
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    if gemini_key and gemini_key not in ("", "your_api_key_here"):
        return True
    if os.environ.get("KIMI_API_KEY", ""):
        return True
    return False


def pytest_collection_modifyitems(config, items):
    """Auto-skip @pytest.mark.requires_ai tests when no creds are present."""
    if _ai_available():
        return  # don't skip anything
    skip_marker = pytest.mark.skip(reason="No AI credentials found (VERTEX_CREDENTIALS_PATH / GEMINI_API_KEY / KIMI_API_KEY)")
    for item in items:
        if item.get_closest_marker("requires_ai"):
            item.add_marker(skip_marker)


# ---------------------------------------------------------------------------
# App client fixture — uses in-process TestClient (no real network calls for
# routing; AI calls DO go out if creds are present).
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def client():
    """
    Spin up the FastAPI app via httpx TestClient.
    Uses a temporary SQLite DB so tests never touch production data.
    The DB path is injected before import so server.config picks it up.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_db = os.path.join(tmpdir, "test_nets.db")
        # Override DB_PATH before the app module is loaded
        os.environ.setdefault("NETS_DB_PATH", tmp_db)

        # Import app AFTER env is patched
        from server.app import app
        from server import db as _db
        import asyncio

        # Init the temp DB schema (Python 3.10+ requires a new loop explicitly)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_db.init_db())
        finally:
            loop.close()
            asyncio.set_event_loop(None)

        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


# ---------------------------------------------------------------------------
# Sample homework fixture — inserts a minimal homework so AI endpoints have
# a plausible anchor (subject/grade context is passed in request bodies,
# not fetched from DB, so this is primarily for documentation / future use).
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def sample_homework(client):
    """
    Insert one homework record into the temp DB and return its dict.
    Uses the REST API so it exercises the actual create path.
    """
    payload = {
        "title": "Algebra smoke-test HW",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
        "family": "aniq-fanlar",
        "content_json": {"flashcards": [], "boss": {"questions": []}},
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, f"Failed to create sample homework: {resp.text}"
    return resp.json()
