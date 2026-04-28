"""
Wave F1 migration — create the `tutor_conversations` table + index.

Idempotent. Only owns `tutor_conversations`. Does NOT create `tutor_attempts`
(that table is owned by the grading-lane teammate).

Usage:
    python scripts/migrate_tutor_conversations.py [--db-path /path/to/nets.db] [--dry-run]

Safety rails:
  --db-path    SQLite DB path. Defaults to env NETS_DB_PATH or "nets.db".
  --dry-run    Print what would change without writing.

Wrapped in a single SQLite transaction so partial failure leaves the DB
untouched.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path


_TUTOR_CONVERSATIONS_DDL = """
CREATE TABLE IF NOT EXISTS tutor_conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    hw_id TEXT NOT NULL,
    phase TEXT NOT NULL,
    question_id TEXT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

_TUTOR_CONVERSATIONS_INDEX_DDL = """
CREATE INDEX IF NOT EXISTS idx_tutor_session
    ON tutor_conversations(session_id, hw_id, created_at)
"""


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    )
    return cur.fetchone() is not None


def _index_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='index' AND name=?",
        (name,),
    )
    return cur.fetchone() is not None


def migrate(db_path: Path, dry_run: bool) -> int:
    """Apply the migration. Returns 0 on success, non-zero on failure."""
    if not db_path.exists():
        # First-run case — caller should run `init_db()` instead, but we still
        # create the file rather than fail noisily so dry-run / fresh setups
        # behave predictably.
        print(f"  no SQLite DB at {db_path}; will be created on first connect")

    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        had_table = _table_exists(conn, "tutor_conversations")
        had_index = _index_exists(conn, "idx_tutor_session")

        if had_table and had_index:
            print("  tutor_conversations table + index already present — nothing to do")
            return 0

        # Plain execute() (not executescript()) keeps us inside the
        # transaction we open below, so dry-run can roll back cleanly.
        cur.execute("BEGIN")
        if not had_table:
            if dry_run:
                print("  [DRY] would CREATE TABLE tutor_conversations")
            else:
                cur.execute(_TUTOR_CONVERSATIONS_DDL)
                print("  created table tutor_conversations")
        if not had_index:
            if dry_run:
                print("  [DRY] would CREATE INDEX idx_tutor_session")
            else:
                cur.execute(_TUTOR_CONVERSATIONS_INDEX_DDL)
                print("  created index idx_tutor_session")

        if dry_run:
            conn.rollback()
        else:
            conn.commit()
        return 0
    except Exception as exc:
        if conn is not None:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
        print(f"  migration failed: {exc}")
        return 1
    finally:
        if conn is not None:
            conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Wave F1 — create tutor_conversations table + index (idempotent).",
    )
    parser.add_argument(
        "--db-path",
        default=os.getenv("NETS_DB_PATH", "nets.db"),
        help="SQLite DB path (default: $NETS_DB_PATH or ./nets.db).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without writing to the DB.",
    )
    args = parser.parse_args(argv)

    db_path = Path(args.db_path)
    print(f"Migrating tutor_conversations on {db_path} (dry_run={args.dry_run})")
    rc = migrate(db_path, args.dry_run)
    print("Done." if rc == 0 else f"FAILED (rc={rc})")
    return rc


if __name__ == "__main__":
    sys.exit(main())
