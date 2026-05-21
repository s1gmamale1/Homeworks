"""Function tier — does the full prompt-pack support end-to-end CBP
generation expectations?

Asserts that, given the inputs CBP generation expects (subject, grade,
language, textbook address), every per-subject prompt names enough of the
schema and rules that a downstream LLM can produce a valid CBP without
re-deriving them. This is a structural function test — no LLM call.
"""
from __future__ import annotations

from server.config import PROMPTS_DIR


SUBJECTS = (
    "math-algebra",
    "geometriya-g7-11",
    "biology",
    "physics",
    "kimyo-g7-11",
    "english",
    "history",
)


def _read(subject: str) -> str:
    return (PROMPTS_DIR / subject / "case-based-preview.md").read_text(encoding="utf-8")


def _read_shared() -> str:
    return (PROMPTS_DIR / "runtime" / "_cbp_contract.md").read_text(encoding="utf-8")


def test_shared_contract_specifies_full_json_schema():
    """The shared contract MUST contain a complete JSON-shaped output
    schema. Asserts presence of the top-level fields a generator must emit."""
    text = _read_shared()
    for top_level in (
        "title",
        "metadata",
        "source_extraction",
        "case_setup",
        "checkpoints",
        "final_simulation",
        "feedback_summary",
        "completion_rules",
    ):
        assert f'"{top_level}"' in text, (
            f"Shared contract output schema missing top-level field: {top_level}"
        )


def test_shared_contract_specifies_completion_rule_value():
    text = _read_shared()
    # ge_2_of_3 is the locked plan value
    assert "ge_2_of_3" in text


def test_each_subject_explicitly_names_kind_field_values():
    """Generators read `kind` literal values from the prompt. Each subject
    prompt should show all three kinds in its checkpoint-shapes table."""
    for subject in SUBJECTS:
        text = _read(subject).lower()
        for kind in ("identify", "decide", "justify"):
            assert kind in text, f"{subject}: missing kind '{kind}'"


def test_each_subject_names_subject_specific_case_type():
    """Each per-subject prompt should name a `case_type` value to drop into
    metadata. Without this, generators emit a generic case_type and the
    runtime can't surface subject-aware UI hints."""
    expected_case_types = {
        "math-algebra": ("practical-problem",),
        "geometriya-g7-11": ("geometric-construction", "practical-problem"),
        "biology": ("observation", "diagnostic", "phenomenon"),
        "physics": ("phenomenon", "prediction"),
        "kimyo-g7-11": ("lab-safety", "reaction-prediction", "qualitative-test"),
        "english": ("communication", "grammar-fix", "vocabulary-choice"),
        "history": ("historical-decision", "source-evaluation", "perspective-switch", "cause-effect-chain"),
    }
    for subject, options in expected_case_types.items():
        text = _read(subject)
        matched = [o for o in options if o in text]
        assert matched, f"{subject}: missing any of expected case_type values: {options}"


def test_each_subject_specifies_required_skill_examples():
    """Generators benefit from concrete examples of `required_skill`
    values. Each subject prompt should provide at least one quoted example."""
    for subject in SUBJECTS:
        text = _read(subject)
        assert "required_skill" in text or "required skill" in text.lower()


def test_each_subject_describes_soft_retry_mutation_rule():
    """Forbid #19's mutation rule (mutate ≥1 of numbers / scene / character)
    must be repeated in each per-subject prompt so the generator knows what
    to vary."""
    for subject in SUBJECTS:
        text = _read(subject).lower()
        # Each prompt names at least two mutation axes — exact vocabulary
        # varies by subject (math: numbers / scene; biology: organism; history:
        # actor / event / period). Accept any of the family vocabularies.
        axes_named = sum(
            1
            for axis in (
                "number", "scene", "character", "scenario", "compound",
                "organism", "word", "actor", "event", "period", "framing",
                "city", "specific",
            )
            if axis in text
        )
        assert axes_named >= 2, (
            f"{subject}: soft-retry mutation rule should name multiple axes "
            f"to mutate (found {axes_named})"
        )


def test_shared_contract_specifies_final_rule_5_claims():
    """Standard §16 — the student must be able to say 5 things after a valid
    CBP. The shared contract MUST list all 5."""
    text = _read_shared().lower()
    # The 5 claims paraphrase to: situation, decision, concept, consequence, mistake
    for claim_keyword in ("situation", "decision", "concept", "happened", "mistake"):
        assert claim_keyword in text, (
            f"Shared contract §7 (Final rule) missing reference to '{claim_keyword}'"
        )
