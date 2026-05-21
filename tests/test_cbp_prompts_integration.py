"""Integration tier — prompt loading and cross-prompt consistency.

Verifies that all 7 per-subject CBP prompts + the shared contract can be
loaded through `server.config.PROMPTS_DIR`, that no prompt accidentally
references another subject's family wrong, and that the shared contract's
key contract clauses are findable from each subject prompt's perspective.
"""
from __future__ import annotations

import pytest

from server.config import PROMPTS_DIR


SUBJECT_FAMILIES = {
    "math-algebra": "Math",
    "geometriya-g7-11": "Math",
    "biology": "Sciences",
    "physics": "Sciences",
    "kimyo-g7-11": "Sciences",
    "english": "Languages",
    "history": "History",
}


def _load(subject: str) -> str:
    return (PROMPTS_DIR / subject / "case-based-preview.md").read_text(encoding="utf-8")


def test_all_seven_prompts_loadable():
    loaded = {s: _load(s) for s in SUBJECT_FAMILIES.keys()}
    assert len(loaded) == 7
    for s, text in loaded.items():
        assert text.strip(), f"{s}: prompt loaded but empty"


def test_each_prompt_declares_correct_family():
    for subject, expected_family in SUBJECT_FAMILIES.items():
        text = _load(subject)
        assert f"**Family:** {expected_family}" in text, (
            f"{subject}: missing or wrong family declaration "
            f"(expected '**Family:** {expected_family}')"
        )


def test_shared_contract_loads_via_runtime_path():
    """Mirrors `tutor.py`'s `RUNTIME_PROMPTS = PROMPTS_DIR / 'runtime'` access."""
    path = PROMPTS_DIR / "runtime" / "_cbp_contract.md"
    text = path.read_text(encoding="utf-8")
    assert "Case-Based Preview" in text
    assert "Shared Generation Contract" in text


def test_no_subject_prompt_references_wrong_family():
    """Math prompts shouldn't reference 'Sciences family' and vice versa."""
    math_subjects = {s for s, f in SUBJECT_FAMILIES.items() if f == "Math"}
    sciences_subjects = {s for s, f in SUBJECT_FAMILIES.items() if f == "Sciences"}

    for s in math_subjects:
        text = _load(s)
        # Math may reference Math; should NOT declare Sciences as its family
        assert "**Family:** Sciences" not in text

    for s in sciences_subjects:
        text = _load(s)
        assert "**Family:** Math" not in text


def test_every_subject_prompt_mentions_checkpoint_kinds():
    """The three kinds (identify, decide, justify) must appear in every
    subject prompt — these are the structural anchor of CBP."""
    for subject in SUBJECT_FAMILIES:
        text = _load(subject).lower()
        for kind in ("identify", "decide", "justify"):
            assert kind in text, f"{subject}: missing checkpoint kind '{kind}'"


def test_every_subject_prompt_references_shared_validation():
    """Every subject prompt should defer to the shared contract's §5
    checklist (or §14 of the Standard) for the validation step."""
    for subject in SUBJECT_FAMILIES:
        text = _load(subject)
        assert "_cbp_contract.md" in text, (
            f"{subject}: must reference _cbp_contract.md as the validation source"
        )
        # Either "18-item" or §5 mention or "checklist" must appear
        assert any(t in text for t in ("18-item", "checklist", "§5", "§5")), (
            f"{subject}: must reference the validation checklist"
        )


def test_history_prompt_derives_from_standard_section_9_6():
    """History has no Infra family-prompt — it derives from CBP Standard
    §9.6. The prompt MUST note this provenance explicitly."""
    text = _load("history")
    assert "no Infra family-prompt" in text or "Standard §9.6" in text or "Standard §9.6" in text
