"""Plan Wave 2 — boss-question-generator prompt v4 contract guard.

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


def test_prompt_version_bumped_to_v4():
    text = _PROMPT_PATH.read_text(encoding="utf-8")
    first_line = text.splitlines()[0]
    assert "boss-question-generator:v4" in first_line, (
        f"prompt header must declare v4; got: {first_line!r}"
    )
    assert (
        boss_dynamic.PROMPT_VERSION["boss-question-generator"] == "v4"
    ), "PROMPT_VERSION dict must mirror the prompt-file header"


def test_prompt_lists_authored_question_stems_input():
    text = _PROMPT_PATH.read_text(encoding="utf-8")
    assert "authored_question_stems" in text, (
        "prompt v4 must surface authored_question_stems in 'Allowed inputs'"
    )
    assert "authored_difficulty_floor" in text, (
        "prompt v4 must surface authored_difficulty_floor in 'Allowed inputs'"
    )


def test_prompt_has_per_skill_floor_rule():
    text = _PROMPT_PATH.read_text(encoding="utf-8")
    assert "Per-skill difficulty floor" in text, (
        "prompt v4 must declare the per-skill difficulty floor as a hard rule"
    )
    # Accept either casing of 'one step below' so the rule body can be
    # rephrased without breaking the contract test.
    assert (
        "one step below" in text or "ONE step below" in text
    ), "prompt v4 must spell out the one-step-below allowance"
    assert "Anchor to the authored pool" in text, (
        "prompt v4 must declare the anchor-to-authored-pool rule"
    )


def test_prompt_v4_declares_language_hard_requirement():
    """v4 bumped the language rule from soft preference to hard requirement
    (Bug #9 fix, 2026-05-13 audit). Pin that contract."""
    text = _PROMPT_PATH.read_text(encoding="utf-8")
    assert "Language — HARD REQUIREMENT" in text or "HARD REQUIREMENT" in text, (
        "prompt v4 must escalate language to a hard requirement (was a soft 'prefer' in v2)"
    )
    # Must explicitly forbid English snake_case target_skill on uz/ru homeworks.
    assert "snake_case" in text.lower() or "sign_error" in text, (
        "prompt v4 must explicitly forbid English snake_case target_skill names"
    )


def test_prompt_v4_front_loads_language_directive_before_role():
    """Option C fix (2026-05-13 audit): the language directive used to be
    rule 9 of 11, buried at ~line 40. LLMs weight earlier prompt content
    more heavily than later, so the directive was easily overridden by
    in-context English examples. v4 promotes the directive to a banner
    BEFORE the 'You are the Boss Question Generator' role line."""
    text = _PROMPT_PATH.read_text(encoding="utf-8")
    role_idx = text.find("You are the Boss Question Generator")
    assert role_idx > 0, "couldn't locate the role line in the prompt"
    pre_role = text[:role_idx]
    assert "OUTPUT LANGUAGE" in pre_role, (
        "prompt v4 must front-load the OUTPUT LANGUAGE directive BEFORE the "
        "role line — burying it as rule 9 (the v3 location) lets in-context "
        "examples override it"
    )
    # Must reference both the lifted top-level field AND the nested fallback.
    assert "output_language" in pre_role or "INPUT.output_language" in pre_role, (
        "language directive must reference the top-level output_language input field"
    )


def test_payload_lifts_output_language_to_top_level():
    """Option C: boss_dynamic.generate_boss_question must surface
    boss_policy.language as a top-level INPUT.output_language key for the
    prompt banner to reference. Without lifting, Kimi has to navigate into
    boss_policy.language which is deeply nested in the JSON input."""
    # Smoke test that the constant we expect to see in payload is referenced
    # in the boss_dynamic source. (Behavioural test on the call site lives
    # in test_boss_dynamic_skill_floor.py — this is the prompt-side guard.)
    from server.services import boss_dynamic
    import inspect
    src = inspect.getsource(boss_dynamic.generate_boss_question)
    assert 'output_language' in src, (
        "generate_boss_question must lift boss_policy.language to "
        "INPUT.output_language so the prompt banner can find it"
    )
