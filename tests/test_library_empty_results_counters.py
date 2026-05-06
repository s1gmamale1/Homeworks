"""
LIB-counter-01: when a search/filter on the library returns zero
homeworks, the Total / Subjects / Hard / Uzbek stat strip must still
render (showing 0 in every slot) instead of vanishing entirely. The
prior code early-returned to the empty state before `renderStats()`
ever ran, so users had no readout that the filter dropped the count
to zero.

These are static guards on `frontend/js/library.js` because the page
is plain ES module JS — there's no React or jsdom in the test stack,
and a pure source check is enough to catch the regression that
re-introduces an early `return` between `hide(loadingEl)` and the
stats render.
"""
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).parent.parent
LIBRARY_JS = ROOT / "frontend" / "js" / "library.js"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_and_render_body() -> str:
    """Return the source of the `loadAndRender` function body so the
    assertions don't get fooled by a `renderStats` reference inside
    some other helper (e.g. a future per-tile stats panel)."""
    src = _read(LIBRARY_JS)
    match = re.search(
        r"async function loadAndRender\s*\([^)]*\)\s*\{",
        src,
    )
    assert match, "loadAndRender function not found in library.js"
    start = match.end()
    # Walk the brace stack to find the matching close brace.
    depth = 1
    i = start
    while i < len(src) and depth > 0:
        ch = src[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        i += 1
    assert depth == 0, "unbalanced braces walking loadAndRender body"
    return src[start : i - 1]


def test_load_and_render_calls_render_stats_before_empty_branch():
    """`renderStats(items)` must run BEFORE the `!items.length` guard so
    a zero-result search shows 0 in every counter card, not nothing."""
    body = _load_and_render_body()
    stats_idx = body.find("renderStats(items)")
    empty_branch = re.search(r"if\s*\(\s*!\s*items\.length\s*\)", body)
    assert stats_idx >= 0, (
        "renderStats(items) call missing from loadAndRender — the stat "
        "strip will never populate."
    )
    assert empty_branch, (
        "expected `if (!items.length)` empty-state branch in loadAndRender."
    )
    assert stats_idx < empty_branch.start(), (
        "renderStats(items) must be invoked BEFORE the empty-state branch "
        "or the Total/Subjects/Hard/Uzbek counters disappear when a search "
        "returns nothing instead of reading 0."
    )


def test_load_and_render_reveals_stats_before_empty_branch():
    """`reveal(statsEl)` must also run before the empty branch — otherwise
    we render the stats DOM but leave the section `hidden`."""
    body = _load_and_render_body()
    reveal_idx = body.find("reveal(statsEl)")
    empty_branch = re.search(r"if\s*\(\s*!\s*items\.length\s*\)", body)
    assert reveal_idx >= 0, (
        "reveal(statsEl) call missing from loadAndRender — the stat "
        "strip will stay [hidden] even after renderStats fills it."
    )
    assert empty_branch, (
        "expected `if (!items.length)` empty-state branch in loadAndRender."
    )
    assert reveal_idx < empty_branch.start(), (
        "reveal(statsEl) must run BEFORE the empty-state branch so the "
        "rendered zero-counters are visible to the user."
    )


def test_render_stats_handles_empty_array_with_zeros():
    """Sanity-check the helper itself: when handed `[]` it produces a
    zero in every numeric slot. Done by asserting the source uses the
    real array length / Set size / running totals (no hard-coded
    minimum) so an empty input naturally yields zeros."""
    src = _read(LIBRARY_JS)
    match = re.search(r"function renderStats\s*\([^)]*\)\s*\{", src)
    assert match, "renderStats function not found"
    start = match.end()
    depth = 1
    i = start
    while i < len(src) and depth > 0:
        ch = src[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        i += 1
    body = src[start : i - 1]
    # The four counters must come from the input list, not constants.
    assert "items.length" in body, "Total counter must derive from items.length"
    assert "subjectIds.size" in body, "Subjects counter must derive from a Set size"
    assert re.search(r"\bhard\b", body), "Hard counter local must be present"
    assert re.search(r"\buz\b", body), "Uzbek counter local must be present"
