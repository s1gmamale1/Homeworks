"""Regression tests for the Tic Tac Toe runtime UI (frontend polish PR).

Pins the contract between this PR's frontend work and the backend's
phase=ttt + phase=ttt-session endpoints (server/routes/ai.py:_check_answer_ttt
and _check_answer_ttt_session, shipped on PR #149):

- All required IDs preserved (#gb-panel-ttt + game-break dispatch hook
  preserved so registry keeps working).
- New required IDs (#gb-ttt-hero, #gb-ttt-stats, #gb-ttt-draws,
  #gb-ttt-losses, #gb-ttt-correct, #gb-ttt-turn-pill, #gb-ttt-board,
  #gb-ttt-question-card, #gb-ttt-question, #gb-ttt-options,
  #gb-ttt-feedback, #gb-ttt-result-card, #gb-ttt-session-card).
- gbState.ttt initial-shape literal carries new fields (sessionId, busy,
  complete, games, gameNum, draws, losses, correct, pendingCellIdx,
  currentItemIdx, currentItemId).
- All new + preserved functions present (gbInitTTT, gbTTTRender,
  gbTTTPickItem, gbTTTCellClick, gbTTTShowQuestion, gbTTTOptionClick,
  gbTTTCheckAnswer, gbTTTHandleResolve, gbTTTAfterPlayerMove,
  gbTTTAIMove, gbTTTEndGame, gbTTTNextGame, gbTTTSessionEnd,
  gbTTTSessionFinalize, gbTTTAction); preserved minimax helpers
  (gbTTTWinner, gbTTTBoardFull, gbTTTScore, gbTTTBestMove).
- Old gbTTTAnswer(picked, correct, btnEl) signature is GONE (client no
  longer reads `correct` — server-only since side-disjoint injector).
- Single network swap-points: gbTTTCheckAnswer → /api/ai/check-answer
  with phase=ttt + homework_id field (NOT hwId); gbTTTSessionFinalize →
  /api/ai/check-answer with phase=ttt-session.
- ctx.hwId canonical 3-key chain in both adapters (TM #140 idiom).
- Answer-leak guard: rendered GB_TTT JS literal contains zero
  `correct` / `distractors` keys after side-disjoint serialization.
- No client-side correctness logic in new gbTTT* function bodies.
- i18n keys (ttt.*) present in all 3 runtime languages (uz/ru/en).
- Dark-mode CSS parity (≥10 [data-theme="dark"] .gb-ttt-* selectors).
- Wrong-no-mercy uses random-empty-cell placement; mercy uses
  pendingCellIdx (intended cell).
- Foundation stub `const GB_TTT = []` preserved (regex-replaced at inject).
- Game-break dispatch hook `gbAdvanceFromGame(5, 'gb-panel-ttt')` intact.

Companion to:
- tests/test_runtime_final_boss_ui.py (FB #147 reference shape)
- tests/test_runtime_tile_match_ui.py (TM #140 patterns)
- tests/test_ttt_check_answer.py (backend route contract)
- tests/test_ttt_injector.py (side-disjoint serialization)
"""
from __future__ import annotations
from pathlib import Path

import json
import re

import pytest

from server.services.injector import inject

_REPO_ROOT = Path(__file__).resolve().parent.parent
_RUNTIME_EXTRAS = (
    (_REPO_ROOT / "server" / "template" / "js" / "perfect_homework.js").read_text(encoding="utf-8") + "\n" +
    (_REPO_ROOT / "server" / "template" / "static" / "css" / "perfect_homework.css").read_text(encoding="utf-8") + "\n" +
    (_REPO_ROOT / "server" / "template" / "static" / "js" / "tutor.js").read_text(encoding="utf-8")
)

def _inject_full(*args, **kwargs):
    return inject(*args, **kwargs) + "\n" + _RUNTIME_EXTRAS



# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _empty_content() -> dict:
    return {
        "meta": {"title": "TTT UI Smoke", "subject_display": "X", "section": "", "cefr_level": ""},
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
        "boss_meta": None,
        "real_life": None,
        "real_life_challenge": None,
        "reading": None,
        "consolidation": None,
        "reflection": None,
    }


def _ttt_items_fixture() -> list:
    """TTT items WITH server-only fields. After inject(), the GB_TTT literal
    must be stripped (correct + distractors gone — side-disjoint serialization)."""
    return [
        {
            "id": "ttt-1",
            "q": "What is 7 x 8?",
            "correct": "56",
            "distractors": ["54", "48", "63"],
        },
        {
            "id": "ttt-2",
            "q": "Which fraction equals 3/6?",
            "correct": "1/2",
            "distractors": ["2/5", "4/9", "5/8"],
        },
    ]


@pytest.fixture(scope="module")
def html_empty() -> str:
    return _inject_full(
        _empty_content(),
        runtime_context={"hw_id": "HW-TTT-EMPTY", "subject": "math", "grade": 8},
    )


@pytest.fixture(scope="module")
def html_with_ttt() -> str:
    body = _empty_content()
    body["gb_ttt"] = _ttt_items_fixture()
    return _inject_full(
        body,
        runtime_context={"hw_id": "HW-TTT-1", "subject": "math", "grade": 8},
    )


# ---------------------------------------------------------------------------
# 1. All required IDs present
# ---------------------------------------------------------------------------


REQUIRED_IDS = [
    "gb-panel-ttt",          # game-break registry depends on this
    "gb-ttt-hero",
    "gb-ttt-stats",
    "gb-ttt-draws",
    "gb-ttt-losses",
    "gb-ttt-correct",
    "gb-ttt-turn-pill",
    "gb-ttt-board",
    "gb-ttt-question-card",
    "gb-ttt-question",
    "gb-ttt-options",
    "gb-ttt-feedback",
    "gb-ttt-result-card",
    "gb-ttt-session-card",
    "gb-ttt-counter",        # legacy back-compat
]


@pytest.mark.parametrize("id_", REQUIRED_IDS)
def test_required_id_present(html_empty: str, id_: str):
    assert f'id="{id_}"' in html_empty, f"required id #{id_} missing"


# ---------------------------------------------------------------------------
# 2. gbState.ttt initial-shape literal
# ---------------------------------------------------------------------------


def test_gbstate_ttt_initial_shape(html_empty: str):
    m = re.search(r"ttt\s*:\s*\{([^}]*)\}", html_empty)
    assert m, "gbState.ttt literal missing"
    body = m.group(1)
    required = [
        "sessionId", "busy", "complete", "games", "gameNum",
        "draws", "losses", "correct",
        "pendingCellIdx", "currentItemIdx", "currentItemId",
    ]
    for name in required:
        assert re.search(rf"\b{name}\s*:", body), (
            f"gbState.ttt must declare field `{name}` (got: {body[:200]})"
        )


# ---------------------------------------------------------------------------
# 3. All required functions present
# ---------------------------------------------------------------------------


REQUIRED_FUNCTIONS = [
    # New / rewritten state machine
    "gbInitTTT",
    "gbTTTRender",
    "gbTTTPickItem",
    "gbTTTCellClick",
    "gbTTTShowQuestion",
    "gbTTTOptionClick",
    "gbTTTCheckAnswer",
    "gbTTTHandleResolve",
    "gbTTTAfterPlayerMove",
    "gbTTTAIMove",
    "gbTTTEndGame",
    "gbTTTNextGame",
    "gbTTTSessionEnd",
    "gbTTTSessionFinalize",
    "gbTTTAction",
    # Preserved minimax helpers
    "gbTTTWinner",
    "gbTTTBoardFull",
    "gbTTTScore",
    "gbTTTBestMove",
]


@pytest.mark.parametrize("fn", REQUIRED_FUNCTIONS)
def test_required_function_present(html_empty: str, fn: str):
    pat = re.compile(
        rf"\bfunction\s+{re.escape(fn)}\s*\(|\basync\s+function\s+{re.escape(fn)}\s*\("
    )
    assert pat.search(html_empty), f"required JS function `{fn}` missing"


# ---------------------------------------------------------------------------
# 4. Game-break dispatch hook intact
# ---------------------------------------------------------------------------


def test_game_break_dispatch_hook_intact(html_empty: str):
    pat = re.compile(r"gbAdvanceFromGame\s*\(\s*5\s*,\s*['\"]gb-panel-ttt['\"]")
    matches = pat.findall(html_empty)
    assert len(matches) >= 1, (
        "gbAdvanceFromGame(5, 'gb-panel-ttt') must remain (game-break registry hook)"
    )


# ---------------------------------------------------------------------------
# 5. Single network swap-point — phase=ttt POST + homework_id field
# ---------------------------------------------------------------------------


def _function_body(html: str, fn_name: str) -> str:
    """Extract the body of a top-level function declaration (template indent = 8)."""
    pat = re.compile(
        rf"(?:async\s+)?function\s+{re.escape(fn_name)}\s*\([^)]*\)\s*\{{"
    )
    m = pat.search(html)
    assert m, f"{fn_name} not found"
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


def test_check_answer_endpoint_phase_ttt(html_empty: str):
    body = _function_body(html_empty, "gbTTTCheckAnswer")
    assert "/api/ai/check-answer" in body, (
        "gbTTTCheckAnswer must POST to /api/ai/check-answer"
    )
    assert re.search(r"phase\s*:\s*['\"]ttt['\"]", body), (
        "gbTTTCheckAnswer payload must set phase: 'ttt'"
    )
    assert re.search(r"method\s*:\s*['\"]POST['\"]", body), (
        "gbTTTCheckAnswer must use POST"
    )
    # Body MUST use `homework_id` field name, NOT `hwId` (matches backend req model).
    assert re.search(r"homework_id\s*:", body), (
        "gbTTTCheckAnswer body must include `homework_id` field"
    )


# ---------------------------------------------------------------------------
# 6. Session network swap-point — phase=ttt-session
# ---------------------------------------------------------------------------


def test_session_finalize_endpoint(html_empty: str):
    body = _function_body(html_empty, "gbTTTSessionFinalize")
    assert "/api/ai/check-answer" in body, (
        "gbTTTSessionFinalize must POST to /api/ai/check-answer"
    )
    assert re.search(r"phase\s*:\s*['\"]ttt-session['\"]", body), (
        "gbTTTSessionFinalize payload must set phase: 'ttt-session'"
    )
    assert re.search(r"method\s*:\s*['\"]POST['\"]", body), (
        "gbTTTSessionFinalize must use POST"
    )
    assert re.search(r"results\s*:", body), (
        "gbTTTSessionFinalize body must include `results` field"
    )


# ---------------------------------------------------------------------------
# 7. ctx.hwId canonical 3-key chain
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fn", ["gbTTTCheckAnswer", "gbTTTSessionFinalize"])
def test_ctx_hwid_priority_chain(html_empty: str, fn: str):
    body = _function_body(html_empty, fn)
    pat = re.compile(
        r"ctx\.hwId\s*\|\|\s*ctx\.homework_id\s*\|\|\s*ctx\.homeworkId"
    )
    assert pat.search(body), (
        f"{fn} must read homework id via the canonical 3-key chain "
        f"(ctx.hwId || ctx.homework_id || ctx.homeworkId) — TM #140 / SF lesson"
    )


# ---------------------------------------------------------------------------
# 8. Old gbTTTAnswer(picked, correct, btnEl) signature is GONE
# ---------------------------------------------------------------------------


def test_old_gbtttanswer_signature_removed(html_empty: str):
    pat = re.compile(
        r"function\s+gbTTTAnswer\s*\(\s*picked\s*,\s*correct\s*,\s*btnEl\s*\)"
    )
    matches = pat.findall(html_empty)
    assert len(matches) == 0, (
        "Old gbTTTAnswer(picked, correct, btnEl) must be removed — its `correct` "
        "param is now stripped server-side. Found: " + str(matches)
    )


# ---------------------------------------------------------------------------
# 9. Answer-leak guard — rendered GB_TTT contains zero correct/distractors keys
# ---------------------------------------------------------------------------


def _extract_gb_ttt_literal(html: str) -> list:
    """Pull out the substituted const GB_TTT = [...] literal."""
    m = re.search(r"const\s+GB_TTT\s*=\s*(\[.*?\]);", html, re.DOTALL)
    assert m, "GB_TTT assignment missing"
    return json.loads(m.group(1))


def test_gb_ttt_no_answer_leak(html_with_ttt: str):
    parsed = _extract_gb_ttt_literal(html_with_ttt)
    BANNED = {"correct", "distractors"}

    def walk(obj, path="$"):
        if isinstance(obj, dict):
            for k, v in obj.items():
                assert k not in BANNED, (
                    f"server-only field `{k}` leaked into GB_TTT at {path}"
                )
                walk(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                walk(item, f"{path}[{i}]")

    walk(parsed)
    assert len(parsed) == 2, f"two TTT items expected, got {len(parsed)}"
    # Wire format must be exactly {id, q, options}.
    for item in parsed:
        assert set(item.keys()) == {"id", "q", "options"}, (
            f"GB_TTT item keys must be exactly id/q/options, got {set(item.keys())}"
        )
        assert isinstance(item["options"], list)
        assert len(item["options"]) == 4


# ---------------------------------------------------------------------------
# 10. No client-side correctness logic in new gbTTT* function bodies
# ---------------------------------------------------------------------------


def _new_ttt_function_bodies(html: str) -> str:
    """Concatenate every gbTTT* state-machine function body for grep assertions.

    Excludes pure logic helpers (gbTTTWinner, gbTTTBoardFull, gbTTTScore,
    gbTTTBestMove) which operate on the cell board mark, not the question.
    """
    chunks = []
    new_funcs = [
        "gbInitTTT", "gbTTTRender", "gbTTTPickItem",
        "gbTTTCellClick", "gbTTTShowQuestion", "gbTTTOptionClick",
        "gbTTTCheckAnswer", "gbTTTHandleResolve", "gbTTTAfterPlayerMove",
        "gbTTTAIMove", "gbTTTEndGame", "gbTTTNextGame",
        "gbTTTSessionEnd", "gbTTTSessionFinalize", "gbTTTAction",
    ]
    for fn in new_funcs:
        pat = re.compile(
            rf"(?:async\s+)?function\s+{re.escape(fn)}\s*\([^)]*\)\s*\{{"
        )
        for m in pat.finditer(html):
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
            chunks.append(html[start:i])
    assert chunks, "no new gbTTT* function bodies found"
    return "\n".join(chunks)


def test_no_client_side_correctness_logic(html_empty: str):
    bodies = _new_ttt_function_bodies(html_empty)
    # New code must not reference server-only answer fields on items.
    for forbidden in (
        "item.correct", "item.distractors",
        "q.correct", "q.distractors",
        ".correct ?", ".correct||", ".correct =",
    ):
        # We allow `correct` as an arbitrary local var name (e.g. is_correct
        # destructure or `correct_value` from the response payload), but item
        # field reads via dot-access on a question are forbidden.
        if forbidden.startswith(("item.", "q.")):
            assert forbidden not in bodies, (
                f"new gbTTT* JS must not reference `{forbidden}` (server-only field on item)"
            )
    # Hard guard: no `q.correct` / `q.distractors` style lookups.
    assert not re.search(r"\b(?:item|q|raw)\.correct\b", bodies), (
        "new gbTTT* JS must not read `.correct` from an item/question (server-only)"
    )
    assert not re.search(r"\b(?:item|q|raw)\.distractors\b", bodies), (
        "new gbTTT* JS must not read `.distractors` from an item/question (server-only)"
    )


# ---------------------------------------------------------------------------
# 11. i18n keys × 3 languages
# ---------------------------------------------------------------------------


REQUIRED_I18N_KEYS = [
    "ttt.heroTitle",
    "ttt.subtitle",
    "ttt.draws",
    "ttt.losses",
    "ttt.correct",
    "ttt.boardCopy",
    "ttt.turnYour",
    "ttt.turnAI",
    "ttt.turnAnswer",
    "ttt.feedbackCorrect",
    "ttt.feedbackWrong",
    "ttt.feedbackMercy",
    "ttt.resultWinTitle",
    "ttt.resultWinText",
    "ttt.resultDrawTitle",
    "ttt.resultDrawText",
    "ttt.resultLossTitle",
    "ttt.resultLossText",
    "ttt.sessionStrongTitle",
    "ttt.sessionStrongText",
    "ttt.sessionSolidTitle",
    "ttt.sessionSolidText",
    "ttt.sessionFailedTitle",
    "ttt.sessionFailedText",
    "ttt.dockTap",
    "ttt.dockAnswer",
    "ttt.dockNext",
    "ttt.dockResult",
    "ttt.dockComplete",
    "ttt.duolingoToast",
]


@pytest.mark.parametrize("key", REQUIRED_I18N_KEYS)
def test_i18n_key_in_all_three_languages(html_empty: str, key: str):
    """Each new key must appear ≥3 times (uz/ru/en blocks)."""
    pat = re.compile(r"['\"]" + re.escape(key) + r"['\"]\s*:")
    matches = pat.findall(html_empty)
    assert len(matches) >= 3, (
        f"i18n key `{key}` must be defined in uz/ru/en (found {len(matches)})"
    )


# ---------------------------------------------------------------------------
# 12. Dark-mode CSS parity (≥10 selectors)
# ---------------------------------------------------------------------------


def test_dark_mode_ttt_selectors_at_least_10(html_empty: str):
    pat = re.compile(r'\[data-theme="dark"\]\s+\.gb-ttt-')
    matches = pat.findall(html_empty)
    assert len(matches) >= 10, (
        f"dark-mode parity needs ≥10 [data-theme=\"dark\"] .gb-ttt- selectors; found {len(matches)}"
    )


# ---------------------------------------------------------------------------
# 13. Result card structure — outcome title + text slots
# ---------------------------------------------------------------------------


def test_result_card_children(html_empty: str):
    """gb-ttt-result-card must contain title + text children."""
    m = re.search(
        r'id="gb-ttt-result-card"[^>]*>(.*?)</section>',
        html_empty,
        re.DOTALL,
    )
    assert m, "gb-ttt-result-card section not found"
    inner = m.group(1)
    assert 'id="gb-ttt-result-title"' in inner, (
        "gb-ttt-result-card must contain #gb-ttt-result-title"
    )
    assert 'id="gb-ttt-result-text"' in inner, (
        "gb-ttt-result-card must contain #gb-ttt-result-text"
    )


# ---------------------------------------------------------------------------
# 14. Session card structure — mastery tier + xp slots
# ---------------------------------------------------------------------------


def test_session_card_children(html_empty: str):
    m = re.search(
        r'id="gb-ttt-session-card"[^>]*>(.*?)</section>',
        html_empty,
        re.DOTALL,
    )
    assert m, "gb-ttt-session-card section not found"
    inner = m.group(1)
    for child in ("gb-ttt-session-title", "gb-ttt-session-text",
                  "gb-ttt-session-xp", "gb-ttt-mastery-pill",
                  "gb-ttt-duolingo-toast"):
        assert f'id="{child}"' in inner, (
            f"gb-ttt-session-card must contain #{child}"
        )


# ---------------------------------------------------------------------------
# 15. Wrong-no-mercy uses random-empty-cell placement
# ---------------------------------------------------------------------------


def test_wrong_no_mercy_uses_random_empty(html_empty: str):
    """gbTTTHandleResolve's wrong-no-mercy branch must scatter to random empty."""
    body = _function_body(html_empty, "gbTTTHandleResolve")
    # Look for random-empty-cell pattern (board[i] check + Math.random index).
    has_empty_filter = bool(re.search(
        r"(emptyIndices|empties|filter[^;]*board\[)",
        body,
    ))
    has_math_random = "Math.random" in body
    assert has_empty_filter, (
        "gbTTTHandleResolve must compute empty-cell list for scatter placement"
    )
    assert has_math_random, (
        "gbTTTHandleResolve must use Math.random() for scatter placement"
    )


# ---------------------------------------------------------------------------
# 16. Mercy bounce uses pendingCellIdx (intended cell)
# ---------------------------------------------------------------------------


def test_mercy_bounce_uses_pending_cell(html_empty: str):
    """When mercy = true, X lands on the intended cell (pendingCellIdx)."""
    body = _function_body(html_empty, "gbTTTHandleResolve")
    # Some branch must read mercy from response and use pendingCellIdx for placement.
    assert "mercy" in body, "gbTTTHandleResolve must read mercy from response"
    assert "pendingCellIdx" in body, (
        "gbTTTHandleResolve must reference pendingCellIdx (intended cell)"
    )
    # The mercy branch must place on intended cell — look for both being assigned together.
    has_correct_or_mercy_branch = bool(re.search(
        r"(isCorrect\s*\|\|\s*isMercy|isMercy\s*\|\|\s*isCorrect|mercy\s*\)\s*\{\s*[^}]*pendingCellIdx)",
        body,
    ))
    assert has_correct_or_mercy_branch, (
        "gbTTTHandleResolve must route correct OR mercy to pendingCellIdx placement"
    )


# ---------------------------------------------------------------------------
# 17. Foundation stub `const GB_TTT = []` regex-replaceable
# ---------------------------------------------------------------------------


def test_gb_ttt_foundation_stub_replaceable(html_empty: str, html_with_ttt: str):
    """The empty homework path renders an empty array; non-empty path renders items."""
    empty_match = re.search(r"const\s+GB_TTT\s*=\s*\[\s*\];", html_empty)
    assert empty_match, "const GB_TTT = []; missing in empty render"
    populated = _extract_gb_ttt_literal(html_with_ttt)
    assert len(populated) > 0, "GB_TTT must be populated when gb_ttt has items"


# ---------------------------------------------------------------------------
# 18. async functions — gbTTTOptionClick, gbTTTCheckAnswer, gbTTTSessionFinalize
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fn", [
    "gbTTTOptionClick",
    "gbTTTCheckAnswer",
    "gbTTTSessionFinalize",
    "gbTTTSessionEnd",
])
def test_function_is_async(html_empty: str, fn: str):
    pat = re.compile(rf"async\s+function\s+{re.escape(fn)}\s*\(")
    assert pat.search(html_empty), (
        f"{fn} must be declared async (it awaits a fetch)"
    )


# ---------------------------------------------------------------------------
# 19. Cell rendering uses data-cell-idx attribute (test contract)
# ---------------------------------------------------------------------------


def test_cells_carry_data_cell_idx(html_empty: str):
    """Cells must be rendered with data-cell-idx for click delegation parity
    with reference design's data-i."""
    body = _function_body(html_empty, "gbTTTRender")
    assert "data-cell-idx" in body, (
        "gbTTTRender must set data-cell-idx on each cell button"
    )


# ---------------------------------------------------------------------------
# 20. Options carry data-option-value attribute
# ---------------------------------------------------------------------------


def test_options_carry_data_option_value(html_empty: str):
    """Option buttons must be rendered with data-option-value so the
    handler can look up the picked value on resolve."""
    body = _function_body(html_empty, "gbTTTShowQuestion")
    assert "data-option-value" in body, (
        "gbTTTShowQuestion must set data-option-value on each option button"
    )
