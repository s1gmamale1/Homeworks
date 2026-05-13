"""
Repair UTF-8 mojibake in homework content_json (and version snapshots).

Why this script exists:
    HW-20260507-001 was discovered on 2026-05-13 with Greek + math characters
    corrupted into double-encoded mojibake — e.g., `δ` stored as
    `Ã\x8eÂ´`, `±` as `Ã\x82Â±`, `−` as `Ã¢Ë\x86â\x80\x99`. The corruption
    is at-rest in the DB, not a render-time bug. Symptoms in the runtime:
    ugly broken glyphs in adaptive-quiz options and boss authored stems.

What this script does:
    1. Walks `homeworks.content_json` and `homework_versions.content_json`.
    2. Detects mojibake by scanning for byte-sequence markers known to be
       double-encoded UTF-8 (e.g., `Ã\x82`, `Ã\x8e`, `Ã¢Ë`).
    3. Runs `ftfy.fix_text()` on every string value in the JSON tree.
    4. By default prints a before/after diff (DRY-RUN mode). Pass `--apply`
       to write the fixed JSON back. Optional `--backup-first` runs
       scripts/backup_db.sh before touching rows.

Usage:
    python scripts/repair_mojibake.py [--db-path nets.db] [--apply] [--backup-first] [--hw-id HW-XXX]

Safety:
  --apply         Required to actually write changes. Default is dry-run.
  --backup-first  Run scripts/backup_db.sh before any UPDATE.
  --hw-id         Restrict repair to a single homework id.
  Runs inside a single SQLite transaction; partial failure rolls back.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any


# Byte-sequence markers strongly indicative of UTF-8-as-Latin1/CP1252
# double-encoding. If any of these appears verbatim in a JSON string, ftfy
# will almost certainly fix it. False positives are essentially nil — these
# sequences don't occur in legitimate Uzbek/Russian/English text.
MOJIBAKE_MARKERS = [
    "Ã",   # Ã[NBSP]  → typically prefixes ±, ·, ², etc.
    "Ã",   # ÃŽ       → typically prefixes δ (Greek letter)
    "Ã¢Ë",  # â‹    → math symbol prefix
    "Ã¢â",  # ââ€  → math symbol prefix
    "ÃÂ",  # ÃÂ    → fallback double-encoding marker
]


def has_mojibake(s: str) -> bool:
    return any(m in s for m in MOJIBAKE_MARKERS)


def fix_tree(node: Any, _changed: list[bool]) -> Any:
    """Recursively walk a JSON tree and ftfy.fix_text every string value.

    Sets _changed[0] = True if ANY string in the tree changed. Returns the
    repaired tree (new container; original is untouched).
    """
    import ftfy

    if isinstance(node, dict):
        return {k: fix_tree(v, _changed) for k, v in node.items()}
    if isinstance(node, list):
        return [fix_tree(item, _changed) for item in node]
    if isinstance(node, str):
        if not has_mojibake(node):
            return node
        fixed = ftfy.fix_text(node)
        if fixed != node:
            _changed[0] = True
        return fixed
    return node


def repair_row(content_json_str: str) -> tuple[bool, str, list[tuple[str, str]]]:
    """Returns (changed, new_json_str, diffs) where diffs is a list of
    (before, after) pairs for the strings that changed — for dry-run output.
    """
    tree = json.loads(content_json_str)
    changed_flag = [False]
    diffs: list[tuple[str, str]] = []

    def collect_diffs(orig: Any, new: Any) -> None:
        if isinstance(orig, dict) and isinstance(new, dict):
            for k in orig:
                collect_diffs(orig.get(k), new.get(k))
        elif isinstance(orig, list) and isinstance(new, list):
            for a, b in zip(orig, new):
                collect_diffs(a, b)
        elif isinstance(orig, str) and isinstance(new, str) and orig != new:
            diffs.append((orig, new))

    new_tree = fix_tree(tree, changed_flag)
    if changed_flag[0]:
        collect_diffs(tree, new_tree)
        new_json = json.dumps(new_tree, ensure_ascii=False)
        return True, new_json, diffs
    return False, content_json_str, []


def main() -> int:
    # Windows consoles default to cp1252; ftfy outputs U+2212, U+2248, etc.
    # which can't be printed without forcing UTF-8 stdout.
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", default="nets.db")
    parser.add_argument("--apply", action="store_true",
                        help="Write changes (default: dry-run).")
    parser.add_argument("--backup-first", action="store_true",
                        help="Run scripts/backup_db.sh before writes.")
    parser.add_argument("--hw-id", default=None,
                        help="Restrict to one homework id.")
    args = parser.parse_args()

    db_path = Path(args.db_path).resolve()
    if not db_path.exists():
        print(f"ERROR: DB not found: {db_path}", file=sys.stderr)
        return 2

    if args.apply and args.backup_first:
        backup = Path(__file__).parent / "backup_db.sh"
        print(f"Running backup: {backup}")
        result = subprocess.run(["bash", str(backup)], capture_output=True, text=True)
        if result.returncode != 0:
            print("Backup failed:", result.stderr, file=sys.stderr)
            return 3
        print("Backup OK")

    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row

    total_rows_scanned = 0
    total_rows_changed = 0
    total_strings_fixed = 0

    try:
        con.execute("BEGIN")

        # --- homeworks table ---
        if args.hw_id:
            rows = con.execute(
                "SELECT id, content_json FROM homeworks WHERE id = ?",
                (args.hw_id,),
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT id, content_json FROM homeworks WHERE content_json IS NOT NULL"
            ).fetchall()

        for r in rows:
            total_rows_scanned += 1
            if not r["content_json"]:
                continue
            changed, new_json, diffs = repair_row(r["content_json"])
            if not changed:
                continue
            total_rows_changed += 1
            total_strings_fixed += len(diffs)
            print(f"\n[homeworks] {r['id']} — {len(diffs)} strings to repair")
            for before, after in diffs[:5]:
                print(f"  - {before[:80]!r}")
                print(f"  + {after[:80]!r}")
            if len(diffs) > 5:
                print(f"  ... and {len(diffs) - 5} more")
            if args.apply:
                con.execute(
                    "UPDATE homeworks SET content_json = ? WHERE id = ?",
                    (new_json, r["id"]),
                )

        # --- homework_versions table ---
        if args.hw_id:
            vrows = con.execute(
                "SELECT id, homework_id, saved_at, content_json FROM homework_versions "
                "WHERE homework_id = ?",
                (args.hw_id,),
            ).fetchall()
        else:
            vrows = con.execute(
                "SELECT id, homework_id, saved_at, content_json FROM homework_versions "
                "WHERE content_json IS NOT NULL"
            ).fetchall()

        for r in vrows:
            total_rows_scanned += 1
            if not r["content_json"]:
                continue
            changed, new_json, diffs = repair_row(r["content_json"])
            if not changed:
                continue
            total_rows_changed += 1
            total_strings_fixed += len(diffs)
            print(f"\n[homework_versions] {r['homework_id']} saved={r['saved_at']} — {len(diffs)} strings to repair")
            for before, after in diffs[:3]:
                print(f"  - {before[:80]!r}")
                print(f"  + {after[:80]!r}")
            if args.apply:
                con.execute(
                    "UPDATE homework_versions SET content_json = ? WHERE id = ?",
                    (new_json, r["id"]),
                )

        if args.apply:
            con.execute("COMMIT")
            print(f"\nAPPLIED. Scanned={total_rows_scanned}, "
                  f"rows_changed={total_rows_changed}, strings_fixed={total_strings_fixed}")
        else:
            con.execute("ROLLBACK")
            print(f"\nDRY-RUN. Scanned={total_rows_scanned}, "
                  f"rows_would_change={total_rows_changed}, strings_would_fix={total_strings_fixed}")
            print("Re-run with --apply to commit changes.")
    finally:
        con.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
