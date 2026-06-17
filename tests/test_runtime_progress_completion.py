"""
Regression tests for the homework-player progress bar.

The top progress bar used to be driven entirely by `state.stage` via a
hardcoded `phaseMap` lookup — every transition `setStage(N)` immediately
moved the dots forward, regardless of whether the student had actually
completed the phase. That meant:
  - Inside a long phase (preview panels / flashcards / sprint / boss /
    real-life) the bar never moved while the student worked.
  - A timer- or auto-driven transition would mark a phase "done" before
    the student had finished it.
  - The Done dot only ever showed `.active` (60% fill in CSS), never 100%.

The refactor introduces a `completionState` model with per-phase
`{viewed, required, complete}` counters. `updateProgress()` now reads
real student-action counters — not raw stage index — to decide each
segment's state, and `setStage()` is purely a stage label that calls
through to `updateProgress()`.

These tests pin the new contract in place by static-greping
`server/template/perfect_homework.html`. They are runtime-agnostic:
they don't spin up a headless browser, they verify the source of truth.

If any of these break, the progress bar has likely regressed back to
hardcoded stage-index logic and the user-visible bug returns.
"""
from pathlib import Path

import pytest


_JS_PATH = Path(__file__).parent.parent / "server" / "template" / "js" / "perfect_homework.js"
_CSS_PATH = Path(__file__).parent.parent / "server" / "template" / "static" / "css" / "perfect_homework.css"
_HTML_PATH = Path(__file__).parent.parent / "server" / "template" / "perfect_homework.html"
HOMEWORK_HTML = _JS_PATH.read_text(encoding="utf-8") + "\n" + _CSS_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def runtime_source() -> str:
    return HOMEWORK_HTML


# ---------------------------------------------------------------------------
# Model exists
# ---------------------------------------------------------------------------

def test_completion_state_object_exists(runtime_source: str):
    """The new completionState model must be defined."""
    assert "const completionState = {" in runtime_source, (
        "completionState model missing — progress is likely back to "
        "hardcoded stage-index logic."
    )


@pytest.mark.parametrize(
    "phase_id",
    ["preview", "flashcards", "sprint", "gameBreaks", "realLife", "boss", "done"],
)
def test_completion_state_covers_each_phase(runtime_source: str, phase_id: str):
    """Every dot in the 7-segment bar must have a corresponding phase entry."""
    # Allow either single-line { viewed: ... } or multi-line declaration.
    assert phase_id + ":" in runtime_source, (
        f"phase '{phase_id}' missing from completionState — dot "
        f"{phase_id!r} would never advance."
    )


@pytest.mark.parametrize(
    "fn",
    [
        "function setPhaseRequired(",
        "function bumpPhase(",
        "function setPhaseProgress(",
        "function completePhase(",
        "function completeAllPhases(",
        "function updateProgress(",
    ],
)
def test_progress_helpers_exist(runtime_source: str, fn: str):
    assert fn in runtime_source, f"missing helper: {fn!r}"


# ---------------------------------------------------------------------------
# Hooks wired into every phase advance / answer / completion
# ---------------------------------------------------------------------------

REQUIRED_HOOKS = [
    # Preview: 1 (gate) + total sub-pages across all panels, distinct
    # (panel,page) pairs tracked via state.previewSeenPages so back-swipes
    # don't double-count and intra-panel page swipes drive the bar.
    # Complete when transitioning into flashcards.
    ("setPhaseRequired('preview',", "preview required set when stage 2 opens"),
    ("previewMarkPageSeen(", "preview tracks distinct (panel,page) pairs"),
    ("state.previewSeenPages", "preview seen-pages Set initialised"),
    ("completePhase('preview')", "preview marked done at flashcards transition"),
    # Flashcards: required = FLASHCARDS.length, distinct card indices
    # tracked in state.flashcardsSeen so back-and-forth navigation doesn't
    # over-count. Complete on endStage3.
    ("setPhaseRequired('flashcards',", "flashcards required at startStage3"),
    ("state.flashcardsSeen", "flashcards seen-cards Set initialised"),
    ("setPhaseProgress(\n                        'flashcards'", "flashcards progress driven by Set size"),
    ("completePhase('flashcards')", "flashcards marked done at endStage3"),
    # Sprint: required = MS_QUESTIONS.length, bump per next question,
    # complete on msFinishSprint.
    ("setPhaseRequired('sprint',", "sprint required at startMemorySprintPhase"),
    ("bumpPhase('sprint',", "sprint bumps per answered question"),
    ("completePhase('sprint')", "sprint marked done at msFinishSprint"),
    # Game Breaks: required = sub-game count; setPhaseProgress mirrors
    # gbUpdateProgress; complete on gbExitToStage6.
    ("setPhaseRequired('gameBreaks',", "gameBreaks required at startStage5"),
    ("setPhaseProgress('gameBreaks',", "gameBreaks progress mirrors sub-game idx"),
    ("completePhase('gameBreaks')", "gameBreaks marked done at gbExitToStage6"),
    # Real Life: required = number of questions; setPhaseProgress mirrors
    # submitted count; complete on rlShowEndPlaceholder.
    ("setPhaseRequired('realLife',", "realLife required at startStage6"),
    ("setPhaseProgress('realLife',", "realLife progress reflects answered count"),
    ("completePhase('realLife')", "realLife marked done at rlShowEndPlaceholder"),
    # Boss: required = BOSS_QUESTIONS.length; setPhaseProgress mirrors
    # bossState.qIndex; complete on bossEnd.
    ("setPhaseRequired('boss',", "boss required at startFinalBoss"),
    ("setPhaseProgress('boss',", "boss progress mirrors qIndex"),
    ("completePhase('boss')", "boss marked done at bossEnd"),
    # Results = 100% on every dot.
    ("completeAllPhases()", "completeAllPhases called at showResultsScreen"),
]


@pytest.mark.parametrize("hook,reason", REQUIRED_HOOKS)
def test_hook_present(runtime_source: str, hook: str, reason: str):
    assert hook in runtime_source, (
        f"missing progress hook: {hook!r}  ({reason}). Without this, the "
        "progress bar will not reflect real student completion for that phase."
    )


# ---------------------------------------------------------------------------
# Hardcoded stage-index hardening
# ---------------------------------------------------------------------------

def test_update_progress_does_not_grade_dots_purely_from_phase_map(runtime_source: str):
    """The body of updateProgress() must read completionState — not just
    derive `done`/`active` from a stage→dot lookup like the old code did."""
    # Locate the function body.
    start = runtime_source.index("function updateProgress(")
    # Read enough of the function to inspect — 4000 chars is plenty for the
    # body (the function is ~50 lines).
    body = runtime_source[start:start + 4000]
    # Cut at the function's closing brace heuristically — first "\n        }\n"
    # at column 8, matching the rest of the file's indent style.
    end = body.find("\n        }\n")
    if end > 0:
        body = body[:end]
    assert "completionState" in body or "ph.complete" in body or "ph.viewed" in body, (
        "updateProgress() body must consult completionState (ph.complete / "
        "ph.viewed) — otherwise progress is back to hardcoded stage-index logic."
    )


def test_old_phase_map_is_no_longer_the_sole_source_for_progress(runtime_source: str):
    """`phaseMap` may still exist for back-compat, but the runtime must
    NOT use `phaseMap[state.stage]` as the only signal for done/active
    classes. The refactored code uses `_currentPhaseIdForStage` to find
    which phase the student is in and `completionState` to decide
    done/active — so the legacy `const active = phaseMap[state.stage]`
    pattern must be gone."""
    assert "const active = phaseMap[state.stage]" not in runtime_source, (
        "old hardcoded `const active = phaseMap[state.stage]` pattern still "
        "present — progress bar will revert to stage-index behaviour."
    )


def test_progress_bar_partial_fill_uses_real_ratio(runtime_source: str):
    """The partial fill width for the active dot must derive from
    ph.viewed / ph.required, not a static 60%."""
    # Find the body of updateProgress and confirm the ratio expression is there.
    src = runtime_source
    start = src.index("function updateProgress(")
    end = src.find("\n        }\n        // Back-compat shim", start)
    if end < 0:
        end = start + 4000
    body = src[start:end]
    assert "ph.viewed / Math.max(1, ph.required)" in body, (
        "active-dot fill ratio is no longer derived from ph.viewed/ph.required — "
        "the dot will revert to the static 60% width and the user can't tell "
        "how far through a long phase they are."
    )


def test_done_phase_segments_reach_100_percent(runtime_source: str):
    """When ph.complete flips, the active dot must be set to width:100% so
    the bar reads as fully done — not the legacy 60% .active state."""
    src = runtime_source
    start = src.index("function updateProgress(")
    end = src.find("\n        }\n        // Back-compat shim", start)
    if end < 0:
        end = start + 4000
    body = src[start:end]
    # The complete branch should set 100%.
    assert "ph.complete" in body and "'100%'" in body, (
        "completed phase doesn't write width:100% — the Done dot will never "
        "reach 100% on the results screen."
    )


# ---------------------------------------------------------------------------
# Sanity: legacy back-compat shim still exists so other call sites work.
# ---------------------------------------------------------------------------

def test_legacy_update_phase_progress_still_callable(runtime_source: str):
    """setStage() and any external code calling updatePhaseProgress() must
    still work — it just delegates to updateProgress() now."""
    assert "function updatePhaseProgress() { updateProgress(); }" in runtime_source, (
        "back-compat updatePhaseProgress() shim missing — setStage() and "
        "other call sites would crash."
    )


# ---------------------------------------------------------------------------
# The "stuck at 35%" regression — preview must move with intra-panel page
# swipes, not just panel-to-panel transitions.
# ---------------------------------------------------------------------------

def test_preview_required_counts_sub_pages_not_just_panels(runtime_source: str):
    """startStage2 must set preview.required to (1 + total sub-pages across
    all panels), not just (1 + PANELS.length). Without this, a student
    reading a multi-page panel sees the bar frozen at the same percentage
    until they finish the panel and tap next — the user-visible 35% bug."""
    # The startStage2 body should sum p.pages.length across PANELS.
    src = runtime_source
    start = src.index("function startStage2(")
    body = src[start:start + 2500]
    assert "p.pages.length" in body or "panel.pages.length" in body, (
        "startStage2 doesn't sum sub-page counts — preview.required will "
        "stay at PANELS.length and the bar will stutter (the original "
        "'stuck at 35%' bug)."
    )
    assert "totalPages" in body, "totalPages accumulator missing in startStage2"


def test_switchpage_marks_each_page_seen(runtime_source: str):
    """switchPage (intra-panel sub-page navigation) must call
    previewMarkPageSeen so the bar moves while the student reads a long
    panel. This is the fix for the 35%-stuck regression."""
    src = runtime_source
    start = src.index("function switchPage(")
    end = src.find("\n        function ", start + 1)
    body = src[start:end] if end > 0 else src[start:start + 2500]
    assert "previewMarkPageSeen(" in body, (
        "switchPage doesn't mark the new page as seen — student swipes "
        "through panel sub-pages and the progress bar doesn't move."
    )


def test_nextpanel_marks_page_zero_of_new_panel_seen(runtime_source: str):
    """nextPanel must register the freshly-revealed (newPanelIdx, 0)
    pair as seen so transitioning panels also drives the bar forward."""
    src = runtime_source
    start = src.index("function nextPanel(")
    end = src.find("\n        function ", start + 1)
    body = src[start:end] if end > 0 else src[start:start + 2500]
    assert "previewMarkPageSeen(state.panelIndex, 0)" in body, (
        "nextPanel doesn't register the new panel's page 0 as seen."
    )


def test_flashcards_uses_distinct_set_not_per_event_bumps(runtime_source: str):
    """Flashcards progress must count distinct card indices visited (so
    back-and-forth navigation doesn't over-count or stall the bar). Look
    for state.flashcardsSeen and the size-changed guard."""
    src = runtime_source
    start = src.index("function switchCard(")
    end = src.find("\n        function ", start + 1)
    body = src[start:end] if end > 0 else src[start:start + 2500]
    assert "state.flashcardsSeen" in body, (
        "switchCard doesn't track distinct cards in state.flashcardsSeen — "
        "back-and-forth navigation would over-bump or stall the bar."
    )
    assert "beforeSize" in body and ".size !== beforeSize" in body, (
        "switchCard doesn't guard the progress write on a size change — "
        "re-visiting a card would double-count."
    )
