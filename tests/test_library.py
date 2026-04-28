"""
Tests for /api/library and /api/library/facets.

Covers:
  1. Empty-DB shape — empty list + total=0
  2. Subject filter — only matching rows returned
  3. Facets shape — keys subjects, grades, modes present

Uses the session-scoped `client` fixture from conftest.py. Each test wipes the
homeworks table first via direct DB access to keep tests independent of any
ordering or other test files in the suite.
"""
import asyncio
import os

import pytest


def _wipe_homeworks() -> None:
    """Hard-delete all homework rows so each test starts from a clean slate.

    Uses the same DB the TestClient app is bound to. We read DB_PATH from
    server.config (the already-resolved Path object) rather than re-reading
    os.environ so this stays consistent regardless of module-import order.
    """
    import aiosqlite
    from server.config import DB_PATH

    db_path = str(DB_PATH)

    async def _do() -> None:
        async with aiosqlite.connect(db_path) as db:
            await db.execute("DELETE FROM homework_versions")
            await db.execute("DELETE FROM homeworks")
            await db.commit()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_do())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


@pytest.fixture(autouse=True)
def _clean_db(client):
    """Reset the DB before every test in this module."""
    _wipe_homeworks()
    yield


def _post_homework(client, title: str, subject: str, grade: int, mode: str) -> str:
    payload = {"title": title, "subject": subject, "grade": grade, "mode": mode}
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, f"POST failed: {resp.status_code} {resp.text}"
    return resp.json()["id"]


def test_library_empty_db(client):
    """GET /api/library on an empty DB returns an empty page."""
    resp = client.get("/api/library")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data == {"items": [], "total": 0}


def test_library_filter_by_subject(client):
    """Subject filter returns only rows whose subject matches."""
    # Two rows with subject="math-algebra", one with subject="biology"
    _post_homework(client, "Algebra A", "math-algebra", 8, "hard")
    _post_homework(client, "Algebra B", "math-algebra", 8, "hard")
    _post_homework(client, "Biology A", "biology",      8, "hard")

    resp = client.get("/api/library", params={"subject": "math-algebra"})
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["total"] == 2, data
    assert len(data["items"]) == 2
    for item in data["items"]:
        assert item["subject"] == "math-algebra"


def test_library_facets_shape(client):
    """Facets endpoint returns dict with subjects, grades, modes keys."""
    _post_homework(client, "Algebra X", "math-algebra", 8, "hard")
    _post_homework(client, "Biology Y", "biology",      9, "hard")

    resp = client.get("/api/library/facets")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert isinstance(data, dict)
    assert set(data.keys()) == {"subjects", "grades", "modes"}
    assert isinstance(data["subjects"], list)
    assert isinstance(data["grades"], list)
    assert isinstance(data["modes"], list)
    # Sanity: the values we just inserted should appear.
    assert "math-algebra" in data["subjects"]
    assert "biology" in data["subjects"]
    assert 8 in data["grades"]
    assert "hard" in data["modes"]


def test_library_chapter_extraction(client):
    """Verify that chapter is extracted from content_json.meta.section."""
    # 1. Create the homework (initial scaffold has empty section)
    payload = {
        "title": "Physics HW",
        "subject": "physics",
        "grade": 9,
        "mode": "easy"
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200
    hw_id = resp.json()["id"]

    # 2. Update with a real section
    update_payload = {
        "content_json": {
            "meta": {
                "section": "Chapter 1: Kinematics"
            }
        }
    }
    resp = client.put(f"/api/homeworks/{hw_id}", json=update_payload)
    assert resp.status_code == 200

    # 3. Check the library list
    resp = client.get("/api/library", params={"subject": "physics"})
    assert resp.status_code == 200
    data = resp.json()

    assert data["total"] == 1
    item = data["items"][0]
    assert item["chapter"] == "Chapter 1: Kinematics"

