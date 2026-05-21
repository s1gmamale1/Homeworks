"""Sanity tier — does the new CBP-specific tutor wiring exist?

Pure introspection of the safe-list, extras frozenset, and scrub function.
"""
from __future__ import annotations


def test_cbp_extras_contains_case_framing_keys():
    from server.services.tutor import _TUTOR_CONTEXT_CBP_EXTRA_KEYS
    for key in ("case_setup", "metadata", "source_extraction"):
        assert key in _TUTOR_CONTEXT_CBP_EXTRA_KEYS


def test_cbp_extras_contains_case_setup_inner_keys():
    from server.services.tutor import _TUTOR_CONTEXT_CBP_EXTRA_KEYS
    for key in ("story", "role", "task"):
        assert key in _TUTOR_CONTEXT_CBP_EXTRA_KEYS


def test_cbp_extras_contains_concept_hint_keys():
    from server.services.tutor import _TUTOR_CONTEXT_CBP_EXTRA_KEYS
    for key in ("source_concept", "required_skill", "topic", "core_concept", "main_rule", "key_terms"):
        assert key in _TUTOR_CONTEXT_CBP_EXTRA_KEYS


def test_cbp_extras_contains_kind_discriminator():
    from server.services.tutor import _TUTOR_CONTEXT_CBP_EXTRA_KEYS
    assert "kind" in _TUTOR_CONTEXT_CBP_EXTRA_KEYS


def test_cbp_extras_does_NOT_contain_answer_bearing_keys():
    """Negative sanity — these MUST stay out of the CBP allow-list."""
    from server.services.tutor import _TUTOR_CONTEXT_CBP_EXTRA_KEYS
    forbidden = {
        "answer_spec", "expected", "accepted_answers", "option_index", "correct",
        "learning_block_after", "consequence_preview", "retake_variants",
        "final_simulation", "correct_path", "wrong_path",
        "feedback_summary", "completion_rules",
    }
    leaked = forbidden & _TUTOR_CONTEXT_CBP_EXTRA_KEYS
    assert not leaked, f"CBP extras must not include answer-bearing keys: {leaked}"


def test_redactor_is_single_source_in_ai_context_and_tutor():
    """Regression fence for backend-integration-audit finding #1.

    The live `/api/ai/tutor/chat` route runs through
    `services/ai_context.py::build_tutor_context`, which previously had its
    OWN copy of `_redact_question_for_tutor` and a STALE safe-keys list
    (missing `explanation`, `flashcard_ref`, and the CBP phase branch).
    Result: PR #2's CBP coupling was dead code on the live path.

    Both modules must now point at the same function object (the one in
    `services/tutor_redaction.py`). If a future refactor re-introduces a
    duplicate redactor in either module, this test fails loudly.
    """
    from server.services.ai_context import _redact_question_for_tutor as ai_redact
    from server.services.tutor import _redact_question_for_tutor as tutor_redact
    assert ai_redact is tutor_redact, (
        "Redactor must be single-sourced via tutor_redaction.py - "
        "ai_context.py and tutor.py must NOT re-define it."
    )


def test_safe_keys_and_cbp_extras_are_disjoint_or_intentional():
    """Confirms the two sets don't have accidental overlap that would mask
    intent. Some overlap is fine (e.g., if `options` were in both); flag
    any unexpected overlap."""
    from server.services.tutor import (
        _TUTOR_CONTEXT_CBP_EXTRA_KEYS,
        _TUTOR_CONTEXT_SAFE_KEYS,
    )
    overlap = _TUTOR_CONTEXT_SAFE_KEYS & _TUTOR_CONTEXT_CBP_EXTRA_KEYS
    # `kind` could conceivably be added to either set in future; current
    # design puts it in CBP extras only. Assert nothing unexpected:
    expected_overlap = set()
    unexpected = overlap - expected_overlap
    assert not unexpected, f"Unexpected overlap between safe-list and CBP extras: {unexpected}"
