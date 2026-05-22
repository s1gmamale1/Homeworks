"""React runtime read API — the student-facing hydration + gate boundary.

Two GET endpoints, grouped here so the entire student read path is auditable
in one file:

  GET /api/runtime/homeworks/{id}              -> redacted content_json
  GET /api/runtime/homeworks/{id}/gate-state   -> server-authoritative gates

The redaction (runtime_redactor) is the delivery-mechanism replacement for the
legacy injector's per-game stripping. Gating is server-verified: the client
can't compute "passed" because it never receives the answers.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..db import get_homework
from ..services.content_json_compat import normalize_content_json_for_runtime
from ..services.gate_state import compute_gate_state
from ..services.runtime_redactor import redact_for_runtime

router = APIRouter(tags=["runtime"])


@router.get("/runtime/homeworks/{hw_id}")
async def runtime_hydrate(hw_id: str):
    """Student-safe hydration payload. Answers stripped server-side."""
    hw = await get_homework(hw_id)
    if not hw:
        raise HTTPException(status_code=404, detail={"error": "Homework not found", "code": "NOT_FOUND"})
    if hw.get("deleted_at"):
        raise HTTPException(status_code=409, detail={"error": "Homework trashed", "code": "TRASHED"})

    normalized = normalize_content_json_for_runtime(hw.get("content_json") or {})
    safe = redact_for_runtime(normalized, hw_id=hw.get("id") or hw_id)
    meta = safe.get("meta") or {}
    return {
        "id": hw.get("id"),
        "title": meta.get("title") or hw.get("title"),
        "subject": hw.get("subject"),
        "grade": hw.get("grade"),
        "lang": meta.get("lang") or hw.get("language") or "uz",
        "flow_version": safe.get("flow_version"),
        "content_json": safe,
    }


@router.get("/runtime/homeworks/{hw_id}/gate-state")
async def runtime_gate_state(hw_id: str, session_id: Optional[str] = Query(default=None)):
    """Server-authoritative gate state for the two Learning Sections.

    practice_arc_unlocked is true only when BOTH learning sections pass. Without
    a session_id we report the structure with zero progress (a fresh student).
    """
    hw = await get_homework(hw_id)
    if not hw:
        raise HTTPException(status_code=404, detail={"error": "Homework not found", "code": "NOT_FOUND"})
    if hw.get("deleted_at"):
        raise HTTPException(status_code=409, detail={"error": "Homework trashed", "code": "TRASHED"})

    return await compute_gate_state(session_id, hw_id)
