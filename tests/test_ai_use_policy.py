"""Tests for the AI-use policy table (server/services/ai_use_policy.py).

Pins research §9.3: every tutor-phase resolves to a policy; an unknown key
fails closed to the safe default; and the assessment surface (boss) never
silently grants the in-app tutor.
"""
from __future__ import annotations

from server.services.ai_use_policy import (
    AI_USE_POLICY,
    SAFE_DEFAULT_POLICY,
    policy_for,
)


_REQUIRED_KEYS = {"tutor", "external_ai", "assessment"}


# ---------------------------------------------------------------------------
# Table shape
# ---------------------------------------------------------------------------


def test_every_table_entry_has_the_three_required_keys():
    for phase, policy in AI_USE_POLICY.items():
        assert _REQUIRED_KEYS <= set(policy.keys()), (
            f"{phase!r} missing required keys: {_REQUIRED_KEYS - set(policy.keys())}"
        )


def test_external_ai_values_are_in_the_allowed_vocabulary():
    """external_ai is True | False | "acknowledged" — nothing else."""
    for phase, policy in AI_USE_POLICY.items():
        assert policy["external_ai"] in (True, False, "acknowledged"), (
            f"{phase!r} has out-of-vocabulary external_ai: {policy['external_ai']!r}"
        )


# ---------------------------------------------------------------------------
# Every documented phase key resolves
# ---------------------------------------------------------------------------


def test_every_phase_key_resolves():
    """Each key in the table resolves to a dict carrying the required keys."""
    for phase in AI_USE_POLICY:
        if "/" in phase:
            base, sub = phase.split("/", 1)
            resolved = policy_for(base, sub)
        else:
            resolved = policy_for(phase)
        assert _REQUIRED_KEYS <= set(resolved.keys())


def test_preview_and_practice_are_learning_surfaces():
    """preview / practice / practice/case_based: tutor ON, external OFF, not graded."""
    for phase, sub in (("preview", None), ("practice", None), ("practice", "case_based")):
        p = policy_for(phase, sub)
        assert p["tutor"] is True
        assert p["external_ai"] is False
        assert p["assessment"] is False


def test_boss_is_the_assessment_tutor_off():
    """The assessment surface: tutor OFF, external OFF, this is what counts."""
    p = policy_for("boss")
    assert p["assessment"] is True
    assert p["tutor"] is False
    assert p["external_ai"] is False


def test_reflection_tutor_on_external_acknowledged_not_graded():
    p = policy_for("practice", "reflection")
    assert p["tutor"] is True
    assert p["external_ai"] == "acknowledged"
    assert p["assessment"] is False


# ---------------------------------------------------------------------------
# Resolution ladder
# ---------------------------------------------------------------------------


def test_composite_key_wins_over_bare_phase():
    """practice/reflection (acknowledged) must NOT collapse to bare practice (off)."""
    bare = policy_for("practice")
    composite = policy_for("practice", "reflection")
    assert bare["external_ai"] is False
    assert composite["external_ai"] == "acknowledged"


def test_unknown_subphase_falls_back_to_bare_phase():
    """An unrecognized subphase falls back to the bare-phase policy, not the default."""
    p = policy_for("practice", "no_such_subphase")
    assert p == policy_for("practice")
    assert p["tutor"] is True


def test_unknown_phase_falls_back_to_safe_default():
    p = policy_for("totally_unknown_phase")
    assert p == SAFE_DEFAULT_POLICY


def test_safe_default_is_fail_closed():
    """The fallback locks everything down and treats the surface as assessment."""
    assert SAFE_DEFAULT_POLICY["tutor"] is False
    assert SAFE_DEFAULT_POLICY["external_ai"] is False
    assert SAFE_DEFAULT_POLICY["assessment"] is True


def test_unknown_phase_with_subphase_also_safe_default():
    assert policy_for("nope", "also_nope") == SAFE_DEFAULT_POLICY


def test_empty_phase_resolves_to_safe_default():
    assert policy_for("") == SAFE_DEFAULT_POLICY


# ---------------------------------------------------------------------------
# Assessment-surface invariant (research §9.3)
# ---------------------------------------------------------------------------


def test_assessment_surfaces_have_tutor_off():
    """Any phase marked assessment must NOT also grant the in-app tutor."""
    for phase, policy in AI_USE_POLICY.items():
        if policy.get("assessment") is True:
            assert policy.get("tutor") is False, (
                f"{phase!r} is an assessment but grants the tutor — that's a help-during-test leak"
            )


# ---------------------------------------------------------------------------
# Immutability: callers can't mutate the shared table
# ---------------------------------------------------------------------------


def test_policy_for_returns_a_copy_not_the_shared_dict():
    p = policy_for("boss")
    p["tutor"] = True  # mutate the returned dict
    # The shared table must be untouched.
    assert AI_USE_POLICY["boss"]["tutor"] is False
    assert policy_for("boss")["tutor"] is False
