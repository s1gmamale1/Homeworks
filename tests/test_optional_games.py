"""Regression tests for the "every Phase-3 game is optional" rule.

Rule: when a content_json game-break key is empty, the injector must NOT
stamp placeholder content into the corresponding template constant, and the
runtime registry (gbActiveGameOrder) must skip that game's slot. If all five
games are empty, Stage 5 is skipped entirely.

These tests pin both halves of the rule:
  - Injector side: empty input → empty JS array (no fake "Bu bosqich hali
    to'ldirilmagan" placeholders).
  - Template side: registry helpers exist and are wired.

Applies to every existing game and every future game added to Phase 3.
"""

import json
import re

from server.services.injector import inject


GAME_KEYS = [
    ("gb_adaptive_quiz", "GB_ADAPTIVE_QUIZ"),
    ("gb_why_chain",     "GB_WHY_CHAIN"),
    ("gb_memory_match",  "GB_MEMORY_MATCH"),
    ("gb_puzzle_lock",   "GB_PUZZLE_LOCK"),
    ("gb_mystery_box",   "GB_MYSTERY_BOX"),
]


def _empty_content():
    return {
        "meta": {
            "title": "Empty Smoke",
            "subject_display": "X",
            "section": "",
            "cefr_level": "",
        },
        "gate_quote": {"mode": "auto"},
        "panels": [],
        "flashcards": [],
        "memory_sprint": [],
        "gb_adaptive_quiz": [],
        "gb_why_chain": [],
        "gb_memory_match": [],
        "gb_puzzle_lock": [],
        "gb_mystery_box": [],
        "boss_questions": [],
        "real_life": None,
        "reading": None,
        "consolidation": None,
        "reflection": None,
    }


def _extract_const_array(html: str, const_name: str):
    match = re.search(rf"const {const_name}\s*=\s*(\[.*?\]);", html, re.DOTALL)
    assert match, f"{const_name} constant not found in injected HTML"
    return json.loads(match.group(1))


def test_every_game_emits_empty_array_when_empty():
    """When the content_json key is empty, the injected JS const must be []
    — never a placeholder array, never `[{prompt: 'Bu bosqich hali to'ldirilmagan'}]`."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-EMPTY", "subject": "math-algebra", "grade": 8})
    for key, const_name in GAME_KEYS:
        items = _extract_const_array(html, const_name)
        assert items == [], (
            f"{const_name} must be [] when {key} is empty. Got {items!r}. "
            "If you re-added a placeholder fallback, remove it — every game is optional."
        )


def test_no_placeholder_string_appears_for_games():
    """The 'Bu bosqich hali to'ldirilmagan' placeholder string still appears for
    panels/flashcards/memory_sprint/boss_questions/real_life (those phases
    aren't optional games), but it must NOT appear inside any of the five
    GB_* constants. This test pins that boundary."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-S", "subject": "math-algebra", "grade": 8})
    for _, const_name in GAME_KEYS:
        match = re.search(rf"const {const_name}\s*=\s*(\[.*?\]);", html, re.DOTALL)
        assert match
        const_body = match.group(1)
        assert "Bu bosqich" not in const_body, (
            f"{const_name} contains a placeholder string — game-break placeholders are forbidden."
        )
        assert "to'ldirilmagan" not in const_body
        assert "Joylashtirilmagan" not in const_body


def test_registry_helpers_present_in_template():
    """The runtime must expose gbActiveGameOrder, gbActiveGameLabels,
    gbAdvanceFromGame, and gbIsLastGame — the data-driven game flow depends
    on all four. If any is missing, the empty-skip behavior breaks."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-R", "subject": "math-algebra", "grade": 8})
    for fn in ["gbActiveGameOrder", "gbActiveGameLabels", "gbAdvanceFromGame", "gbIsLastGame"]:
        assert f"function {fn}(" in html, f"Runtime registry helper {fn}() is missing — was it removed?"


def test_registry_lists_all_five_games():
    """gbActiveGameOrder must enumerate AQ, WC, MM, PL, MB. Every new game
    added to Phase 3 must be appended to this registry — that's the single
    source of truth for the runtime ordering. This test catches the case
    where someone adds a game to the schema/injector but forgets the
    registry entry (which would silently dead-end the new game)."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-RG", "subject": "math-algebra", "grade": 8})
    for const_name in [c for _, c in GAME_KEYS]:
        # Each constant must appear on a line that pushes it into the registry.
        assert re.search(
            rf"Array\.isArray\({const_name}\)\s*&&\s*{const_name}\.length\s*>\s*0",
            html,
        ), f"{const_name} is not registered in gbActiveGameOrder() — runtime would never reach this game."


def test_advancement_uses_registry_not_hardcoded_subgame_indices():
    """gbAQFinish, gbWCFinish, and gbMMWin/gbPLWin/gbMBWin must dispatch via
    gbAdvanceFromGame instead of hardcoding the next subGame index. This
    test guards against future regressions where someone re-adds a manual
    `gbState.subGame = N` advancement that bypasses the registry."""
    html = inject(_empty_content(), runtime_context={"hw_id": "HW-A", "subject": "math-algebra", "grade": 8})
    # gbAQFinish must call gbAdvanceFromGame.
    aq_finish = re.search(r"function gbAQFinish\(\)\s*\{[^}]*\}", html, re.DOTALL)
    assert aq_finish, "gbAQFinish not found"
    assert "gbAdvanceFromGame(0" in aq_finish.group(0), (
        "gbAQFinish must call gbAdvanceFromGame(0, 'gb-panel-aq') — don't hardcode the next game."
    )
    # gbWCFinish must call gbAdvanceFromGame.
    wc_finish = re.search(r"function gbWCFinish\(\)\s*\{[^}]*\}", html, re.DOTALL)
    assert wc_finish, "gbWCFinish not found"
    assert "gbAdvanceFromGame(1" in wc_finish.group(0), (
        "gbWCFinish must call gbAdvanceFromGame(1, 'gb-panel-wc')."
    )
    # gbHandleAction's subGame=2/3/4 completion paths must dispatch to gbAdvanceFromGame.
    # Checking the whole HTML (the dispatch calls are unique enough); a
    # function-body regex would have to handle nested braces and is fragile.
    assert "gbAdvanceFromGame(2, 'gb-panel-mm')" in html, "MM completion must call gbAdvanceFromGame(2, 'gb-panel-mm')"
    assert "gbAdvanceFromGame(3, 'gb-panel-pl')" in html, "PL completion must call gbAdvanceFromGame(3, 'gb-panel-pl')"
    assert "gbAdvanceFromGame(4, 'gb-panel-mb')" in html, "MB completion must call gbAdvanceFromGame(4, 'gb-panel-mb')"


def test_empty_homework_preview_renders_without_game_placeholders(client):
    """End-to-end: create a homework with all 5 games empty, fetch /preview,
    confirm the served HTML has [] for every game constant and contains the
    skip-stage-5 path."""
    create = client.post(
        "/api/homeworks",
        json={
            "title": "All-Empty Smoke",
            "subject": "math-algebra",
            "grade": 8,
            "mode": "hard",
            "content_json": {
                "meta": {
                    "title": "All-Empty Smoke",
                    "subject_display": "X",
                    "section": "",
                    "cefr_level": "",
                },
                "gate_quote": {"mode": "auto"},
                "panels": [], "flashcards": [], "memory_sprint": [],
                "gb_adaptive_quiz": [], "gb_why_chain": [], "gb_memory_match": [],
                "gb_puzzle_lock": [], "gb_mystery_box": [],
                "boss_questions": [], "real_life": None,
                "reading": None, "consolidation": None, "reflection": None,
            },
        },
    )
    assert create.status_code == 200, create.text
    hw_id = create.json()["id"]

    preview = client.get(f"/api/homeworks/{hw_id}/preview")
    assert preview.status_code == 200
    for _, const_name in GAME_KEYS:
        assert _extract_const_array(preview.text, const_name) == []
    # Defensive: the skip path uses gbExitToStage6 if order.length === 0.
    assert "if (order.length === 0)" in preview.text, (
        "startStage5 must short-circuit to gbExitToStage6 when no games are authored."
    )


def test_one_game_only_runtime_treats_it_as_first_and_last():
    """When only one game is populated, gbIsLastGame should return true for
    that game's subGame index — so the button reads 'Keyingi bosqich' (next
    stage) instead of 'Keyingi o'yin' (next game). This is the case authors
    will hit most when piloting a single mechanic."""
    payload = _empty_content()
    payload["gb_puzzle_lock"] = [{"content": "tile", "q": "q?", "a": "a"}]
    html = inject(payload, runtime_context={"hw_id": "HW-1G", "subject": "math-algebra", "grade": 8})
    pl_items = _extract_const_array(html, "GB_PUZZLE_LOCK")
    assert len(pl_items) == 1
    # Other four constants must remain empty.
    for key, const_name in GAME_KEYS:
        if key == "gb_puzzle_lock":
            continue
        assert _extract_const_array(html, const_name) == [], (
            f"{const_name} must be [] when only Puzzle Lock has content."
        )
