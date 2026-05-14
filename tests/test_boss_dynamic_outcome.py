"""Regression — end-of-boss outcome / stars / XP must reflect correctness.

Bug context (2026-05-14):
    Student played the boss to completion answering every visible question
    correctly. Result card showed "+0 XP" and 0 stars anyway. The runtime
    reads `resp.outcome` / `resp.stars` / `resp.outcome_xp` and defaults to
    'passing' / 0 / 0 when they're missing — and the server was never
    sending them.

Fix (this test file's contract):
    server.services.boss_dynamic.compute_boss_outcome computes
    {outcome, stars, outcome_xp} from HP retention + correctness + hints
    on terminal status transitions. ai_plan5.boss_submit_answer wires
    those fields into BossSubmitAnswerResponse when status moves out of
    'active'.
"""
from __future__ import annotations

from server.services.boss_dynamic import compute_boss_outcome


# ---------------------------------------------------------------------------
# Star / outcome thresholds (defined alongside the implementation)
# ---------------------------------------------------------------------------


def test_perfect_win_yields_expert_three_stars():
    """Defeated boss with HP retention >= 70% AND correctness >= 80%."""
    r = compute_boss_outcome(
        hp=90, max_hp=100,
        correct_count=5, total_attempts=5,
        hints_used=0, status="won",
    )
    assert r["outcome"] == "expert"
    assert r["stars"] == 3
    assert r["outcome_xp"] > 0


def test_solid_win_yields_strong_two_stars():
    """Won with HP retention 40-69% and correctness 60-79%."""
    r = compute_boss_outcome(
        hp=50, max_hp=100,
        correct_count=4, total_attempts=6,  # correctness ~0.67
        hints_used=0, status="won",
    )
    assert r["outcome"] == "strong"
    assert r["stars"] == 2


def test_won_but_low_hp_yields_passing_one_star():
    """Won with low HP retention but correctness floor — 1 star, passing."""
    r = compute_boss_outcome(
        hp=15, max_hp=100,
        correct_count=3, total_attempts=5,  # correctness 0.60
        hints_used=0, status="won",
    )
    assert r["outcome"] == "passing"
    assert r["stars"] == 1


def test_failed_with_perfect_correctness_still_yields_passing(client=None):
    """Bug #5 + Bug #6 anchor scenario — the exact case observed 2026-05-14:
    student answered every visible question correctly but trials ran out
    before HP did → boss_status='failed'. The user-facing OUTCOME must still
    award 1 star + non-zero XP and label them 'passing', NOT 'hali_emas'.

    Pre-fix UX:
        - resp.outcome missing → runtime defaulted to 'passing' (correct
          label, but only by accident)
        - resp.stars missing  → 0 stars
        - resp.outcome_xp missing → +0 XP
        Result: student saw "O'tdingiz" header with 0 stars and 0 XP.

    Post-fix UX:
        - outcome='passing', stars=1, outcome_xp=110
        - Student sees positive recognition matching their effort even though
          the boss_status state machine recorded a 'failed' arc.

    This test pins the *semantic* contract: boss_status is a state-machine
    label (won/failed/active), outcome is the student-facing tier. They do
    NOT need to agree — a 'failed' arc with high correctness produces a
    'passing' outcome, and that's by design.
    """
    r = compute_boss_outcome(
        hp=10, max_hp=100,
        correct_count=2, total_attempts=2,  # 100% correct
        hints_used=0, status="failed",
    )
    assert r["outcome"] == "passing"
    assert r["stars"] == 1
    # 50 XP per correct + (hp/max_hp * 100) bonus = 100 + 10 = 110
    assert r["outcome_xp"] == 110, (
        f"Expected 110 XP (50*2 correct + 10 HP bonus), got {r['outcome_xp']}"
    )


def test_failed_status_does_not_force_hali_emas_outcome():
    """Bug #6: boss_status='failed' is a state-machine label (trials hit 0
    before HP did), NOT a value judgment of the student's performance.
    Outcome tier must derive from correctness + HP, not status alone.

    This test exercises three failed-status scenarios with different
    correctness rates and asserts the outcome tier reflects performance:
        - high correctness (>= 50%) → passing (1 star, positive XP)
        - low correctness  (< 50%)  → hali_emas (0 stars)

    The state-machine label 'failed' alone never determines the tier.
    """
    # High correctness + failed status → passing
    r_high = compute_boss_outcome(
        hp=5, max_hp=100,
        correct_count=4, total_attempts=5,  # 80% correct
        hints_used=0, status="failed",
    )
    assert r_high["outcome"] == "passing", (
        f"failed + 80% correct must yield 'passing' tier, got {r_high['outcome']!r}"
    )
    assert r_high["stars"] >= 1

    # Mediocre correctness (exactly 50%) + failed → still passing
    r_mid = compute_boss_outcome(
        hp=20, max_hp=100,
        correct_count=3, total_attempts=6,  # 50% correct
        hints_used=0, status="failed",
    )
    assert r_mid["outcome"] == "passing"

    # Low correctness + failed → hali_emas
    r_low = compute_boss_outcome(
        hp=10, max_hp=100,
        correct_count=1, total_attempts=5,  # 20% correct
        hints_used=0, status="failed",
    )
    assert r_low["outcome"] == "hali_emas"
    assert r_low["stars"] == 0


def test_failed_with_low_correctness_yields_hali_emas_zero_stars():
    """Failed AND correctness < 0.50 → no stars, hali_emas tier."""
    r = compute_boss_outcome(
        hp=20, max_hp=100,
        correct_count=1, total_attempts=5,  # correctness 0.20
        hints_used=0, status="failed",
    )
    assert r["outcome"] == "hali_emas"
    assert r["stars"] == 0


def test_zero_attempts_yields_hali_emas():
    """Edge case — never answered. Hali emas + 0 everything."""
    r = compute_boss_outcome(
        hp=100, max_hp=100,
        correct_count=0, total_attempts=0,
        hints_used=0, status="failed",
    )
    assert r["outcome"] == "hali_emas"
    assert r["stars"] == 0
    assert r["outcome_xp"] == 0


def test_xp_formula_includes_hp_bonus():
    """50 per correct + hp_ratio * 100 bonus."""
    r1 = compute_boss_outcome(
        hp=100, max_hp=100,
        correct_count=3, total_attempts=3,
        hints_used=0, status="won",
    )
    r2 = compute_boss_outcome(
        hp=10, max_hp=100,
        correct_count=3, total_attempts=3,
        hints_used=0, status="won",
    )
    # Same correctness, lower HP → less XP
    assert r1["outcome_xp"] > r2["outcome_xp"]
    # 150 (correct) + 100 (full HP) = 250
    assert r1["outcome_xp"] == 250
    # 150 + 10 = 160
    assert r2["outcome_xp"] == 160


def test_hint_usage_penalises_xp():
    """Each hint used costs 25 XP. Two students with identical performance
    differ only by hint usage."""
    no_hints = compute_boss_outcome(
        hp=50, max_hp=100,
        correct_count=4, total_attempts=5,
        hints_used=0, status="won",
    )
    used_hints = compute_boss_outcome(
        hp=50, max_hp=100,
        correct_count=4, total_attempts=5,
        hints_used=2, status="won",
    )
    assert used_hints["outcome_xp"] == no_hints["outcome_xp"] - 50


def test_xp_floored_at_zero():
    """Negative XP from heavy hint penalty must clamp to 0, not go negative."""
    r = compute_boss_outcome(
        hp=0, max_hp=100,
        correct_count=0, total_attempts=5,
        hints_used=10, status="failed",
    )
    assert r["outcome_xp"] == 0


def test_outcome_tier_mapping_is_consistent():
    """Each star count must map to exactly one outcome tier."""
    mappings = {3: "expert", 2: "strong", 1: "passing", 0: "hali_emas"}
    # 3 stars / expert
    r = compute_boss_outcome(hp=100, max_hp=100, correct_count=10,
                              total_attempts=10, hints_used=0, status="won")
    assert (r["stars"], r["outcome"]) == (3, mappings[3])
    # 2 stars / strong
    r = compute_boss_outcome(hp=50, max_hp=100, correct_count=7,
                              total_attempts=10, hints_used=0, status="won")
    assert (r["stars"], r["outcome"]) == (2, mappings[2])
    # 1 star / passing
    r = compute_boss_outcome(hp=10, max_hp=100, correct_count=5,
                              total_attempts=10, hints_used=0, status="won")
    assert (r["stars"], r["outcome"]) == (1, mappings[1])
    # 0 stars / hali_emas
    r = compute_boss_outcome(hp=20, max_hp=100, correct_count=2,
                              total_attempts=10, hints_used=0, status="failed")
    assert (r["stars"], r["outcome"]) == (0, mappings[0])


# ---------------------------------------------------------------------------
# Response contract — BossSubmitAnswerResponse exposes the new fields
# ---------------------------------------------------------------------------


def test_boss_submit_answer_response_includes_outcome_fields():
    """The Pydantic response model must declare outcome, stars, outcome_xp
    so the runtime can read them without falling back to defaults."""
    from server.routes.ai_plan5 import BossSubmitAnswerResponse

    fields = BossSubmitAnswerResponse.model_fields
    assert "outcome" in fields, "BossSubmitAnswerResponse missing 'outcome'"
    assert "stars" in fields, "BossSubmitAnswerResponse missing 'stars'"
    assert "outcome_xp" in fields, "BossSubmitAnswerResponse missing 'outcome_xp'"
    # All three are Optional — only populated on terminal status transitions.
    assert fields["outcome"].default is None
    assert fields["stars"].default is None
    assert fields["outcome_xp"].default is None
