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
