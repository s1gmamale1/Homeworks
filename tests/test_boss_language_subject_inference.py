"""Regression — boss output language must follow the lesson subject, not
the audience-language field on the homework row.

Bug observed 2026-05-20 on HW-20260514-007 (subject=english, row.language=uz):
boss generated Uzbek questions for an English lesson because the earlier
_default_policy only consulted the subject-inference table when the row's
`language` was falsy. Every prod row has language="uz" (audience signal),
so inference never fired and Kimi defaulted to Uzbek output.

Fix: subject inference runs FIRST. If subject maps to a known working
language (english → en, russian → ru), that wins regardless of the row's
audience-language field. Subjects not in the map (biology, history,
math-algebra, etc.) fall through to the row's language, then to "uz".
"""
from __future__ import annotations

import pytest

from server.services.boss_context_builder import _default_policy


def test_english_subject_with_uz_audience_yields_en_output():
    """The real prod shape: row.language='uz' (audience), subject='english'.
    Boss output language MUST be 'en' so questions render in the language
    the lesson content is written in."""
    policy = _default_policy(language="uz", subject="english")
    assert policy["language"] == "en", (
        "English-subject homework with uz audience must emit English boss "
        "questions — the lesson content is in English and the boss tests "
        "what the content teaches"
    )


def test_russian_subject_with_uz_audience_yields_ru_output():
    policy = _default_policy(language="uz", subject="russian")
    assert policy["language"] == "ru"


def test_biology_subject_with_uz_audience_yields_uz_output():
    """Subject not in the language-mapping table → fall through to the
    row's audience language. Biology in Uzbek schools = Uzbek boss."""
    policy = _default_policy(language="uz", subject="biology")
    assert policy["language"] == "uz"


def test_math_algebra_subject_with_uz_audience_yields_uz_output():
    policy = _default_policy(language="uz", subject="math-algebra")
    assert policy["language"] == "uz"


def test_english_subject_with_null_language_still_yields_en():
    """Even when row.language is null (older imports), english subject
    must still produce English boss output."""
    policy = _default_policy(language=None, subject="english")
    assert policy["language"] == "en"


def test_null_subject_null_language_falls_through_to_uz():
    """No subject signal and no row language → platform default uz."""
    policy = _default_policy(language=None, subject=None)
    assert policy["language"] == "uz"


def test_unknown_subject_with_explicit_row_language_keeps_row_value():
    """Subject not in the table + explicit row.language → keep the row's
    language. (e.g. an imported homework with subject='social-studies' and
    language='ru' on a Russian-medium school deployment.)"""
    policy = _default_policy(language="ru", subject="social-studies")
    assert policy["language"] == "ru"


def test_subject_inference_overrides_explicit_row_language():
    """This is the load-bearing assertion: when subject is in the mapping
    table, it WINS even if the row carries a different language. Without
    this, the 2026-05-20 Uzbek-on-English-lesson bug returns."""
    # English subject + non-English row language → English wins.
    assert _default_policy(language="uz", subject="english")["language"] == "en"
    assert _default_policy(language="ru", subject="english")["language"] == "en"
    # Russian subject + non-Russian row language → Russian wins.
    assert _default_policy(language="uz", subject="russian")["language"] == "ru"
    assert _default_policy(language="en", subject="russian")["language"] == "ru"


def test_policy_carries_other_fields_unchanged():
    """Language inference must not break the rest of the policy contract."""
    policy = _default_policy(language="uz", subject="english")
    assert policy["target_weak_topics_first"] is True
    assert policy["avoid_repetition"] is True
    assert policy["max_question_length"] == 900
