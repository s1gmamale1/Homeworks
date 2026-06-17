"""Regression tests for the phase announcement card retrofit (Bug #4).

Pins the invariants that ensure every phase transition the user sees
gets a labeled announcement card (not silent hand-offs):

  - A shared `phase-announce-card` overlay exists in the DOM.

  - `playPhaseAnnouncement(labelKey, onDone)` exists, reads the label
    from RUNTIME_LABELS via RT(), and delegates to the existing
    playPhaseIntro animation.

  - Sub-game transitions inside Stage 5 (Adaptive Quiz, Sentence Fill,
    Tile Match, Puzzle Lock, Mystery Box, Tic Tac Toe) each carry a
    `labelKey` field on their gbActiveGameOrder registry entry, and the
    `gbAdvanceFromGame` advancer fires the announcement before the next
    game's init runs.

  - Real-Life Challenge (startStage6), Consolidation (showConsolidationScreen),
    and Reflection (showReflectionScreen) each invoke
    `playPhaseAnnouncement` with the matching `phase.*` label key.

  - Boss is intentionally NOT retrofitted — it has its own bespoke
    `boss-intro-card` flow.

  - Per-locale labels exist in RUNTIME_LABELS for uz / ru / en. Card text
    follows the homework's language, never hardcoded to one locale.

If any of these regress, the user's "phases hand off silently" bug
returns. Each test is named after the regression it guards.
"""

from __future__ import annotations

import re
from pathlib import Path

_JS_PATH = Path(__file__).resolve().parent.parent / "server" / "template" / "js" / "perfect_homework.js"
_CSS_PATH = Path(__file__).resolve().parent.parent / "server" / "template" / "static" / "css" / "perfect_homework.css"
_HTML_PATH = Path(__file__).resolve().parent.parent / "server" / "template" / "perfect_homework.html"
TEMPLATE = _HTML_PATH.read_text(encoding="utf-8") + "\n" + _JS_PATH.read_text(encoding="utf-8") + "\n" + _CSS_PATH.read_text(encoding="utf-8")


def _slice_function(name: str) -> str:
    start = TEMPLATE.find(f"function {name}(")
    assert start != -1, f"function {name} not found in template"
    after = TEMPLATE.find("\n        function ", start + 1)
    if after == -1:
        after = len(TEMPLATE)
    return TEMPLATE[start:after]


# ---- Invariant 1: shared card DOM + helper exist --------------------------

def test_phase_announce_card_dom_exists():
    """The shared overlay card must be present in the template DOM."""
    assert '<div id="phase-announce-card"' in TEMPLATE
    assert 'id="phase-announce-text"' in TEMPLATE


def test_play_phase_announcement_helper_exists():
    """playPhaseAnnouncement(labelKey, onDone) is the new entry point."""
    assert "function playPhaseAnnouncement(labelKey, onDone)" in TEMPLATE


def test_play_phase_announcement_reads_label_from_i18n():
    """The card text must come from RT(labelKey), never hardcoded."""
    body = _slice_function("playPhaseAnnouncement")
    assert "RT(labelKey)" in body, (
        "playPhaseAnnouncement must look up the label via RT() so the card "
        "speaks the homework's language; hardcoding strings here would "
        "regress the i18n contract"
    )
    assert "playPhaseIntro('phase-announce-card'" in body, (
        "the helper must delegate to the existing playPhaseIntro animation "
        "with the shared card id"
    )


# ---- Invariant 2: sub-game transitions trigger the announcement -----------

def test_each_sub_game_registry_entry_has_label_key():
    """Every gbActiveGameOrder entry carries a labelKey for i18n lookup."""
    # The registry block is small enough to assert on the raw template.
    expected = [
        ("aq",  "game.aq"),
        ("wc",  "game.wc"),
        ("tm",  "game.tm"),
        ("pl",  "game.pl"),
        ("mb",  "game.mb"),
        ("ttt", "game.ttt"),
    ]
    for game_id, label_key in expected:
        # Pattern: id: 'aq' ... labelKey: 'game.aq'
        pattern = rf"id:\s*'{game_id}'[^}}]*labelKey:\s*'{re.escape(label_key)}'"
        assert re.search(pattern, TEMPLATE), (
            f"gbActiveGameOrder entry for {game_id!r} must carry "
            f"labelKey: {label_key!r} so the announcement card can look up "
            f"its localized name"
        )


def test_gb_advance_from_game_plays_announcement_before_transition():
    """Bug #6 fix: announcement card must precede gbTransition AND next.init.

    Pre-fix order was `gbTransition(...) { playPhaseAnnouncement(...) { init } }`
    which let the next sub-game's panel slide in underneath the announcement
    card. Correct order is `playPhaseAnnouncement(...) { gbTransition(...) { init } }`:
    previous panel stays visible behind the card, then after the card fades
    the new panel slides in cleanly.
    """
    body = _slice_function("gbAdvanceFromGame")
    pa_pos = body.find("playPhaseAnnouncement(next.labelKey")
    transition_pos = body.find("gbTransition(currentPanelId, next.panel")
    init_pos = body.find("next.init()")
    assert 0 < pa_pos < transition_pos < init_pos, (
        f"ordering must be playPhaseAnnouncement → gbTransition → next.init(); "
        f"got positions pa@{pa_pos} transition@{transition_pos} init@{init_pos}"
    )


def test_gb_advance_from_game_fades_previous_panel_before_announcement():
    """Timing fix (2026-05-06): the previous sub-game panel must visually
    close BEFORE the announcement card appears.

    Pre-fix flow: `playPhaseAnnouncement(...)` fired immediately while
    `currentPanelId` was still `.active` and fully opaque, so the next
    phase name was overlaid on the still-visible previous panel —
    students saw two phases at once. The fix sets the from-panel's
    opacity to 0 (and adds a blur) *before* the announcement, then runs
    the announcement inside a setTimeout/proceed callback so the fade
    has time to play.

    Pin in source: opacity-0 write must precede the playPhaseAnnouncement
    call, AND the playPhaseAnnouncement call must live inside a
    `proceed`/setTimeout block that runs after the fade transition.
    """
    body = _slice_function("gbAdvanceFromGame")
    fade_pos = body.find("fromPanel.style.opacity = '0'")
    pa_pos = body.find("playPhaseAnnouncement(next.labelKey")
    proceed_pos = body.find("const proceed = ()")
    settimeout_pos = body.find("setTimeout(proceed")
    assert 0 < fade_pos, (
        "gbAdvanceFromGame must set the from-panel's opacity to 0 to fade "
        "the previous game out before the announcement card appears"
    )
    assert 0 < proceed_pos < fade_pos, (
        "the `proceed` deferral closure must be declared before the "
        "fade-out write so the announcement is queued behind the fade"
    )
    assert 0 < proceed_pos < pa_pos, (
        "playPhaseAnnouncement must live inside the deferred `proceed` "
        "closure, not at the top level of gbAdvanceFromGame"
    )
    assert 0 < fade_pos < settimeout_pos, (
        "setTimeout(proceed, ...) must come AFTER the from-panel fade "
        "writes so the fade has actually started before the timer arms"
    )


def test_rlc_stage6_holds_screen_invisible_during_announcement():
    """Timing fix (2026-05-06): startRLCStage6 must keep #rlc-screen
    invisible while the phase.real_life announcement plays.

    Pre-fix: `rlcScreen.classList.add('active')` made the screen visible,
    then `playPhaseAnnouncement` fired immediately so any previously-
    rendered step content showed through behind the card. Mirror the
    startStage6 / showConsolidationScreen pattern: opacity 0 before the
    announcement, opacity 1 inside the onDone callback.
    """
    body = _slice_function("startRLCStage6")
    if "playPhaseAnnouncement" not in body:
        # If the path is gated and never calls the announcement, nothing
        # to assert — the bug can't manifest.
        return
    pa_pos = body.find("playPhaseAnnouncement('phase.real_life'")
    hide_pos = body.find("rlcScreen.style.opacity = '0'")
    reveal_pos = body.find("rlcScreen.style.opacity = '1'")
    assert 0 < hide_pos < pa_pos, (
        "startRLCStage6 must set #rlc-screen opacity to 0 BEFORE "
        "playPhaseAnnouncement so the screen content doesn't bleed "
        "through behind the card"
    )
    assert 0 < pa_pos < reveal_pos, (
        "the rlc-screen reveal (opacity 1) must be inside the "
        "playPhaseAnnouncement onDone callback, not before it"
    )


def test_announcement_is_not_triggered_from_progress_or_setstage_helpers():
    """Regression rule: the announcement card must only fire from explicit
    phase-transition functions, never from progress/state-update helpers.

    Calling `playPhaseAnnouncement` from `setStage`, `updateProgress`,
    `bumpPhase`, `setPhaseProgress`, `setPhaseRequired`, or `completePhase`
    would let the card pop in mid-phase whenever any of those bookkeeping
    helpers fired (e.g. on every flashcard tap, every sprint answer, every
    sub-game progress write). The card belongs to transition entry points
    only.
    """
    suspect_helpers = [
        "setStage",
        "updateProgress",
        "bumpPhase",
        "setPhaseProgress",
        "setPhaseRequired",
        "completePhase",
        "completeAllPhases",
        "updatePhaseProgress",
    ]
    for fn_name in suspect_helpers:
        if f"function {fn_name}(" not in TEMPLATE:
            continue
        body = _slice_function(fn_name)
        assert "playPhaseAnnouncement" not in body, (
            f"{fn_name}() must NOT call playPhaseAnnouncement — that helper "
            f"is fired on routine progress/state writes (every keystroke, "
            f"every flashcard tap, every sprint answer). If the announcement "
            f"is bound to it, the card will appear mid-phase."
        )


def test_phase_announcement_callers_run_after_screen_deactivation():
    """Pin the deactivation → announce → activate ordering for the entry-
    point functions that switch screens (not sub-game panels).

    `startStage6`, `showConsolidationScreen`, `showReflectionScreen` all
    follow the same template:
        document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
        ... add new screen + opacity:0 hold ...
        playPhaseAnnouncement(...);

    If `playPhaseAnnouncement` ever runs before the previous screens'
    `.classList.remove('active')`, the prior phase's content will still
    be on screen behind the announcement card.
    """
    for fn_name, label_key in [
        ("startStage6",            "'phase.real_life'"),
        ("showConsolidationScreen", "'phase.consolidation'"),
        ("showReflectionScreen",    "'phase.reflection'"),
    ]:
        body = _slice_function(fn_name)
        deactivate_pos = body.find(".classList.remove('active')")
        announce_pos = body.find("playPhaseAnnouncement(" + label_key)
        assert 0 < deactivate_pos < announce_pos, (
            f"{fn_name}: previous screens must have `.classList.remove('active')` "
            f"called BEFORE playPhaseAnnouncement; got deactivate@{deactivate_pos} "
            f"announce@{announce_pos}. The announcement card must never overlap "
            f"with unfinished previous-phase content."
        )


# ---- Invariant 3: post-Stage-5 phases trigger the announcement -----------

def test_real_life_phase_plays_announcement():
    """startStage6 plays the phase.real_life announcement before story reveal."""
    body = _slice_function("startStage6")
    assert "playPhaseAnnouncement('phase.real_life'" in body, (
        "Real-Life Challenge entry must show the labeled announcement card; "
        "without it, students transition silently from Game Breaks into a "
        "fresh scenario with no labeled hand-off"
    )


def test_real_life_card_hidden_during_announcement():
    """Bug #6 fix: startStage6 hides the WHOLE rl-card during the card.

    Hiding only `#rl-story-section` (pre-fix) left the rl-header-badge +
    card chrome visible behind the announcement so the student saw both
    simultaneously. Now the entire #rl-card opacity goes to 0 before the
    announcement and back to 1 inside the onDone callback.
    """
    body = _slice_function("startStage6")
    assert "rlCard.style.opacity = '0'" in body, (
        "startStage6 must set #rl-card opacity to 0 BEFORE playPhaseAnnouncement"
    )
    pa_pos = body.find("playPhaseAnnouncement('phase.real_life'")
    reveal_pos = body.find("rlCard.style.opacity = '1'")
    assert 0 < pa_pos < reveal_pos, (
        "rl-card reveal (opacity 1) must be inside the playPhaseAnnouncement "
        "onDone callback, not before it"
    )


def test_consolidation_phase_plays_announcement():
    """showConsolidationScreen plays the phase.consolidation announcement."""
    body = _slice_function("showConsolidationScreen")
    assert "playPhaseAnnouncement('phase.consolidation'" in body, (
        "Consolidation entry must show the labeled announcement card"
    )


def test_reflection_phase_plays_announcement():
    """showReflectionScreen plays the phase.reflection announcement."""
    body = _slice_function("showReflectionScreen")
    assert "playPhaseAnnouncement('phase.reflection'" in body, (
        "Reflection entry must show the labeled announcement card"
    )


# ---- Invariant 4: Boss is NOT retrofitted ---------------------------------

def test_boss_phase_does_not_use_phase_announcement_card():
    """Boss keeps its bespoke boss-intro-card; no playPhaseAnnouncement call."""
    # Boss flow lives in functions like startFinalBoss, bossRenderQuestion, bossEnd.
    # None of them should call the new helper.
    for fn_name in ("startFinalBoss", "bossEnd", "bossRenderQuestion"):
        if f"function {fn_name}" in TEMPLATE:
            body = _slice_function(fn_name)
            assert "playPhaseAnnouncement" not in body, (
                f"{fn_name} must NOT call playPhaseAnnouncement — Boss has its "
                f"own boss-intro-card flow that the user explicitly asked us "
                f"to leave alone"
            )


# ---- Invariant 5: per-locale labels exist for every announcement key ------

def test_runtime_labels_carry_phase_keys_in_all_three_locales():
    """phase.{game_breaks,real_life,consolidation,reflection} present in uz/ru/en."""
    # Find the 3 locale blocks
    uz_start = TEMPLATE.find("uz: {")
    ru_start = TEMPLATE.find("ru: {")
    en_start = TEMPLATE.find("en: {")
    assert uz_start != -1 and ru_start != -1 and en_start != -1
    # Order in the file is uz → ru → en
    uz_block = TEMPLATE[uz_start:ru_start]
    ru_block = TEMPLATE[ru_start:en_start]
    en_block = TEMPLATE[en_start:TEMPLATE.find("};", en_start)]

    phase_keys = ["phase.game_breaks", "phase.real_life", "phase.consolidation", "phase.reflection"]
    for block_name, block in [("uz", uz_block), ("ru", ru_block), ("en", en_block)]:
        for key in phase_keys:
            assert f"'{key}'" in block, (
                f"RUNTIME_LABELS.{block_name} is missing '{key}' — the "
                f"announcement card will fall back to the raw key text in "
                f"that locale, defeating i18n"
            )


def test_runtime_labels_carry_game_keys_in_all_three_locales():
    """game.{aq,wc,mm,pl,mb,ttt} present in uz/ru/en blocks."""
    uz_start = TEMPLATE.find("uz: {")
    ru_start = TEMPLATE.find("ru: {")
    en_start = TEMPLATE.find("en: {")
    uz_block = TEMPLATE[uz_start:ru_start]
    ru_block = TEMPLATE[ru_start:en_start]
    en_block = TEMPLATE[en_start:TEMPLATE.find("};", en_start)]

    game_keys = ["game.aq", "game.wc", "game.tm", "game.pl", "game.mb", "game.ttt"]
    for block_name, block in [("uz", uz_block), ("ru", ru_block), ("en", en_block)]:
        for key in game_keys:
            assert f"'{key}'" in block, (
                f"RUNTIME_LABELS.{block_name} is missing '{key}' — the "
                f"sub-game announcement will fall back to the raw key in "
                f"that locale"
            )


# ---- Invariant 6: empty sub-games still skip ------------------------------

def test_announcement_does_not_fire_for_empty_sub_games():
    """Empty sub-game arrays skip via gbActiveGameOrder filter — preserved."""
    # gbAdvanceFromGame iterates only over the filtered order list. If a
    # sub-game's array is empty, it's never in the list, so it's never
    # dispatched and the announcement never fires for it.
    order_body = _slice_function("gbActiveGameOrder")
    # The filter pattern: each .push() is gated on Array.isArray(GB_X) && length
    assert "Array.isArray(GB_ADAPTIVE_QUIZ) && GB_ADAPTIVE_QUIZ.length" in order_body or \
           "GB_ADAPTIVE_QUIZ.length" in order_body, (
        "gbActiveGameOrder must keep filtering empty game arrays so the "
        "announcement card is NOT dispatched for unauthored games — that "
        "would resurrect the placeholder-card bug from feedback_games_optional"
    )
