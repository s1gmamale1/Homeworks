#!/usr/bin/env python3
"""
polish_game_breaks.py — Fix the format issues in HW-007's Game Breaks:
  1. Strip leading `[Bloom: ... | PISA: ...]` tag from each question's body
     (the tag still lives in the dedicated `tags` field — we just remove
     the duplicate that's leaking into the visible prompt).
  2. Restore Q1's SVG by re-parsing it from the source MD (it got stripped
     to text-only labels during an earlier builder roundtrip).
  3. Clean up Sentence Fill question text — collapse LaTeX-escaped
     underscores `\\_\\_\\_` to plain `___` so the blank renders cleanly.
"""

import json
import re
import urllib.request
from pathlib import Path

BUILDER = "http://127.0.0.1:8000"
HW = "HW-20260427-007"
SRC_MD = Path(r"D:/Aylananing Kesuvchilari Burchaklari Xossasi (grade 8 geometry).md")


def http_get(url):
    return json.loads(urllib.request.urlopen(url, timeout=15).read().decode("utf-8"))


def http_put(url, body):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="PUT",
                                  headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=15).read().decode("utf-8"))


# Tag pattern: optional backticks around `[Bloom: ... | PISA: ...]`
TAG_PATTERN = re.compile(r"^`?\s*\[Bloom:[^\]]*\]\s*`?\s*\n?", re.M)


def strip_inline_tags(text: str) -> str:
    """Remove the leading [Bloom: ... | PISA: ...] tag line from a question."""
    cleaned = TAG_PATTERN.sub("", text, count=1).lstrip()
    return cleaned


def clean_blank_marker(text: str) -> str:
    """Replace LaTeX-escaped underscores with a clean blank marker.
    `\\_\\_\\_` and `\\text{ \\_\\_\\_ }` become `___`."""
    # \text{ \_\_\_ } -> ___
    text = re.sub(r"\\text\{\s*(?:\\_)+\s*\}", "___", text)
    # bare \_\_\_ -> ___
    text = re.sub(r"(?:\\_){2,}", "___", text)
    return text


def reparse_q1_svg_from_source() -> str:
    """Pull the original Q1 (1-Savol) SVG out of the source MD."""
    md = SRC_MD.read_text(encoding="utf-8")
    # Q1 sits between "**1-Savol" and "**2-Savol"
    chunk = re.search(r"\*\*1-Savol[\s\S]+?\*\*2-Savol", md)
    if not chunk:
        return ""
    svg_match = re.search(r"```svg\s*(<svg[\s\S]+?</svg>)\s*```", chunk.group(0))
    return svg_match.group(1).strip() if svg_match else ""


def main():
    record = http_get(f"{BUILDER}/api/homeworks/{HW}")
    c = record["content_json"]

    aq = c.get("gb_adaptive_quiz", [])
    wc = c.get("gb_why_chain", [])

    # ---- (1) Strip Bloom/PISA tag from Adaptive Quiz + Sentence Fill ----
    print("--- Cleaning question text ---")
    for q in aq + wc:
        if q.get("q"):
            before = q["q"][:60]
            q["q"] = strip_inline_tags(q["q"])
            q["q"] = clean_blank_marker(q["q"])
            after = q["q"][:60]
            if before != after:
                print(f"  [clean] {before!r}")
                print(f"      ->  {after!r}")

    # ---- (2) Restore Q1 SVG from source ----
    if aq and ("<svg" not in aq[0].get("q", "")):
        svg = reparse_q1_svg_from_source()
        if svg:
            # Question body without SVG tail
            body = aq[0]["q"]
            # Drop any junk svg-wrap div the previous import left behind
            body = re.sub(r"<br>\s*<div[^>]*svg-wrap[^>]*>[\s\S]*?</div>\s*$", "", body)
            body = body.rstrip()
            aq[0]["q"] = body + f"<br><div class='svg-wrap' style='max-width:300px'>{svg}</div>"
            print(f"  [restored Q1 SVG] {len(svg)} chars")
        else:
            print("  [WARN] Could not extract Q1 SVG from source MD")

    # PUT
    http_put(f"{BUILDER}/api/homeworks/{HW}", {"content_json": c})
    print("\n[OK] PUT /api/homeworks/" + HW)

    # Verify
    rec2 = http_get(f"{BUILDER}/api/homeworks/{HW}")
    aq2 = rec2["content_json"].get("gb_adaptive_quiz", [])
    wc2 = rec2["content_json"].get("gb_why_chain", [])

    print("\n=== After polish ===")
    for i, q in enumerate(aq2, 1):
        starts = q["q"][:50].replace("\n", " ")
        has_svg = "<svg" in q["q"]
        has_tag_inline = q["q"].lstrip().startswith("`[Bloom") or q["q"].lstrip().startswith("[Bloom")
        print(f"  AQ Q{i}: tag-inline={has_tag_inline}  has-svg={has_svg}  starts={starts!r}")
    for i, q in enumerate(wc2, 1):
        starts = q["q"][:50].replace("\n", " ")
        has_underscore_latex = "\\_\\_" in q["q"]
        has_tag_inline = q["q"].lstrip().startswith("`[Bloom") or q["q"].lstrip().startswith("[Bloom")
        print(f"  SF Q{i}: tag-inline={has_tag_inline}  latex-underscore={has_underscore_latex}  starts={starts!r}")


if __name__ == "__main__":
    main()
