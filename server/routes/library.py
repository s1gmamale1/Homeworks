"""Library routes — browse homeworks by subject × grade.

GET /api/library          — paginated list with optional filters
GET /api/library/facets   — distinct subject/grade/mode values for dropdowns
"""

from typing import Optional

from fastapi import APIRouter, Query

from server.db import connect

router = APIRouter(prefix="/library", tags=["library"])


@router.get("")
async def list_library(
    subject: Optional[str] = Query(None),
    grade: Optional[int] = Query(None),
    mode: Optional[str] = Query(None),
    q: Optional[str] = Query(None, description="Full-text search on title and chapter"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    """Return a paginated, filtered list of non-deleted homeworks."""
    conditions = ["deleted_at IS NULL"]
    params: list = []

    if subject:
        conditions.append("subject = ?")
        params.append(subject)

    if grade is not None:
        conditions.append("grade = ?")
        params.append(grade)

    if mode:
        conditions.append("mode = ?")
        params.append(mode)

    if q:
        like = f"%{q}%"
        # Search title; chapter lives inside content_json — also search it via LIKE on the blob.
        conditions.append("(title LIKE ? OR content_json LIKE ?)")
        params.extend([like, like])

    where_clause = " AND ".join(conditions)
    base_sql = f"FROM homeworks WHERE {where_clause}"

    count_sql = f"SELECT COUNT(*) {base_sql}"
    items_sql = (
        f"SELECT id, subject, grade, mode, title, "
        f"json_extract(content_json, '$.meta.section') AS chapter, "
        f"updated_at "
        f"{base_sql} "
        f"ORDER BY updated_at DESC "
        f"LIMIT ? OFFSET ?"
    )

    db = await connect()
    try:
        cursor = await db.execute(count_sql, params)
        row = await cursor.fetchone()
        total = row[0] if row else 0

        cursor = await db.execute(items_sql, params + [limit, offset])
        rows = await cursor.fetchall()
        items = [dict(r) for r in rows]
    finally:
        await db.close()

    return {"items": items, "total": total}


@router.get("/facets")
async def library_facets() -> dict:
    """Return distinct subject, grade, and mode values for filter dropdowns."""
    db = await connect()
    try:
        cur = await db.execute(
            "SELECT DISTINCT subject FROM homeworks WHERE deleted_at IS NULL ORDER BY subject"
        )
        subjects = [r[0] for r in await cur.fetchall()]

        cur = await db.execute(
            "SELECT DISTINCT grade FROM homeworks WHERE deleted_at IS NULL ORDER BY grade"
        )
        grades = [r[0] for r in await cur.fetchall()]

        cur = await db.execute(
            "SELECT DISTINCT mode FROM homeworks WHERE deleted_at IS NULL ORDER BY mode"
        )
        modes = [r[0] for r in await cur.fetchall()]
    finally:
        await db.close()

    return {"subjects": subjects, "grades": grades, "modes": modes}
