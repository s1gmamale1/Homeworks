import pytest
from server.services.ai_context import (
    extract_phase_content, 
    summarize_homework_content, 
    _find_question_in_content, 
    _redact_question_for_tutor
)

def test_extract_phase_content():
    content_json = {
        "preview": {"text": "Hello preview"},
        "final-boss": {"state": "ready"}
    }
    # Test preview subphase
    res = extract_phase_content(content_json, "preview")
    assert "preview_data" in res
    assert res["preview_data"] == {"text": "Hello preview"}

    # Test unknown subphase fallback
    res = extract_phase_content(content_json, "unknown-phase")
    assert "raw_subphase" in res
    assert res["raw_subphase"] == {}

def test_summarize_homework_content():
    content_json = {
        "title": "Algebra Basics",
        "subject": "Math",
        "grade": 8,
        "summary": "Intro to algebra.",
        "practice": {},
        "final-boss": {}
    }
    summary = summarize_homework_content(content_json)
    assert summary["title"] == "Algebra Basics"
    assert summary["grade"] == 8
    assert "practice" in summary["phases_available"]
    assert "final-boss" in summary["phases_available"]

def test_find_question_in_content_works():
    content = {"questions": [{"question_id": "q1", "text": "What is 2+2?"}]}
    result = _find_question_in_content(content, "q1")
    assert result == {"question_id": "q1", "text": "What is 2+2?"}

    assert _find_question_in_content({}, "q1") is None
    assert _find_question_in_content({"a": 1}, "") is None


def test_redact_question_for_tutor_strips_answer_bearing_in_preview():
    # BLOCKER #4 (alias hardening): a gated question carrying an answer-bearing
    # field (here the `expected_answer` alias) must be scrubbed even under
    # phase="preview" — the client-claimed phase no longer bypasses the scrub.
    q = {"text": "What is 2+2?", "expected_answer": "4"}
    result = _redact_question_for_tutor(q, "preview")
    assert "expected_answer" not in result
    assert "text" in result  # teaching prompt still allowed through

    # Practice strips non-safe keys too (unchanged).
    result = _redact_question_for_tutor(q, "practice")
    assert "expected_answer" not in result
    assert "text" in result


def test_redact_question_for_tutor_passes_pure_teaching_in_preview():
    # Control: a preview question with NO answer-bearing field is unaffected.
    q = {"text": "Explain why 2+2=4.", "tier": "EASY"}
    result = _redact_question_for_tutor(q, "preview")
    assert result["text"] == "Explain why 2+2=4."
    assert result["tier"] == "EASY"
