"""Sanity tier — the new CBP prompt files are wired into the expected
locations and reference the shared contract correctly.
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


def test_shared_contract_path_is_under_runtime():
    """The shared contract MUST live in `runtime/` (mirrors
    `_shared_context_contract.md` precedent), NOT inside a subject folder."""
    contract = PROMPTS_DIR / "runtime" / "_cbp_contract.md"
    assert contract.exists()
    # Negative check — no per-subject folder should host the shared contract
    for s in SUBJECTS:
        assert not (PROMPTS_DIR / s / "_cbp_contract.md").exists()


def test_shared_contract_names_the_eight_required_sections():
    """The shared contract MUST expose all 8 ordered output sections of the
    CBP envelope so per-subject prompts can mention them without restating."""
    text = (PROMPTS_DIR / "runtime" / "_cbp_contract.md").read_text(encoding="utf-8")
    for section in (
        "case_setup",
        "Checkpoint 1",
        "Learning Block 1",
        "Checkpoint 2",
        "Learning Block 2",
        "Checkpoint 3",
        "final_simulation",
        "feedback_summary",
    ):
        assert section in text, f"Shared contract missing required section: {section}"


def test_shared_contract_names_required_schema_fields():
    """Shared contract spec §6 (output JSON schema) must name the core
    schema fields so generators emit them in the right shape."""
    text = (PROMPTS_DIR / "runtime" / "_cbp_contract.md").read_text(encoding="utf-8")
    for field in (
        "checkpoints",
        "answer_spec",
        "learning_block_after",
        "consequence_preview",
        "final_simulation",
        "completion_rules",
    ):
        assert field in text, f"Shared contract missing schema field reference: {field}"


def test_shared_contract_explicitly_forbids_dragon_trap():
    """Standard §4 / Forbid #3 — case must lose meaning if math is stripped.
    Shared contract must call this out explicitly."""
    text = (PROMPTS_DIR / "runtime" / "_cbp_contract.md").read_text(encoding="utf-8").lower()
    assert "dragon trap" in text or "load-bearing" in text


def test_each_subject_prompt_has_validation_redirect():
    """Each subject prompt's §"Validation" section must explicitly defer to
    the shared contract — not duplicate the 18-item list."""
    for subject in SUBJECTS:
        text = (PROMPTS_DIR / subject / "case-based-preview.md").read_text(encoding="utf-8")
        # Some prompts use § symbol, others use ASCII; accept either
        assert "_cbp_contract.md" in text
        # No subject prompt should redefine the 18 items in full
        item_count = text.count("18-item")
        # Subject may reference the term once; full duplication would mention items 1..18
        assert "Item 18" not in text or item_count <= 2


def test_per_family_prompts_share_archetype_terminology():
    """Sister prompts in the same family should use consistent archetype
    terms. Math family uses 'practical-problem'; Sciences uses 'phenomenon'
    or 'observation' or 'lab-safety'; Languages uses 'communication'."""
    math_text = (PROMPTS_DIR / "math-algebra" / "case-based-preview.md").read_text(encoding="utf-8")
    assert "practical-problem" in math_text or "practical problem" in math_text.lower()

    biology_text = (PROMPTS_DIR / "biology" / "case-based-preview.md").read_text(encoding="utf-8")
    physics_text = (PROMPTS_DIR / "physics" / "case-based-preview.md").read_text(encoding="utf-8")
    kimyo_text = (PROMPTS_DIR / "kimyo-g7-11" / "case-based-preview.md").read_text(encoding="utf-8")
    for t in (biology_text, physics_text, kimyo_text):
        assert any(
            s in t.lower()
            for s in ("phenomenon", "observation", "lab", "diagnostic", "prediction")
        )

    english_text = (PROMPTS_DIR / "english" / "case-based-preview.md").read_text(encoding="utf-8")
    assert "communication" in english_text.lower()
