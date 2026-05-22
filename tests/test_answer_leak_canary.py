"""Answer-leak canary for the Boss-Arena Why→How→What rework.

Two guarantees:

  1. The client-facing generate-question response
     (``BossGenerateQuestionResponse``) — and the route projection that builds
     it — must NEVER carry any answer-bearing field at ANY nesting depth. The
     new scenario/why/how/what fields are PROMPT text (safe); the canary
     proves no expected_answer / rubric / coverage rubric / canonical leaked
     alongside them.

  2. The redaction deny-list (``redaction_constants.ANSWER_BEARING_KEYS``) must
     still contain the CBP grading-anchor keys. This is a regression guard so
     the boss work never weakens the Case-Based-Preview redaction.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from server.routes.ai_plan5 import BossGenerateQuestionResponse
from server.services import redaction_constants


# Keys that must NEVER appear in the client-facing generate-question payload,
# at any depth.
_FORBIDDEN_KEYS = {
    "expected_answer",
    "rubric",
    "ans",
    "accepted_answers",
    "correct",
    "canonical",
    "answer_spec",
    "coverage",
}


def _walk_keys(obj) -> set[str]:
    """Collect every dict key appearing anywhere in a nested structure."""
    found: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            found.add(str(k))
            found |= _walk_keys(v)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            found |= _walk_keys(item)
    return found


# ---------------------------------------------------------------------------
# 1. Response model field-level + serialized canary
# ---------------------------------------------------------------------------


def test_generate_question_response_model_has_no_answer_fields():
    """The Pydantic model's declared fields must not include any answer-
    bearing key. (Catches a future dev adding `expected_answer` to the
    response model.)"""
    model_fields = set(BossGenerateQuestionResponse.model_fields.keys())
    leaked = model_fields & _FORBIDDEN_KEYS
    assert not leaked, f"BossGenerateQuestionResponse leaks answer fields: {leaked}"


def test_generate_question_response_serialized_has_no_answer_keys_at_any_depth():
    """A fully-populated response, dumped to a dict, must contain none of the
    forbidden keys at any nesting depth — including the new scenario/why/how/
    what fields which are PROMPT text."""
    resp = BossGenerateQuestionResponse(
        question_id="gbq_x",
        question_text="Scenario + prompts",
        scenario="A baker has 5/6 kg of flour.",
        why="Why must you divide here?",
        how="How do you carry out the division?",
        what="What is the result?",
        target_skill="fraction_division",
        difficulty="medium",
        why_this_question="weak topic",
        boss_session_id="bs_x",
    )
    keys = _walk_keys(resp.model_dump())
    leaked = keys & _FORBIDDEN_KEYS
    assert not leaked, f"serialized generate-question response leaks: {leaked}"


def test_generate_question_response_carries_structured_prompt_fields():
    """Positive control — the safe Why→How→What prompt fields ARE present
    (so we know the canary above is meaningful, not passing by omission)."""
    fields = set(BossGenerateQuestionResponse.model_fields.keys())
    for safe in ("scenario", "why", "how", "what"):
        assert safe in fields, f"response model should expose prompt field {safe!r}"


# ---------------------------------------------------------------------------
# 2. End-to-end route projection canary
# ---------------------------------------------------------------------------


def _make_english_homework(client) -> str:
    payload = {
        "title": "leak-canary",
        "subject": "english",
        "grade": 8,
        "mode": "hard",
        "family": "til-fanlar",
        "content_json": {
            "title": "leak-canary",
            "subject": "english",
            "grade": 8,
            "language": "en",
            "boss_questions": [
                {"q": "Translate", "tags": "[Bloom: L2]", "dmg": 20},
            ],
        },
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def test_generate_question_route_response_has_no_answer_keys(client):
    """Drive the real /boss/start + /boss/generate-question route with a
    stubbed generator that DOES produce expected_answer + rubric + coverage-
    bearing content, and assert the HTTP JSON the client receives strips all
    of it — only prompt text survives."""
    from server.schemas.ai_contracts import (
        BossQuestionGenerated, BossExpectedAnswer, BossRubric,
    )

    hw_id = _make_english_homework(client)
    sess = "leakcanary0001"

    start = client.post("/api/ai/boss/start", json={
        "session_id": sess, "homework_id": hw_id, "force_fresh": True,
    })
    assert start.status_code == 200, start.text
    bsid = start.json()["boss_session_id"]

    async def _fake_generate_structured(*args, **kwargs):
        return BossQuestionGenerated(
            question_text="A baker splits 5/6 kg of flour into 3 bags.",
            scenario="A baker has 5/6 kg of flour.",
            why="Why does this need division?",
            how="How do you divide a fraction by a whole number?",
            what="What is the amount per bag?",
            expected_answer=BossExpectedAnswer(
                canonical="5/18", accepted_variants=["0.277..."], notes="grading anchor",
            ),
            rubric=BossRubric(full_credit=["5/18"], partial_credit=[], common_mistakes=[]),
            target_skill="fraction_division",
            difficulty="medium",
            source_phase_ids=["practice"],
            why_this_question="weak topic",
        )

    with patch(
        "server.services.boss_dynamic.ai_gateway.generate_structured",
        side_effect=_fake_generate_structured,
    ):
        gen = client.post("/api/ai/boss/generate-question", json={
            "boss_session_id": bsid,
        })
    assert gen.status_code == 200, gen.text
    body = gen.json()

    keys = _walk_keys(body)
    leaked = keys & _FORBIDDEN_KEYS
    assert not leaked, (
        f"generate-question HTTP response leaked answer keys: {leaked}; body={body}"
    )
    # The canonical answer string itself must not appear anywhere.
    assert "5/18" not in str(body), "canonical answer value leaked into client payload"
    # Positive control — the prompt parts ARE present.
    assert body.get("scenario"), "scenario prompt should be returned to the client"
    assert body.get("why") and body.get("how") and body.get("what")


# ---------------------------------------------------------------------------
# 3. Redaction deny-list regression guard (CBP must not be weakened)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "key",
    ["concept_keywords", "method_keywords", "mistake_keywords", "pass_score"],
)
def test_answer_bearing_keys_still_contains_cbp_anchor(key):
    """The boss work is ADD-only on the deny-list. The CBP Decision-Process
    grading anchors must remain — removing one would silently re-expose the
    grading key in hydration."""
    assert key in redaction_constants.ANSWER_BEARING_KEYS, (
        f"{key!r} dropped from ANSWER_BEARING_KEYS — CBP redaction weakened"
    )


def test_answer_bearing_keys_added_expected_concepts():
    """The new boss authored grading anchor must be on the deny-list."""
    assert "expected_concepts" in redaction_constants.ANSWER_BEARING_KEYS
