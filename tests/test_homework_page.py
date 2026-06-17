"""Smoke tests for the permanent share URL + builder preview endpoints
exposed by `server/routes/homework_page.py`. Covers the three response branches:

  - 200: existing, non-trashed homework returns rendered HTML with the AI
         bootstrap injected (`<script src="/static/runtime/runtime.js">`).
  - 404: missing id returns a browser-friendly HTML 404 page on `/h/{id}`
         and a JSON-style 404 on `/api/homeworks/{id}/preview`.
  - 409: trashed homework returns 409 (HTML body on `/h/{id}`,
         JSON detail on `/api/homeworks/{id}/preview`).
"""

from pathlib import Path

import pytest

_TUTOR_JS = Path(__file__).resolve().parent.parent / "server" / "template" / "static" / "js" / "tutor.js"


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


# ──────────────────────────────────────────────────────────────────
# Phase 0-A — gate quote (curated library + skip lock)
# ──────────────────────────────────────────────────────────────────


def test_h_route_renders_single_gate_quote(client, created_hw):
    """Runtime ships a three-slot sequence; opening gate is quote-only."""
    r = client.get(f"/h/{created_hw['id']}")
    assert r.status_code == 200
    body = r.text
    # Single quote injected — array literal contains exactly one object.
    import json as _json, re as _re
    match = _re.search(r"const QUOTES\s*=\s*(\[[\s\S]*?\]);", body)
    assert match, "QUOTES array not found in rendered HTML"
    arr = _json.loads(match.group(1))
    # Only one object in the array (one closing brace immediately before the closing bracket).
    assert len(arr) == 3
    assert arr[0]["type"] == "quote"
    assert arr[2]["type"] == "fact"
    # Author chip CSS class is in the template.
    assert "quote-author-chip" in body
    # Skip lock ring CSS is in the template.
    assert "skip-lock-ring" in body
    assert "Yaxshi uka" not in body
    assert "keep poing" not in body
    assert 'id="break-kicker"' in body
    assert 'id="break-text"' in body


def test_h_route_renders_pinned_quote(client):
    """Author pinned a specific id; runtime renders that text. POST creates
    the row with an empty scaffold; PUT installs the gate_quote envelope."""
    from server.services import quotes as quotes_service

    library = quotes_service.all_quotes()
    target = next(q for q in library if q.get("type") == "quote")

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
    assert len(arr) == 3
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


def test_h_route_legacy_demo_quote_is_ignored(client):
    """Old demo break text should not survive through legacy quotes."""
    create = client.post("/api/homeworks", json={
        "title": "Legacy-demo cleanup smoke",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
    })
    assert create.status_code == 200, create.text
    hw_id = create.json()["id"]

    update = client.put(f"/api/homeworks/{hw_id}", json={
        "content_json": {
            "meta": {"title": "Legacy-demo cleanup smoke"},
            "panels": [],
            "flashcards": [],
            "boss_questions": [],
            "memory_sprint": [],
            "quotes": ["Yaxshi uka, keep poing"],
        },
    })
    assert update.status_code == 200, update.text

    r = client.get(f"/h/{hw_id}")
    assert r.status_code == 200
    assert "Yaxshi uka" not in r.text
    assert "keep poing" not in r.text


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
    body = r.text + "\n" + _TUTOR_JS.read_text(encoding="utf-8")

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


# ──────────────────────────────────────────────────────────────────
# Wave J — visual cosmetics
# ──────────────────────────────────────────────────────────────────

def test_tutor_no_local_theme_toggle(client, created_hw):
    """Post-2026-04-29 cleanup: the tutor must NOT ship its own
    light/dark toggle. The page-level navbar toggle
    (frontend/js/theme.js) is the single source of truth — the
    runtime player consumes the saved value via the `storage`
    listener in `applyStoredTheme()`. A user-visible per-tutor
    toggle splits the mental model and the audit flagged it.

    This test inverts the prior `test_theme_toggle_button_present`
    so a future "let's add a chat-side toggle" PR has to come back
    and rewrite the rule rather than silently regress."""
    r = client.get(f"/h/{created_hw['id']}")
    assert r.status_code == 200
    body = r.text + "\n" + _TUTOR_JS.read_text(encoding="utf-8")
    assert 'id="nets-tutor-theme-toggle"' not in body, (
        "tutor panel must not ship a per-chat theme toggle — the "
        "navbar toggle drives `data-theme` for the whole player"
    )
    # The storage-sync hook that lets the navbar toggle reach the
    # runtime player MUST still be in place.
    assert "applyStoredTheme" in body, (
        "tutor must keep the read-only theme mirror so a navbar "
        "toggle in another tab/document still updates the runtime"
    )
    assert "addEventListener('storage'" in body or "addEventListener(\"storage\"" in body, (
        "tutor must still listen for the cross-document `storage` "
        "event — that's how the navbar toggle reaches the player"
    )


def test_tutor_avatar_present(client, created_hw):
    """Wave J F2: rendered HTML must contain the persona avatar element."""
    r = client.get(f"/h/{created_hw['id']}")
    assert r.status_code == 200
    body = r.text
    assert 'id="nets-tutor-avatar"' in body, \
        "Wave J tutor avatar (id=nets-tutor-avatar) missing from rendered HTML"
    # Avatar must appear inside the panel header — before the phase badge.
    avatar_pos = body.find('id="nets-tutor-avatar"')
    badge_pos  = body.find('id="nets-tutor-phase-badge"')
    assert avatar_pos != -1 and badge_pos != -1
    assert avatar_pos < badge_pos, "avatar must appear before the phase badge in the header"


# ──────────────────────────────────────────────────────────────────
# Wave I3 — runtime template i18n (RUNTIME_LABELS) + lang-aware
# friendly 404/409 pages.
# ──────────────────────────────────────────────────────────────────


def test_runtime_template_has_runtime_labels(client, created_hw):
    """Wave I3: rendered template must declare a top-level RUNTIME_LABELS dict
    with at least the canonical reading.next_question key."""
    r = client.get(f"/h/{created_hw['id']}")
    assert r.status_code == 200
    body = r.text
    assert "RUNTIME_LABELS = {" in body, "RUNTIME_LABELS dict missing from template"
    assert "'reading.next_question'" in body, \
        "RUNTIME_LABELS must contain canonical 'reading.next_question' key"
    # All three language blocks must be present.
    for lang_block in ("uz: {", "ru: {", "en: {"):
        assert lang_block in body, f"RUNTIME_LABELS missing language block: {lang_block}"
    # Helper functions are exposed for global use.
    assert "function RT(" in body
    assert "window.RT = RT" in body


def test_runtime_no_hardcoded_keyingi_savol_outside_labels(client, created_hw):
    """Wave I3 regression rule: 'Keyingi savol' must appear ONLY inside the
    RUNTIME_LABELS.uz block — never bare in JS code outside it.

    This prevents future authors from re-introducing the hardcoded string by
    accident. The rule scans the full rendered page; any match must be within
    a small radius of 'RUNTIME_LABELS' or the per-language opener so we know
    it's the dict entry, not stray code.
    """
    r = client.get(f"/h/{created_hw['id']}")
    assert r.status_code == 200
    body = r.text
    needle = "Keyingi savol"
    # We allow the literal in two places:
    #   1. Inside RUNTIME_LABELS (uz: { ... 'reading.next_question': 'Keyingi savol', ... })
    #   2. Inside the comment block immediately above RUNTIME_LABELS (placeholder text).
    # Find the byte ranges for the RUNTIME_LABELS literal.
    rl_start = body.find("RUNTIME_LABELS = {")
    assert rl_start >= 0, "RUNTIME_LABELS not declared"
    # Find matching closing brace by walking depth — string-naive but adequate
    # for our hand-written dict (we know it has no nested } in keys).
    depth = 0
    rl_end = rl_start
    started = False
    for i in range(rl_start, len(body)):
        ch = body[i]
        if ch == "{":
            depth += 1
            started = True
        elif ch == "}":
            depth -= 1
            if started and depth == 0:
                rl_end = i + 1
                break
    assert rl_end > rl_start, "could not find end of RUNTIME_LABELS"

    pos = 0
    while True:
        idx = body.find(needle, pos)
        if idx < 0:
            break
        # Must be inside the RUNTIME_LABELS literal — anything else is a
        # leftover hardcoded string and must be replaced with RT('reading.next_question').
        assert rl_start <= idx <= rl_end, (
            f"'Keyingi savol' found outside RUNTIME_LABELS at offset {idx}; "
            f"replace with RT('reading.next_question'). Surrounding text: "
            f"{body[max(0, idx - 60):idx + 80]!r}"
        )
        pos = idx + len(needle)


def test_runtime_button_text_same_label_restores_visibility():
    """If a transition hides the button text and then reuses the same label,
    setBtnText must still clear the inline hidden state. Otherwise buttons
    like Keyingi can render as a blue pill with invisible text."""
    from pathlib import Path
    import re

    html = (Path("server/template/js/perfect_homework.js").read_text(encoding="utf-8") + "\n" +
            Path("server/template/static/css/perfect_homework.css").read_text(encoding="utf-8"))
    match = re.search(
        r"function setBtnText\(text\)\s*\{(?P<body>[\s\S]*?)\n\s*\}\n\n\s*function skipCurrentPhase",
        html,
    )
    assert match, "setBtnText function not found"
    body = match.group("body")

    assert "if (btnText.innerText === text)" in body
    same_label_branch = body.split("if (btnText.innerText === text)", 1)[1].split("btnText.classList.add('fade-out')", 1)[0]
    assert "btnText.classList.remove('fade-out', 'fade-in')" in same_label_branch
    assert "btnText.style.opacity = '1'" in same_label_branch


def test_runtime_template_lang_attr_matches_homework_lang(client):
    """Wave I3: <html lang="..."> must reflect the homework's resolved language
    (not the hardcoded 'uz' default).

    We set the language via content_json.meta.lang (the in-flight resolution
    path used by render_homework). The DB.language column is the long-term
    Wave I1 source, but this test exercises the runtime side regardless of
    which lane wires the column.
    """
    create = client.post("/api/homeworks", json={
        "title": "Russian homework",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
    })
    assert create.status_code == 200, create.text
    hw_id = create.json()["id"]

    update = client.put(f"/api/homeworks/{hw_id}", json={
        "content_json": {
            "meta": {"title": "Russian homework", "lang": "ru"},
            "panels": [],
            "flashcards": [],
            "boss_questions": [],
            "memory_sprint": [],
        },
    })
    assert update.status_code == 200, update.text

    r = client.get(f"/h/{hw_id}")
    assert r.status_code == 200
    assert '<html lang="ru">' in r.text, \
        "rendered template must reflect content_json.meta.lang='ru'"


def test_friendly_404_page_default_uz(client):
    """Wave I3: GET /h/<bogus> with no ?lang= → defaults to Uzbek body."""
    r = client.get("/h/HW-99999999-999")
    assert r.status_code == 404
    assert "Bu topshiriq mavjud emas" in r.text
    assert '<html lang="uz">' in r.text


def test_friendly_404_page_lang_param_ru(client):
    """Wave I3: ?lang=ru on missing homework → Russian friendly page."""
    r = client.get("/h/HW-99999999-999?lang=ru")
    assert r.status_code == 404
    assert "Это задание не существует" in r.text
    assert '<html lang="ru">' in r.text


def test_friendly_404_page_lang_param_en(client):
    """Wave I3: ?lang=en on missing homework → English friendly page."""
    r = client.get("/h/HW-99999999-999?lang=en")
    assert r.status_code == 404
    assert "This homework does not exist" in r.text
    assert '<html lang="en">' in r.text


def test_friendly_404_page_lang_param_garbage_falls_back_to_uz(client):
    """Wave I3 defensive: an unknown ?lang=zz must NOT crash; falls back to uz."""
    r = client.get("/h/HW-99999999-999?lang=zz")
    assert r.status_code == 404
    assert "Bu topshiriq mavjud emas" in r.text


def test_friendly_409_page_uses_homework_lang(client):
    """Wave I3: trashed homework's friendly 409 reads the homework's own
    DB language column (not the request lang).

    Sets the DB column directly via aiosqlite since HomeworkCreate doesn't
    yet accept `language` (Wave I1 owns adding the field; we read it).
    """
    import aiosqlite
    import asyncio
    from server.db import connect

    create = client.post("/api/homeworks", json={
        "title": "Russian, trashed",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
    })
    assert create.status_code == 200, create.text
    hw_id = create.json()["id"]

    # Stamp language='ru' directly on the row — simulates what Wave I1's
    # builder UI will do once the field is exposed.
    async def _set_language():
        db = await connect()
        try:
            await db.execute(
                "UPDATE homeworks SET language = ? WHERE id = ?",
                ("ru", hw_id),
            )
            await db.commit()
        finally:
            await db.close()
    asyncio.run(_set_language())

    delete = client.delete(f"/api/homeworks/{hw_id}")
    assert delete.status_code in (200, 204), delete.text

    r = client.get(f"/h/{hw_id}")
    assert r.status_code == 409
    assert "Это задание удалено" in r.text
    assert '<html lang="ru">' in r.text


# Wave F4 — Stuck? Ask tutor CTA
# ──────────────────────────────────────────────────────────────────

def test_tutor_cta_button_present_in_template(client, created_hw):
    """Wave F4: rendered homework page must include the Stuck? Ask tutor CTA button."""
    r = client.get(f"/h/{created_hw['id']}")
    assert r.status_code == 200
    body = r.text
    # CTA button element must be present.
    assert 'id="nets-tutor-cta"' in body, \
        "Wave F4 CTA button (id=nets-tutor-cta) missing from rendered HTML"
    # At least one of the three i18n labels must appear verbatim.
    i18n_labels = (
        'Tushunmadingmi? Tyutorga ayt',
        'Stuck? Ask the tutor →',
        'Не понял? Спроси у тьютора →',
    )
    assert any(label in body for label in i18n_labels), \
        f"Wave F4 CTA: none of the expected i18n labels found. Checked: {i18n_labels}"
    # CTA must appear before the tutor widget in the DOM.
    cta_pos    = body.find('id="nets-tutor-cta"')
    widget_pos = body.find('id="nets-ai-tutor"')
    assert cta_pos != -1 and widget_pos != -1
    assert cta_pos < widget_pos, "CTA button must appear before the tutor widget in the HTML"
