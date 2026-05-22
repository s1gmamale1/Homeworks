"""Regression tests for `/api/ai/check-answer` with phase=final-boss.

Pins the per-question grading branch added in Chunk B of the Final Boss
backend redesign:

- Phase dispatch: phase="final-boss" + homework_id → `_check_answer_final_boss`
- Back-compat: phase="final-boss" without homework_id falls through to legacy
  `tutor.check_answer` (no regression for older clients)
- Adapter delegates to existing `tutor.boss_turn` (LLM call) — tests mock it
- Mastery stars / outcome / outcome_xp on `done=True` per spec §11
- Hint-cost grade-banding helper unit tests (g1_4=5, g5/g6_8=10, g9_11=15)
- HP grade-banding helper unit tests (50/100/100/150)
- Answer-leak guard: response on a CORRECT decision contains no `accepted`,
  `ans`, `accepted_answers`, or `answer_spec` keys
- Per-(homework_id, session_id) state isolation in `_FB_ATTEMPTS`
- Existing `/api/ai/boss-turn` extended additively: surfaces outcome/stars on
  `done=True` (in-progress responses unchanged)
- Boundary semantics: 80% HP exactly = 3-star eligible; 50% HP exactly is
  NOT 2-star (must be > 50%)
"""
from __future__ import annotations

from unittest.mock import patch, AsyncMock

import pytest

import server.routes.ai as _ai_routes


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


async def _always_unlocked(*a, **k):
    return True


@pytest.fixture(autouse=True)
def _unlock_practice_arc(monkeypatch):
    """Final Boss is a practice-arc game, so the grader now enforces the
    server-side unlock check (BLOCKER #3) before grading. These are grading
    unit tests, not gating tests, so make the unlock check always pass and let
    the grader run. The gate itself is pinned by
    tests/test_practice_gate_server_enforced.py. Patches the symbol as imported
    into ai.py."""
    monkeypatch.setattr("server.routes.ai.is_practice_unlocked", _always_unlocked)


@pytest.fixture(autouse=True)
def _wipe_fb_attempts():
    """Reset the in-memory FB attempt tracker between tests."""
    _ai_routes._FB_ATTEMPTS.clear()
    yield
    _ai_routes._FB_ATTEMPTS.clear()


def _build_boss_questions() -> list[dict]:
    """Return a minimal valid boss_questions list with answer-bearing fields.

    `accepted_answers` / `ans` / `answer_spec` are PRESENT here — the injector
    strips them only at the runtime boundary; the endpoint reads the raw dict.
    The leak gate (test #15) asserts they never appear in the response.
    """
    return [
        {
            "id": "bq_001",
            "q": "2 + 2 nechi?",
            "ans": ["4"],
            "accepted_answers": ["4", "to'rt"],
            "answer_spec": {"kind": "equality", "expected": ["4"]},
            "dmg": 10,
            "hint_cost_per_use": 12,
        },
        {
            "id": "bq_002",
            "q": "3 * 5 nechi?",
            "ans": ["15"],
            "accepted_answers": ["15", "o'n besh"],
            "answer_spec": {"kind": "equality", "expected": ["15"]},
            "dmg": 20,
        },
    ]


def _seed_homework(
    client,
    *,
    boss_questions: list[dict] | None = None,
    boss_meta: dict | None = None,
    grade: int = 8,
) -> str:
    """Insert a homework with FB content and return its hw_id."""
    if boss_questions is None:
        boss_questions = _build_boss_questions()
    content: dict = {
        "meta": {"title": "FB check-answer test HW"},
        "panels": [],
        "flashcards": [],
        "boss_questions": boss_questions,
    }
    if boss_meta is not None:
        content["boss_meta"] = boss_meta
    payload = {
        "title": "FB check-answer test HW",
        "subject": "math-algebra",
        "grade": grade,
        "mode": "hard",
        "family": "aniq-fanlar",
        "content_json": content,
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _post_check(client, hw_id: str | None, **overrides) -> tuple[int, dict]:
    body = {
        "phase": "final-boss",
        "session_id": overrides.pop("session_id", "sess-FB-A"),
        "question_id": overrides.pop("question_id", "bq_001"),
        "student_answer": overrides.pop("student_answer", "4"),
        "attempt_number": overrides.pop("attempt_number", 1),
    }
    if hw_id is not None:
        body["homework_id"] = hw_id
    body.update(overrides)
    resp = client.post("/api/ai/check-answer", json=body)
    try:
        return resp.status_code, resp.json()
    except Exception:
        return resp.status_code, {"_raw": resp.text}


def _mock_boss_turn(
    *,
    correct: bool = True,
    damage: int = 10,
    done: bool = False,
    extra: dict | None = None,
) -> AsyncMock:
    """Build an AsyncMock that mimics `tutor.boss_turn`'s response shape."""
    payload: dict = {
        "correct": correct,
        "damage_dealt": damage if correct else 0,
        "boss_response": "Mock boss says hi",
        "hint": None,
        "score": 1.0 if correct else 0.0,
        "axis_1": 4 if correct else 1,
        "axis_2": 4 if correct else 1,
        "axis_1_label": "Mastered" if correct else "Novice",
        "axis_2_label": "Mastered" if correct else "Novice",
    }
    if done:
        payload["done"] = True
    if extra:
        payload.update(extra)
    mock = AsyncMock(return_value=payload)
    return mock


# ---------------------------------------------------------------------------
# 1-2. Adapter correctness — delegates to tutor.boss_turn
# ---------------------------------------------------------------------------


def test_fb_check_answer_correct_returns_damage_dealt(client):
    hw_id = _seed_homework(client)
    with patch.object(_ai_routes.tutor, "boss_turn",
                      new=_mock_boss_turn(correct=True, damage=10)):
        code, data = _post_check(client, hw_id)
    assert code == 200, data
    assert data["correct"] is True
    assert data["damage_dealt"] == 10
    assert data["phase"] == "final-boss"


def test_fb_check_answer_wrong_returns_zero_damage(client):
    hw_id = _seed_homework(client)
    with patch.object(_ai_routes.tutor, "boss_turn",
                      new=_mock_boss_turn(correct=False)):
        code, data = _post_check(client, hw_id, student_answer="banana")
    assert code == 200, data
    assert data["correct"] is False
    assert data["damage_dealt"] == 0


# ---------------------------------------------------------------------------
# 3-4. Phase dispatch + back-compat gate
# ---------------------------------------------------------------------------


def test_fb_check_answer_phase_dispatch(client):
    """Phase=final-boss + homework_id MUST invoke _check_answer_final_boss."""
    hw_id = _seed_homework(client)
    with patch.object(_ai_routes, "_check_answer_final_boss",
                      new=AsyncMock(return_value={"phase": "final-boss", "_dispatched": True})) as adapter:
        code, data = _post_check(client, hw_id)
    assert code == 200, data
    assert data.get("_dispatched") is True
    adapter.assert_awaited_once()


def test_fb_back_compat_phase_only_no_homework_id(client):
    """phase=final-boss WITHOUT homework_id falls through to legacy path."""
    legacy_mock = AsyncMock(return_value={"correct": True, "score": 0.9, "_legacy": True})
    fb_mock = AsyncMock(return_value={"_should_not_be_called": True})
    with patch.object(_ai_routes.tutor, "check_answer", new=legacy_mock), \
         patch.object(_ai_routes, "_check_answer_final_boss", new=fb_mock):
        resp = client.post("/api/ai/check-answer", json={
            "phase": "final-boss",
            "question": "Some boss question",
            "student_answer": "42",
            "expected_answers": ["42"],
        })
    assert resp.status_code == 200
    assert resp.json().get("_legacy") is True
    fb_mock.assert_not_awaited()


# ---------------------------------------------------------------------------
# 5-11. Mastery stars / outcome / XP rewards (per spec §11)
# ---------------------------------------------------------------------------


def test_fb_outcome_3_stars_first_attempt_no_hints_high_hp(client):
    """First attempt + 0 hints + 80% HP → 3 stars + 1000 XP for sub boss."""
    hw_id = _seed_homework(client)
    with patch.object(_ai_routes.tutor, "boss_turn",
                      new=_mock_boss_turn(correct=True, damage=10, done=True)):
        code, data = _post_check(
            client, hw_id,
            attempt_number=1,
            hp_remaining=80,        # 80% of grade-8 default 100
            attempts_used=0,
            boss_type="sub",
        )
    assert code == 200, data
    assert data["stars"] == 3
    assert data["outcome_xp"] == 1000
    assert data["outcome"] in ("expert", "strong", "passing", "hali_emas")


def test_fb_outcome_2_stars_with_one_attempt_60pct_hp(client):
    """attempt<=2 + HP > 50% → 2 stars + 700 XP for sub boss."""
    hw_id = _seed_homework(client)
    with patch.object(_ai_routes.tutor, "boss_turn",
                      new=_mock_boss_turn(correct=True, damage=10, done=True)):
        code, data = _post_check(
            client, hw_id,
            attempt_number=2,
            hp_remaining=60,        # 60% — between 50 and 80 → 2-star
            attempts_used=1,
            boss_type="sub",
        )
    assert code == 200, data
    assert data["stars"] == 2
    assert data["outcome_xp"] == 700


def test_fb_outcome_1_star_any_defeat(client):
    """Defeat with low HP / many attempts → 1 star + 500 XP for sub boss."""
    hw_id = _seed_homework(client)
    with patch.object(_ai_routes.tutor, "boss_turn",
                      new=_mock_boss_turn(correct=True, damage=10, done=True)):
        code, data = _post_check(
            client, hw_id,
            attempt_number=4,
            hp_remaining=15,        # <50% → only 1-star eligible
            attempts_used=3,
            boss_type="sub",
        )
    assert code == 200, data
    assert data["stars"] == 1
    assert data["outcome_xp"] == 500


def test_fb_outcome_hali_emas_when_hp_exhausted(client):
    """Boss not defeated (HP exhausted) → outcome=hali_emas, stars=0, xp=0."""
    hw_id = _seed_homework(client)
    with patch.object(_ai_routes.tutor, "boss_turn",
                      new=_mock_boss_turn(correct=False, done=True)):
        code, data = _post_check(
            client, hw_id,
            attempt_number=5,
            hp_remaining=0,
            attempts_used=4,
            boss_type="sub",
            student_answer="banana",
        )
    assert code == 200, data
    assert data["outcome"] == "hali_emas"
    assert data["stars"] == 0
    assert data["outcome_xp"] == 0


def test_fb_outcome_big_boss_3_stars_xp_2000(client):
    """boss_type=big + 3-star defeat → 2000 XP."""
    hw_id = _seed_homework(client)
    with patch.object(_ai_routes.tutor, "boss_turn",
                      new=_mock_boss_turn(correct=True, damage=10, done=True)):
        code, data = _post_check(
            client, hw_id,
            attempt_number=1,
            hp_remaining=90,
            attempts_used=0,
            boss_type="big",
        )
    assert code == 200, data
    assert data["stars"] == 3
    assert data["outcome_xp"] == 2000


def test_fb_outcome_mythical_boss_3_stars_xp_5000(client):
    """boss_type=mythical + 3-star defeat → 5000 XP."""
    hw_id = _seed_homework(client)
    with patch.object(_ai_routes.tutor, "boss_turn",
                      new=_mock_boss_turn(correct=True, damage=10, done=True)):
        code, data = _post_check(
            client, hw_id,
            attempt_number=1,
            hp_remaining=100,
            attempts_used=0,
            boss_type="mythical",
        )
    assert code == 200, data
    assert data["stars"] == 3
    assert data["outcome_xp"] == 5000


def test_fb_outcome_mythical_boss_lower_stars_xp_zero(client):
    """Mythical boss only rewards 3-star — 1- and 2-star defeats yield 0 XP."""
    hw_id = _seed_homework(client)
    with patch.object(_ai_routes.tutor, "boss_turn",
                      new=_mock_boss_turn(correct=True, damage=10, done=True)):
        code, data = _post_check(
            client, hw_id,
            attempt_number=2,
            hp_remaining=60,
            attempts_used=1,
            boss_type="mythical",
        )
    assert code == 200, data
    assert data["stars"] == 2
    assert data["outcome_xp"] == 0  # Mythical: only 3-star earns XP

    # Also verify 1-star path on mythical → still 0
    _ai_routes._FB_ATTEMPTS.clear()
    with patch.object(_ai_routes.tutor, "boss_turn",
                      new=_mock_boss_turn(correct=True, damage=10, done=True)):
        code, data = _post_check(
            client, hw_id,
            session_id="sess-FB-B",
            attempt_number=4,
            hp_remaining=10,
            attempts_used=3,
            boss_type="mythical",
        )
    assert code == 200, data
    assert data["stars"] == 1
    assert data["outcome_xp"] == 0


# ---------------------------------------------------------------------------
# 12-14. Helper unit tests (HP + hint cost grade-banding)
# ---------------------------------------------------------------------------


def test_fb_default_hp_for_grade_band_g1_4_is_50():
    assert _ai_routes._fb_default_hp_for_grade_band("g1_4") == 50


def test_fb_default_hp_for_grade_band_g9_11_is_150():
    assert _ai_routes._fb_default_hp_for_grade_band("g9_11") == 150
    # Sanity: middle bands and unknowns
    assert _ai_routes._fb_default_hp_for_grade_band("g5") == 100
    assert _ai_routes._fb_default_hp_for_grade_band("g6_8") == 100
    assert _ai_routes._fb_default_hp_for_grade_band(None) == 100
    assert _ai_routes._fb_default_hp_for_grade_band("nonsense") == 100


def test_fb_default_hint_cost_for_grade_band():
    """All four grade bands return spec §8 costs."""
    assert _ai_routes._fb_default_hint_cost_for_grade_band("g1_4") == 5
    assert _ai_routes._fb_default_hint_cost_for_grade_band("g5") == 10
    assert _ai_routes._fb_default_hint_cost_for_grade_band("g6_8") == 10
    assert _ai_routes._fb_default_hint_cost_for_grade_band("g9_11") == 15
    assert _ai_routes._fb_default_hint_cost_for_grade_band(None) == 10


# ---------------------------------------------------------------------------
# 15. Answer-leak gate (the soul-rule security invariant)
# ---------------------------------------------------------------------------


def test_fb_no_answer_leak_in_response(client):
    """Response on a CORRECT decision MUST NOT echo accepted/ans/answer_spec."""
    hw_id = _seed_homework(client)
    # The mocked boss_turn intentionally returns answer-bearing keys to verify
    # the route strips them before responding.
    with patch.object(_ai_routes.tutor, "boss_turn",
                      new=_mock_boss_turn(
                          correct=True, damage=10,
                          extra={
                              "accepted": ["4", "four"],
                              "ans": ["4"],
                              "accepted_answers": ["4"],
                              "answer_spec": {"kind": "equality", "expected": ["4"]},
                          },
                      )):
        code, data = _post_check(client, hw_id)
    assert code == 200, data
    leak_keys = {"accepted", "ans", "accepted_answers", "answer_spec",
                 "expected_answers"}
    leaked = leak_keys.intersection(data.keys())
    assert not leaked, f"Answer-bearing keys leaked into response: {leaked}"

    # Defensive: also no leak in nested dicts (currently flat, but pin invariant).
    import json
    serialized = json.dumps(data, ensure_ascii=False)
    for needle in ("accepted_answers", "answer_spec", "\"accepted\"", "\"ans\""):
        assert needle not in serialized, (
            f"Suspicious substring {needle!r} appears in serialized response"
        )


# ---------------------------------------------------------------------------
# 16. Bad input handling
# ---------------------------------------------------------------------------


def test_fb_unknown_question_id_rejected(client):
    """Unknown question_id returns a clean 404 with FB_Q_NOT_FOUND code."""
    hw_id = _seed_homework(client)
    with patch.object(_ai_routes.tutor, "boss_turn",
                      new=_mock_boss_turn(correct=True)) as mock:
        code, data = _post_check(client, hw_id, question_id="bq_does_not_exist")
    assert code == 404, data
    detail = data.get("detail") or data
    if isinstance(detail, dict):
        assert detail.get("code") == "FB_Q_NOT_FOUND"
    # The LLM grader must NOT have been called when validation failed.
    mock.assert_not_awaited()


def test_fb_missing_homework_id_when_phase_set(client):
    """phase=final-boss WITHOUT homework_id falls through, not a 400."""
    # This is asserted by the back-compat test above; here we additionally
    # confirm that posting WITH homework_id but invalid hw → 404.
    with patch.object(_ai_routes.tutor, "boss_turn",
                      new=_mock_boss_turn(correct=True)):
        resp = client.post("/api/ai/check-answer", json={
            "phase": "final-boss",
            "homework_id": "hw_does_not_exist_xyz",
            "question_id": "bq_001",
            "student_answer": "4",
            "session_id": "sess-FB-Z",
        })
    assert resp.status_code == 404
    detail = resp.json().get("detail") or resp.json()
    if isinstance(detail, dict):
        assert detail.get("code") == "HW_NOT_FOUND"


# ---------------------------------------------------------------------------
# 17-18. Session state isolation
# ---------------------------------------------------------------------------


def test_fb_attempts_tracked_across_session(client):
    """Multiple wrong submits on same session_id increment attempts_used."""
    hw_id = _seed_homework(client)
    with patch.object(_ai_routes.tutor, "boss_turn",
                      new=_mock_boss_turn(correct=False)):
        code1, data1 = _post_check(client, hw_id, student_answer="banana")
        code2, data2 = _post_check(client, hw_id, student_answer="apple")
        code3, data3 = _post_check(client, hw_id, student_answer="grape")
    assert code1 == 200 and code2 == 200 and code3 == 200
    # First wrong: attempts_used → 1; third wrong: attempts_used → 3.
    assert data1["attempts_used"] == 1
    assert data2["attempts_used"] == 2
    assert data3["attempts_used"] == 3


def test_fb_check_answer_session_isolation(client):
    """Different session_ids maintain independent _FB_ATTEMPTS state."""
    hw_id = _seed_homework(client)
    with patch.object(_ai_routes.tutor, "boss_turn",
                      new=_mock_boss_turn(correct=False)):
        # session A — three wrong submits
        for _ in range(3):
            _post_check(client, hw_id, session_id="sess-A", student_answer="bad")
        # session B — one wrong submit
        code, data = _post_check(client, hw_id, session_id="sess-B", student_answer="bad")
    assert code == 200, data
    # B has only 1 attempt. A has 3. They live in separate keys.
    assert data["attempts_used"] == 1
    state_a = _ai_routes._FB_ATTEMPTS.get((hw_id, "sess-A"))
    state_b = _ai_routes._FB_ATTEMPTS.get((hw_id, "sess-B"))
    assert state_a is not None and state_b is not None
    assert state_a["attempts_used"] == 3
    assert state_b["attempts_used"] == 1


# ---------------------------------------------------------------------------
# 19. /api/ai/boss-turn extension — outcome/stars surfaced on done=True
# ---------------------------------------------------------------------------


def test_boss_turn_endpoint_now_returns_outcome_on_defeat(client):
    """POST /api/ai/boss-turn — when LLM signals done=True, outcome surfaces."""
    with patch.object(_ai_routes.tutor, "boss_turn",
                      new=_mock_boss_turn(correct=True, damage=10, done=True)):
        resp = client.post("/api/ai/boss-turn", json={
            "boss_question": "2+2?",
            "student_answer": "4",
            "expected_answers": ["4"],
            "damage_value": 10,
            "hp_remaining": 80,
            "attempt_number": 1,
            "subject": "math-algebra",
            "grade": 8,
            "boss_type": "sub",
            "grade_band": "g6_8",
            "max_hp": 100,
            "hints_used": 0,
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["correct"] is True
    assert data["stars"] == 3
    assert data["outcome"] == "expert"
    assert data["outcome_xp"] == 1000
    assert data["boss_type_used"] == "sub"


def test_boss_turn_endpoint_in_progress_unchanged(client):
    """When done is absent/false, /api/ai/boss-turn response shape unchanged."""
    with patch.object(_ai_routes.tutor, "boss_turn",
                      new=_mock_boss_turn(correct=True, damage=10, done=False)):
        resp = client.post("/api/ai/boss-turn", json={
            "boss_question": "2+2?",
            "student_answer": "4",
            "expected_answers": ["4"],
            "damage_value": 10,
            "hp_remaining": 80,
            "attempt_number": 1,
            "subject": "math-algebra",
            "grade": 8,
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["correct"] is True
    # No outcome fields when in-progress (done absent / false).
    assert "outcome" not in data
    assert "stars" not in data
    assert "outcome_xp" not in data


# ---------------------------------------------------------------------------
# 20. Boundary semantics — 80%/50% pinning
# ---------------------------------------------------------------------------


def test_fb_outcome_thresholds_at_boundaries():
    """Exact 80% HP = 3-star eligible; exact 50% HP = NOT 2-star (must be > 50%)."""
    # 80% HP exactly + first attempt + 0 hints → 3 stars
    out = _ai_routes._boss_outcome_for(
        hp_remaining=80, max_hp=100, hints_used=0,
        attempt_number=1, boss_type="sub",
    )
    assert out == ("expert", 3, 1000), f"80% HP boundary should yield 3-star, got {out}"

    # Just below 80% (79) + first attempt + 0 hints → NOT 3-star, but still 2-star
    out = _ai_routes._boss_outcome_for(
        hp_remaining=79, max_hp=100, hints_used=0,
        attempt_number=1, boss_type="sub",
    )
    assert out[1] == 2, f"79% HP first attempt should yield 2-star, got {out}"

    # 50% HP exactly + 2 attempts → NOT 2-star (must be strictly > 50%)
    out = _ai_routes._boss_outcome_for(
        hp_remaining=50, max_hp=100, hints_used=0,
        attempt_number=2, boss_type="sub",
    )
    assert out[1] == 1, f"50% HP exactly should NOT be 2-star (must be >50%), got {out}"

    # 51% HP + 2 attempts → 2-star
    out = _ai_routes._boss_outcome_for(
        hp_remaining=51, max_hp=100, hints_used=0,
        attempt_number=2, boss_type="sub",
    )
    assert out[1] == 2, f"51% HP should be 2-star, got {out}"

    # Hint used disqualifies 3-star even with 100% HP first attempt
    out = _ai_routes._boss_outcome_for(
        hp_remaining=100, max_hp=100, hints_used=1,
        attempt_number=1, boss_type="sub",
    )
    assert out[1] == 2, f"100% HP + 1 hint should be 2-star (no 3-star), got {out}"

    # hp_remaining <= 0 → hali_emas regardless of other inputs
    out = _ai_routes._boss_outcome_for(
        hp_remaining=0, max_hp=100, hints_used=0,
        attempt_number=1, boss_type="sub",
    )
    assert out == ("hali_emas", 0, 0)
