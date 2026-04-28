"""
Wave C housekeeping — tests for POST /api/homeworks favicon + content_json merge.

Covers:
  1. Favicon endpoint returns 200 + image/x-icon content-type
  2. POST without content_json uses empty scaffold
  3. POST with content_json merges it into scaffold
  4. POST with content_json.meta deep-merges meta fields
"""
import pytest


def test_favicon_returns_200(client):
    """GET /favicon.ico returns 200 with image content-type."""
    resp = client.get("/favicon.ico")
    assert resp.status_code == 200
    assert resp.headers.get("content-type", "").startswith("image/")
    assert resp.headers.get("cache-control") == "max-age=31536000"


def test_create_homework_default_scaffold(client):
    """POST without content_json → response has full empty_scaffold keys."""
    resp = client.post("/api/homeworks", json={
        "title": "Test HW Default",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
    })
    assert resp.status_code == 200
    body = resp.json()
    content = body.get("content_json", {})

    # Check all required scaffold keys are present
    for key in ("meta", "gate_quote", "panels", "flashcards", "memory_sprint",
                "gb_adaptive_quiz", "gb_why_chain", "gb_memory_match",
                "real_life", "boss_questions", "reflection"):
        assert key in content, f"Missing scaffold key: {key}"


def test_create_homework_respects_content_json(client):
    """POST with content_json merges it into scaffold."""
    resp = client.post("/api/homeworks", json={
        "title": "Test HW Content",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
        "content_json": {
            "boss_questions": [{"q": "What is 2+2?", "ans": ["4"]}],
            "flashcards": [{"front": "Q", "back": "A"}]
        }
    })
    assert resp.status_code == 200
    body = resp.json()
    content = body.get("content_json", {})

    # Custom values should be present
    assert len(content.get("boss_questions", [])) == 1
    assert content["boss_questions"][0]["q"] == "What is 2+2?"
    assert len(content.get("flashcards", [])) == 1

    # Other scaffold keys should still be there (empty)
    assert "panels" in content
    assert "memory_sprint" in content
    assert "meta" in content


def test_create_homework_meta_deep_merge(client):
    """POST with content_json.meta deep-merges meta fields."""
    resp = client.post("/api/homeworks", json={
        "title": "Test HW Meta",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
        "content_json": {
            "meta": {
                "section": "Unit 5",
                "cefr_level": "B2"
            }
        }
    })
    assert resp.status_code == 200
    body = resp.json()
    content = body.get("content_json", {})
    meta = content.get("meta", {})

    # Scaffold defaults should be present
    assert meta.get("title") == "Test HW Meta"
    assert meta.get("subject_display") == "math-algebra"

    # Custom meta fields should override
    assert meta.get("section") == "Unit 5"
    assert meta.get("cefr_level") == "B2"
