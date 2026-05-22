"""Reflection / finalization HTTP surface.

The thin FastAPI layer over ``services.reflection_engine``. Three endpoints,
all under the ``/api/runtime/reflection`` group so the whole finalize → mark →
redo path is auditable in one file:

  POST /api/runtime/reflection/finalize        -> run the pipeline, return debrief
  GET  /api/runtime/reflection/{hw_id}          -> the persisted debrief (404 if none)
  POST /api/runtime/reflection/redo             -> needs_retry → active + reshuffle

The route never computes any grading/verdict itself — the engine owns that. The
returned debrief never carries answer-bearing data (the engine builds it clean).
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..db.session_repo import get_session
from ..services import reflection_engine

router = APIRouter(tags=["reflection"])


# --- Request models ---

class FinalizeRequest(BaseModel):
    session_id: str
    hw_id: str
    reflection_answers: list[str] = Field(default_factory=list)


class RedoRequest(BaseModel):
    session_id: str
    hw_id: str


# --- Endpoints ---

@router.post("/runtime/reflection/finalize")
async def finalize_reflection(req: FinalizeRequest):
    """Run the full finalization pipeline and return the rich debrief.

    Idempotent-ish: re-finalizing recomputes from the current attempts and
    overwrites the persisted report + session mark.
    """
    session = await get_session(req.session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "Session not found", "code": "SESSION_NOT_FOUND"},
        )
    return await reflection_engine.finalize(
        req.session_id,
        req.hw_id,
        req.reflection_answers,
    )


@router.get("/runtime/reflection/{hw_id}")
async def get_reflection(hw_id: str, session_id: str = Query(...)):
    """Return the persisted mark/debrief for this session+homework.

    404 if the homework was never finalized for this session.
    """
    debrief = await reflection_engine.get_debrief(session_id, hw_id)
    if debrief is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "No reflection report for this session", "code": "NOT_FINALIZED"},
        )
    return debrief


@router.post("/runtime/reflection/redo")
async def redo_reflection(req: RedoRequest):
    """Re-route a needs_retry session back into the Practice Arc.

    Flips status → active, clears Division-3 progress, signals a reshuffle.
    """
    session = await get_session(req.session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "Session not found", "code": "SESSION_NOT_FOUND"},
        )
    return await reflection_engine.redo(req.session_id, req.hw_id)
