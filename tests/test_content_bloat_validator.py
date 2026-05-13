"""PR 2 — write-time content_json bloat validator regression tests.

Guards: pre-PR-2, the API would happily accept content_json containing inline
`<img src="data:image/png;base64,...">` blobs and 1.5MB single fields,
producing the bloat that broke AI grading on HW-20260429-019. PR 2 adds a
write-boundary validator that rejects these at POST/PUT/PATCH time.

Each test asserts the BAD pre-PR-2 state cannot return:
- bloated content_json saving silently
- existing-row PATCHes being blocked (we explicitly DON'T validate the merged
  result on PATCH so authors can incrementally fix old rows)
"""
from __future__ import annotations

import base64
from pathlib import Path

import pytest
from fastapi import HTTPException

from server.routes.homework import (
    _MAX_FIELD_CHARS,
    _check_no_inline_bloat,
)


ROOT = Path(__file__).resolve().parents[1]


# ── _check_no_inline_bloat — direct unit tests ───────────────────────────────


def test_check_passes_normal_content():
    """Sanity — typical content_json should pass without raising."""
    content = {
        "meta": {"title": "Unit 19"},
        "panels": [
            {"id": 1, "title": "Summary", "blocks": [{"type": "p", "text": "Hello"}]}
        ],
        "boss_questions": [
            {"q": "What is 2+2?", "ans": ["4"]}
        ],
    }
    _check_no_inline_bloat(content)  # no raise


def test_check_rejects_inline_data_url_in_string():
    """A string field with `data:image/...;base64,` MUST raise 422."""
    content = {
        "boss_questions": [
            {"q": 'Read this: <img src="data:image/png;base64,iVBORw0KGgoAAAA"/>'}
        ]
    }
    with pytest.raises(HTTPException) as excinfo:
        _check_no_inline_bloat(content)
    assert excinfo.value.status_code == 422
    detail = excinfo.value.detail
    assert detail["code"] == "BASE64_NOT_ALLOWED_IN_TEXT"
    assert "boss_questions" in detail["path"]
    assert ".q" in detail["path"]


def test_check_rejects_oversized_field():
    """A single string > 200KB MUST raise 422 even without base64."""
    big_text = "x" * (_MAX_FIELD_CHARS + 1)
    content = {"meta": {"section": big_text}}
    with pytest.raises(HTTPException) as excinfo:
        _check_no_inline_bloat(content)
    assert excinfo.value.status_code == 422
    detail = excinfo.value.detail
    assert detail["code"] == "CONTENT_FIELD_TOO_LARGE"
    assert detail["size"] > detail["cap"]
    assert "meta.section" in detail["path"]


def test_check_path_resolves_into_lists():
    """Field path should include list indices for clear error reporting."""
    content = {
        "panels": [
            {"id": 0, "title": "ok"},
            {"id": 1, "title": 'bad <img src="data:image/png;base64,XXX">'},
        ]
    }
    with pytest.raises(HTTPException) as excinfo:
        _check_no_inline_bloat(content)
    assert "[1]" in excinfo.value.detail["path"]
    assert ".title" in excinfo.value.detail["path"]


def test_check_ignores_non_string_leaves():
    """Numbers, bools, None should pass through silently."""
    content = {
        "n": 42,
        "f": 3.14,
        "b": True,
        "none": None,
        "lst": [1, 2.0, False, None, "ok"],
    }
    _check_no_inline_bloat(content)  # no raise


def test_check_recurses_deeply():
    """Bloat hidden 4 levels deep should still be caught."""
    content = {
        "a": {"b": {"c": [{"d": 'data:image/png;base64,XXX'}]}}
    }
    with pytest.raises(HTTPException) as excinfo:
        _check_no_inline_bloat(content)
    assert "a.b.c" in excinfo.value.detail["path"]
    assert "[0].d" in excinfo.value.detail["path"]


def test_check_caps_real_world_bloat():
    """Regression specific to HW-20260429-019: 1.5MB inline base64 in q."""
    bloated_q = 'Real q text <img src="data:image/png;base64,' + ("A" * 1_500_000) + '">'
    content = {"boss_questions": [{"q": bloated_q}]}
    with pytest.raises(HTTPException) as excinfo:
        _check_no_inline_bloat(content)
    # Either failure mode is acceptable (oversized OR base64) — both block.
    assert excinfo.value.detail["code"] in (
        "CONTENT_FIELD_TOO_LARGE",
        "BASE64_NOT_ALLOWED_IN_TEXT",
    )


# ── Integration via TestClient — POST / PUT / PATCH ──────────────────────────
# Requires the `client` fixture from tests/conftest.py (cv2 dependency).


def test_post_rejects_bloated_content(client):
    """POST /api/homeworks with inline base64 in a content field → 422."""
    body = {
        "title": "[BLOAT TEST]",
        "subject": "english",
        "grade": 8,
        "mode": "hard",
        "content_json": {
            "boss_questions": [
                {"q": 'Q with <img src="data:image/png;base64,iVBORw"/>', "ans": ["x"]}
            ]
        },
    }
    resp = client.post("/api/homeworks", json=body)
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "BASE64_NOT_ALLOWED_IN_TEXT"


def test_post_accepts_clean_content(client):
    """POST with normal content → 200 (sanity)."""
    body = {
        "title": "[clean]",
        "subject": "english",
        "grade": 8,
        "mode": "hard",
        "content_json": {
            "meta": {"title": "Test"},
            "boss_questions": [{"q": "What is 2+2?", "ans": ["4"]}],
        },
    }
    resp = client.post("/api/homeworks", json=body)
    assert resp.status_code == 200


def test_put_rejects_bloated_overwrite(client):
    """PUT a bloated content_json onto an existing row → 422."""
    # Seed a clean row first.
    seed = client.post(
        "/api/homeworks",
        json={
            "title": "[seed]",
            "subject": "english",
            "grade": 8,
            "mode": "hard",
            "content_json": {"meta": {"title": "x"}},
        },
    )
    assert seed.status_code == 200
    hw_id = seed.json()["id"]

    # PUT bloated content — must be rejected.
    resp = client.put(
        f"/api/homeworks/{hw_id}",
        json={
            "content_json": {
                "boss_questions": [
                    {"q": 'data:image/png;base64,XXXXXXXXXXXXXXXXXX', "ans": ["y"]}
                ]
            }
        },
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "BASE64_NOT_ALLOWED_IN_TEXT"


def test_patch_rejects_bloated_incoming(client):
    """PATCH with bloated patch content → 422."""
    seed = client.post(
        "/api/homeworks",
        json={
            "title": "[seed-patch]",
            "subject": "english",
            "grade": 8,
            "mode": "hard",
            "content_json": {"meta": {"title": "x"}},
        },
    )
    hw_id = seed.json()["id"]

    resp = client.patch(
        f"/api/homeworks/{hw_id}/content",
        json={
            "content_json": {
                "boss_questions": [
                    {"q": 'data:image/png;base64,YYYYYYYY', "ans": ["z"]}
                ]
            }
        },
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "BASE64_NOT_ALLOWED_IN_TEXT"
    assert "patch" in resp.json()["detail"]["path"]


def test_patch_does_not_block_clean_patches_on_existing_bloated_rows(client):
    """Critical: existing rows may have pre-PR-2 bloat. PATCH validates only
    the INCOMING patch dict, NOT the merged result, so authors can fix
    bloated rows incrementally. A clean patch must succeed even if the row
    already carries bloat in another field."""
    # We can't create a bloated row through the public API anymore (PR 2 blocks
    # it). Simulate the legacy state by going around the API — write directly
    # to the DB. This mirrors the real-world case where pre-PR-2 rows exist.
    import asyncio

    from server import db as db_mod

    bloated_seed = {
        "title": "[legacy-bloated]",
        "subject": "english",
        "grade": 8,
        "mode": "hard",
        "family": "til-fanlar",
        "status": "draft",
        "content_json": {
            "meta": {"title": "Legacy"},
            "boss_questions": [
                {"q": 'data:image/png;base64,LEGACYBLOAT', "ans": ["a"]}
            ],
        },
    }
    created = asyncio.run(db_mod.create_homework(bloated_seed))
    hw_id = created["id"]

    # Now a clean patch on an unrelated key should succeed.
    resp = client.patch(
        f"/api/homeworks/{hw_id}/content",
        json={"content_json": {"meta": {"title": "Updated cleanly"}}},
    )
    assert resp.status_code == 200, (
        f"Clean patch should not be blocked by pre-existing bloat in another "
        f"field. Got {resp.status_code}: {resp.text}"
    )


def test_patch_extracts_structured_image_data_uri_before_bloat_check(client):
    """Structured image media is migrated to /generated instead of rejected.

    Text fields with base64 still fail closed; this path only applies to an
    authored image block where the server can preserve the visual safely.
    """
    seed = client.post(
        "/api/homeworks",
        json={
            "title": "[structured-image-upload]",
            "subject": "math-algebra",
            "grade": 8,
            "mode": "hard",
            "content_json": {"meta": {"title": "x"}},
        },
    )
    assert seed.status_code == 200, seed.text
    hw_id = seed.json()["id"]
    tiny_png = base64.b64encode(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
        b"\x00\x00\x00\x1f\x15\xc4\x89"
    ).decode("ascii")

    resp = client.patch(
        f"/api/homeworks/{hw_id}/content",
        json={
            "content_json": {
                "panels": [
                    {"pages": [{"blocks": [{"type": "image", "src": f"data:image/png;base64,{tiny_png}"}]}]}
                ]
            }
        },
    )
    assert resp.status_code == 200, resp.text
    src = resp.json()["content_json"]["panels"][0]["pages"][0]["blocks"][0]["src"]
    written = ROOT / "frontend" / src.lstrip("/")
    try:
        assert src.startswith(f"/generated/{hw_id}__media_")
        assert written.exists()
    finally:
        written.unlink(missing_ok=True)


# ── Bug A regression: rich-field HTML data URIs ──────────────────────────────
#
# Pre-fix: `<img src="data:image/png;base64,…">` embedded in HTML stored under
# rich-field keys (boss.q, real_life.q1.q, flashcards.def, etc. — anything not
# named `html` or `text`) was missed by migration, then rejected by the bloat
# validator with HTTP 422. Author saw "Save failed" on every image upload.


_TINY_PNG_B64 = base64.b64encode(
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
    b"\x00\x00\x00\x1f\x15\xc4\x89"
).decode("ascii")


def _seed_clean_homework(client, subject: str = "math-algebra") -> str:
    seed = client.post(
        "/api/homeworks",
        json={
            "title": "[richfield-image-upload]",
            "subject": subject,
            "grade": 8,
            "mode": "hard",
            "content_json": {"meta": {"title": "x"}},
        },
    )
    assert seed.status_code == 200, seed.text
    return seed.json()["id"]


def test_patch_extracts_data_uri_from_boss_question_q(client):
    """Bug A regression: <img data:URI> inside boss_questions[].q must extract."""
    hw_id = _seed_clean_homework(client)
    html_with_image = (
        '<p>Solve: <span class="image-wrap">'
        f'<img src="data:image/png;base64,{_TINY_PNG_B64}" alt="">'
        '</span></p>'
    )
    resp = client.patch(
        f"/api/homeworks/{hw_id}/content",
        json={"content_json": {"boss_questions": [{"id": "bq_0", "q": html_with_image, "ans": ["4"]}]}},
    )
    assert resp.status_code == 200, resp.text
    saved_q = resp.json()["content_json"]["boss_questions"][0]["q"]
    assert "data:image/png;base64," not in saved_q
    assert f"/generated/{hw_id}__media_" in saved_q
    # The extracted file should exist on disk.
    import re as _re
    match = _re.search(r'src="(/generated/[^"]+)"', saved_q)
    assert match, f"Expected /generated/ src in saved q: {saved_q}"
    written = ROOT / "frontend" / match.group(1).lstrip("/")
    try:
        assert written.exists(), f"Extracted file missing: {written}"
    finally:
        written.unlink(missing_ok=True)


def test_put_extracts_data_uri_from_real_life_question(client):
    """Bug A regression: <img data:URI> inside real_life.q1.prompt must extract on PUT."""
    hw_id = _seed_clean_homework(client)
    html_with_image = (
        '<p>What is X? '
        f'<div class="image-wrap"><img src="data:image/png;base64,{_TINY_PNG_B64}" alt=""></div>'
        '</p>'
    )
    resp = client.put(
        f"/api/homeworks/{hw_id}",
        json={"content_json": {"real_life": {"story": "...", "q1": {"prompt": html_with_image, "ans": "42", "fb": ""}}}},
    )
    assert resp.status_code == 200, resp.text
    saved_prompt = resp.json()["content_json"]["real_life"]["q1"]["prompt"]
    assert "data:image/png;base64," not in saved_prompt
    assert f"/generated/{hw_id}__media_" in saved_prompt
    import re as _re
    match = _re.search(r'src="(/generated/[^"]+)"', saved_prompt)
    assert match
    written = ROOT / "frontend" / match.group(1).lstrip("/")
    try:
        assert written.exists()
    finally:
        written.unlink(missing_ok=True)


def test_patch_extracts_data_uri_from_flashcard_def(client):
    """Bug A regression: <img data:URI> inside flashcards[].def must extract."""
    hw_id = _seed_clean_homework(client)
    html_with_image = (
        f'Pythagoras: <img src="data:image/png;base64,{_TINY_PNG_B64}" alt="triangle">'
    )
    resp = client.patch(
        f"/api/homeworks/{hw_id}/content",
        json={"content_json": {"flashcards": [{"term": "Triangle", "def": html_with_image}]}},
    )
    assert resp.status_code == 200, resp.text
    saved_def = resp.json()["content_json"]["flashcards"][0]["def"]
    assert "data:image/png;base64," not in saved_def
    assert f"/generated/{hw_id}__media_" in saved_def
    import re as _re
    match = _re.search(r'src="(/generated/[^"]+)"', saved_def)
    assert match
    written = ROOT / "frontend" / match.group(1).lstrip("/")
    try:
        assert written.exists()
    finally:
        written.unlink(missing_ok=True)


# ── Bug B regression: authored SVG with marker substring survives ────────────
#
# Pre-fix: `_is_generic_svg` matched the marker phrases anywhere in the SVG
# body via substring containment. Authored SVGs whose <text> or <path> data
# happened to include the phrase ("Look at this formula diagram showing …")
# were silently replaced with a generic context SVG on every save — the
# "image overwritten by a different image" symptom. Tightened to require the
# marker as the exact trimmed body of <text>/<title>/<desc> or aria-label.


def test_authored_svg_with_marker_substring_is_preserved(client):
    """Bug B regression: authored SVG mentioning 'formula diagram' inside longer
    <text> survives migration unchanged.
    """
    from server.services.content_media_migration import migrate_content_media

    authored = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        '<text x="10" y="20">Look at this formula diagram and solve</text>'
        '<circle cx="50" cy="50" r="40" fill="red"/>'
        '</svg>'
    )
    content = {"real_life": {"q1": {"q": "X?", "media": {"type": "svg", "html": authored}}}}
    migrated, _, stats = migrate_content_media(
        content, subject="math-algebra", hw_id="HW-AUTHORED", write_files=False
    )
    assert stats.generic_svgs_rewritten == 0
    assert migrated["real_life"]["q1"]["media"]["html"] == authored


def test_placeholder_svg_with_bare_marker_still_rewrites(client):
    """Bug B legitimate path: AI placeholder SVG with bare <text>Homework
    diagram</text> (no other content) still gets rewritten to context SVG.
    Preserves the original placeholder-cleanup behavior.
    """
    from server.services.content_media_migration import migrate_content_media

    placeholder = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="720">'
        '<text>Homework diagram</text>'
        '<text>Formula diagram</text>'
        '</svg>'
    )
    content = {"real_life": {"q1": {"q": "X?", "media": {"type": "svg", "html": placeholder}}}}
    migrated, _, stats = migrate_content_media(
        content, subject="math-algebra", hw_id="HW-PLACEHOLDER", write_files=False
    )
    assert stats.generic_svgs_rewritten == 1
    rewritten = migrated["real_life"]["q1"]["media"]["html"]
    assert rewritten != placeholder
    assert 'aria-label=' in rewritten
    assert "Homework diagram" not in rewritten
    assert "Formula diagram" not in rewritten


def test_authored_svg_with_marker_inside_aria_label_text_is_preserved():
    """Bug B regression: an authored SVG whose aria-label contains the phrase
    as part of a longer description should NOT trip the placeholder check.
    """
    from server.services.content_media_migration import migrate_content_media

    authored = (
        '<svg xmlns="http://www.w3.org/2000/svg" aria-label="My formula diagram with sin(x)" viewBox="0 0 100 100">'
        '<path d="M10 10 L90 90" stroke="blue"/>'
        '</svg>'
    )
    migrated, _, stats = migrate_content_media(
        {"media": {"type": "svg", "html": authored}}, subject="math-algebra", hw_id="HW-X", write_files=False
    )
    assert stats.generic_svgs_rewritten == 0
    assert migrated["media"]["html"] == authored
