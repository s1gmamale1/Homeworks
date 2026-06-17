"""Memory-Sprint explainer reveal contract — regression guard.

Bug history (2026-05-13):
  ``msRenderQuestion`` wrote ``explainerEl.innerHTML = item.explain`` on
  every question render, but the ``.ms-question-explainer`` element had
  no visibility gate. The explanation rendered as plain prose the moment
  a question appeared — leaking the answer before the student picked an
  option. Auto-advance had no state machine, so flow between questions
  felt stuck or premature.

The fix (PR #215) wraps the explainer in a five-part contract:
  1. ``.ms-question-explainer`` defaults to ``opacity: 0`` (hidden).
  2. A ``.ms-question-explainer.is-shown`` rule lifts it (``opacity: 1``)
     — visibility is class-gated, never property-toggled inline.
  3. ``msRenderQuestion`` calls ``msClearAdvanceTimers()`` and removes
     ``.is-shown`` BEFORE writing ``innerHTML = item.explain`` — order is
     load-bearing: any leaked state from the prior question is gone
     before the new explanation enters the DOM.
  4. ``msClearAdvanceTimers`` removes ALL FOUR capture-phase document
     listeners it adds (``pointerdown``, ``click``, ``touchstart``,
     ``keydown``). Forgetting one keeps a stale listener bound across
     questions and can advance prematurely.
  5. ``msCollapseToLoader`` defensively clears the timers + the
     ``.is-shown`` class so any external advance path (e.g. sprint
     restart, finish) cannot leave a dangling listener.

This test pins each clause as a static-file assertion. The behavior
itself was verified end-to-end against the live preview during PR #215
review; see the PR body for those traces.

Pre-fix baseline: tests 1, 2, 3, 4, 5 all fail on ``origin/server`` —
the rules / functions don't exist before this commit.
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

    Selector matching uses a comment-stripped copy of the template so
    selector text inside ``/* ... */`` cannot trigger a false positive.
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


def _function_body(html: str, name: str) -> str:
    """Return the body (between the outer braces) of a top-level
    ``function name(...) { ... }`` declaration. Used to assert ordering
    of statements inside specific helpers."""
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


# ── Clause 1: hidden by default ────────────────────────────────────────


def test_explainer_default_opacity_is_zero():
    """``.ms-question-explainer`` must default to ``opacity: 0``.

    Without this, ``msRenderQuestion`` writing the explanation text into
    ``innerHTML`` leaks the answer the moment a question renders. The
    visibility gate has to live in the static rule, not on a JS-toggled
    inline style, so reload / first-paint never has a window where the
    text is visible.
    """
    html = _read()
    # Block from the dedicated rule (not the shared subtitle+explainer
    # font/colour rule above it). Walk every block matching the selector
    # and find the one that declares opacity.
    stripped = _CSS_COMMENT_RE.sub("", html)
    rule_re = re.compile(
        r"(^|\n)\s*\.ms-question-explainer\s*\{([^}]*)\}",
        re.MULTILINE,
    )
    bodies = [m.group(2) for m in rule_re.finditer(stripped)]
    assert bodies, "no .ms-question-explainer rule found"
    has_opacity_zero = any(re.search(r"opacity\s*:\s*0\s*;", b) for b in bodies)
    assert has_opacity_zero, (
        "Memory-Sprint regression: `.ms-question-explainer` no longer "
        "defaults to `opacity: 0`. The explanation will be visible the "
        "moment a question renders, leaking the answer before the "
        "student picks an option."
    )


def test_explainer_default_has_pointer_events_none():
    """Hidden state must also disable pointer events.

    If a future refactor swaps the hidden state to ``visibility: hidden``
    or relies purely on opacity, leftover pointer-events on the invisible
    card could swallow the answer-button click underneath. Pin
    ``pointer-events: none`` on the base rule.
    """
    html = _read()
    stripped = _CSS_COMMENT_RE.sub("", html)
    rule_re = re.compile(
        r"(^|\n)\s*\.ms-question-explainer\s*\{([^}]*)\}",
        re.MULTILINE,
    )
    bodies = [m.group(2) for m in rule_re.finditer(stripped)]
    has_pe_none = any(
        re.search(r"pointer-events\s*:\s*none\s*;", b) for b in bodies
    )
    assert has_pe_none, (
        "Memory-Sprint regression: `.ms-question-explainer` no longer "
        "sets `pointer-events: none` in its hidden state — an invisible "
        "card can still swallow taps meant for the answer buttons."
    )


# ── Clause 2: reveal gated on the .is-shown class ──────────────────────


def test_is_shown_class_lifts_opacity():
    """A ``.ms-question-explainer.is-shown`` rule must exist and set
    ``opacity: 1``. This is the single visibility gate — the JS toggles
    only the class, never inline opacity, so the transition can run.
    """
    html = _read()
    block = _block_for_selector(html, ".ms-question-explainer.is-shown")
    assert re.search(r"opacity\s*:\s*1\s*;", block), (
        "Memory-Sprint regression: `.ms-question-explainer.is-shown` no "
        "longer sets `opacity: 1`. The class is the only thing that "
        "reveals the explanation; removing this re-hides it forever."
    )


def test_is_shown_class_lifts_transform():
    """The reveal animation slides the card up from translateY(8px) to 0.
    The hidden state declares the offset; the ``.is-shown`` state pins
    ``translateY(0)`` so the transition has a target.
    """
    html = _read()
    block = _block_for_selector(html, ".ms-question-explainer.is-shown")
    assert re.search(r"transform\s*:\s*translateY\(\s*0\s*\)\s*;", block), (
        "Memory-Sprint regression: `.ms-question-explainer.is-shown` no "
        "longer pins translateY(0) — the slide-up reveal will jump or "
        "stay offset."
    )


# ── Clause 3: render-time ordering ─────────────────────────────────────


def test_msRenderQuestion_clears_state_before_writing_explain():
    """``msRenderQuestion`` must clear timers and strip ``.is-shown``
    BEFORE assigning ``innerHTML = item.explain``. Order is load-bearing:

    - If ``innerHTML`` runs first, the previous question's ``.is-shown``
      can still be present, briefly painting the new explanation
      visible until the class strip runs on the next microtask.
    - If ``msClearAdvanceTimers()`` is missing, a stale advance timer or
      skip listener from the previous answer can fire against the new
      question (advancing past it on its first paint).

    This test parses ``msRenderQuestion`` and asserts the relative
    position of three substrings.
    """
    html = _read()
    body = _function_body(html, "msRenderQuestion")
    # Anchor positions
    pos_clear = body.find("msClearAdvanceTimers()")
    pos_strip = body.find("classList.remove('is-shown')")
    # The innerHTML assignment we care about is the explainer one.
    # Find ``explainerEl.innerHTML`` (or matching) assignment.
    inner_match = re.search(
        r"explainerEl\.innerHTML\s*=\s*item\.explain",
        body,
    )
    assert pos_clear != -1, (
        "Memory-Sprint regression: `msRenderQuestion` no longer calls "
        "`msClearAdvanceTimers()`. Stale timers/listeners from the "
        "previous answer can advance the new question prematurely."
    )
    assert pos_strip != -1, (
        "Memory-Sprint regression: `msRenderQuestion` no longer strips "
        "`.is-shown` from the explainer. The previous question's "
        "revealed state will paint over the new question on first frame."
    )
    assert inner_match, (
        "Memory-Sprint anchor: `explainerEl.innerHTML = item.explain` "
        "assignment is gone from `msRenderQuestion`. The reveal "
        "contract was tied to this specific write — re-audit before "
        "weakening the test."
    )
    pos_inner = inner_match.start()
    assert pos_clear < pos_inner, (
        "Memory-Sprint regression: `msClearAdvanceTimers()` must run "
        "BEFORE `explainerEl.innerHTML = item.explain`. Reordering risks "
        "the previous answer's advance timer firing against the new "
        "question's first paint."
    )
    assert pos_strip < pos_inner, (
        "Memory-Sprint regression: `.is-shown` must be stripped BEFORE "
        "writing the new explanation text. Reordering causes a one-frame "
        "flash of the new answer the moment the question loads."
    )


# ── Clause 4: skip-listener bookkeeping (all four removed) ─────────────


def test_msClearAdvanceTimers_removes_all_four_listeners():
    """Every listener bound by the reveal handler must be removed in
    ``msClearAdvanceTimers``. Missing one keeps a stale capture-phase
    handler on ``document`` after the sprint advances — a later click
    anywhere in the homework runtime can fire ``advanceNow()`` against
    a freed question and crash or jump state.

    Pinned events: ``pointerdown``, ``click``, ``touchstart``, ``keydown``.
    """
    html = _read()
    body = _function_body(html, "msClearAdvanceTimers")
    for evt in ("pointerdown", "click", "touchstart", "keydown"):
        pattern = re.compile(
            r"removeEventListener\(\s*['\"]" + re.escape(evt) + r"['\"]\s*,\s*msState\.skipHandler",
        )
        assert pattern.search(body), (
            f"Memory-Sprint regression: `msClearAdvanceTimers` no longer "
            f"removes the `{evt}` capture-phase listener it bound on "
            f"reveal. A stale handler on document can fire `advanceNow()` "
            f"against a freed question state."
        )


def test_skipHandler_binds_all_four_listeners_in_capture_phase():
    """The reveal block must bind the SAME four events the cleanup
    removes — anything bound but not removed is a leak; anything removed
    but never bound is dead code.

    Capture-phase (``true`` as the third arg) is also pinned: bubbling
    answer-button clicks inside ``#ms-question-box`` cannot otherwise
    skip the wait, because they're stopped before reaching ``document``.
    """
    html = _read()
    # Locate the msHandleAnswer body to scope the search — bind site is here.
    handler_body = _function_body(html, "msHandleAnswer")
    for evt in ("pointerdown", "click", "touchstart", "keydown"):
        # Allow whitespace + optional skipHandler argument; require capture: true.
        pattern = re.compile(
            r"addEventListener\(\s*['\"]" + re.escape(evt) +
            r"['\"]\s*,\s*msState\.skipHandler\s*,\s*true\s*\)",
        )
        assert pattern.search(handler_body), (
            f"Memory-Sprint regression: `msHandleAnswer` no longer binds "
            f"a capture-phase `{evt}` listener via msState.skipHandler. "
            f"Skip-anywhere coverage is incomplete."
        )


# ── Clause 5: defensive cleanup in msCollapseToLoader ──────────────────


def test_msCollapseToLoader_clears_timers_and_strips_is_shown():
    """``msCollapseToLoader`` is reachable from auto-advance, click-skip,
    AND any future external advance path (sprint restart, finish, error
    recovery). It must defensively clear the same state ``msRenderQuestion``
    clears, so no path can leave a dangling capture-phase listener bound
    on document or a stale .is-shown class on the explainer.
    """
    html = _read()
    body = _function_body(html, "msCollapseToLoader")
    assert "msClearAdvanceTimers()" in body, (
        "Memory-Sprint regression: `msCollapseToLoader` no longer calls "
        "`msClearAdvanceTimers()`. External advance paths can leave a "
        "capture-phase listener bound to document."
    )
    assert re.search(
        r"classList\.remove\(\s*['\"]is-shown['\"]\s*\)", body
    ), (
        "Memory-Sprint regression: `msCollapseToLoader` no longer strips "
        "`.is-shown`. A stale revealed state can carry over to the next "
        "question's first frame."
    )


# ── Clause 6: state struct holds the three slots ───────────────────────


def test_msState_declares_reveal_advance_and_skip_slots():
    """The state machine relies on three named slots on ``msState`` —
    ``revealTimer``, ``advanceTimer``, ``skipHandler``. If a future
    refactor renames or drops one, the cleanup helper will silently miss
    it (the helper only clears what it knows about), re-opening the
    listener-leak class of bugs.
    """
    html = _read()
    # Find the msState object literal declaration.
    m = re.search(r"const\s+msState\s*=\s*\{", html)
    assert m, "msState declaration not found"
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
    decl = html[start:end]
    for slot in ("revealTimer", "advanceTimer", "skipHandler"):
        assert re.search(rf"\b{slot}\b", decl), (
            f"Memory-Sprint regression: `msState` no longer declares "
            f"`{slot}`. The reveal/skip state machine depends on this "
            f"slot — silently dropping it leaks listeners and timers."
        )
