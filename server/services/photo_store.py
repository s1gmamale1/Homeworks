"""Filesystem-backed photo store. v1 uses local FS; v2 can swap to MinIO/S3
without changing this interface.

Env vars:
  NETS_PHOTO_DIR — base directory for photo storage (default: data/notebook_photos)
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Optional


def _root() -> Path:
    base = os.environ.get("NETS_PHOTO_DIR", "data/notebook_photos")
    return Path(base)


def _safe_hw(hw_id: str) -> str:
    """Sanitize hw_id to prevent path traversal and enforce a max length."""
    sanitized = "".join(c for c in hw_id if c.isalnum() or c in "-_")[:64]
    return sanitized or "unknown"


def save(image_bytes: bytes, *, hw_id: str, photo_id: Optional[str] = None) -> str:
    """Save image bytes under hw_id; return photo_id (UUID string).

    If *photo_id* is not provided a new UUID4 is generated.
    The directory ``{NETS_PHOTO_DIR}/{hw_id}/`` is created on first use.
    """
    photo_id = photo_id or str(uuid.uuid4())
    folder = _root() / _safe_hw(hw_id)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{photo_id}.jpg"
    path.write_bytes(image_bytes)
    return photo_id


def load(photo_id: str, *, hw_id: str) -> Optional[bytes]:
    """Return the raw bytes for *photo_id* under *hw_id*, or None if not found."""
    path = _root() / _safe_hw(hw_id) / f"{photo_id}.jpg"
    if not path.exists():
        return None
    return path.read_bytes()


def delete(photo_id: str, *, hw_id: str) -> bool:
    """Delete the photo file. Returns True if the file existed and was removed."""
    path = _root() / _safe_hw(hw_id) / f"{photo_id}.jpg"
    if path.exists():
        path.unlink()
        return True
    return False


def path_for(photo_id: str, *, hw_id: str) -> Path:
    """Return the resolved Path object for *photo_id* (file may not exist yet)."""
    return _root() / _safe_hw(hw_id) / f"{photo_id}.jpg"
