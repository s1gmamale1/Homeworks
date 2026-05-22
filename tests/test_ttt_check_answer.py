"""Regression tests for `/api/ai/check-answer` with phase=ttt and phase=ttt-session.

Pins the per-pick + end-of-session grading branches added in T2a of the
Tic Tac Toe backend redesign (TIC_TAC_TOE_BACKEND_PLAN.md §1.3, §1.4, §2.3):

- Correct pick: +xp_correct (default 50), `is_correct: True`, `mercy: False`,
  `correct_value` returned for client-side highlighting.
- Wrong pick + no mercy: 0 XP, `is_correct: False`, `mercy: False`,
  `correct_value` STILL returned (post-resolution reveal — bounded by 9
  cells per game, so probing is visible and self-limiting).
- Wrong pick + mercy bounce: +xp_mercy (default 10), `mercy: True`. Roll is
  server-side via `random.random()`; tests monkeypatch
  `server.routes.ai.random.random` so the outcome is deterministic.
- Unknown item_id: 404 with detail "ttt_item_not_found" (the answer key
  lookup is the source of truth — populated by the injector at render time).
- Session strong-session bonus: 2+ draws in a 3-game session triggers
  +xp_strong_session (default 100); mastery_tier label respects the
  0/20/40/60% thresholds.
- Session 0 wins + 0 draws → `duolingo_remediation: True` (frontend will
  show a soft-toast remediation prompt, see plan §7.5).
- Config override: `gb_ttt_config` partial overrides merge cleanly with
  `_TTT_DEFAULTS`; explicit zero values are preserved (a zeroed
  `xp_strong_session` correctly suppresses the strong-session bonus).

The route reads `_TTT_ANSWER_KEY[hw_id]`, populated by `injector.inject()` at
render time. Tests hit `GET /api/homeworks/{hw_id}/preview` after homework
creation so the key map is in place before the check-answer call.
"""
from __future__ import annotations

import pytest

import server.routes.ai as _ai_routes
import server.services.injector as _injector


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


async def _always_unlocked(*a, **k):
    return True


@pytest.fixture(autouse=True)
def _unlock_practice_arc(monkeypatch):
    """TTT is now a server-gated practice-arc game (BLOCKER #3). These are
    grading unit tests, not gating tests — patch the unlock check always-True
    so they exercise the grader, not the 403 PRACTICE_LOCKED guard. The gate
    itself is pinned by tests/test_practice_gate_server_enforced.py."""
    monkeypatch.setattr("server.routes.ai.is_practice_unlocked", _always_unlocked)


@pytest.fixture(autouse=True)
def _wipe_ttt_answer_key():
    """Reset the in-memory answer key between tests so render-state doesn't leak."""
    _injector._TTT_ANSWER_KEY.clear()
    yield
    _injector._TTT_ANSWER_KEY.clear()


def _build_ttt_items() -> list[dict]:
    """Three valid TTT items with stable ids so tests can pin item_id strings.

    Auto-shuffle in the injector is deterministic by item_id seed, but the
    `correct` value is what we assert against on the response — order of
    options[] is irrelevant to the route logic.
    """
    return [
        {"id": "ttt-A", "q": "What is 7 x 8?", "correct": "56", "distractors": ["54", "48", "63"]},
        {"id": "ttt-B", "q": "What is 12 + 9?", "correct": "21", "distractors": ["19", "23", "20"]},
        {"id": "ttt-C", "q": "Which is prime?", "correct": "11", "distractors": ["9", "15", "21"]},
    ]


def _seed_homework(
    client,
    *,
    items: list[dict] | None = None,
    config: dict | None = None,
    grade: int = 8,
) -> str:
    """Insert a homework with TTT content + render preview to populate the answer key."""
    if items is None:
        items = _build_ttt_items()
    content: dict = {
        "meta": {"title": "TTT check-answer test HW"},
        "panels": [],
        "flashcards": [],
        "boss_questions": [],
        "memory_sprint": [],
        "gb_ttt": items,
    }
    if config is not None:
        content["gb_ttt_config"] = config
    payload = {
        "title": "TTT check-answer test HW",
        "subject": "math-algebra",
        "grade": grade,
        "mode": "hard",
        "family": "aniq-fanlar",
        "content_json": content,
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, resp.text
    hw_id = resp.json()["id"]

    # Render the preview — this triggers `injector.inject()` which populates
    # `_TTT_ANSWER_KEY[hw_id]` from `_serialize_ttt`. Without this round-trip
    # the route's answer-key lookup returns {} and every check-answer 404s.
    preview = client.get(f"/api/homeworks/{hw_id}/preview")
    assert preview.status_code == 200, preview.text

    return hw_id


def _post_check(client, **body) -> tuple[int, dict]:
    resp = client.post("/api/ai/check-answer", json=body)
    try:
        return resp.status_code, resp.json()
    except Exception:
        return resp.status_code, {"_raw": resp.text}


# ---------------------------------------------------------------------------
# 1. Correct pick → +50 XP
# ---------------------------------------------------------------------------


def test_ttt_correct_pick_returns_50_xp(client):
    hw_id = _seed_homework(client)
    code, data = _post_check(
        client,
        phase="ttt",
        homework_id=hw_id,
        item_id="ttt-A",
        picked="56",
    )
    assert code == 200, data
    assert data["is_correct"] is True
    assert data["mercy"] is False
    assert data["xp_delta"] == 50
    assert data["correct_value"] == "56"


# ---------------------------------------------------------------------------
# 2. Wrong + no mercy → 0 XP, correct_value still returned
# ---------------------------------------------------------------------------


def test_ttt_wrong_pick_no_mercy_returns_zero_xp(client, monkeypatch):
    """random.random() returns 0.5 → above the default 0.002 mercy threshold,
    so the wrong pick consumes a turn at zero XP."""
    monkeypatch.setattr(_ai_routes.random, "random", lambda: 0.5)
    hw_id = _seed_homework(client)
    code, data = _post_check(
        client,
        phase="ttt",
        homework_id=hw_id,
        item_id="ttt-A",
        picked="48",
    )
    assert code == 200, data
    assert data["is_correct"] is False
    assert data["mercy"] is False
    assert data["xp_delta"] == 0
    # Post-resolution reveal — frontend uses this to highlight the winning option.
    assert data["correct_value"] == "56"


def test_ttt_grades_from_content_json_without_injector_render(client):
    """React-served (v2) homeworks never call inject(), so _TTT_ANSWER_KEY is
    never populated. The grader must resolve the answer key directly from
    content_json. Regression for the v2 React TTT grading gap (404
    ttt_item_not_found) found during the v2 game browser-walk."""
    items = _build_ttt_items()
    resp = client.post("/api/homeworks", json={
        "title": "TTT v2 no-render HW",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
        "family": "aniq-fanlar",
        "content_json": {"meta": {"title": "TTT v2 no-render HW"}, "gb_ttt": items},
    })
    assert resp.status_code == 200, resp.text
    hw_id = resp.json()["id"]
    # Deliberately DO NOT render the preview — _TTT_ANSWER_KEY stays empty,
    # mirroring the React hydration path that never goes through inject().
    assert not _injector._TTT_ANSWER_KEY.get(hw_id)

    code, data = _post_check(client, phase="ttt", homework_id=hw_id, item_id="ttt-A", picked="56")
    assert code == 200, data
    assert data["is_correct"] is True
    assert data["correct_value"] == "56"

    # A wrong pick still grades (not a 404) via the content_json-resolved key.
    code2, data2 = _post_check(client, phase="ttt", homework_id=hw_id, item_id="ttt-B", picked="99")
    assert code2 == 200, data2
    assert data2["is_correct"] is False


# ---------------------------------------------------------------------------
# 3. Wrong + mercy bounce → +10 XP
# ---------------------------------------------------------------------------


def test_ttt_wrong_pick_mercy_returns_10_xp(client, monkeypatch):
    """random.random() returns 0.001 → BELOW the 0.002 mercy threshold,
    so the wrong pick triggers a hidden mercy bounce at +10 XP."""
    monkeypatch.setattr(_ai_routes.random, "random", lambda: 0.001)
    hw_id = _seed_homework(client)
    code, data = _post_check(
        client,
        phase="ttt",
        homework_id=hw_id,
        item_id="ttt-B",
        picked="19",
    )
    assert code == 200, data
    assert data["is_correct"] is False
    assert data["mercy"] is True
    assert data["xp_delta"] == 10
    assert data["correct_value"] == "21"


# ---------------------------------------------------------------------------
# 4. Unknown item_id → 404 ttt_item_not_found
# ---------------------------------------------------------------------------


def test_ttt_unknown_item_id_returns_404(client):
    hw_id = _seed_homework(client)
    code, data = _post_check(
        client,
        phase="ttt",
        homework_id=hw_id,
        item_id="ttt-Z-DOES-NOT-EXIST",
        picked="anything",
    )
    assert code == 404, data
    # FastAPI envelopes string detail values directly under the "detail" key.
    assert data.get("detail") == "ttt_item_not_found"


# ---------------------------------------------------------------------------
# 5. Session [draw, draw, loss] → strong-session bonus + Unbreakable tier
# ---------------------------------------------------------------------------


def test_ttt_session_two_draws_triggers_strong_bonus(client):
    """Per spec: 2 draws + 1 loss in a 3-game session.

    Per-outcome XP: 0 wins * 300 + 2 draws * 200 = 400.
    Strong-session bonus: draws >= 2 → +100.
    Total session_xp: 500.

    Mastery tier: (wins + draws) / total_games = (0 + 2) / 3 = 66.67%.
    66.67% >= 60% → "Unbreakable" (per plan §1.4 explicit ">=60%" boundary).

    duolingo_remediation: False (we have draws — student isn't fully zero'd).
    """
    hw_id = _seed_homework(client)
    code, data = _post_check(
        client,
        phase="ttt-session",
        homework_id=hw_id,
        results=[
            {"outcome": "draw"},
            {"outcome": "draw"},
            {"outcome": "loss"},
        ],
    )
    assert code == 200, data
    assert data["session_xp"] == 500
    assert data["strong_session_bonus"] == 100
    assert data["mastery_tier"] == "Unbreakable"
    assert data["duolingo_remediation"] is False
    assert data["wins"] == 0
    assert data["draws"] == 2
    assert data["losses"] == 1


# ---------------------------------------------------------------------------
# 6. Session [loss, loss, loss] → Duolingo remediation + Learning the Board
# ---------------------------------------------------------------------------


def test_ttt_session_zero_draws_zero_wins_triggers_remediation(client):
    """0 wins + 0 draws + 3 losses → 0% mastery → 'Learning the Board' + remediation."""
    hw_id = _seed_homework(client)
    code, data = _post_check(
        client,
        phase="ttt-session",
        homework_id=hw_id,
        results=[
            {"outcome": "loss"},
            {"outcome": "loss"},
            {"outcome": "loss"},
        ],
    )
    assert code == 200, data
    assert data["session_xp"] == 0
    assert data["strong_session_bonus"] == 0
    assert data["mastery_tier"] == "Learning the Board"
    assert data["duolingo_remediation"] is True
    assert data["wins"] == 0
    assert data["draws"] == 0
    assert data["losses"] == 3


# ---------------------------------------------------------------------------
# 7. Config override merges with defaults (None values filtered)
# ---------------------------------------------------------------------------


def test_ttt_session_config_override_changes_xp(client):
    """Authored gb_ttt_config: {xp_draw: 99, xp_strong_session: 0}.

    Two-draw session. Per-outcome: 0 + 2 * 99 = 198.
    Strong-session bonus: xp_strong_session=0 (override) → 0 even with 2 draws.
    Total session_xp: 198.

    Confirms the merge order — explicit overrides win over defaults — AND that
    explicit zeros are preserved (the override filter must drop None only,
    not all falsy values).
    """
    hw_id = _seed_homework(
        client,
        config={"xp_draw": 99, "xp_strong_session": 0},
    )
    code, data = _post_check(
        client,
        phase="ttt-session",
        homework_id=hw_id,
        results=[
            {"outcome": "draw"},
            {"outcome": "draw"},
        ],
    )
    assert code == 200, data
    assert data["session_xp"] == 198
    assert data["strong_session_bonus"] == 0
    # 2/2 = 100% → Unbreakable; tier doesn't depend on the XP override.
    assert data["mastery_tier"] == "Unbreakable"
    assert data["duolingo_remediation"] is False
