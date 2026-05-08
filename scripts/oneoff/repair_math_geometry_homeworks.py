"""
Slim bloated math / geometry homework records by replacing huge inline
bitmap data URIs with lightweight SVG placeholders.

This is a one-off data repair for local demo homework rows whose
`content_json` grew to multi-megabyte size because image blocks stored
full base64 PNG payloads inline.
"""

from __future__ import annotations

import argparse
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
SVG_DATA_URI_PREFIX = "data:image/svg+xml;utf8,"
MAX_LABEL = 52
HOMEWORK_BLOAT_THRESHOLD = 200_000
INLINE_IMAGE_BLOAT_THRESHOLD = 20_000
GENERATED_IMAGE_PATTERN = re.compile(
    r'(?:(?:https?:)?//[^"\']+)?/generated/[^"\']+\.(?:png|jpe?g|webp|gif|svg)',
    re.IGNORECASE,
)


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


def _needs_subject_display_fix(subject: str, subject_display: Any) -> bool:
    if not isinstance(subject_display, str):
        return not subject_display
    normalized = subject_display.strip().lower()
    return normalized in {"", subject.lower(), "math-algebra", "geometriya-g7-11"}


def _svg_markup(subject: str, label: str) -> str:
    accent = "#0066CC" if subject == "math-algebra" else "#0F8A6C"
    title = _truncate(label)
    subtitle = "Homework diagram"
    return f"""
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


def _svg_data_uri(subject: str, label: str) -> str:
    svg = _svg_markup(subject, label)
    return SVG_DATA_URI_PREFIX + urllib.parse.quote(svg, safe="")


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


def _is_bloated_data_uri(value: str) -> bool:
    return isinstance(value, str) and value.startswith(BITMAP_PREFIXES) and len(value) >= INLINE_IMAGE_BLOAT_THRESHOLD


def _is_svg_data_uri_ref(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(SVG_DATA_URI_PREFIX)


def _is_stale_generated_image_ref(value: Any) -> bool:
    return isinstance(value, str) and bool(GENERATED_IMAGE_PATTERN.search(value))


def _has_repairable_img_html(value: Any) -> bool:
    if not isinstance(value, str) or "<img" not in value:
        return False
    return (
        "data:image/" in value
        or "/generated/" in value
        or "generated/" in value
    )


def _extract_first_img_src(html: str) -> str | None:
    match = re.search(r'<img\b[^>]*\bsrc=["\']([^"\']+)["\'][^>]*>', html or "", flags=re.IGNORECASE)
    return match.group(1) if match else None


def _decode_svg_data_uri(value: str) -> str:
    return urllib.parse.unquote(value[len(SVG_DATA_URI_PREFIX):]) if _is_svg_data_uri_ref(value) else ""


def _media_block_from_src(src: str, subject: str, label: str) -> dict[str, str]:
    if _is_svg_data_uri_ref(src):
        html = _decode_svg_data_uri(src).strip() or _svg_markup(subject, label)
        return {"type": "svg", "html": html}
    return {"type": "image", "src": src, "alt": label}


def _replace_svg_data_uri_imgs_in_html(html: str) -> tuple[str, int]:
    replacements = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal replacements
        src = match.group(1)
        html = _decode_svg_data_uri(src).strip()
        if not html:
            return match.group(0)
        replacements += 1
        return html

    updated = re.sub(
        r'<img\b[^>]*\bsrc=["\'](data:image/svg\+xml;utf8,[^"\']+)["\'][^>]*>',
        repl,
        html,
        flags=re.IGNORECASE,
    )
    return updated, replacements


def _needs_media_repair(node: Any) -> bool:
    if isinstance(node, dict):
        return any(_needs_media_repair(v) for v in node.values())
    if isinstance(node, list):
        return any(_needs_media_repair(v) for v in node)
    if isinstance(node, str):
        return _is_stale_generated_image_ref(node) or _is_svg_data_uri_ref(node) or _has_repairable_img_html(node)
    return False


def _repair_node(node: Any, subject: str, breadcrumbs: list[str], stats: RepairStats) -> Any:
    if isinstance(node, dict):
        local_label = _guess_label(node, breadcrumbs, subject)
        if node.get("type") == "quote" and _has_repairable_img_html(node.get("text")):
            src = _extract_first_img_src(str(node.get("text") or ""))
            if src:
                stats.html_replaced += 1
                return _media_block_from_src(src, subject, local_label)
        if node.get("type") == "image" and _is_svg_data_uri_ref(node.get("src")):
            stats.src_replaced += 1
            return _media_block_from_src(str(node.get("src") or ""), subject, local_label)
        repaired: dict[str, Any] = {}
        for key, value in node.items():
            next_breadcrumbs = breadcrumbs
            if key in {"title", "term", "label", "caption", "prompt", "question", "name"} and isinstance(value, str):
                next_breadcrumbs = breadcrumbs + [value]
            if key == "html" and _has_repairable_img_html(value):
                repaired_html, replaced = _replace_svg_data_uri_imgs_in_html(value)
                repaired[key] = repaired_html
                stats.html_replaced += replaced
                continue
            repaired[key] = _repair_node(value, subject, next_breadcrumbs, stats)
        return repaired

    if isinstance(node, list):
        return [_repair_node(item, subject, breadcrumbs, stats) for item in node]

    if isinstance(node, str) and _has_repairable_img_html(node):
        repaired_html, replaced = _replace_svg_data_uri_imgs_in_html(node)
        stats.html_replaced += replaced
        return repaired_html

    return node


def _repair_homework(content_json: str, subject: str) -> tuple[str, bool, RepairStats]:
    stats = RepairStats(rows_seen=1)
    data = json.loads(content_json)
    before = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    repaired = data
    if len(content_json) >= HOMEWORK_BLOAT_THRESHOLD or _needs_media_repair(data):
        repaired = _repair_node(data, subject, [], stats)
    meta = repaired.setdefault("meta", {})
    expected_display = _subject_display(subject)
    if _needs_subject_display_fix(subject, meta.get("subject_display")):
        meta["subject_display"] = expected_display
        stats.metadata_fixed += 1

    after = json.dumps(repaired, ensure_ascii=False, separators=(",", ":"))
    changed = before != after
    if changed:
        stats.rows_changed = 1
    return after, changed, stats


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repair bloated math / geometry homework content_json rows.")
    parser.add_argument("--ids", nargs="*", default=None, help="Optional homework IDs to repair instead of all math/geometry rows.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    db_path = Path(DB_PATH)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    if args.ids:
        placeholders = ",".join("?" for _ in args.ids)
        rows = con.execute(
            f"""
            select id, subject, title, content_json
            from homeworks
            where id in ({placeholders})
            order by id
            """,
            tuple(args.ids),
        ).fetchall()
    else:
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
