"""Regression — BLOCKER #4: tutor "preview" must not be an answer-escape hatch.

The leak it guards: `/api/ai/tutor/chat` trusts a client-supplied `phase`. A
tampered client could send `phase="preview"` while referencing a gated question
(e.g. boss `bq_0`); the old redactor returned the RAW question dict — including
`answer_spec` / `ans` — straight into the LLM prompt context, leaking the
answer.

The fix makes redaction depend on the QUESTION CONTENT, not the claimed phase:
a question carrying ANY answer-bearing field is always scrubbed, even under
phase="preview". Pure teaching content (no answer fields) still passes through
so legit preview panels are unaffected.

Both copies of `_redact_question_for_tutor` (ai_context + tutor) are pinned.
"""
from __future__ import annotations

import json

import pytest

from server.services.ai_context import _redact_question_for_tutor as redact_ctx
from server.services.tutor import _redact_question_for_tutor as redact_tutor

_SECRET = "MAGIC_SECRET_42"


def _answer_bearing_question() -> dict:
    """A gradeable question carrying answer-bearing fields at multiple depths."""
    return {
        "id": "bq_0",
        "question_id": "bq_0",
        "prompt": "Solve for x: 2x + 4 = 10",
        "type": "boss",
        "ans": _SECRET,
        "answer_spec": {"type": "text_exact", "expected": _SECRET},
        "options": [
            {"label": "A", "text": "x = 3", "is_correct": True},
            {"label": "B", "text": "x = 5"},
        ],
    }


@pytest.mark.parametrize("redact", [redact_ctx, redact_tutor], ids=["ai_context", "tutor"])
def test_preview_phase_does_not_leak_answer_bearing_question(redact):
    """phase="preview" must NOT bypass the scrub for an answer-bearing question."""
    q = _answer_bearing_question()
    safe = redact(q, phase="preview")
    blob = json.dumps(safe, ensure_ascii=False)

    # The literal answer must be gone.
    assert _SECRET not in blob, f"answer leaked under phase=preview: {blob}"
    # The answer-bearing keys must be stripped from the returned dict.
    assert "answer_spec" not in safe, blob
    assert "ans" not in safe, blob
    # Nested answer markers must not survive either.
    assert "is_correct" not in blob, blob
    assert "expected" not in blob, blob
    # The teaching prompt is still allowed through so the tutor stays useful.
    assert safe.get("prompt") == q["prompt"], blob


@pytest.mark.parametrize("redact", [redact_ctx, redact_tutor], ids=["ai_context", "tutor"])
def test_preview_phase_passes_pure_teaching_content_through(redact):
    """Control: a pure-teaching dict (no answer fields) is unaffected by the fix."""
    teaching = {
        "id": "panel_1",
        "title": "Why πr² is the area of a circle",
        "prompt": "A circle of radius r has area A = πr².",
        "text": "Slice the circle into thin rings and unroll them into a triangle.",
        "type": "teaching",
    }
    safe = redact(teaching, phase="preview")
    # Teaching text survives intact.
    assert safe.get("title") == teaching["title"]
    assert safe.get("prompt") == teaching["prompt"]
    assert safe.get("text") == teaching["text"]


@pytest.mark.parametrize("redact", [redact_ctx, redact_tutor], ids=["ai_context", "tutor"])
def test_non_preview_phases_also_scrub(redact):
    """practice/boss phases keep scrubbing answer-bearing questions (unchanged)."""
    for phase in ("practice", "boss"):
        safe = redact(_answer_bearing_question(), phase=phase)
        blob = json.dumps(safe, ensure_ascii=False)
        assert _SECRET not in blob, f"{phase}: {blob}"
        assert "answer_spec" not in safe, f"{phase}: {blob}"
