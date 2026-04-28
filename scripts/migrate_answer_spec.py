"""
Migrate legacy `ans[]` / `accepted_answers[]` fields into structured `answer_spec`.

Idempotent. Touches both fixture JSON files and the SQLite homeworks table.

Usage:
    python scripts/migrate_answer_spec.py --db-path /path/to/nets.db [--dry-run] [--backup-first] [--force]

Safety rails:
  --db-path        Required for DB writes. Defaults to env NETS_DB_PATH or "nets.db".
  --dry-run        Print what would change without writing fixtures or rows.
  --backup-first   Run scripts/backup_db.sh before any UPDATE. Aborts if backup fails.
  --force          Skip the backup-size sanity check.

The migration runs inside a single SQLite transaction so partial failure leaves
the DB untouched. Empty / answer-less questions (e.g. memory_sprint items that
use `options[] + correct` indices) are skipped — only items with a non-empty
legacy answers field are upgraded.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Spec inference (pure, exposed for tests)
# ---------------------------------------------------------------------------


def _try_float(text: str) -> float | None:
    """Parse a stringified number, accepting comma decimals. Returns None on failure."""
    try:
        return float(str(text).strip().replace(",", "."))
    except (ValueError, TypeError):
        return None


def _all_numeric(values: list[str]) -> bool:
    return bool(values) and all(_try_float(v) is not None for v in values)


def guess_type(ans_list: list[str]) -> str:
    """Pick the most likely answer_spec type for a list of legacy strings."""
    if not ans_list:
        return "semantic"

    if _all_numeric(ans_list):
        # Multiple numeric roots → set_match (e.g. "2,3" for x²-5x+6=0).
        return "set_match" if len(ans_list) > 1 else "numeric"

    # Single answers containing ± / ; / multi-numeric "a, b" still indicate a set.
    for ans in ans_list:
        s = str(ans)
        if "±" in s or ";" in s:
            return "set_match"
        if "," in s:
            parts = [p.strip() for p in s.split(",") if p.strip()]
            if len(parts) > 1 and _all_numeric(parts):
                return "set_match"

    # Short tokens (≤2 chars) are likely option letters / single-word labels.
    if ans_list and len(str(ans_list[0])) <= 2:
        return "text_exact"

    return "text_fuzzy"


def _to_number(val: str) -> Any:
    """Cast a numeric string to int or float depending on integer-ness."""
    f = _try_float(val)
    if f is None:
        return val
    return int(f) if f.is_integer() else f


def infer_spec(old_answers: list[str]) -> dict:
    """Build an answer_spec dict from legacy answers. Pure / unit-testable."""
    ans_type = guess_type(old_answers)
    canonical = old_answers[0] if old_answers else ""

    if ans_type == "numeric":
        expected: Any = _to_number(canonical) if canonical else 0
        if isinstance(expected, str):
            ans_type = "text_fuzzy"
    elif ans_type == "set_match":
        # Build a numeric list. Honour both multi-element ans=["2","3"] and
        # single comma/semicolon-joined ans=["2, 3"].
        raw_parts: list[str] = []
        if len(old_answers) > 1:
            raw_parts = [str(a) for a in old_answers]
        elif old_answers:
            text = str(old_answers[0]).replace(";", ",").replace("±", "")
            raw_parts = [p.strip() for p in text.split(",") if p.strip()]

        nums: list[Any] = []
        for p in raw_parts:
            n = _to_number(p)
            if isinstance(n, (int, float)):
                nums.append(n)
        expected = nums if nums else raw_parts
    else:
        expected = canonical

    spec: dict = {
        "type": ans_type,
        "expected": expected,
        "canonical_display": canonical,
        "allow_ai_fallback": True,
    }

    if ans_type == "numeric":
        spec["tolerance"] = 0
        spec["allow_ai_fallback"] = False
    elif ans_type == "text_exact":
        spec["allow_ai_fallback"] = False

    return spec


# ---------------------------------------------------------------------------
# Mutation helpers
# ---------------------------------------------------------------------------


_QUESTION_BUCKETS = ("boss_questions", "gb_adaptive_quiz", "memory_sprint", "gb_why_chain")


# ---------------------------------------------------------------------------
# Wave E: option_index migration (memory_sprint, gb_why_chain, real_life)
# ---------------------------------------------------------------------------


def migrate_option_index(item: dict) -> bool:
    """Augment a single question item with an ``answer_spec`` of type
    ``option_index``.  The item must have ``correct`` (int, 0-based) and
    ``options`` (list).  Works for any bucket with this shape.

    Returns True if the item was mutated, False if it was already migrated or
    is missing the required fields (idempotent).
    """
    if not isinstance(item, dict):
        return False

    # Idempotent: skip if already has a valid answer_spec
    if "answer_spec" in item and isinstance(item["answer_spec"], dict):
        return False

    correct = item.get("correct")
    options = item.get("options")

    if not isinstance(correct, int) or not isinstance(options, list) or not options:
        # Not a tap-quiz item — nothing to infer.
        return False

    option_count = len(options)
    # Guard against an out-of-range correct index in malformed fixtures.
    if correct < 0 or correct >= option_count:
        return False

    canonical = options[correct] if options else None

    spec: dict[str, Any] = {
        "type": "option_index",
        "expected": correct,
        "option_count": option_count,
        "allow_ai_fallback": False,
    }
    if canonical is not None:
        spec["canonical_display"] = str(canonical)

    item["answer_spec"] = spec
    return True


# Backward-compat alias — existing tests and callers may reference this name.
migrate_memory_sprint = migrate_option_index


def migrate_real_life(item: dict) -> bool:
    """Augment a single real_life q-item with an ``answer_spec`` of type
    ``option_index`` when it has ``options[]`` + ``correct: int``.
    Open-ended items (no ``options``) are left untouched.

    Returns True if the item was mutated, False otherwise (idempotent).
    """
    return migrate_option_index(item)


def _legacy_answers(question: dict) -> list[str]:
    raw = question.get("accepted_answers")
    if raw is None:
        raw = question.get("ans")
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw if str(x).strip() != ""]
    if isinstance(raw, str) and raw.strip():
        return [raw]
    return []


def migrate_question(question: dict) -> bool:
    """Add answer_spec to a question dict in-place. Returns True if mutated."""
    if not isinstance(question, dict):
        return False
    if "answer_spec" in question and isinstance(question["answer_spec"], dict):
        return False

    legacy = _legacy_answers(question)
    if not legacy:
        # Memory-sprint items use options[] + correct (index) — nothing to migrate.
        return False

    question["answer_spec"] = infer_spec(legacy)
    # Preserve / standardize the legacy field for one release cycle of dual support.
    if "accepted_answers" not in question:
        question["accepted_answers"] = legacy
    return True


def migrate_content(content: dict) -> bool:
    """Migrate every question shape inside a content_json dict."""
    if not isinstance(content, dict):
        return False
    mutated = False

    # List-style buckets (boss_questions, gb_adaptive_quiz, memory_sprint, gb_why_chain).
    for key in _QUESTION_BUCKETS:
        bucket = content.get(key)
        if not isinstance(bucket, list):
            continue
        for q in bucket:
            if key in ("memory_sprint", "gb_why_chain"):
                # Wave E: these items use options[]+correct index, not ans[].
                # Try the option_index migration first; fall through to legacy-ans
                # migration for the rare items that have both.
                if migrate_option_index(q):
                    mutated = True
                    continue
            if migrate_question(q):
                mutated = True

    # real_life is a dict of sub-keys (badge, story, q1..q6, endTitle, endSub, …).
    # Only q-prefixed keys (q1, q2, …) can be question items; skip structural keys
    # like badge/story/endTitle/endSub even if they happen to look like dicts.
    real_life = content.get("real_life")
    if isinstance(real_life, dict):
        for key, q_item in real_life.items():
            if not str(key).startswith("q"):
                continue
            if isinstance(q_item, dict):
                if migrate_real_life(q_item):
                    mutated = True

    return mutated


# ---------------------------------------------------------------------------
# Fixture / DB drivers
# ---------------------------------------------------------------------------


def process_fixtures(dry_run: bool) -> int:
    fixtures_dir = Path("fixtures")
    if not fixtures_dir.exists():
        return 0

    touched = 0
    for p in sorted(fixtures_dir.glob("*.json")):
        try:
            content = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"  skip {p.name}: {exc}")
            continue
        if migrate_content(content):
            touched += 1
            if dry_run:
                print(f"  [DRY] would update fixture {p.name}")
            else:
                p.write_text(
                    json.dumps(content, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                print(f"  updated fixture {p.name}")
    return touched


def _backup_db(db_path: Path) -> bool:
    """Run scripts/backup_db.sh against db_path. Returns True on success."""
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
    """Sanity check that a recent backup exists. First-run safe.

    For .gz files, we skip byte-comparison entirely since gzip compresses 3-10x.
    We only verify the backup is non-empty and less than 24 hours old.
    This achieves the actual goal (sanity check that a recent backup exists)
    without false positives from compression ratios.
    """
    backups_dir = Path("backups")
    if not backups_dir.exists():
        # First-run case: no backup directory yet, so skip the check.
        return True
    candidates = sorted(backups_dir.glob("*.db.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        # No backup files found; skip the check.
        return True
    latest = candidates[0]
    try:
        backup_size = latest.stat().st_size
        backup_mtime = latest.stat().st_mtime
    except OSError:
        return True

    # Check if backup is empty.
    if backup_size == 0:
        print(
            f"  backup sanity check: backup file {latest.name} is empty (0 bytes). "
            f"Use --force to override."
        )
        return False

    # Check if backup is older than 24 hours.
    now = time.time()
    age_seconds = now - backup_mtime
    age_hours = age_seconds / 3600
    if age_hours > 24:
        print(
            f"  backup sanity check: backup file {latest.name} is {age_hours:.1f} hours old "
            f"(>24h). Use --force to override."
        )
        return False

    return True


def process_db(db_path: Path, dry_run: bool) -> int:
    if not db_path.exists():
        print(f"  no SQLite DB at {db_path} — nothing to migrate")
        return 0

    print(f"  connecting to {db_path}")
    conn: sqlite3.Connection | None = None
    touched = 0
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        try:
            cur.execute("SELECT id, content_json FROM homeworks")
        except sqlite3.OperationalError:
            print("  homeworks table not found; skipping DB step")
            return 0
        rows = cur.fetchall()

        # Single transaction so a failure mid-loop leaves the DB pristine.
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

            if migrate_content(content):
                touched += 1
                if dry_run:
                    print(f"    [DRY] would update homework {hw_id}")
                else:
                    new_raw = json.dumps(content, ensure_ascii=False)
                    cur.execute(
                        "UPDATE homeworks SET content_json = ? WHERE id = ?",
                        (new_raw, hw_id),
                    )
                    print(f"    updated homework {hw_id}")

        if dry_run:
            cur.execute("ROLLBACK")
        else:
            cur.execute("COMMIT")
    finally:
        if conn is not None:
            conn.close()
    return touched


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Migrate answer_spec into content_json for hybrid grading."
    )
    parser.add_argument(
        "--db-path",
        default=os.getenv("NETS_DB_PATH", "nets.db"),
        help="SQLite DB path (default: $NETS_DB_PATH or ./nets.db).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without writing fixtures or DB rows.",
    )
    parser.add_argument(
        "--backup-first",
        action="store_true",
        help="Run scripts/backup_db.sh before any UPDATE.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip the backup-size sanity check.",
    )
    parser.add_argument(
        "--skip-fixtures",
        action="store_true",
        help="Skip JSON fixture migration (DB only).",
    )
    parser.add_argument(
        "--skip-db",
        action="store_true",
        help="Skip SQLite DB migration (fixtures only).",
    )
    args = parser.parse_args(argv)

    db_path = Path(args.db_path)

    if not args.skip_fixtures:
        print("Processing fixtures...")
        n = process_fixtures(args.dry_run)
        print(f"  fixtures touched: {n}")

    if not args.skip_db:
        print("Processing database...")
        if not args.dry_run and not args.force and db_path.exists():
            if not _backup_size_sanity(db_path):
                print("Aborted: pass --force to override.")
                return 2
        if args.backup_first and not args.dry_run and db_path.exists():
            if not _backup_db(db_path):
                print("Aborted: backup failed and --backup-first was requested.")
                return 3
        n = process_db(db_path, args.dry_run)
        print(f"  homeworks touched: {n}")

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
