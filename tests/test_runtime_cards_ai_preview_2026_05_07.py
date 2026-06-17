"""
Regression tests for PR — flashcards clamp / single-card finish, real-life
"Keyingi" AI lock, and screen-0 start-button overlap.

All checks are static asserts on the shipped runtime template — Python has
no JS runtime in CI, so we rely on regex over the source.

Issues covered:

  1a. Flashcard backward-scroll on card 1 wrapped to the last card via
      `getWrappedCardIndex(state.cardIndex - 1)`. Fix replaces the wrap with
      a clamp at the three navigation entry points (swipe handler, side-card
      click handlers, keyboard).

  1b. Phases with exactly one flashcard never showed "Yakunlash" because
      `startStage3` called `renderFlashcard(false)` regardless of count, and
      the only path that flips Yakunlash on is reaching `length - 1` via
      `switchCard` — but a single-card phase has no swipe target. Fix passes
      `fcCount <= 1` to the initial `renderFlashcard()`.

  2.  Real-Life AI grading is fired async via `rlDispatchTutorAi` while the
      morphing button is already showing "Keyingi savol". Students could tap
      Keyingi and skip the AI verdict. Fix adds a `setRlAiLock(true)`-driven
      `is-ai-pending` lock around the action button: dimmed, click-disabled
      via CSS pointer-events:none, and gated in JS handleAction. The lock
      clears in every `nets:result` exit path plus a 12 s safety timeout.

  3.  `.state-start` was pinned to viewport center via `bottom: 50vh;
      transform: translate(-50%, 50%)`, and the screen-0 title block had a
      hardcoded `margin-bottom: 140px` to clear it. Long titles (3-4 lines
      after `injector.py` rewrites the h1) bled into the button. Fix lowers
      the start CTA to `bottom: 22vh` (lower third), drops the +50% Y
      translate, and replaces the inline 140px margin with a `.screen-0-title`
      class with a smaller buffer.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


ROOT = Path(__file__).parent.parent
_JS_PATH = ROOT / "server" / "template" / "js" / "perfect_homework.js"
_CSS_PATH = ROOT / "server" / "template" / "static" / "css" / "perfect_homework.css"
_HTML_PATH = ROOT / "server" / "template" / "perfect_homework.html"
RUNTIME = _HTML_PATH.read_text(encoding="utf-8") + "\n" + _JS_PATH.read_text(encoding="utf-8") + "\n" + _CSS_PATH.read_text(encoding="utf-8")


def _read() -> str:
    return RUNTIME


# ── #1a flashcard clamp — no wrap at boundaries ─────────────────────────────


def test_swipe_handler_clamps_at_first_card():
    """The stage-3 swipe handler must not call switchCard with a wrapped
    index when on the first card. Look for the cardIndex > 0 guard in the
    right-swipe branch."""
    src = _read()
    # Find the handleSwipe stage-3 block.
    block = re.search(
        r"if \(state\.stage === 3\) \{(?P<body>.*?)return;\s*\}",
        src,
        re.DOTALL,
    )
    assert block, "stage-3 swipe block not found"
    body = block.group("body")
    # Backward direction must check cardIndex > 0 (NOT call getWrappedCardIndex).
    assert re.search(r"dir\s*===\s*['\"]right['\"]\s*&&\s*state\.cardIndex\s*>\s*0", body), (
        "Right-swipe (backward) must clamp at cardIndex > 0, not wrap"
    )
    # Forward direction must check cardIndex < length-1.
    assert re.search(r"dir\s*===\s*['\"]left['\"]\s*&&\s*state\.cardIndex\s*<\s*FLASHCARDS\.length\s*-\s*1", body), (
        "Left-swipe (forward) must clamp at cardIndex < FLASHCARDS.length - 1"
    )
    # And must NOT reference getWrappedCardIndex inside the swipe block.
    assert "getWrappedCardIndex" not in body, (
        "Swipe handler must not wrap via getWrappedCardIndex — clamp instead"
    )


def test_side_card_click_handlers_clamp_at_boundaries():
    """The setupFlashcardCarouselControls click/keyboard handlers must check
    boundaries before calling switchCard so the prev side-card on card 1
    cannot wrap to the last card."""
    src = _read()
    sig = re.search(r"function\s+setupFlashcardCarouselControls\s*\(\)\s*\{", src)
    assert sig, "setupFlashcardCarouselControls not found"
    # Walk to matching brace.
    start = sig.end()
    depth = 1
    i = start
    while i < len(src) and depth > 0:
        ch = src[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                break
        i += 1
    body = src[start:i]
    # rotateToPrev: must not call getWrappedCardIndex on (cardIndex - 1).
    assert "state.cardIndex <= 0" in body, (
        "rotateToPrev must early-return when cardIndex <= 0 (don't wrap)"
    )
    assert "state.cardIndex >= FLASHCARDS.length - 1" in body, (
        "rotateToNext must early-return when cardIndex is the last card"
    )
    assert "getWrappedCardIndex(state.cardIndex - 1)" not in body, (
        "rotateToPrev must clamp, not wrap"
    )
    assert "getWrappedCardIndex(state.cardIndex + 1)" not in body, (
        "rotateToNext must clamp, not wrap"
    )


def test_side_cards_hide_at_boundaries():
    """Visual rails for prev/next cards must hide at first/last index so the
    student can't click a wrap-preview card."""
    src = _read()
    sig = re.search(r"function\s+renderFlashcardSides\s*\(\)\s*\{", src)
    assert sig
    start = sig.end()
    depth = 1
    i = start
    while i < len(src) and depth > 0:
        ch = src[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                break
        i += 1
    body = src[start:i]
    assert "atFirst" in body and "atLast" in body, (
        "renderFlashcardSides must compute boundary flags"
    )
    assert "visibility" in body, (
        "Side rails must toggle visibility at boundaries so wrap-previews "
        "can't be clicked"
    )


# ── #1b single-card finish button — Yakunlash from first paint ──────────────


def test_single_card_phase_starts_with_yakunlash():
    """startStage3 must pass `fcCount <= 1` to renderFlashcard so the only
    card on screen also shows the finish CTA — there is no swipe target."""
    src = _read()
    sig = re.search(r"function\s+startStage3\s*\(\)\s*\{", src)
    assert sig
    start = sig.end()
    depth = 1
    i = start
    while i < len(src) and depth > 0:
        ch = src[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                break
        i += 1
    body = src[start:i]
    # The stale `renderFlashcard(false);` call must be gone.
    assert "renderFlashcard(false)" not in body, (
        "startStage3 must not hardcode false — single-card phase needs Yakunlash"
    )
    # And the call must condition on fcCount <= 1.
    assert re.search(r"renderFlashcard\(\s*fcCount\s*<=?\s*1", body), (
        "startStage3 must call renderFlashcard(fcCount <= 1) so a one-card "
        "phase activates Yakunlash from the first paint"
    )


# ── #2 real-life AI lock — student cannot bypass Keyingi while AI grading ───


def test_rl_ai_lock_helpers_present():
    """The lock/unlock helpers + safety timer must exist."""
    src = _read()
    assert re.search(r"function\s+setRlAiLock\s*\(", src), (
        "Missing setRlAiLock helper — needed to dim + click-disable the FAB"
    )
    assert re.search(r"function\s+rlClearAiPending\s*\(", src), (
        "Missing rlClearAiPending helper — needed for unified result-listener "
        "and safety-timeout exit paths"
    )
    assert "RL_AI_LOCK_TIMEOUT_MS" in src, (
        "Missing RL_AI_LOCK_TIMEOUT_MS — without it a dropped nets:result "
        "event would freeze the action button forever"
    )


def test_rl_dispatch_engages_lock():
    """rlDispatchTutorAi must call setRlAiLock(true) and arm the safety
    timer before dispatching the tutor request."""
    src = _read()
    sig = re.search(r"function\s+rlDispatchTutorAi\s*\(", src)
    assert sig
    start = sig.end()
    depth = 0
    # Walk until we find the first `{` and balance it.
    while src[start] != "{":
        start += 1
    start += 1
    depth = 1
    i = start
    while i < len(src) and depth > 0:
        ch = src[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                break
        i += 1
    body = src[start:i]
    assert "setRlAiLock(true)" in body, (
        "rlDispatchTutorAi must set the lock before firing the tutor event"
    )
    assert "rlPendingAiTimer" in body and "setTimeout" in body, (
        "rlDispatchTutorAi must arm the safety timer"
    )


def test_handle_action_blocks_while_locked():
    """handleAction must early-return when #action-button.is-ai-pending is set."""
    src = _read()
    sig = re.search(r"function\s+handleAction\s*\(\)\s*\{", src)
    assert sig
    start = sig.end()
    depth = 1
    i = start
    while i < len(src) and depth > 0:
        ch = src[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                break
        i += 1
    body = src[start:i]
    assert "is-ai-pending" in body, (
        "handleAction must consult the .is-ai-pending lock so taps during "
        "AI grading are no-ops"
    )


def test_action_button_lock_css_blocks_pointer_events():
    """The .is-ai-pending rule must dim opacity + block pointer events.
    Without pointer-events:none a click can still register before JS sees
    the lock class."""
    src = _read()
    block = re.search(
        r"#action-button\.is-ai-pending\s*\{(?P<body>[^}]*)\}",
        src,
    )
    assert block, "Missing #action-button.is-ai-pending rule"
    body = block.group("body")
    assert re.search(r"pointer-events\s*:\s*none", body), (
        "is-ai-pending must set pointer-events:none so clicks are swallowed "
        "even if the JS guard misses"
    )
    assert re.search(r"opacity\s*:", body), (
        "is-ai-pending must dim the button so the student sees it as inactive"
    )


def test_result_listener_clears_lock_on_every_path():
    """Every exit path inside the nets:result handler — stale ticket,
    fallback/error, missing fbEl, success — must call rlClearAiPending so
    the lock can't outlive the response."""
    src = _read()
    # Multiple `nets:result` listeners exist (tutor widget + real-life
    # phase). We want the real-life one — pick by scoping its body to
    # contain stage6State.
    body = None
    for m in re.finditer(r"document\.addEventListener\(['\"]nets:result['\"]", src):
        j = m.end()
        while j < len(src) and src[j] != "{":
            j += 1
        if j >= len(src):
            continue
        start = j + 1
        depth = 1
        i = start
        while i < len(src) and depth > 0:
            ch = src[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        candidate = src[start:i]
        if "stage6State" in candidate or "rlPendingAi" in candidate:
            body = candidate
            break
    assert body is not None, "real-life nets:result listener not found"
    # Count rlClearAiPending references — must replace the legacy 4 sites
    # where rlPendingAi = null was the only cleanup.
    clears = len(re.findall(r"rlClearAiPending\(\)", body))
    assert clears >= 4, (
        f"rlClearAiPending should fire on stale, fallback, missing-el, and "
        f"end-of-handler exit paths — found {clears} call sites in listener"
    )
    # The bare `rlPendingAi = null;` lines from the old version must be gone
    # to avoid leaving the lock engaged.
    assert "rlPendingAi = null;" not in body, (
        "Listener still has bare rlPendingAi = null — must use "
        "rlClearAiPending to also drop the lock + cancel the safety timer"
    )


# ── #3 screen-0 start CTA must clear the subject title ──────────────────────


def test_state_start_button_anchored_to_lower_third():
    """The start CTA must NOT pin its center to viewport middle (50vh +
    translateY 50%). It must anchor in the lower third so multi-line
    homework titles cannot bleed into it."""
    src = _read()
    block = re.search(r"\.state-start\s*\{(?P<body>[^}]*)\}", src)
    assert block, ".state-start CSS rule not found"
    raw_body = block.group("body")
    # Strip /* ... */ comments so legacy values mentioned in explanatory
    # comments don't fool the regex below.
    body = re.sub(r"/\*.*?\*/", "", raw_body, flags=re.DOTALL)
    # Must not pin center via translate(-50%, 50%) anymore.
    assert "translate(-50%, 50%)" not in body, (
        ".state-start no longer pins button center at viewport middle "
        "(was overlapping the subject title on long-h1 homeworks)"
    )
    # Must use translateX only.
    assert re.search(r"transform\s*:\s*translateX\(\s*-50%\s*\)", body), (
        ".state-start must use transform: translateX(-50%) (no Y component)"
    )
    # bottom must be in the lower third (smaller than 50vh).
    bottom = re.search(r"bottom\s*:\s*([\d.]+)vh", body)
    assert bottom, ".state-start must set bottom in vh units"
    val = float(bottom.group(1))
    assert val < 50, (
        f".state-start bottom must drop below the legacy 50vh center "
        f"anchor — got {val}vh"
    )
    # Sanity floor — don't let someone ship `bottom: 0` and bury the CTA.
    assert val >= 12, (
        f".state-start bottom shouldn't sit on the safe-area edge — got {val}vh"
    )


def test_screen_0_title_uses_class_not_inline_140px_margin():
    """The screen-0 inner block must no longer carry the inline 140px margin
    (it was a workaround for the centered-button overlap that the lower-third
    anchor now solves)."""
    src = _read()
    # Locate the screen-0 block.
    block = re.search(
        r'<div id="screen-0"[^>]*>(?P<body>.*?)</div>\s*<!--\s*Stage 1',
        src,
        re.DOTALL,
    )
    assert block, "screen-0 block not found"
    body = block.group("body")
    assert "margin-bottom: 140px" not in body, (
        "The 140px inline-margin spacer is obsolete now that the start CTA "
        "is bottom-anchored — remove it so titles can flex-center freely"
    )
    # And the new class must be present.
    assert "screen-0-title" in body, (
        "screen-0 inner block should carry .screen-0-title for stylable "
        "buffer instead of an inline 140px margin"
    )


def test_screen_0_title_class_has_buffer():
    """The .screen-0-title CSS rule must exist with at least a small
    bottom buffer so the title still feels grouped with the CTA."""
    src = _read()
    block = re.search(r"\.screen-0-title\s*\{(?P<body>[^}]*)\}", src)
    assert block, ".screen-0-title CSS rule not declared"
    body = block.group("body")
    assert re.search(r"margin-bottom\s*:", body), (
        ".screen-0-title must define a margin-bottom buffer"
    )
