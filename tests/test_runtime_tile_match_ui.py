"""Regression tests for the Tile Match runtime UI (frontend side).

Pins the contract between this PR's frontend work and the backend's tile-match
endpoint (phase='tile-match'):
- Panel markup hooks (#gb-panel-tm + child IDs)
- JS state machine functions (16) are present and wired
- Sub-slot 2 lives in gbActiveGameOrder with id:'tm'
- gbState.tm initial shape (tiles/pairsTotal/selectedLeft/complete)
- GB_TILE_MATCH global declaration present
- Dispatch branch (subGame===2) routes to gbTMAction / gbAdvanceFromGame(2,...)
- extract_student_work tile-match extractor reads gbState.tm (not gbState.mm)
- gbTMCheckPair POSTs phase='tile-match' + left_id + right_id + homework_id
  + session_id so backend attempt state does not bleed across students/runs
- Dark-mode CSS overrides (≥15 selectors)
- i18n keys (tm.*) exist in all three runtime languages (uz/ru/en)
- No answer-leak attrs in TM panel markup or TM JS layer
- No mode-toggle button inside TM panel (mode is implicit)
- Legacy MM classes untouched (CSS preserved)

These pins protect against regressions where someone renames a selector,
reverts wiring, or confuses TM with the old MM state machine.

Companion to:
- tests/test_optional_games.py (registry + advance hook for all 8 games)
- tests/test_runtime_sentence_fill_ui.py (reference pattern, SF slot 6)
"""
from __future__ import annotations

import re

import pytest

from server.services.injector import inject


def _empty_content():
    return {
        "meta": {"title": "TM UI Smoke", "subject_display": "X", "section": "", "cefr_level": ""},
        "gate_quote": {"mode": "auto"},
        "panels": [],
        "flashcards": [],
        "memory_sprint": [],
        "gb_adaptive_quiz": [],
        "gb_why_chain": [],
        "gb_memory_match": [],
        "gb_puzzle_lock": [],
        "gb_mystery_box": [],
        "gb_ttt": [],
        "gb_sentence_fill": [],
        "gb_tile_match": [],
        "boss_questions": [],
        "real_life": None,
        "reading": None,
        "consolidation": None,
        "reflection": None,
    }


# ---------------------------------------------------------------------------
# 1. Panel presence
# ---------------------------------------------------------------------------


def test_tm_panel_present():
    """#gb-panel-tm must exist and have class gb-game-panel."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-TM-1", "subject": "math-algebra", "grade": 8})
    assert 'id="gb-panel-tm"' in html, "#gb-panel-tm is missing from the template"
    assert "gb-game-panel" in html, ".gb-game-panel class missing — panel transition won't fire"
    # Confirm both on the same element
    assert re.search(r'class="gb-game-panel[^"]*"\s+id="gb-panel-tm"', html), (
        "#gb-panel-tm must carry class gb-game-panel for Stage-5 transition"
    )


# ---------------------------------------------------------------------------
# 2. Top-bar dots + match pill
# ---------------------------------------------------------------------------


def test_tm_topbar_has_dots_and_match_pill():
    """Top-bar must expose progress dots, active dot, and matched/total pill."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-TM-2", "subject": "math-algebra", "grade": 8})
    assert 'class="gb-tm-dots"' in html, ".gb-tm-dots missing"
    assert 'class="gb-tm-dot-active"' in html, ".gb-tm-dot-active missing"
    assert 'id="gb-tm-matched-top"' in html, "#gb-tm-matched-top missing"
    assert 'id="gb-tm-pairs-total"' in html, "#gb-tm-pairs-total missing"


# ---------------------------------------------------------------------------
# 3. Hero section — eyebrow, XP pill, title, subtitle
# ---------------------------------------------------------------------------


def test_tm_hero_has_eyebrow_title_subtitle_xp():
    """Hero article must contain eyebrow, XP pill, h1 title, and subtitle."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-TM-3", "subject": "math-algebra", "grade": 8})
    assert 'id="gb-tm-eyebrow"' in html, "#gb-tm-eyebrow missing"
    assert 'id="gb-tm-xp-pill"' in html, "#gb-tm-xp-pill missing"
    assert 'id="gb-tm-title"' in html, "#gb-tm-title missing"
    assert 'id="gb-tm-subtitle"' in html, "#gb-tm-subtitle missing"


# ---------------------------------------------------------------------------
# 4. Stats grid — three cards + three labels
# ---------------------------------------------------------------------------


def test_tm_stats_grid_has_no_fake_timer():
    """Timer is intentionally hidden: it was server-tick only, not real-time."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-TM-4", "subject": "math-algebra", "grade": 8})
    assert 'id="gb-tm-timer"' not in html, "#gb-tm-timer should stay removed from visible UI"
    assert 'id="gb-tm-stat-timer-label"' not in html, "#gb-tm timer label should stay removed"
    assert 'id="gb-tm-matched-stat"' in html, "#gb-tm-matched-stat missing"
    assert 'id="gb-tm-wrong-stat"' in html, "#gb-tm-wrong-stat missing"
    assert 'id="gb-tm-stat-matched-label"' in html, "#gb-tm-stat-matched-label missing"
    assert 'id="gb-tm-stat-wrong-label"' in html, "#gb-tm-stat-wrong-label missing"


# ---------------------------------------------------------------------------
# 5. Board columns
# ---------------------------------------------------------------------------


def test_tm_board_columns():
    """Board must expose left + right column containers and their label IDs."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-TM-5", "subject": "math-algebra", "grade": 8})
    assert 'id="gb-tm-col-left"' in html, "#gb-tm-col-left missing"
    assert 'id="gb-tm-col-right"' in html, "#gb-tm-col-right missing"
    assert 'id="gb-tm-left"' in html, "#gb-tm-left tile container missing"
    assert 'id="gb-tm-right"' in html, "#gb-tm-right tile container missing"
    assert 'id="gb-tm-col-left-label"' in html, "#gb-tm-col-left-label missing"
    assert 'id="gb-tm-col-right-label"' in html, "#gb-tm-col-right-label missing"


# ---------------------------------------------------------------------------
# 6. Result card
# ---------------------------------------------------------------------------


def test_tm_result_card_present():
    """Result card must exist with title, body text, score label, and score value."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-TM-6", "subject": "math-algebra", "grade": 8})
    assert 'id="gb-tm-result-card"' in html, "#gb-tm-result-card missing"
    assert 'id="gb-tm-result-title"' in html, "#gb-tm-result-title missing"
    assert 'id="gb-tm-result-text"' in html, "#gb-tm-result-text missing"
    assert 'id="gb-tm-score-label"' in html, "#gb-tm-score-label missing"
    assert 'id="gb-tm-score-value"' in html, "#gb-tm-score-value missing"


# ---------------------------------------------------------------------------
# 7. Toast element
# ---------------------------------------------------------------------------


def test_tm_toast_present():
    """#gb-tm-toast must exist with role=status and aria-live=polite."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-TM-7", "subject": "math-algebra", "grade": 8})
    assert 'id="gb-tm-toast"' in html, "#gb-tm-toast missing"
    toast_match = re.search(r'id="gb-tm-toast"[^>]*', html)
    assert toast_match, "#gb-tm-toast element not found"
    toast_tag = toast_match.group(0)
    assert 'role="status"' in toast_tag, '#gb-tm-toast must have role="status"'
    assert 'aria-live="polite"' in toast_tag, '#gb-tm-toast must have aria-live="polite"'


# ---------------------------------------------------------------------------
# 8. gbState.tm initial shape
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field", [
    "tiles:[]",
    "pairsTotal:0",
    "selectedLeft:null",
    "complete:false",
    "sessionId:null",
])
def test_tm_state_slot_in_gbState(field):
    """gbState.tm initial object must contain the expected field."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-TM-8", "subject": "math-algebra", "grade": 8})
    # Normalise whitespace for comparisons like "tiles: []" vs "tiles:[]"
    compact = re.sub(r'\s+', '', html)
    field_compact = re.sub(r'\s+', '', field)
    assert f"tm:{{{field_compact}" in compact or field_compact in compact, (
        f"gbState.tm must contain '{field}' — JS state machine depends on it"
    )


# ---------------------------------------------------------------------------
# 9. GB_TILE_MATCH global declaration
# ---------------------------------------------------------------------------


def test_tm_global_declaration():
    """const GB_TILE_MATCH = ...; must be present in the post-inject JS.
    The injector substitutes __GB_TILE_MATCH__ with a JSON array — for empty
    homeworks that's `[]`; for populated ones it's the side-disjoint flat list."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-TM-9", "subject": "math-algebra", "grade": 8})
    assert re.search(r"const GB_TILE_MATCH\s*=\s*\[", html), (
        "GB_TILE_MATCH global declaration missing — injector did not substitute __GB_TILE_MATCH__"
    )


# ---------------------------------------------------------------------------
# 10. Registry row at slot 2
# ---------------------------------------------------------------------------


def test_tm_registry_row_at_slot_2():
    """gbActiveGameOrder must include exactly one TM entry at sub:2."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-TM-10", "subject": "math-algebra", "grade": 8})
    assert re.search(
        r"id:\s*'tm',\s*sub:\s*2,\s*init:\s*gbInitTM,\s*panel:\s*'gb-panel-tm',\s*label:\s*'Tile Match',\s*labelKey:\s*'game\.tm'",
        html,
    ), "Tile Match must be registered at sub:2 in gbActiveGameOrder() with correct fields"


# ---------------------------------------------------------------------------
# 11. Dispatch branch — subGame === 2
# ---------------------------------------------------------------------------


def test_tm_dispatch_branch_updated():
    """gbHandleAction subGame===2 branch must use gbState.tm, gbTMAction(),
    and gbAdvanceFromGame(2, 'gb-panel-tm') — NOT gbState.mm / gbMMAction."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-TM-11", "subject": "math-algebra", "grade": 8})
    # Find the subGame===2 branch — the block contains nested braces so we
    # match from the opening `{` up through the first standalone `}` line
    # (using DOTALL so `.` crosses newlines).
    assert "gbState.subGame === 2" in html, "gbHandleAction must branch on subGame===2"
    branch = re.search(
        r"if \(gbState\.subGame === 2\)\s*\{[\s\S]*?\n\s+\}",
        html,
    )
    assert branch, "subGame===2 branch body not found"
    body = branch.group(0)
    assert "gbState.tm" in body, "subGame===2 branch must reference gbState.tm"
    assert "gbTMAction()" in body, "subGame===2 branch must call gbTMAction()"
    assert "gbAdvanceFromGame(2, 'gb-panel-tm')" in body, (
        "subGame===2 branch must call gbAdvanceFromGame(2, 'gb-panel-tm')"
    )
    assert "gbState.mm" not in body, (
        "subGame===2 branch must NOT reference gbState.mm — TM replaced MM at slot 2"
    )
    assert "gbMMAction" not in body, (
        "subGame===2 branch must NOT call gbMMAction — TM replaced MM at slot 2"
    )


# ---------------------------------------------------------------------------
# 12. extract_student_work tile-match extractor reads gbState.tm
# ---------------------------------------------------------------------------


def test_tm_extract_student_work_uses_tm_state():
    """The 'tile-match' extractor branch must read gbState.tm, not gbState.mm."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-TM-12", "subject": "math-algebra", "grade": 8})
    extractor = re.search(
        r"'tile-match':\s*\(\)\s*=>\s*\{[\s\S]*?\},",
        html,
    )
    assert extractor, "'tile-match' extractor branch not found in extract_student_work"
    body = extractor.group(0)
    assert "gbState.tm" in body, "tile-match extractor must read gbState.tm"
    assert "gbState.mm" not in body, (
        "tile-match extractor must NOT read gbState.mm — wrong state object"
    )


# ---------------------------------------------------------------------------
# 13. State machine functions — all 16 must be defined
# ---------------------------------------------------------------------------


REQUIRED_TM_FUNCTIONS = [
    "gbInitTM",
    "gbTMRenderStaticI18n",
    "gbTMShuffle",
    "gbTMRenderBoard",
    "gbTMSelectLeft",
    "gbTMTryMatch",
    "gbTMCheckPair",
    "gbTMHandleResponse",
    "gbTMShowHint",
    "gbTMShowToast",
    "gbTMUpdateStats",
    "gbTMUpdateXp",
    "gbTMRenderResult",
    "gbTMFinish",
    "gbTMAction",
]


@pytest.mark.parametrize("fn", REQUIRED_TM_FUNCTIONS)
def test_tm_state_machine_functions_present(fn):
    """Every TM JS function must be defined — any missing causes a runtime error on first mount."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-TM-13", "subject": "math-algebra", "grade": 8})
    assert f"function {fn}(" in html, (
        f"TM state machine function {fn}() is missing — was it deleted or renamed?"
    )


# ---------------------------------------------------------------------------
# 14. gbTMCheckPair endpoint contract
# ---------------------------------------------------------------------------


def test_tm_check_pair_endpoint_contract():
    """gbTMCheckPair must POST phase='tile-match', ids, homework_id, and session_id."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-TM-14", "subject": "math-algebra", "grade": 8})
    fn_match = re.search(
        r"async function gbTMCheckPair\([^)]*\)\s*\{[\s\S]*?(?=\n\s{8}(?:async\s+)?function )",
        html,
    )
    assert fn_match, "gbTMCheckPair function body not found"
    body = fn_match.group(0)
    assert "phase: 'tile-match'" in body, "gbTMCheckPair must send phase='tile-match'"
    assert "left_id" in body, "gbTMCheckPair must send left_id"
    assert "right_id" in body, "gbTMCheckPair must send right_id"
    assert "homework_id" in body, "gbTMCheckPair must send homework_id"
    assert "session_id" in body, "gbTMCheckPair must send session_id to isolate attempt state"


def test_tm_init_mints_session_id_before_first_check():
    """Each Tile Match mount gets a fresh client session id before grading starts."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-TM-14B", "subject": "math-algebra", "grade": 8})
    init_match = re.search(
        r"function gbInitTM\(\)\s*\{[\s\S]*?(?=\n\s{8}function gbTMRenderStaticI18n)",
        html,
    )
    assert init_match, "gbInitTM function body not found"
    body = init_match.group(0)
    assert "tm.sessionId = gbTMSessionId();" in body, (
        "gbInitTM must mint a per-run session id so correct matches from a previous run "
        "cannot make this run's correct answer look wrong"
    )
    assert "function gbTMSessionId()" in html, "gbTMSessionId helper missing"


# ---------------------------------------------------------------------------
# 15. i18n keys for all three languages
# ---------------------------------------------------------------------------


TM_I18N_KEYS = [
    "tm.eyebrow",
    "tm.title",
    "tm.subtitle",
    "tm.col_left",
    "tm.col_right",
    "tm.stats_matched",
    "tm.stats_wrong",
    "tm.toast_correct",
    "tm.toast_streak",
    "tm.toast_wrong",
    "tm.toast_pick_left",
    "tm.result_perfect",
    "tm.result_flawless",
    "tm.result_cleared",
    "tm.result_not_yet",
    "tm.dock_select",
    "tm.dock_choose_meaning",
    "tm.dock_next_game",
    "tm.dock_replay",
    "tm.hint_correct",
    "tm.xp_label",
    "game.tm",
    "tm.pairs_status",
]


@pytest.mark.parametrize("key", TM_I18N_KEYS)
def test_tm_i18n_keys_uz_ru_en(key):
    """Every tm.* key must appear at least 3 times (uz + ru + en blocks)."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-TM-15", "subject": "math-algebra", "grade": 8})
    count = html.count(f"'{key}'")
    assert count >= 3, (
        f"i18n key '{key}' appears {count} times — expected ≥3 (uz+ru+en). "
        "Was a translation block reverted?"
    )


# ---------------------------------------------------------------------------
# 16. Dark-mode CSS parity
# ---------------------------------------------------------------------------


def test_tm_dark_mode_has_parity():
    """At least 15 [data-theme=\"dark\"] .gb-tm-* selectors must exist."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-TM-16", "subject": "math-algebra", "grade": 8})
    matches = re.findall(r'\[data-theme="dark"\]\s+\.gb-tm-', html)
    assert len(matches) >= 15, (
        f"Only {len(matches)} dark-mode overrides for .gb-tm-* found — "
        "expected ≥15. TM panel will look broken in dark mode."
    )


# ---------------------------------------------------------------------------
# 17. No answer-leak attrs in panel markup
# ---------------------------------------------------------------------------


def test_tm_no_answer_leak_attrs_in_panel():
    """The #gb-panel-tm HTML block must contain zero data-correct / data-answer /
    data-expected attributes — those are the server-side answer pipeline only."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-TM-17", "subject": "math-algebra", "grade": 8})
    # Slice the panel block
    panel_match = re.search(
        r'<div class="gb-game-panel enter-right" id="gb-panel-tm">([\s\S]*?)</div>\s*<!-- Sub-game 4',
        html,
    )
    assert panel_match, "#gb-panel-tm block could not be isolated"
    panel_body = panel_match.group(1)
    for attr in ("data-correct", "data-answer", "data-expected"):
        assert attr not in panel_body, (
            f"'{attr}' found inside #gb-panel-tm markup — answer-leak risk. "
            "Correct answers must only travel via the grading endpoint response."
        )


# ---------------------------------------------------------------------------
# 18. No runtime mode toggle inside TM panel
# ---------------------------------------------------------------------------


def test_tm_no_runtime_mode_toggle():
    """TM design has no mode chip — no gb-tm-mode-btn or gb-tm-mode-toggle
    should exist in the panel. Mode is implicit (always matching)."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-TM-18", "subject": "math-algebra", "grade": 8})
    assert "gb-tm-mode-btn" not in html, (
        ".gb-tm-mode-btn found — TM has no student-facing mode toggle"
    )
    assert "gb-tm-mode-toggle" not in html, (
        ".gb-tm-mode-toggle found — TM has no student-facing mode toggle"
    )


# ---------------------------------------------------------------------------
# 19. No answer-leak setAttribute calls in TM JS layer
# ---------------------------------------------------------------------------


def test_tm_answer_leak_guard_at_js_layer():
    """TM JS must never call setAttribute('data-correct'/'data-answer'/'data-expected')
    on tiles — the only allowed answer-reveal path is resp.hint from the endpoint."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-TM-19", "subject": "math-algebra", "grade": 8})
    forbidden = [
        "setAttribute('data-correct'",
        "setAttribute('data-answer'",
        "setAttribute('data-expected'",
    ]
    for call in forbidden:
        assert call not in html, (
            f"JS calls `{call}` — answer-leak risk in TM tiles. "
            "Correct answers must only come from the grading endpoint response."
        )


# ---------------------------------------------------------------------------
# 20. Legacy MM classes still present (CSS not deleted)
# ---------------------------------------------------------------------------


LEGACY_MM_CLASSES = [
    ".gb-mm-grid",
    ".gb-mm-card",
    ".gb-mm-front-face",
    ".gb-mm-back-face",
    ".gb-mm-confirm-box",
    ".gb-mm-confirm-input",
    ".gb-mm-status",
    ".gb-mm-win-banner",
]


@pytest.mark.parametrize("cls", LEGACY_MM_CLASSES)
def test_tm_legacy_mm_classes_untouched(cls):
    """Legacy MM CSS classes must remain in the stylesheet — removing them
    would break old homework previews that still render MM panel markup."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-TM-20", "subject": "math-algebra", "grade": 8})
    assert cls in html, (
        f"Legacy MM class `{cls}` is missing from the stylesheet — "
        "it must be preserved even though TM replaced MM at slot 2."
    )
