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


def test_shared_contract_has_dpe_step_in_required_structure():
    """Backend-prompts-audit finding F1 (CRITICAL): CBP Standard §5 + Infra
    family prompts mandate a Decision Process Explanation between Checkpoint 3
    and the final simulation. Lock the contract so DPE can't be silently
    dropped again."""
    text = (PROMPTS_DIR / "runtime" / "_cbp_contract.md").read_text(encoding="utf-8")
    assert "Decision Process Explanation" in text or "decision_process_explanation" in text
    # DPE must sit between Ckp 3 and final_simulation, not after
    ckp3_pos = text.find("Checkpoint 3")
    dpe_pos = text.find("Decision Process Explanation")
    fs_pos = text.find("Final simulation")
    if dpe_pos == -1:
        dpe_pos = text.find("decision_process_explanation")
    assert ckp3_pos < dpe_pos < fs_pos, (
        f"DPE must sit BETWEEN Checkpoint 3 ({ckp3_pos}) and Final simulation ({fs_pos}); "
        f"got DPE at {dpe_pos}"
    )


def test_shared_contract_json_schema_includes_decision_process_explanation():
    text = (PROMPTS_DIR / "runtime" / "_cbp_contract.md").read_text(encoding="utf-8")
    assert '"decision_process_explanation":' in text
    # The three sub-prompts (concept · method · mistake)
    schema_block = text[text.find('"decision_process_explanation":'):]
    schema_block = schema_block[:500]  # local window
    for field in ('"concept":', '"method":', '"mistake":'):
        assert field in schema_block, f"DPE JSON schema missing field: {field}"


def test_shared_contract_final_rule_has_six_claims_including_reasoning_before_outcome():
    """Standard §16 has 5 claims, but with DPE added the Infra family prompts
    list 6. The 6th claim is what DPE establishes."""
    text = (PROMPTS_DIR / "runtime" / "_cbp_contract.md").read_text(encoding="utf-8")
    # Locate the §7 Final rule block
    final_block = text[text.find("## 7. Final rule"):]
    # Count the bullet claims (lines starting with `- I `)
    bullet_claims = [l for l in final_block.splitlines() if l.strip().startswith("- I ")]
    assert len(bullet_claims) >= 6, (
        f"Final rule must list 6 claims (5 from Standard §16 + 1 DPE-related); "
        f"found {len(bullet_claims)}: {bullet_claims}"
    )
    assert any("explained my reasoning" in c.lower() for c in bullet_claims), (
        "Final rule must include the DPE-derived claim "
        "'I explained my reasoning before seeing the outcome'"
    )


def test_shared_contract_uzbek_register_drops_sen_carve_out():
    """Backend-prompts-audit finding F3 (HIGH): the prior version of §3
    permitted in-case `sen` "if the scene genuinely calls for it" — which
    Uzbek Foundation Review Risk 6.4 forbids without authorization. The
    carve-out must be removed and §3 must require Siz throughout."""
    text = (PROMPTS_DIR / "runtime" / "_cbp_contract.md").read_text(encoding="utf-8")
    # The exact prior carve-out text MUST be gone
    assert "may use `sen` if the scene genuinely calls for it" not in text
    # The new rule should affirmatively require Siz in BOTH layers
    assert "also formal **Siz**" in text or "formal Siz" in text.lower()
    # An explicit Foundation Review reference is the strongest fence
    assert "Foundation Review" in text or "Risk 6.4" in text or "Foundation" in text


def test_shared_contract_uses_case_setup_role_not_student_role():
    """Backend-prompts-audit finding F4 (HIGH): the prior version drifted
    between `case_setup.student_role` (§5 item 5) and `case_setup.role`
    (§6 JSON schema). Pick one; we standardized on `case_setup.role`
    matching the JSON schema."""
    text = (PROMPTS_DIR / "runtime" / "_cbp_contract.md").read_text(encoding="utf-8")
    assert "case_setup.student_role" not in text, (
        "The contract must use `case_setup.role` consistently — "
        "`student_role` indicates the prior naming drift was not fully resolved."
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
