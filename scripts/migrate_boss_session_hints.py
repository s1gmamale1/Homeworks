"""
Boss-Arena migration — add hint/tally/shape columns to `boss_sessions`.

Idempotent. Adds the four Boss-Arena columns (spec §6 hint threading + the
per-session correctness tallies the outcome scorer reads):

  * hints_used     INTEGER DEFAULT 0
  * correct_count  INTEGER DEFAULT 0
  * total_attempts INTEGER DEFAULT 0
  * question_kind  TEXT

`init_db()` in server/db/migrations.py also applies these via guarded
ALTER TABLE statements; this standalone script mirrors that for operators who
prefer to run a one-off migration against a production DB without booting the
app.

Usage:
    python scripts/migrate_boss_session_hints.py [--db-path /path/to/nets.db] [--dry-run]

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


# (column, ALTER statement). Order does not matter — each is independently
# guarded by a column-exists check.
_NEW_COLUMNS: tuple[tuple[str, str], ...] = (
    ("hints_used", "ALTER TABLE boss_sessions ADD COLUMN hints_used INTEGER DEFAULT 0"),
    ("correct_count", "ALTER TABLE boss_sessions ADD COLUMN correct_count INTEGER DEFAULT 0"),
    ("total_attempts", "ALTER TABLE boss_sessions ADD COLUMN total_attempts INTEGER DEFAULT 0"),
    ("question_kind", "ALTER TABLE boss_sessions ADD COLUMN question_kind TEXT"),
)


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    )
    return cur.fetchone() is not None


def _existing_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}


def migrate(db_path: Path, dry_run: bool) -> int:
    """Apply the migration. Returns 0 on success, non-zero on failure."""
    if not db_path.exists():
        print(f"  no SQLite DB at {db_path}; run init_db() to create it first")
        # Nothing to migrate on a missing DB — init_db() will create the table
        # with the columns already present.
        return 0

    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        if not _table_exists(conn, "boss_sessions"):
            print("  boss_sessions table not present — run init_db() first; nothing to do")
            return 0

        existing = _existing_columns(conn, "boss_sessions")
        missing = [(col, ddl) for col, ddl in _NEW_COLUMNS if col not in existing]
        if not missing:
            print("  boss_sessions already has all Boss-Arena columns — nothing to do")
            return 0

        cur = conn.cursor()
        cur.execute("BEGIN")
        for col, ddl in missing:
            if dry_run:
                print(f"  [DRY] would add column boss_sessions.{col}")
            else:
                cur.execute(ddl)
                print(f"  added column boss_sessions.{col}")

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
        description="Boss-Arena — add hint/tally/shape columns to boss_sessions (idempotent).",
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
    print(f"Migrating boss_sessions columns on {db_path} (dry_run={args.dry_run})")
    rc = migrate(db_path, args.dry_run)
    print("Done." if rc == 0 else f"FAILED (rc={rc})")
    return rc


if __name__ == "__main__":
    sys.exit(main())
