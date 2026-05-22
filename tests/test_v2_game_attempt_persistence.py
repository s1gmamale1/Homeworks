"""Regression tests: v2 Practice-Arc games + Boss MUST persist per-attempt rows.

Before this wiring, only CBP / Memory-Check / adaptive-quiz / mystery-box /
puzzle-lock persisted to `phase_attempts`; tile-match, sentence-fill,
real-life-challenge, the Final Boss, and Tic-Tac-Toe kept state in MEMORY-ONLY
module dicts (`_TM_ATTEMPTS`, `_SF_ATTEMPTS`, `_RLC_ATTEMPTS`, `_FB_ATTEMPTS`)
that evaporate on restart. The Reflection engine reads `phase_attempts` to
extract real performance, so each of these phases now writes a row as a
side-effect of grading.

These tests guard the regression: for each newly-wired phase, a single
check-answer call with session_id + homework_id lands exactly one
`phase_attempts` row with the right `phase` value. Persistence is a side-effect
only — grading logic and response shapes are unchanged (pinned by the
per-phase endpoint test files).

AI graders (RLC reasoning, Final Boss boss_turn) are mocked — never a live
provider. The practice-arc unlock gate is patched always-True (these are
persistence unit tests, not gating tests; the gate is pinned by
tests/test_practice_gate_server_enforced.py).
"""
from __future__ import annotations

import asyncio
from unittest.mock import patch, AsyncMock

import pytest

import server.routes.ai as _ai_routes
import server.services.injector as _injector


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


async def _always_unlocked(*a, **k):
    return True


@pytest.fixture(autouse=True)
def _unlock_practice_arc(monkeypatch):
    """All five newly-wired phases (tile-match / sentence-fill / RLC / final-boss
    / ttt) are server-gated practice-arc games. These tests exercise the
    persistence side-effect, not the 403 PRACTICE_LOCKED guard, so make the
    unlock check always pass. Patches the symbol as imported into ai.py."""
    monkeypatch.setattr("server.routes.ai.is_practice_unlocked", _always_unlocked)


@pytest.fixture(autouse=True)
def _wipe_in_memory_trackers():
    """Reset the in-memory attempt trackers + TTT answer key between tests so
    cross-test state never leaks into a persistence assertion."""
    _ai_routes._TM_ATTEMPTS.clear()
    _ai_routes._SF_ATTEMPTS.clear()
    _ai_routes._RLC_ATTEMPTS.clear()
    _ai_routes._FB_ATTEMPTS.clear()
    _injector._TTT_ANSWER_KEY.clear()
    yield
    _ai_routes._TM_ATTEMPTS.clear()
    _ai_routes._SF_ATTEMPTS.clear()
    _ai_routes._RLC_ATTEMPTS.clear()
    _ai_routes._FB_ATTEMPTS.clear()
    _injector._TTT_ANSWER_KEY.clear()


def _read_attempts(session_id: str, hw_id: str, phase: str) -> list[dict]:
    """Read phase_attempts rows back via the repo (own event loop, like the
    existing CBP/MC persistence tests)."""
    from server.db.attempts_repo import list_phase_attempts

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(
            list_phase_attempts(session_id, hw_id, phase=phase)
        )
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Sentence-Fill
# ---------------------------------------------------------------------------


def _seed_sentence_fill(client) -> str:
    payload = {
        "title": "SF persistence HW",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
        "family": "aniq-fanlar",
        "content_json": {
            "meta": {"title": "SF persistence HW"},
            "panels": [],
            "flashcards": [],
            "boss_questions": [],
            "gb_sentence_fill": [
                {
                    "id": "sf_001",
                    "mode": "word_bank",
                    "passage": "The capital of France is ___.",
                    "answers": ["Paris"],
                    "explanations": ["Paris is the capital of France."],
                },
            ],
        },
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def test_sentence_fill_check_persists_phase_attempt(client):
    """A sentence-fill blank submission lands exactly one phase_attempts row
    with phase='sentence-fill' and a server-derived subphase='blank_<idx>'."""
    hw_id = _seed_sentence_fill(client)
    session_id = "sess-sf-persist"
    resp = client.post("/api/ai/check-answer", json={
        "phase": "sentence-fill",
        "homework_id": hw_id,
        "item_id": "sf_001",
        "blank_idx": 0,
        "student_value": "Paris",
        "attempt_number": 1,
        "session_id": session_id,
    })
    assert resp.status_code == 200, resp.text

    rows = _read_attempts(session_id, hw_id, "sentence-fill")
    assert len(rows) == 1, f"expected exactly one sentence-fill row, got {rows}"
    row = rows[0]
    assert row["phase"] == "sentence-fill"
    assert row["subphase"] == "blank_0"
    assert row["correct"] == 1
    assert row["checker_source"] == "phase_adapter:sentence-fill"


def test_sentence_fill_no_session_id_skips_persist(client):
    """Persistence is gracefully skipped when session_id is absent (anon/preview
    callers) — grading still succeeds, but no row is written."""
    hw_id = _seed_sentence_fill(client)
    resp = client.post("/api/ai/check-answer", json={
        "phase": "sentence-fill",
        "homework_id": hw_id,
        "item_id": "sf_001",
        "blank_idx": 0,
        "student_value": "Paris",
        "attempt_number": 1,
        # session_id deliberately omitted
    })
    assert resp.status_code == 200, resp.text
    # Nothing should land under the "default" session for this hw.
    rows = _read_attempts("default", hw_id, "sentence-fill")
    assert rows == [], f"expected no row when session_id is absent, got {rows}"


# ---------------------------------------------------------------------------
# Tile-Match
# ---------------------------------------------------------------------------


def _seed_tile_match(client) -> str:
    payload = {
        "title": "TM persistence HW",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
        "family": "aniq-fanlar",
        "content_json": {
            "meta": {"title": "TM persistence HW"},
            "panels": [],
            "flashcards": [],
            "boss_questions": [],
            "gb_tile_match": [
                {"id": "tm_001", "left": "F = ma", "right": "Newton's 2nd"},
                {"id": "tm_002", "left": "v = d/t", "right": "Velocity"},
            ],
        },
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def test_tile_match_check_persists_phase_attempt(client):
    """A correct tile-match pick lands one phase_attempts row with
    phase='tile-match' and subphase keyed off the SERVER-DERIVED pair index."""
    from server.services.tile_match_tokens import left_token, right_token

    hw_id = _seed_tile_match(client)
    session_id = "sess-tm-persist"
    resp = client.post("/api/ai/check-answer", json={
        "phase": "tile-match",
        "homework_id": hw_id,
        "left_id": left_token(hw_id, 0),
        "right_id": right_token(hw_id, 0),
        "session_id": session_id,
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["correct"] is True

    rows = _read_attempts(session_id, hw_id, "tile-match")
    assert len(rows) == 1, f"expected exactly one tile-match row, got {rows}"
    row = rows[0]
    assert row["phase"] == "tile-match"
    assert row["subphase"] == "pair_0"
    assert row["correct"] == 1
    assert row["checker_source"] == "phase_adapter:tile-match"


# ---------------------------------------------------------------------------
# Real-Life Challenge (AMR-graded; reasoning step mocks the AI grader)
# ---------------------------------------------------------------------------


def _build_rlc_case() -> dict:
    return {
        "id": "rlc_001",
        "expert_role": "fire_inspector",
        "title": "Bozor yong'in xavfi keysi",
        "intro": "Siz yong'in xavfsizligi inspektorisiz.",
        "tier": "basic",
        "grade_band": "g7_9",
        "steps": [
            {
                "id": "step1",
                "kind": "decision",
                "title": "1-bosqich",
                "prompt": "Eng to'g'ri birinchi qadam qaysi?",
                "options": [
                    {"id": "a", "label": "Evakuatsiya", "is_correct": True,
                     "consequence": "Hech kim shikastlanmadi."},
                    {"id": "b", "label": "Hech narsa", "is_correct": False,
                     "consequence": "Yong'in tarqaldi."},
                ],
            },
            {
                "id": "step5",
                "kind": "reasoning",
                "title": "5-bosqich",
                "prompt": "Nima uchun?",
                "min_chars": 20,
                "acceptable_keywords": ["xavfsizlik"],
            },
        ],
    }


def _seed_rlc(client) -> str:
    payload = {
        "title": "RLC persistence HW",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
        "family": "aniq-fanlar",
        "content_json": {
            "meta": {"title": "RLC persistence HW"},
            "panels": [],
            "flashcards": [],
            "boss_questions": [],
            "real_life_challenge": _build_rlc_case(),
        },
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def test_real_life_challenge_decision_persists_phase_attempt(client):
    """An RLC decision step lands one phase_attempts row with
    phase='real-life-challenge', subphase=step_id, and score mirroring the
    binary verdict (no AI grader fires on a decision step)."""
    hw_id = _seed_rlc(client)
    session_id = "sess-rlc-persist"
    resp = client.post("/api/ai/check-answer", json={
        "phase": "real-life-challenge",
        "homework_id": hw_id,
        "session_id": session_id,
        "step_id": "step1",
        "selected_option_id": "a",
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["correct"] is True

    rows = _read_attempts(session_id, hw_id, "real-life-challenge")
    assert len(rows) == 1, f"expected exactly one RLC row, got {rows}"
    row = rows[0]
    assert row["phase"] == "real-life-challenge"
    assert row["subphase"] == "step1"
    assert row["step_id"] == "step1"
    assert row["correct"] == 1
    assert row["score"] == 1.0
    assert row["checker_source"] == "phase_adapter:real-life-challenge"


def test_real_life_challenge_reasoning_persists_normalized_score(client):
    """The AMR-graded reasoning step persists score normalized 0-100 → 0-1 and
    carries the AI feedback. The AI grader is mocked (never a live provider)."""
    hw_id = _seed_rlc(client)
    session_id = "sess-rlc-reasoning"

    async def _fake_grader(text, step, *, case_intro, expert_role):
        return (80, "Yaxshi asoslandi.")

    long_text = "Odamlar xavfsizligi hamma narsadan ustun bo'lgani uchun evakuatsiya."
    with patch.object(_ai_routes, "_grade_rlc_reasoning", new=_fake_grader):
        resp = client.post("/api/ai/check-answer", json={
            "phase": "real-life-challenge",
            "homework_id": hw_id,
            "session_id": session_id,
            "step_id": "step5",
            "reasoning_text": long_text,
        })
    assert resp.status_code == 200, resp.text

    rows = _read_attempts(session_id, hw_id, "real-life-challenge")
    assert len(rows) == 1, f"expected exactly one RLC reasoning row, got {rows}"
    row = rows[0]
    assert row["subphase"] == "step5"
    # 80/100 normalized to 0.8.
    assert abs(row["score"] - 0.8) < 1e-9
    assert row["feedback"] == "Yaxshi asoslandi."


# ---------------------------------------------------------------------------
# Final Boss — the v2 React bossTurn() path (mock tutor.boss_turn)
# ---------------------------------------------------------------------------


def _seed_final_boss(client) -> str:
    payload = {
        "title": "FB persistence HW",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
        "family": "aniq-fanlar",
        "content_json": {
            "meta": {"title": "FB persistence HW"},
            "panels": [],
            "flashcards": [],
            "boss_questions": [
                {
                    "id": "bq_001",
                    "q": "2 + 2 nechi?",
                    "ans": ["4"],
                    "accepted_answers": ["4"],
                    "answer_spec": {"kind": "equality", "expected": ["4"]},
                    "dmg": 10,
                },
            ],
        },
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _mock_boss_turn(*, correct=True, score=1.0):
    return AsyncMock(return_value={
        "correct": correct,
        "damage_dealt": 10 if correct else 0,
        "boss_response": "Mock boss",
        "hint": None,
        "score": score,
        "axis_1": 4 if correct else 1,
        "axis_2": 4 if correct else 1,
        "axis_1_label": "Mastered" if correct else "Novice",
        "axis_2_label": "Mastered" if correct else "Novice",
    })


def test_final_boss_turn_persists_phase_attempt(client):
    """The v2 bossTurn() path (POST /api/ai/check-answer phase='final-boss')
    lands exactly one phase_attempts row with phase='final-boss', the boss
    question id as subphase, and the AMR score from tutor.boss_turn. The LLM
    grader is mocked — never a live provider."""
    hw_id = _seed_final_boss(client)
    session_id = "sess-fb-persist"
    with patch.object(_ai_routes.tutor, "boss_turn",
                      new=_mock_boss_turn(correct=True, score=1.0)):
        resp = client.post("/api/ai/check-answer", json={
            "phase": "final-boss",
            "homework_id": hw_id,
            "session_id": session_id,
            "question_id": "bq_001",
            "student_answer": "4",
            "attempt_number": 1,
        })
    assert resp.status_code == 200, resp.text
    assert resp.json()["correct"] is True

    rows = _read_attempts(session_id, hw_id, "final-boss")
    assert len(rows) == 1, f"expected exactly one final-boss row, got {rows}"
    row = rows[0]
    assert row["phase"] == "final-boss"
    assert row["subphase"] == "bq_001"
    assert row["question_id"] == "bq_001"
    assert row["correct"] == 1
    assert row["score"] == 1.0
    assert row["checker_source"] == "phase_adapter:final-boss"


def test_final_boss_wrong_turn_persists_zero_score(client):
    """A wrong boss turn still persists a row (correct=0, score from grader)."""
    hw_id = _seed_final_boss(client)
    session_id = "sess-fb-wrong"
    with patch.object(_ai_routes.tutor, "boss_turn",
                      new=_mock_boss_turn(correct=False, score=0.0)):
        resp = client.post("/api/ai/check-answer", json={
            "phase": "final-boss",
            "homework_id": hw_id,
            "session_id": session_id,
            "question_id": "bq_001",
            "student_answer": "banana",
            "attempt_number": 1,
        })
    assert resp.status_code == 200, resp.text

    rows = _read_attempts(session_id, hw_id, "final-boss")
    assert len(rows) == 1, f"expected exactly one final-boss row, got {rows}"
    assert rows[0]["correct"] == 0
    assert rows[0]["score"] == 0.0


# ---------------------------------------------------------------------------
# Tic-Tac-Toe — per-pick and end-of-session tally
# ---------------------------------------------------------------------------


def _seed_ttt(client) -> str:
    payload = {
        "title": "TTT persistence HW",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
        "family": "aniq-fanlar",
        "content_json": {
            "meta": {"title": "TTT persistence HW"},
            "panels": [],
            "flashcards": [],
            "boss_questions": [],
            "memory_sprint": [],
            "gb_ttt": [
                {"id": "ttt-A", "q": "What is 7 x 8?", "correct": "56",
                 "distractors": ["54", "48", "63"]},
            ],
        },
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, resp.text
    hw_id = resp.json()["id"]
    # Render preview so injector populates the TTT answer key.
    preview = client.get(f"/api/homeworks/{hw_id}/preview")
    assert preview.status_code == 200, preview.text
    return hw_id


def test_ttt_pick_persists_phase_attempt(client):
    """A single TTT pick lands one phase_attempts row with phase='ttt' and a
    server-derived subphase='pick_<item_id>'."""
    hw_id = _seed_ttt(client)
    session_id = "sess-ttt-persist"
    resp = client.post("/api/ai/check-answer", json={
        "phase": "ttt",
        "homework_id": hw_id,
        "session_id": session_id,
        "item_id": "ttt-A",
        "picked": "56",
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_correct"] is True

    rows = _read_attempts(session_id, hw_id, "ttt")
    assert len(rows) == 1, f"expected exactly one ttt row, got {rows}"
    row = rows[0]
    assert row["phase"] == "ttt"
    assert row["subphase"] == "pick_ttt-A"
    assert row["correct"] == 1
    assert row["checker_source"] == "phase_adapter:ttt"


def test_ttt_session_tally_persists_phase_attempt(client):
    """The end-of-session tally lands one phase_attempts row with
    phase='ttt-session' and subphase='tally'. Score is the draw+win ratio."""
    hw_id = _seed_ttt(client)
    session_id = "sess-ttt-session"
    resp = client.post("/api/ai/check-answer", json={
        "phase": "ttt-session",
        "homework_id": hw_id,
        "session_id": session_id,
        "results": [
            {"outcome": "win"},
            {"outcome": "draw"},
            {"outcome": "loss"},
        ],
    })
    assert resp.status_code == 200, resp.text

    rows = _read_attempts(session_id, hw_id, "ttt-session")
    assert len(rows) == 1, f"expected exactly one ttt-session row, got {rows}"
    row = rows[0]
    assert row["phase"] == "ttt-session"
    assert row["subphase"] == "tally"
    # 2 of 3 non-loss outcomes → 0.666...
    assert abs(row["score"] - (2 / 3)) < 1e-9
    assert row["correct"] == 1
    assert row["checker_source"] == "phase_adapter:ttt-session"
