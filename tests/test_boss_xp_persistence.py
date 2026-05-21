"""Regression — boss `outcome_xp` must persist to `sessions.boss_xp_earned`.

Per `docs/audits/2026-05-09-engagement.md`, the `outcome_xp` value computed
at boss defeat was previously surfaced in the JSON response and then
discarded — never written to the DB. That left the XP signal entirely
ephemeral (closing the tab dropped it) and blocked downstream features
that need cross-session reward state (streak counter, results-screen
echo, future analytics).

This file pins:
  1. The new `session_repo.update_session_boss_xp` helper executes the
     UPDATE and persists the integer value.
  2. The migration adds the column with the documented default (0).
  3. The legacy `/api/ai/check-answer` (phase=final-boss) write site at
     `server/routes/ai.py` fires the helper inside the `done=True` branch
     and persists the same value surfaced in the response.
  4. The Plan-5 boss state machine (`server/routes/ai_plan5.py`) fires
     the helper inside the terminal-state branch — covered via a
     source-level regression assertion because the full integration
     requires LLM mocks the rest of this test file doesn't carry.
  5. Default-zero invariant: a freshly created session has
     `boss_xp_earned = 0` until a boss defeat fires.
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path
from unittest.mock import patch, AsyncMock

import pytest

import server.routes.ai as _ai_routes
from server.db import session_repo
from server.db.connection import connect


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _read_boss_xp(session_id: str):
    """Read sessions.boss_xp_earned for the given session row, or None if absent."""
    db = await connect()
    try:
        async with db.execute(
            "SELECT boss_xp_earned FROM sessions WHERE id = ?", (session_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None
    finally:
        await db.close()


def _seed_homework(client) -> str:
    """Insert a homework with one boss question and return hw_id."""
    payload = {
        "title": "Boss XP test HW",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
        "family": "aniq-fanlar",
        "content_json": {
            "meta": {"title": "Boss XP test HW"},
            "panels": [],
            "flashcards": [],
            "boss_questions": [
                {
                    "id": "bq_001",
                    "q": "2 + 2 nechi?",
                    "ans": ["4"],
                    "accepted_answers": ["4"],
                    "answer_spec": {"kind": "equality", "expected": ["4"]},
                    "dmg": 10,
                },
            ],
        },
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _mock_boss_turn(*, correct: bool = True, damage: int = 10, done: bool = False) -> AsyncMock:
    """tutor.boss_turn mock — minimal shape matching the legacy contract."""
    payload: dict = {
        "correct": correct,
        "damage_dealt": damage if correct else 0,
        "boss_response": "Mock",
        "hint": None,
        "score": 1.0 if correct else 0.0,
        "axis_1": 4 if correct else 1,
        "axis_2": 4 if correct else 1,
        "axis_1_label": "Mastered" if correct else "Novice",
        "axis_2_label": "Mastered" if correct else "Novice",
    }
    if done:
        payload["done"] = True
    return AsyncMock(return_value=payload)


@pytest.fixture(autouse=True)
def _wipe_fb_attempts():
    """Reset the in-memory FB attempt tracker between tests."""
    _ai_routes._FB_ATTEMPTS.clear()
    yield
    _ai_routes._FB_ATTEMPTS.clear()


@pytest.fixture
def hw_id(client):
    """Seed a homework once per test and return its id. Needed so the
    session row's FK -> homeworks(id) constraint is satisfied; the temp DB
    runs with PRAGMA foreign_keys = ON per server/db/connection.py."""
    return _seed_homework(client)


# ---------------------------------------------------------------------------
# 1. Helper unit tests
# ---------------------------------------------------------------------------


def test_helper_writes_value_directly(client, hw_id):
    """update_session_boss_xp executes the UPDATE and reads back."""
    sid = "test-helper-write"
    asyncio.run(session_repo.create_session(sid, hw_id, "Test", "2026-05-21T10:00:00"))
    asyncio.run(session_repo.update_session_boss_xp(sid, 7500))
    assert asyncio.run(_read_boss_xp(sid)) == 7500


def test_helper_overwrites_previous_value(client, hw_id):
    """Last-write-wins on duplicate defeat (retry path, no DB uniqueness gate)."""
    sid = "test-overwrite"
    asyncio.run(session_repo.create_session(sid, hw_id, "Test", "2026-05-21T10:00:00"))
    asyncio.run(session_repo.update_session_boss_xp(sid, 100))
    asyncio.run(session_repo.update_session_boss_xp(sid, 999))
    assert asyncio.run(_read_boss_xp(sid)) == 999


# ---------------------------------------------------------------------------
# 2. Default-zero invariant
# ---------------------------------------------------------------------------


def test_default_zero_when_no_boss(client, hw_id):
    """A newly created session row carries the column default (0) until a
    boss defeat writes over it. Without the migration this would fail with
    an absent-column error."""
    sid = "test-default-zero"
    asyncio.run(session_repo.create_session(sid, hw_id, "Test", "2026-05-21T10:00:00"))
    assert asyncio.run(_read_boss_xp(sid)) == 0


# ---------------------------------------------------------------------------
# 3. Legacy `/api/ai/check-answer` (phase=final-boss) integration
# ---------------------------------------------------------------------------


def test_legacy_boss_turn_persists_on_done(client, hw_id):
    """Legacy adapter at server/routes/ai.py:`_check_answer_final_boss` —
    on `done=True` from tutor.boss_turn, the route computes outcome_xp via
    `_boss_outcome_for` and MUST persist it to sessions.boss_xp_earned."""
    sid = "test-legacy-done"
    asyncio.run(session_repo.create_session(sid, hw_id, "Test", "2026-05-21T10:00:00"))

    with patch.object(_ai_routes.tutor, "boss_turn",
                      new=_mock_boss_turn(correct=True, damage=10, done=True)):
        resp = client.post("/api/ai/check-answer", json={
            "phase": "final-boss",
            "homework_id": hw_id,
            "session_id": sid,
            "question_id": "bq_001",
            "student_answer": "4",
            "attempt_number": 1,
            "hp_remaining": 80,    # 80% of grade-8 default 100 → 3-star path
            "attempts_used": 0,
        })

    assert resp.status_code == 200, resp.text
    body = resp.json()
    surfaced_xp = body.get("outcome_xp")
    assert isinstance(surfaced_xp, int) and surfaced_xp > 0, (
        f"outcome_xp should surface on done=True, got: {body}"
    )
    persisted = asyncio.run(_read_boss_xp(sid))
    assert persisted == surfaced_xp, (
        f"sessions.boss_xp_earned ({persisted}) must equal response outcome_xp "
        f"({surfaced_xp}) — without persistence the value is discarded after response."
    )


def test_legacy_boss_turn_does_not_persist_when_not_done(client, hw_id):
    """Mid-fight turns (no `done` key) must NOT touch boss_xp_earned —
    the column stays at the default 0 until the boss is actually defeated.
    Without this guard, every wrong-answer turn would zero out the column
    on retry, breaking the last-write-wins semantics for genuine defeat."""
    sid = "test-not-done"
    asyncio.run(session_repo.create_session(sid, hw_id, "Test", "2026-05-21T10:00:00"))

    with patch.object(_ai_routes.tutor, "boss_turn",
                      new=_mock_boss_turn(correct=True, damage=10, done=False)):
        resp = client.post("/api/ai/check-answer", json={
            "phase": "final-boss",
            "homework_id": hw_id,
            "session_id": sid,
            "question_id": "bq_001",
            "student_answer": "4",
            "attempt_number": 1,
            "hp_remaining": 50,
            "attempts_used": 0,
        })

    assert resp.status_code == 200, resp.text
    assert "outcome_xp" not in resp.json(), (
        "outcome_xp must not surface on in-progress turns"
    )
    assert asyncio.run(_read_boss_xp(sid)) == 0, (
        "boss_xp_earned must stay at default 0 until done=True fires"
    )


# ---------------------------------------------------------------------------
# 4. Plan-5 path — source-level regression (full integration needs LLM mocks)
# ---------------------------------------------------------------------------


def test_plan5_route_persists_xp_in_terminal_branch():
    """Static-source assertion: server/routes/ai_plan5.py MUST call
    session_repo.update_session_boss_xp inside the `if new_status != "active":`
    branch in submit_answer. Without this guard, a future refactor of the
    boss state machine could silently drop the persist hook and the dynamic-
    boss path would regress to the pre-PR-B behaviour where XP vanishes
    after the response."""
    src = Path("server/routes/ai_plan5.py").read_text(encoding="utf-8")

    assert "session_repo.update_session_boss_xp" in src, (
        "ai_plan5.py must persist outcome_xp at boss terminal state. "
        "Expected call: session_repo.update_session_boss_xp(session_id, xp). "
        "See the `if new_status != \"active\":` block in submit_answer."
    )

    pattern = re.compile(
        r'if\s+new_status\s*!=\s*"active":[\s\S]{0,1500}?session_repo\.update_session_boss_xp',
    )
    assert pattern.search(src), (
        "Persist call must be inside the terminal-state branch, not unconditional. "
        "Otherwise every in-flight answer submission would zero the column."
    )


def test_plan5_imports_session_repo():
    """Static-source assertion: the new persist call requires session_repo
    in scope. Catches the regression where the call is added but the import
    is forgotten — would fail at import time, not test time."""
    src = Path("server/routes/ai_plan5.py").read_text(encoding="utf-8")
    pattern = re.compile(
        r'from\s+\.\.db\s+import\s+[^\n]*\bsession_repo\b'
    )
    assert pattern.search(src), (
        "ai_plan5.py must `from ..db import session_repo` (or include it in "
        "the existing multi-import). Otherwise the persist call NameErrors."
    )


def test_legacy_ai_route_persists_xp_in_done_branch():
    """Static-source assertion: server/routes/ai.py must persist inside
    the `if done:` block in the FB check-answer adapter — the same line
    range that already writes response['outcome_xp']."""
    src = Path("server/routes/ai.py").read_text(encoding="utf-8")

    assert "session_repo.update_session_boss_xp" in src, (
        "ai.py legacy adapter must persist outcome_xp on done=True."
    )

    pattern = re.compile(
        r'response\["outcome_xp"\]\s*=\s*int\(outcome_xp\)[\s\S]{0,400}?session_repo\.update_session_boss_xp',
    )
    assert pattern.search(src), (
        "Persist call must follow the response['outcome_xp'] assignment in the "
        "done branch. Without this ordering, the value isn't surfaced or saved together."
    )


def test_legacy_ai_route_imports_session_repo():
    """Static-source assertion: ai.py must import session_repo."""
    src = Path("server/routes/ai.py").read_text(encoding="utf-8")
    pattern = re.compile(r'from\s+\.\.db\s+import\s+session_repo')
    assert pattern.search(src), (
        "ai.py must `from ..db import session_repo`. Otherwise the persist call NameErrors."
    )


# ---------------------------------------------------------------------------
# 5. Migration column existence
# ---------------------------------------------------------------------------


def test_migration_added_boss_xp_earned_column(client):
    """The migrations tuple in db/migrations.py must contain the ALTER TABLE
    that adds boss_xp_earned. Without this the column is absent on existing
    DBs that predate the migration."""
    src = Path("server/db/migrations.py").read_text(encoding="utf-8")
    pattern = re.compile(
        r'ALTER\s+TABLE\s+sessions\s+ADD\s+COLUMN\s+boss_xp_earned\s+INTEGER',
        re.IGNORECASE,
    )
    assert pattern.search(src), (
        "migrations.py must contain the ALTER TABLE sessions ADD COLUMN "
        "boss_xp_earned INTEGER ... migration in the existing batched tuple."
    )

    # Runtime check: the column actually exists in the test DB.
    async def _check():
        db = await connect()
        try:
            async with db.execute("PRAGMA table_info(sessions)") as cur:
                cols = [row[1] for row in await cur.fetchall()]
                return cols
        finally:
            await db.close()

    cols = asyncio.run(_check())
    assert "boss_xp_earned" in cols, (
        f"boss_xp_earned column missing from sessions table. Columns: {cols}"
    )
