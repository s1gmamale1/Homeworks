"""
Slim bloated math / geometry homework records by replacing huge inline
bitmap data URIs with lightweight SVG placeholders.

This is a one-off data repair for local demo homework rows whose
`content_json` grew to multi-megabyte size because image blocks stored
full base64 PNG payloads inline.
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server.config import DB_PATH


TARGET_SUBJECTS = {"math-algebra", "geometriya-g7-11"}
BITMAP_PREFIXES = ("data:image/png;base64,", "data:image/jpeg;base64,", "data:image/jpg;base64,")
MAX_LABEL = 52


@dataclass
class RepairStats:
    rows_seen: int = 0
    rows_changed: int = 0
    src_replaced: int = 0
    html_replaced: int = 0
    metadata_fixed: int = 0


def _truncate(text: str, limit: int = MAX_LABEL) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return "Diagram"
    return text[: limit - 3].rstrip() + "..." if len(text) > limit else text


def _subject_display(subject: str) -> str:
    return {
        "math-algebra": "Algebra",
        "geometriya-g7-11": "Geometriya",
    }.get(subject, subject)


def _svg_data_uri(subject: str, label: str) -> str:
    accent = "#0066CC" if subject == "math-algebra" else "#0F8A6C"
    title = _truncate(label)
    subtitle = "Homework diagram"
    svg = f"""
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="720" viewBox="0 0 1200 720">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#F8FBFF"/>
      <stop offset="100%" stop-color="#EAF4FF"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="720" rx="44" fill="url(#bg)"/>
  <rect x="48" y="48" width="1104" height="624" rx="36" fill="#FFFFFF" stroke="{accent}" stroke-width="6"/>
  <circle cx="154" cy="150" r="34" fill="{accent}" opacity="0.12"/>
  <circle cx="1046" cy="570" r="48" fill="{accent}" opacity="0.08"/>
  <path d="M156 546 L360 294 L566 546 Z" fill="none" stroke="{accent}" stroke-width="12" stroke-linecap="round" stroke-linejoin="round" opacity="0.75"/>
  <path d="M710 248 H1006" stroke="{accent}" stroke-width="12" stroke-linecap="round" opacity="0.72"/>
  <path d="M710 338 H948" stroke="{accent}" stroke-width="12" stroke-linecap="round" opacity="0.56"/>
  <path d="M710 428 H880" stroke="{accent}" stroke-width="12" stroke-linecap="round" opacity="0.4"/>
  <text x="96" y="128" font-family="Segoe UI, Arial, sans-serif" font-size="28" font-weight="700" fill="{accent}">{subtitle}</text>
  <text x="96" y="612" font-family="Segoe UI, Arial, sans-serif" font-size="54" font-weight="700" fill="#17324D">{title}</text>
</svg>
""".strip()
    return "data:image/svg+xml;utf8," + urllib.parse.quote(svg, safe="")


def _guess_label(node: Any, breadcrumbs: list[str], fallback_subject: str) -> str:
    if isinstance(node, dict):
        for key in ("title", "term", "label", "caption", "prompt", "question", "name", "text", "front", "back"):
            value = node.get(key)
            if isinstance(value, str) and value.strip():
                return _truncate(re.sub(r"<[^>]+>", " ", value))
    for crumb in reversed(breadcrumbs):
        clean = re.sub(r"<[^>]+>", " ", crumb)
        clean = re.sub(r"\s+", " ", clean).strip()
        if clean:
            return _truncate(clean)
    return _subject_display(fallback_subject)


def _replace_img_srcs_in_html(html: str, subject: str, label: str) -> tuple[str, int]:
    replacements = 0
    replacement_src = _svg_data_uri(subject, label)

    def repl(match: re.Match[str]) -> str:
        nonlocal replacements
        replacements += 1
        prefix = match.group(1)
        quote = match.group(2)
        return f"{prefix}{quote}{replacement_src}{quote}"

    updated = re.sub(
        r'(<img\b[^>]*\bsrc=)(["\'])(data:image/(?:png|jpeg|jpg);base64,[^"\']+)\2',
        repl,
        html,
        flags=re.IGNORECASE,
    )
    return updated, replacements


def _repair_node(node: Any, subject: str, breadcrumbs: list[str], stats: RepairStats) -> Any:
    if isinstance(node, dict):
        local_label = _guess_label(node, breadcrumbs, subject)
        repaired: dict[str, Any] = {}
        for key, value in node.items():
            next_breadcrumbs = breadcrumbs
            if key in {"title", "term", "label", "caption", "prompt", "question", "name"} and isinstance(value, str):
                next_breadcrumbs = breadcrumbs + [value]
            if key == "src" and isinstance(value, str) and value.startswith(BITMAP_PREFIXES):
                repaired[key] = _svg_data_uri(subject, local_label)
                stats.src_replaced += 1
                continue
            if key == "html" and isinstance(value, str) and "data:image/" in value:
                repaired_html, replaced = _replace_img_srcs_in_html(value, subject, local_label)
                repaired[key] = repaired_html
                stats.html_replaced += replaced
                continue
            repaired[key] = _repair_node(value, subject, next_breadcrumbs, stats)
        return repaired

    if isinstance(node, list):
        return [_repair_node(item, subject, breadcrumbs, stats) for item in node]

    if isinstance(node, str) and "data:image/" in node and "<img" in node:
        label = _guess_label(None, breadcrumbs, subject)
        repaired_html, replaced = _replace_img_srcs_in_html(node, subject, label)
        stats.html_replaced += replaced
        return repaired_html

    return node


def _repair_homework(content_json: str, subject: str) -> tuple[str, bool, RepairStats]:
    stats = RepairStats(rows_seen=1)
    data = json.loads(content_json)
    before = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    repaired = _repair_node(data, subject, [], stats)
    meta = repaired.setdefault("meta", {})
    expected_display = _subject_display(subject)
    if meta.get("subject_display") != expected_display:
        meta["subject_display"] = expected_display
        stats.metadata_fixed += 1

    after = json.dumps(repaired, ensure_ascii=False, separators=(",", ":"))
    changed = before != after
    if changed:
        stats.rows_changed = 1
    return after, changed, stats


def main() -> int:
    db_path = Path(DB_PATH)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        """
        select id, subject, title, content_json
        from homeworks
        where subject in (?, ?)
        order by id
        """,
        tuple(TARGET_SUBJECTS),
    ).fetchall()

    total = RepairStats()
    print(f"DB: {db_path}")
    print(f"Scanning {len(rows)} math / geometry homeworks")

    for row in rows:
        total.rows_seen += 1
        hw_id = row["id"]
        subject = row["subject"]
        title = row["title"]
        content_json = row["content_json"] or ""
        if not content_json:
            print(f"{hw_id}: skipped empty content_json")
            continue

        repaired_json, changed, stats = _repair_homework(content_json, subject)
        total.src_replaced += stats.src_replaced
        total.html_replaced += stats.html_replaced
        total.metadata_fixed += stats.metadata_fixed
        if not changed:
            print(f"{hw_id}: no changes | {title}")
            continue

        con.execute("update homeworks set content_json = ? where id = ?", (repaired_json, hw_id))
        total.rows_changed += 1
        print(
            f"{hw_id}: repaired | src={stats.src_replaced} html={stats.html_replaced} "
            f"meta={stats.metadata_fixed} | {title}"
        )

    con.commit()
    print(
        f"Done. changed={total.rows_changed} src_replaced={total.src_replaced} "
        f"html_replaced={total.html_replaced} metadata_fixed={total.metadata_fixed}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
