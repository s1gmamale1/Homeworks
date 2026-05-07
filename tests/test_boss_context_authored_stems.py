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
