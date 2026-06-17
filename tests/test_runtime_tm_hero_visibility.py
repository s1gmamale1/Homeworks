"""Tile-Match hero card visibility contract — regression guard.

Bug history (2026-05-14):
  ``.gb-tm-hero`` was effectively invisible on narrower viewports and
  inside the builder preview iframe. Two compounding causes:

  1. The card's surface relied on ``backdrop-filter`` plus a
     near-transparent white gradient (``rgba(255,255,255,.42 -> .20)``)
     and a white-on-white border ``var(--surface-border)`` (which is
     ``rgba(255,255,255,.5)`` in light mode). On the page's
     ``#f5f5f7`` background — and in any environment where
     ``backdrop-filter`` degrades (older Android Chrome, embedded
     webviews, the builder iframe) — the card had no contrast and
     read as floating dark text.
  2. The parent ``.gb-game-panel`` is ``display: flex; flex-direction:
     column; overflow-y: auto`` — designed to scroll on overflow. The
     hero had the default ``flex-shrink: 1`` and ``overflow: hidden``
     (kept around for the decorative ``::after`` blob). When total
     content exceeded the panel's bounded height, flexbox shrank the
     hero instead of letting the panel scroll, and ``overflow:hidden``
     silently clipped the ``h1`` + subtitle.

The fix (PR #221) pins a four-clause static-source contract on the
single ``.gb-tm-hero`` rule plus one anchor:

  1. ``flex-shrink: 0`` — refuse to be shrunk by flexbox.
  2. ``min-height: max-content`` — explicit floor so a future refactor
     can't re-introduce shrinking via a contradictory rule.
  3. Background declaration contains at least one ``rgba(...)`` stop
     with alpha ``>= 0.80`` — fences against the ``.42/.20`` regression
     and forces the card to be a real visible surface, not a glass
     pane that depends on ``backdrop-filter`` to be perceptible.
  4. Border is a hard-coded dark ``rgba(...)`` — NOT
     ``var(--surface-border)``. The token resolves to translucent white
     in light mode and provides no edge over ``#f5f5f7``; the regression
     pin demands a dark hairline instead.

Anchor (clause 5):
  ``[data-theme="dark"] .gb-tm-hero`` rule still exists — the premise
  this fix relies on is that dark-mode parity is provided by an
  opaque override. If the override is deleted, this test forces the
  author to either re-add it or update both fixes together.

This test pins each clause as a static-file assertion against the
template source. The behavior itself was verified end-to-end against
the live preview during PR #221 review (``preview_inspect`` before/after
at 440px iframe width: hero ``boundingBox.height`` went from 0 to
113.95px after the fix).

Pre-fix baseline: clauses 1, 2, 3, 4 all fail on ``origin/server@336d8cf``
— the rules don't exist before this commit. Clause 5 (the anchor)
passes both before and after; it's a premise check, not a behaviour
check.
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


def _block_for_selector(html: str, selector: str) -> str:
    """Return the body of the FIRST CSS rule whose selector matches.

    Comments are stripped first so a selector mentioned inside ``/* ... */``
    cannot trigger a false positive.
    """
    stripped = _CSS_COMMENT_RE.sub("", html)
    pattern = re.compile(
        r"(^|\n)\s*" + re.escape(selector) + r"\s*\{",
        re.MULTILINE,
    )
    m = pattern.search(stripped)
    assert m, f"selector {selector!r} not found in template"
    start = stripped.index("{", m.start()) + 1
    depth = 1
    for i in range(start, len(stripped)):
        c = stripped[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return stripped[start:i]
    raise AssertionError(f"unbalanced braces for selector {selector!r}")


# ── Clause 1: don't let flexbox squash the hero ────────────────────────


def test_hero_rule_pins_flex_shrink_zero():
    """``.gb-tm-hero`` must declare ``flex-shrink: 0``.

    The parent ``.gb-game-panel`` is a flex column with
    ``overflow-y: auto``. With the default ``flex-shrink: 1`` the hero
    is the child that loses height when total content exceeds the
    panel — and because the hero carries ``overflow: hidden`` (for its
    decorative ``::after`` blob), the squash clips the ``h1`` and
    subtitle silently. Pinning ``flex-shrink: 0`` keeps the hero at its
    natural height and lets the panel scroll, which is what
    ``overflow-y: auto`` was always intended to do.
    """
    block = _block_for_selector(_read(), ".gb-tm-hero")
    assert re.search(r"flex-shrink\s*:\s*0\s*;", block), (
        "Tile-Match regression: `.gb-tm-hero` no longer pins "
        "`flex-shrink: 0`. Inside the panel's flex column the hero will "
        "be shrunk by flexbox and its `overflow: hidden` will clip the "
        "h1 + subtitle — the exact bug PR #221 fixed."
    )


# ── Clause 2: explicit floor so a future rule can't re-introduce shrink ─


def test_hero_rule_pins_min_height_max_content():
    """``.gb-tm-hero`` must declare ``min-height: max-content``.

    Belt-and-braces alongside ``flex-shrink: 0``. If a future media
    query or override re-introduces ``flex-shrink: 1`` (or some browser
    interprets the parent constraints differently), the explicit
    ``min-height: max-content`` still forbids the card from collapsing
    below the size of its own content.
    """
    block = _block_for_selector(_read(), ".gb-tm-hero")
    assert re.search(r"min-height\s*:\s*max-content\s*;", block), (
        "Tile-Match regression: `.gb-tm-hero` no longer pins "
        "`min-height: max-content`. The card can be squeezed below its "
        "natural content height again by a flex parent that adds a "
        "height constraint."
    )


# ── Clause 3: surface is opaque enough to survive on a light bg ────────


def test_hero_background_has_opaque_rgba_stop():
    """The ``background`` declaration on ``.gb-tm-hero`` must contain at
    least one ``rgba(...)`` stop with alpha ``>= 0.80``.

    The pre-fix gradient was ``rgba(255,255,255,.42 -> .20)`` over the
    page's ``#f5f5f7`` background. Without ``backdrop-filter`` (older
    Android Chrome, embedded webviews, the builder preview iframe) the
    card had no contrast and read as floating text. This pin demands an
    opaque-enough surface so the card has visible substance regardless
    of ``backdrop-filter`` support.
    """
    block = _block_for_selector(_read(), ".gb-tm-hero")
    bg_match = re.search(
        r"background\s*:\s*([^;]+);",
        block,
    )
    assert bg_match, (
        "Tile-Match regression: `.gb-tm-hero` has no `background:` "
        "declaration — the card surface itself is missing."
    )
    declaration = bg_match.group(1)
    rgba_alphas = re.findall(
        r"rgba\s*\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*([0-9]*\.?[0-9]+)\s*\)",
        declaration,
    )
    assert rgba_alphas, (
        "Tile-Match regression: `.gb-tm-hero` background no longer uses "
        "any rgba(...) stops — the contrast-floor pin cannot be enforced. "
        f"declaration: {declaration!r}"
    )
    max_alpha = max(float(a) for a in rgba_alphas)
    assert max_alpha >= 0.80, (
        f"Tile-Match regression: `.gb-tm-hero` background dropped to "
        f"max alpha {max_alpha:.2f} (< 0.80). The pre-fix gradient was "
        f".42/.20 — anything below 0.80 risks the same invisible-card "
        f"bug when backdrop-filter degrades. declaration: {declaration!r}"
    )


# ── Clause 4: card edge is a dark hairline, not a white-on-white token ─


def test_hero_border_is_hard_coded_dark_rgba():
    """``.gb-tm-hero`` ``border:`` must be a hard-coded ``rgba(...)`` —
    NOT ``var(--surface-border)``.

    ``--surface-border`` resolves to ``rgba(255,255,255,.5)`` in light
    mode (see ``:root`` in the template). A white border on the
    page's near-white ``#f5f5f7`` is invisible — the card has no edge.
    The fix swapped to a dark hairline ``rgba(15,23,42,.10)``-style
    border so the card outline survives over white. Pin against the
    regression by forbidding the surface-border token here.
    """
    block = _block_for_selector(_read(), ".gb-tm-hero")
    border_match = re.search(r"border\s*:\s*([^;]+);", block)
    assert border_match, (
        "Tile-Match regression: `.gb-tm-hero` has no `border:` "
        "declaration. The card edge will not survive on a light bg."
    )
    declaration = border_match.group(1)
    assert "var(--surface-border)" not in declaration, (
        "Tile-Match regression: `.gb-tm-hero` border re-uses "
        "`var(--surface-border)`. In light mode that token resolves to "
        "`rgba(255,255,255,.5)` — a white border on near-white bg is "
        "invisible. PR #221 swapped this to a dark hairline rgba; the "
        f"swap was reverted. declaration: {declaration!r}"
    )
    assert re.search(
        r"rgba\s*\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*[0-9.]+\s*\)",
        declaration,
    ), (
        "Tile-Match regression: `.gb-tm-hero` border is no longer a "
        f"hard-coded rgba(...) — the dark hairline pin is gone. "
        f"declaration: {declaration!r}"
    )


# ── Clause 5 (anchor): dark-mode override still exists ─────────────────


def test_hero_dark_mode_override_anchor_still_exists():
    """Anchor: the ``[data-theme="dark"] .gb-tm-hero`` rule must exist.

    The light-mode fix is safe to ship un-touched in dark mode because
    a dark-theme override already paints the card with an opaque dark
    gradient. This anchor is a premise check — if the override is
    deleted, the next person editing the light-mode rule needs to
    re-add dark parity at the same time. Without this anchor a future
    PR could delete the dark rule silently and the contrast bug
    re-appears for dark-mode users only.
    """
    html = _read()
    stripped = _CSS_COMMENT_RE.sub("", html)
    pattern = re.compile(
        r'(^|\n)\s*\[data-theme="dark"\]\s+\.gb-tm-hero\s*\{',
        re.MULTILINE,
    )
    assert pattern.search(stripped), (
        "Tile-Match anchor failed: `[data-theme=\"dark\"] .gb-tm-hero` "
        "rule no longer exists. PR #221 leaves the dark-mode rule "
        "untouched on the premise that it's already opaque enough; if "
        "it's been deleted, dark-mode users will hit the same "
        "invisible-card bug. Restore the override or update both "
        "fixes together."
    )
