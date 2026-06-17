"""Generic media upload endpoint for the builder (Extra Materials → type=file).

POST /api/uploads  — multipart file → saved under server/media/uploads, returns
                     a stable URL the runtime/builder can reference.

URL-only authoring is still the default (link/video types); this exists so an
author can attach a file (PDF, image, audio…) without an external host. Files
are served read-only from /media (mounted in app.py).
"""
from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from server.config import BASE_DIR

router = APIRouter(tags=["uploads"])
log = logging.getLogger(__name__)

UPLOAD_DIR: Path = BASE_DIR / "server" / "media" / "uploads"
MAX_FILE_BYTES = 25 * 1024 * 1024  # 25 MB
_READ_CAP = MAX_FILE_BYTES + 1024  # read a hair past the cap to detect oversize

# Allowlist by extension → coarse "type" the UI uses to pick a renderer. Anything
# not listed is rejected (no executables/scripts).
_EXT_TYPE: dict[str, str] = {
    ".png": "image", ".jpg": "image", ".jpeg": "image", ".gif": "image",
    ".webp": "image", ".svg": "image",
    ".mp3": "audio", ".wav": "audio", ".ogg": "audio", ".m4a": "audio",
    ".mp4": "video", ".webm": "video", ".mov": "video",
    ".pdf": "file", ".txt": "file", ".csv": "file",
    ".doc": "file", ".docx": "file", ".ppt": "file", ".pptx": "file",
    ".xls": "file", ".xlsx": "file",
}


def _safe_ext(filename: str) -> str:
    """Lowercased extension from the original name; '' if none/odd."""
    m = re.search(r"(\.[A-Za-z0-9]{1,8})$", filename or "")
    return m.group(1).lower() if m else ""


@router.post("/uploads")
async def upload_file(file: UploadFile = File(...)) -> dict:
    """Accept one file, validate type + size, store it, return its URL."""
    ext = _safe_ext(file.filename or "")
    kind = _EXT_TYPE.get(ext)
    if not kind:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "unsupported_file_type",
                "message": f"File type '{ext or 'unknown'}' is not allowed.",
                "allowed": sorted(_EXT_TYPE.keys()),
            },
        )

    data = await file.read(_READ_CAP)
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=413,
            detail={"error": "file_too_large", "message": "Max upload size is 25 MB."},
        )
    if not data:
        raise HTTPException(
            status_code=400,
            detail={"error": "empty_file", "message": "The uploaded file is empty."},
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{ext}"
    (UPLOAD_DIR / stored_name).write_bytes(data)

    url = f"/media/uploads/{stored_name}"
    log.info("upload stored: %s (%d bytes, type=%s)", stored_name, len(data), kind)
    return {"url": url, "name": file.filename or stored_name, "type": kind}
