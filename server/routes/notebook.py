"""HTTP route for notebook formula capture grading.

Endpoints:
  POST /api/notebook/grade     — multipart photo upload + IDs -> graded JSON or rejection
  GET  /api/notebook/captures  — list captures for a session (review/retry UI)
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from server import db
from server.routes.ai import _find_question_in_content, _handle_exc
from server.services import notebook_grade, tutor

router = APIRouter(prefix="/notebook", tags=["notebook"])
log = logging.getLogger(__name__)

# Hard cap so a multi-GB upload can't exhaust memory before Layer 1 rejects it.
# Layer 1 rejects anything > 5 MB, so reading 6 MB is enough to detect oversize.
_READ_CAP = notebook_grade.MAX_FILE_BYTES + 1024 * 1024  # 6 MB


def _load_prompt_template() -> str:
    """Read the runtime grader prompt from disk on every request.

    Reading per-request (rather than module-import time) lets ops hot-edit
    the prompt without restarting the server.
    """
    path = (
        Path(__file__).parent.parent / "prompts" / "runtime" / "notebook-grader.md"
    )
    return path.read_text(encoding="utf-8")


@router.post("/grade")
async def grade_endpoint(
    image: UploadFile = File(...),
    session_id: str = Form(...),
    hw_id: str = Form(...),
    question_id: str = Form(...),
):
    """Accept multipart photo + IDs; return graded JSON or localized rejection."""
    tutor._validate_session_id(session_id)

    image_bytes = await image.read(_READ_CAP)
    mime = image.content_type or "image/jpeg"

    # Pull question.q + answer_spec.expected from homework's content_json
    question_text = ""
    expected: Any = None
    try:
        hw = await db.get_homework(hw_id)
    except Exception as exc:
        log.warning("get_homework failed for hw_id=%s: %s", hw_id, exc)
        hw = None

    if hw and hw.get("content_json"):
        q = _find_question_in_content(hw["content_json"], question_id)
        if isinstance(q, dict):
            question_text = (
                q.get("q") or q.get("prompt") or q.get("question") or ""
            )
            spec = q.get("answer_spec") or {}
            if isinstance(spec, dict):
                expected = spec.get("expected")

    try:
        prompt_template = _load_prompt_template()
        grade = await notebook_grade.grade_capture(
            image_bytes=image_bytes,
            mime=mime,
            session_id=session_id,
            hw_id=hw_id,
            question_id=question_id,
            question_text=question_text,
            expected=expected,
            prompt_template=prompt_template,
        )
        return grade.to_response_dict()
    except HTTPException:
        raise
    except Exception as e:
        _handle_exc(e)


@router.get("/captures")
async def list_captures(session_id: str, hw_id: str):
    """List all captures for a session (for review/retry UI)."""
    tutor._validate_session_id(session_id)
    rows = await db.list_captures_for_session(session_id, hw_id)
    return {"captures": rows}
