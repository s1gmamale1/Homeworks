"""Regression tests for FE-3 DOM markers — closes the TODO from PR #197.

Background
----------
PR #197 (FE polish) shipped the ``window.NETS_STATE`` mirror but left an
explicit TODO in ``syncNetsState``:

    // DOM markers are wired (TODO(FE-3): add data-nets-active /
    // data-question-id / data-subphase to each phase renderer's
    // active question wrapper).

``runtime.js#collectRuntimeContext`` (PR #192) prefers the
``[data-nets-active="true"]`` DOM marker over ``window.NETS_STATE``;
without it, the collector scopes ``screen_context`` to whatever the
``document.activeElement`` happens to be — which is often ``<body>``
between phase transitions and pulls in content from the wrong screen.

This file pins the FE-3 closeout: the active ``.screen`` wrapper gets
the marker triplet whenever ``syncNetsState`` runs, and stale markers
are removed before the new one is set.

What this pins
--------------
1. ``syncNetsState`` calls ``setAttribute('data-nets-active', 'true')``.
2. Stale ``[data-nets-active="true"]`` markers are cleared via
   ``removeAttribute('data-nets-active')`` BEFORE the new one is set
   (so the collector never sees two active wrappers).
3. ``syncNetsState`` writes ``data-question-id`` and ``data-subphase``
   on the same wrapper.
4. The wrapper targeted is ``.screen.active`` (single phase root —
   prevents screen_context cross-contamination between hidden screens).
5. The ``window.NETS_STATE`` mirror is still updated (PR #197 contract
   not regressed).

Companion to:
- tests/test_runtime_fe_foundation.py — submitRuntimeAnswer / bridge URLs
- tests/test_runtime_fe4_screen_context.py — collector context window
"""
from __future__ import annotations

import os
import re

import pytest


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def perfect_homework_html() -> str:
    path = os.path.join(_repo_root(), "server", "template", "perfect_homework.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _sync_nets_state_body(html: str) -> str:
    """Return the body of ``function syncNetsState()`` by walking matched
    braces. Pinning the body — not just the file — means tests catch
    the case where someone defines the markers but never inside the
    helper that's actually called on phase change.
    """
    pat = re.compile(r"function\s+syncNetsState\s*\(\s*\)\s*\{")
    m = pat.search(html)
    assert m, "syncNetsState() helper not found in perfect_homework.html"
    start = m.end()
    depth = 1
    i = start
    while i < len(html) and depth > 0:
        c = html[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    return html[start:i]


# ---------------------------------------------------------------------------
# 1. data-nets-active marker is written
# ---------------------------------------------------------------------------


def test_sync_nets_state_sets_data_nets_active(perfect_homework_html: str):
    body = _sync_nets_state_body(perfect_homework_html)
    assert "setAttribute('data-nets-active', 'true')" in body, (
        "syncNetsState must call setAttribute('data-nets-active', 'true') "
        "on the currently active screen so collectRuntimeContext picks it up "
        "instead of falling back to document.activeElement (which is often "
        "<body> between phase transitions)."
    )


# ---------------------------------------------------------------------------
# 2. Stale markers are cleared first (collector must never see two)
# ---------------------------------------------------------------------------


def test_sync_nets_state_clears_stale_markers(perfect_homework_html: str):
    body = _sync_nets_state_body(perfect_homework_html)
    # The cleanup must use a real DOM query, not just be referenced in a comment.
    assert "[data-nets-active=\"true\"]" in body, (
        "syncNetsState must query for [data-nets-active=\"true\"] before "
        "tagging a new node so a stale marker from the previous phase is "
        "removed first."
    )
    assert "removeAttribute('data-nets-active')" in body, (
        "syncNetsState must call removeAttribute('data-nets-active') on the "
        "previously tagged node — collectRuntimeContext picks the FIRST "
        "matching node, and a stale marker would shadow the live one."
    )
    # Cleanup must precede the setAttribute call; otherwise the just-tagged
    # node gets stripped immediately.
    cleanup_idx = body.find("removeAttribute('data-nets-active')")
    set_idx = body.find("setAttribute('data-nets-active', 'true')")
    assert 0 <= cleanup_idx < set_idx, (
        "removeAttribute('data-nets-active') must run BEFORE "
        "setAttribute('data-nets-active', 'true') — otherwise the new "
        "marker gets wiped immediately."
    )


# ---------------------------------------------------------------------------
# 3. data-question-id and data-subphase are written on the same wrapper
# ---------------------------------------------------------------------------


def test_sync_nets_state_writes_question_and_subphase_attrs(perfect_homework_html: str):
    body = _sync_nets_state_body(perfect_homework_html)
    assert "setAttribute('data-question-id'" in body, (
        "active wrapper must expose data-question-id so the collector knows "
        "which question_id to attach to the AI request"
    )
    assert "setAttribute('data-subphase'" in body, (
        "active wrapper must expose data-subphase so the AI prompt routing "
        "(memory-sprint vs adaptive-quiz vs final-boss …) is grounded in "
        "the DOM rather than a JS-only mirror"
    )


# ---------------------------------------------------------------------------
# 4. The wrapper targeted is .screen.active (not a per-question div)
# ---------------------------------------------------------------------------


def test_sync_nets_state_targets_active_screen(perfect_homework_html: str):
    """Using `.screen.active` as the active container means screen_context
    is scoped to the one phase root the runtime keeps shown — content from
    hidden screens (boss screen while we're in flashcards, etc) cannot
    leak into the AI context. A per-question target would be too narrow
    (the prompt + options often live in sibling divs).
    """
    body = _sync_nets_state_body(perfect_homework_html)
    assert ".screen.active" in body, (
        "syncNetsState must target `.screen.active` so screen_context is "
        "scoped to the visible phase root (not a per-question wrapper, "
        "which is too narrow, and not document.body, which leaks)."
    )


# ---------------------------------------------------------------------------
# 5. window.NETS_STATE mirror is still updated (PR #197 contract intact)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "key",
    [
        "window.NETS_STATE.phase",
        "window.NETS_STATE.subphase",
        "window.NETS_STATE.questionId",
    ],
)
def test_sync_nets_state_keeps_window_mirror(perfect_homework_html: str, key: str):
    """The DOM markers are additive — the JS-side mirror that PR #197 built
    must still update so the runtime fallback path (when no .screen has
    .active, e.g., during a phase fade) keeps working.
    """
    body = _sync_nets_state_body(perfect_homework_html)
    assert key in body, (
        f"syncNetsState must keep updating {key} (PR #197 contract); the "
        "DOM markers are additive, not a replacement."
    )
