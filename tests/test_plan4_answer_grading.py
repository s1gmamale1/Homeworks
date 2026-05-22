import pytest
from fastapi import HTTPException
from pydantic import BaseModel
from typing import Optional
from unittest.mock import patch

from server.schemas.ai_contracts import AnswerCheckResult
from server.services import ai_gateway
from server.services.runtime_answer_resolver import resolve_runtime_answer, ResolvedAnswerTarget

class DummyRequest(BaseModel):
    session_id: str
    homework_id: str
    phase: str
    phase_index: int = 1
    question_id: Optional[str]
    answer_type: str = "text"
    student_answer: str = "test"
    student_work_text: str = ""
    attempt_number: int = 1

@pytest.mark.asyncio
async def test_resolve_runtime_answer_hw_not_found(monkeypatch):
    async def mock_get_homework(hw_id): return None
    monkeypatch.setattr("server.db.get_homework", mock_get_homework)
    
    req = DummyRequest(session_id="sess1", homework_id="hw99", phase="practice", question_id="q1")
    
    with pytest.raises(HTTPException) as excinfo:
        await resolve_runtime_answer(req)
    
    assert excinfo.value.status_code == 404
    assert excinfo.value.detail["error_code"] == "HW_NOT_FOUND"

@pytest.mark.asyncio
async def test_resolve_runtime_answer_question_not_found(monkeypatch):
    async def mock_get_homework(hw_id): 
        return {"content_json": {"practice": {"items": []}}}
    monkeypatch.setattr("server.db.get_homework", mock_get_homework)
    
    req = DummyRequest(session_id="sess1", homework_id="hw1", phase="practice", question_id="q1")
    
    with pytest.raises(HTTPException) as excinfo:
        await resolve_runtime_answer(req)
        
    assert excinfo.value.status_code == 404
    assert excinfo.value.detail["error_code"] == "QUESTION_NOT_RESOLVED"

@pytest.mark.asyncio
async def test_resolve_runtime_answer_requires_question_id(monkeypatch):
    async def mock_get_homework(hw_id):
        return {"content_json": {"practice": {"items": []}}}
    monkeypatch.setattr("server.db.get_homework", mock_get_homework)

    req = DummyRequest(session_id="sess1", homework_id="hw1", phase="practice", question_id=None)

    with pytest.raises(HTTPException) as excinfo:
        await resolve_runtime_answer(req)

    assert excinfo.value.status_code == 400
    assert excinfo.value.detail["error_code"] == "MISSING_QUESTION_ID"
    assert "missing_question_id" in excinfo.value.detail["missing_context_flags"]

@pytest.mark.asyncio
async def test_resolve_runtime_answer_rejects_ungradable_question(monkeypatch):
    async def mock_get_homework(hw_id):
        return {
            "content_json": {
                "practice": {
                    "items": [
                        {"id": "q1", "text": "Explain photosynthesis."}
                    ]
                }
            }
        }
    monkeypatch.setattr("server.db.get_homework", mock_get_homework)

    req = DummyRequest(session_id="sess1", homework_id="hw1", phase="practice", question_id="q1")

    with pytest.raises(HTTPException) as excinfo:
        await resolve_runtime_answer(req)

    assert excinfo.value.status_code == 422
    assert excinfo.value.detail["error_code"] == "ANSWER_TARGET_NOT_GRADABLE"
    assert "missing_answer_material" in excinfo.value.detail["missing_context_flags"]

@pytest.mark.asyncio
async def test_resolve_runtime_answer_success(monkeypatch):
    async def mock_get_homework(hw_id):
        return {
            "content_json": {
                "practice": {
                    "items": [
                        {
                            "id": "q1", 
                            "text": "What is 2+2?", 
                            "expected_answers": ["4"], 
                            "rubric": {"detail": "basic"}
                        }
                    ]
                }
            }
        }
    monkeypatch.setattr("server.db.get_homework", mock_get_homework)
    
    req = DummyRequest(session_id="sess1", homework_id="hw1", phase="practice", question_id="q1")
    
    target = await resolve_runtime_answer(req)
    assert isinstance(target, ResolvedAnswerTarget)
    assert target.question_text == "What is 2+2?"
    assert target.expected_answers == ["4"]
    assert target.trusted_source_path == "content_json.practice.items[0]"

@pytest.mark.parametrize(
    ("text_key", "question_text"),
    [
        ("text", "What is 2+2?"),
        ("q", "What is 3+3?"),
        ("prompt", "What is 4+4?"),
    ],
)
@pytest.mark.asyncio
async def test_resolve_runtime_answer_accepts_trusted_question_text_aliases(
    monkeypatch,
    text_key,
    question_text,
):
    async def mock_get_homework(hw_id):
        return {
            "content_json": {
                "practice": {
                    "items": [
                        {
                            "id": "q1",
                            text_key: question_text,
                            "expected_answers": ["answer"],
                        }
                    ]
                }
            }
        }
    monkeypatch.setattr("server.db.get_homework", mock_get_homework)

    req = DummyRequest(session_id="sess1", homework_id="hw1", phase="practice", question_id="q1")

    target = await resolve_runtime_answer(req)

    assert target.question_text == question_text
    assert target.trusted_source_path == "content_json.practice.items[0]"

@pytest.mark.asyncio
async def test_process_runtime_answer_deterministic_correct(monkeypatch):
    from server.services.tutor import process_runtime_answer
    
    # Mock db add_phase_attempt to do nothing
    async def mock_add(*args, **kwargs): pass
    monkeypatch.setattr("server.db.attempts_repo.add_phase_attempt", mock_add)
    monkeypatch.setattr("server.services.tutor._validate_session_id", lambda x: x)
    
    target = {
        "session_id": "sess1",
        "answer_spec": {"type": "text_exact", "expected": "4"},
        "expected_answers": ["4"],
    }
    
    res = await process_runtime_answer(target, "4")
    assert res["ok"] is True
    assert res["grading_method"] == "deterministic"
    assert res["is_correct"] is True
    assert res["score"] == 1.0

@pytest.mark.asyncio
async def test_process_runtime_answer_ai_judge_tiers(monkeypatch):
    from server.services.tutor import process_runtime_answer
    
    async def mock_add(*args, **kwargs): pass
    monkeypatch.setattr("server.db.attempts_repo.add_phase_attempt", mock_add)
    monkeypatch.setattr("server.services.tutor._validate_session_id", lambda x: x)
    
    # Force fallback to AI Judge
    target = {
        "session_id": "sess1",
        "answer_spec": {"type": "semantic"}, # Will fail deterministic
        "answer_type": "text",
        "phase": "practice"
    }

    gateway_calls = []

    # Helper to mock gateway returning specific confidence
    async def run_tier(score, confidence):
        async def mock_generate_structured(*args, **kwargs):
            gateway_calls.append(kwargs)
            return AnswerCheckResult(
                score=score,
                confidence=confidence,
                feedback="test",
            )
        monkeypatch.setattr("server.services.tutor.ai_gateway.generate_structured", mock_generate_structured)
        with patch("server.services.tutor.ai_orchestrator.generate_json") as legacy_generate_json:
            result = await process_runtime_answer(target, "test")
        legacy_generate_json.assert_not_called()
        assert gateway_calls[-1]["task"] == ai_gateway.AITask.ANSWER_CHECK
        assert gateway_calls[-1]["schema"] is AnswerCheckResult
        return result

    # >= 0.90 confidence
    res = await run_tier(0.95, 0.95)
    assert res["confidence"] == 0.95
    assert res["is_correct"] is True
    assert res["requires_review"] is False
    assert res["feedback"] == "test"

    # 0.75 - 0.89 confidence
    res = await run_tier(0.85, 0.80)
    assert res["confidence"] == 0.80
    assert res["is_correct"] is True
    assert res["requires_review"] is False
    assert "medium_confidence" in res["misconception_tags"]

    # 0.60 - 0.74 confidence
    res = await run_tier(0.80, 0.65)
    assert res["confidence"] == 0.65
    assert res["is_correct"] is False
    assert res["requires_review"] is False

    # < 0.60 confidence
    res = await run_tier(0.50, 0.50)
    assert res["confidence"] == 0.50
    assert res["is_correct"] is False
    assert res["requires_review"] is True
    assert res["score"] == 0.0

def test_prompt_file_shapes():
    import os
    prompts = [
        "server/prompts/runtime/answer-checker-language.md",
        "server/prompts/runtime/answer-checker-math.md",
        # Converged 2026-05-22: the legacy answer-checker-boss.md was deleted and
        # the tutor.py final-boss branch now uses the canonical boss-answer-checker.md.
        "server/prompts/runtime/boss-answer-checker.md",
    ]
    for p in prompts:
        path = os.path.join(os.path.dirname(__file__), "..", p)
        assert os.path.exists(path), f"Prompt file missing: {p}"
        with open(path, "rb") as f:
            raw = f.read()
            
        assert not raw.startswith(b"\xef\xbb\xbf"), f"{p} has BOM"
        assert b"\r\n" not in raw, f"{p} has CRLF line endings"
        assert b"\x0c" not in raw, f"{p} has form-feed control char"


# ---------------------------------------------------------------------------
# Hybrid-grading hardening regressions (2026-05-22)
# ---------------------------------------------------------------------------


def _patch_runtime_grading_deps(monkeypatch):
    """Shared monkeypatch setup for process_runtime_answer tests: stub the DB
    attempt writer + session validation so the tests stay pure-compute."""
    async def _noop(*a, **k):
        return None
    monkeypatch.setattr("server.db.attempts_repo.add_phase_attempt", _noop)
    monkeypatch.setattr("server.services.tutor._validate_session_id", lambda x: x)


@pytest.mark.asyncio
async def test_runtime_real_life_phase_routes_to_rlc_grader_prompt(monkeypatch):
    """REGRESSION (item 1): a phase=='real-life-challenge' answer that falls
    through to the AI judge must load the `real-life-challenge-grader` prompt —
    NOT the generic answer-checker-language prompt. Before the fix the ladder
    only branched on math/final-boss, so real-life fell through to the language
    checker with the wrong rubric.

    Also pins the no-leak guarantee: `acceptable_keywords` ride into the prompt
    INPUT only and never appear in the response body.
    """
    from server.services.tutor import process_runtime_answer

    _patch_runtime_grading_deps(monkeypatch)

    loaded_prompts = []
    real_loader = __import__(
        "server.services.tutor", fromlist=["_load_runtime_prompt"]
    )._load_runtime_prompt

    def _spy_loader(name):
        loaded_prompts.append(name)
        return real_loader(name)

    monkeypatch.setattr("server.services.tutor._load_runtime_prompt", _spy_loader)

    captured = {}

    async def _mock_structured(*args, **kwargs):
        captured["prompt"] = kwargs.get("prompt", "")
        return AnswerCheckResult(score=0.9, confidence=0.95, feedback="yaxshi")

    monkeypatch.setattr(
        "server.services.tutor.ai_gateway.generate_structured", _mock_structured
    )
    monkeypatch.setattr("server.db.set_answer_cache", _async_noop())

    target = {
        "session_id": "sess-rlc",
        "answer_spec": {"type": "semantic"},  # forces AI judge
        "phase": "real-life-challenge",
        "question_text": "Bemorni qanday davolaysiz?",
        "acceptable_keywords": ["SEKRET_ANCHOR_KW"],
    }
    res = await process_runtime_answer(target, "javobim")

    assert "real-life-challenge-grader" in loaded_prompts, (
        f"expected RLC grader prompt to load, got {loaded_prompts}"
    )
    # The keyword anchor is allowed in the PROMPT (server-side) ...
    assert "SEKRET_ANCHOR_KW" in captured["prompt"]
    # ... but must NOT leak into the response returned to the client.
    import json as _json
    assert "SEKRET_ANCHOR_KW" not in _json.dumps(res, ensure_ascii=False)


@pytest.mark.asyncio
async def test_runtime_final_boss_routes_to_canonical_boss_answer_checker(monkeypatch):
    """REGRESSION (item 2): phase=='final-boss' must load the canonical
    `boss-answer-checker` prompt, not the deleted legacy `answer-checker-boss`.
    """
    from server.services.tutor import process_runtime_answer

    _patch_runtime_grading_deps(monkeypatch)

    loaded_prompts = []
    real_loader = __import__(
        "server.services.tutor", fromlist=["_load_runtime_prompt"]
    )._load_runtime_prompt

    def _spy_loader(name):
        loaded_prompts.append(name)
        return real_loader(name)

    monkeypatch.setattr("server.services.tutor._load_runtime_prompt", _spy_loader)

    async def _mock_structured(*args, **kwargs):
        return AnswerCheckResult(score=0.5, confidence=0.95, feedback="strict")

    monkeypatch.setattr(
        "server.services.tutor.ai_gateway.generate_structured", _mock_structured
    )
    monkeypatch.setattr("server.db.set_answer_cache", _async_noop())

    target = {
        "session_id": "sess-boss",
        "answer_spec": {"type": "semantic"},
        "phase": "final-boss",
        "question_text": "Final savol",
    }
    await process_runtime_answer(target, "javob")

    assert "boss-answer-checker" in loaded_prompts
    assert "answer-checker-boss" not in loaded_prompts


def _async_noop():
    async def _noop(*a, **k):
        return None
    return _noop


@pytest.mark.asyncio
async def test_runtime_high_confidence_writes_answer_cache(monkeypatch):
    """REGRESSION (item 3a): a >=0.90 confidence verdict from the AI judge in
    process_runtime_answer must write the answer cache (parity with
    tutor.check_answer). Before the fix the runtime ladder never cached.
    """
    from server.services.tutor import process_runtime_answer

    _patch_runtime_grading_deps(monkeypatch)

    cache_writes = []

    async def _spy_set_cache(key, response):
        cache_writes.append((key, response))

    async def _spy_add_review(*a, **k):
        raise AssertionError("review queue must NOT be called on high confidence")

    async def _mock_structured(*args, **kwargs):
        return AnswerCheckResult(score=0.95, confidence=0.95, feedback="great")

    monkeypatch.setattr("server.db.set_answer_cache", _spy_set_cache)
    monkeypatch.setattr("server.db.add_to_review_queue", _spy_add_review)
    monkeypatch.setattr(
        "server.services.tutor.ai_gateway.generate_structured", _mock_structured
    )

    target = {
        "session_id": "sess-cache",
        "question_id": "q-cache",
        "answer_spec": {"type": "semantic"},
        "phase": "practice",
    }
    res = await process_runtime_answer(target, "ans")
    assert res["is_correct"] is True
    assert len(cache_writes) == 1, "high-confidence verdict must write cache exactly once"


@pytest.mark.asyncio
async def test_runtime_low_confidence_enrolls_review_queue(monkeypatch):
    """REGRESSION (item 3b): a <0.60 confidence verdict must enroll a review
    item (parity with tutor.check_answer) and must NOT write the answer cache.
    """
    from server.services.tutor import process_runtime_answer

    _patch_runtime_grading_deps(monkeypatch)

    review_inserts = []
    cache_writes = []

    async def _spy_add_review(question_id, student_answer, answer_spec, ai_response):
        review_inserts.append(question_id)
        return True

    async def _spy_set_cache(key, response):
        cache_writes.append(key)

    async def _mock_structured(*args, **kwargs):
        return AnswerCheckResult(score=0.4, confidence=0.40, feedback="unsure")

    monkeypatch.setattr("server.db.add_to_review_queue", _spy_add_review)
    monkeypatch.setattr("server.db.set_answer_cache", _spy_set_cache)
    monkeypatch.setattr(
        "server.services.tutor.ai_gateway.generate_structured", _mock_structured
    )

    target = {
        "session_id": "sess-review",
        "question_id": "q-review",
        "answer_spec": {"type": "semantic"},
        "phase": "practice",
    }
    res = await process_runtime_answer(target, "ans")
    assert res["requires_review"] is True
    assert review_inserts == ["q-review"]
    assert cache_writes == [], "low-confidence verdict must not write cache"


@pytest.mark.asyncio
async def test_runtime_ai_judge_exception_enrolls_review_queue(monkeypatch):
    """REGRESSION (item 3c): when the AI judge raises, the attempt must be
    enrolled for human review instead of silently dropped.
    """
    from server.services.tutor import process_runtime_answer

    _patch_runtime_grading_deps(monkeypatch)

    review_inserts = []

    async def _spy_add_review(question_id, student_answer, answer_spec, ai_response):
        review_inserts.append(question_id)
        return True

    async def _boom(*args, **kwargs):
        raise RuntimeError("provider exploded")

    monkeypatch.setattr("server.db.add_to_review_queue", _spy_add_review)
    monkeypatch.setattr(
        "server.services.tutor.ai_gateway.generate_structured", _boom
    )

    target = {
        "session_id": "sess-exc",
        "question_id": "q-exc",
        "answer_spec": {"type": "semantic"},
        "phase": "practice",
    }
    res = await process_runtime_answer(target, "ans")
    assert res["grading_method"] == "error"
    assert res["requires_review"] is True
    assert review_inserts == ["q-exc"]
