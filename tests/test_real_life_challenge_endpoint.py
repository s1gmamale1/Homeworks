"""Regression tests for `/api/ai/check-answer` with phase=real-life-challenge.

Pins the per-step grading branch added in Chunk B of the RLC backend redesign:

- Decision-style steps (decision / info_request / final_decision):
  * correct option → xp.decision_quality=50, advances step
  * wrong attempt 1 → no consequence reveal yet, xp=0
  * wrong attempt 2 → reveals correct_option_label (pedagogical), xp=0
- Concept-select step:
  * correct chip → xp.concept_id=50
  * wrong chip → xp.concept_id=0
- Reasoning step (AI-graded):
  * below min_chars → 400 reject BEFORE LLM call (mock asserts not called)
  * mocked grader score → maps 1:1 to xp.reasoning_quality
- Outcome tiers per spec §5: expert_decision (90+, +50 bonus, ×1.0),
  strong_analysis (75-89, ×1.0), passing (60-74, ×0.8), hali_emas (<60, ×0.4)
- Answer-leak guard: response on a CORRECT decision contains no `is_correct`
  flags, no other-option consequences, no foreign acceptable_keywords.
- Back-compat gate: phase=real-life-challenge WITHOUT homework_id falls
  through to legacy tutor.check_answer (no regression for legacy callers).
- Unknown step_id → 404. Kind/payload mismatch → 400.
- Snapshot test on the prompt template asserts key directives present.
"""
from __future__ import annotations

from pathlib import Path
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
    """Real-Life Challenge is now a server-gated practice-arc game (BLOCKER #3).
    These are grading unit tests, not gating tests — patch the unlock check
    always-True so they exercise the grader, not the 403 PRACTICE_LOCKED guard.
    The gate itself is pinned by tests/test_practice_gate_server_enforced.py."""
    monkeypatch.setattr("server.routes.ai.is_practice_unlocked", _always_unlocked)


@pytest.fixture(autouse=True)
def _wipe_rlc_attempts():
    """Reset the in-memory RLC attempt tracker between tests."""
    _ai_routes._RLC_ATTEMPTS.clear()
    yield
    _ai_routes._RLC_ATTEMPTS.clear()


def _build_rlc_case(
    *,
    case_id: str = "rlc_001",
    expert_role: str = "fire_inspector",
    tier: str = "basic",
    grade_band: str = "g7_9",
    min_chars: int = 80,
) -> dict:
    """Return a minimal valid RLC case dict (5 steps in spec order).

    Server-only fields (is_correct / consequence / acceptable_keywords) are
    PRESENT here — they are stripped only at the injector boundary, not at
    DB-write time. The endpoint reads the raw dict from content_json.
    """
    return {
        "id": case_id,
        "expert_role": expert_role,
        "title": "Bozor yong'in xavfi keysi",
        "intro": (
            "Siz yong'in xavfsizligi inspektorisiz. Eski bozor maydonida "
            "elektr sim qisqa tutashuvi yuz berdi."
        ),
        "pisa_level": "L4",
        "tier": tier,
        "grade_band": grade_band,
        "variant": "standard",
        "steps": [
            {
                "id": "step1",
                "kind": "decision",
                "title": "1-bosqich. Vaziyatni baholash",
                "prompt": "Eng to'g'ri birinchi qadam qaysi?",
                "options": [
                    {
                        "id": "a", "label": "Sotuvchilarni darhol evakuatsiya qilish",
                        "is_correct": True,
                        "consequence": "Hech kim shikastlanmadi.",
                    },
                    {
                        "id": "b", "label": "Faqat suvni o'chirish",
                        "is_correct": False,
                        "consequence": "Yong'in tarqaldi, do'konlar yondi.",
                    },
                    {
                        "id": "c", "label": "Hech narsa qilmaslik",
                        "is_correct": False,
                        "consequence": "Vaziyat yomonlashdi.",
                    },
                ],
            },
            {
                "id": "step2",
                "kind": "info_request",
                "title": "2-bosqich. Ma'lumot so'rash",
                "prompt": "Qaysi ma'lumot eng qimmatli?",
                "options": [
                    {
                        "id": "a", "label": "Elektr tizimi yoshi",
                        "is_correct": True,
                        "consequence": "Eski sim asosiy sabab ekan.",
                        "info_cost": {"time": "5 daqiqa"},
                    },
                    {
                        "id": "b", "label": "Sotuvchilar ro'yxati",
                        "is_correct": False,
                        "consequence": "Bu ma'lumot keyinroq foydali bo'lardi.",
                    },
                ],
            },
            {
                "id": "step3",
                "kind": "final_decision",
                "title": "3-bosqich. Yakuniy qaror",
                "prompt": "Bozorni qachon qayta ochishingiz kerak?",
                "options": [
                    {
                        "id": "a", "label": "Elektr tizimini to'liq tekshirgandan keyin",
                        "is_correct": True,
                        "consequence": "Xavfsiz qayta ochildi.",
                    },
                    {
                        "id": "b", "label": "Ertaga ertalab",
                        "is_correct": False,
                        "consequence": "Yana yong'in xavfi paydo bo'ldi.",
                    },
                ],
            },
            {
                "id": "step4",
                "kind": "concept_select",
                "title": "4-bosqich. Asosiy konsept",
                "prompt": "Bu vaziyatga eng mos tushuncha qaysi?",
                "concept_chips": [
                    {"id": "c1", "label": "Profilaktika ustuvorligi", "is_correct": True},
                    {"id": "c2", "label": "Tezkor qaror", "is_correct": False},
                    {"id": "c3", "label": "Iqtisodiy tejamkorlik", "is_correct": False},
                ],
            },
            {
                "id": "step5",
                "kind": "reasoning",
                "title": "5-bosqich. O'z fikringizni asoslang",
                "prompt": (
                    "Nima uchun siz yuqoridagi qarorlarni qabul qildingiz? "
                    "Stakeholder-larni hisobga oldingizmi?"
                ),
                "placeholder": "Fikringizni 1-3 jumlada yozing...",
                "min_chars": min_chars,
                "acceptable_keywords": [
                    "evakuatsiya", "xavfsizlik", "profilaktika", "stakeholder",
                ],
            },
        ],
    }


def _seed_homework(client, *, case: dict | None = None, grade: int = 8) -> str:
    """Insert a homework with an RLC case and return its hw_id."""
    if case is None:
        case = _build_rlc_case()
    payload = {
        "title": "RLC check-answer test HW",
        "subject": "math-algebra",
        "grade": grade,
        "mode": "hard",
        "family": "aniq-fanlar",
        "content_json": {
            "meta": {"title": "RLC check-answer test HW"},
            "panels": [],
            "flashcards": [],
            "boss_questions": [],
            "real_life_challenge": case,
        },
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _post_check(client, hw_id: str, **overrides) -> tuple[int, dict]:
    body = {
        "phase": "real-life-challenge",
        "homework_id": hw_id,
        "session_id": overrides.pop("session_id", "sess-A"),
    }
    body.update(overrides)
    resp = client.post("/api/ai/check-answer", json=body)
    try:
        return resp.status_code, resp.json()
    except Exception:
        return resp.status_code, {"_raw": resp.text}


# ---------------------------------------------------------------------------
# 1-3. Decision step grading
# ---------------------------------------------------------------------------


def test_rlc_decision_correct_option_returns_xp_and_advances(client):
    hw_id = _seed_homework(client)
    code, data = _post_check(client, hw_id, step_id="step1", selected_option_id="a")
    assert code == 200, data
    assert data["step_id"] == "step1"
    assert data["kind"] == "decision"
    assert data["correct"] is True
    assert data["xp"]["decision_quality"] == 50
    assert data["xp"]["step_total"] == 50
    assert data["step_index"] == 0
    assert data["total_steps"] == 5
    assert data["complete"] is False


def test_rlc_decision_wrong_attempt_1_no_reveal(client):
    hw_id = _seed_homework(client)
    code, data = _post_check(client, hw_id, step_id="step1", selected_option_id="b")
    assert code == 200, data
    assert data["correct"] is False
    # First wrong attempt — NO label reveal yet (encourage retry).
    assert data["correct_option_label"] is None
    assert data["xp"]["decision_quality"] == 0
    assert data["xp"]["step_total"] == 0
    # Wrong-pick consequence DOES surface (it's THEIR consequence).
    assert data["consequence"] == "Yong'in tarqaldi, do'konlar yondi."


def test_rlc_decision_wrong_attempt_2_reveals_label(client):
    hw_id = _seed_homework(client)
    # First wrong → no reveal
    _post_check(client, hw_id, step_id="step1", selected_option_id="b")
    # Second wrong → label revealed
    code, data = _post_check(client, hw_id, step_id="step1", selected_option_id="c")
    assert code == 200, data
    assert data["correct"] is False
    assert data["correct_option_label"] == "Sotuvchilarni darhol evakuatsiya qilish"
    assert data["xp"]["decision_quality"] == 0


# ---------------------------------------------------------------------------
# 4-5. info_request + final_decision steps
# ---------------------------------------------------------------------------


def test_rlc_info_request_step(client):
    hw_id = _seed_homework(client)
    code, data = _post_check(client, hw_id, step_id="step2", selected_option_id="a")
    assert code == 200, data
    assert data["kind"] == "info_request"
    assert data["correct"] is True
    assert data["xp"]["decision_quality"] == 50


def test_rlc_final_decision_step(client):
    hw_id = _seed_homework(client)
    code, data = _post_check(client, hw_id, step_id="step3", selected_option_id="a")
    assert code == 200, data
    assert data["kind"] == "final_decision"
    assert data["correct"] is True
    assert data["xp"]["decision_quality"] == 50


# ---------------------------------------------------------------------------
# 6-7. concept_select step
# ---------------------------------------------------------------------------


def test_rlc_concept_select_correct_chip(client):
    hw_id = _seed_homework(client)
    code, data = _post_check(client, hw_id, step_id="step4", selected_chip_id="c1")
    assert code == 200, data
    assert data["kind"] == "concept_select"
    assert data["correct"] is True
    assert data["xp"]["concept_id"] == 50
    assert data["xp"]["decision_quality"] == 0
    assert data["xp"]["step_total"] == 50


def test_rlc_concept_select_wrong_chip_no_xp(client):
    hw_id = _seed_homework(client)
    code, data = _post_check(client, hw_id, step_id="step4", selected_chip_id="c2")
    assert code == 200, data
    assert data["correct"] is False
    assert data["xp"]["concept_id"] == 0
    assert data["xp"]["step_total"] == 0


# ---------------------------------------------------------------------------
# 8-10. Reasoning step + AI grader
# ---------------------------------------------------------------------------


def test_rlc_reasoning_below_min_chars_rejected(client):
    hw_id = _seed_homework(client)
    fake_grader = AsyncMock()
    with patch.object(_ai_routes, "_grade_rlc_reasoning", new=fake_grader):
        code, data = _post_check(
            client, hw_id,
            step_id="step5",
            reasoning_text="Juda qisqa.",
        )
    assert code == 400, data
    # Grader MUST NOT have been called — cheap min-char gate runs first.
    fake_grader.assert_not_called()


def test_rlc_reasoning_ai_grades_score_50(client):
    hw_id = _seed_homework(client)
    long_text = (
        "Men sotuvchilarni darhol evakuatsiya qildim, chunki odamlar xavfsizligi "
        "hamma narsadan ustun, va elektr tizimini tekshirish kerak edi."
    )

    async def _fake_50(text, step, *, case_intro, expert_role):
        assert expert_role == "fire_inspector"
        return (50, "Bitta konseptni aytdingiz, ammo qo'llamadingiz.")

    with patch.object(_ai_routes, "_grade_rlc_reasoning", new=_fake_50):
        code, data = _post_check(
            client, hw_id,
            step_id="step5",
            reasoning_text=long_text,
        )
    assert code == 200, data
    assert data["kind"] == "reasoning"
    assert data["reasoning_score"] == 50
    assert data["xp"]["reasoning_quality"] == 50
    assert data["xp"]["step_total"] == 50
    assert data["complete"] is True


def test_rlc_reasoning_ai_grades_score_95(client):
    hw_id = _seed_homework(client)
    long_text = (
        "Profilaktika ustuvor, sotuvchilar va qo'shni do'konlar xavfsizligi "
        "uchun darhol evakuatsiya, keyin tizim tekshiruvi — bu trade-off "
        "qiymatga arziydi."
    )

    async def _fake_95(*a, **k):
        return (95, "Stakeholder-larni va trade-off-larni hisobga oldingiz.")

    with patch.object(_ai_routes, "_grade_rlc_reasoning", new=_fake_95):
        code, data = _post_check(
            client, hw_id,
            step_id="step5",
            reasoning_text=long_text,
        )
    assert code == 200, data
    assert data["reasoning_score"] == 95
    assert data["xp"]["reasoning_quality"] == 95


# ---------------------------------------------------------------------------
# 11-14. Outcome tier computation on completion
# ---------------------------------------------------------------------------


def _walk_through_full_case(client, hw_id, *, reasoning_score: int):
    """Walk all 5 steps with a perfect MC path; mock the reasoning grader."""

    # Steps 1-4 — perfect path.
    for step_id, opt_or_chip in [
        ("step1", {"selected_option_id": "a"}),
        ("step2", {"selected_option_id": "a"}),
        ("step3", {"selected_option_id": "a"}),
        ("step4", {"selected_chip_id": "c1"}),
    ]:
        code, _ = _post_check(client, hw_id, step_id=step_id, **opt_or_chip)
        assert code == 200

    long_text = (
        "Profilaktika xavfsizlik trade-off stakeholder evakuatsiya — "
        "men barcha sotuvchilarni va qo'shnilarni hisobga oldim."
    )

    async def _fake(*a, **k):
        return (reasoning_score, "Mock feedback")

    with patch.object(_ai_routes, "_grade_rlc_reasoning", new=_fake):
        code, data = _post_check(
            client, hw_id, step_id="step5", reasoning_text=long_text,
        )
    assert code == 200, data
    return data


def test_rlc_complete_outcome_expert_decision(client):
    hw_id = _seed_homework(client)
    # Perfect MC path = 50+50+50+50 = 200 decision_quality+concept_id portion.
    # Plus reasoning 95 → rubric total 200+95=295/300 = 98.3% → expert.
    data = _walk_through_full_case(client, hw_id, reasoning_score=95)
    assert data["complete"] is True
    assert data["outcome"] == "expert_decision"
    assert data["completion_bonus_xp"] == 50
    # Un-multiplied total = 50+50+50+50+95+50 = 345; multiplier=1.0
    assert data["total_xp"] == 345
    rb = data["rubric_breakdown"]
    assert rb["decision_quality"] == 150
    assert rb["concept_id"] == 50
    assert rb["reasoning_quality"] == 95
    assert rb["bonus"] == 50


def test_rlc_complete_outcome_strong_analysis(client):
    hw_id = _seed_homework(client)
    # Perfect MC = 200, reasoning = 50 → 250/300 = 83.3% → strong_analysis.
    data = _walk_through_full_case(client, hw_id, reasoning_score=50)
    assert data["outcome"] == "strong_analysis"
    assert data["completion_bonus_xp"] == 0
    # Un-multiplied = 50+50+50+50+50+0 = 250; multiplier=1.0.
    assert data["total_xp"] == 250


def test_rlc_complete_outcome_passing(client):
    hw_id = _seed_homework(client)
    # MC steps 1+2 correct, step3 wrong, step4 correct, reasoning 30:
    # rubric = 50+50+0+50+30 = 180/300 = 60% → passing (×0.8).
    for step_id, opt_or_chip in [
        ("step1", {"selected_option_id": "a"}),  # correct
        ("step2", {"selected_option_id": "a"}),  # correct
        ("step3", {"selected_option_id": "b"}),  # WRONG
        ("step4", {"selected_chip_id": "c1"}),   # correct
    ]:
        _post_check(client, hw_id, step_id=step_id, **opt_or_chip)

    async def _fake(*a, **k):
        return (30, "Mock")

    with patch.object(_ai_routes, "_grade_rlc_reasoning", new=_fake):
        long_text = (
            "Men xavfsizlikka e'tibor berdim, chunki odamlar muhim. "
            "Ammo tizim tekshiruvi kerak."
        )
        code, data = _post_check(
            client, hw_id, step_id="step5", reasoning_text=long_text,
        )
    assert code == 200, data
    assert data["outcome"] == "passing"
    # Un-multiplied = 50+50+0+50+30+0 = 180; ×0.8 = 144.
    assert data["total_xp"] == 144


def test_rlc_complete_outcome_hali_emas(client):
    hw_id = _seed_homework(client)
    # Step 1 correct (50), 2 wrong (0), 3 wrong (0), 4 wrong (0), reasoning 20:
    # rubric = 50+0+0+0+20 = 70/300 = 23% → hali_emas (×0.4).
    for step_id, opt_or_chip in [
        ("step1", {"selected_option_id": "a"}),  # correct
        ("step2", {"selected_option_id": "b"}),  # wrong
        ("step3", {"selected_option_id": "b"}),  # wrong
        ("step4", {"selected_chip_id": "c2"}),   # wrong
    ]:
        _post_check(client, hw_id, step_id=step_id, **opt_or_chip)

    async def _fake(*a, **k):
        return (20, "Mock")

    with patch.object(_ai_routes, "_grade_rlc_reasoning", new=_fake):
        long_text = (
            "Men shunchaki to'g'ri javob berdim, ammo o'ylamadim shu paytda "
            "va atroflarga qarayotganimni eslay olmayman ham."
        )
        code, data = _post_check(
            client, hw_id, step_id="step5", reasoning_text=long_text,
        )
    assert code == 200, data
    assert data["outcome"] == "hali_emas"
    # Un-multiplied = 50+0+0+0+20+0 = 70; ×0.4 = 28.
    assert data["total_xp"] == 28


# ---------------------------------------------------------------------------
# 15. Answer-leak guard
# ---------------------------------------------------------------------------


def test_rlc_no_answer_leak_in_response(client):
    """Pin the no-leak invariant on a CORRECT decision response."""
    hw_id = _seed_homework(client)
    code, data = _post_check(client, hw_id, step_id="step1", selected_option_id="a")
    assert code == 200, data

    # Recursively walk the response and assert FORBIDDEN keys are absent.
    def _walk(node, path=""):
        forbidden = {"is_correct", "acceptable_keywords"}
        if isinstance(node, dict):
            for k, v in node.items():
                assert k not in forbidden, (
                    f"Leaked forbidden key {k!r} at {path}"
                )
                _walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, item in enumerate(node):
                _walk(item, f"{path}[{i}]")

    _walk(data)

    # The CORRECT-pick response must NOT carry consequence text from the
    # wrong options (would be a leak path the student didn't earn).
    serialized = repr(data)
    assert "Yong'in tarqaldi" not in serialized, "Leaked wrong-option B consequence"
    assert "Vaziyat yomonlashdi" not in serialized, "Leaked wrong-option C consequence"
    # Acceptable_keywords from step5 must never surface anywhere.
    assert "evakuatsiya" not in serialized, "Leaked step5 acceptable_keyword"
    assert "stakeholder" not in serialized, "Leaked step5 acceptable_keyword"
    # On a correct decision, consequence field is null per plan §3c.
    assert data["consequence"] is None


# ---------------------------------------------------------------------------
# 16. Back-compat — phase=RLC without homework_id falls through
# ---------------------------------------------------------------------------


@patch("server.services.ai_orchestrator.generate_json")
def test_rlc_back_compat_legacy_callers_without_homework_id_fall_through(
    mock_generate, client,
):
    """phase=real-life-challenge without homework_id → legacy tutor.check_answer.

    The legacy path uses an `answer_spec` shape; the deterministic checker
    handles equality without ever calling generate_json.
    """
    body = {
        "phase": "real-life-challenge",
        "question": "What is 2+2?",
        "student_answer": "4",
        "expected_answers": ["4"],
        "answer_spec": {"type": "text_fuzzy", "expected": "4"},
    }
    resp = client.post("/api/ai/check-answer", json=body)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # Legacy shape — has `correct` + `feedback`, NOT the RLC envelope.
    assert "correct" in data
    assert "step_id" not in data
    assert "rubric_breakdown" not in data
    # Deterministic equality match — generate_json must not have been called.
    mock_generate.assert_not_called()


# ---------------------------------------------------------------------------
# 17-18. Validation errors
# ---------------------------------------------------------------------------


def test_rlc_unknown_step_id_rejected(client):
    hw_id = _seed_homework(client)
    code, data = _post_check(
        client, hw_id, step_id="step9", selected_option_id="a",
    )
    assert code == 404, data
    detail = data.get("detail") or {}
    if isinstance(detail, dict):
        assert detail.get("code") == "RLC_STEP_NOT_FOUND"


def test_rlc_kind_payload_mismatch_rejected(client):
    """Decision step receives selected_chip_id (no selected_option_id) → 400."""
    hw_id = _seed_homework(client)
    code, data = _post_check(
        client, hw_id, step_id="step1", selected_chip_id="c1",
    )
    assert code == 400, data
    detail = data.get("detail") or {}
    if isinstance(detail, dict):
        assert detail.get("code") == "RLC_MISSING_OPTION_ID"


# ---------------------------------------------------------------------------
# 19. Snapshot — prompt template directives
# ---------------------------------------------------------------------------


def test_rlc_grader_prompt_contains_key_directives():
    """The grader prompt must carry the score-range markers + JSON output rule."""
    repo_root = Path(__file__).resolve().parent.parent
    prompt_path = (
        repo_root / "server" / "prompts" / "runtime"
        / "real-life-challenge-grader.md"
    )
    assert prompt_path.exists(), f"Missing prompt template at {prompt_path}"
    text = prompt_path.read_text(encoding="utf-8")

    # Score-range bands per plan §3f.
    assert "0-30" in text
    assert "31-60" in text
    assert "61-85" in text
    assert "86-100" in text

    # Output format directive.
    assert "JSON" in text
    assert "score" in text
    assert "feedback" in text

    # Reasoning-grader anchors required by the plan.
    assert "acceptable_keywords" in text
    assert "expert_role" in text or "Expert role" in text
    assert "case_intro" in text or "Case intro" in text

    # Anti-leak: prompt must instruct the LLM not to echo keywords back.
    lower = text.lower()
    assert ("never" in lower and "echo" in lower) or ("do not" in lower and (
        "echo" in lower or "quote" in lower or "list" in lower
    )), "Prompt must instruct LLM not to echo acceptable_keywords back"


# ---------------------------------------------------------------------------
# 20 (bonus). Unknown homework_id → 404
# ---------------------------------------------------------------------------


def test_rlc_unknown_homework_id_returns_404(client):
    code, data = _post_check(
        client, "HW-DOES-NOT-EXIST",
        step_id="step1", selected_option_id="a",
    )
    assert code == 404, data


# ---------------------------------------------------------------------------
# 21 (bonus). homework with no real_life_challenge content → 404
# ---------------------------------------------------------------------------


def test_rlc_homework_without_rlc_content_returns_404(client):
    payload = {
        "title": "No-RLC HW",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
        "family": "aniq-fanlar",
        "content_json": {
            "meta": {"title": "No-RLC HW"},
            "panels": [], "flashcards": [], "boss_questions": [],
            # NO real_life_challenge field.
        },
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200
    hw_id = resp.json()["id"]
    code, data = _post_check(
        client, hw_id, step_id="step1", selected_option_id="a",
    )
    assert code == 404, data
    detail = data.get("detail") or {}
    if isinstance(detail, dict):
        assert detail.get("code") == "RLC_NO_CONTENT"
