"""Regression — boss-answer-checker prompt (Bug B + Bug C fixes, 2026-05-14).

v1 hardcoded "typically Uzbek" for feedback AND example misconception tags
"sign_error" / "meaning_in_context". On an English homework that produced
Uzbek feedback ("Siz 'has to' o'rniga 'have to' ishlatdingiz..."); on uz/ru
homeworks it taught the LLM to emit English snake_case tags that then
poisoned weak_topics → boss-question-generator (the Bug #3 origin loop).

v2 (Bug B):
  - Adds front-loaded language banner ("🔒 OUTPUT LANGUAGE — STRICT, FIRST RULE")
  - Adds `language` to "Allowed inputs"
  - Rule 7 (Feedback) reads from input, not "typically Uzbek"
  - Rule 3 (Misconception tags) forbids English snake_case on uz/ru
  - PROMPT_VERSION["boss-answer-checker"] = "v2"
  - check_boss_answer payload now includes `language`

v3 (Bug C):
  - Adds rule 1a "Semantic equivalence" — accept grammatically valid
    variants of the canonical even when surface form differs. Protects
    students when the LLM-generated question/rubric contains typos
    (e.g. "Does he have to come?" rejected because rubric expected "has to").
  - PROMPT_VERSION["boss-answer-checker"] = "v3"
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest


def _prompt_text() -> str:
    path = (
        Path(__file__).resolve().parent.parent
        / "server" / "prompts" / "runtime" / "boss-answer-checker.md"
    )
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Version + structure
# ---------------------------------------------------------------------------


def test_prompt_version_bumped_to_v4():
    # Bumped v3 -> v4 for the Boss-Arena coverage-based grading rework: the
    # checker now also scores per-axis `coverage` (why/how/what, 0..1).
    body = _prompt_text()
    assert "boss-answer-checker:v4" in body, (
        "Prompt version header must say v4 — v2 added language banner "
        "(Bug B); v3 added semantic-equivalence (Bug C); v4 adds per-axis "
        "coverage scoring (Boss-Arena spec §6)"
    )


def test_prompt_version_map_pinned_to_v4():
    """The Python-side PROMPT_VERSION map must match the .md header so
    ai_call_logs records the correct version on every check_boss_answer."""
    from server.services.boss_dynamic import PROMPT_VERSION
    assert PROMPT_VERSION["boss-answer-checker"] == "v4"


def test_prompt_scores_why_how_what_coverage():
    """Boss-Arena (spec §6): the checker must score per-axis coverage for the
    Why→How→What chain. Pin the `coverage` key + the three axes so the
    contract can't silently regress, and confirm the answer-leak guard
    survives (feedback must still never reveal the canonical)."""
    body = _prompt_text()
    assert "coverage" in body, (
        "prompt must instruct the model to emit a `coverage` object "
        "(per-axis why/how/what scoring, spec §6)"
    )
    for axis in ("why", "how", "what"):
        assert axis in body, f"prompt must reference the {axis!r} coverage axis"
    # Answer-leak guard must remain.
    assert "Never reveal" in body or "never reveal" in body, (
        "coverage scoring must NOT relax the no-canonical-leak rule"
    )


def test_prompt_has_front_loaded_language_banner():
    """The language banner MUST appear before the role/rules so the LLM
    treats it as overriding any later language guidance (same pattern as
    the v4 generator)."""
    body = _prompt_text()
    # Banner appears in the first 800 chars (before "## Role").
    head = body[:800]
    assert "OUTPUT LANGUAGE" in head and "STRICT" in head and "FIRST RULE" in head, (
        "Front-loaded language banner missing or too far down the prompt"
    )
    # Banner explicitly names the field that drives the language.
    assert "INPUT.language" in head or "INPUT.boss_policy.language" in head


# ---------------------------------------------------------------------------
# 2. Inputs declaration includes `language`
# ---------------------------------------------------------------------------


def test_prompt_allowed_inputs_includes_language():
    body = _prompt_text()
    # Find the Allowed inputs section
    allowed_idx = body.find("## Allowed inputs")
    next_section_idx = body.find("## Hard rules", allowed_idx)
    assert allowed_idx >= 0 and next_section_idx > allowed_idx
    section = body[allowed_idx:next_section_idx]
    assert "`language`" in section, (
        "Allowed inputs section must explicitly declare `language` so the "
        "LLM knows the field exists and what values it takes"
    )


# ---------------------------------------------------------------------------
# 3. Hard rules — feedback language + tag language
# ---------------------------------------------------------------------------


def test_prompt_feedback_rule_reads_language_from_input():
    """Rule 7 must instruct the LLM to read `INPUT.language` for feedback
    language, NOT default to 'typically Uzbek' like v1."""
    body = _prompt_text()
    assert "typically Uzbek" not in body, (
        "v1's 'typically Uzbek' default must be REMOVED — that's exactly "
        "the bug producing Uzbek feedback on English homeworks"
    )
    # The feedback rule must reference INPUT.language
    feedback_section_start = body.find("Feedback")
    assert feedback_section_start > 0
    feedback_section = body[feedback_section_start:feedback_section_start + 400]
    assert "language" in feedback_section.lower(), (
        "Feedback rule must reference the language field"
    )


def test_prompt_has_semantic_equivalence_rule():
    """Bug C: v3 must contain a 'semantic equivalence' rule that overrides
    strict-literal rubric matching when the student's answer is
    grammatically valid in the target language."""
    body = _prompt_text()
    assert "Semantic equivalence" in body or "semantic equivalence" in body, (
        "v3 must include a Semantic equivalence rule (rule 1a) so grammar-"
        "correct variants like 'Does he have to come?' aren't rejected"
    )
    # Must mention auxiliary verbs since that's the canonical example.
    assert "Do/Does/Did" in body or "auxiliary" in body.lower(), (
        "Semantic equivalence rule must include the English-auxiliary-verb "
        "example so the LLM recognises the 'Does he have to' pattern"
    )


def test_prompt_acknowledges_question_typos():
    """Bug C: prompt must instruct the LLM to prefer the student's
    grammatically-corrected version when the question itself contains a
    typo (LLM generator occasionally produces buggy stems)."""
    body = _prompt_text()
    # The rule must mention question-side typos / grammar errors.
    assert "typo" in body.lower() or "grammar error" in body.lower(), (
        "Rule 1a must call out generator-side typos so students aren't "
        "penalised for fixing the question's mistake"
    )


def test_prompt_misconception_tag_rule_forbids_english_snake_case_on_uz_ru():
    """Rule 3 must explicitly forbid English snake_case misconception tags
    on uz/ru homeworks — that's the origin of the weak_topics poison loop."""
    body = _prompt_text()
    # Locate the misconception_tags rule.
    rule_idx = body.find("isconception")
    assert rule_idx >= 0, "Misconception tags rule must exist"
    rule_window = body[rule_idx:rule_idx + 800]
    # The rule must mention language-appropriate tags.
    assert "language" in rule_window.lower()
    # Explicit prohibition of English snake_case on uz/ru.
    assert "snake_case" in rule_window or "uz" in rule_window.lower(), (
        "Rule must explicitly call out English snake_case as forbidden on "
        "uz/ru lessons"
    )


# ---------------------------------------------------------------------------
# 4. check_boss_answer payload includes `language`
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_boss_answer_threads_language_into_payload():
    """When the route passes `language='en'`, the prompt payload sent to the
    gateway must include `"language": "en"` so the LLM can read it via
    INPUT.language. Without this, v2's language banner has nothing to read
    and the LLM falls back to its own heuristic."""
    from server.services import boss_dynamic
    from server.schemas.ai_contracts import BossAnswerCheckResult

    captured_prompts: list[str] = []

    async def _fake_generate_structured(*args, **kwargs):
        captured_prompts.append(kwargs.get("prompt", "") or (args[1] if len(args) >= 2 else ""))
        return BossAnswerCheckResult(
            is_correct=True,
            score=0.95,
            confidence=0.9,
            feedback="ok",
            misconception_tags=[],
            damage_multiplier=1.0,
            difficulty_recommendation="stay",
            should_retry_same_skill=False,
        )

    with patch(
        "server.services.boss_dynamic.ai_gateway.generate_structured",
        side_effect=_fake_generate_structured,
    ):
        await boss_dynamic.check_boss_answer(
            question_text="Test question",
            expected_answer={"canonical": "test"},
            rubric={"full_credit": ["test"]},
            student_answer="test",
            target_skill="translation",
            difficulty="medium",
            language="en",
        )

    assert captured_prompts, "ai_gateway.generate_structured must be called"
    full_prompt = captured_prompts[0]
    # The payload section (after the prompt template) must include language.
    # The INPUT block is serialized JSON, so look for `"language": "en"`.
    assert '"language": "en"' in full_prompt, (
        "Payload sent to the answer-checker must include `language` so the "
        "v2 prompt's language banner can read it"
    )


@pytest.mark.asyncio
async def test_check_boss_answer_accepts_uz_language():
    """Sanity check — Uzbek lessons must also thread cleanly."""
    from server.services import boss_dynamic
    from server.schemas.ai_contracts import BossAnswerCheckResult

    captured_prompts: list[str] = []

    async def _fake_generate_structured(*args, **kwargs):
        captured_prompts.append(kwargs.get("prompt", "") or (args[1] if len(args) >= 2 else ""))
        return BossAnswerCheckResult(
            is_correct=True, score=0.95, confidence=0.9, feedback="To'g'ri",
            misconception_tags=[], damage_multiplier=1.0,
            difficulty_recommendation="stay", should_retry_same_skill=False,
        )

    with patch(
        "server.services.boss_dynamic.ai_gateway.generate_structured",
        side_effect=_fake_generate_structured,
    ):
        await boss_dynamic.check_boss_answer(
            question_text="Test",
            expected_answer={"canonical": "5%"},
            rubric={"full_credit": ["5%"]},
            student_answer="5%",
            target_skill="nisbiy xatolik",
            difficulty="medium",
            language="uz",
        )

    assert '"language": "uz"' in captured_prompts[0]


@pytest.mark.asyncio
async def test_check_boss_answer_accepts_none_language_for_back_compat():
    """Older callers that haven't been updated yet pass language=None
    (default) — must not crash. Payload contains `"language": null` and the
    prompt falls back to its own heuristic in that case."""
    from server.services import boss_dynamic
    from server.schemas.ai_contracts import BossAnswerCheckResult

    async def _fake_generate_structured(*args, **kwargs):
        return BossAnswerCheckResult(
            is_correct=True, score=0.95, confidence=0.9, feedback="ok",
            misconception_tags=[], damage_multiplier=1.0,
            difficulty_recommendation="stay", should_retry_same_skill=False,
        )

    with patch(
        "server.services.boss_dynamic.ai_gateway.generate_structured",
        side_effect=_fake_generate_structured,
    ):
        # No language kwarg — defaults to None.
        verdict = await boss_dynamic.check_boss_answer(
            question_text="Test",
            expected_answer={"canonical": "x"},
            rubric={"full_credit": ["x"]},
            student_answer="x",
            target_skill="t",
            difficulty="medium",
        )
    assert verdict.is_correct is True


# ---------------------------------------------------------------------------
# 5. End-to-end via the submit-answer route — language flows from homework
# ---------------------------------------------------------------------------


def test_boss_submit_answer_passes_homework_language_to_checker(client, monkeypatch):
    """The route must read homework.content_json.language and thread it to
    check_boss_answer. Regression for the exact bug: English homework →
    Uzbek feedback because the route never told the checker what language
    to use."""
    # We can't easily run the full /boss/submit-answer pipeline without a
    # mountain of fixtures, so we patch check_boss_answer and assert the
    # `language` kwarg it receives.
    captured_kwargs: dict = {}

    async def _fake_check(**kwargs):
        captured_kwargs.update(kwargs)
        # Return a sane verdict so the rest of the route can proceed.
        from server.services.boss_dynamic import BossAnswerVerdict
        return BossAnswerVerdict(
            is_correct=True,
            score=0.95,
            confidence=0.9,
            feedback_to_student="ok",
            misconception_tags=[],
            damage_multiplier=1.0,
            difficulty_recommendation="stay",
            should_retry_same_skill=False,
        )

    # Create an English homework with a single authored boss question.
    payload = {
        "title": "lang-thread-en",
        "subject": "english",
        "grade": 8,
        "mode": "hard",
        "family": "til-fanlar",
        "content_json": {
            "title": "lang-thread-en",
            "subject": "english",
            "grade": 8,
            "language": "en",
            "boss_questions": [
                {"q": "Translate", "tags": "[Bloom: L2]", "dmg": 10},
            ],
        },
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, resp.text
    hw_id = resp.json()["id"]
    sess = "plan5lang001"

    # Start a fresh boss session.
    start = client.post("/api/ai/boss/start", json={
        "session_id": sess, "homework_id": hw_id, "force_fresh": True,
    })
    assert start.status_code == 200, start.text
    boss_session_id = start.json()["boss_session_id"]

    # Generate a question (we don't care about the LLM output — patch the
    # gateway to return a stub).
    from server.schemas.ai_contracts import BossQuestionGenerated, BossExpectedAnswer, BossRubric

    async def _fake_generate_structured(*args, **kwargs):
        return BossQuestionGenerated(
            question_text="Translate a school sentence to English.",
            expected_answer=BossExpectedAnswer(canonical="ok"),
            rubric=BossRubric(full_credit=["ok"]),
            target_skill="translation",
            difficulty="medium",
            source_phase_ids=["practice"],
            why_this_question="test",
        )

    with patch(
        "server.services.boss_dynamic.ai_gateway.generate_structured",
        side_effect=_fake_generate_structured,
    ):
        gen = client.post("/api/ai/boss/generate-question", json={
            "boss_session_id": boss_session_id,
        })
    assert gen.status_code == 200, gen.text
    question_id = gen.json()["question_id"]

    # NOW submit an answer — and verify check_boss_answer received language='en'.
    with patch(
        "server.services.boss_dynamic.check_boss_answer",
        side_effect=_fake_check,
    ):
        submit = client.post("/api/ai/boss/submit-answer", json={
            "boss_session_id": boss_session_id,
            "question_id": question_id,
            "student_answer": "Test answer.",
        })
    assert submit.status_code == 200, submit.text
    assert captured_kwargs.get("language") == "en", (
        f"Route must thread homework language 'en' to check_boss_answer; "
        f"got language={captured_kwargs.get('language')!r}"
    )
