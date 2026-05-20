from __future__ import annotations

from server.services.tutor import _redact_question_for_tutor


def test_memory_check_no_answer_leak_in_tutor_context():
    question = {
        "id": "mc_1",
        "type": "fill_blank",
        "prompt": "The process plants use to make food is called _____.",
        "options": ["respiration", "photosynthesis"],
        "answer_spec": {
            "type": "text_exact",
            "expected": "MAGIC_TOKEN_PHOTOSYNTHESIS",
            "accepted_answers": ["MAGIC_TOKEN_ALT"],
        },
        "accepted_answers": ["MAGIC_TOKEN_TOP_LEVEL"],
        "flashcard_ref": "fc_photo",
        "explanation": "Plants use photosynthesis.",
    }

    redacted = _redact_question_for_tutor(question, "memory_check")
    raw = str(redacted)

    assert "MAGIC_TOKEN" not in raw
    assert "answer_spec" not in redacted
    assert "accepted_answers" not in redacted
    assert redacted["prompt"].startswith("The process")
    assert redacted["flashcard_ref"] == "fc_photo"


def test_case_based_phase_uses_same_no_leak_path():
    question = {
        "question": "Which decision is safest?",
        "answer_spec": {"expected": "MAGIC_TOKEN_DECISION"},
        "options": [{"label": "A", "correct": True}, {"label": "B", "correct": False}],
    }

    redacted = _redact_question_for_tutor(question, "case_based")
    raw = str(redacted)

    assert "MAGIC_TOKEN" not in raw
    assert "correct" not in raw
    assert redacted["question"] == "Which decision is safest?"

