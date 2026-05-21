"""Integration tier — FastAPI TestClient + temp SQLite. Asserts the
schema/route/DB round-trip preserves the CBP shape end-to-end."""
from __future__ import annotations

from factories import full_content_json_with_cbp, valid_checkpoint


def _post_homework(client, content_json):
    payload = {
        "title": "CBP integration test",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
        "family": "aniq-fanlar",
        "content_json": content_json,
    }
    return client.post("/api/homeworks", json=payload)


def test_post_v2_homework_with_cbp_returns_200(client):
    resp = _post_homework(client, full_content_json_with_cbp())
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["content_json"]["flow_version"] == "v2"
    assert "case_based_preview" in data["content_json"]


def test_cbp_checkpoints_preserved_on_read_back(client):
    resp = _post_homework(client, full_content_json_with_cbp())
    assert resp.status_code == 200
    hw_id = resp.json()["id"]
    fetched = client.get(f"/api/homeworks/{hw_id}")
    assert fetched.status_code == 200
    cps = fetched.json()["content_json"]["case_based_preview"]["checkpoints"]
    assert len(cps) == 3
    assert [c["kind"] for c in cps] == ["identify", "decide", "justify"]


def test_homework_page_injects_cbp_constant(client):
    resp = _post_homework(client, full_content_json_with_cbp())
    assert resp.status_code == 200
    hw_id = resp.json()["id"]
    page = client.get(f"/h/{hw_id}")
    assert page.status_code == 200
    assert "const CBP = " in page.text


def test_malformed_cbp_rejected_by_schema_validator():
    """4-checkpoint payload — `CaseBasedPreview` validator rejects directly.

    NB: the `/api/homeworks` route currently does NOT run `ContentJSON`
    validation against incoming `content_json` (it accepts the raw dict).
    Wiring the route boundary to the schema is a follow-up arc; the
    schema-level fence is what PR #1 actually ships, and it is verified
    here against a route-shaped payload.
    """
    from pydantic import ValidationError
    import pytest as _pytest

    from server.schemas.content import CaseBasedPreview

    bad = full_content_json_with_cbp()
    bad["case_based_preview"]["checkpoints"].append(valid_checkpoint("justify"))
    with _pytest.raises(ValidationError):
        CaseBasedPreview(**bad["case_based_preview"])
