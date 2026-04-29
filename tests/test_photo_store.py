"""
Wave K — tests for server.services.photo_store.

pytest tests/test_photo_store.py -v
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest


# ── 1. save + load roundtrip ──────────────────────────────────────────────────

def test_save_load_roundtrip(tmp_path, monkeypatch):
    """Bytes saved must come back byte-for-byte identical on load."""
    monkeypatch.setenv("NETS_PHOTO_DIR", str(tmp_path))

    from server.services import photo_store

    data = b"\xff\xd8\xff\xe0" + b"\x00" * 64 + b"fake jpeg content"
    pid = photo_store.save(data, hw_id="hw-001")

    loaded = photo_store.load(pid, hw_id="hw-001")
    assert loaded == data


# ── 2. save with explicit photo_id ────────────────────────────────────────────

def test_save_with_explicit_photo_id(tmp_path, monkeypatch):
    """When photo_id is provided, the file must land at the expected path."""
    monkeypatch.setenv("NETS_PHOTO_DIR", str(tmp_path))

    from server.services import photo_store

    data = b"image bytes here"
    explicit_id = "my-custom-id-abc123"
    returned_id = photo_store.save(data, hw_id="hw-002", photo_id=explicit_id)

    assert returned_id == explicit_id

    expected_path = tmp_path / "hw-002" / f"{explicit_id}.jpg"
    assert expected_path.exists(), f"Expected file at {expected_path}"
    assert expected_path.read_bytes() == data


# ── 3. load missing → None ────────────────────────────────────────────────────

def test_load_missing_returns_none(tmp_path, monkeypatch):
    """load() must return None for a photo_id that was never saved."""
    monkeypatch.setenv("NETS_PHOTO_DIR", str(tmp_path))

    from server.services import photo_store

    result = photo_store.load("nonexistent-id", hw_id="hw-003")
    assert result is None


# ── 4. delete existing → True; subsequent load → None ────────────────────────

def test_delete_existing(tmp_path, monkeypatch):
    """delete() must return True and the file must be gone afterwards."""
    monkeypatch.setenv("NETS_PHOTO_DIR", str(tmp_path))

    from server.services import photo_store

    data = b"delete me"
    pid = photo_store.save(data, hw_id="hw-004")

    deleted = photo_store.delete(pid, hw_id="hw-004")
    assert deleted is True

    # File should no longer be loadable
    result = photo_store.load(pid, hw_id="hw-004")
    assert result is None


def test_delete_nonexistent_returns_false(tmp_path, monkeypatch):
    """delete() must return False when the photo doesn't exist."""
    monkeypatch.setenv("NETS_PHOTO_DIR", str(tmp_path))

    from server.services import photo_store

    deleted = photo_store.delete("ghost-id", hw_id="hw-004")
    assert deleted is False


# ── 5. hw_id sanitization — path traversal prevention ────────────────────────

def test_hw_id_sanitization_no_path_escape(tmp_path, monkeypatch):
    """hw_id='../etc/passwd' must not escape the NETS_PHOTO_DIR root."""
    monkeypatch.setenv("NETS_PHOTO_DIR", str(tmp_path))

    from server.services import photo_store

    data = b"should be sandboxed"
    pid = photo_store.save(data, hw_id="../etc/passwd")

    # Verify the file was written INSIDE tmp_path (not escaped to /etc/passwd)
    photo_path = photo_store.path_for(pid, hw_id="../etc/passwd")
    resolved = photo_path.resolve()
    tmp_resolved = tmp_path.resolve()

    assert str(resolved).startswith(str(tmp_resolved)), (
        f"Path traversal! File at {resolved} is outside root {tmp_resolved}"
    )

    # Verify the sanitized directory name doesn't contain traversal chars
    parts = resolved.parts
    for part in parts[len(tmp_resolved.parts):]:
        assert ".." not in part, f"Found '..' in path segment: {part!r}"
        assert "/" not in part and "\\" not in part, f"Separator in path segment: {part!r}"
