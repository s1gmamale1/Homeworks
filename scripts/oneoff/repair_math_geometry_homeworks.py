"""
Slim bloated math / geometry homework records by replacing huge inline
bitmap data URIs with lightweight SVG placeholders.

This is a one-off data repair for local demo homework rows whose
`content_json` grew to multi-megabyte size because image blocks stored
full base64 PNG payloads inline.
"""

from __future__ import annotations

import argparse
import html
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
from server.services.content_media_migration import migrate_content_media


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
STATIC_IMAGE_REPLACEMENTS = {
    "HW-20260505-008__panels_1_pages_0_blocks_4_text__handdrawn.png": "/generated/HW-20260505-008_factorization_methods.svg",
}


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


def _clean_svg_label(label: str, subject: str) -> str:
    clean = _truncate(re.sub(r"<[^>]+>", " ", label or ""))
    if clean.lower() in {"", "diagram", "formula diagram", "homework diagram", "handdrawn diagram"}:
        return "Ko'phadlarni ajratish" if subject == "math-algebra" else "Geometriya diagrammasi"
    return clean


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
    is_math = subject == "math-algebra"
    accent = "#0066CC" if is_math else "#0F8A6C"
    title = html.escape(_clean_svg_label(label, subject), quote=False)
    eyebrow = "ALGEBRA" if is_math else "GEOMETRIYA"
    left_title = "Umumiy omil" if is_math else "Burchak"
    left_formula = "ax + ay" if is_math else "∠A + ∠B"
    left_sub = "= a(x + y)" if is_math else "= 180°"
    right_title = "Guruhlash" if is_math else "Uchburchak"
    right_formula = "ax+ay+bx+by" if is_math else "a² + b² = c²"
    right_sub = "= (a+b)(x+y)" if is_math else "to'g'ri burchak"
    return f"""
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="760" viewBox="0 0 900 760">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#f7fbff"/>
      <stop offset="100%" stop-color="#eaf4ff"/>
    </linearGradient>
    <linearGradient id="core" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{accent}"/>
      <stop offset="100%" stop-color="#0F8A6C"/>
    </linearGradient>
    <filter id="softShadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="12" stdDeviation="14" flood-color="#17324D" flood-opacity="0.14"/>
    </filter>
  </defs>
  <rect width="900" height="760" rx="36" fill="url(#bg)"/>
  <rect x="32" y="32" width="836" height="696" rx="32" fill="#FFFFFF" opacity="0.58"/>
  <text x="70" y="88" font-family="Segoe UI, Arial, sans-serif" font-size="24" font-weight="800" fill="{accent}">{eyebrow}</text>
  <text x="70" y="142" font-family="Segoe UI, Arial, sans-serif" font-size="40" font-weight="850" fill="#17324D">{title}</text>
  <text x="70" y="186" font-family="Segoe UI, Arial, sans-serif" font-size="24" fill="#5D7188">Asosiy belgi va mos usulni tanlang.</text>
  <g filter="url(#softShadow)">
    <rect x="198" y="238" width="504" height="122" rx="28" fill="url(#core)"/>
    <text x="270" y="290" font-family="Segoe UI, Arial, sans-serif" font-size="25" font-weight="800" fill="#DFF3FF">BOSHLASH</text>
    <text x="270" y="334" font-family="Segoe UI, Arial, sans-serif" font-size="34" font-weight="850" fill="#FFFFFF">{title}</text>
  </g>
  <path d="M344 360 L252 430" fill="none" stroke="{accent}" stroke-width="6" stroke-linecap="round"/>
  <path d="M556 360 L648 430" fill="none" stroke="{accent}" stroke-width="6" stroke-linecap="round"/>
  <g filter="url(#softShadow)">
    <rect x="92" y="430" width="326" height="174" rx="24" fill="#FFFFFF" stroke="#D7E6F7" stroke-width="3"/>
    <circle cx="130" cy="476" r="15" fill="{accent}"/>
    <text x="164" y="486" font-family="Segoe UI, Arial, sans-serif" font-size="25" font-weight="820" fill="#17324D">{left_title}</text>
    <text x="130" y="544" font-family="Segoe UI, Arial, sans-serif" font-size="34" font-weight="850" fill="#17324D">{left_formula}</text>
    <text x="130" y="584" font-family="Segoe UI, Arial, sans-serif" font-size="24" fill="#5D7188">{left_sub}</text>
  </g>
  <g filter="url(#softShadow)">
    <rect x="482" y="430" width="326" height="174" rx="24" fill="#FFFFFF" stroke="#D7E6F7" stroke-width="3"/>
    <circle cx="520" cy="476" r="15" fill="#0F8A6C"/>
    <text x="554" y="486" font-family="Segoe UI, Arial, sans-serif" font-size="25" font-weight="820" fill="#17324D">{right_title}</text>
    <text x="520" y="544" font-family="Segoe UI, Arial, sans-serif" font-size="30" font-weight="850" fill="#17324D">{right_formula}</text>
    <text x="520" y="584" font-family="Segoe UI, Arial, sans-serif" font-size="24" fill="#5D7188">{right_sub}</text>
  </g>
  <g filter="url(#softShadow)">
    <rect x="118" y="640" width="664" height="54" rx="20" fill="#FFFFFF" stroke="#D7E6F7" stroke-width="3"/>
    <text x="156" y="675" font-family="Segoe UI, Arial, sans-serif" font-size="22" fill="#17324D">Tekshiruv: natijani ochib ko'ring va boshlang'ich ifoda bilan solishtiring.</text>
  </g>
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


def _static_replacement_for_src(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    for old_name, replacement in STATIC_IMAGE_REPLACEMENTS.items():
        if old_name in value:
            return replacement
    return None


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
    replacement = _static_replacement_for_src(src)
    if replacement:
        return {"type": "image", "src": replacement, "alt": label}
    if _is_svg_data_uri_ref(src):
        html = _decode_svg_data_uri(src).strip()
        return {"type": "svg", "html": html}
    return {"type": "image", "src": src, "alt": label}


def _replace_svg_data_uri_imgs_in_html(html_text: str, subject: str, label: str) -> tuple[str, int]:
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
        html_text,
        flags=re.IGNORECASE,
    )
    return updated, replacements


def _needs_media_repair(node: Any) -> bool:
    if isinstance(node, dict):
        return any(_needs_media_repair(v) for v in node.values())
    if isinstance(node, list):
        return any(_needs_media_repair(v) for v in node)
    if isinstance(node, str):
        return (
            _is_stale_generated_image_ref(node)
            or _is_svg_data_uri_ref(node)
            or _has_repairable_img_html(node)
        )
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
        if node.get("type") == "image" and _static_replacement_for_src(node.get("src")):
            stats.src_replaced += 1
            return _media_block_from_src(str(node.get("src") or ""), subject, local_label)
        repaired: dict[str, Any] = {}
        for key, value in node.items():
            next_breadcrumbs = breadcrumbs + [local_label] if local_label else breadcrumbs
            if key in {"title", "term", "label", "caption", "prompt", "question", "name"} and isinstance(value, str):
                next_breadcrumbs = breadcrumbs + [value]
            if key == "html" and _has_repairable_img_html(value):
                repaired_html, replaced = _replace_svg_data_uri_imgs_in_html(value, subject, local_label)
                repaired[key] = repaired_html
                stats.html_replaced += replaced
                continue
            repaired[key] = _repair_node(value, subject, next_breadcrumbs, stats)
        return repaired

    if isinstance(node, list):
        return [_repair_node(item, subject, breadcrumbs, stats) for item in node]

    if isinstance(node, str) and _has_repairable_img_html(node):
        label = _guess_label(None, breadcrumbs, subject)
        repaired_html, replaced = _replace_svg_data_uri_imgs_in_html(node, subject, label)
        stats.html_replaced += replaced
        return repaired_html

    return node


def _repair_homework(content_json: str, subject: str, hw_id: str | None = None) -> tuple[str, bool, RepairStats]:
    stats = RepairStats(rows_seen=1)
    data = json.loads(content_json)
    before = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    repaired = data
    if len(content_json) >= HOMEWORK_BLOAT_THRESHOLD or _needs_media_repair(data):
        repaired, _, media_stats = migrate_content_media(data, subject=subject, hw_id=hw_id, write_files=True)
        stats.src_replaced += (
            media_stats.generated_urls_normalized
            + media_stats.svg_data_uris_decoded
            + media_stats.bitmap_data_uris_extracted
        )
        stats.html_replaced += (
            media_stats.image_html_blocks_lifted
            + media_stats.generic_svgs_rewritten
        )
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

        repaired_json, changed, stats = _repair_homework(content_json, subject, hw_id=hw_id)
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
