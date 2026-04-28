"""
Wave B3 — tests for GET /api/homeworks pagination + search.

Covers:
  1. Default response shape
  2. ?q= title search
  3. ?subject= filter
  4. ?grade= filter
  5. ?limit= / ?offset= pagination consistency
"""
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create(client, title, subject="math-algebra", grade=8, mode="hard"):
    """Create a homework via POST and return the response dict."""
    resp = client.post("/api/homeworks", json={
        "title": title,
        "subject": subject,
        "grade": grade,
        "mode": mode,
    })
    assert resp.status_code == 200, f"POST /api/homeworks failed: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_default_response_shape(client):
    """GET /api/homeworks returns {items, total, limit, offset} with limit==50, offset==0."""
    resp = client.get("/api/homeworks")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, dict), "Response must be a dict, not a list"
    for key in ("items", "total", "limit", "offset"):
        assert key in body, f"Missing key: {key}"
    assert isinstance(body["items"], list)
    assert isinstance(body["total"], int)
    assert body["limit"] == 50
    assert body["offset"] == 0


def test_search_q_filters_by_title(client):
    """?q=Algebra returns only homeworks whose title contains 'Algebra'."""
    _create(client, "Algebra Practice Unique9a", subject="math-algebra", grade=8, mode="hard")
    _create(client, "Geometry Drill Unique9b", subject="geometriya-g7-11", grade=8, mode="hard")

    resp = client.get("/api/homeworks?q=Algebra+Practice+Unique9a")
    assert resp.status_code == 200
    body = resp.json()
    assert all("Algebra" in hw["title"] for hw in body["items"]), (
        f"Expected only Algebra homeworks, got: {[h['title'] for h in body['items']]}"
    )
    assert body["total"] >= 1


def test_filter_by_subject(client):
    """?subject=biology returns only biology homeworks."""
    _create(client, "Bio HW Unique8a", subject="biology", grade=7, mode="easy")
    _create(client, "Physics HW Unique8b", subject="physics", grade=7, mode="easy")

    resp = client.get("/api/homeworks?subject=biology")
    assert resp.status_code == 200
    body = resp.json()
    assert all(hw["subject"] == "biology" for hw in body["items"]), (
        f"Expected only biology items, got subjects: {[h['subject'] for h in body['items']]}"
    )
    assert body["total"] >= 1


def test_filter_by_grade(client):
    """?grade=5 returns only grade-5 homeworks."""
    _create(client, "Grade5 HW Unique7a", subject="math-algebra", grade=5, mode="easy")
    _create(client, "Grade8 HW Unique7b", subject="math-algebra", grade=8, mode="hard")

    resp = client.get("/api/homeworks?grade=5")
    assert resp.status_code == 200
    body = resp.json()
    assert all(hw["grade"] == 5 for hw in body["items"]), (
        f"Expected only grade-5 items, got grades: {[h['grade'] for h in body['items']]}"
    )
    assert body["total"] >= 1


def test_pagination_offset(client):
    """limit=2&offset=0 and limit=2&offset=2 together cover 4 items; total is consistent."""
    # Create 4 homeworks with a unique title prefix so we can count them
    for i in range(4):
        _create(client, f"PaginationTest Unique6 {i}", subject="history", grade=9, mode="hard")

    # First page
    resp0 = client.get("/api/homeworks?limit=2&offset=0&q=PaginationTest+Unique6")
    assert resp0.status_code == 200
    body0 = resp0.json()
    assert len(body0["items"]) == 2
    total = body0["total"]
    assert total >= 4

    # Second page
    resp2 = client.get("/api/homeworks?limit=2&offset=2&q=PaginationTest+Unique6")
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert len(body2["items"]) == 2

    # total is stable across pages
    assert body2["total"] == total

    # The two pages return distinct IDs
    ids0 = {hw["id"] for hw in body0["items"]}
    ids2 = {hw["id"] for hw in body2["items"]}
    assert ids0.isdisjoint(ids2), "Pages must not overlap"
