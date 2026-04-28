"""Smoke tests for the permanent share URL + builder preview endpoints
exposed by `server/routes/homework_page.py`. Covers the three response branches:

  - 200: existing, non-trashed homework returns rendered HTML with the AI
         bootstrap injected (`<script src="/static/runtime/runtime.js">`).
  - 404: missing id returns a browser-friendly HTML 404 page on `/h/{id}`
         and a JSON-style 404 on `/api/homeworks/{id}/preview`.
  - 409: trashed homework returns 409 (HTML body on `/h/{id}`,
         JSON detail on `/api/homeworks/{id}/preview`).
"""

import pytest


@pytest.fixture
def created_hw(client):
    """Create a fresh homework via the API; return its dict.

    Independent from the session-scoped `sample_homework` fixture so each test
    can mutate state (trash, delete) without poisoning the shared fixture.
    """
    payload = {
        "title": "Homework page smoke",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
        "family": "aniq-fanlar",
        "content_json": {
            "meta": {
                "title": "Homework page smoke",
                "subject_display": "Algebra",
            },
            "panels": [],
            "flashcards": [],
            "boss_questions": [],
            "memory_sprint": [],
        },
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_h_route_renders_html_with_ai_bootstrap(client, created_hw):
    """200 branch — /h/{id} for a live homework returns HTML + runtime."""
    r = client.get(f"/h/{created_hw['id']}")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    body = r.text
    # Sanity: it's the rendered template, not the 404/409 placeholder.
    assert "<title>Topilmadi" not in body
    assert "<title>O'chirilgan" not in body
    # AI bootstrap is now always injected (Wave B1+B2 requirement).
    assert "runtime.js" in body
    assert "NETS_CTX" in body


def test_h_route_missing_id_returns_friendly_404(client):
    """404 branch — unknown id returns the friendly HTML page, not raw JSON."""
    r = client.get("/h/HW-99999999-999")
    assert r.status_code == 404
    assert "text/html" in r.headers.get("content-type", "")
    assert "404" in r.text
    # Should be the friendly placeholder, NOT the rendered template.
    assert "NETS_CTX" not in r.text


def test_h_route_trashed_homework_returns_409(client, created_hw):
    """409 branch — trashed homework returns the friendly 409 HTML page."""
    # Soft-delete the homework via the same path the dashboard uses.
    del_resp = client.delete(f"/api/homeworks/{created_hw['id']}")
    assert del_resp.status_code in (200, 204), del_resp.text

    r = client.get(f"/h/{created_hw['id']}")
    assert r.status_code == 409
    assert "text/html" in r.headers.get("content-type", "")
    assert "409" in r.text
    # Friendly placeholder, not rendered template.
    assert "NETS_CTX" not in r.text


def test_preview_route_renders_html_no_cache(client, created_hw):
    """Builder preview keeps the same render contract but with no-cache headers."""
    r = client.get(f"/api/homeworks/{created_hw['id']}/preview")
    assert r.status_code == 200
    assert "no-cache" in r.headers.get("cache-control", "").lower()
    body = r.text
    assert "runtime.js" in body
    assert "NETS_CTX" in body


def test_preview_route_missing_id_returns_json_404(client):
    """Builder preview returns JSON-style HTTPException, not the friendly HTML."""
    r = client.get("/api/homeworks/HW-99999999-999/preview")
    assert r.status_code == 404
    # FastAPI HTTPException with detail dict serializes to JSON.
    body = r.json()
    assert body["detail"]["code"] == "NOT_FOUND"


def test_preview_route_trashed_returns_json_409(client, created_hw):
    """Builder preview surfaces 409 with TRASHED code so the iframe can react."""
    del_resp = client.delete(f"/api/homeworks/{created_hw['id']}")
    assert del_resp.status_code in (200, 204), del_resp.text

    r = client.get(f"/api/homeworks/{created_hw['id']}/preview")
    assert r.status_code == 409
    body = r.json()
    assert body["detail"]["code"] == "TRASHED"


# ──────────────────────────────────────────────────────────────────
# Wave F2 — persistent AI tutor widget
# ──────────────────────────────────────────────────────────────────

def test_tutor_widget_dom_present(client, created_hw):
    """Rendered homework HTML must contain the persistent tutor widget DOM."""
    r = client.get(f"/h/{created_hw['id']}")
    assert r.status_code == 200
    body = r.text
    # Required IDs from the F2 spec.
    for needle in (
        'id="nets-ai-tutor"',
        'id="nets-tutor-fab"',
        'id="nets-tutor-panel"',
        'id="nets-tutor-messages"',
        'id="nets-tutor-input-form"',
        'id="nets-tutor-phase-badge"',
    ):
        assert needle in body, f"missing tutor widget DOM: {needle}"
    # Phase-change event must be dispatched somewhere in the template JS.
    assert "nets:phase-change" in body


def test_tutor_widget_inline_no_external_assets(client, created_hw):
    """Tutor widget assets are inline — no NEW external <link rel='stylesheet' href='https?://…'>."""
    r = client.get(f"/h/{created_hw['id']}")
    assert r.status_code == 200
    body = r.text.lower()
    # No external stylesheet links allowed (relative same-origin links are also disallowed
    # by the inline-only constraint, but we specifically guard against http/https hosts).
    import re as _re
    matches = _re.findall(r'<link[^>]+rel\s*=\s*["\']stylesheet["\'][^>]*>', body)
    for tag in matches:
        # Allow data: URLs only (none currently). External http/https hosts are forbidden.
        assert 'href="http' not in tag and "href='http" not in tag, \
            f"unexpected external stylesheet in tutor widget area: {tag}"


# ──────────────────────────────────────────────────────────────────
# Phase 0-A — gate quote (curated library + skip lock)
# ──────────────────────────────────────────────────────────────────


def test_h_route_renders_single_gate_quote(client, created_hw):
    """The runtime template now ships with a single-element QUOTES array
    (server-side selector picks one per inject) and an author chip."""
    r = client.get(f"/h/{created_hw['id']}")
    assert r.status_code == 200
    body = r.text
    # Single quote injected — array literal contains exactly one object.
    import re as _re
    match = _re.search(r"const QUOTES\s*=\s*(\[[\s\S]*?\]);", body)
    assert match, "QUOTES array not found in rendered HTML"
    arr_literal = match.group(1)
    # Only one object in the array (one closing brace immediately before the closing bracket).
    assert arr_literal.count("{") == 1, f"expected exactly 1 quote, got literal: {arr_literal[:200]}"
    # Author chip CSS class is in the template.
    assert "quote-author-chip" in body
    # Skip lock ring CSS is in the template.
    assert "skip-lock-ring" in body


def test_h_route_renders_pinned_quote(client):
    """Author pinned a specific id; runtime renders that text. POST creates
    the row with an empty scaffold; PUT installs the gate_quote envelope."""
    from server.services import quotes as quotes_service

    library = quotes_service.all_quotes()
    target = library[0]

    create = client.post("/api/homeworks", json={
        "title": "Pinned-quote smoke",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
    })
    assert create.status_code == 200, create.text
    hw_id = create.json()["id"]

    update = client.put(f"/api/homeworks/{hw_id}", json={
        "content_json": {
            "meta": {"title": "Pinned-quote smoke"},
            "panels": [],
            "flashcards": [],
            "boss_questions": [],
            "memory_sprint": [],
            "gate_quote": {"mode": "pinned", "pinned_id": target["id"]},
        },
    })
    assert update.status_code == 200, update.text

    r = client.get(f"/h/{hw_id}")
    assert r.status_code == 200
    # The pinned quote's text must appear in the QUOTES array literal.
    body = r.text
    import re as _re, json as _json
    match = _re.search(r"const QUOTES\s*=\s*(\[[\s\S]*?\]);", body)
    assert match, "QUOTES array not found"
    arr = _json.loads(match.group(1))
    assert len(arr) == 1
    assert arr[0]["t"] == target["text"]
    assert arr[0]["a"] == target["author"]


def test_h_route_legacy_quotes_array_migrates_to_custom(client):
    """Old homeworks with `content_json.quotes = ['...']` still render — the
    selector treats the first non-empty entry as a custom override."""
    create = client.post("/api/homeworks", json={
        "title": "Legacy-quotes smoke",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
    })
    assert create.status_code == 200, create.text
    hw_id = create.json()["id"]

    update = client.put(f"/api/homeworks/{hw_id}", json={
        "content_json": {
            "meta": {"title": "Legacy-quotes smoke"},
            "panels": [],
            "flashcards": [],
            "boss_questions": [],
            "memory_sprint": [],
            "quotes": ["Eski iqtibos matni"],
        },
    })
    assert update.status_code == 200, update.text

    r = client.get(f"/h/{hw_id}")
    assert r.status_code == 200
    assert "Eski iqtibos matni" in r.text


def test_quotes_api_endpoint_returns_facets(client):
    """GET /api/quotes serves the searchable library used by the picker."""
    r = client.get("/api/quotes?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert "total" in body
    assert "facets" in body
    assert isinstance(body["facets"]["types"], list)
    assert isinstance(body["facets"]["origins"], list)
    assert "fact" in body["facets"]["types"] or "quote" in body["facets"]["types"]


def test_runtime_js_exposes_new_methods():
    """server/template/runtime.js must expose tutorChat, tutorHistory, bossPlan."""
    import os
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    runtime_path = os.path.join(here, "server", "template", "runtime.js")
    with open(runtime_path, "r", encoding="utf-8") as f:
        src = f.read()
    # Method definitions (function declarations).
    for name in ("tutorChat", "tutorHistory", "bossPlan"):
        assert f"function {name}(" in src, f"runtime.js missing function {name}"
        # Each must also be exposed on window.NETS_AI.
        assert name in src.split("window.NETS_AI = {")[1].split("}")[0], \
            f"{name} not exposed on window.NETS_AI"
