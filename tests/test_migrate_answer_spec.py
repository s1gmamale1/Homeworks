"""Unit tests for scripts/migrate_answer_spec.py.

Targets reviewer issues 1, 2, 4, 8, 9:
  - memory_sprint key (#1) — fixed by using `memory_sprint` not `ms_questions`.
  - multi-root numeric collapse (#2) — set_match emitted when len(ans) > 1.
  - test coverage (#4) — these tests.
  - vacuous rubric (#8) — `rubric` key absent unless meaningful.
  - dry-run safety (#5) — no DB / fixture writes when --dry-run set.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

# Make scripts/ importable.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import migrate_answer_spec as m  # noqa: E402


# ---------------------------------------------------------------------------
# Pure spec-inference tests (no I/O)
# ---------------------------------------------------------------------------


def test_numeric_single_root() -> None:
    spec = m.infer_spec(["5"])
    assert spec["type"] == "numeric"
    assert spec["expected"] == 5
    assert spec["allow_ai_fallback"] is False
    assert "rubric" not in spec  # no vacuous placeholder rubric (#8)


def test_numeric_multi_root() -> None:
    """Reviewer issue #2: ans=['2','3'] must NOT collapse to a single numeric."""
    spec = m.infer_spec(["2", "3"])
    assert spec["type"] == "set_match"
    assert spec["expected"] == [2, 3]


def test_set_match_pm_form() -> None:
    """Single legacy answer 'pm 9' / multi-numeric string also yields set_match."""
    spec = m.infer_spec(["9, -9"])
    assert spec["type"] == "set_match"
    assert sorted(spec["expected"]) == [-9, 9]


def test_text_fuzzy_when_long_word() -> None:
    spec = m.infer_spec(["mitoxondriya"])
    assert spec["type"] == "text_fuzzy"
    assert spec["expected"] == "mitoxondriya"


def test_memory_sprint_key_works() -> None:
    """Reviewer issue #1: bucket name must be `memory_sprint` (not ms_questions)."""
    content = {
        "memory_sprint": [
            # MS items WITH legacy answers should migrate (rare but contract-supported).
            {"prompt": "What is 2+2?", "ans": ["4"]},
            # MS items without ans should be skipped (no answers to infer).
            {"prompt": "Pick A or B", "options": ["A", "B"], "correct": 0},
        ],
        "boss_questions": [],
        "gb_adaptive_quiz": [],
    }
    mutated = m.migrate_content(content)
    assert mutated is True
    assert "answer_spec" in content["memory_sprint"][0]
    assert content["memory_sprint"][0]["answer_spec"]["type"] == "numeric"
    assert "answer_spec" not in content["memory_sprint"][1]


def test_idempotent() -> None:
    content = {
        "boss_questions": [{"q": "x?", "ans": ["7"]}],
        "gb_adaptive_quiz": [],
        "memory_sprint": [],
    }
    assert m.migrate_content(content) is True
    snapshot = json.dumps(content, sort_keys=True)
    # Second pass: nothing should mutate.
    assert m.migrate_content(content) is False
    assert json.dumps(content, sort_keys=True) == snapshot


def test_dry_run_no_writes(tmp_path: Path) -> None:
    """Reviewer issue #5: --dry-run must not modify DB rows or fixtures."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """CREATE TABLE homeworks (
            id TEXT PRIMARY KEY,
            content_json TEXT
        )"""
    )
    payload = json.dumps(
        {"boss_questions": [{"q": "x?", "ans": ["7"]}], "gb_adaptive_quiz": [], "memory_sprint": []}
    )
    conn.execute("INSERT INTO homeworks (id, content_json) VALUES (?, ?)", ("HW-1", payload))
    conn.commit()
    conn.close()

    rc = m.main(["--db-path", str(db_path), "--skip-fixtures", "--dry-run"])
    assert rc == 0

    # Row content must be byte-identical.
    conn = sqlite3.connect(str(db_path))
    row = conn.execute("SELECT content_json FROM homeworks WHERE id = ?", ("HW-1",)).fetchone()
    conn.close()
    assert row[0] == payload, "dry-run wrote to the DB"


def test_db_real_write(tmp_path: Path) -> None:
    """End-to-end: real run actually persists answer_spec."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """CREATE TABLE homeworks (
            id TEXT PRIMARY KEY,
            content_json TEXT
        )"""
    )
    payload = json.dumps(
        {"boss_questions": [{"q": "roots?", "ans": ["2", "3"]}], "gb_adaptive_quiz": [], "memory_sprint": []}
    )
    conn.execute("INSERT INTO homeworks (id, content_json) VALUES (?, ?)", ("HW-2", payload))
    conn.commit()
    conn.close()

    # --force skips backup-size check; we have no backup folder anyway, but be explicit.
    rc = m.main(["--db-path", str(db_path), "--skip-fixtures", "--force"])
    assert rc == 0

    conn = sqlite3.connect(str(db_path))
    row = conn.execute("SELECT content_json FROM homeworks WHERE id = ?", ("HW-2",)).fetchone()
    conn.close()
    saved = json.loads(row[0])
    spec = saved["boss_questions"][0]["answer_spec"]
    assert spec["type"] == "set_match"
    assert spec["expected"] == [2, 3]


def test_no_legacy_answers_skipped() -> None:
    """Items without ans/accepted_answers must not gain a vacuous spec."""
    content = {
        "boss_questions": [{"q": "open-ended", "hint": "think hard"}],
        "gb_adaptive_quiz": [],
        "memory_sprint": [],
    }
    mutated = m.migrate_content(content)
    assert mutated is False
    assert "answer_spec" not in content["boss_questions"][0]
