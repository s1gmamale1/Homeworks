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
    import re as _re
    r = client.get(f"/h/{created_hw['id']}")
    assert r.status_code == 200
    body = r.text.lower()
    # Reviewed/pinned CDN stylesheets with SRI hashes are permitted (added by molotovgit, PR #16,
    # approved by Sigma in PR #11 review). Any NEW external stylesheet without an integrity
    # attribute, or from an unlisted host, is still forbidden.
    _ALLOWED_CDN_HOSTS = ("cdn.jsdelivr.net",)
    matches = _re.findall(r'<link[^>]+rel\s*=\s*["\']stylesheet["\'][^>]*>', body)
    for tag in matches:
        is_external = 'href="http' in tag or "href='http" in tag
        if not is_external:
            continue
        has_sri = "integrity=" in tag
        from_allowed_host = any(host in tag for host in _ALLOWED_CDN_HOSTS)
        assert has_sri and from_allowed_host, \
            f"unexpected external stylesheet (no SRI or unlisted host) in page: {tag}"


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


def test_tutor_widget_hwid_uses_lazy_getter(client, created_hw):
    """Regression test: tutor widget state.hwId must use lazy getter, not eager init.

    Wave F2 hotfix #12 made state.hwId a property getter that reads
    window.NETS_CTX.hwId lazily. This prevents locking hwId to '' at IIFE-init time
    when NETS_CTX is still undefined.

    This test inspects the rendered HTML to ensure the getter pattern is in place
    and the eager anti-pattern (hwId: ctx.hwId || ...) is not present.
    """
    r = client.get(f"/h/{created_hw['id']}")
    assert r.status_code == 200
    body = r.text

    # Load-bearing assertion: the getter must be present in the tutor widget.
    assert "get hwId() { return currentHwId(); }" in body, \
        "tutor widget state.hwId must use lazy getter pattern"

    # Defensive: ensure eager anti-pattern was not reintroduced.
    # This pattern would lock hwId to '' at init time.
    assert "hwId: ctx.hwId" not in body, \
        "tutor widget must not use eager hwId initialization pattern"

    # Helper function that the getter relies on must be defined.
    assert "function currentHwId()" in body, \
        "tutor widget must define currentHwId() helper function"
