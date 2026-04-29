"""Wave K — /api/notebook/* route tests.

Covers happy path, all rejection branches, and persistence via the captures GET.
Vision LLM and prefilter are mocked; the rest of the stack runs in-process.
"""
from __future__ import annotations

import asyncio
import json
import os
from unittest.mock import AsyncMock, patch

import aiosqlite
import pytest


# Magic-byte stubs (~150 bytes each)
_JPG_HEAD = b"\xff\xd8\xff\xe0" + b"\x00" * 200
_TXT_HEAD = b"hello, this is plain text not an image " * 10


def _db_path() -> str:
    from server.config import DB_PATH
    return str(DB_PATH)


def _wipe_captures():
    async def _do():
        async with aiosqlite.connect(_db_path()) as conn:
            await conn.execute("DELETE FROM notebook_captures")
            await conn.commit()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_do())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


@pytest.fixture(autouse=True)
def clean_captures():
    _wipe_captures()
    yield


def _make_homework(client, *, with_question: bool = True) -> str:
    """Create a homework with an answer-bearing question for the grader."""
    content = {"flashcards": [], "boss": {"questions": []}}
    if with_question:
        content["practice"] = {
            "questions": [
                {
                    "id": "q1",
                    "q": "Solve x + 3 = 5",
                    "answer_spec": {"expected": "2", "type": "numeric"},
                }
            ]
        }
    resp = client.post("/api/homeworks", json={
        "title": "Notebook test HW",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
        "family": "aniq-fanlar",
        "content_json": content,
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


_VALID_VISION_JSON = {
    "transcribed_text": "x + 3 = 5, so x = 2",
    "confidence": 0.85,
    "matches_expected": True,
    "score_1_to_4": 4,
    "axis_1_concept_id": 4,
    "axis_2_process_integrity": 4,
    "correct": True,
    "feedback": "Toza yechim!",
}


class _FakePF:
    def __init__(self, ok=True, reason=None, deskewed=_JPG_HEAD):
        self.ok = ok
        self.reason = reason
        self.deskewed_bytes = deskewed
        self.detected_skew_deg = 0.0
        self.pen_density_ratio = 0.05
        self.face_ratio = 0.0


def test_grade_missing_image_returns_422(client):
    """No image part → FastAPI 422 before our code runs."""
    resp = client.post("/api/notebook/grade", data={
        "session_id": "sess-route-001",
        "hw_id": "HW-X",
        "question_id": "q1",
    })
    assert resp.status_code == 422


def test_grade_happy_path(client, tmp_path, monkeypatch):
    monkeypatch.setenv("NETS_PHOTO_DIR", str(tmp_path))
    hw_id = _make_homework(client)

    with patch("server.services.notebook_grade.notebook_prefilter.validate",
               return_value=_FakePF()), \
         patch("server.services.notebook_grade.gemini.generate_vision",
               new=AsyncMock(return_value={"text": json.dumps(_VALID_VISION_JSON)})):
        resp = client.post("/api/notebook/grade",
            data={
                "session_id": "sess-route-002",
                "hw_id": hw_id,
                "question_id": "q1",
            },
            files={"image": ("notebook.jpg", _JPG_HEAD, "image/jpeg")},
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["rejected"] is False
    assert data["score_1_to_4"] == 4
    assert data["correct"] is True
    assert data["transcribed_text"].startswith("x + 3 = 5")
    assert data["photo_id"]


def test_grade_rejects_text_file_as_invalid(client, tmp_path, monkeypatch):
    monkeypatch.setenv("NETS_PHOTO_DIR", str(tmp_path))
    hw_id = _make_homework(client)

    resp = client.post("/api/notebook/grade",
        data={
            "session_id": "sess-route-003",
            "hw_id": hw_id,
            "question_id": "q1",
        },
        files={"image": ("note.txt", _TXT_HEAD, "image/jpeg")},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["rejected"] is True
    assert data["reason"] == "invalid_file"
    # Localized retry messages are in the response
    assert "retry_message_uz" in data
    assert "retry_message_ru" in data
    assert "retry_message_en" in data


def test_grade_rejects_oversized_file(client, tmp_path, monkeypatch):
    """6 MB upload exceeds Layer 1 cap (5 MB) and is rejected as invalid_file."""
    monkeypatch.setenv("NETS_PHOTO_DIR", str(tmp_path))
    hw_id = _make_homework(client)

    big = _JPG_HEAD + b"\x00" * (6 * 1024 * 1024 - len(_JPG_HEAD))
    resp = client.post("/api/notebook/grade",
        data={
            "session_id": "sess-route-004",
            "hw_id": hw_id,
            "question_id": "q1",
        },
        files={"image": ("big.jpg", big, "image/jpeg")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["rejected"] is True
    assert data["reason"] == "invalid_file"


def test_grade_invalid_session_id_400(client, tmp_path, monkeypatch):
    """Bad session_id is rejected before reaching the pipeline."""
    monkeypatch.setenv("NETS_PHOTO_DIR", str(tmp_path))
    hw_id = _make_homework(client)

    resp = client.post("/api/notebook/grade",
        data={
            "session_id": "x",  # too short
            "hw_id": hw_id,
            "question_id": "q1",
        },
        files={"image": ("notebook.jpg", _JPG_HEAD, "image/jpeg")},
    )
    assert resp.status_code == 400


def test_captures_get_returns_persisted_rows(client, tmp_path, monkeypatch):
    """After two grades, GET /api/notebook/captures returns both rows."""
    monkeypatch.setenv("NETS_PHOTO_DIR", str(tmp_path))
    hw_id = _make_homework(client)
    sess = "sess-route-005"

    with patch("server.services.notebook_grade.notebook_prefilter.validate",
               return_value=_FakePF()), \
         patch("server.services.notebook_grade.gemini.generate_vision",
               new=AsyncMock(return_value={"text": json.dumps(_VALID_VISION_JSON)})):
        for _ in range(2):
            r = client.post("/api/notebook/grade",
                data={"session_id": sess, "hw_id": hw_id, "question_id": "q1"},
                files={"image": ("n.jpg", _JPG_HEAD, "image/jpeg")},
            )
            assert r.status_code == 200, r.text

    # Now list
    r = client.get(f"/api/notebook/captures?session_id={sess}&hw_id={hw_id}")
    assert r.status_code == 200, r.text
    rows = r.json()["captures"]
    assert len(rows) == 2
    assert all(row["status"] == "graded" for row in rows)


def test_captures_get_validates_session_id(client):
    r = client.get("/api/notebook/captures?session_id=x&hw_id=anything")
    assert r.status_code == 400
