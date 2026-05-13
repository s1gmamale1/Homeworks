"""Plan Wave 2 — boss-question-generator prompt v3 contract guard.

These tests cover the prompt-side half of the per-skill difficulty floor
work. They are file-content assertions, not behavioural — but they catch the
exact failure mode where someone bumps the runtime helper's behaviour
without updating the prompt (or vice versa), which would mean the LLM is
flying blind about the new inputs.
"""
from __future__ import annotations

from server.config import PROMPTS_DIR
from server.services import boss_dynamic


_PROMPT_PATH = PROMPTS_DIR / "runtime" / "boss-question-generator.md"


def test_prompt_version_bumped_to_v3():
    text = _PROMPT_PATH.read_text(encoding="utf-8")
    first_line = text.splitlines()[0]
    assert "boss-question-generator:v3" in first_line, (
        f"prompt header must declare v3; got: {first_line!r}"
    )
    assert (
        boss_dynamic.PROMPT_VERSION["boss-question-generator"] == "v3"
    ), "PROMPT_VERSION dict must mirror the prompt-file header"


def test_prompt_lists_authored_question_stems_input():
    text = _PROMPT_PATH.read_text(encoding="utf-8")
    assert "authored_question_stems" in text, (
        "prompt v3 must surface authored_question_stems in 'Allowed inputs'"
    )
    assert "authored_difficulty_floor" in text, (
        "prompt v3 must surface authored_difficulty_floor in 'Allowed inputs'"
    )


def test_prompt_has_per_skill_floor_rule():
    text = _PROMPT_PATH.read_text(encoding="utf-8")
    assert "Per-skill difficulty floor" in text, (
        "prompt v3 must declare the per-skill difficulty floor as a hard rule"
    )
    # Accept either casing of 'one step below' so the rule body can be
    # rephrased without breaking the contract test.
    assert (
        "one step below" in text or "ONE step below" in text
    ), "prompt v3 must spell out the one-step-below allowance"
    assert "Anchor to the authored pool" in text, (
        "prompt v3 must declare the anchor-to-authored-pool rule"
    )


def test_prompt_v3_declares_language_hard_requirement():
    """v3 bumped the language rule from soft preference to hard requirement
    (Bug #9 fix, 2026-05-13 audit). Pin that contract."""
    text = _PROMPT_PATH.read_text(encoding="utf-8")
    assert "Language — HARD REQUIREMENT" in text or "HARD REQUIREMENT" in text, (
        "prompt v3 must escalate language to a hard requirement (was a soft 'prefer' in v2)"
    )
    # Must explicitly forbid English snake_case target_skill on uz/ru homeworks.
    assert "snake_case" in text.lower() or "sign_error" in text, (
        "prompt v3 must explicitly forbid English snake_case target_skill names"
    )
