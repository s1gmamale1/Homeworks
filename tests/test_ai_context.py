"""Tests for server/services/ai_context.py

Covers:
 1. sanitize_screen_context_v2 — scrubs markers without deleting whole lines
 2. _find_question_in_content — recursive lookup by question_id
 3. _redact_question_for_tutor — preview passes through, practice strips answers
 4. build_tutor_context — resolves homework, session, question, metrics from DB

Run:
    python -m pytest tests/test_ai_context.py -v
"""
from __future__ import annotations

import asyncio
import os
from unittest.mock import patch

import aiosqlite
import pytest

from server.services import ai_context


@pytest.fixture(scope="module", autouse=True)
def _ensure_db(client):
    """Depend on the client fixture so the temp DB is initialized."""
    pass


def _db_path() -> str:
    from server.config import DB_PATH
    return str(DB_PATH)


# ---------------------------------------------------------------------------
# 1. sanitize_screen_context_v2
# ---------------------------------------------------------------------------


def test_sanitize_v2_empty_input():
    result = ai_context.sanitize_screen_context_v2("")
    assert result["text"] == ""
    assert result["raw_len"] == 0
    assert result["redacted"] is False


def test_sanitize_v2_none_input():
    result = ai_context.sanitize_screen_context_v2(None)  # type: ignore[arg-type]
    assert result["text"] == ""


def test_sanitize_v2_plain_prose_unchanged():
    prose = "This is a normal sentence about photosynthesis."
    result = ai_context.sanitize_screen_context_v2(prose)
    assert result["text"] == prose
    assert result["redacted"] is False


def test_sanitize_v2_preserves_educational_text():
    """The key fix: a line with class='correct' should NOT delete the whole line."""
    text = '<div class="question correct">According to the text, Maya has to clean the room.</div>'
    result = ai_context.sanitize_screen_context_v2(text)
    assert "According to the text, Maya has to clean the room." in result["text"]
    assert "correct" not in result["text"] or "class=" not in result["text"]
    assert result["redacted"] is True


def test_sanitize_v2_data_correct_removed():
    text = 'good line\n<div data-correct=true>hidden</div>\nstill good'
    result = ai_context.sanitize_screen_context_v2(text)
    assert "data-correct" not in result["text"]
    assert "good line" in result["text"]
    assert "still good" in result["text"]


def test_sanitize_v2_answer_key_redacted():
    text = "answer key: 42 is the solution"
    result = ai_context.sanitize_screen_context_v2(text)
    assert "answer key:" not in result["text"]
    assert "[redacted answer key]" in result["text"]


def test_sanitize_v2_expected_value_redacted():
    text = "The answer is photosynthesis, not photosynthetic."
    result = ai_context.sanitize_screen_context_v2(text, expected_values=["photosynthesis"])
    assert "[redacted]" in result["text"]
    assert "photosynthetic" in result["text"]


def test_sanitize_v2_truncation():
    text = "A" * 5000
    result = ai_context.sanitize_screen_context_v2(text)
    assert len(result["text"]) == 1800
    assert result["raw_len"] == 5000


def test_sanitize_v2_diagnostics():
    text = "plain text"
    result = ai_context.sanitize_screen_context_v2(text)
    assert result["raw_len"] == 10
    assert result["clean_len"] == 10
    assert result["redacted"] is False


# ---------------------------------------------------------------------------
# 2. _find_question_in_content
# ---------------------------------------------------------------------------


def test_find_question_top_level():
    content = {"questions": [{"id": "q1", "text": "hello"}]}
    assert ai_context._find_question_in_content(content, "q1") == {"id": "q1", "text": "hello"}


def test_find_question_nested():
    content = {
        "reading": {
            "questions": [
                {"question_id": "rq1", "prompt": "What is the main idea?"}
            ]
        }
    }
    assert ai_context._find_question_in_content(content, "rq1") == {
        "question_id": "rq1", "prompt": "What is the main idea?"
    }


def test_find_question_deeply_nested():
    content = {
        "gb_why_chain": {
            "steps": [
                {"id": "step_1", "question": "Why does ice float?"}
            ]
        }
    }
    assert ai_context._find_question_in_content(content, "step_1") == {
        "id": "step_1", "question": "Why does ice float?"
    }


def test_find_question_not_found():
    assert ai_context._find_question_in_content({"a": 1}, "missing") is None


def test_find_question_empty_inputs():
    assert ai_context._find_question_in_content({}, "q") is None
    assert ai_context._find_question_in_content({"a": 1}, "") is None


# ---------------------------------------------------------------------------
# 3. _redact_question_for_tutor
# ---------------------------------------------------------------------------


def test_redact_preview_strips_answer_bearing_fields():
    """BLOCKER #4: phase="preview" must NOT pass answer-bearing fields through.

    Pre-fix, preview returned the raw question (incl. answer_spec/solution) so a
    tampered client could tag a gated question as preview and leak the answer.
    Redaction is now driven by question CONTENT, not the claimed phase: any
    answer-bearing field is scrubbed even under preview.
    """
    q = {"prompt": "Solve for x", "answer_spec": {"expected": "5"}, "solution": "x=5"}
    result = ai_context._redact_question_for_tutor(q, "preview")
    assert result["prompt"] == "Solve for x"
    assert "answer_spec" not in result
    assert "solution" not in result


def test_redact_preview_passes_pure_teaching_content_through():
    """Control: a preview question with NO answer-bearing field is unaffected —
    legit teaching panels still flow through unchanged."""
    q = {"prompt": "Why is the sky blue?", "text": "Rayleigh scattering.", "tier": "EASY"}
    result = ai_context._redact_question_for_tutor(q, "preview")
    assert result["prompt"] == "Why is the sky blue?"
    assert result["text"] == "Rayleigh scattering."
    assert result["tier"] == "EASY"


def test_redact_practice_strips_answers():
    q = {
        "prompt": "Solve for x",
        "answer_spec": {"expected": "5"},
        "solution": "x=5",
        "options": [{"label": "A", "value": "5"}],
    }
    result = ai_context._redact_question_for_tutor(q, "practice")
    assert result["prompt"] == "Solve for x"
    assert "answer_spec" not in result
    assert "solution" not in result


def test_redact_practice_allows_safe_keys():
    q = {"id": "q1", "q": "What is 2+2?", "tier": "EASY", "tags": ["arithmetic"]}
    result = ai_context._redact_question_for_tutor(q, "practice")
    assert result["q"] == "What is 2+2?"
    assert result["tier"] == "EASY"
    assert result["tags"] == ["arithmetic"]


def test_redact_non_dict_returns_empty():
    assert ai_context._redact_question_for_tutor("not a dict", "practice") == {}  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 4. build_tutor_context — DB integration
# ---------------------------------------------------------------------------


async def _create_session(conn: aiosqlite.Connection, session_id: str, hw_id: str) -> None:
    await conn.execute(
        "INSERT INTO sessions (id, homework_id, student_name, started_at, status) VALUES (?, ?, ?, datetime('now'), 'active')",
        (session_id, hw_id, "Test Student"),
    )
    await conn.commit()


async def _create_homework(conn: aiosqlite.Connection, hw_id: str) -> None:
    await conn.execute(
        """
        INSERT INTO homeworks (id, title, subject, grade, mode, family, language, status, content_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """,
        (
            hw_id,
            "Test HW",
            "math-algebra",
            8,
            "hard",
            "aniq-fanlar",
            "uz",
            "published",
            '{"q1": {"question_id": "q1", "q": "What is 2+2?", "answer_spec": {"expected": "4"}}}',
        ),
    )
    await conn.commit()


@pytest.mark.asyncio
async def test_build_context_missing_hw():
    packet = await ai_context.build_tutor_context(
        session_id="sess_1", hw_id="missing_hw", phase="preview"
    )
    assert "missing_hw" in packet.missing_context_flags
    assert packet.phase == "preview"


@pytest.mark.asyncio
async def test_build_context_resolves_from_db():
    async with aiosqlite.connect(_db_path()) as conn:
        await _create_homework(conn, "hw_1")
        await _create_session(conn, "sess_1", "hw_1")

    packet = await ai_context.build_tutor_context(
        session_id="sess_1",
        hw_id="hw_1",
        phase="practice",
        question_id="q1",
        screen_context="Visible text here",
        student_work_text="4",
    )

    assert packet.session_id == "sess_1"
    assert packet.hw_id == "hw_1"
    assert packet.phase == "practice"
    assert packet.subject == "math-algebra"
    assert packet.grade == 8
    assert packet.current_question_id == "q1"
    assert packet.current_question_text == "What is 2+2?"
    assert packet.visible_screen_text == "Visible text here"
    assert packet.student_work_text == "4"
    assert "missing_hw" not in packet.missing_context_flags


@pytest.mark.asyncio
async def test_build_context_phase_fallback_to_session():
    async with aiosqlite.connect(_db_path()) as conn:
        await _create_homework(conn, "hw_2")
        await conn.execute(
            "INSERT INTO sessions (id, homework_id, student_name, started_at, status, current_phase) VALUES (?, ?, ?, datetime('now'), 'active', ?)",
            ("sess_2", "hw_2", "Test", "boss"),
        )
        await conn.commit()

    packet = await ai_context.build_tutor_context(
        session_id="sess_2", hw_id="hw_2"
    )
    assert packet.phase == "boss"


@pytest.mark.asyncio
async def test_build_context_phase_fallback_to_preview():
    async with aiosqlite.connect(_db_path()) as conn:
        await _create_homework(conn, "hw_3")
        await _create_session(conn, "sess_3", "hw_3")

    packet = await ai_context.build_tutor_context(
        session_id="sess_3", hw_id="hw_3"
    )
    assert packet.phase == "preview"


@pytest.mark.asyncio
async def test_build_context_question_fallback_to_session():
    async with aiosqlite.connect(_db_path()) as conn:
        await _create_homework(conn, "hw_4")
        await conn.execute(
            "INSERT INTO sessions (id, homework_id, student_name, started_at, status, current_question_id) VALUES (?, ?, ?, datetime('now'), 'active', ?)",
            ("sess_4", "hw_4", "Test", "q1"),
        )
        await conn.commit()

    packet = await ai_context.build_tutor_context(
        session_id="sess_4", hw_id="hw_4"
    )
    assert packet.current_question_id == "q1"
    assert packet.current_question_text == "What is 2+2?"


@pytest.mark.asyncio
async def test_build_context_sanitizes_screen_context():
    async with aiosqlite.connect(_db_path()) as conn:
        await _create_homework(conn, "hw_5")
        await _create_session(conn, "sess_5", "hw_5")

    packet = await ai_context.build_tutor_context(
        session_id="sess_5",
        hw_id="hw_5",
        phase="practice",
        question_id="q1",
        screen_context='<div class="correct">Answer is 4</div>',
    )
    # The sanitizer strips class attributes AND redacts the expected answer "4"
    assert "correct" not in packet.visible_screen_text
    assert "class=" not in packet.visible_screen_text
    assert "[redacted]" in packet.visible_screen_text


@pytest.mark.asyncio
async def test_build_context_missing_question_flag():
    async with aiosqlite.connect(_db_path()) as conn:
        await _create_homework(conn, "hw_6")
        await _create_session(conn, "sess_6", "hw_6")

    packet = await ai_context.build_tutor_context(
        session_id="sess_6", hw_id="hw_6", phase="practice"
    )
    assert "missing_question_id" in packet.missing_context_flags


@pytest.mark.asyncio
async def test_build_context_question_not_found():
    async with aiosqlite.connect(_db_path()) as conn:
        await _create_homework(conn, "hw_7")
        await _create_session(conn, "sess_7", "hw_7")

    packet = await ai_context.build_tutor_context(
        session_id="sess_7", hw_id="hw_7", phase="practice", question_id="no_such_q"
    )
    assert "question_not_found" in packet.missing_context_flags
