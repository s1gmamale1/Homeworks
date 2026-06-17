"""Regression tests for Bug #2 — Reading segment + question on the same page.

Pre-fix: `readingBuildPages` emitted TWO pages per segment-with-checkpoint
(a `kind:'text'` page followed by a `kind:'question'` page). The student had
to swipe past the passage to land on a near-empty card with just the
question, then swipe back to re-read.

Post-fix: when a segment carries a checkpoint, `readingBuildPages` emits
ONE combined page `kind:'segment_with_question'` that wraps the passage
text on top with the question + input + check button + feedback area
directly below it inside the same `.wave2-slide-page`.

These tests pin the new contract so a future refactor can't silently
revert to the two-page split.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_JS_PATH = Path(__file__).resolve().parent.parent / "server" / "template" / "js" / "perfect_homework.js"
_CSS_PATH = Path(__file__).resolve().parent.parent / "server" / "template" / "static" / "css" / "perfect_homework.css"
_HTML_PATH = Path(__file__).resolve().parent.parent / "server" / "template" / "perfect_homework.html"


def _template() -> str:
    return _HTML_PATH.read_text(encoding="utf-8") + "\n" + _JS_PATH.read_text(encoding="utf-8") + "\n" + _CSS_PATH.read_text(encoding="utf-8")


def _slice_function(name: str, html: str | None = None) -> str:
    """Return the source slice for a JS `function name(...)` block.

    Cuts from the function header to the next top-level `function ` keyword
    so we can grep invariants without a real JS parser.
    """
    src = html if html is not None else _template()
    start = src.find(f"function {name}(")
    assert start != -1, f"function {name} not found in template"
    after = src.find("\n        function ", start + 1)
    if after == -1:
        after = len(src)
    return src[start:after]


# ---------------------------------------------------------------------------
# Pin the literal page-kind enum
# ---------------------------------------------------------------------------

def test_segment_with_question_kind_present():
    """The 'segment_with_question' literal must exist somewhere in the template,
    either single- or double-quoted. This is the cheapest contract pin."""
    src = _template()
    assert "'segment_with_question'" in src or '"segment_with_question"' in src, (
        "the new combined page kind 'segment_with_question' is missing from "
        "the runtime template — Bug #2 reverted"
    )


# ---------------------------------------------------------------------------
# readingBuildPages emits one combined page per segment+checkpoint
# ---------------------------------------------------------------------------

def test_reading_segment_with_question_emits_combined_page():
    """`readingBuildPages` must emit a single `kind:'segment_with_question'`
    page when a segment carries a checkpoint, instead of two separate
    `kind:'text'` + `kind:'question'` pages."""
    body = _slice_function("readingBuildPages")
    # The new page kind must be emitted somewhere in the segment loop.
    assert "kind: 'segment_with_question'" in body, (
        "readingBuildPages must emit kind:'segment_with_question' for "
        "segments that carry a checkpoint"
    )
    # The combined page must carry both the passage HTML and the cpIndex
    # (so the renderer can grab the right checkpoint).
    assert re.search(
        r"kind:\s*'segment_with_question',\s*html:\s*segText,\s*cpIndex:\s*i",
        body,
    ), (
        "the combined page must include both `html: segText` and `cpIndex: i` "
        "so the renderer can build the passage + question stack from a single page"
    )


def test_reading_segment_without_checkpoint_keeps_text_only_page():
    """A segment with NO checkpoint stays a `kind:'text'` page — the new
    combined kind must NOT eat the text-only path."""
    body = _slice_function("readingBuildPages")
    assert "kind: 'text'" in body, (
        "readingBuildPages must still emit kind:'text' for segments that "
        "have no checkpoint (text-only segments)"
    )
    # Sanity: the segment-aware loop must check seg.checkpoint to decide
    # which page kind to emit. (Pin the predicate name so a refactor that
    # renames it triggers this test.)
    assert re.search(
        r"seg\.checkpoint",
        body,
    ), "the segment loop must consult seg.checkpoint to pick the page kind"


def test_reading_no_two_pages_per_segment_when_combined():
    """The pre-fix pattern (push text page, then push question page back-to-back
    inside the segment loop) must not survive. The combined-page path must
    NOT emit BOTH a `kind:'text'` AND a `kind:'question'` for the same segment.
    """
    body = _slice_function("readingBuildPages")
    # Specifically: the unconditional pre-fix pattern was
    #   pages.push({ kind: 'text', html: segText });
    #   pages.push({ kind: 'question', cpIndex: i });
    # That two-line back-to-back push must be gone or guarded by
    # an else-branch (text-only segments) — never both for the same segment.
    pattern = (
        r"pages\.push\(\s*\{\s*kind:\s*'text'[^}]*\}\s*\)\s*;"
        r"\s*pages\.push\(\s*\{\s*kind:\s*'question'"
    )
    assert not re.search(pattern, body), (
        "the pre-fix two-page-push for a segment with checkpoint is back "
        "— Bug #2 regression"
    )


# ---------------------------------------------------------------------------
# renderReading + updateReadingContinueState handle the new kind
# ---------------------------------------------------------------------------

def test_reading_renderer_handles_segment_with_question_kind():
    """`renderReading` must contain a branch for the combined page kind
    that builds passage + checkpoint block in the same .wave2-slide-page."""
    body = _slice_function("renderReading")
    assert "page.kind === 'segment_with_question'" in body, (
        "renderReading must have a `page.kind === 'segment_with_question'` "
        "branch — without it the combined page never renders"
    )
    # The branch must call the existing _buildReadingCheckpointBlock helper
    # in 'segment' mode (auto-advance after correct, no manual Next button).
    # This guarantees we don't duplicate the question/input/feedback logic.
    assert "_buildReadingCheckpointBlock" in body, (
        "renderReading must reuse _buildReadingCheckpointBlock for the "
        "combined page so the question UI doesn't get duplicated"
    )


def test_reading_continue_state_recognises_combined_page():
    """`updateReadingContinueState` must treat the combined page kind the
    same as a `'question'` page when checking pageNeedsAnswer — otherwise
    the lock message never appears for the new combined panels."""
    body = _slice_function("updateReadingContinueState")
    assert "currentPage.kind === 'segment_with_question'" in body, (
        "updateReadingContinueState must check for "
        "currentPage.kind === 'segment_with_question' alongside 'question' "
        "so the answer-lock state still applies on combined pages"
    )


def test_reading_can_advance_blocks_unanswered_combined_page():
    """The wave2 `canAdvance` hook inside renderReading must block forward
    motion from an unanswered combined page (same lock as plain question)."""
    body = _slice_function("renderReading")
    assert "fromPage.kind === 'segment_with_question'" in body, (
        "canAdvance must block forward navigation on "
        "fromPage.kind === 'segment_with_question' just like 'question' — "
        "without that branch the lock invariant doesn't apply to combined pages"
    )


# ---------------------------------------------------------------------------
# Legacy fixture path stays untouched
# ---------------------------------------------------------------------------

def test_reading_legacy_chunker_path_preserved():
    """No-segments path still emits `kind:'legacy'` pages so old fixtures
    keep their geometric checkpoint distribution."""
    body = _slice_function("readingBuildPages")
    assert "kind: 'legacy', html" in body, (
        "the legacy chunker path must keep emitting kind:'legacy' pages "
        "so pre-segment fixtures don't break"
    )


def test_reading_legacy_renderer_branch_preserved():
    """`renderReading` must keep its 'legacy' branch (chunker fallback)."""
    body = _slice_function("renderReading")
    # Legacy branch present — the comment `} else { // 'legacy'` is the marker.
    assert "// 'legacy'" in body or "page.kind === 'legacy'" in body or "default" in body, (
        "renderReading legacy branch is gone — back-compat regression"
    )
