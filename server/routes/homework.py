from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ValidationError
from typing import Optional, Dict, Any

from server import db
from server.schemas.content import ContentJSON
from server.services.routing import SUBJECTS, ALWAYS_HARD, SUBJECT_GRADES, SUBJECT_TO_FAMILY

router = APIRouter(prefix="/homeworks", tags=["homework"])


def _validate_content_json(content: Any) -> None:
    """Run `content` through ContentJSON. Raises 400 INVALID_CONTENT on failure.

    GPT-5.5 audit (2026-04-29) flagged content_json as the largest long-term
    safety risk: a frontend or agent that drops a key silently corrupts a
    homework. This is the single boundary hook gating PUT + PATCH.
    """
    if content is None:
        return
    if not isinstance(content, dict):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "content_json must be a JSON object",
                "code": "INVALID_CONTENT",
                "details": [{"msg": "content_json is not a dict"}],
            },
        )
    try:
        ContentJSON.model_validate(content)
    except ValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "content_json validation failed",
                "code": "INVALID_CONTENT",
                "details": exc.errors(),
            },
        )

class HomeworkCreate(BaseModel):
    title: str
    subject: str
    grade: int
    mode: str
    content_json: Optional[Dict[str, Any]] = None

class HomeworkUpdate(BaseModel):
    title: Optional[str] = None
    content_json: Optional[Dict[str, Any]] = None

class ContentPatch(BaseModel):
    content_json: Dict[str, Any]


def _deep_merge_content(base: dict, patch: dict) -> dict:
    """Merge `patch` into `base` and return the result.

    Semantics — designed for safe partial updates of `content_json`:
    - Top-level keys present in `patch` overwrite the same keys in `base`.
    - When BOTH sides hold a dict at the same key, recurse (so callers can
      target nested fields like `meta.section` without rewriting `meta`).
    - Arrays are replaced wholesale — no append/merge into existing arrays.
    - `None` in `patch` sets the key to null (does NOT delete it).
    - Keys absent from `patch` are left untouched in `base`.
    """
    out = dict(base) if isinstance(base, dict) else {}
    for key, value in patch.items():
        existing = out.get(key)
        if isinstance(value, dict) and isinstance(existing, dict):
            out[key] = _deep_merge_content(existing, value)
        else:
            out[key] = value
    return out

@router.get("")
async def list_homeworks(
    q: Optional[str] = Query(None),
    subject: Optional[str] = Query(None),
    grade: Optional[int] = Query(None),
    mode: Optional[str] = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
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
      "gb_adaptive_quiz": [], "gb_why_chain": [], "gb_memory_match": [], "gb_puzzle_lock": [], "gb_mystery_box": [], "gb_ttt": [],
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

    if "content_json" in updates:
        _validate_content_json(updates["content_json"])

    return await db.update_homework(hw_id, updates)

@router.patch("/{hw_id}/content")
async def patch_homework_content(hw_id: str, body: ContentPatch):
    """Partial update of `content_json`. Merges the keys you send into the
    existing blob — keys you omit are left alone. Use this when you only want
    to update a subset (e.g., adding `gb_puzzle_lock` without resending every
    other phase). PUT still does a full overwrite.
    """
    hw = await db.get_homework(hw_id)
    if not hw:
        raise HTTPException(status_code=404, detail={"error": "Not found", "code": "NOT_FOUND"})
    if hw.get("deleted_at"):
        raise HTTPException(
            status_code=409,
            detail={"error": "Cannot patch a trashed homework. Restore it first.", "code": "TRASHED"},
        )

    existing = hw.get("content_json") or {}
    merged = _deep_merge_content(existing, body.content_json)
    # Validate the *merged* result, not just the patch — otherwise an
    # accidental key drop in the patch wouldn't be caught.
    _validate_content_json(merged)
    return await db.update_homework(hw_id, {"content_json": merged})

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
