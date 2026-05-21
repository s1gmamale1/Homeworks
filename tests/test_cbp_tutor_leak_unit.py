"""Unit tier — pure scrub logic with isolated Checkpoint-shaped inputs.

Asserts the CBP-specific allow-list extension behaves as designed and
default-deny still applies to answer-bearing keys.
"""
from __future__ import annotations

import pytest

from server.services.tutor import (
    _TUTOR_CONTEXT_CBP_EXTRA_KEYS,
    _TUTOR_CONTEXT_SAFE_KEYS,
    _redact_question_for_tutor,
)


def test_case_based_phase_keeps_question_and_options():
    q = {
        "question": "Which method applies here?",
        "options": [{"label": "A"}, {"label": "B"}],
        "kind": "decide",
    }
    redacted = _redact_question_for_tutor(q, "case_based")
    assert redacted["question"] == "Which method applies here?"
    assert redacted["kind"] == "decide"
    assert len(redacted["options"]) == 2
    assert redacted["options"][0] == {"label": "A"}


def test_case_based_strips_answer_spec_expected():
    q = {
        "question": "q",
        "answer_spec": {"type": "text_exact", "expected": "MAGIC_ANSWER"},
    }
    redacted = _redact_question_for_tutor(q, "case_based")
    assert "answer_spec" not in redacted
    assert "MAGIC_ANSWER" not in str(redacted)


def test_case_based_strips_options_correct_flag():
    q = {
        "question": "q",
        "options": [
            {"label": "A", "correct": True},
            {"label": "B", "correct": False},
        ],
    }
    redacted = _redact_question_for_tutor(q, "case_based")
    raw = str(redacted)
    assert "correct" not in raw
    # Label survives
    assert redacted["options"][0]["label"] == "A"


def test_case_based_strips_learning_block_after():
    q = {
        "question": "q",
        "kind": "identify",
        "learning_block_after": {"body": "MAGIC_EXPLANATION"},
    }
    redacted = _redact_question_for_tutor(q, "case_based")
    assert "learning_block_after" not in redacted
    assert "MAGIC_EXPLANATION" not in str(redacted)


def test_case_based_strips_retake_variants():
    q = {
        "question": "q",
        "kind": "decide",
        "retake_variants": [
            {"kind": "decide", "question": "MAGIC_RETAKE_PROMPT"},
        ],
    }
    redacted = _redact_question_for_tutor(q, "case_based")
    assert "retake_variants" not in redacted
    assert "MAGIC_RETAKE_PROMPT" not in str(redacted)


def test_case_based_keeps_case_setup_framing():
    q = {
        "question": "Which decision?",
        "case_setup": {
            "story": "Sample story",
            "role": "assistant",
            "task": "Decide on the right path",
        },
    }
    redacted = _redact_question_for_tutor(q, "case_based")
    assert "case_setup" in redacted
    assert redacted["case_setup"]["story"] == "Sample story"
    assert redacted["case_setup"]["role"] == "assistant"
    assert redacted["case_setup"]["task"] == "Decide on the right path"


def test_case_based_keeps_metadata_concept_hints():
    q = {
        "question": "q",
        "metadata": {
            "topic": "fractions",
            "source_concept": "division",
            "required_skill": "split-equally",
        },
    }
    redacted = _redact_question_for_tutor(q, "case_based")
    assert redacted["metadata"]["topic"] == "fractions"
    assert redacted["metadata"]["source_concept"] == "division"
    assert redacted["metadata"]["required_skill"] == "split-equally"


def test_case_based_keeps_source_extraction_rules():
    q = {
        "question": "q",
        "source_extraction": {
            "core_concept": "a/b ÷ n",
            "main_rule": "a / (b·n)",
            "common_mistake": "multiplying by n",
            "key_terms": ["fraction", "whole number"],
        },
    }
    redacted = _redact_question_for_tutor(q, "case_based")
    sx = redacted["source_extraction"]
    assert sx["core_concept"] == "a/b ÷ n"
    assert sx["main_rule"] == "a / (b·n)"
    assert sx["common_mistake"] == "multiplying by n"
    assert sx["key_terms"] == ["fraction", "whole number"]


def test_practice_phase_does_NOT_get_cbp_extras():
    """Negative test: practice phase MUST NOT pick up case framing keys —
    default-deny posture is preserved."""
    q = {
        "question": "q",
        "case_setup": {"story": "leaked-via-wrong-phase"},
        "metadata": {"source_concept": "leaked-concept"},
    }
    redacted = _redact_question_for_tutor(q, "practice")
    assert "case_setup" not in redacted
    assert "metadata" not in redacted
    assert "leaked-via-wrong-phase" not in str(redacted)
    assert "leaked-concept" not in str(redacted)


def test_memory_check_phase_does_NOT_get_cbp_extras():
    """Memory Check also stays on the strict allow-list."""
    q = {
        "question": "q",
        "case_setup": {"story": "should-not-pass"},
    }
    redacted = _redact_question_for_tutor(q, "memory_check")
    assert "case_setup" not in redacted


def test_boss_phase_does_NOT_get_cbp_extras():
    q = {
        "question": "q",
        "case_setup": {"story": "should-not-pass"},
    }
    redacted = _redact_question_for_tutor(q, "boss")
    assert "case_setup" not in redacted


def test_preview_phase_passes_through_unchanged():
    """Preview is unchanged from prior behavior — full dict copy."""
    q = {
        "question": "q",
        "answer_spec": {"expected": "REVEALED_IN_PREVIEW"},
        "any_key": "any_value",
    }
    redacted = _redact_question_for_tutor(q, "preview")
    assert redacted == q
    assert redacted is not q  # defensive copy
