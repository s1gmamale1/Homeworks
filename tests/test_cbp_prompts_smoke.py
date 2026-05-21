"""Smoke tier — prompts directory health and minimum file sizes."""
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


def test_prompts_dir_exists():
    assert PROMPTS_DIR.exists()
    assert PROMPTS_DIR.is_dir()


def test_runtime_subdir_has_shared_contract():
    contract = PROMPTS_DIR / "runtime" / "_cbp_contract.md"
    assert contract.exists()
    assert contract.is_file()


def test_each_subject_has_cbp_prompt_file():
    for subject in SUBJECTS:
        path = PROMPTS_DIR / subject / "case-based-preview.md"
        assert path.exists(), f"Missing: {path}"
        assert path.is_file()


def test_no_subject_cbp_prompt_is_empty():
    """Catch the 'committed an empty file' regression."""
    for subject in SUBJECTS:
        path = PROMPTS_DIR / subject / "case-based-preview.md"
        size = path.stat().st_size
        assert size > 200, f"{subject}/case-based-preview.md is suspiciously small ({size} bytes)"


def test_shared_contract_is_non_trivial():
    contract = PROMPTS_DIR / "runtime" / "_cbp_contract.md"
    assert contract.stat().st_size > 2000


def test_app_still_imports():
    from server.app import app
    assert app is not None
