from __future__ import annotations

import argparse
import asyncio
import copy
import difflib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server.db import get_homework, list_homeworks, update_homework  # noqa: E402
from server.schemas.content import ContentJSON  # noqa: E402

Transform = Callable[[dict, dict], dict | None]
TRANSFORMS: dict[str, Transform] = {}


def register_transform(name: str):
    def decorator(fn: Transform) -> Transform:
        TRANSFORMS[name] = fn
        return fn

    return decorator


@register_transform("noop")
def transform_noop(content_json: dict, row: dict) -> dict | None:
    return content_json


@register_transform("add_default_dmg_to_boss")
def transform_add_default_dmg_to_boss(content_json: dict, row: dict) -> dict | None:
    boss_questions = content_json.get("boss_questions")
    if not isinstance(boss_questions, list):
        return None

    changed = False
    new_content = copy.deepcopy(content_json)
    for item in new_content.get("boss_questions", []):
        if isinstance(item, dict) and "dmg" not in item:
            item["dmg"] = 10
            changed = True
    return new_content if changed else None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_bytes(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False)


def _diff_keys(before: dict, after: dict) -> list[str]:
    keys = set(before) | set(after)
    return sorted(k for k in keys if before.get(k) != after.get(k))


def _validation_errors(exc: Exception) -> list[dict[str, Any]]:
    errors = getattr(exc, "errors", None)
    return errors() if callable(errors) else [{"msg": str(exc)}]


def _print_diff(hw_id: str, before: dict, after: dict) -> None:
    old = json.dumps(before, indent=2, ensure_ascii=False, sort_keys=True).splitlines()
    new = json.dumps(after, indent=2, ensure_ascii=False, sort_keys=True).splitlines()
    print(f"\n--- diff for {hw_id} ---")
    print(
        "\n".join(
            difflib.unified_diff(
                old,
                new,
                fromfile=f"{hw_id}:before",
                tofile=f"{hw_id}:after",
                lineterm="",
            )
        )
    )


def _default_report_path(transform: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path("audit-output") / f"migration_{transform}_{stamp}.json"


def _row_ids_arg(raw: str | None) -> set[str] | None:
    return {part.strip() for part in raw.split(",") if part.strip()} if raw else None


async def _selected_rows(ids: set[str] | None, limit: int | None) -> list[dict]:
    if ids is None:
        rows = await list_homeworks(include_deleted=False)
    else:
        rows = []
        for hw_id in ids:
            row = await get_homework(hw_id)
            if row and not row.get("deleted_at"):
                rows.append(row)
    if limit is not None:
        rows = rows[:limit]
    return rows


async def run_migration(args: argparse.Namespace) -> dict:
    transform = TRANSFORMS[args.transform]
    started_at = _utc_now()
    summary = {
        "total": 0,
        "transformed": 0,
        "skipped_unchanged": 0,
        "skipped_validation_failure": 0,
        "skipped_transform_error": 0,
    }
    report_rows: list[dict[str, Any]] = []
    diff_count = 0

    rows = await _selected_rows(_row_ids_arg(args.ids), args.limit)
    for row in rows:
        summary["total"] += 1
        hw_id = row["id"]
        full_row = await get_homework(hw_id)
        content = (full_row or {}).get("content_json") or {}
        if not isinstance(content, dict):
            status = "skipped_validation_failure"
            summary[status] += 1
            report_rows.append({"hw_id": hw_id, "status": status, "errors": [{"msg": "content_json is not an object"}]})
            continue

        try:
            new_content = transform(copy.deepcopy(content), dict(full_row or row))
        except Exception as exc:
            status = "skipped_transform_error"
            summary[status] += 1
            report_rows.append({"hw_id": hw_id, "status": status, "exception": repr(exc)})
            if args.verbose:
                print(f"{hw_id}: {status}: {exc}")
            continue

        if new_content is None or _json_bytes(new_content) == _json_bytes(content):
            status = "skipped_unchanged"
            summary[status] += 1
            report_rows.append({"hw_id": hw_id, "status": status})
            if args.verbose:
                print(f"{hw_id}: {status}")
            continue

        try:
            ContentJSON.model_validate(new_content)
        except Exception as exc:
            status = "skipped_validation_failure"
            summary[status] += 1
            report_rows.append({"hw_id": hw_id, "status": status, "errors": _validation_errors(exc)})
            if args.verbose:
                print(f"{hw_id}: {status}: {exc}")
            continue

        if diff_count < 3:
            _print_diff(hw_id, content, new_content)
            diff_count += 1
        if args.apply:
            await update_homework(hw_id, {"content_json": new_content})

        status = "transformed"
        summary[status] += 1
        report_rows.append({"hw_id": hw_id, "status": status, "diff_keys": _diff_keys(content, new_content)})
        if args.verbose:
            verb = "updated" if args.apply else "would update"
            print(f"{hw_id}: {verb} ({', '.join(_diff_keys(content, new_content))})")

    return {
        "transform": args.transform,
        "started_at": started_at,
        "ended_at": _utc_now(),
        "applied": bool(args.apply),
        "summary": summary,
        "rows": report_rows,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Safely migrate stored homework content_json blobs.")
    parser.add_argument("--transform", required=True, choices=sorted(TRANSFORMS), help="Registered transform to run.")
    parser.add_argument("--apply", action="store_true", help="Write validated changes to the DB. Default is dry-run.")
    parser.add_argument("--limit", type=int, default=None, help="Process only the first N matching rows.")
    parser.add_argument("--ids", default=None, help="Comma-separated homework IDs to process.")
    parser.add_argument("--report", default=None, help="JSON report path.")
    parser.add_argument("--db", default=None, help="Override DB path. Default comes from server.config.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print per-row status.")
    return parser


def _print_summary(summary: dict[str, int]) -> None:
    print("\nsummary")
    print("status                         count")
    print("-----------------------------  -----")
    for key, value in summary.items():
        print(f"{key:<29}  {value:>5}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.db:
        os.environ["NETS_DB_PATH"] = str(Path(args.db))
    report = asyncio.run(run_migration(args))
    report_path = Path(args.report) if args.report else _default_report_path(args.transform)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _print_summary(report["summary"])
    print(f"\nreport: {report_path}")
    print("mode: apply" if args.apply else "mode: dry-run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
