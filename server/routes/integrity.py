"""Academic-integrity HTTP surface (research §9.6 — authorship affirmation).

Thin FastAPI layer over the affirmations repo + the review-queue resolver.
Integrity here is TEACHER INTELLIGENCE: a teacher records that they reviewed a
session and affirm (or decline) the student's authorship, optionally resolving
the integrity review-queue items the signals raised.

Endpoints (mounted with the app-wide ``/api`` prefix, like every other router):
  POST /api/integrity/affirm                      -> create an affirmation
  GET  /api/integrity/affirmations?session_id&hw  -> list affirmations (JSON)
  GET  /api/integrity/affirmations/view?session_id-> read-only <pre> JSON dump

This router computes no grade and no verdict — affirmation is advisory metadata.
"""
import json
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .. import db

router = APIRouter(tags=["integrity"])


# --- Request models ---


class AffirmRequest(BaseModel):
    session_id: str
    homework_id: str
    teacher_id: Optional[str] = None
    affirmed: bool = False
    note: Optional[str] = None
    checkpoints: list = Field(default_factory=list)
    # Integrity review-queue item ids the teacher is resolving as part of this
    # affirmation. Each is marked resolved with a teacher_affirmation decision.
    resolve_queue_ids: list[int] = Field(default_factory=list)


# --- Endpoints ---


@router.post("/integrity/affirm")
async def affirm(req: AffirmRequest) -> dict:
    """Record a teacher's authorship affirmation for a session.

    Side effect: any ``resolve_queue_ids`` are resolved in the review queue with
    a ``{"resolved_by": "teacher_affirmation", ...}`` decision, so the audit
    trail links the affirmation to the integrity signals it addressed.
    """
    resolved_ids: list[int] = []
    for qid in req.resolve_queue_ids:
        try:
            ok = await db.resolve_review_item(
                int(qid),
                {
                    "resolved_by": "teacher_affirmation",
                    "session_id": req.session_id,
                    "homework_id": req.homework_id,
                    "teacher_id": req.teacher_id,
                    "affirmed": bool(req.affirmed),
                },
            )
        except Exception:
            ok = False
        if ok:
            resolved_ids.append(int(qid))

    record = await db.create_affirmation(
        req.session_id,
        req.homework_id,
        teacher_id=req.teacher_id,
        affirmed=req.affirmed,
        note=req.note,
        checkpoints=req.checkpoints,
        integrity_queue_ids=resolved_ids,
    )
    return {"ok": True, "affirmation": record, "resolved_queue_ids": resolved_ids}


@router.get("/integrity/affirmations")
async def list_affirmations_endpoint(
    session_id: Optional[str] = Query(default=None),
    homework_id: Optional[str] = Query(default=None),
) -> list[dict]:
    """List affirmations, optionally filtered by session and/or homework."""
    return await db.list_affirmations(session_id=session_id, homework_id=homework_id)


@router.get("/integrity/affirmations/view", response_class=HTMLResponse)
async def view_affirmations(
    session_id: Optional[str] = Query(default=None),
) -> HTMLResponse:
    """Read-only ``<pre>`` JSON dump of a session's affirmations (no framework)."""
    rows = await db.list_affirmations(session_id=session_id)
    body = json.dumps(rows, ensure_ascii=False, indent=2)
    # textContent-safe: escape the only characters that could break out of <pre>.
    safe = body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return HTMLResponse(f"<pre>{safe}</pre>")
