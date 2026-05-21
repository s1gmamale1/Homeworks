"""Function tier — end-to-end leak prevention against MAGIC_TOKEN sentinels.

Places a unique sentinel string in every answer-bearing position of a
realistic CBP Checkpoint shape and asserts the redactor scrubs all of them
under the `case_based` phase.
"""
from __future__ import annotations

from server.services.tutor import _redact_question_for_tutor


def test_no_leak_from_any_answer_bearing_field_in_full_cbp_question():
    """One sentinel per known answer-bearing position. After redaction
    under phase='case_based', NONE of the sentinels may appear in the
    redacted payload's stringified form."""
    sentinels = {
        "answer_expected": "MAGIC_LEAK_S01_ANSWER_EXPECTED",
        "accepted_answer": "MAGIC_LEAK_S02_ACCEPTED",
        "lb_body": "MAGIC_LEAK_S04_LB_BODY",
        "lb_consequence": "MAGIC_LEAK_S05_LB_CONSEQ",
        "retake_question": "MAGIC_LEAK_S06_RETAKE_Q",
        "retake_expected": "MAGIC_LEAK_S07_RETAKE_EXP",
        "final_sim_correct": "MAGIC_LEAK_S08_SIM_CORRECT",
        "final_sim_wrong": "MAGIC_LEAK_S09_SIM_WRONG",
        "feedback_understood": "MAGIC_LEAK_S10_FB_UNDERSTOOD",
        "feedback_review": "MAGIC_LEAK_S11_FB_REVIEW",
    }

    cp = {
        "kind": "decide",
        "question": "Which method applies?",
        "options": [
            # `correct` flag (boolean) is dropped via key-level scrub —
            # tested directly in test_cbp_tutor_leak_unit.py. The label is
            # a legitimately-visible field and intentionally NOT a sentinel.
            {"label": "A", "correct": False},
            {"label": "B", "correct": True},
        ],
        "answer_spec": {
            "type": "text_exact",
            "expected": sentinels["answer_expected"],
            "accepted_answers": [sentinels["accepted_answer"]],
        },
        "learning_block_after": {
            "body": sentinels["lb_body"],
            "consequence_preview": sentinels["lb_consequence"],
        },
        "retake_variants": [
            {
                "kind": "decide",
                "question": sentinels["retake_question"],
                "answer_spec": {"expected": sentinels["retake_expected"]},
            },
        ],
        # Envelope-level keys that might bleed into a Checkpoint context
        "final_simulation": {
            "correct_path": sentinels["final_sim_correct"],
            "wrong_path": sentinels["final_sim_wrong"],
        },
        "feedback_summary": {
            "student_understood": sentinels["feedback_understood"],
            "what_to_review": sentinels["feedback_review"],
        },
    }

    redacted = _redact_question_for_tutor(cp, "case_based")
    raw = str(redacted)
    leaked = [name for name, sentinel in sentinels.items() if sentinel in raw]
    assert not leaked, f"Sentinels leaked under case_based redaction: {leaked}"


def test_no_leak_under_practice_phase_either():
    """Same sentinel matrix, but phase='practice' — even stricter (no CBP
    framing extension) so the leak surface is smaller. Sanity check."""
    cp = {
        "question": "q",
        "answer_spec": {"expected": "MAGIC_PRACTICE_LEAK"},
        "options": [{"label": "A", "correct": True}],
    }
    redacted = _redact_question_for_tutor(cp, "practice")
    assert "MAGIC_PRACTICE_LEAK" not in str(redacted)
    assert "correct" not in str(redacted)


def test_redactor_returns_dict_for_dict_input():
    """Edge case: empty dict input, non-dict input."""
    assert _redact_question_for_tutor({}, "case_based") == {}
    assert _redact_question_for_tutor("not a dict", "case_based") == {}
    assert _redact_question_for_tutor(None, "case_based") == {}
