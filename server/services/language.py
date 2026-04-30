"""Language-subject registry.

Single source of truth for which subjects use the Language Mastery Rubric (LMR)
instead of the Anchored Mastery Rubric (AMR). The grader (`tutor.check_answer`)
and the runtime template both consult this list to pick the right rubric +
prompt + UI behaviour.

Adding a new language subject is a one-line change here. Anything not in this
set falls through to the default AMR (math/science/social-studies) path.
"""
from __future__ import annotations


# Subjects that map to family `til-fanlar` and use LMR.
LANGUAGE_SUBJECTS: frozenset[str] = frozenset({
    "english",
    "ona-tili",
    "rus-tili",
    # Aliases / variants that may appear in older homeworks
    "ingliz-tili",
    "ingliz-tili-g1-11",
    "ona-tili-g1-11",
    "rus-tili-g1-11",
})


def is_language_subject(subject: str | None) -> bool:
    """True if `subject` should be graded with LMR rather than AMR."""
    if not subject:
        return False
    return subject.lower().strip() in LANGUAGE_SUBJECTS


def rubric_for_subject(subject: str | None) -> str:
    """Return rubric key — 'lmr' for language, 'amr' otherwise."""
    return "lmr" if is_language_subject(subject) else "amr"
