"""Media-preserving content_json migration helpers.

Older rows can contain media in a few inconvenient shapes:
- absolute LAN URLs such as ``http://192.168.1.87:8000/generated/foo.png``
- SVG data URIs embedded as image blocks
- bitmap data URIs embedded in structured image blocks
- image-only ``<img ...>`` HTML stuffed into text/quote blocks

The migration must preserve authored visuals. It should never replace a
working generated image with a generic placeholder just because the server
changed.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import html
import re
import urllib.parse
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from server.config import BASE_DIR


GENERATED_IMAGE_PATTERN = re.compile(
    r'(?:(?:https?:)?//[^"\']+)?(?P<path>/generated/[^"\']+\.(?:png|jpe?g|webp|gif|svg))',
    re.IGNORECASE,
)
SVG_DATA_URI_PREFIX = "data:image/svg+xml;utf8,"
BITMAP_DATA_URI_RE = re.compile(
    r"^data:image/(?P<kind>png|jpe?g|webp|gif);base64,(?P<data>[A-Za-z0-9+/=\s]+)$",
    re.IGNORECASE,
)
IMG_TAG_RE = re.compile(r'<img\b[^>]*\bsrc=["\'](?P<src>[^"\']+)["\'][^>]*>', re.IGNORECASE)
GENERIC_PLACEHOLDER_MARKERS = (
    "Homework diagram",
    "Formula diagram",
    "Handdrawn diagram",
)
# Match the marker only when it appears as the entire rendered label of an SVG —
# i.e. the trimmed content of <text>/<title>/<desc>, or the value of aria-label.
# Substring-anywhere matching was clobbering authored SVGs whose <path> data or
# longer descriptive text incidentally contained one of the marker phrases.
_GENERIC_SVG_LABEL_RE = re.compile(
    r"(?:<(?:text|title|desc)\b[^>]*>\s*(?:Homework diagram|Formula diagram|Handdrawn diagram)\s*</(?:text|title|desc)>"
    r"|\baria-label\s*=\s*[\"']\s*(?:Homework diagram|Formula diagram|Handdrawn diagram)\s*[\"'])",
    re.IGNORECASE,
)
MAX_EXTRACTED_IMAGE_BYTES = 8 * 1024 * 1024


@dataclass
class MediaMigrationStats:
    generated_urls_normalized: int = 0
    svg_data_uris_decoded: int = 0
    bitmap_data_uris_extracted: int = 0
    image_html_blocks_lifted: int = 0
    generic_svgs_rewritten: int = 0
    unresolved_bitmap_data_uris: int = 0

    def to_dict(self) -> dict[str, int]:
        return asdict(self)

    @property
    def total(self) -> int:
        return sum(self.to_dict().values())


def _normalize_generated_url(value: str) -> tuple[str, int]:
    count = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return match.group("path")

    return GENERATED_IMAGE_PATTERN.sub(repl, value), count


def _is_svg_data_uri(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(SVG_DATA_URI_PREFIX)


def _decode_svg_data_uri(value: str) -> str:
    return urllib.parse.unquote(value[len(SVG_DATA_URI_PREFIX):]).strip()


def _is_generic_svg(value: Any) -> bool:
    return isinstance(value, str) and bool(_GENERIC_SVG_LABEL_RE.search(value))


def _clean_label(label: str, subject: str) -> str:
    label = re.sub(r"<[^>]+>", " ", label or "")
    label = re.sub(r"\s+", " ", label).strip()
    if not label or label.lower() in {"diagram", "homework diagram", "formula diagram", "handdrawn diagram"}:
        return "Ko'phadlarni ajratish" if subject == "math-algebra" else "Mavzu diagrammasi"
    return label[:64]


def _context_svg(subject: str, label: str) -> str:
    title = html.escape(_clean_label(label, subject), quote=False)
    accent = "#0066CC" if subject == "math-algebra" else "#0F8A6C"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 540" role="img" aria-label="{title}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#F8FBFF"/>
      <stop offset="100%" stop-color="#EAF4FF"/>
    </linearGradient>
  </defs>
  <rect width="900" height="540" rx="34" fill="url(#bg)"/>
  <rect x="42" y="42" width="816" height="456" rx="28" fill="#FFFFFF" stroke="{accent}" stroke-width="4"/>
  <text x="78" y="106" font-family="Segoe UI, Arial, sans-serif" font-size="24" font-weight="800" fill="{accent}">{title}</text>
  <path d="M120 386 L292 184 L464 386 Z" fill="none" stroke="{accent}" stroke-width="10" stroke-linejoin="round"/>
  <path d="M548 188 H760 M548 270 H720 M548 352 H790" stroke="{accent}" stroke-width="10" stroke-linecap="round" opacity=".7"/>
</svg>"""


def _guess_label(node: Any, breadcrumbs: list[str], subject: str) -> str:
    if isinstance(node, dict):
        for key in ("title", "term", "label", "caption", "prompt", "question", "name", "text"):
            value = node.get(key)
            if isinstance(value, str) and value.strip():
                return _clean_label(value, subject)
    for crumb in reversed(breadcrumbs):
        if isinstance(crumb, str) and crumb.strip():
            return _clean_label(crumb, subject)
    return "Algebra" if subject == "math-algebra" else "Diagramma"


def _extract_bitmap_data_uri(src: str, hw_id: str | None, stats: MediaMigrationStats) -> str | None:
    match = BITMAP_DATA_URI_RE.match(src.strip())
    if not match:
        return None
    if not hw_id:
        stats.unresolved_bitmap_data_uris += 1
        return None
    raw = base64.b64decode(re.sub(r"\s+", "", match.group("data")), validate=True)
    if len(raw) > MAX_EXTRACTED_IMAGE_BYTES:
        stats.unresolved_bitmap_data_uris += 1
        return None
    kind = match.group("kind").lower().replace("jpeg", "jpg")
    digest = hashlib.sha256(raw).hexdigest()[:16]
    safe_hw_id = re.sub(r"[^A-Za-z0-9_.-]+", "-", hw_id)[:80]
    filename = f"{safe_hw_id}__media_{digest}.{kind}"
    out_dir = BASE_DIR / "frontend" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / filename).write_bytes(raw)
    stats.bitmap_data_uris_extracted += 1
    return f"/generated/{filename}"


def _normalize_image_src(src: str, hw_id: str | None, stats: MediaMigrationStats, *, write_files: bool) -> str:
    if _is_svg_data_uri(src):
        return src
    extracted = _extract_bitmap_data_uri(src, hw_id if write_files else None, stats)
    if extracted:
        return extracted
    normalized, count = _normalize_generated_url(src)
    stats.generated_urls_normalized += count
    return normalized


def _media_block_from_img_src(
    src: str,
    subject: str,
    label: str,
    hw_id: str | None,
    stats: MediaMigrationStats,
    *,
    write_files: bool,
) -> dict[str, str]:
    if _is_svg_data_uri(src):
        svg = _decode_svg_data_uri(src)
        stats.svg_data_uris_decoded += 1
        if not svg or _is_generic_svg(svg):
            svg = _context_svg(subject, label)
            stats.generic_svgs_rewritten += 1
        return {"type": "svg", "html": svg}
    return {"type": "image", "src": _normalize_image_src(src, hw_id, stats, write_files=write_files), "alt": label}


def _is_image_only_html(value: str) -> bool:
    stripped = (value or "").strip()
    if not stripped or "<img" not in stripped.lower():
        return False
    without = IMG_TAG_RE.sub("", stripped).strip()
    without = re.sub(r"<br\s*/?>", "", without, flags=re.IGNORECASE).strip()
    return without == ""


def _extract_img_alt(value: str) -> str | None:
    match = re.search(r'\balt=["\']([^"\']*)["\']', value or "", flags=re.IGNORECASE)
    if not match:
        return None
    alt = re.sub(r"\s+", " ", match.group(1)).strip()
    return alt or None


def _replace_img_srcs_in_html(
    value: str,
    subject: str,
    label: str,
    hw_id: str | None,
    stats: MediaMigrationStats,
    *,
    write_files: bool,
) -> str:
    def repl(match: re.Match[str]) -> str:
        src = match.group("src")
        if _is_svg_data_uri(src):
            svg = _decode_svg_data_uri(src)
            stats.svg_data_uris_decoded += 1
            if not svg or _is_generic_svg(svg):
                svg = _context_svg(subject, label)
                stats.generic_svgs_rewritten += 1
            return svg
        new_src = _normalize_image_src(src, hw_id, stats, write_files=write_files)
        if new_src == src:
            return match.group(0)
        return match.group(0).replace(src, new_src)

    return IMG_TAG_RE.sub(repl, value)


def _walk(node: Any, subject: str, hw_id: str | None, breadcrumbs: list[str], stats: MediaMigrationStats, *, write_files: bool) -> Any:
    if isinstance(node, dict):
        label = _guess_label(node, breadcrumbs, subject)
        node_type = node.get("type")

        if node_type == "image" and isinstance(node.get("src"), str):
            if _is_svg_data_uri(node["src"]):
                return _media_block_from_img_src(node["src"], subject, label, hw_id, stats, write_files=write_files)
            new_node = dict(node)
            new_node["src"] = _normalize_image_src(node["src"], hw_id, stats, write_files=write_files)
            return new_node

        if node_type == "svg" and isinstance(node.get("html"), str):
            html_value = node["html"]
            if _is_generic_svg(html_value):
                stats.generic_svgs_rewritten += 1
                new_node = dict(node)
                new_node["html"] = _context_svg(subject, label)
                return new_node

        if node_type in {"quote", "p", "text"} and isinstance(node.get("text"), str) and _is_image_only_html(node["text"]):
            src_match = IMG_TAG_RE.search(node["text"])
            if src_match:
                stats.image_html_blocks_lifted += 1
                img_label = _extract_img_alt(node["text"]) or label
                return _media_block_from_img_src(src_match.group("src"), subject, img_label, hw_id, stats, write_files=write_files)

        repaired: dict[str, Any] = {}
        next_breadcrumbs = breadcrumbs + [label] if label else breadcrumbs
        for key, value in node.items():
            if key in {"title", "term", "label", "caption", "prompt", "question", "name"} and isinstance(value, str):
                child_breadcrumbs = breadcrumbs + [value]
            else:
                child_breadcrumbs = next_breadcrumbs

            if key == "src" and isinstance(value, str):
                repaired[key] = _normalize_image_src(value, hw_id, stats, write_files=write_files)
            elif key == "html" and isinstance(value, str):
                if _is_generic_svg(value):
                    stats.generic_svgs_rewritten += 1
                    repaired[key] = _context_svg(subject, label)
                else:
                    repaired[key] = _replace_img_srcs_in_html(value, subject, label, hw_id, stats, write_files=write_files)
            elif key == "text" and isinstance(value, str):
                repaired[key] = _replace_img_srcs_in_html(value, subject, label, hw_id, stats, write_files=write_files)
            else:
                repaired[key] = _walk(value, subject, hw_id, child_breadcrumbs, stats, write_files=write_files)
        return repaired

    if isinstance(node, list):
        return [_walk(item, subject, hw_id, breadcrumbs, stats, write_files=write_files) for item in node]

    if isinstance(node, str):
        # Rich-field editors (boss.q, real_life.q1.q, flashcards.def, …) store
        # editor HTML under arbitrary keys, not just `html`/`text`. Any string
        # leaf carrying an <img> tag may hold a data URI that must be extracted
        # before _check_no_inline_bloat runs — otherwise PUT fails with 422.
        if IMG_TAG_RE.search(node):
            label = _guess_label(None, breadcrumbs, subject)
            return _replace_img_srcs_in_html(node, subject, label, hw_id, stats, write_files=write_files)
        normalized, count = _normalize_generated_url(node)
        stats.generated_urls_normalized += count
        if _is_svg_data_uri(normalized):
            stats.svg_data_uris_decoded += 1
            svg = _decode_svg_data_uri(normalized)
            if not svg or _is_generic_svg(svg):
                stats.generic_svgs_rewritten += 1
                return _context_svg(subject, _guess_label(None, breadcrumbs, subject))
            return svg
        return normalized

    return node


def migrate_content_media(
    content: Any,
    *,
    subject: str = "",
    hw_id: str | None = None,
    write_files: bool = False,
) -> tuple[Any, bool, MediaMigrationStats]:
    """Return a media-normalized deep copy of ``content``.

    Real generated assets are preserved. Absolute generated URLs are converted
    to server-relative paths so LAN IP changes stop breaking old rows.
    """
    stats = MediaMigrationStats()
    original = copy.deepcopy(content)
    repaired = _walk(original, subject, hw_id, [], stats, write_files=write_files)
    return repaired, repaired != content, stats
