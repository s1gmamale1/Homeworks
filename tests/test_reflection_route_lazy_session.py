"""Regression: reflection finalize/redo must lazy-create the sessions row.

The v2 React runtime generates session_ids client-side (localStorage) and
never tells the server about them — phase_attempts get inserted with the
session_id as a column, but `sessions(id=...)` is never populated by any
production code path. Before this fix, both `/api/runtime/reflection/finalize`
and `/api/runtime/reflection/redo` did `get_session() → None → 404`, which
meant EVERY real student got 404 SESSION_NOT_FOUND when they hit the debrief.

The fix: `ensure_session(session_id, hw_id)` get-or-creates the row before
the engine runs (so `_write_session_mark` can actually persist the verdict
instead of UPDATE-no-op'ing on a missing row).

These tests fail on the pre-fix code:
  • `test_finalize_lazy_creates_missing_session_row` — pre-fix returns 404,
    post-fix returns 200 AND a sessions row materializes.
  • `test_redo_lazy_creates_missing_session_row` — same shape for redo.
  • `test_finalize_existing_session_row_untouched` — guards idempotency:
    finalize on a pre-existing sessions row must not duplicate or overwrite.
"""
from __future__ import annotations

import asyncio
import uuid

import pytest

from server.db.session_repo import create_session, get_session


def _run(coro):
    """Run an async coroutine in a fresh event loop.

    Python 3.14 raises if you call `asyncio.get_event_loop()` outside a running
    loop — and TestClient uses its own internal loop, so we cannot reuse it
    from sync test code. A fresh loop per call is the safe pattern.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _row_exists_for(session_id: str) -> bool:
    return _run(get_session(session_id)) is not None


def _stub_engine(monkeypatch):
    """Patch out the heavy engine internals so the route test stays focused on
    the gate behavior (sessions-row materialization) and doesn't depend on
    attempt fixtures, gating, AI, or final_reports."""
    from server.services import reflection_engine

    async def fake_finalize(session_id, hw_id, reflection_answers=None):  # noqa: ARG001
        return {
            "verdict": "passed",
            "verdict_label": "Tabriklaymiz",
            "overall_pct": 100,
            "band": {"key": "mastery", "name": "Mastery"},
            "divisions": [],
            "weak_points": [],
            "strong_points": [],
            "next_steps": [],
            "narrative": "stub",
            "encouragement": "stub",
            "redo_recommendation": "none",
            "mistake_repairs": 0,
            "ai_unavailable": True,
        }

    async def fake_redo(session_id, hw_id):  # noqa: ARG001
        return {"ok": True, "reshuffled": True, "cleared": 0}

    monkeypatch.setattr(reflection_engine, "finalize", fake_finalize)
    monkeypatch.setattr(reflection_engine, "redo", fake_redo)


def test_finalize_lazy_creates_missing_session_row(client, sample_homework, monkeypatch):
    """A fresh client-generated session_id (no row in `sessions`) must NOT
    return 404 — the route must lazy-create the row and proceed.

    Pre-fix behavior: 404 {"detail": {"code": "SESSION_NOT_FOUND"}}.
    Post-fix: 200 + the engine's debrief + a new row in the sessions table.
    """
    _stub_engine(monkeypatch)
    hw_id = sample_homework["id"]
    session_id = f"sess-{uuid.uuid4()}"

    # Sanity: precondition assertion — proves the test would be vacuous if the
    # sessions row already existed.
    assert not _row_exists_for(session_id), "test setup: session should not pre-exist"

    resp = client.post(
        "/api/runtime/reflection/finalize",
        json={"session_id": session_id, "hw_id": hw_id, "reflection_answers": ["x"]},
    )

    assert resp.status_code == 200, (
        f"Expected 200 (lazy-create), got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert body.get("verdict") in {"passed", "needs_retry"}
    # Post-condition: ensure_session must have actually inserted the row so
    # _write_session_mark inside the engine has something to UPDATE.
    assert _row_exists_for(session_id), (
        "ensure_session did not materialize the sessions row — "
        "_write_session_mark will silently no-op without it"
    )


def test_redo_lazy_creates_missing_session_row(client, sample_homework, monkeypatch):
    """Same lazy-create behavior for the redo route."""
    _stub_engine(monkeypatch)
    hw_id = sample_homework["id"]
    session_id = f"sess-{uuid.uuid4()}"

    assert not _row_exists_for(session_id), "test setup: session should not pre-exist"

    resp = client.post(
        "/api/runtime/reflection/redo",
        json={"session_id": session_id, "hw_id": hw_id},
    )

    assert resp.status_code == 200, (
        f"Expected 200 (lazy-create), got {resp.status_code}: {resp.text}"
    )
    assert resp.json() == {"ok": True, "reshuffled": True, "cleared": 0}
    assert _row_exists_for(session_id)


def test_finalize_existing_session_row_untouched(client, sample_homework, monkeypatch):
    """ensure_session must be idempotent — calling finalize on a session_id
    that ALREADY has a row in `sessions` must not duplicate or clobber it.
    """
    _stub_engine(monkeypatch)
    hw_id = sample_homework["id"]
    session_id = f"sess-{uuid.uuid4()}"
    pre_started_at = "2026-01-01T00:00:00+00:00"

    _run(create_session(session_id, hw_id, "pre-existing-student", pre_started_at))

    resp = client.post(
        "/api/runtime/reflection/finalize",
        json={"session_id": session_id, "hw_id": hw_id, "reflection_answers": []},
    )
    assert resp.status_code == 200, resp.text

    # The original started_at + student_name must survive — ensure_session
    # is get-or-create, not get-or-replace.
    row = _run(get_session(session_id))
    assert row is not None
    assert row.get("student_name") == "pre-existing-student"
    assert row.get("started_at") == pre_started_at
