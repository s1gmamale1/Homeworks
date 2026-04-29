"""Wave K — notebook_grade orchestrator unit tests.

Covers Layers 1, 4, and the full mocked pipeline for grade_capture.
Layer 2 (OpenCV prefilter) and Layer 3 (vision LLM) are mocked.
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from server.services import notebook_grade
from server.services.notebook_grade import (
    NotebookGrade,
    _build_grounded_prompt,
    _post_llm_sanity,
    _strip_markdown_fences,
    _validate_input,
)


# Magic-byte stubs (~150 bytes each so they pass MIN_FILE_BYTES)
_JPG_HEAD = b"\xff\xd8\xff\xe0" + b"\x00" * 200
_PNG_HEAD = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200
_WEBP_HEAD = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 200
_TXT_HEAD = b"hello, this is plain text not an image " * 10


def _run(coro):
    """Tiny helper: drive a coroutine without depending on pytest-asyncio."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


# ── Layer 1: input validation ───────────────────────────────────────────────


def test_validate_input_accepts_jpg():
    assert _validate_input(_JPG_HEAD, "image/jpeg") is None


def test_validate_input_accepts_png():
    assert _validate_input(_PNG_HEAD, "image/png") is None


def test_validate_input_accepts_webp():
    assert _validate_input(_WEBP_HEAD, "image/webp") is None


def test_validate_input_rejects_text_file():
    rg = _validate_input(_TXT_HEAD, "image/jpeg")  # claims jpeg but isn't
    assert rg is not None and rg.rejected is True
    assert rg.reason == "invalid_file"


def test_validate_input_rejects_bad_mime():
    rg = _validate_input(_JPG_HEAD, "application/pdf")
    assert rg is not None and rg.reason == "invalid_file"


def test_validate_input_rejects_oversized():
    big = _JPG_HEAD + b"\x00" * (notebook_grade.MAX_FILE_BYTES + 1)
    rg = _validate_input(big, "image/jpeg")
    assert rg is not None and rg.reason == "invalid_file"


def test_validate_input_rejects_tiny():
    rg = _validate_input(b"\xff\xd8\xff", "image/jpeg")  # 3 bytes
    assert rg is not None and rg.reason == "invalid_file"


# ── Grounded prompt builder ─────────────────────────────────────────────────


def test_build_prompt_with_str_expected():
    out = _build_grounded_prompt(
        question_text="solve x+1=3", expected="2",
        prompt_template="Q: {question_text} | EXP: {expected}",
    )
    assert out == "Q: solve x+1=3 | EXP: 2"


def test_build_prompt_with_list_expected():
    out = _build_grounded_prompt(
        question_text="list factors", expected=["2", "3"],
        prompt_template="Q: {question_text} | EXP: {expected}",
    )
    assert "2, 3" in out


def test_build_prompt_with_none_expected():
    out = _build_grounded_prompt(
        question_text="solve", expected=None,
        prompt_template="Q: {question_text} | EXP: {expected}",
    )
    assert "(not specified)" in out


def test_build_prompt_with_empty_question():
    out = _build_grounded_prompt(
        question_text="", expected="42",
        prompt_template="Q: {question_text} | EXP: {expected}",
    )
    assert "(not provided)" in out


# ── Layer 4: post-LLM sanity ────────────────────────────────────────────────


def test_sanity_ok_for_valid_grade():
    ok, reason = _post_llm_sanity({
        "transcribed_text": "x = 2 + 3 = 5",
        "confidence": 0.85,
        "matches_expected": True,
    })
    assert ok is True
    assert reason == ""


def test_sanity_rejects_empty_transcription():
    ok, reason = _post_llm_sanity({
        "transcribed_text": "",
        "confidence": 0.9,
    })
    assert ok is False
    assert reason == "vision_low_confidence"


def test_sanity_rejects_null_transcription():
    ok, reason = _post_llm_sanity({
        "transcribed_text": None,
        "confidence": 0.5,
    })
    assert ok is False and reason == "vision_low_confidence"


def test_sanity_rejects_high_conf_with_illegible_pattern():
    """Hallucination guard — model claims illegible but reports high confidence."""
    ok, reason = _post_llm_sanity({
        "transcribed_text": "The work is [illegible] in places",
        "confidence": 0.85,
    })
    assert ok is False
    assert reason == "vision_low_confidence"


def test_sanity_rejects_low_confidence():
    ok, reason = _post_llm_sanity({
        "transcribed_text": "x = 5",
        "confidence": 0.2,
    })
    assert ok is False and reason == "vision_low_confidence"


def test_sanity_rejects_no_math_symbols():
    ok, reason = _post_llm_sanity({
        "transcribed_text": "the cat sat on the mat",
        "confidence": 0.9,
    })
    assert ok is False
    assert reason == "no_math_symbols"


# ── Markdown fence stripping ────────────────────────────────────────────────


def test_strip_fences_with_lang_tag():
    s = '```json\n{"a": 1}\n```'
    assert _strip_markdown_fences(s) == '{"a": 1}'


def test_strip_fences_without_lang_tag():
    s = '```\n{"a": 1}\n```'
    assert _strip_markdown_fences(s) == '{"a": 1}'


def test_strip_fences_passthrough_when_no_fence():
    s = '{"a": 1}'
    assert _strip_markdown_fences(s) == '{"a": 1}'


# ── Full pipeline (mocked) ──────────────────────────────────────────────────


class _FakePF:
    def __init__(self, ok, reason=None, deskewed=None):
        self.ok = ok
        self.reason = reason
        self.deskewed_bytes = deskewed
        self.detected_skew_deg = 0.0
        self.pen_density_ratio = 0.05
        self.face_ratio = 0.0


_VALID_VISION_JSON = {
    "transcribed_text": "x + 3 = 5, x = 2",
    "confidence": 0.85,
    "matches_expected": True,
    "score_1_to_4": 4,
    "axis_1_concept_id": 4,
    "axis_2_process_integrity": 4,
    "correct": True,
    "feedback": "Yaxshi! Toza yechim.",
}


def test_grade_capture_happy_path(tmp_path, monkeypatch):
    """Full pipeline with mocked prefilter + mocked vision returns a graded NotebookGrade."""
    monkeypatch.setenv("NETS_PHOTO_DIR", str(tmp_path))

    with patch.object(notebook_grade.notebook_prefilter, "validate",
                      return_value=_FakePF(ok=True, deskewed=_JPG_HEAD)), \
         patch.object(notebook_grade.gemini, "generate_vision",
                      new=AsyncMock(return_value={"text": json.dumps(_VALID_VISION_JSON)})), \
         patch.object(notebook_grade.db, "add_capture",
                      new=AsyncMock(return_value=1)) as mock_add:
        grade = _run(notebook_grade.grade_capture(
            image_bytes=_JPG_HEAD, mime="image/jpeg",
            session_id="sess-grade-001", hw_id="HW-TEST-1", question_id="q1",
            question_text="solve x+3=5", expected="2",
            prompt_template="Q: {question_text} EXP: {expected}",
        ))

    assert grade.rejected is False
    assert grade.score_1_to_4 == 4
    assert grade.correct is True
    assert grade.matches_expected is True
    assert grade.transcribed_text == "x + 3 = 5, x = 2"
    assert grade.photo_id is not None
    # DB row was written with status='graded'
    assert mock_add.call_count == 1
    kwargs = mock_add.call_args.kwargs
    assert kwargs["status"] == "graded"
    assert kwargs["correct"] == 1


def test_grade_capture_rejection_blank_or_scene(tmp_path, monkeypatch):
    """Prefilter returns ok=False -> NotebookGrade(rejected=True) + DB row status=rejected."""
    monkeypatch.setenv("NETS_PHOTO_DIR", str(tmp_path))

    with patch.object(notebook_grade.notebook_prefilter, "validate",
                      return_value=_FakePF(ok=False, reason="blank_or_scene")), \
         patch.object(notebook_grade.db, "add_capture",
                      new=AsyncMock(return_value=2)) as mock_add:
        grade = _run(notebook_grade.grade_capture(
            image_bytes=_JPG_HEAD, mime="image/jpeg",
            session_id="sess-blank-001", hw_id="HW-TEST-2", question_id="q1",
            question_text="any", expected=None,
            prompt_template="{question_text} {expected}",
        ))

    assert grade.rejected is True
    assert grade.reason == "blank_or_scene"
    assert mock_add.call_args.kwargs["status"] == "rejected"
    assert mock_add.call_args.kwargs["rejection_reason"] == "blank_or_scene"


def test_grade_capture_hallucination_guard(tmp_path, monkeypatch):
    """Vision returns 'illegible' + high confidence -> forced to vision_low_confidence rejection."""
    monkeypatch.setenv("NETS_PHOTO_DIR", str(tmp_path))

    bad_json = {
        "transcribed_text": "[illegible] something",
        "confidence": 0.85,
        "matches_expected": False,
        "score_1_to_4": 1,
        "axis_1_concept_id": 1,
        "axis_2_process_integrity": 1,
        "correct": False,
        "feedback": "...",
    }
    with patch.object(notebook_grade.notebook_prefilter, "validate",
                      return_value=_FakePF(ok=True, deskewed=_JPG_HEAD)), \
         patch.object(notebook_grade.gemini, "generate_vision",
                      new=AsyncMock(return_value={"text": json.dumps(bad_json)})), \
         patch.object(notebook_grade.db, "add_capture",
                      new=AsyncMock(return_value=3)) as mock_add:
        grade = _run(notebook_grade.grade_capture(
            image_bytes=_JPG_HEAD, mime="image/jpeg",
            session_id="sess-hall-001", hw_id="HW-TEST-3", question_id="q1",
            question_text="any", expected="2",
            prompt_template="{question_text} {expected}",
        ))

    assert grade.rejected is True
    assert grade.reason == "vision_low_confidence"
    assert mock_add.call_args.kwargs["status"] == "rejected"


def test_grade_capture_invalid_input_rejection(tmp_path, monkeypatch):
    """Invalid file bytes don't reach the prefilter or LLM."""
    monkeypatch.setenv("NETS_PHOTO_DIR", str(tmp_path))

    with patch.object(notebook_grade.notebook_prefilter, "validate") as mock_pf, \
         patch.object(notebook_grade.gemini, "generate_vision",
                      new=AsyncMock()) as mock_vis, \
         patch.object(notebook_grade.db, "add_capture",
                      new=AsyncMock(return_value=4)):
        grade = _run(notebook_grade.grade_capture(
            image_bytes=_TXT_HEAD, mime="image/jpeg",
            session_id="sess-bad-001", hw_id="HW-TEST-4", question_id="q1",
            question_text="any", expected=None,
            prompt_template="{question_text} {expected}",
        ))

    assert grade.rejected is True
    assert grade.reason == "invalid_file"
    mock_pf.assert_not_called()
    mock_vis.assert_not_called()


def test_to_response_dict_includes_localized_messages():
    rg = NotebookGrade(rejected=True, reason="blank_or_scene")
    d = rg.to_response_dict()
    assert "retry_message_uz" in d
    assert "retry_message_ru" in d
    assert "retry_message_en" in d
    assert "ko'rinmayapti" in d["retry_message_uz"]


def test_to_response_dict_no_messages_for_graded():
    rg = NotebookGrade(rejected=False, score_1_to_4=4, feedback="great")
    d = rg.to_response_dict()
    assert "retry_message_uz" not in d
