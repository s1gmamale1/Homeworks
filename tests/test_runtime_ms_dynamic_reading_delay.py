"""Memory-Sprint dynamic reading-delay contract — regression guard.

Background (2026-05-14):
  The Memory-Sprint explainer reveal flow (PR #215) auto-advanced
  after a flat 4200 ms hard-code. A two-word explanation got the same
  4.2 s as a sixty-word recap — students had to either rush the long
  ones (or tap to skip) or wait through dead time on the short ones.

The fix replaces the literal with ``msReadingDelayMs(item.explain)``
which scales the wait with how long the explanation actually takes to
read at 220 wpm + small pauses for commas + slightly bigger pauses for
sentence terminators + a 3 s "saw it land" buffer. The full formula:

    seconds = (wordCount / 220) * 60
            + commas  * 0.15
            + periods * 0.3
            + 3

… clamped to [3000 ms, 15000 ms] so a one-word hint still gets the
base buffer and an unreasonably long string can't soft-lock the UI
without user input (click-to-skip is still bound either way).

This test pins the contract as static-file assertions, same shape as
``tests/test_runtime_ms_explainer_reveal.py``:

  1. ``msReadingDelayMs`` helper exists with the right signature.
  2. The four magic numbers from the formula (``220``, ``0.15``,
     ``0.3``, ``+ 3``) all appear inside the helper body.
  3. The helper strips HTML before counting (the explainer uses
     ``innerHTML`` for inline images / bold / SVGs).
  4. Clamp boundaries (3000 / 15000) are honoured.
  5. ``msHandleAnswer`` no longer passes the literal ``4200`` to
     ``setTimeout(advanceNow, …)`` and instead calls
     ``msReadingDelayMs(item.explain)`` on the explain branch.

Pre-fix baseline (PR #215 era): test 1, 2, 3, 4, 5 all fail — the
helper didn't exist and ``msHandleAnswer`` used the hard-coded literal.
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


def _function_body(html: str, name: str) -> str:
    """Return the body of a top-level ``function name(...) { ... }``
    declaration — mirrors the helper from
    ``tests/test_runtime_ms_explainer_reveal.py``."""
    pattern = re.compile(
        r"function\s+" + re.escape(name) + r"\s*\([^)]*\)\s*\{",
    )
    m = pattern.search(html)
    assert m, f"function {name}() not found in template"
    start = m.end()
    depth = 1
    for i in range(start, len(html)):
        c = html[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return html[start:i]
    raise AssertionError(f"unbalanced braces in function {name}()")


# ── Clause 1: the helper exists ────────────────────────────────────────


def test_msReadingDelayMs_helper_exists():
    """A ``function msReadingDelayMs(...)`` declaration must exist.
    The auto-advance flow relies on calling it for every question;
    removing it without restoring the caller is a regression.
    """
    html = _read()
    assert re.search(r"function\s+msReadingDelayMs\s*\(", html), (
        "Dynamic-wait regression: `msReadingDelayMs` helper is gone "
        "from the template. Memory Sprint auto-advance has no way to "
        "scale its wait with the explanation length and either:\n"
        "  (a) reverted to the flat 4200 ms hard-code, OR\n"
        "  (b) is calling an undefined function and throwing at runtime."
    )


# ── Clause 2: the four formula constants are present ───────────────────


def test_msReadingDelayMs_uses_the_four_formula_constants():
    """The wpm rate (220), comma pause (0.15), period pause (0.3),
    and base buffer (3) are all load-bearing. If any one is silently
    edited (e.g. someone halves the buffer to 1.5 s), the auto-advance
    pacing changes for every student. Pin each literal so the change
    has to be deliberate.
    """
    html = _read()
    body = _function_body(html, "msReadingDelayMs")
    # 220 wpm rate (used as `/ 220`).
    assert re.search(r"/\s*220\b", body), (
        "Dynamic-wait regression: `msReadingDelayMs` no longer divides "
        "wordCount by 220 (the silent-reading wpm constant). Editing "
        "the rate changes every student's pacing — make sure it's "
        "deliberate and update this test if so."
    )
    # 0.15 s per comma.
    assert re.search(r"\*\s*0\.15\b", body), (
        "Dynamic-wait regression: `msReadingDelayMs` no longer adds "
        "0.15 s per comma. Reading-pause math degraded — long sentences "
        "now auto-advance before the student can finish them."
    )
    # 0.3 s per sentence terminator.
    assert re.search(r"\*\s*0\.3\b", body), (
        "Dynamic-wait regression: `msReadingDelayMs` no longer adds "
        "0.3 s per sentence terminator. Multi-sentence explanations "
        "lose their natural between-sentence pause budget."
    )
    # +3 s base buffer.
    assert re.search(r"\+\s*3\b", body), (
        "Dynamic-wait regression: `msReadingDelayMs` no longer adds "
        "the 3 s base buffer. Even a one-word explanation needs time "
        "for the student to register the verdict before advancing."
    )


# ── Clause 3: HTML stripping before word count ─────────────────────────


def test_msReadingDelayMs_strips_html_before_counting():
    """The explainer uses ``innerHTML`` (so explain may contain inline
    ``<img>`` / ``<b>`` / ``<svg>`` markup). Counting tags as words would
    inflate the delay for image-heavy explanations and undercount real
    word density. Pin the HTML-stripping regex inside the helper.
    """
    html = _read()
    body = _function_body(html, "msReadingDelayMs")
    # Look for a `replace(/<[^>]*>/...` or `replace(/<.*?>/...` pattern.
    assert re.search(r"replace\(\s*/<[^/]*?>/", body) or re.search(
        r"replace\(\s*/<.*?>/", body
    ), (
        "Dynamic-wait regression: `msReadingDelayMs` no longer strips "
        "HTML tags from `rawHtml` before counting words. An explain "
        "string like `<img src=foo>` would count `<img`, `src=foo>` as "
        "words, inflating the wait."
    )


# ── Clause 4: clamp boundaries ─────────────────────────────────────────


def test_msReadingDelayMs_clamps_to_safe_bounds():
    """The helper must clamp to a sensible range:
      - Lower bound (~3000 ms) so a one-word hint still gets the base
        buffer the student needs to register the verdict.
      - Upper bound (~15000 ms) so an unreasonably long string can't
        soft-lock the UI without user input — click-to-skip is still
        bound, but the auto-advance should never be longer than a
        reasonable patience budget.

    Both literals must appear inside the helper body.
    """
    html = _read()
    body = _function_body(html, "msReadingDelayMs")
    assert re.search(r"\b3000\b", body), (
        "Dynamic-wait regression: lower clamp (~3000 ms) is missing — "
        "a one-word explanation could now auto-advance in <1 s, "
        "stealing the verdict-recognition beat from the student."
    )
    assert re.search(r"\b15000\b", body), (
        "Dynamic-wait regression: upper clamp (~15000 ms) is missing — "
        "an unreasonably long explain string could now hold the UI for "
        "30+ seconds with no advance, masking a stuck-state bug."
    )


# ── Clause 5: caller wires it through ──────────────────────────────────


def test_msHandleAnswer_uses_the_dynamic_delay_not_the_literal_4200():
    """The auto-advance ``setTimeout(advanceNow, …)`` must consume the
    dynamic delay, NOT the old flat ``4200`` literal. Pinning both
    halves prevents a partial revert (helper still exists but the
    caller falls back to the literal).
    """
    html = _read()
    body = _function_body(html, "msHandleAnswer")
    # The dynamic call must appear on the explain branch.
    assert re.search(
        r"setTimeout\s*\(\s*advanceNow\s*,\s*msReadingDelayMs\(",
        body,
    ), (
        "Dynamic-wait regression: `msHandleAnswer` no longer calls "
        "`setTimeout(advanceNow, msReadingDelayMs(...))` on the explain "
        "branch. The auto-advance delay either reverted to a literal "
        "or is reading from somewhere else that won't scale with text."
    )
    # And the flat 4200 must NOT be present as a setTimeout delay
    # anywhere in this handler (it lived in exactly one place before).
    assert not re.search(
        r"setTimeout\s*\(\s*advanceNow\s*,\s*4200\b", body
    ), (
        "Dynamic-wait regression: `msHandleAnswer` still passes the "
        "old flat 4200 ms literal to `setTimeout(advanceNow, ...)`. "
        "The dynamic-delay helper was added but the caller wasn't "
        "switched over — the old behaviour leaked back in."
    )


# ── Bonus: the 900 ms no-explain fallback is preserved ─────────────────


def test_msHandleAnswer_no_explain_branch_still_uses_900ms():
    """When ``item.explain`` is empty/whitespace, there's nothing for
    the dynamic helper to time — the flow skips the reveal beat and
    advances on a 900 ms collapse. That path predates the dynamic
    delay; this test pins that it's still present and not accidentally
    rewritten to call the helper (which would clamp up to 3000 ms even
    for questions with no explanation at all).
    """
    html = _read()
    body = _function_body(html, "msHandleAnswer")
    assert re.search(
        r"setTimeout\s*\(\s*advanceNow\s*,\s*900\b", body
    ), (
        "Dynamic-wait regression: the no-explain fast-path "
        "`setTimeout(advanceNow, 900)` is gone from `msHandleAnswer`. "
        "Questions without an explanation will either hang or get the "
        "wrong floor delay from the dynamic helper's 3000 ms clamp."
    )
