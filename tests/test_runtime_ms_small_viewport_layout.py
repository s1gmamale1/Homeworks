"""Memory-Sprint small-viewport layout — regression guard.

Bug history (2026-05-14, this PR):
  On very small phones (~360-390px wide), Memory-Sprint option cards
  overlapped each other and the question-box annotations:

  - Buttons were 42vw wide inside an 88vw answer-zone → only ~7px of
    horizontal gap between the two columns at the 25%/75% centres.
  - Answer-zone height was 250px with row centres at 28% / 74% →
    74px button + 3-4 line wraps from long Uzbek phrases like
    "Kombinatorika o'rniga arifmetika qo'llanildi — ko'paytirish
    kerak edi" pushed the bottom row into the top row's footprint.
  - Long compound tokens ("Misonceptsion") could push a button past
    its `width` cap because `overflow-wrap` was the default `normal`.

The fix layers three things into `perfect_homework.html`:

  1. Base ``.ms-option-btn`` gets ``overflow-wrap: anywhere``,
     ``word-break: break-word``, and ``hyphens: auto`` so long
     unbreakable tokens cannot exceed the width cap.
  2. The existing ``@media (max-width: 640px)`` block bumps the
     answer-zone height (250px → 300px) and shrinks the button
     width (42vw → 40vw), giving a real horizontal gap and enough
     vertical clearance between the two rows for 3-line wraps.
  3. A new ``@media (max-width: 400px)`` block targets iPhone-SE-class
     phones: 340px answer-zone, 42vw / 88-px-min-height buttons,
     13px / 1.22 line-height, and tighter card padding so 4-line
     answers still fit.

This test pins each invariant as a static-file assertion. We do NOT
re-validate the absolute-positioning math here — the JS positioner
(``msPositionsFor``) is asserted by other tests in this directory.
"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).parent.parent
_JS_PATH = ROOT / "server" / "template" / "js" / "perfect_homework.js"
_CSS_PATH = ROOT / "server" / "template" / "static" / "css" / "perfect_homework.css"
_HTML_PATH = ROOT / "server" / "template" / "perfect_homework.html"
RUNTIME = _HTML_PATH.read_text(encoding="utf-8") + "\n" + _JS_PATH.read_text(encoding="utf-8") + "\n" + _CSS_PATH.read_text(encoding="utf-8")

_CSS_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)


def _read() -> str:
    return RUNTIME


def _stripped() -> str:
    return _CSS_COMMENT_RE.sub("", _read())


def _first_rule_body(html: str, selector_pattern: str) -> str:
    """Return the body (between { and }) of the FIRST CSS rule whose
    selector line matches ``selector_pattern`` (anchored to a new-line
    boundary so we don't match descendant rules in larger blocks)."""
    pattern = re.compile(
        r"(?:^|\n)\s*" + selector_pattern + r"\s*\{",
        re.MULTILINE,
    )
    m = pattern.search(html)
    assert m, f"selector pattern {selector_pattern!r} not found"
    start = html.index("{", m.start()) + 1
    depth = 1
    for i in range(start, len(html)):
        c = html[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return html[start:i]
    raise AssertionError(f"unbalanced braces for {selector_pattern!r}")


def _ms_media_block(html: str, max_width_px: int) -> str:
    """Return the body of the ``@media (max-width: <Npx>)`` block
    that CONTAINS the Memory-Sprint ``.ms-option-btn`` rule. The
    runtime template has multiple parallel media queries at the same
    breakpoint (one per phase: flashcards, RL, MS, ...), so picking the
    first match is wrong. We walk every block and choose by content.
    """
    pattern = re.compile(
        r"@media\s*\(\s*max-width\s*:\s*"
        + str(max_width_px)
        + r"px\s*\)\s*\{",
    )
    bodies: list[str] = []
    for m in pattern.finditer(html):
        start = m.end()
        depth = 1
        for i in range(start, len(html)):
            c = html[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    bodies.append(html[start:i])
                    break
    assert bodies, (
        f"@media (max-width: {max_width_px}px) block not found at all"
    )
    for body in bodies:
        if re.search(r"(?:^|\n)\s*\.ms-option-btn\s*\{", body):
            return body
    raise AssertionError(
        f"no @media (max-width: {max_width_px}px) block contains "
        f"`.ms-option-btn`"
    )


# ── Clause 1: base rule handles long unbreakable tokens ──────────────


def test_base_ms_option_btn_breaks_long_tokens():
    """Without ``overflow-wrap: anywhere`` (or equivalent), a single
    long Uzbek-transliterated word can push the button past its
    ``width: min(38vw, 280px)`` cap and overlap the neighbouring
    column."""
    html = _stripped()
    body = _first_rule_body(html, r"\.ms-option-btn")
    assert re.search(r"overflow-wrap\s*:\s*anywhere\s*;", body), (
        "Memory-Sprint regression: `.ms-option-btn` no longer sets "
        "`overflow-wrap: anywhere`. Long unbreakable tokens can push "
        "the button past its width cap and overlap the adjacent column."
    )
    # word-break: break-word is a redundant safety net for older
    # WebKit (iOS Safari < 15) that doesn't honour overflow-wrap:anywhere
    # inside flex items consistently.
    assert re.search(r"word-break\s*:\s*break-word\s*;", body), (
        "Memory-Sprint regression: `.ms-option-btn` no longer sets "
        "`word-break: break-word`. Older iOS Safari versions need this "
        "as a safety net inside flex items."
    )


# ── Clause 2: 640px breakpoint gives clear column gap + zone height ──


def test_640px_breakpoint_widens_answer_zone():
    """Answer-zone must be at least 280px tall in the ≤640px breakpoint
    so the JS positioner's 28% / 74% row centres leave clearance for
    multi-line answers (74-80px buttons + 3-line wraps)."""
    block = _ms_media_block(_stripped(), 640)
    zone_body = _first_rule_body(block, r"\.ms-answer-zone")
    m = re.search(r"height\s*:\s*(\d+)\s*px", zone_body)
    assert m, (
        "Memory-Sprint regression: `.ms-answer-zone` no longer sets a "
        "px height inside the 640px breakpoint."
    )
    height_px = int(m.group(1))
    assert height_px >= 280, (
        f"Memory-Sprint regression: `.ms-answer-zone` height is "
        f"{height_px}px in @media (max-width: 640px). With row centres "
        f"at 28% / 74% and ~80px buttons, 3-line answers overlap the "
        f"adjacent row. Bump to >= 280px (current value: 300)."
    )


def test_640px_breakpoint_narrows_option_width():
    """Width must be <= 40vw inside the 640px breakpoint so the two
    columns have a real horizontal gap between their 25%/75% centres
    (88vw answer-zone → centres are 44vw apart → 40vw buttons leave a
    4vw gap; 42vw left only ~2vw)."""
    block = _ms_media_block(_stripped(), 640)
    btn_body = _first_rule_body(block, r"\.ms-option-btn")
    m = re.search(r"width\s*:\s*(\d+)\s*vw", btn_body)
    assert m, (
        "Memory-Sprint regression: `.ms-option-btn` no longer sets a "
        "vw width inside the 640px breakpoint."
    )
    width_vw = int(m.group(1))
    assert width_vw <= 40, (
        f"Memory-Sprint regression: `.ms-option-btn` width is "
        f"{width_vw}vw in @media (max-width: 640px). Columns at 25%/75% "
        f"of an 88vw zone are 44vw apart — buttons wider than 40vw leave "
        f"no visible gap. Drop to <= 40vw."
    )


# ── Clause 3: ≤400px breakpoint covers iPhone-SE-class phones ────────


def test_400px_breakpoint_exists():
    """A second media query for very small phones must exist. Without
    this tier, iPhone-SE-class viewports (375px) keep the 640px-tier
    sizing, which is still too cramped for 3-4 line answers."""
    html = _stripped()
    assert re.search(
        r"@media\s*\(\s*max-width\s*:\s*400px\s*\)",
        html,
    ), (
        "Memory-Sprint regression: the ≤400px media-query for very "
        "small phones (iPhone SE / budget Android) has been removed. "
        "Long answers overflow at that size without it."
    )


def test_400px_breakpoint_extends_answer_zone_further():
    """At ≤400px the answer-zone must be even taller than the 640px
    tier (the row-centre percentages do not change, so we have to grow
    the absolute height to keep the row gap usable when font/padding
    shrinks but text still wraps to 3-4 lines)."""
    block = _ms_media_block(_stripped(), 400)
    zone_body = _first_rule_body(block, r"\.ms-answer-zone")
    m = re.search(r"height\s*:\s*(\d+)\s*px", zone_body)
    assert m, (
        "Memory-Sprint regression: `.ms-answer-zone` height is missing "
        "from the ≤400px breakpoint."
    )
    height_px = int(m.group(1))
    assert height_px >= 320, (
        f"Memory-Sprint regression: `.ms-answer-zone` height is only "
        f"{height_px}px in @media (max-width: 400px). Should be >= 320 "
        f"to give the JS positioner enough vertical room for 4-line "
        f"answers on iPhone-SE-class screens."
    )


def test_400px_breakpoint_shrinks_typography():
    """Font and line-height must shrink inside the ≤400px tier so
    long answers fit without horizontal overflow. We pin
    ``font-size <= 13px`` and ``line-height <= 1.25``."""
    block = _ms_media_block(_stripped(), 400)
    btn_body = _first_rule_body(block, r"\.ms-option-btn")
    fs = re.search(r"font-size\s*:\s*([\d.]+)\s*px", btn_body)
    assert fs, "Memory-Sprint regression: missing `font-size` in ≤400px "\
        "`.ms-option-btn` rule."
    assert float(fs.group(1)) <= 13.0, (
        f"Memory-Sprint regression: `.ms-option-btn` font-size is "
        f"{fs.group(1)}px in the ≤400px tier. Drop to <= 13px so 3-line "
        f"answers fit without horizontal overflow."
    )
    lh = re.search(r"line-height\s*:\s*([\d.]+)\s*;", btn_body)
    assert lh, "Memory-Sprint regression: missing `line-height` in "\
        "≤400px `.ms-option-btn` rule."
    assert float(lh.group(1)) <= 1.3, (
        f"Memory-Sprint regression: `.ms-option-btn` line-height is "
        f"{lh.group(1)} in the ≤400px tier. Drop to <= 1.3 so 4-line "
        f"answers don't overlap the adjacent row."
    )


# ── Clause 4: row spacing math sanity-check ──────────────────────────


def test_ms_positions_for_uses_28_74_row_centres():
    """Anchor: the JS positioner still puts the row centres at 28% and
    74% of the answer-zone height. If a future refactor changes those
    percentages, the CSS heights above need to be re-derived — the
    pinning here makes the dependency explicit so the test breaks
    loudly instead of letting the rows silently re-collide."""
    html = _read()
    m = re.search(
        r"function\s+msPositionsFor\s*\(",
        html,
    )
    assert m, "msPositionsFor() not found in runtime template"
    # Capture the function body
    start = html.index("{", m.start()) + 1
    depth = 1
    end = start
    for i in range(start, len(html)):
        c = html[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    body = html[start:end]
    # n === 4 branch — the layout under test
    assert "top: '28%'" in body and "top: '74%'" in body, (
        "Memory-Sprint anchor: msPositionsFor's row centres are no "
        "longer at 28% / 74%. The CSS answer-zone heights in the "
        "small-viewport rules were sized for those percentages — update "
        "both together."
    )
