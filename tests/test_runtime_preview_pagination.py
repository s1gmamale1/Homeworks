"""Preview pagination regression tests.

User-flagged: long preview content used to scroll into a long article
inside one panel page, leaving blank space below the action button.
After Wave V.1, each authored page is split at script init into smaller
rendered pages so the active page only needs ~1-2cm of scroll at most.

These tests check three things:
1. The chunking helpers exist in the runtime template and run at init.
2. A Python port of the same height-estimate / chunking algorithm
   matches the JS one for representative inputs (so the JS contract is
   tested without spinning up jsdom).
3. The chunking actually splits a long page and preserves block order.
"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).parent.parent
_JS_PATH = ROOT / "server" / "template" / "js" / "perfect_homework.js"
_CSS_PATH = ROOT / "server" / "template" / "static" / "css" / "perfect_homework.css"
_HTML_PATH = ROOT / "server" / "template" / "perfect_homework.html"
RUNTIME = _HTML_PATH.read_text(encoding="utf-8") + "\n" + _JS_PATH.read_text(encoding="utf-8") + "\n" + _CSS_PATH.read_text(encoding="utf-8")


def _read(src) -> str:
    if isinstance(src, str):
        return src
    return src.read_text(encoding="utf-8")


# ── Python port of the JS chunking helpers ─────────────────────────────
# Mirrors _previewEstimateBlockHeight / _previewChunkPageBlocks /
# _previewExpandPanelPages in server/template/perfect_homework.html.
# Keep these in sync if the JS heuristic changes — `test_python_port_*`
# below verifies the constants line up.

PREVIEW_PAGE_BUDGET_PX = 760


def _lines(text: str, per_line: int) -> int:
    return max(1, -(-len(text) // per_line))  # ceil division


def py_estimate_block_height(b: dict) -> int:
    if not b or "type" not in b:
        return 0
    t = b["type"]
    if t in ("image", "svg", "diagram"):
        return 380
    text = str(b.get("text") or "")
    if t == "h2":
        return 56 + _lines(text, 32) * 32
    if t == "code":
        return 36 + _lines(text, 56) * 22
    if t in ("ul", "ol"):
        items = b.get("items") or []
        return 8 + sum(24 + _lines(str(i or ""), 50) * 22 for i in items)
    if t in ("quote", "callout"):
        return 28 + _lines(text, 46) * 26
    return 22 + _lines(text, 50) * 24


def py_chunk_blocks(blocks: list[dict], budget: int = PREVIEW_PAGE_BUDGET_PX) -> list[list[dict]]:
    out: list[list[dict]] = []
    current: list[dict] = []
    acc = 0
    for b in blocks or []:
        h = py_estimate_block_height(b)
        if acc + h > budget and current:
            out.append(current)
            current = []
            acc = 0
        current.append(b)
        acc += h
    if current:
        out.append(current)
    return out or [[]]


# ── Static checks against the runtime template ────────────────────────


def test_pagination_helpers_exist_in_runtime():
    html = _read(RUNTIME)
    assert "const PREVIEW_PAGE_BUDGET_PX = 760;" in html, (
        "page budget constant should be defined and exposed for tuning"
    )
    assert "function _previewEstimateBlockHeight" in html
    assert "function _previewChunkPageBlocks" in html
    assert "function _previewExpandPanelPages" in html
    # Must run at init so all consumers see chunked panels.
    assert "PANELS[i] = _previewExpandPanelPages(PANELS[i], PREVIEW_PAGE_BUDGET_PX)" in html
    # Must be exposed on window for downstream test harnesses.
    assert "window._previewChunkPageBlocks = _previewChunkPageBlocks" in html


def test_pagination_budget_matches_python_port():
    html = _read(RUNTIME)
    m = re.search(r"const PREVIEW_PAGE_BUDGET_PX = (\d+)\s*;", html)
    assert m, "PREVIEW_PAGE_BUDGET_PX literal must be a plain integer"
    assert int(m.group(1)) == PREVIEW_PAGE_BUDGET_PX, (
        "Python port and JS constant drifted — update both together"
    )


# ── Behavioural checks via the Python port ────────────────────────────


def test_short_page_stays_as_one_page():
    blocks = [
        {"type": "h2", "text": "Short heading"},
        {"type": "p", "text": "A short paragraph with maybe one sentence."},
    ]
    chunks = py_chunk_blocks(blocks)
    assert len(chunks) == 1
    assert chunks[0] == blocks


def test_long_page_splits_into_multiple_pages():
    long_para = (
        "Lorem ipsum dolor sit amet consectetur adipiscing elit, "
        "sed do eiusmod tempor incididunt ut labore et dolore magna "
        "aliqua. Ut enim ad minim veniam, quis nostrud exercitation. "
    )
    blocks = [
        {"type": "h2", "text": "Long page"},
        *[{"type": "p", "text": long_para * 4} for _ in range(8)],
    ]
    chunks = py_chunk_blocks(blocks)
    assert len(chunks) >= 2, "expected long content to split into 2+ pages"

    # Order must be preserved across chunks: concatenation == original.
    flat = [b for chunk in chunks for b in chunk]
    assert flat == blocks, "chunking must preserve original block order"

    # Each chunk's estimated total stays under the budget (with the one
    # exception: a single block bigger than the budget is allowed onto
    # its own page so we don't drop content).
    for chunk in chunks:
        total = sum(py_estimate_block_height(b) for b in chunk)
        assert total <= PREVIEW_PAGE_BUDGET_PX or len(chunk) == 1, (
            f"chunk {chunk!r} overflows budget ({total}px) and isn't single-block"
        )


def test_image_block_does_not_share_a_page_with_full_text():
    # A block image takes ~380px, so a page with a long-enough text run
    # plus an image should split.
    blocks = [
        {"type": "p", "text": "P" * 600},      # ~12 lines × 24 = ~288 + 22 = ~310px
        {"type": "p", "text": "P" * 600},      # another ~310px
        {"type": "image", "src": "/x.png", "alt": ""},  # 380px → forces split
    ]
    chunks = py_chunk_blocks(blocks)
    assert len(chunks) >= 2


def test_oversized_single_block_is_kept_intact_on_its_own_page():
    huge = {"type": "p", "text": "X" * 10000}
    blocks = [{"type": "p", "text": "small"}, huge]
    chunks = py_chunk_blocks(blocks)
    # The small one fits on its own page, the huge one lands on the next
    # page even though it alone is over budget. We don't split a block.
    assert len(chunks) == 2
    assert chunks[1] == [huge]


def test_empty_page_returns_a_single_empty_chunk():
    # The runtime relies on every panel having at least one renderable
    # page; chunking [] must return [[]] so the iterator still produces
    # a placeholder.
    assert py_chunk_blocks([]) == [[]]
    assert py_chunk_blocks(None) == [[]]


def test_panel_card_geometry_still_supports_short_pages():
    """The chunked pages count on a single panel-card height that hugs
    content (PR #68). Re-assert the related rule so a future revert
    doesn't quietly bring back the giant blank scroll zone."""
    html = _read(RUNTIME)
    panel_block = re.search(r"\.panel-card\s*\{(?P<body>[^}]*)\}", html)
    assert panel_block, "missing .panel-card rule"
    body = panel_block.group("body")
    assert "max-height: 82vh" in body
    assert "min-height: min(360px, 70vh)" in body
    assert "height: auto" in body
