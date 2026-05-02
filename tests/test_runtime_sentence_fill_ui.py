"""Regression tests for the Sentence Fill runtime UI (frontend side).

Pins the contract between this PR's frontend work and the backend's PR #132:
- Panel markup hooks (#gb-panel-sf + 11+ child IDs)
- JS state machine functions are present and wired
- Sub-slot 6 lives in gbActiveGameOrder + GB_SUBGAME_TO_SUBPHASE
- Exit sentinel was bumped from 6 → 99 (so slot 6 doesn't collide with exit)
- Dark-mode CSS overrides exist for SF surfaces
- i18n keys (sf.*) exist in all three runtime languages (uz/ru/en)
- gbSFFinish calls gbAdvanceFromGame(6, 'gb-panel-sf')
- gbSFGradeBlank uses phase='sentence-fill' on /api/ai/check-answer

These pins protect against regressions where someone reverts wiring or
renames a selector and the rest of the codebase silently keeps "passing".

Companion to:
- tests/test_runtime_sentence_fill_panel.py (backend injector + answer-leak)
- tests/test_optional_games.py (registry + advance hook for all 7 games)
"""
from __future__ import annotations

import re

from server.services.injector import inject


def _empty_content():
    return {
        "meta": {"title": "SF UI Smoke", "subject_display": "X", "section": "", "cefr_level": ""},
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
        "boss_questions": [],
        "real_life": None,
        "reading": None,
        "consolidation": None,
        "reflection": None,
    }


# ---------------------------------------------------------------------------
# Markup hooks — JS depends on every one of these IDs / classes
# ---------------------------------------------------------------------------


def test_sf_panel_markup_hooks_present():
    """Every ID/class the JS state machine writes into must be in the
    template. If any of these go missing, gbInitSF / gbSFRenderPassage /
    gbSFApplyMode would silently fail at runtime."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-SF-UI", "subject": "math-algebra", "grade": 8})
    required_ids = [
        "gb-panel-sf",
        "gb-sf-eyebrow",
        "gb-sf-dots",
        "gb-sf-progress-label",
        "gb-sf-chain-label",
        "gb-sf-eyebrow-meta",
        "gb-sf-mode-chip",
        "gb-sf-xp-pill",
        "gb-sf-title",
        "gb-sf-subtitle",
        "gb-sf-passage-label",
        "gb-sf-cloze-text",
        "gb-sf-microcopy",
        "gb-sf-word-bank",
        "gb-sf-recall-grid",
        "gb-sf-keyboard-hint",
        "gb-sf-result-card",
        "gb-sf-result-title",
        "gb-sf-result-text",
        "gb-sf-score-label",
        "gb-sf-score-value",
        "gb-sf-toast",
    ]
    for el_id in required_ids:
        assert f'id="{el_id}"' in html, (
            f"#{el_id} hook is missing from the SF panel — JS state machine "
            "depends on it. Was the markup edited or replaced?"
        )


def test_sf_panel_has_no_runtime_mode_toggle():
    """Mode is author-set in the builder (per content_json item). The
    runtime must NOT expose a student-facing toggle. Pins that the old
    segmented control + per-mode buttons are gone for good."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-SF-NT", "subject": "math-algebra", "grade": 8})
    forbidden_ids = ["gb-sf-segmented", "gb-sf-mode-bank", "gb-sf-mode-recall"]
    for el_id in forbidden_ids:
        assert f'id="{el_id}"' not in html, (
            f"#{el_id} found in template — runtime mode toggle should have been "
            "removed. Mode is author-set in the builder, not student-toggleable."
        )
    assert "gb-sf-mode-btn" not in html, (
        "`.gb-sf-mode-btn` class found — toggle button styling should have been "
        "removed in favor of read-only `.gb-sf-mode-chip`."
    )


def test_sf_mode_chip_is_read_only_span():
    """The mode chip must be a `<span>`, not a `<button>` or other
    interactive element. Mirrors AQ tier-eyebrow pattern."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-SF-CH", "subject": "math-algebra", "grade": 8})
    assert re.search(
        r'<span\s+class="gb-sf-mode-chip"\s+id="gb-sf-mode-chip"',
        html,
    ), "gb-sf-mode-chip must be a non-interactive <span>"


def test_sf_panel_uses_enter_right_class():
    """The Stage-5 panel transition relies on .enter-right being on every
    game panel before activation. Catches the regression where SF reverts
    to a static `display: none` placeholder."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-SF-EH", "subject": "math-algebra", "grade": 8})
    assert re.search(r'class="gb-game-panel enter-right"\s+id="gb-panel-sf"', html), (
        "SF panel must have class 'gb-game-panel enter-right' before mount — "
        "otherwise the Stage-5 sliding transition won't run."
    )


def test_no_sf_placeholder_leak():
    """The original backend placeholder ('SENTENCE FILL — PLACEHOLDER')
    must NOT appear once the frontend ships — that text is a sign someone
    re-introduced the stub block."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-SF-PL", "subject": "math-algebra", "grade": 8})
    assert "SENTENCE FILL — PLACEHOLDER" not in html
    assert "gb-sf-placeholder" not in html


# ---------------------------------------------------------------------------
# JS state machine — every required function
# ---------------------------------------------------------------------------


REQUIRED_SF_FUNCTIONS = [
    "gbInitSF",
    "gbSFRenderItem",
    "gbSFRenderPassage",
    "gbSFApplyMode",
    "gbSFSelectBlank",
    "gbSFPickWord",
    "gbSFSyncUsedWords",
    "gbSFAction",
    "gbSFShowToast",
    "gbSFFinish",
    "gbSFGradeBlank",
    "gbSetButtonForSF",
]


def test_sf_state_machine_functions_present():
    """All 12 SF JS functions must be defined. Any one missing means a
    runtime error on first mount."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-SF-FN", "subject": "math-algebra", "grade": 8})
    for fn in REQUIRED_SF_FUNCTIONS:
        assert f"function {fn}(" in html, (
            f"SF state machine function {fn}() is missing — was it deleted?"
        )


def test_sf_grade_blank_posts_phase_sentence_fill():
    """gbSFGradeBlank must POST to /api/ai/check-answer with
    phase='sentence-fill'. Backend Chunk B routes on this phase string."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-SF-PH", "subject": "math-algebra", "grade": 8})
    grade_fn = re.search(
        r"async function gbSFGradeBlank\([^)]*\)\s*\{[\s\S]*?(?=\n\s{8}(?:async\s+)?function )",
        html,
    )
    assert grade_fn, "gbSFGradeBlank function body not found"
    body = grade_fn.group(0)
    assert "/api/ai/check-answer" in body, "gbSFGradeBlank must POST to /api/ai/check-answer"
    assert "phase: 'sentence-fill'" in body, (
        "gbSFGradeBlank must send phase='sentence-fill' — backend routes on it."
    )
    assert "homework_id" in body, (
        "gbSFGradeBlank must send homework_id — Chunk B requires it."
    )


# ---------------------------------------------------------------------------
# Registry / lifecycle wiring
# ---------------------------------------------------------------------------


def test_sf_registered_at_slot_6():
    """gbActiveGameOrder must include {id:'sf', sub:6, ...}. Without this,
    the registry walk never reaches SF and the game is dead code."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-SF-R6", "subject": "math-algebra", "grade": 8})
    assert re.search(
        r"id:\s*'sf',\s*sub:\s*6,\s*init:\s*gbInitSF,\s*panel:\s*'gb-panel-sf'",
        html,
    ), "Sentence Fill must be registered at sub:6 in gbActiveGameOrder()"


def test_sf_subphase_map_slot_6_is_sentence_fill():
    """GB_SUBGAME_TO_SUBPHASE[6] must map to 'sentence-fill' so the tutor
    chat picks up the right phase context when SF is active."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-SF-SUB", "subject": "math-algebra", "grade": 8})
    map_match = re.search(r"const GB_SUBGAME_TO_SUBPHASE\s*=\s*\{([^}]+)\}", html)
    assert map_match, "GB_SUBGAME_TO_SUBPHASE map not found"
    body = map_match.group(1)
    assert re.search(r"6:\s*'sentence-fill'", body), (
        "GB_SUBGAME_TO_SUBPHASE[6] must be 'sentence-fill'"
    )


def test_exit_sentinel_bumped_to_99():
    """The Stage-5 exit sentinel was 6 (collided with SF's slot). It must
    now be 99 (or any non-game-slot value). If it's still 6, advancing past
    the last game would land in the SF branch instead of exiting."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-SF-EX", "subject": "math-algebra", "grade": 8})
    assert "gbState.subGame = 99;" in html, (
        "Exit-Stage-5 sentinel must be 99 (was 6 — collided with SF slot 6)"
    )
    assert "gbState.subGame === 99" in html, (
        "gbHandleAction must dispatch on subGame===99 to exit Stage 5"
    )


def test_sf_handler_dispatch_branch_present():
    """gbHandleAction must dispatch SF actions when subGame===6 and
    advance via gbAdvanceFromGame on completion."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-SF-H", "subject": "math-algebra", "grade": 8})
    handler = re.search(r"function gbHandleAction\(\)\s*\{[\s\S]*?\n\s{8}\}", html)
    assert handler, "gbHandleAction not found"
    body = handler.group(0)
    assert "gbState.subGame === 6" in body, "gbHandleAction must branch on subGame===6"
    assert "gbAdvanceFromGame(6, 'gb-panel-sf')" in body, (
        "gbHandleAction's SF branch must call gbAdvanceFromGame(6, 'gb-panel-sf') on complete"
    )
    assert "gbSFAction()" in body, "gbHandleAction must delegate to gbSFAction()"


# ---------------------------------------------------------------------------
# i18n — sf.* keys must exist for uz / ru / en
# ---------------------------------------------------------------------------


def test_sf_i18n_keys_present_in_all_languages():
    """The `sf.*` keys are read at runtime via RT('sf.*'). They must exist
    in all three RUNTIME_LABELS dicts (uz, ru, en) — otherwise UI shows the
    raw key string."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-SF-I18", "subject": "math-algebra", "grade": 8})
    sf_keys = [
        "sf.title", "sf.eyebrow", "sf.passage_label",
        "sf.mode_word_bank", "sf.mode_free_recall",
        "sf.subtitle_bank", "sf.subtitle_recall",
        "sf.btn_check", "sf.btn_next",
        "sf.result_perfect", "sf.result_partial",
        "sf.toast_perfect", "sf.toast_partial", "sf.toast_locked",
        "sf.score_label", "sf.keyboard_hint", "sf.chain_label",
        "game.sf",
    ]
    for k in sf_keys:
        # Each key must appear at least 3 times (uz + ru + en blocks).
        count = html.count(f"'{k}'")
        assert count >= 3, (
            f"i18n key '{k}' appears {count} times — expected ≥3 (uz+ru+en). "
            "Was a translation block reverted?"
        )


# ---------------------------------------------------------------------------
# Dark mode coverage
# ---------------------------------------------------------------------------


def test_sf_dark_mode_overrides_present():
    """Dark mode must override the key SF surfaces (panel cards, blanks,
    inputs). If these are missing the SF panel inverts ugly in dark mode."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-SF-DM", "subject": "math-algebra", "grade": 8})
    required_dark_selectors = [
        '[data-theme="dark"] .gb-sf-blank',
        '[data-theme="dark"] .gb-sf-main-card',
        '[data-theme="dark"] .gb-sf-control-card',
        '[data-theme="dark"] .gb-sf-result-card',
    ]
    for sel in required_dark_selectors:
        assert sel in html, f"Dark-mode override missing: `{sel}`"


# ---------------------------------------------------------------------------
# Answer-leak guard at the JS layer (markup + injector covered separately)
# ---------------------------------------------------------------------------


def test_sf_js_does_not_read_data_correct_attrs():
    """The frontend must never read data-correct/data-answer/data-expected
    on SF blanks. The only path the client learns the right answer is the
    server's response on a 2nd-attempt-wrong reveal."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-SF-LK", "subject": "math-algebra", "grade": 8})
    # Find the SF block (between gbWCFinish and gbInitMM).
    block = re.search(r"function gbWCFinish\(\)[\s\S]*?function gbInitMM", html)
    assert block, "could not isolate SF JS block"
    body = block.group(0)
    forbidden = ["data-correct", "data-answer", "data-expected"]
    for attr in forbidden:
        assert attr not in body, (
            f"SF JS block reads or writes `{attr}` — answer-leak risk. "
            "The only allowed answer-reveal path is result.correct_answer "
            "from the grading endpoint on lock=true."
        )
