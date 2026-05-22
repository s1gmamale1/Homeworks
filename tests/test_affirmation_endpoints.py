"""Tests for the authorship-affirmation HTTP surface (research §9.6).

Covers:
  - POST /api/integrity/affirm        -> 200 + a record carrying a new id
  - GET  /api/integrity/affirmations  -> returns the created record (filtered)
  - resolve_queue_ids linkage         -> resolves a seeded review-queue item
  - empty session                     -> []
  - the read-only <pre> view surface

Integrity here is teacher intelligence: affirmations compute no grade and no
verdict. These tests exercise the real router + repo against the temp DB the
``client`` fixture initialises (schema includes ``authorship_affirmations``).
"""
from __future__ import annotations

import asyncio
import os

import aiosqlite


# ---------------------------------------------------------------------------
# Helpers — seed/read review-queue rows directly so we can test the linkage.
# ---------------------------------------------------------------------------


def _seed_review_item(question_id: str, student_answer: str) -> None:
    """Insert one pending review_queue row into the temp DB (sync wrapper)."""
    db_path = os.environ.get("NETS_DB_PATH")
    assert db_path, "client fixture must set NETS_DB_PATH"

    async def _do() -> None:
        from server import db as _db  # uses the same NETS_DB_PATH

        await _db.add_to_review_queue(
            question_id=question_id,
            student_answer=student_answer,
            answer_spec={"type": "semantic", "expected": "x"},
            ai_response={"confidence": 0.4, "score": 0.5},
        )

    _run(_do())


def _review_status(item_id: int) -> str | None:
    """Return the status of a review_queue row (or None if absent)."""
    db_path = os.environ.get("NETS_DB_PATH")

    async def _do() -> str | None:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT status FROM review_queue WHERE id = ?", (item_id,)
            )
            row = await cur.fetchone()
            return row["status"] if row else None

    return _run(_do())


def _run(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


# ---------------------------------------------------------------------------
# POST /affirm + GET round-trip
# ---------------------------------------------------------------------------


def test_affirm_creates_record_and_returns_id(client):
    resp = client.post(
        "/api/integrity/affirm",
        json={
            "session_id": "sess-aff-1",
            "homework_id": "hw-aff-1",
            "teacher_id": "teacher-7",
            "affirmed": True,
            "note": "Reviewed in person; student walked me through the work.",
            "checkpoints": ["intro", "boss"],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    aff = body["affirmation"]
    assert isinstance(aff["id"], int) and aff["id"] > 0
    assert aff["session_id"] == "sess-aff-1"
    assert aff["affirmed"] is True
    assert aff["checkpoints"] == ["intro", "boss"]
    assert body["resolved_queue_ids"] == []


def test_get_affirmations_returns_created_record(client):
    client.post(
        "/api/integrity/affirm",
        json={"session_id": "sess-aff-2", "homework_id": "hw-aff-2", "affirmed": False},
    )
    resp = client.get("/api/integrity/affirmations", params={"session_id": "sess-aff-2"})
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert isinstance(rows, list) and len(rows) >= 1
    assert all(r["session_id"] == "sess-aff-2" for r in rows)
    # affirmed normalised to a bool, not SQLite's 0/1.
    assert rows[0]["affirmed"] is False


def test_get_affirmations_filters_by_homework(client):
    client.post(
        "/api/integrity/affirm",
        json={"session_id": "sess-aff-3", "homework_id": "hw-filter-A", "affirmed": True},
    )
    client.post(
        "/api/integrity/affirm",
        json={"session_id": "sess-aff-3", "homework_id": "hw-filter-B", "affirmed": True},
    )
    resp = client.get(
        "/api/integrity/affirmations",
        params={"session_id": "sess-aff-3", "homework_id": "hw-filter-A"},
    )
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["homework_id"] == "hw-filter-A"


def test_empty_session_returns_empty_list(client):
    resp = client.get(
        "/api/integrity/affirmations",
        params={"session_id": "sess-does-not-exist-xyz"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# resolve_queue_ids linkage
# ---------------------------------------------------------------------------


def test_resolve_queue_ids_resolves_seeded_review_item(client):
    _seed_review_item("q-aff-link", "an answer to review")
    # Read the queue back through the API to learn the row id.
    queue = client.get("/api/ai/review-queue").json()
    item = next(q for q in queue if q["question_id"] == "q-aff-link")
    assert _review_status(item["id"]) == "pending"

    resp = client.post(
        "/api/integrity/affirm",
        json={
            "session_id": "sess-aff-link",
            "homework_id": "hw-aff-link",
            "teacher_id": "teacher-9",
            "affirmed": True,
            "resolve_queue_ids": [item["id"]],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["resolved_queue_ids"] == [item["id"]]
    # The affirmation row records which queue items it covered.
    assert body["affirmation"]["integrity_queue_ids"] == [item["id"]]
    # And the review item is actually resolved (no longer pending).
    assert _review_status(item["id"]) == "resolved"


def test_resolve_nonexistent_queue_id_is_ignored_not_fatal(client):
    resp = client.post(
        "/api/integrity/affirm",
        json={
            "session_id": "sess-aff-ghost",
            "homework_id": "hw-aff-ghost",
            "affirmed": False,
            "resolve_queue_ids": [999999],
        },
    )
    assert resp.status_code == 200, resp.text
    # A ghost id resolves nothing but the affirmation still records.
    assert resp.json()["resolved_queue_ids"] == []
    assert isinstance(resp.json()["affirmation"]["id"], int)


# ---------------------------------------------------------------------------
# Read-only <pre> view
# ---------------------------------------------------------------------------


def test_affirmations_view_returns_pre_html(client):
    client.post(
        "/api/integrity/affirm",
        json={"session_id": "sess-aff-view", "homework_id": "hw-aff-view", "affirmed": True},
    )
    resp = client.get("/api/integrity/affirmations/view", params={"session_id": "sess-aff-view"})
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "<pre>" in resp.text
    assert "sess-aff-view" in resp.text
