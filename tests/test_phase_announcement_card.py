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

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "server" / "template" / "perfect_homework.html"
TEMPLATE = TEMPLATE_PATH.read_text(encoding="utf-8")


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
        ("mm",  "game.mm"),
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


def test_gb_advance_from_game_plays_announcement_before_next_init():
    """gbAdvanceFromGame fires playPhaseAnnouncement before next.init()."""
    body = _slice_function("gbAdvanceFromGame")
    assert "playPhaseAnnouncement(next.labelKey" in body, (
        "the announcement must wrap next.init() so the student sees the "
        "next game's name before the game shell appears"
    )
    # The init() call should be inside the announcement callback, not before
    # it. Check ordering: playPhaseAnnouncement appears BEFORE next.init().
    pa_pos = body.find("playPhaseAnnouncement(next.labelKey")
    init_pos = body.find("next.init()")
    assert 0 < pa_pos < init_pos, (
        "next.init() must run inside the playPhaseAnnouncement onDone "
        "callback, not before — running it first would let the next game "
        "render under the announcement card"
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

    game_keys = ["game.aq", "game.wc", "game.mm", "game.pl", "game.mb", "game.ttt"]
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
