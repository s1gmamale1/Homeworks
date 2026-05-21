"""Integration tier — redact a full nested CBP Checkpoint shape end-to-end.

Composes the redactor with a realistic full-shape Checkpoint dict to assert
the scrub catches every answer-bearing key in a layered payload (not just
synthetic minimal dicts).

PR #2 deliberately does NOT depend on PR #1's `CaseBasedPreview` schema —
the tutor redactor is dict-based and must work on author-provided shapes
even before/after the schema lands.
"""
from __future__ import annotations

from server.services.tutor import _redact_question_for_tutor


def _full_checkpoint_dict(kind: str = "identify") -> dict:
    """Inline factory — mirrors what `tests/factories.valid_checkpoint`
    produces in PR #1, but kept here so PR #2 is independent of PR #1."""
    return {
        "kind": kind,
        "question": f"Sample {kind} question",
        "options": [
            {"label": "A", "correct": False},
            {"label": "B", "correct": True},
            {"label": "C", "correct": False},
            {"label": "D", "correct": False},
        ],
        "answer_spec": {"type": "option_index", "option_index": 1},
        "learning_block_after": {
            "body": f"Explanation after {kind}.",
            "consequence_preview": "Agar boshqacha tanlasangiz, natija boshqa bo'lardi.",
        },
        "retake_variants": [],
    }


def test_realistic_checkpoint_redacts_cleanly():
    """Full Checkpoint shape with envelope-level CBP framing attached."""
    cp = _full_checkpoint_dict("identify")
    # Runtime would attach these from the envelope context when calling tutor
    cp["case_setup"] = {
        "story": "Test story",
        "role": "helper",
        "task": "Decide split",
    }
    cp["metadata"] = {"source_concept": "division"}

    redacted = _redact_question_for_tutor(cp, "case_based")

    # Answer-bearing keys are gone
    assert "answer_spec" not in redacted
    assert "learning_block_after" not in redacted
    assert "retake_variants" not in redacted
    # Framing survives
    assert redacted["case_setup"]["story"] == "Test story"
    assert redacted["metadata"]["source_concept"] == "division"
    # Question + kind survive
    assert "question" in redacted
    assert redacted["kind"] == "identify"


def test_full_cbp_envelope_redaction():
    """Pass a full CaseBasedPreview-shaped envelope (not just a single
    checkpoint) through the redactor. The redactor should strip everything
    answer-bearing while preserving navigable framing."""
    envelope = {
        "title": "Test CBP",
        "metadata": {"topic": "fractions"},
        "case_setup": {"story": "s", "role": "r", "task": "t"},
        "source_extraction": {"core_concept": "division", "main_rule": "rule"},
        "checkpoints": [
            _full_checkpoint_dict("identify"),
            _full_checkpoint_dict("decide"),
            _full_checkpoint_dict("justify"),
        ],
        "final_simulation": {
            "correct_path": "right",
            "wrong_path": "wrong",
        },
        "feedback_summary": {"student_understood": "concept"},
        "completion_rules": {"pass_condition": "ge_2_of_3"},
    }

    redacted = _redact_question_for_tutor(envelope, "case_based")

    # `checkpoints` is NOT a safe-listed key — entire list disappears so the
    # tutor only ever sees a single Checkpoint at a time (runtime is
    # responsible for picking the active one).
    assert "checkpoints" not in redacted
    # `final_simulation` and `feedback_summary` are answer-bearing — stripped.
    assert "final_simulation" not in redacted
    assert "feedback_summary" not in redacted
    # `completion_rules` is not framing — stripped.
    assert "completion_rules" not in redacted
    # Framing siblings survive
    assert "case_setup" in redacted
    assert "metadata" in redacted
    assert "source_extraction" in redacted


def test_all_three_checkpoint_kinds_redact_consistently():
    """Each checkpoint kind (identify / decide / justify) must redact
    identically — the kind doesn't change the redaction policy."""
    for kind in ("identify", "decide", "justify"):
        cp = _full_checkpoint_dict(kind)
        redacted = _redact_question_for_tutor(cp, "case_based")
        assert redacted["kind"] == kind
        assert "answer_spec" not in redacted
        assert "learning_block_after" not in redacted


def test_nested_retake_variant_does_not_leak():
    """A Checkpoint with a retake_variants list containing future questions
    must not leak those questions."""
    cp = _full_checkpoint_dict("decide")
    cp["retake_variants"] = [
        {
            "kind": "decide",
            "question": "FUTURE_QUESTION_DO_NOT_LEAK",
            "answer_spec": {"expected": "FUTURE_ANSWER"},
        },
    ]
    redacted = _redact_question_for_tutor(cp, "case_based")
    assert "retake_variants" not in redacted
    assert "FUTURE_QUESTION_DO_NOT_LEAK" not in str(redacted)
    assert "FUTURE_ANSWER" not in str(redacted)
