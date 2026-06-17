"""Static regressions for text-only flashcard layout.

Real reproducer: HW-20260505-006 (Nisbiy xatolik) ships with no media on
all ten flashcards. Content should be visually centered, but the metadata row
must stay anchored at the top of each face.
"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).parent.parent
_JS_PATH = ROOT / "server" / "template" / "js" / "perfect_homework.js"
_CSS_PATH = ROOT / "server" / "template" / "static" / "css" / "perfect_homework.css"
_HTML_PATH = ROOT / "server" / "template" / "perfect_homework.html"
RUNTIME = _HTML_PATH.read_text(encoding="utf-8") + "\n" + _JS_PATH.read_text(encoding="utf-8") + "\n" + _CSS_PATH.read_text(encoding="utf-8")


def _read() -> str:
    return RUNTIME


def _css_block(source: str, selector: str) -> str:
    pattern = re.escape(selector) + r"\s*(?:,\s*[^{}]+)?\s*\{(?P<body>[^}]*)\}"
    match = re.search(pattern, source)
    assert match, f"missing CSS block for {selector}"
    return match.group("body")


def test_no_image_front_centers_content_without_moving_metadata():
    html = _read()
    assert ".fc-inner.no-image .fc-front,\n        .fc-inner.no-image .fc-back" not in html
    term_body = _css_block(html, ".fc-inner.no-image .fc-term")
    hint_body = _css_block(html, ".fc-inner.no-image .fc-front .fc-tap-hint")
    assert "margin-top: auto" in term_body
    assert "margin-bottom: auto" in hint_body


def test_no_image_back_centers_definition_without_moving_metadata():
    html = _read()
    body = _css_block(html, ".fc-inner.no-image .fc-definition")
    assert "margin-top: auto" in body
    assert "margin-bottom: auto" in body


def test_no_image_definition_font_bumped():
    html = _read()
    body = _css_block(html, ".fc-inner.no-image .fc-definition")
    m = re.search(r"font-size:\s*(\d+)px", body)
    assert m, "definition font-size missing on no-image cards"
    assert int(m.group(1)) >= 17


def test_no_image_term_still_large():
    html = _read()
    body = _css_block(html, ".fc-inner.no-image .fc-term")
    m = re.search(r"font-size:\s*(\d+)px", body)
    assert m, "term font-size missing on no-image cards"
    assert int(m.group(1)) >= 26


def test_flashcard_caret_exponents_are_formatted_inline():
    html = _read()
    assert "function fcFormatInlineMathHtml" in html
    assert "replace(/([A-Za-z0-9αβγ])\\^([0-9]+)/g" in html
    assert "defEl.innerHTML = fcFormatInlineMathHtml" in html
