"""Unit tests for scripts/migrate_answer_spec.py.

Targets reviewer issues 1, 2, 4, 8, 9:
  - memory_sprint key (#1) — fixed by using `memory_sprint` not `ms_questions`.
  - multi-root numeric collapse (#2) — set_match emitted when len(ans) > 1.
  - test coverage (#4) — these tests.
  - vacuous rubric (#8) — `rubric` key absent unless meaningful.
  - dry-run safety (#5) — no DB / fixture writes when --dry-run set.
"""

from __future__ import annotations

import gzip
import json
import sqlite3
import sys
import time
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
    """Reviewer issue #1: bucket name must be `memory_sprint` (not ms_questions).

    Wave E update: items with ``options[]+correct`` now receive an ``option_index``
    spec (the Wave E migration path).  Items with only legacy ``ans[]`` still get
    the legacy spec inference.
    """
    content = {
        "memory_sprint": [
            # MS items WITH legacy answers (no options/correct) — rare, legacy path.
            {"prompt": "What is 2+2?", "ans": ["4"]},
            # MS items with options+correct — Wave E option_index path.
            {"prompt": "Pick A or B", "options": ["A", "B"], "correct": 0},
        ],
        "boss_questions": [],
        "gb_adaptive_quiz": [],
    }
    mutated = m.migrate_content(content)
    assert mutated is True
    # Legacy-ans item → numeric spec via legacy infer path
    assert "answer_spec" in content["memory_sprint"][0]
    assert content["memory_sprint"][0]["answer_spec"]["type"] == "numeric"
    # options+correct item → option_index spec via Wave E path
    assert "answer_spec" in content["memory_sprint"][1]
    assert content["memory_sprint"][1]["answer_spec"]["type"] == "option_index"
    assert content["memory_sprint"][1]["answer_spec"]["expected"] == 0


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


# ---------------------------------------------------------------------------
# Backup sanity check tests (fix for #15)
# ---------------------------------------------------------------------------


def test_backup_sanity_no_backup_directory(tmp_path: Path) -> None:
    """First-run case: backups/ doesn't exist. Sanity check passes (skip it)."""
    db_path = tmp_path / "nets.db"
    db_path.write_text("dummy db", encoding="utf-8")

    # Create a temp dir and change to it so backups/ doesn't exist.
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    original_cwd = __import__("os").getcwd()
    try:
        __import__("os").chdir(str(work_dir))
        result = m._backup_size_sanity(db_path)
        assert result is True, "sanity check should pass when backups/ doesn't exist"
    finally:
        __import__("os").chdir(original_cwd)


def test_backup_sanity_recent_backup_passes(tmp_path: Path) -> None:
    """Fresh .gz file exists. Sanity check passes."""
    db_path = tmp_path / "nets.db"
    db_path.write_text("dummy db content", encoding="utf-8")

    work_dir = tmp_path / "work"
    work_dir.mkdir()
    backups_dir = work_dir / "backups"
    backups_dir.mkdir()

    # Create a fresh .db.gz backup (non-empty, mtime = now).
    backup_path = backups_dir / "nets.db.gz"
    with gzip.open(str(backup_path), "wb") as f:
        f.write(b"compressed backup content")

    original_cwd = __import__("os").getcwd()
    try:
        __import__("os").chdir(str(work_dir))
        result = m._backup_size_sanity(db_path)
        assert result is True, "sanity check should pass for a fresh non-empty backup"
    finally:
        __import__("os").chdir(original_cwd)


def test_backup_sanity_old_backup_fails(tmp_path: Path) -> None:
    """Backup with mtime > 24h ago. Sanity check fails."""
    db_path = tmp_path / "nets.db"
    db_path.write_text("dummy db content", encoding="utf-8")

    work_dir = tmp_path / "work"
    work_dir.mkdir()
    backups_dir = work_dir / "backups"
    backups_dir.mkdir()

    # Create a .db.gz backup with mtime from >24h ago.
    backup_path = backups_dir / "nets.db.gz"
    with gzip.open(str(backup_path), "wb") as f:
        f.write(b"compressed backup content")

    # Set mtime to 48 hours in the past.
    old_time = time.time() - (48 * 3600)
    __import__("os").utime(str(backup_path), (old_time, old_time))

    original_cwd = __import__("os").getcwd()
    try:
        __import__("os").chdir(str(work_dir))
        result = m._backup_size_sanity(db_path)
        assert result is False, "sanity check should fail for a backup older than 24 hours"
    finally:
        __import__("os").chdir(original_cwd)


# ---------------------------------------------------------------------------
# Wave E: migrate_memory_sprint tests
# ---------------------------------------------------------------------------


def test_migrate_memory_sprint_basic() -> None:
    """migrate_memory_sprint adds option_index answer_spec from correct + options."""
    item = {
        "type": "KO",
        "prompt": "Kvadrat tenglamaning discriminantini toping",
        "options": ["D = b²-4ac", "D = b+4ac", "D = 2b-ac", "D = b²+4ac"],
        "correct": 0,
    }
    changed = m.migrate_memory_sprint(item)
    assert changed is True
    spec = item["answer_spec"]
    assert spec["type"] == "option_index"
    assert spec["expected"] == 0
    assert spec["option_count"] == 4
    assert spec["allow_ai_fallback"] is False
    assert spec["canonical_display"] == "D = b²-4ac"


def test_migrate_memory_sprint_idempotent() -> None:
    """migrate_memory_sprint is idempotent — second call returns False."""
    item = {
        "type": "TF",
        "prompt": "Fotosintez o'simliklarda sodir bo'ladi",
        "options": ["To'g'ri", "Noto'g'ri"],
        "correct": 0,
    }
    assert m.migrate_memory_sprint(item) is True
    # Second call — already has answer_spec
    assert m.migrate_memory_sprint(item) is False


def test_migrate_memory_sprint_via_migrate_content() -> None:
    """migrate_content routes memory_sprint items through migrate_memory_sprint."""
    content = {
        "boss_questions": [],
        "gb_adaptive_quiz": [],
        "memory_sprint": [
            {
                "type": "YNNG",
                "prompt": "Insoniyat Mars sayyorasiga bordi",
                "options": ["Ha", "Yo'q", "Ma'lum emas"],
                "correct": 1,
            }
        ],
    }
    mutated = m.migrate_content(content)
    assert mutated is True
    spec = content["memory_sprint"][0]["answer_spec"]
    assert spec["type"] == "option_index"
    assert spec["expected"] == 1
    assert spec["option_count"] == 3
    assert spec["canonical_display"] == "Yo'q"


# ---------------------------------------------------------------------------
# Wave E expansion: real_life and gb_why_chain tests
# ---------------------------------------------------------------------------


def test_migrate_real_life_basic() -> None:
    """migrate_real_life adds option_index spec to a q-item with options+correct."""
    item = {
        "prompt": "Qaysi biri to'g'ri javob?",
        "options": ["A variant", "B variant", "C variant"],
        "correct": 2,
    }
    changed = m.migrate_real_life(item)
    assert changed is True
    spec = item["answer_spec"]
    assert spec["type"] == "option_index"
    assert spec["expected"] == 2
    assert spec["option_count"] == 3
    assert spec["allow_ai_fallback"] is False
    assert spec["canonical_display"] == "C variant"


def test_migrate_real_life_skips_open_ended() -> None:
    """migrate_real_life leaves open-ended items (no options) untouched."""
    item = {
        "prompt": "DNK tarkibini tushuntiring.",
        "ans": "adenin, guanin, sitozin, timin",
        "fb": "To'g'ri.",
    }
    changed = m.migrate_real_life(item)
    assert changed is False
    assert "answer_spec" not in item


def test_migrate_real_life_idempotent() -> None:
    """Second migrate_real_life call on already-migrated item returns False."""
    item = {
        "prompt": "Qaysi organoid fotosintez qiladi?",
        "options": ["Mitoxondriya", "Xloroplast", "Yadro"],
        "correct": 1,
    }
    assert m.migrate_real_life(item) is True
    assert m.migrate_real_life(item) is False


def test_migrate_gb_why_chain_basic() -> None:
    """migrate_content routes gb_why_chain items through migrate_option_index."""
    content = {
        "boss_questions": [],
        "gb_adaptive_quiz": [],
        "memory_sprint": [],
        "gb_why_chain": [
            {
                "q": "Nima uchun bu formula ishlatiladi?",
                "options": ["Tezlikni topish uchun", "Kuchni topish uchun", "Energiyani topish uchun"],
                "correct": 1,
            }
        ],
    }
    mutated = m.migrate_content(content)
    assert mutated is True
    spec = content["gb_why_chain"][0]["answer_spec"]
    assert spec["type"] == "option_index"
    assert spec["expected"] == 1
    assert spec["option_count"] == 3
    assert spec["canonical_display"] == "Kuchni topish uchun"
