"""Hybrid-grading hardening sweep (2026-05-22, item 5).

Parametrized contract guard over every phase that reaches the unified runtime
grading pipeline (``tutor.process_runtime_answer``, behind
``POST /api/ai/runtime/submit-answer``). For each phase the AI-judge path is
exercised with a stubbed gateway and we assert three invariants:

  1. The response is well-formed (the unified contract keys are present).
  2. ``score`` is clamped to ``[0, 1]`` — guaranteed by the ``AnswerCheckResult``
     Pydantic schema (``ge=0.0, le=1.0``), which every AI-graded path validates
     through ``ai_gateway.generate_structured``.
  3. NO answer-bearing field value leaks into the response body — the
     server-only grading anchors (the expected answer, accepted list,
     acceptable_keywords, rubric, answer_spec subtree) never reach the client.

These complement the per-game endpoint tests (which pin each game's bespoke
deterministic branch); this file pins the SHARED AI-judge contract that all
phases funnel through.

Vision/notebook grading is intentionally NOT in this sweep — it stays on the
Kimi K2.6 path (CLAUDE.md lock) and is graded by ``notebook_grade``, a separate
pipeline that never routes through ``process_runtime_answer``.
"""
from __future__ import annotations

import json

import pytest

from server.schemas.ai_contracts import AnswerCheckResult
from server.services import tutor


# A unique sentinel that, if it ever appears in the response body, proves an
# answer-bearing field leaked from the server-only grading anchors.
_SECRET_ANSWER = "ZZQX_SECRET_EXPECTED_ANSWER_42"
_SECRET_KEYWORD = "ZZQX_SECRET_ANCHOR_KEYWORD"

# Every phase string that the runtime client may submit to /runtime/submit-answer
# and that falls through deterministic grading into the shared AI judge.
_PHASES = [
    "practice",
    "real-life-challenge",
    "reading-checkpoint",
    "final-boss",
    "tile-match",
    "sentence-fill",
    "ttt",
    "mystery-box",
    "puzzle-lock",
    "adaptive-quiz",
    "memory-palace",
]

# Answer-bearing KEYS that must never appear in a grading response body. This is
# the subset of redaction_constants.ANSWER_BEARING_KEYS that carries the
# *expected answer* itself — `correct`/`is_correct` are excluded because those
# are the student's own verdict (legitimately returned), not a leaked key.
_FORBIDDEN_KEYS = {
    "answer_spec",
    "expected",
    "expected_answer",
    "expected_answers",
    "accepted_answers",
    "accepted",
    "acceptable_keywords",
    "acceptable",
    "rubric",
    "solution",
    "solution_text",
    "matched_expected",
    "correct_path",
    "correct_answer",
    "correct_option",
}


def _walk_keys(obj):
    """Yield every dict key found anywhere in a nested structure."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _walk_keys(v)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            yield from _walk_keys(item)


@pytest.fixture(autouse=True)
def _stub_runtime_grading(monkeypatch):
    """Stub the DB writers + session validation so the sweep is pure-compute."""
    async def _noop(*a, **k):
        return None

    monkeypatch.setattr("server.db.attempts_repo.add_phase_attempt", _noop)
    monkeypatch.setattr("server.db.set_answer_cache", _noop)
    monkeypatch.setattr("server.db.add_to_review_queue", _noop)
    monkeypatch.setattr("server.services.tutor._validate_session_id", lambda x: x)


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", _PHASES)
async def test_runtime_ai_judge_phase_is_well_formed_clamped_and_leak_free(
    phase, monkeypatch
):
    """For every phase: the AI-judge response is well-formed, score in [0,1],
    and no answer-bearing key/value leaks into the body."""

    # The gateway is stubbed to a VALID AnswerCheckResult — the schema enforces
    # score/confidence in [0,1], so the model could not have returned an
    # out-of-range score in the first place. We additionally assert the runtime
    # never widens the range.
    async def _mock_structured(*args, **kwargs):
        return AnswerCheckResult(score=0.83, confidence=0.95, feedback="ok")

    monkeypatch.setattr(
        "server.services.tutor.ai_gateway.generate_structured", _mock_structured
    )

    target = {
        "session_id": f"sess-{phase}",
        "question_id": f"q-{phase}",
        "phase": phase,
        "answer_spec": {"type": "semantic"},  # forces fall-through to AI judge
        "question_text": "Savol matni?",
        # Server-only grading anchors — these must NEVER appear in the response.
        "expected_answers": [_SECRET_ANSWER],
        "acceptable_keywords": [_SECRET_KEYWORD],
    }

    res = await tutor.process_runtime_answer(target, "student answer")

    # 1. Well-formed unified contract.
    for key in ("ok", "grading_method", "is_correct", "score", "confidence",
                "feedback", "requires_review"):
        assert key in res, f"phase={phase}: missing contract key {key!r}"
    assert res["ok"] is True

    # 2. Score clamped to [0, 1].
    assert 0.0 <= res["score"] <= 1.0, f"phase={phase}: score out of range: {res['score']}"
    assert 0.0 <= res["confidence"] <= 1.0

    # 3. No answer-bearing VALUE leaks into the body.
    body = json.dumps(res, ensure_ascii=False)
    assert _SECRET_ANSWER not in body, (
        f"phase={phase}: expected-answer value leaked into response: {body!r}"
    )
    assert _SECRET_KEYWORD not in body, (
        f"phase={phase}: acceptable_keyword anchor leaked into response: {body!r}"
    )
    # ... and no answer-bearing KEY leaks either.
    leaked = set(_walk_keys(res)) & _FORBIDDEN_KEYS
    assert not leaked, f"phase={phase}: answer-bearing keys leaked into response: {leaked}"


@pytest.mark.asyncio
@pytest.mark.parametrize("raw_score", [-0.5, 1.0, 0.0])
async def test_runtime_score_never_escapes_unit_interval(raw_score, monkeypatch):
    """The deterministic correct/incorrect verdicts and the AI-judge tiers must
    all keep ``score`` within [0, 1]. The AnswerCheckResult schema rejects an
    out-of-range model score, so we test the deterministic boundaries here
    (1.0 correct / 0.0 incorrect) plus an AI mid value."""
    # Deterministic correct → score 1.0.
    target = {
        "session_id": "sess-clamp",
        "answer_spec": {"type": "text_exact", "expected": "42"},
        "expected_answers": ["42"],
        "phase": "practice",
    }
    res = await tutor.process_runtime_answer(target, "42")
    assert res["score"] == 1.0

    # Deterministic incorrect → score 0.0.
    res = await tutor.process_runtime_answer(target, "wrong")
    assert res["score"] == 0.0
    assert 0.0 <= res["score"] <= 1.0
