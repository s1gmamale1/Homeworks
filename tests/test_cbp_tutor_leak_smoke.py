"""Smoke tier — boot health + import sanity for PR #2 tutor changes."""
from __future__ import annotations


def test_tutor_module_imports():
    from server.services import tutor
    assert tutor is not None


def test_redact_function_exported():
    from server.services.tutor import _redact_question_for_tutor
    assert callable(_redact_question_for_tutor)


def test_cbp_extra_keys_frozenset_exported():
    from server.services.tutor import _TUTOR_CONTEXT_CBP_EXTRA_KEYS
    assert isinstance(_TUTOR_CONTEXT_CBP_EXTRA_KEYS, frozenset)
    assert len(_TUTOR_CONTEXT_CBP_EXTRA_KEYS) > 0


def test_case_based_in_allowed_phases():
    from server.services.tutor import ALLOWED_PHASES
    assert "case_based" in ALLOWED_PHASES


def test_app_still_imports():
    """The tutor.py edits must not break app startup."""
    from server.app import app
    assert app is not None
