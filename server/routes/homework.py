from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any

from server import db
from server.services.routing import SUBJECTS, ALWAYS_HARD, SUBJECT_GRADES, SUBJECT_TO_FAMILY

router = APIRouter(prefix="/homeworks", tags=["homework"])

class HomeworkCreate(BaseModel):
    title: str
    subject: str
    grade: int
    mode: str
    content_json: Optional[Dict[str, Any]] = None

class HomeworkUpdate(BaseModel):
    title: Optional[str] = None
    content_json: Optional[Dict[str, Any]] = None

@router.get("")
async def list_homeworks(
    q: Optional[str] = Query(None),
    subject: Optional[str] = Query(None),
    grade: Optional[int] = Query(None),
    mode: Optional[str] = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
    legacy: bool = Query(False),
    include_deleted: bool = Query(False),
):
    # Clamp limit to 200 max — silently friendly.
    limit = min(limit, 200)
    result = await db.search_homeworks(
        q=q,
        subject=subject,
        grade=grade,
        mode=mode,
        include_deleted=include_deleted,
        limit=limit,
        offset=offset,
    )
    if legacy:
        # TODO(post-frontend-cutover): remove legacy=true branch
        return result["items"]
    return result

@router.post("")
async def create_homework(hw: HomeworkCreate):
    if hw.subject not in SUBJECTS:
        raise HTTPException(status_code=400, detail={"error": "Invalid subject", "code": "INVALID_SUBJECT"})

    valid_grades = SUBJECT_GRADES.get(hw.subject, [])
    if hw.grade not in valid_grades:
        raise HTTPException(status_code=400, detail={"error": "Invalid grade for subject", "code": "INVALID_GRADE"})

    mode = hw.mode
    if hw.subject in ALWAYS_HARD:
        mode = "hard"
    elif mode not in ["easy", "hard"]:
        raise HTTPException(status_code=400, detail={"error": "Mode must be easy or hard", "code": "INVALID_MODE"})

    family = SUBJECT_TO_FAMILY.get(hw.subject)

    empty_scaffold = {
      "meta": { "title": hw.title, "subject_display": hw.subject, "section": "", "cefr_level": "" },
      "gate_quote": { "mode": "auto" },
      "panels": [], "flashcards": [], "memory_sprint": [],
      "gb_adaptive_quiz": [], "gb_why_chain": [], "gb_memory_match": [],
      "real_life": None, "boss_questions": [], "reflection": None
    }

    final_content = {**empty_scaffold, **(hw.content_json or {})}
    if hw.content_json and "meta" in hw.content_json:
      final_content["meta"] = {**empty_scaffold["meta"], **hw.content_json["meta"]}

    result = await db.create_homework({
        "title": hw.title,
        "subject": hw.subject,
        "grade": hw.grade,
        "mode": mode,
        "family": family,
        "status": "draft",
        "content_json": final_content
    })

    return result

@router.get("/{hw_id}")
async def get_homework(hw_id: str):
    hw = await db.get_homework(hw_id)
    if not hw:
        raise HTTPException(status_code=404, detail={"error": "Not found", "code": "NOT_FOUND"})
    return hw

@router.put("/{hw_id}")
async def update_homework(hw_id: str, hw_update: HomeworkUpdate):
    hw = await db.get_homework(hw_id)
    if not hw:
        raise HTTPException(status_code=404, detail={"error": "Not found", "code": "NOT_FOUND"})
    if hw.get("deleted_at"):
        raise HTTPException(
            status_code=409,
            detail={"error": "Cannot update a trashed homework. Restore it first.", "code": "TRASHED"},
        )

    updates = hw_update.model_dump(exclude_unset=True)
    if not updates:
        return hw

    return await db.update_homework(hw_id, updates)

@router.delete("/{hw_id}")
async def delete_homework(hw_id: str):
    """Soft delete — moves to trash."""
    success = await db.delete_homework(hw_id)
    if not success:
        # Either not found, or already trashed — surface both as 404 for idempotency.
        existing = await db.get_homework(hw_id)
        if not existing:
            raise HTTPException(status_code=404, detail={"error": "Not found", "code": "NOT_FOUND"})
        # Already trashed — treat as success/no-op.
        return {"ok": True, "already_trashed": True}

    return {"ok": True, "trashed": True}


@router.post("/{hw_id}/restore")
async def restore_homework(hw_id: str):
    """Restore a soft-deleted homework out of the trash."""
    success = await db.restore_homework(hw_id)
    if not success:
        existing = await db.get_homework(hw_id)
        if not existing:
            raise HTTPException(status_code=404, detail={"error": "Not found", "code": "NOT_FOUND"})
        # Wasn't actually deleted — no-op.
        return {"ok": True, "already_active": True}
    return {"ok": True, "restored": True}


@router.delete("/{hw_id}/permanent")
async def hard_delete_homework(hw_id: str):
    """Admin-only: permanent deletion. Wipes the homework AND its version history."""
    success = await db.hard_delete_homework(hw_id)
    if not success:
        raise HTTPException(status_code=404, detail={"error": "Not found", "code": "NOT_FOUND"})
    return {"ok": True, "hard_deleted": True}


@router.post("/{hw_id}/duplicate")
async def duplicate_homework(hw_id: str):
    """Clone a homework (title+subject+grade+mode+content_json) into a fresh record.
    Status is reset to draft. Version history is NOT cloned.
    """
    source = await db.get_homework(hw_id)
    if not source:
        raise HTTPException(status_code=404, detail={"error": "Not found", "code": "NOT_FOUND"})
    if source.get("deleted_at"):
        raise HTTPException(
            status_code=409,
            detail={"error": "Cannot duplicate a trashed homework. Restore it first.", "code": "TRASHED"},
        )

    result = await db.create_homework({
        "title": f"{source.get('title', 'Homework')} (copy)",
        "subject": source["subject"],
        "grade": source["grade"],
        "mode": source["mode"],
        "family": source["family"],
        "language": source.get("language", "uz"),
        "status": "draft",
        "content_json": source.get("content_json") or {},
    })
    return result
