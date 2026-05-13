"""Regression tests — authored boss_questions[] feed BossContext as reference pool.

Guards the invariant that BossContext.authored_question_stems is populated from
content_json.boss_questions, answer-leak keys are stripped, difficulty is inferred
from dmg, and empty pools yield None floor.
"""
from __future__ import annotations

import asyncio

import pytest

from server.services.boss_context_builder import build_boss_context


# ---------------------------------------------------------------------------
# Fixture helpers — mirror _make_homework pattern from test_plan5_dynamic_boss.py
# ---------------------------------------------------------------------------


def _make_homework_with_boss_questions(client, *, hw_id_hint: str = "stems-hw") -> str:
    """Insert a homework with three boss_questions (mix of dmg values, one with
    answer-leak keys) so the stem-extraction path is exercised."""
    payload = {
        "title": f"Boss stems test ({hw_id_hint})",
        "subject": "english",
        "grade": 8,
        "mode": "hard",
        "family": "til-fanlar",
        "content_json": {
            "title": f"Boss stems test ({hw_id_hint})",
            "subject": "english",
            "grade": 8,
            "language": "uz",
            "boss_questions": [
                {
                    "q": "Q1",
                    "tags": "[Bloom: L2]",
                    "dmg": 10,
                    "ans": ["leak"],
                    "answer_spec": {"type": "text_exact"},
                },
                {
                    "q": "Q2",
                    "tags": "[Bloom: L3]",
                    "dmg": 20,
                },
                {
                    "q": "Q3",
                    "dmg": 30,
                },
            ],
        },
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _make_homework_no_boss_questions(client, *, hw_id_hint: str = "stems-empty") -> str:
    """Insert a homework with no boss_questions key."""
    payload = {
        "title": f"Boss stems empty test ({hw_id_hint})",
        "subject": "english",
        "grade": 8,
        "mode": "hard",
        "family": "til-fanlar",
        "content_json": {
            "title": f"Boss stems empty test ({hw_id_hint})",
            "subject": "english",
            "grade": 8,
            "language": "uz",
        },
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_build_boss_context_includes_authored_question_stems(client):
    """authored_question_stems populated from content_json.boss_questions."""
    hw_id = _make_homework_with_boss_questions(client, hw_id_hint="t-stems-1")

    ctx = asyncio.run(
        build_boss_context(
            session_id="stems_sess_001",
            homework_id=hw_id,
            asked_questions=[],
            recent_boss_phrases=[],
        )
    )

    assert len(ctx.authored_question_stems) == 3
    for stem in ctx.authored_question_stems:
        assert "question_text" in stem
        assert "tags" in stem
        assert "hint" in stem
        assert "authored_difficulty" in stem


def test_authored_stems_scrubbed_of_answer_keys(client):
    """No answer-leak keys survive into authored_question_stems."""
    hw_id = _make_homework_with_boss_questions(client, hw_id_hint="t-stems-2")

    ctx = asyncio.run(
        build_boss_context(
            session_id="stems_sess_002",
            homework_id=hw_id,
            asked_questions=[],
            recent_boss_phrases=[],
        )
    )

    leak_keys = {"ans", "answer_spec", "accepted_answers", "expected", "correct"}
    for stem in ctx.authored_question_stems:
        for key in leak_keys:
            assert key not in stem, f"Answer-leak key '{key}' found in stem: {stem}"


def test_authored_difficulty_floor_is_pool_max(client):
    """authored_difficulty_floor equals the hardest authored_difficulty in the pool."""
    hw_id = _make_homework_with_boss_questions(client, hw_id_hint="t-stems-3")

    ctx = asyncio.run(
        build_boss_context(
            session_id="stems_sess_003",
            homework_id=hw_id,
            asked_questions=[],
            recent_boss_phrases=[],
        )
    )

    # dmg values are [10, 20, 30] → difficulties [easy, medium, hard] → floor = hard
    assert ctx.authored_difficulty_floor == "hard"


def test_empty_boss_questions_yields_empty_stems_and_null_floor(client):
    """When boss_questions is absent, stems == [] and floor is None."""
    hw_id = _make_homework_no_boss_questions(client, hw_id_hint="t-stems-4")

    ctx = asyncio.run(
        build_boss_context(
            session_id="stems_sess_004",
            homework_id=hw_id,
            asked_questions=[],
            recent_boss_phrases=[],
        )
    )

    assert ctx.authored_question_stems == []
    assert ctx.authored_difficulty_floor is None


# ---------------------------------------------------------------------------
# Option B fix (2026-05-13 audit) — filter language-drifted asked_questions
# ---------------------------------------------------------------------------


def test_build_boss_context_filters_english_asked_questions_on_uz_homework(client):
    """Option B: when a uz/ru homework has accumulated past generations that
    drifted to English (pre-fix bug), those entries must be filtered OUT of
    the asked_questions[] before sending to Kimi. Otherwise the English
    prior questions act as in-context examples and pull subsequent
    generations toward English even with the v4 language banner."""
    hw_id = _make_homework_with_boss_questions(client, hw_id_hint="t-filter-1")

    # Mix of English (drifted) and Uzbek (clean) prior generations.
    asked = [
        {
            "question_id": "gbq_en1",
            "question_text": "A student measures the length of a school bench as 200 cm with a possible error of 5 cm. What is the relative error?",
            "target_skill": "sign_error",
            "difficulty": "medium",
        },
        {
            "question_id": "gbq_en2",
            "question_text": "A student measures the length of a pencil as 175 mm with a possible error of 2 mm. What is the relative error as a percentage?",
            "target_skill": "sign_error",
            "difficulty": "medium",
        },
        {
            "question_id": "gbq_uz1",
            "question_text": "100 ga 5% nisbiy xatolik bo'yicha o'lchash. Aniq xatolik nechadan iborat?",
            "target_skill": "nisbiy xatolik",
            "difficulty": "medium",
        },
        {
            "question_id": "gbq_uz2",
            "question_text": "Yosh o'quvchining taqvimida o'qituv soati 45 da 5 ta minut. Nisbiy xatolik qanday aniqlanadi?",
            "target_skill": "nisbiy xatolik",
            "difficulty": "medium",
        },
    ]

    ctx = asyncio.run(
        build_boss_context(
            session_id="filter_sess_001",
            homework_id=hw_id,
            asked_questions=asked,
            recent_boss_phrases=[],
        )
    )

    # The English entries must be gone. Only the 2 Uzbek entries should
    # survive into ctx.asked_questions.
    surviving_ids = {q.get("question_id") for q in ctx.asked_questions}
    assert "gbq_en1" not in surviving_ids, (
        "Option B regression — English asked_question 'gbq_en1' was not filtered"
    )
    assert "gbq_en2" not in surviving_ids, (
        "Option B regression — English asked_question 'gbq_en2' was not filtered"
    )
    assert "gbq_uz1" in surviving_ids
    assert "gbq_uz2" in surviving_ids
    assert len(ctx.asked_questions) == 2


def test_build_boss_context_does_not_filter_asked_questions_on_english_homework(client):
    """Counterpart: on an English homework, English asked_questions are
    legitimate and must NOT be filtered (otherwise we'd kill anti-repetition
    for English-language boss flows)."""
    # Re-use the fixture but flip language to English.
    payload = {
        "title": "English boss test",
        "subject": "english",
        "grade": 8,
        "mode": "hard",
        "family": "til-fanlar",
        "content_json": {
            "title": "English boss test",
            "subject": "english",
            "grade": 8,
            "language": "en",
            "boss_questions": [
                {"q": "What does X mean?", "tags": "[Bloom: L2]", "dmg": 10},
            ],
        },
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200
    hw_id = resp.json()["id"]

    asked = [
        {
            "question_id": "gbq_a",
            "question_text": "A student measures the length of a school bench with a ruler.",
            "target_skill": "measurement",
            "difficulty": "medium",
        },
    ]
    ctx = asyncio.run(
        build_boss_context(
            session_id="en_sess_001",
            homework_id=hw_id,
            asked_questions=asked,
            recent_boss_phrases=[],
        )
    )
    # English homework: English asked_questions must pass through.
    assert len(ctx.asked_questions) == 1
    assert ctx.asked_questions[0]["question_id"] == "gbq_a"
