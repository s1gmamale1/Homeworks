"""Regression tests — authored boss_questions[] feed BossContext as reference pool.

Guards the invariant that BossContext.authored_question_stems is populated from
content_json.boss_questions, answer-leak keys are stripped, difficulty is inferred
from dmg, and empty pools yield None floor.
"""
from __future__ import annotations

import asyncio

import pytest

from server.services.boss_context_builder import build_boss_context


# ---------------------------------------------------------------------------
# Fixture helpers — mirror _make_homework pattern from test_plan5_dynamic_boss.py
# ---------------------------------------------------------------------------


def _make_homework_with_boss_questions(client, *, hw_id_hint: str = "stems-hw") -> str:
    """Insert a homework with three boss_questions (mix of dmg values, one with
    answer-leak keys) so the stem-extraction path is exercised."""
    payload = {
        "title": f"Boss stems test ({hw_id_hint})",
        "subject": "english",
        "grade": 8,
        "mode": "hard",
        "family": "til-fanlar",
        "content_json": {
            "title": f"Boss stems test ({hw_id_hint})",
            "subject": "english",
            "grade": 8,
            "language": "uz",
            "boss_questions": [
                {
                    "q": "Q1",
                    "tags": "[Bloom: L2]",
                    "dmg": 10,
                    "ans": ["leak"],
                    "answer_spec": {"type": "text_exact"},
                },
                {
                    "q": "Q2",
                    "tags": "[Bloom: L3]",
                    "dmg": 20,
                },
                {
                    "q": "Q3",
                    "dmg": 30,
                },
            ],
        },
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _make_homework_no_boss_questions(client, *, hw_id_hint: str = "stems-empty") -> str:
    """Insert a homework with no boss_questions key."""
    payload = {
        "title": f"Boss stems empty test ({hw_id_hint})",
        "subject": "english",
        "grade": 8,
        "mode": "hard",
        "family": "til-fanlar",
        "content_json": {
            "title": f"Boss stems empty test ({hw_id_hint})",
            "subject": "english",
            "grade": 8,
            "language": "uz",
        },
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_build_boss_context_includes_authored_question_stems(client):
    """authored_question_stems populated from content_json.boss_questions."""
    hw_id = _make_homework_with_boss_questions(client, hw_id_hint="t-stems-1")

    ctx = asyncio.run(
        build_boss_context(
            session_id="stems_sess_001",
            homework_id=hw_id,
            asked_questions=[],
            recent_boss_phrases=[],
        )
    )

    assert len(ctx.authored_question_stems) == 3
    for stem in ctx.authored_question_stems:
        assert "question_text" in stem
        assert "tags" in stem
        assert "hint" in stem
        assert "authored_difficulty" in stem


def test_authored_stems_scrubbed_of_answer_keys(client):
    """No answer-leak keys survive into authored_question_stems."""
    hw_id = _make_homework_with_boss_questions(client, hw_id_hint="t-stems-2")

    ctx = asyncio.run(
        build_boss_context(
            session_id="stems_sess_002",
            homework_id=hw_id,
            asked_questions=[],
            recent_boss_phrases=[],
        )
    )

    leak_keys = {"ans", "answer_spec", "accepted_answers", "expected", "correct"}
    for stem in ctx.authored_question_stems:
        for key in leak_keys:
            assert key not in stem, f"Answer-leak key '{key}' found in stem: {stem}"


def test_authored_difficulty_floor_is_pool_max(client):
    """authored_difficulty_floor equals the hardest authored_difficulty in the pool."""
    hw_id = _make_homework_with_boss_questions(client, hw_id_hint="t-stems-3")

    ctx = asyncio.run(
        build_boss_context(
            session_id="stems_sess_003",
            homework_id=hw_id,
            asked_questions=[],
            recent_boss_phrases=[],
        )
    )

    # dmg values are [10, 20, 30] → difficulties [easy, medium, hard] → floor = hard
    assert ctx.authored_difficulty_floor == "hard"


def test_empty_boss_questions_yields_empty_stems_and_null_floor(client):
    """When boss_questions is absent, stems == [] and floor is None."""
    hw_id = _make_homework_no_boss_questions(client, hw_id_hint="t-stems-4")

    ctx = asyncio.run(
        build_boss_context(
            session_id="stems_sess_004",
            homework_id=hw_id,
            asked_questions=[],
            recent_boss_phrases=[],
        )
    )

    assert ctx.authored_question_stems == []
    assert ctx.authored_difficulty_floor is None


# ---------------------------------------------------------------------------
# Option B fix (2026-05-13 audit) — filter language-drifted asked_questions
# ---------------------------------------------------------------------------


def test_build_boss_context_filters_english_asked_questions_on_uz_homework(client):
    """Option B: when a uz/ru homework has accumulated past generations that
    drifted to English (pre-fix bug), those entries must be filtered OUT of
    the asked_questions[] before sending to Kimi. Otherwise the English
    prior questions act as in-context examples and pull subsequent
    generations toward English even with the v4 language banner."""
    hw_id = _make_homework_with_boss_questions(client, hw_id_hint="t-filter-1")

    # Mix of English (drifted) and Uzbek (clean) prior generations.
    asked = [
        {
            "question_id": "gbq_en1",
            "question_text": "A student measures the length of a school bench as 200 cm with a possible error of 5 cm. What is the relative error?",
            "target_skill": "sign_error",
            "difficulty": "medium",
        },
        {
            "question_id": "gbq_en2",
            "question_text": "A student measures the length of a pencil as 175 mm with a possible error of 2 mm. What is the relative error as a percentage?",
            "target_skill": "sign_error",
            "difficulty": "medium",
        },
        {
            "question_id": "gbq_uz1",
            "question_text": "100 ga 5% nisbiy xatolik bo'yicha o'lchash. Aniq xatolik nechadan iborat?",
            "target_skill": "nisbiy xatolik",
            "difficulty": "medium",
        },
        {
            "question_id": "gbq_uz2",
            "question_text": "Yosh o'quvchining taqvimida o'qituv soati 45 da 5 ta minut. Nisbiy xatolik qanday aniqlanadi?",
            "target_skill": "nisbiy xatolik",
            "difficulty": "medium",
        },
    ]

    ctx = asyncio.run(
        build_boss_context(
            session_id="filter_sess_001",
            homework_id=hw_id,
            asked_questions=asked,
            recent_boss_phrases=[],
        )
    )

    # The English entries must be gone. Only the 2 Uzbek entries should
    # survive into ctx.asked_questions.
    surviving_ids = {q.get("question_id") for q in ctx.asked_questions}
    assert "gbq_en1" not in surviving_ids, (
        "Option B regression — English asked_question 'gbq_en1' was not filtered"
    )
    assert "gbq_en2" not in surviving_ids, (
        "Option B regression — English asked_question 'gbq_en2' was not filtered"
    )
    assert "gbq_uz1" in surviving_ids
    assert "gbq_uz2" in surviving_ids
    assert len(ctx.asked_questions) == 2


def test_default_policy_infers_language_from_english_subject():
    """Fix B (2026-05-13): when content_json.language is null but subject is
    'english', _default_policy must infer language='en'. Without this,
    HW-20260513-004 (imported from sigmaai with null language) caused Kimi
    to default to Uzbek output on an English lesson."""
    from server.services.boss_context_builder import _default_policy
    policy = _default_policy(language=None, subject="english")
    assert policy["language"] == "en", (
        f"Expected inferred language='en' from subject='english', got "
        f"{policy['language']!r}"
    )


def test_default_policy_falls_back_to_uz_for_unknown_subject():
    """Platform-default fallback: unknown subject + null language → 'uz'
    (the platform's primary audience). Tested separately so we can change
    this default later without breaking other tests."""
    from server.services.boss_context_builder import _default_policy
    policy = _default_policy(language=None, subject="some-new-subject")
    assert policy["language"] == "uz"
    # Also: completely empty.
    assert _default_policy(language=None, subject=None)["language"] == "uz"


def test_build_boss_context_does_not_filter_asked_questions_on_english_homework(client):
    """Counterpart: on an English homework, English asked_questions are
    legitimate and must NOT be filtered (otherwise we'd kill anti-repetition
    for English-language boss flows)."""
    # Re-use the fixture but flip language to English.
    payload = {
        "title": "English boss test",
        "subject": "english",
        "grade": 8,
        "mode": "hard",
        "family": "til-fanlar",
        "content_json": {
            "title": "English boss test",
            "subject": "english",
            "grade": 8,
            "language": "en",
            "boss_questions": [
                {"q": "What does X mean?", "tags": "[Bloom: L2]", "dmg": 10},
            ],
        },
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200
    hw_id = resp.json()["id"]

    asked = [
        {
            "question_id": "gbq_a",
            "question_text": "A student measures the length of a school bench with a ruler.",
            "target_skill": "measurement",
            "difficulty": "medium",
        },
    ]
    ctx = asyncio.run(
        build_boss_context(
            session_id="en_sess_001",
            homework_id=hw_id,
            asked_questions=asked,
            recent_boss_phrases=[],
        )
    )
    # English homework: English asked_questions must pass through.
    assert len(ctx.asked_questions) == 1
    assert ctx.asked_questions[0]["question_id"] == "gbq_a"


# ---------------------------------------------------------------------------
# Bug #3 follow-up (2026-05-14) — scrub English snake_case from weak_topics
# / strong_topics so the LLM never echoes them into target_skill.
#
# These tests cover the helper directly. The end-to-end path (boss_sessions
# DB row → boss_question_generate prompt) is covered by existing live tests
# of the LLM call; the unit-level scrub guarantee is enforced here.
# ---------------------------------------------------------------------------


def test_scrub_drops_english_snake_case_terms_on_uz_lesson():
    """The exact tokens observed in production (`sign_error`, `format_error`)
    on a Uzbek homework must be dropped before the LLM sees them."""
    from server.services.boss_context_builder import _scrub_english_snake_case_topics

    cleaned = _scrub_english_snake_case_topics(
        ["sign_error", "format_error", "nisbiy xatolik"],
        language="uz",
    )
    assert "sign_error" not in cleaned
    assert "format_error" not in cleaned
    assert "nisbiy xatolik" in cleaned, (
        "Legitimate Uzbek terms (with spaces) must survive the scrub"
    )


def test_scrub_drops_english_snake_case_terms_on_ru_lesson():
    """Russian lessons get the same treatment."""
    from server.services.boss_context_builder import _scrub_english_snake_case_topics

    cleaned = _scrub_english_snake_case_topics(
        ["measurement_error", "относительная ошибка"],
        language="ru",
    )
    assert "measurement_error" not in cleaned
    assert "относительная ошибка" in cleaned


def test_scrub_keeps_snake_case_on_english_lesson():
    """English lessons legitimately use snake_case skill identifiers — the
    scrub must pass them through unchanged."""
    from server.services.boss_context_builder import _scrub_english_snake_case_topics

    cleaned = _scrub_english_snake_case_topics(
        ["sign_error", "format_error", "relative_error"],
        language="en",
    )
    assert cleaned == ["sign_error", "format_error", "relative_error"]


def test_scrub_skips_filter_when_language_is_none():
    """When language is unknown (None), the scrub is a no-op rather than
    silently destroying input topics — caller decides the fallback."""
    from server.services.boss_context_builder import _scrub_english_snake_case_topics

    cleaned = _scrub_english_snake_case_topics(
        ["sign_error", "format_error"],
        language=None,
    )
    assert cleaned == ["sign_error", "format_error"]


def test_scrub_keeps_single_token_english_terms():
    """A single-token English word ('measurement') without underscores isn't
    snake_case — it's a borrowed term that can coexist with Uzbek text.
    Pattern is conservative: only `word_word_...` shapes are filtered."""
    from server.services.boss_context_builder import _scrub_english_snake_case_topics

    cleaned = _scrub_english_snake_case_topics(
        ["measurement", "PISA", "Bloom", "sign_error"],
        language="uz",
    )
    # measurement, PISA, Bloom survive; sign_error is dropped.
    assert "measurement" in cleaned
    assert "PISA" in cleaned
    assert "Bloom" in cleaned
    assert "sign_error" not in cleaned


def test_is_english_snake_case_term_helper():
    """Sanity check on the underlying detector — pinned so the regex
    behavior doesn't accidentally widen and start flagging legitimate
    Uzbek phrases that happen to share a structural prefix."""
    from server.services.boss_context_builder import _is_english_snake_case_term

    # True cases — canonical snake_case identifiers.
    assert _is_english_snake_case_term("sign_error") is True
    assert _is_english_snake_case_term("format_error") is True
    assert _is_english_snake_case_term("relative_error_calc") is True
    assert _is_english_snake_case_term("SIGN_ERROR") is True  # case-insensitive

    # False cases — must NOT match.
    assert _is_english_snake_case_term("nisbiy xatolik") is False  # space
    assert _is_english_snake_case_term("measurement") is False     # single token
    assert _is_english_snake_case_term("") is False                # empty
    assert _is_english_snake_case_term("error-handling") is False  # hyphen
    assert _is_english_snake_case_term("error_") is False          # trailing underscore (no second token)


# ---------------------------------------------------------------------------
# Bug A (2026-05-14) — strip HTML tags from authored question_text
#
# Authored stems written with `<strong>...</strong>` were leaking into the
# LLM prompt and back to the runtime, which renders via textContent and
# displays the markup as literal characters. Strip server-side so neither
# the LLM nor the student ever sees the raw HTML.
# ---------------------------------------------------------------------------


def test_strip_html_tags_removes_emphasis_markup():
    """The exact case observed in HW-20260513-004."""
    from server.services.boss_context_builder import _strip_html_tags

    raw = '<strong>Translate to English</strong>, using "have to"'
    assert _strip_html_tags(raw) == 'Translate to English, using "have to"'


def test_strip_html_tags_handles_multiple_tag_types():
    """<em>, <p>, <br>, self-closing tags — all should be removed."""
    from server.services.boss_context_builder import _strip_html_tags

    raw = "<p>Hello<br/><em>world</em><br><span class='x'>!</span></p>"
    assert _strip_html_tags(raw) == "Helloworld!"


def test_strip_html_tags_unescapes_entities():
    """&amp; → &, &lt; → <, &gt; → >, etc."""
    from server.services.boss_context_builder import _strip_html_tags

    raw = "AT&amp;T &lt;CEO&gt; said &quot;hello&quot;"
    assert _strip_html_tags(raw) == 'AT&T <CEO> said "hello"'


def test_strip_html_tags_preserves_plain_text_unchanged():
    """No HTML, no change. Idempotent on already-clean text."""
    from server.services.boss_context_builder import _strip_html_tags

    raw = "Nisbiy xatolikni hisoblang."
    assert _strip_html_tags(raw) == "Nisbiy xatolikni hisoblang."


def test_strip_html_tags_returns_empty_for_none_or_non_string():
    """Defensive — None, ints, dicts must yield empty string, not raise."""
    from server.services.boss_context_builder import _strip_html_tags

    assert _strip_html_tags(None) == ""
    assert _strip_html_tags(42) == ""
    assert _strip_html_tags({"q": "x"}) == ""


def test_build_boss_context_strips_html_from_authored_stems(client):
    """End-to-end: authored stem with <strong> markup must reach
    authored_question_stems[].question_text as plain text — the LLM never
    sees the markup."""
    payload = {
        "title": "html-strip test",
        "subject": "english",
        "grade": 8,
        "mode": "hard",
        "family": "til-fanlar",
        "content_json": {
            "title": "html-strip test",
            "subject": "english",
            "grade": 8,
            "language": "en",
            "boss_questions": [
                {
                    "q": "<strong>Translate to English</strong>, using \"have to\"",
                    "tags": "[Bloom: L3]",
                    "dmg": 10,
                },
            ],
        },
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, resp.text
    hw_id = resp.json()["id"]

    ctx = asyncio.run(
        build_boss_context(
            session_id="html_strip_sess_001",
            homework_id=hw_id,
            asked_questions=[],
            recent_boss_phrases=[],
        )
    )

    assert len(ctx.authored_question_stems) == 1
    stem_text = ctx.authored_question_stems[0]["question_text"]
    assert "<strong>" not in stem_text
    assert "</strong>" not in stem_text
    assert "Translate to English" in stem_text, (
        f"text content must survive the strip; got {stem_text!r}"
    )
