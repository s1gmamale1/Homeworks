"""Shared test factories for the Case-Based Preview arc (PR #1+).

Returns dict shapes (not Pydantic models) so each test can exercise
validation explicitly. Centralized here because 5+ test files need the
same minimal valid CBP payload — inlining would duplicate ~30 LOC per file
and drift over time.
"""
from __future__ import annotations

from typing import Any, Dict


def valid_checkpoint(kind: str = "identify", **overrides) -> Dict[str, Any]:
    cp: Dict[str, Any] = {
        "kind": kind,
        "question": f"Sample question for {kind} checkpoint",
        "options": ["A", "B", "C", "D"],
        "answer_spec": {"type": "option_index", "option_index": 1},
        "learning_block_after": {
            "body": f"Explanation after {kind}.",
            "consequence_preview": "Agar boshqacha tanlasangiz, natija boshqa bo'lardi.",
        },
        "retake_variants": [],
    }
    cp.update(overrides)
    return cp


def valid_cbp_dict(**overrides) -> Dict[str, Any]:
    cbp: Dict[str, Any] = {
        "title": "Test CBP",
        "metadata": {"subject": "math-algebra", "grade": 6, "topic": "fractions"},
        "source_extraction": {
            "core_concept": "dividing a proper fraction by a whole number",
            "main_rule": "a/b ÷ n = a/(b·n)",
            "key_terms": ["proper fraction", "natural number"],
            "common_mistake": "multiplying instead of dividing",
        },
        "visual_plan": {},
        "case_setup": {
            "story": "Siz sinfdoshlaringizga juice tarqatasiz.",
            "role": "yordamchi sotuvchi",
            "task": "3/5 litr juiceni 3 ta kosaga teng bo'lish.",
        },
        "checkpoints": [
            valid_checkpoint("identify"),
            valid_checkpoint("decide"),
            valid_checkpoint("justify"),
        ],
        "final_simulation": {
            "correct_path": "3/5 ÷ 3 = 1/5 — har kosada 1/5 litr juice.",
            "wrong_path": "3/5 × 3 = 9/5 — bu mumkin emas; faqat 3/5 mavjud.",
            "visual_description": "Three cups, each receiving 1/5 of the bottle.",
        },
        "feedback_summary": {
            "student_understood": "fraction division",
            "mistake_appeared": None,
            "what_to_review": "section A",
        },
        "completion_rules": {"pass_condition": "ge_2_of_3"},
    }
    cbp.update(overrides)
    return cbp


def full_content_json_with_cbp(**overrides) -> Dict[str, Any]:
    cj: Dict[str, Any] = {
        "meta": {"title": "CBP test HW", "subject_display": "Math", "section": "1"},
        "panels": [],
        "quotes": [],
        # Flat shape — matches FlashcardItem schema (`term`/`def` keys).
        "flashcards": [{"term": "Proper fraction", "def": "Numerator < denominator"}],
        "memory_sprint": [],
        "boss_questions": [],
        "flow_version": "v2",
        "case_based_preview": valid_cbp_dict(),
    }
    cj.update(overrides)
    return cj
