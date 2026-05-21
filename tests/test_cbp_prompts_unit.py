"""Unit tier — per-file structural assertions on each CBP prompt.

Each subject prompt is a Markdown contract. The unit tests check that
required sections exist and that each prompt references the shared
contract correctly.
"""
from __future__ import annotations

import pytest

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

SHARED_CONTRACT = PROMPTS_DIR / "runtime" / "_cbp_contract.md"


@pytest.fixture(scope="module")
def shared_text() -> str:
    return SHARED_CONTRACT.read_text(encoding="utf-8")


@pytest.fixture(scope="module", params=SUBJECTS)
def subject(request) -> str:
    return request.param


@pytest.fixture(scope="module")
def subject_text(subject) -> str:
    return (PROMPTS_DIR / subject / "case-based-preview.md").read_text(encoding="utf-8")


def test_shared_contract_exists():
    assert SHARED_CONTRACT.exists()
    assert SHARED_CONTRACT.stat().st_size > 1000  # non-trivial content


def test_shared_contract_mentions_18_item_checklist(shared_text):
    assert "18-item validation checklist" in shared_text
    assert "Standard §14" in shared_text or "Standard §14" in shared_text


def test_shared_contract_lists_forbid_rules(shared_text):
    for forbid in ("#3", "#4", "#5", "#6", "#19", "#20"):
        assert forbid in shared_text, f"Forbid rule {forbid} missing from shared contract"


def test_shared_contract_lists_three_checkpoint_kinds(shared_text):
    for kind in ("identify", "decide", "justify"):
        assert kind.lower() in shared_text.lower()


def test_shared_contract_describes_uzbek_register(shared_text):
    assert "formal" in shared_text.lower()
    assert "Siz" in shared_text
    # Negative reference — `sen` mentioned as a constraint
    assert "sen" in shared_text.lower()


def test_shared_contract_specifies_pass_condition(shared_text):
    assert "ge_2_of_3" in shared_text or "≥2 of 3" in shared_text or "2 of 3" in shared_text


def test_per_subject_file_exists(subject):
    path = PROMPTS_DIR / subject / "case-based-preview.md"
    assert path.exists(), f"Missing CBP prompt for subject: {subject}"


def test_per_subject_file_non_trivial(subject_text):
    assert len(subject_text) > 500, "Subject prompt looks too short to be useful"


def test_per_subject_references_shared_contract(subject_text):
    assert "_cbp_contract.md" in subject_text, (
        "Subject prompt must reference the shared contract"
    )


def test_per_subject_declares_family(subject_text):
    """Each per-subject file must declare which family it belongs to."""
    assert "**Family:**" in subject_text


def test_per_subject_has_case_archetype_section(subject_text):
    assert "Subject case archetype" in subject_text or "case archetype" in subject_text.lower()


def test_per_subject_has_checkpoint_shapes_section(subject_text):
    assert "Checkpoint shapes" in subject_text or "checkpoint shapes" in subject_text.lower()


def test_per_subject_has_validation_section(subject_text):
    assert "Validation" in subject_text or "validation" in subject_text.lower()


def test_per_subject_has_soft_retry_rule(subject_text):
    assert "Forbid #19" in subject_text or "soft-retry" in subject_text.lower() or "regenerated variant" in subject_text.lower()


def test_per_subject_has_anti_patterns(subject_text):
    """Each subject names at least one bad-case example so the generator
    learns what NOT to produce."""
    assert "Bad" in subject_text or "Anti-patterns" in subject_text or "Avoid" in subject_text
