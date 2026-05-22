"""Tests for the pure integrity-signal flag engine (server/services/integrity_signals.py).

Covers each detector's fire / no-fire behavior at the boundaries plus the
FAIRNESS-FIRST guarantee: a slow, careful student and a fully-default policy
both yield ZERO flags.
"""
from __future__ import annotations

from server.services.integrity_signals import (
    AntiCheatPolicy,
    IntegrityFlag,
    IntegritySignalInput,
    compute_flags,
    policy_from_boss_meta,
    DEFAULT_SUDDEN_MASTERY_MIN_ITEMS,
)


def _inp(**overrides) -> IntegritySignalInput:
    base = dict(
        phase="boss",
        subphase=None,
        is_assessment=True,
        time_ms=None,
        paste_detected=False,
        pre_assessment_mastery=None,
        assessment_correct_rate=None,
        assessment_item_count=0,
        grade=8,
    )
    base.update(overrides)
    return IntegritySignalInput(**base)


def _codes(flags: list[IntegrityFlag]) -> set[str]:
    return {f.reason_code for f in flags}


# ---------------------------------------------------------------------------
# too_fast (LOW) — opt-in via response_time_floor_ms > 0
# ---------------------------------------------------------------------------


def test_too_fast_fires_below_floor():
    policy = AntiCheatPolicy(response_time_floor_ms=2000)
    flags = compute_flags(_inp(time_ms=1999), policy)
    assert "too_fast" in _codes(flags)
    assert all(f.severity == "low" for f in flags if f.reason_code == "too_fast")


def test_too_fast_no_fire_at_floor_boundary():
    policy = AntiCheatPolicy(response_time_floor_ms=2000)
    # Exactly at the floor is NOT below it.
    assert "too_fast" not in _codes(compute_flags(_inp(time_ms=2000), policy))


def test_too_fast_disabled_when_floor_zero():
    policy = AntiCheatPolicy(response_time_floor_ms=0)
    assert "too_fast" not in _codes(compute_flags(_inp(time_ms=5), policy))


def test_too_fast_no_fire_when_time_unknown():
    policy = AntiCheatPolicy(response_time_floor_ms=2000)
    assert "too_fast" not in _codes(compute_flags(_inp(time_ms=None), policy))


# ---------------------------------------------------------------------------
# paste_on_assessment (MEDIUM) — opt-in via paste_detect
# ---------------------------------------------------------------------------


def test_paste_on_assessment_fires():
    policy = AntiCheatPolicy(paste_detect=True)
    flags = compute_flags(_inp(is_assessment=True, paste_detected=True), policy)
    assert "paste_on_assessment" in _codes(flags)
    assert all(f.severity == "medium" for f in flags if f.reason_code == "paste_on_assessment")


def test_paste_disabled_by_default_policy():
    policy = AntiCheatPolicy()  # paste_detect defaults False
    assert "paste_on_assessment" not in _codes(
        compute_flags(_inp(is_assessment=True, paste_detected=True), policy)
    )


def test_paste_on_non_assessment_phase_yields_none():
    policy = AntiCheatPolicy(paste_detect=True)
    flags = compute_flags(
        _inp(phase="practice", is_assessment=False, paste_detected=True), policy
    )
    assert "paste_on_assessment" not in _codes(flags)


# ---------------------------------------------------------------------------
# sudden_mastery (STRONG) — on by default, stark before/after gap
# ---------------------------------------------------------------------------


def test_sudden_mastery_fires_on_stark_jump():
    policy = AntiCheatPolicy()  # sudden_mastery_enabled defaults True
    flags = compute_flags(
        _inp(
            pre_assessment_mastery=0.30,
            assessment_correct_rate=0.95,
            assessment_item_count=5,
        ),
        policy,
    )
    assert "sudden_mastery" in _codes(flags)
    assert all(f.severity == "strong" for f in flags if f.reason_code == "sudden_mastery")


def test_sudden_mastery_boundary_pre_ceiling_inclusive():
    policy = AntiCheatPolicy()
    # pre == 0.40 (<= ceiling) and post == 0.90 (>= floor) → fires.
    flags = compute_flags(
        _inp(pre_assessment_mastery=0.40, assessment_correct_rate=0.90,
             assessment_item_count=DEFAULT_SUDDEN_MASTERY_MIN_ITEMS),
        policy,
    )
    assert "sudden_mastery" in _codes(flags)


def test_sudden_mastery_no_fire_just_above_pre_ceiling():
    policy = AntiCheatPolicy()
    flags = compute_flags(
        _inp(pre_assessment_mastery=0.41, assessment_correct_rate=0.99,
             assessment_item_count=5),
        policy,
    )
    assert "sudden_mastery" not in _codes(flags)


def test_sudden_mastery_no_fire_below_min_items():
    policy = AntiCheatPolicy()
    flags = compute_flags(
        _inp(pre_assessment_mastery=0.10, assessment_correct_rate=1.0,
             assessment_item_count=DEFAULT_SUDDEN_MASTERY_MIN_ITEMS - 1),
        policy,
    )
    assert "sudden_mastery" not in _codes(flags)


def test_sudden_mastery_no_fire_when_data_unknown():
    policy = AntiCheatPolicy()
    assert "sudden_mastery" not in _codes(
        compute_flags(_inp(pre_assessment_mastery=None, assessment_correct_rate=None), policy)
    )


def test_sudden_mastery_disabled_yields_none():
    policy = AntiCheatPolicy(sudden_mastery_enabled=False)
    flags = compute_flags(
        _inp(pre_assessment_mastery=0.10, assessment_correct_rate=1.0,
             assessment_item_count=10),
        policy,
    )
    assert flags == []


# ---------------------------------------------------------------------------
# sophistication_jump — v1 stub always None
# ---------------------------------------------------------------------------


def test_sophistication_jump_never_fires_v1():
    from server.services import integrity_signals as isig
    # Even with an aggressive policy, the stub emits nothing.
    policy = AntiCheatPolicy(paste_detect=True, response_time_floor_ms=10**9)
    flags = compute_flags(_inp(time_ms=0), policy)
    assert "sophistication_jump" not in _codes(flags)
    assert isig._flag_sophistication_jump(_inp(), policy) is None


# ---------------------------------------------------------------------------
# FAIRNESS-FIRST: false-positive resistance
# ---------------------------------------------------------------------------


def test_slow_careful_student_yields_zero_flags():
    """A slow, careful, moderately-prepared student must NOT be flagged, even
    under a strict opt-in policy with a large time floor."""
    policy = AntiCheatPolicy(
        paste_detect=True,
        response_time_floor_ms=5000,   # large floor — careful student well above it
        sudden_mastery_enabled=True,
    )
    careful = _inp(
        phase="boss",
        is_assessment=True,
        time_ms=120000,                # took two minutes — far above the floor
        paste_detected=False,
        pre_assessment_mastery=0.55,   # moderate prep — above the ceiling
        assessment_correct_rate=0.85,  # solid but below the high floor
        assessment_item_count=5,
    )
    assert compute_flags(careful, policy) == []


def test_ready_student_high_score_yields_zero_flags():
    """H3 — false-positive resistance: a genuinely READY student who scores
    near-perfectly is NOT flagged. ``pre=0.60`` is above the sudden-mastery
    pre-ceiling (0.40), so even with ``post=0.95`` over 5 items the strong
    detector must stay silent under the default policy. This is the load-bearing
    fairness case — a strong student must never be treated as a cheater."""
    policy = AntiCheatPolicy()  # default: sudden_mastery on, paste/time off
    ready = _inp(
        phase="boss",
        is_assessment=True,
        pre_assessment_mastery=0.60,   # already-ready — above the 0.40 ceiling
        assessment_correct_rate=0.95,  # near-perfect — above the 0.90 floor
        assessment_item_count=5,
    )
    assert compute_flags(ready, policy) == []


def test_default_policy_on_non_assessment_yields_zero():
    """A fully-default policy on a non-assessment interaction → no flags."""
    policy = AntiCheatPolicy()
    flags = compute_flags(
        _inp(phase="practice", subphase=None, is_assessment=False,
             time_ms=10, paste_detected=True),
        policy,
    )
    assert flags == []


# ---------------------------------------------------------------------------
# policy_from_boss_meta
# ---------------------------------------------------------------------------


def test_policy_from_boss_meta_none_is_conservative_default():
    p = policy_from_boss_meta(None)
    assert p.paste_detect is False
    assert p.response_time_floor_ms == 0
    assert p.sudden_mastery_enabled is True


def test_policy_from_boss_meta_reads_anti_cheat():
    p = policy_from_boss_meta(
        {"anti_cheat": {"paste_detect": True, "response_time_floor_ms": 1500,
                        "sudden_mastery_enabled": False}}
    )
    assert p.paste_detect is True
    assert p.response_time_floor_ms == 1500
    assert p.sudden_mastery_enabled is False


def test_policy_from_boss_meta_malformed_collapses_to_default():
    assert policy_from_boss_meta({"anti_cheat": "nope"}) == AntiCheatPolicy()
    assert policy_from_boss_meta({}) == AntiCheatPolicy()
    # Negative / non-int floor clamps to 0 (disabled).
    p = policy_from_boss_meta({"anti_cheat": {"response_time_floor_ms": -50}})
    assert p.response_time_floor_ms == 0
    p2 = policy_from_boss_meta({"anti_cheat": {"response_time_floor_ms": "abc"}})
    assert p2.response_time_floor_ms == 0
