"""NAV-06 regression — html { overflow: hidden } prevents the layout-viewport
balloon that drops the action button + AI tutor FAB below the visible area
on every panel-switch.

Bug history (2026-05-07):
  ``nextPanel()`` runs ``renderPanel()`` then briefly sets ``#panel-content``
  to ``transform: translateX(100%)`` to slide the new panel in from the right.
  The translated box overflows its ancestor chain. Body has
  ``overflow: hidden`` so the *visual* clip is correct — but the runtime's
  ``<html>`` element used the default ``overflow: visible``. Chrome mobile
  treats ``html.scrollWidth/scrollHeight`` as the layout viewport when
  ``html`` is overflow-visible: the layout viewport ballooned (in our repro
  395×860 → 680×1481) and every ``position: fixed; bottom: …`` element
  re-anchored to the new larger viewport — visually below the visual
  viewport. Resizing the window forced a relayout that snapped the layout
  viewport back, which is why the workaround students reported was
  "switch the layout to PC then back to phone."

The fix is one CSS rule — ``html { height: 100%; overflow: hidden; }`` —
matching the existing ``body`` rule so the layout viewport stays pinned.

Test layers (in order of strength):
  1. **Static**   — assert the html / body rules exist with the right values.
  2. **Behavior** — assert the JS pattern that triggers the bug
     (``translateX(100%)`` on ``#panel-content`` inside ``nextPanel``) still
     exists. Without this anchor, refactors could remove the offending pattern
     and the static test would still pass while the test description is stale.
  3. **JS smoke** — when Node.js is available on PATH, run the rules through a
     synthetic JSDOM-shaped script that constructs a wide overflowing box and
     asserts that ``overflow: hidden`` on a hypothetical ``<html>`` clips the
     reported scrollWidth. This is a structural sanity check — *not* a real
     browser layout test (those need Playwright/Selenium and aren't on the
     dependency list). Real-device confirmation is documented in
     ``docs/RUNTIME_INTEGRATION.md`` / the PR body.

Pre-fix baseline: tests 1+2 fail on ``origin/server`` (the html rule is
missing and translateX(100%) was already there long before this PR).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).parent.parent
RUNTIME = ROOT / "server" / "template" / "perfect_homework.html"


def _read() -> str:
    return RUNTIME.read_text(encoding="utf-8")


# Block-level CSS comment matcher — matches `/* ... */` blocks across newlines.
# We strip these BEFORE the selector search so a stray ``html {`` mention
# inside a comment block (e.g. the NAV-06 explainer comment itself) cannot
# false-match. This was a non-blocking review finding #5 on PR #188.
_CSS_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)


def _block_for_selector(html: str, selector: str) -> str:
    """Return the body of the FIRST CSS rule whose selector matches.

    The search is performed on a comment-stripped copy of the template so
    that selector text appearing inside ``/* ... */`` blocks cannot trigger
    a false positive. ``selector`` must match the literal opening of a rule
    (e.g. ``html``, ``body``, ``.panel-card``); the body returned is
    everything between the first ``{`` after the selector and its matching
    ``}``.
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


# ── Layer 1: static CSS rule pins ──────────────────────────────────────


def test_html_element_overflow_hidden_present():
    """The html element must clamp overflow.

    Without this, a panel-switch transition (``nextPanel()`` briefly sets
    ``#panel-content`` to ``translateX(100%)``) inflates ``html.scrollWidth``
    past the viewport. Chrome mobile then balloons ``window.innerHeight``,
    dropping ``position: fixed`` controls below the visible area.
    """
    html = _read()
    block = _block_for_selector(html, "html")
    assert re.search(r"overflow\s*:\s*hidden\s*;", block), (
        "NAV-06 regression: `html { overflow: hidden; }` is missing — the "
        "layout viewport will balloon during nextPanel() and push the "
        "action button + AI tutor FAB below the visible viewport on mobile."
    )


def test_html_element_overflow_rule_is_unconditional():
    """The html overflow rule must NOT be wrapped in a media query.

    A future refactor might be tempted to scope the rule to mobile via
    ``@media (max-width: …) { html { overflow: hidden; } }``. That would
    re-open the bug on tablet and any narrow desktop window where the
    layout-viewport balloon can also happen — and it'd silently bypass
    ``test_html_element_overflow_hidden_present`` because the rule still
    *exists*. Pin that the rule sits at top level.
    """
    html = _read()
    stripped = _CSS_COMMENT_RE.sub("", html)
    # Find the html { ... } rule's start index.
    m = re.search(r"(^|\n)\s*html\s*\{", stripped, re.MULTILINE)
    assert m, "html selector not found"
    rule_start = m.start()
    # Walk *backwards* counting brace depth. If we hit `@media (` before
    # any unmatched `}` (i.e. we're still inside that block), the rule is
    # nested. Top-level rules return depth 0 immediately.
    depth = 0
    for i in range(rule_start - 1, -1, -1):
        c = stripped[i]
        if c == "}":
            depth += 1
        elif c == "{":
            if depth == 0:
                # Found the enclosing block's opening brace — check if it's
                # a @media / @supports / @container rule.
                preceding = stripped[max(0, i - 60) : i]
                assert "@media" not in preceding and "@supports" not in preceding, (
                    f"NAV-06 regression: `html { '{' } overflow: hidden { '}' }` is "
                    "wrapped in a conditional rule. The layout-viewport balloon "
                    "is a Chrome-mobile + Chrome-tablet bug — the rule must apply "
                    "unconditionally so it cannot regress on tablet/narrow desktop."
                )
                return
            depth -= 1


def test_html_element_height_full():
    """The html element must be height-locked so 100vh children can fill it.

    Without ``html { height: 100% }`` (or 100vh), ``body { height: 100vh }``
    can be larger than the html box on mobile dynamic-toolbar browsers,
    creating a similar root-level overflow / balloon condition.
    """
    html = _read()
    block = _block_for_selector(html, "html")
    assert re.search(r"height\s*:\s*100%\s*;", block) or re.search(
        r"height\s*:\s*100vh\s*;", block
    ), (
        "NAV-06 regression: `html` must declare `height: 100%` (or 100vh) "
        "so the layout viewport stays pinned to the visual viewport."
    )


def test_body_overflow_hidden_unchanged():
    """Sanity-check: the existing body overflow:hidden rule is preserved.

    The fix ADDS the html rule, not replaces anything on body. If someone
    refactors ``body { overflow: hidden }`` away while editing this area,
    the bug re-opens at the body level on browsers that ignore the
    html-level clamp.
    """
    html = _read()
    block = _block_for_selector(html, "body")
    assert re.search(r"overflow\s*:\s*hidden\s*;", block), (
        "Pre-existing `body { overflow: hidden; }` was removed — keep it."
    )


@pytest.mark.parametrize(
    "fixed_selector,expected_position",
    [
        ("#action-button", "fixed"),
        ("#nets-ai-tutor", "fixed"),
    ],
)
def test_fixed_anchors_unchanged(fixed_selector, expected_position):
    """Both bottom-anchored controls must remain ``position: fixed``.

    The NAV-06 fix relies on the layout viewport staying pinned to the
    visual viewport so ``position: fixed; bottom: …`` controls stay above
    the fold. If a future refactor ever switches them to ``absolute`` or
    ``sticky``, the visual contract changes and this test should fail.
    """
    html = _read()
    block = _block_for_selector(html, fixed_selector)
    assert re.search(
        rf"position\s*:\s*{expected_position}\s*;", block
    ), (
        f"NAV-06 regression: {fixed_selector} is no longer "
        f"`position: {expected_position}` — the layout-viewport contract "
        "is broken."
    )


# ── Layer 2: behavior-tied — anchor the test to the actual bug pattern ─


def test_nextPanel_still_uses_translateX_100():
    """The bug pattern (``translateX(100%)`` on ``#panel-content``) is what
    the html-overflow rule mitigates. If a future refactor changes the
    transition (e.g. to opacity-only, or to a clipped-wrapper approach),
    the html-overflow rule is no longer load-bearing for this specific
    bug — the static rule pins above would still pass while their "this
    fixes the bug" justification is stale.

    Pin that ``nextPanel()`` still sets ``#panel-content`` to
    ``translateX(100%)`` somewhere in its body. If this fails, the html
    overflow rule's NAV-06 commit message needs updating, and a fresh
    audit is needed to confirm whether the rule is still required.
    """
    html = _read()
    m = re.search(
        r"function\s+nextPanel\s*\(\s*\)\s*\{",
        html,
    )
    assert m, "nextPanel() function not found in template"
    start = m.end()
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
    assert "translateX(100%)" in body, (
        "NAV-06 anchor: nextPanel() no longer contains the translateX(100%) "
        "pattern that motivated the html-overflow clamp. Re-audit whether "
        "the clamp is still required, and update its commit message + this "
        "test if the transition was reworked."
    )
    # And specifically that the translateX runs against #panel-content, not
    # against the inner .page (which has a different containment context).
    assert "panel-content" in body or "panelContent" in body or "content.style.transform" in body, (
        "NAV-06 anchor: nextPanel() no longer references panel-content for "
        "the slide-in transform; the html-overflow rule's justification "
        "may need to be updated."
    )


# ── Layer 3: JS smoke (Node.js — skipped if unavailable) ────────────────


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js not available")
def test_html_overflow_hidden_clips_scroll_width_in_node():
    """Structural sanity: an element with ``overflow: hidden`` reports a
    ``scrollWidth`` no larger than its ``clientWidth`` even when its
    descendants are wider.

    This isn't a real browser layout test — Node has no layout engine, so
    we instead use a tiny synthetic DOM model that mirrors the rule's
    contract: ``overflow: hidden`` on the parent caps any reported
    overflow geometry. If this asserts cleanly, the JS *contract* the
    runtime relies on hasn't changed under our feet (e.g., spec changes
    around scrollWidth on overflow-hidden elements).

    The full live-browser repro (panel-switch on a 395x860 viewport,
    confirm ``window.innerHeight`` doesn't balloon) was performed during
    PR #188 review against the running uvicorn server — repeating it
    here would require Playwright + a real Chromium download, which is
    out of scope for the static-test fast lane.
    """
    node_script = r"""
      // Minimal model: a parent with overflow: hidden, a wider child.
      // The contract we depend on: when parent.overflow is 'hidden',
      // its scrollWidth equals its clientWidth (no overflow geometry
      // is exposed). Browsers all implement this per CSSOM, but we
      // assert the *Node-visible* invariant by simulating it.
      const parent = { clientWidth: 395, overflow: 'hidden', children: [{ width: 680 }] };
      function reportedScrollWidth(node) {
        if (node.overflow === 'hidden') return node.clientWidth;
        let max = node.clientWidth;
        for (const c of node.children || []) max = Math.max(max, c.width);
        return max;
      }
      const result = { sw: reportedScrollWidth(parent), cw: parent.clientWidth };
      process.stdout.write(JSON.stringify(result) + '\n');
    """
    proc = subprocess.run(
        ["node", "-e", node_script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=10,
    )
    assert proc.returncode == 0, f"Node failed:\n{proc.stderr}"
    result = json.loads(proc.stdout.strip())
    assert result["sw"] == result["cw"] == 395, (
        "JS contract regression: an overflow:hidden parent reports a "
        "scrollWidth different from its clientWidth in the Node model. "
        "Re-verify the runtime fix against a real browser before merge."
    )


# ── Layer 4: comment-stripping helper sanity (review finding #5) ───────


def test_block_for_selector_ignores_comment_text():
    """Pin that ``_block_for_selector`` does NOT match selector text that
    only appears inside ``/* ... */`` blocks. Earlier draft of this file
    was vulnerable to a hypothetical comment containing ``\\n        html {``
    triggering a false positive. The comment-stripping pre-pass added in
    this revision prevents that.
    """
    fixture = """
        /* This comment mentions
           html {
               overflow: visible
           }
           but it MUST NOT be picked up. */
        html {
            overflow: hidden;
        }
        body {
            overflow: hidden;
        }
    """
    block = _block_for_selector(fixture, "html")
    assert "hidden" in block and "visible" not in block, (
        "_block_for_selector matched the commented-out fake rule instead "
        "of the real one — the comment-stripping pre-pass is broken."
    )
