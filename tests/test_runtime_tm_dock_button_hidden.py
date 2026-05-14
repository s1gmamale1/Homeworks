"""Tile Match — action button hidden during play, shown on complete.

Bug history (2026-05-14, this PR):
  The morphing #action-button showed "Juftlikni tanlang" / "Ma'noni
  tanlang" (or RU/EN equivalents) during Tile Match play. The button
  is **not actionable** in that phase — `gbTMAction()` only advances
  when `gbState.tm.complete` is true; the user matches tiles by
  tapping them in #gb-panel-tm. Painting a pulsing pill with prompt
  text invited mistaken taps and crowded the small-viewport layout.

  Fix: extend `gbSetButtonNext(text, hidden)` with an optional
  `hidden` flag that adds the `tm-dock-hidden` class to #action-button.
  The class is opacity-based (0 + pointer-events: none + animation:
  none) so the position stays stable. Every call to gbSetButtonNext
  also REMOVES `tm-dock-hidden` first, so `gbTMFinish` calling
  ``gbSetButtonNext('<next>')`` (no second arg) automatically reveals
  the button again — no leakage to subsequent phases.

This file pins each invariant as a static-file assertion:
  1. The `tm-dock-hidden` CSS rule exists with opacity:0 and
     pointer-events:none (the two minimum properties needed to make
     the pill non-tappable and invisible).
  2. `gbSetButtonNext` removes `tm-dock-hidden` from the class list
     on every call (the auto-clear contract).
  3. `gbSetButtonNext` conditionally adds `tm-dock-hidden` when the
     `hidden` flag is truthy.
  4. Every in-game Tile Match callsite of `gbSetButtonNext` passes
     `true` as the second argument — there are FOUR such callsites
     (start, deselect, select, wrong-reset).
  5. `gbTMFinish` calls `gbSetButtonNext(...)` WITHOUT the hidden
     flag, so the button reappears when the user has matched every
     tile and "Keyingi …" must be tappable.
"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).parent.parent
RUNTIME = ROOT / "server" / "template" / "perfect_homework.html"

_CSS_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)


def _read() -> str:
    return RUNTIME.read_text(encoding="utf-8")


def _function_body(html: str, name: str) -> str:
    pattern = re.compile(r"function\s+" + re.escape(name) + r"\s*\([^)]*\)\s*\{")
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


# ── Clause 1: CSS rule hides the button visually + disables taps ─────


def test_tm_dock_hidden_class_hides_action_button():
    """Without ``opacity: 0`` the button still paints over content; without
    ``pointer-events: none`` an invisible button can still capture taps
    (the very confusion this PR is trying to remove). Both are required."""
    html = _CSS_COMMENT_RE.sub("", _read())
    pattern = re.compile(
        r"(?:^|\n)\s*#action-button\.tm-dock-hidden\s*\{",
    )
    m = pattern.search(html)
    assert m, (
        "Tile-Match regression: `#action-button.tm-dock-hidden` CSS rule "
        "is missing. The class is applied via gbSetButtonNext(text, true) "
        "during TM play, but without the rule the button stays visible."
    )
    start = html.index("{", m.start()) + 1
    depth = 1
    body = ""
    for i in range(start, len(html)):
        c = html[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                body = html[start:i]
                break
    # `!important` is necessary in practice — the base `#action-button`
    # rule sets `transition: all 600ms`, and without `!important` the
    # opacity property animates from 1 to 0 and any rival rule with
    # equal/lower specificity that lacks `!important` would tie and
    # leave the resolution to source order. Accept both forms.
    assert re.search(r"opacity\s*:\s*0(\s*!important)?\s*;", body), (
        "Tile-Match regression: `#action-button.tm-dock-hidden` no longer "
        "sets `opacity: 0`. The button stays painted during TM play."
    )
    assert re.search(r"pointer-events\s*:\s*none(\s*!important)?\s*;", body), (
        "Tile-Match regression: `#action-button.tm-dock-hidden` no longer "
        "sets `pointer-events: none`. An invisible button can still "
        "swallow taps meant for the tiles underneath."
    )
    # Skipping the 600ms transition on hide is load-bearing too — if the
    # browser pauses animations (background tab, DevTools, certain iframe
    # contexts) the opacity transition can stall mid-fade and the button
    # stays visible. Pin `transition: none` (with or without !important).
    assert re.search(r"transition\s*:\s*none(\s*!important)?\s*;", body), (
        "Tile-Match regression: `#action-button.tm-dock-hidden` no longer "
        "pins `transition: none`. The base `transition: all 600ms` rule "
        "would otherwise animate opacity from 1 to 0 — visible flicker "
        "on phase entry, and stalls at opacity:1 in paused-animation "
        "contexts (background tab, iframe preview)."
    )


# ── Clause 2: gbSetButtonNext auto-clears the class ──────────────────


def test_gbSetButtonNext_always_clears_tm_dock_hidden():
    """The helper must remove `tm-dock-hidden` on every call. Without
    this auto-clear, `gbTMFinish`'s call to `gbSetButtonNext('Keyingi …')`
    (no second arg) would not unhide the button, and the user would be
    stuck on the result card with no way to advance."""
    body = _function_body(_read(), "gbSetButtonNext")
    pattern = re.compile(
        r"classList\.remove\([^)]*['\"]tm-dock-hidden['\"]",
    )
    assert pattern.search(body), (
        "Tile-Match regression: `gbSetButtonNext` no longer removes "
        "`tm-dock-hidden` from #action-button's class list on entry. "
        "Once the class is applied, the button can never reappear — "
        "TM completion deadlocks the user on the result card."
    )


def test_gbSetButtonNext_adds_tm_dock_hidden_when_flag_true():
    """The conditional `if (hidden) classList.add('tm-dock-hidden')` is
    the only place the class is applied. If a refactor drops the
    conditional, the four TM callsites that pass `true` silently no-op
    and the button stays visible during play."""
    body = _function_body(_read(), "gbSetButtonNext")
    # Accept both ``if (hidden)`` and pattern ``hidden && ...``.
    pattern = re.compile(
        r"(?:if\s*\(\s*hidden\s*\)\s*)?[A-Za-z_$][\w.]*\.classList"
        r"\.add\s*\(\s*['\"]tm-dock-hidden['\"]",
    )
    matches = pattern.findall(body)
    assert matches, (
        "Tile-Match regression: `gbSetButtonNext` no longer adds the "
        "`tm-dock-hidden` class when the `hidden` flag is true. The four "
        "TM dock callsites become no-ops and the button stays visible."
    )


# ── Clause 3: all four TM dock-prompt callsites hide the button ──────


def _count_hidden_calls_in(fn_name: str) -> int:
    """Count ``gbSetButtonNext(RT('tm.dock_...'), <truthy>)`` calls
    inside the given top-level function."""
    body = _function_body(_read(), fn_name)
    pattern = re.compile(
        r"gbSetButtonNext\(\s*RT\(\s*['\"]tm\.dock_(?:select|choose_meaning)['\"]\s*\)"
        r"\s*,\s*(?:/\*[^*]*\*/\s*)?(?:true|1)\b",
    )
    return len(pattern.findall(body))


def test_gbInitTM_hides_action_button_on_initial_render():
    """`gbInitTM` runs once when the TM phase mounts. The button must
    enter the phase hidden — leaving it visible at start would only
    confuse users for the ~half-second before they tap a tile.
    (Function name is `gbInitTM`, not `gbTMStart` — Tile Match uses the
    shared `gbInit<Game>` mount convention.)"""
    body = _function_body(_read(), "gbInitTM")
    assert re.search(
        r"gbSetButtonNext\(\s*RT\(\s*['\"]tm\.dock_select['\"]\s*\)"
        r"\s*,\s*(?:/\*[^*]*\*/\s*)?(?:true|1)\b",
        body,
    ), (
        "Tile-Match regression: `gbInitTM` no longer hides the action "
        "button on mount. The pulsing pill will be visible at the start "
        "of the phase even though it is not tappable."
    )


def test_gbTMSelectLeft_hides_button_on_select_and_deselect():
    """Left-column tile click has two branches: deselect (same tile
    tapped twice) and select (a new left tile chosen). Both call
    `gbSetButtonNext(RT('tm.dock_...'))` to update the prompt text;
    both must pass `hidden=true` so the pill stays invisible."""
    n = _count_hidden_calls_in("gbTMSelectLeft")
    assert n == 2, (
        f"Tile-Match regression: expected exactly 2 hidden-flag dock "
        f"calls inside `gbTMSelectLeft` (select branch + deselect "
        f"branch), found {n}. Either a branch is missing the hidden "
        f"flag or the function has been restructured."
    )


def test_gbTMHandleResponse_hides_button_on_wrong_reset():
    """When the user picks a wrong pair, the post-feedback reset path
    calls `gbSetButtonNext(RT('tm.dock_select'))` to restore the
    prompt — that call must also keep the button hidden."""
    body = _function_body(_read(), "gbTMHandleResponse")
    assert re.search(
        r"gbSetButtonNext\(\s*RT\(\s*['\"]tm\.dock_select['\"]\s*\)"
        r"\s*,\s*(?:/\*[^*]*\*/\s*)?(?:true|1)\b",
        body,
    ), (
        "Tile-Match regression: the wrong-pair reset path inside "
        "`gbTMHandleResponse` no longer hides the action button. The "
        "pill flashes back into view for ~1.5s after every wrong match."
    )


def test_no_TM_dock_callsite_omits_the_hidden_flag():
    """Belt-and-suspenders: scan the entire runtime for any
    `gbSetButtonNext(RT('tm.dock_*'), …)` call and verify each one
    passes a truthy second argument. Easier to maintain than enumerating
    callsites by hand if a future refactor adds a fifth path."""
    html = _read()
    # Match the full call and capture the args portion.
    pattern = re.compile(
        r"gbSetButtonNext\(\s*RT\(\s*['\"]tm\.dock_(?:select|choose_meaning)['\"]\s*\)"
        r"([^)]*)\)",
    )
    all_calls = pattern.findall(html)
    assert all_calls, (
        "Tile-Match anchor: no `gbSetButtonNext(RT('tm.dock_*'))` calls "
        "found at all. Either the phase has been removed or the i18n "
        "key shape has changed — re-audit before weakening the test."
    )
    bad_calls: list[str] = []
    for tail in all_calls:
        # Trim whitespace + the leading comma if present. A truthy second
        # argument means "true" or "1" (with optional /* comment */ ahead).
        normalised = re.sub(r"\s+", "", tail)
        if not re.match(r",(/\*[^*]*\*/)?(true|1)$", normalised):
            bad_calls.append(tail)
    assert not bad_calls, (
        f"Tile-Match regression: {len(bad_calls)} `gbSetButtonNext("
        f"RT('tm.dock_*'))` call(s) are missing the hidden=true flag. "
        f"Offending tails: {bad_calls!r}. Every TM dock callsite must "
        f"hide the button — it isn't tappable during play."
    )


# ── Clause 4: completion path reveals the button ─────────────────────


def _balanced_call_args(src: str, fn_name: str) -> list[str]:
    """Return the argument source of every top-level call to ``fn_name``
    inside ``src``. Walks parentheses so we get the FULL argument list
    even when args contain nested calls (e.g.
    ``gbSetButtonNext(gbIsLastGame(2) ? RT('a') : RT('b'))``)."""
    out: list[str] = []
    needle = fn_name + "("
    i = 0
    while True:
        idx = src.find(needle, i)
        if idx < 0:
            return out
        start = idx + len(needle)
        depth = 1
        j = start
        while j < len(src) and depth > 0:
            c = src[j]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    out.append(src[start:j])
                    break
            j += 1
        i = j + 1


def _has_top_level_comma(arg_src: str) -> bool:
    """True iff ``arg_src`` has a comma outside every ``(...)`` group.
    Used to detect a second argument to a function call."""
    depth = 0
    for ch in arg_src:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            return True
    return False


def test_gbTMFinish_reveals_button_with_no_hidden_flag():
    """`gbTMFinish` runs once when every tile has been matched. It must
    call `gbSetButtonNext(...)` WITHOUT a truthy second argument so the
    `tm-dock-hidden` class is auto-cleared and the "Keyingi …" pill
    becomes tappable. Without this, the user gets stranded on the
    result card with no way to advance to the next game / stage.

    The actual call shape is
    ``gbSetButtonNext(gbIsLastGame(2) ? RT('btn.next_stage') : RT('btn.next_game'))``
    — a single ternary expression with nested ``RT()`` calls. A
    paren-balanced walk is the only way to recognise it as a one-arg
    call; naive ``[^)]+?`` regexes stop at the first ``)`` and miss
    the rest of the ternary.
    """
    body = _function_body(_read(), "gbTMFinish")
    all_calls = _balanced_call_args(body, "gbSetButtonNext")
    assert all_calls, (
        "Tile-Match regression: `gbTMFinish` no longer calls "
        "`gbSetButtonNext(...)`. The action button stays in whatever "
        "state TM-play left it — likely tm-dock-hidden — and the user "
        "cannot advance past the result card."
    )
    visible_finishers = [
        arg for arg in all_calls
        if "btn.next" in arg and not _has_top_level_comma(arg)
    ]
    assert visible_finishers, (
        "Tile-Match regression: every `gbSetButtonNext(RT('btn.next_*'))` "
        "call inside `gbTMFinish` is passing a second argument. The "
        "hidden flag must be absent (or falsy) here so the button "
        "reappears with the 'Keyingi …' label."
    )


# ── Clause 5: phase-exit cleanup — class must not leak across phases ─
#
# Bug history (PR #231, HW-20260514-007 audit):
#   The `tm-dock-hidden` auto-clear contract (Clause 2) only fires on
#   `gbSetButtonNext` calls. But the GB→RL exit path (gbExitToStage6 →
#   startStage6) bypasses gbSetButtonNext entirely, so when Tile Match
#   was the last GB sub-game the class survived into the Real-Life
#   phase entry: button rendered with the right state-pill + pulse +
#   "Boshlash" text but opacity:0 from the leaked class made it
#   invisible. Same leak then propagated into Boss entry on the
#   subsequent phase transition.
#
# Fix: every phase-entry that re-skins the morph button must explicitly
# strip `tm-dock-hidden` from its classList.remove call (or equivalent).
# These four pins lock in the cleanup so a future refactor can't quietly
# re-introduce the leak.


_TM_DOCK_REMOVE_RE = re.compile(
    r"classList\.remove\([^)]*['\"]tm-dock-hidden['\"]",
)


def test_gbExitToStage6_strips_tm_dock_hidden_on_phase_exit():
    """gbExitToStage6 is the primary leak point: it transitions Game
    Breaks → Real Life without going through gbSetButtonNext. Must
    include `tm-dock-hidden` in its btn.classList.remove so the class
    doesn't survive into startStage6's button-state setup. Without this
    strip, every homework whose last GB sub-game was Tile Match boots
    into RL with an invisible Boshlash button."""
    body = _function_body(_read(), "gbExitToStage6")
    assert _TM_DOCK_REMOVE_RE.search(body), (
        "Phase-exit regression: `gbExitToStage6` no longer strips "
        "`tm-dock-hidden` from btn.classList. Tile Match's dock-hide "
        "class will leak into the Real-Life phase entry — Boshlash "
        "button renders at opacity:0 (see HW-20260514-007 bug report)."
    )


def test_startStage6_strips_tm_dock_hidden_on_phase_entry():
    """Defensive backstop in the RL phase entry. gbExitToStage6 is the
    primary cleanup point, but startStage6 must also strip the class so
    any other path into Real Life (session restore, skip shortcuts,
    direct phase-routing) can't leave the Boshlash button invisible."""
    body = _function_body(_read(), "startStage6")
    assert _TM_DOCK_REMOVE_RE.search(body), (
        "Phase-entry regression: `startStage6` no longer strips "
        "`tm-dock-hidden`. Removes the defensive backstop — if any "
        "non-gbExitToStage6 path reaches RL with the class set, the "
        "Boshlash button stays invisible."
    )


def test_startFinalBoss_strips_tm_dock_hidden_on_phase_entry():
    """Boss phase entry — same defensive strip. The user-reported
    repro (HW-20260514-007) showed the Javob submit button invisible on
    boss entry even after the Boshlash bug was triggered upstream. Both
    `btn.classList.remove` and the local `ab` element handle must clear
    the class so any leak path is closed."""
    body = _function_body(_read(), "startFinalBoss")
    # Either btn.classList.remove(...'tm-dock-hidden'...) or ab.classList.remove('tm-dock-hidden')
    # is acceptable — the function uses both names for the same element.
    has_btn_remove = _TM_DOCK_REMOVE_RE.search(body) is not None
    has_ab_remove = re.search(
        r"ab\.classList\.remove\(\s*['\"]tm-dock-hidden['\"]\s*\)",
        body,
    ) is not None
    assert has_btn_remove or has_ab_remove, (
        "Phase-entry regression: `startFinalBoss` no longer strips "
        "`tm-dock-hidden` from the action button. If a TM session leaked "
        "the class through RL into Boss, the Javob submit pill renders "
        "at opacity:0 and the boss phase is unplayable."
    )


def test_showConsolidationScreen_strips_tm_dock_hidden():
    """Consolidation interstitial sits between Real Life and Boss for
    homeworks that have consolidation content. Defensive strip here
    closes the last skip-shortcut path that could leak the class — any
    flow that jumps into consolidation with `tm-dock-hidden` still set
    would otherwise hide the consolidation phase's bottom CTA."""
    body = _function_body(_read(), "showConsolidationScreen")
    assert _TM_DOCK_REMOVE_RE.search(body), (
        "Phase-entry regression: `showConsolidationScreen` no longer "
        "strips `tm-dock-hidden`. Skip-to-consolidation paths can leave "
        "the Keyingi pill invisible — re-introduces the same class-leak "
        "family the rest of Clause 5 closes."
    )
