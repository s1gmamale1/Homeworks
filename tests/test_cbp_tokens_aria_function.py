"""Function tier — end-to-end: GET /h/{id} returns HTML with the
substituted `_tokens.css?v=<sha>` link."""
from __future__ import annotations

import re


def _post_homework(client):
    return client.post("/api/homeworks", json={
        "title": "Tokens function test",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
        "family": "aniq-fanlar",
        "content_json": {
            "meta": {"title": "T", "subject_display": "Math", "section": "1"},
            "panels": [],
            "flashcards": [],
            "memory_sprint": [],
            "boss_questions": [],
        },
    })


def test_rendered_homework_page_contains_tokens_link(client):
    resp = _post_homework(client)
    assert resp.status_code == 200
    hw_id = resp.json()["id"]
    page = client.get(f"/h/{hw_id}")
    assert page.status_code == 200
    assert "/css/_tokens.css" in page.text


def test_rendered_homework_page_link_has_no_unresolved_placeholder(client):
    """The `__VERSION__` substitution happens only on static-HTML pages
    (`/`, `/builder.html`). The injector path used by `/h/{id}` does NOT
    run `_render_html_with_version`, so no query-string cache-bust
    placeholder may remain in the rendered output (the link would 404 if
    `__VERSION__` showed up in a real URL request — actually it wouldn't,
    static files match without the query, but the placeholder would
    fingerprint as broken cache control). For now we just assert the
    placeholder is absent from the link."""
    resp = _post_homework(client)
    hw_id = resp.json()["id"]
    page = client.get(f"/h/{hw_id}").text
    # Find the _tokens.css link
    match = re.search(r'/css/_tokens\.css([?][^"\s>]+)?', page)
    assert match, "Expected /css/_tokens.css link in rendered HTML"
    full_link = match.group(0)
    assert "__VERSION__" not in full_link, (
        f"Unresolved __VERSION__ placeholder in rendered link: {full_link}"
    )


def test_rendered_homework_tokens_link_precedes_katex(client):
    """Same ordering invariant as the sanity tier, end-to-end."""
    resp = _post_homework(client)
    hw_id = resp.json()["id"]
    page = client.get(f"/h/{hw_id}").text
    tokens_pos = page.find("/css/_tokens.css")
    katex_pos = page.find("katex.min.css")
    assert 0 < tokens_pos < katex_pos
