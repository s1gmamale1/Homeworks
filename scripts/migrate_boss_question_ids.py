"""
Backfill `id` field on every `content_json.boss_questions[i]` that lacks one.

Idempotent. Touches both fixture JSON files and the SQLite homeworks table.

Why this migration exists:
    Boss-phase grading routes (`/api/ai/check-answer?phase=final-boss`) look
    up the question by id from the persisted row. Older rows (and any row
    saved by a client that doesn't stamp ids) have id-less boss_questions.
    The injector synthesizes ids at render time, but the route can't reverse
    that mapping at request time without help. Stamping ids on disk closes
    the gap once and for all. New rows get this for free via the write-time
    normalizer in routes/homework.py.

Format:
    Missing/empty `id` becomes `bq_{i}` (zero-indexed). Author-supplied ids
    are preserved. The route lookup also accepts the legacy `Q{i+1}` format
    as a transitional fallback (see _fb_find_boss_question).

Usage:
    python scripts/migrate_boss_question_ids.py --db-path /path/to/nets.db [--dry-run] [--backup-first] [--force]

Safety rails:
  --db-path        Required for DB writes. Defaults to env NETS_DB_PATH or "nets.db".
  --dry-run        Print what would change without writing fixtures or rows.
  --backup-first   Run scripts/backup_db.sh before any UPDATE. Aborts if backup fails.
  --force          Skip the backup-size sanity check.

The migration runs inside a single SQLite transaction so partial failure
leaves the DB untouched. Soft-deleted rows (deleted_at IS NOT NULL) are
included so trashed homeworks restored later already have ids.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path


# ---------------------------------------------------------------------------
# Migration logic (pure, exposed for tests)
# ---------------------------------------------------------------------------


def migrate_boss_questions(content: dict) -> int:
    """Stamp `id = bq_{i}` on every id-less boss_question. Returns count assigned.

    Mutates `content` in place. Author-supplied ids are preserved. Idempotent
    (safe to re-run on already-migrated content).
    """
    if not isinstance(content, dict):
        return 0
    bq = content.get("boss_questions")
    if not isinstance(bq, list):
        return 0
    assigned = 0
    for i, item in enumerate(bq):
        if not isinstance(item, dict):
            continue
        if not item.get("id"):
            item["id"] = f"bq_{i}"
            assigned += 1
    return assigned


# ---------------------------------------------------------------------------
# Fixture / DB drivers
# ---------------------------------------------------------------------------


def process_fixtures(dry_run: bool) -> tuple[int, int]:
    """Returns (files_touched, total_ids_assigned)."""
    fixtures_dir = Path("fixtures")
    if not fixtures_dir.exists():
        return (0, 0)

    files_touched = 0
    total_assigned = 0
    for p in sorted(fixtures_dir.glob("*.json")):
        try:
            content = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"  skip {p.name}: {exc}")
            continue
        n = migrate_boss_questions(content)
        if n:
            files_touched += 1
            total_assigned += n
            if dry_run:
                print(f"  [DRY] would update {p.name} (+{n} ids)")
            else:
                p.write_text(
                    json.dumps(content, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                print(f"  updated {p.name} (+{n} ids)")
    return (files_touched, total_assigned)


def _backup_db(db_path: Path) -> bool:
    script = Path("scripts/backup_db.sh")
    if not script.exists():
        print(f"  backup script {script} not found")
        return False
    try:
        result = subprocess.run(
            ["bash", str(script), str(db_path)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            print(f"  backup failed (exit {result.returncode}): {result.stderr.strip()}")
            return False
        print(f"  backup ok: {result.stdout.strip() or '(no output)'}")
        return True
    except Exception as exc:
        print(f"  backup error: {exc}")
        return False


def _backup_size_sanity(db_path: Path) -> bool:
    """Mirrors migrate_answer_spec.py: confirm a recent (<24h) non-empty backup
    exists. Returns True (skip-with-warning friendly) on first runs."""
    backups_dir = Path("backups")
    if not backups_dir.exists():
        return True
    candidates = sorted(backups_dir.glob("*.db.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        return True
    latest = candidates[0]
    try:
        size = latest.stat().st_size
        mtime = latest.stat().st_mtime
    except OSError:
        return True
    if size == 0:
        print(f"  backup sanity: {latest.name} is empty. Use --force to override.")
        return False
    age_h = (time.time() - mtime) / 3600
    if age_h > 24:
        print(f"  backup sanity: {latest.name} is {age_h:.1f}h old (>24h). Use --force to override.")
        return False
    return True


def process_db(db_path: Path, dry_run: bool) -> tuple[int, int]:
    """Returns (rows_touched, total_ids_assigned)."""
    if not db_path.exists():
        print(f"  no SQLite DB at {db_path} — nothing to migrate")
        return (0, 0)

    print(f"  connecting to {db_path}")
    conn: sqlite3.Connection | None = None
    rows_touched = 0
    total_assigned = 0
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        try:
            # Include soft-deleted rows so a later restore doesn't resurrect
            # a row with id-less boss_questions.
            cur.execute("SELECT id, content_json FROM homeworks")
        except sqlite3.OperationalError:
            print("  homeworks table not found; skipping DB step")
            return (0, 0)
        rows = cur.fetchall()

        cur.execute("BEGIN")
        for row in rows:
            hw_id = row["id"]
            raw = row["content_json"]
            if not raw:
                continue
            try:
                content = json.loads(raw)
            except Exception as exc:
                print(f"    skip {hw_id}: invalid JSON ({exc})")
                continue
            n = migrate_boss_questions(content)
            if n:
                rows_touched += 1
                total_assigned += n
                if dry_run:
                    print(f"    [DRY] would update {hw_id} (+{n} ids)")
                else:
                    new_raw = json.dumps(content, ensure_ascii=False)
                    cur.execute(
                        "UPDATE homeworks SET content_json = ? WHERE id = ?",
                        (new_raw, hw_id),
                    )
                    print(f"    updated {hw_id} (+{n} ids)")

        if dry_run:
            cur.execute("ROLLBACK")
        else:
            cur.execute("COMMIT")
    finally:
        if conn is not None:
            conn.close()
    return (rows_touched, total_assigned)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Backfill boss_question ids (bq_{i}) on existing rows.",
    )
    parser.add_argument(
        "--db-path",
        default=os.getenv("NETS_DB_PATH", "nets.db"),
        help="SQLite DB path (default: $NETS_DB_PATH or ./nets.db).",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Print actions without writing fixtures or DB rows.")
    parser.add_argument("--backup-first", action="store_true",
                        help="Run scripts/backup_db.sh before any UPDATE.")
    parser.add_argument("--force", action="store_true",
                        help="Skip the backup-size sanity check.")
    parser.add_argument("--skip-fixtures", action="store_true",
                        help="Skip JSON fixture migration (DB only).")
    parser.add_argument("--skip-db", action="store_true",
                        help="Skip SQLite DB migration (fixtures only).")
    args = parser.parse_args(argv)

    db_path = Path(args.db_path)

    if not args.skip_fixtures:
        print("Processing fixtures...")
        files, ids = process_fixtures(args.dry_run)
        print(f"  fixtures: {files} file(s) touched, {ids} id(s) assigned")

    if not args.skip_db:
        print("Processing database...")
        if not args.dry_run and args.backup_first:
            if not _backup_db(db_path):
                print("Aborting: backup failed.")
                return 1
            if not args.force and not _backup_size_sanity(db_path):
                print("Aborting: backup sanity failed (use --force to override).")
                return 1
        rows, ids = process_db(db_path, args.dry_run)
        print(f"  database: {rows} row(s) touched, {ids} id(s) assigned")

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
