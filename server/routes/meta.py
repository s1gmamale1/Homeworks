import json
import re
import sys

from fastapi import APIRouter, HTTPException, Query

from .. import db
from ..config import FIXTURES_DIR
from ..services import quotes as quotes_service
from ..services.gemini import ACTIVE_BACKEND
from ..services.routing import (
    ALWAYS_HARD,
    FAMILY_COLORS,
    PHASE_ICONS,
    PHASE_NAMES,
    PHASE_PIPELINE,
    STATUS_COLORS,
    SUBJECT_GRADES,
    SUBJECT_TO_FAMILY,
    SUBJECTS,
)

router = APIRouter(tags=["meta"])

# --- Fixture helpers (local to meta.py) ---

_SAFE_NAME = re.compile(r"^[a-z0-9\-]+$")
_ALWAYS_HARD_SUBJECTS = {"english", "history"}
_CEFR_LEVELS = {"a1", "a2", "b1", "b2"}


def _parse_fixture_name(stem: str) -> dict:
    """Parse filename stem into metadata. Returns {subject, grade, mode, cefr_level}.

    Format: {subject}-g{grade}-{mode_or_level}.json
    Examples:
        math-algebra-g8-hard  -> subject=math-algebra, grade=8, mode=hard
        english-g10-b1        -> subject=english, grade=10, mode=hard, cefr_level=b1
        history-g8            -> subject=history, grade=8, mode=hard
    """
    match = re.match(r"^(.+?)-g(\d+)(?:-([a-z0-9]+))?$", stem)
    if not match:
        return {"subject": stem, "grade": None, "mode": None, "cefr_level": None}

    subject, grade_str, suffix = match.group(1), match.group(2), match.group(3)
    grade = int(grade_str)

    cefr = None
    mode = None
    if suffix:
        if suffix in _CEFR_LEVELS:
            cefr = suffix
            mode = "hard"  # CEFR subjects (english) are always hard
        elif suffix in ("easy", "hard"):
            mode = suffix
        else:
            mode = suffix  # unknown — pass through
    else:
        if subject in _ALWAYS_HARD_SUBJECTS:
            mode = "hard"
        else:
            mode = None

    return {"subject": subject, "grade": grade, "mode": mode, "cefr_level": cefr}


@router.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "ai_backend": ACTIVE_BACKEND,  # vertex | gemini_api | kimi | none
        "ai_ready": ACTIVE_BACKEND != "none",
        # Legacy field for existing frontend checks
        "gemini": ACTIVE_BACKEND != "none",
    }


@router.get("/subjects")
async def subjects() -> dict:
    """Returns subject list + family colors + phase metadata for frontend."""
    return {
        "subjects": [
            {
                "id": s,
                "family": SUBJECT_TO_FAMILY[s],
                "always_hard": s in ALWAYS_HARD,
                "grades": SUBJECT_GRADES[s],
            }
            for s in SUBJECTS
        ],
        "families": FAMILY_COLORS,
        "statuses": STATUS_COLORS,
        "phase_names": PHASE_NAMES,
        "phase_icons": PHASE_ICONS,
        # Pipeline keyed by "family:mode" string for JSON compatibility
        "pipelines": {
            f"{fam}:{mode}": phases
            for (fam, mode), phases in PHASE_PIPELINE.items()
        },
    }


@router.get("/fixtures")
async def list_fixtures() -> dict:
    """List available fixture templates with metadata parsed from filenames and meta fields."""
    if not FIXTURES_DIR.exists():
        return {"fixtures": []}

    results = []
    for fpath in sorted(FIXTURES_DIR.glob("*.json")):
        # Skip non-homework fixtures (tests, private helpers)
        if fpath.stem.startswith("_") or fpath.stem.startswith("tutor-"):
            continue
        try:
            data = json.loads(fpath.read_text(encoding="utf-8"))
            parsed = _parse_fixture_name(fpath.stem)
            meta = data.get("meta") or {}
            results.append({
                "name": fpath.stem,
                "title": meta.get("title", fpath.stem),
                "subject": parsed["subject"],
                "subject_display": meta.get("subject_display", parsed["subject"]),
                "grade": parsed["grade"],
                "mode": parsed["mode"],
                "cefr_level": meta.get("cefr_level") or parsed["cefr_level"],
            })
        except Exception as e:
            print(f"[fixtures] skipped {fpath.name}: {e}", file=sys.stderr)

    results.sort(key=lambda x: (x["subject"], x["grade"] or 0))
    return {"fixtures": results}


@router.get("/quotes")
async def list_quotes(
    q: str | None = Query(None, description="Substring search over text + author"),
    type: str | None = Query(None, description="fact | quote"),
    origin: str | None = Query(None, description="National | Global"),
    category: str | None = None,
    author: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    """Searchable view over the gate-quote library.

    Used by the builder's quote-picker modal. Returns matching items plus
    facets so the UI can populate its filter selects from one round-trip.
    """
    library = quotes_service.all_quotes()

    needle = (q or "").strip().casefold()
    items = []
    for entry in library:
        if type and str(entry.get("type", "")).casefold() != type.casefold():
            continue
        if origin and str(entry.get("origin", "")).casefold() != origin.casefold():
            continue
        if category and str(entry.get("category", "")).casefold() != category.casefold():
            continue
        if author and str(entry.get("author", "")).casefold() != author.casefold():
            continue
        if needle:
            haystack = (
                str(entry.get("text", "")).casefold()
                + "\n"
                + str(entry.get("author", "")).casefold()
            )
            if needle not in haystack:
                continue
        items.append(entry)

    total = len(items)
    paged = items[offset : offset + limit]

    # Facets are computed against the full library, not the current filter, so
    # the user can always see every available value to pivot to.
    def _facet(field: str) -> list[str]:
        seen: dict[str, int] = {}
        for entry in library:
            val = str(entry.get(field, "")).strip()
            if not val:
                continue
            seen[val] = seen.get(val, 0) + 1
        return sorted(seen.keys())

    return {
        "items": paged,
        "total": total,
        "limit": limit,
        "offset": offset,
        "facets": {
            "types": _facet("type"),
            "origins": _facet("origin"),
            "categories": _facet("category"),
            "authors": _facet("author"),
        },
    }


@router.get("/fixtures/{name}")
async def get_fixture(name: str):
    """Return the full content_json of a specific fixture."""
    if not _SAFE_NAME.match(name):
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid fixture name", "code": "INVALID_NAME"},
        )

    fpath = FIXTURES_DIR / f"{name}.json"
    if not fpath.exists():
        raise HTTPException(
            status_code=404,
            detail={"error": "Fixture not found", "code": "NOT_FOUND"},
        )

    try:
        return json.loads(fpath.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail={"error": f"Fixture malformed: {e}", "code": "FIXTURE_MALFORMED"},
        )


# --- Trash & version history ---


@router.get("/trash")
async def list_trash() -> dict:
    """List soft-deleted homeworks (the Trash view)."""
    items = await db.list_trashed_homeworks()
    return {"items": items, "count": len(items)}


@router.get("/homeworks/{hw_id}/versions")
async def list_homework_versions(hw_id: str) -> dict:
    """List version snapshots for a homework, newest first.
    Metadata only — no content_json payload, to keep the list cheap.
    """
    hw = await db.get_homework(hw_id)
    if not hw:
        raise HTTPException(
            status_code=404, detail={"error": "Not found", "code": "NOT_FOUND"}
        )
    versions = await db.list_versions(hw_id)
    return {"homework_id": hw_id, "versions": versions, "count": len(versions)}


@router.get("/homeworks/{hw_id}/versions/{version_id}")
async def get_homework_version(hw_id: str, version_id: int) -> dict:
    """Return a specific version's full content (for preview or diff)."""
    version = await db.get_version(version_id)
    if not version:
        raise HTTPException(
            status_code=404, detail={"error": "Version not found", "code": "NOT_FOUND"}
        )
    if version["homework_id"] != hw_id:
        raise HTTPException(
            status_code=400,
            detail={"error": "Version does not belong to this homework", "code": "MISMATCH"},
        )
    return version


@router.post("/homeworks/{hw_id}/versions/{version_id}/restore")
async def restore_homework_version(hw_id: str, version_id: int) -> dict:
    """Restore a version's content back onto the live homework.
    A snapshot of the current state is automatically taken before overwrite.
    """
    hw = await db.get_homework(hw_id)
    if not hw:
        raise HTTPException(
            status_code=404, detail={"error": "Not found", "code": "NOT_FOUND"}
        )
    version = await db.get_version(version_id)
    if not version:
        raise HTTPException(
            status_code=404, detail={"error": "Version not found", "code": "NOT_FOUND"}
        )
    if version["homework_id"] != hw_id:
        raise HTTPException(
            status_code=400,
            detail={"error": "Version does not belong to this homework", "code": "MISMATCH"},
        )
    result = await db.restore_version(version_id)
    if not result:
        raise HTTPException(
            status_code=500,
            detail={"error": "Restore failed", "code": "RESTORE_FAILED"},
        )
    return {"ok": True, "restored_from_version": version_id, "homework": result}


@router.post("/admin/checkpoint")
async def force_checkpoint() -> dict:
    """Force a WAL checkpoint. Useful before backups or manual DB inspection."""
    await db.checkpoint()
    return {"ok": True}
