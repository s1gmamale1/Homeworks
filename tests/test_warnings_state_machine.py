"""Wave J — warning state machine tests.

Tests the evaluate() function in server/services/warnings.py against an
in-memory SQLite database so they're fast, isolated, and don't touch the
production DB.

Covers:
 1. 7 hard-severity events in a row → level 7, deduction_this=5, cumulative=5
 2. 8 in a row → level 8, deduction_this=10, big=True, cumulative=15
 3. 9 in a row → level 9, fail=True
 4. casual_safe 100× → never triggers
 5. insult_mild once → no warning record
 6. insult_mild 3× same category in last 5 → triggers warning
 7. Cross-session persistence: warnings on session A still count for session B
"""
from __future__ import annotations

import asyncio
import os
import tempfile
from unittest.mock import patch

import aiosqlite
import pytest


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_db_path(tmp_path):
    """Return a path to a fresh temp SQLite file and set NETS_DB_PATH."""
    db_file = tmp_path / "warnings_test.db"
    old = os.environ.get("NETS_DB_PATH")
    os.environ["NETS_DB_PATH"] = str(db_file)
    yield str(db_file)
    if old is None:
        os.environ.pop("NETS_DB_PATH", None)
    else:
        os.environ["NETS_DB_PATH"] = old


def _run(coro):
    """Run a coroutine in a fresh event loop (avoids loop-reuse issues in pytest)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _init_db_for_path(db_path: str) -> None:
    """Bootstrap the schema in the temp DB, reloading config to pick up env var."""
    # Force server.config to re-read the env var by reimporting or bypassing cache.
    async def _do():
        async with aiosqlite.connect(db_path) as conn:
            await conn.executescript("""
                CREATE TABLE IF NOT EXISTS tutor_warnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    hw_id TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    category TEXT NOT NULL,
                    matched_term TEXT,
                    warning_level INTEGER NOT NULL,
                    deduction_pct INTEGER DEFAULT 0,
                    is_big_warning INTEGER DEFAULT 0,
                    is_fail INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_warnings_hw
                    ON tutor_warnings(hw_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_warnings_session
                    ON tutor_warnings(session_id, hw_id, created_at);
            """)
            await conn.commit()

    _run(_do())


def _make_classification(
    severity: str = "profanity_mild",
    category: str = "en_profanity",
    lang: str = "en",
    matched_terms=None,
    is_clean: bool = False,
):
    from server.services.slur_filter import SlurClassification

    return SlurClassification(
        severity=severity,
        category=category,
        lang=lang,
        matched_terms=matched_terms or ([] if is_clean else ["testword"]),
        is_clean=is_clean,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_seven_hard_severities_gives_deduction(tmp_db_path):
    """7 hard-severity events → level 7, deduction_this=5, cumulative=5."""
    _init_db_for_path(tmp_db_path)

    from server.services import warnings as w
    import importlib
    # Patch db.connect to use our temp DB path
    with patch("server.db.get_db_path", return_value=__import__("pathlib").Path(tmp_db_path)):
        hw_id = "hw-test-7"
        sess = "sess-A"

        async def _run_eval(n: int):
            outcome = None
            for _ in range(n):
                outcome = await w.evaluate(
                    _make_classification("profanity_mild"),
                    hw_id=hw_id,
                    session_id=sess,
                )
            return outcome

        outcome = _run(_run_eval(7))

    assert outcome is not None
    assert outcome.triggered is True
    assert outcome.level == 7
    assert outcome.deduction_pct_this == 5
    assert outcome.cumulative_deduction_pct == 5
    assert outcome.is_big_warning is False
    assert outcome.is_fail is False


def test_eight_hard_severities_big_warning(tmp_db_path):
    """8 hard-severity events → level 8, big=True, cumulative=15."""
    _init_db_for_path(tmp_db_path)

    from server.services import warnings as w

    with patch("server.db.get_db_path", return_value=__import__("pathlib").Path(tmp_db_path)):
        hw_id = "hw-test-8"
        sess = "sess-A"

        async def _run_eval(n: int):
            outcome = None
            for _ in range(n):
                outcome = await w.evaluate(
                    _make_classification("profanity_strong"),
                    hw_id=hw_id,
                    session_id=sess,
                )
            return outcome

        outcome = _run(_run_eval(8))

    assert outcome is not None
    assert outcome.level == 8
    assert outcome.deduction_pct_this == 10
    assert outcome.cumulative_deduction_pct == 15  # 5 from level 7 + 10 from level 8
    assert outcome.is_big_warning is True
    assert outcome.is_fail is False


def test_nine_hard_severities_fail(tmp_db_path):
    """9 hard-severity events → level 9, fail=True."""
    _init_db_for_path(tmp_db_path)

    from server.services import warnings as w

    with patch("server.db.get_db_path", return_value=__import__("pathlib").Path(tmp_db_path)):
        hw_id = "hw-test-9"
        sess = "sess-A"

        async def _run_eval(n: int):
            outcome = None
            for _ in range(n):
                outcome = await w.evaluate(
                    _make_classification("slur_or_hate"),
                    hw_id=hw_id,
                    session_id=sess,
                )
            return outcome

        outcome = _run(_run_eval(9))

    assert outcome is not None
    assert outcome.is_fail is True
    assert outcome.level == 9
    # deduction_this at level 9 is 0 (fail path, no deduction added)
    assert outcome.deduction_pct_this == 0


def test_casual_safe_never_triggers(tmp_db_path):
    """casual_safe 100× → never triggers a warning record."""
    _init_db_for_path(tmp_db_path)

    from server.services import warnings as w

    with patch("server.db.get_db_path", return_value=__import__("pathlib").Path(tmp_db_path)):
        hw_id = "hw-safe"
        sess = "sess-A"

        async def _run_many():
            last = None
            for _ in range(100):
                last = await w.evaluate(
                    _make_classification("casual_safe", is_clean=True),
                    hw_id=hw_id,
                    session_id=sess,
                )
            return last

        outcome = _run(_run_many())

    assert outcome is not None
    assert outcome.triggered is False
    assert outcome.level == 0
    assert outcome.cumulative_deduction_pct == 0


def test_insult_mild_once_no_warning(tmp_db_path):
    """insult_mild once → no warning record (soft-severity gate not met)."""
    _init_db_for_path(tmp_db_path)

    from server.services import warnings as w

    with patch("server.db.get_db_path", return_value=__import__("pathlib").Path(tmp_db_path)):
        hw_id = "hw-insult-1"
        sess = "sess-A"

        async def _do():
            return await w.evaluate(
                _make_classification("insult_mild", category="uz_mild_insult"),
                hw_id=hw_id,
                session_id=sess,
            )

        outcome = _run(_do())

    assert outcome.triggered is False
    assert outcome.level == 0


def test_insult_mild_three_times_same_category_triggers(tmp_db_path):
    """insult_mild × 3 same category in last 5 → triggers warning."""
    _init_db_for_path(tmp_db_path)

    from server.services import warnings as w

    with patch("server.db.get_db_path", return_value=__import__("pathlib").Path(tmp_db_path)):
        hw_id = "hw-insult-3"
        sess = "sess-A"

        # First, manually seed 3 insult_mild warnings for the same category
        # via evaluate (each will not trigger since count < 3)
        # We need to use the "already have 3 in recent 5" path. Let's seed
        # them directly so that the 4th call sees 3 in recent 5.
        async def _seed_and_test():
            # Seed 3 rows directly into DB so list_recent_warnings returns them
            import aiosqlite
            from server.db import _now
            async with aiosqlite.connect(tmp_db_path) as conn:
                for i in range(3):
                    await conn.execute(
                        "INSERT INTO tutor_warnings "
                        "(session_id, hw_id, severity, category, matched_term, "
                        "warning_level, deduction_pct, is_big_warning, is_fail, created_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (sess, hw_id, "insult_mild", "uz_mild_insult",
                         "seed", i + 1, 0, 0, 0, _now()),
                    )
                await conn.commit()

            # Now call evaluate with the same category — should trigger
            return await w.evaluate(
                _make_classification("insult_mild", category="uz_mild_insult"),
                hw_id=hw_id,
                session_id=sess,
            )

        outcome = _run(_seed_and_test())

    # Should now trigger since same_cat_count >= 3
    assert outcome.triggered is True
    assert outcome.level == 4  # 3 seeded + 1 new


def test_cross_session_persistence(tmp_db_path):
    """Warnings from session A count towards the total when session B starts."""
    _init_db_for_path(tmp_db_path)

    from server.services import warnings as w

    with patch("server.db.get_db_path", return_value=__import__("pathlib").Path(tmp_db_path)):
        hw_id = "hw-cross-session"

        async def _do():
            # Session A fires 5 warnings
            for _ in range(5):
                await w.evaluate(
                    _make_classification("profanity_strong"),
                    hw_id=hw_id,
                    session_id="sess-A",
                )
            # Session B fires 1 warning — should see level 6
            return await w.evaluate(
                _make_classification("profanity_strong"),
                hw_id=hw_id,
                session_id="sess-B",
            )

        outcome = _run(_do())

    assert outcome.triggered is True
    assert outcome.level == 6  # 5 from session A + 1 from session B
