"""Integration tier — rendered /h/{id} contains the full CBP engine.

NOTE on cross-PR dependency: like PR #5, the CBP runtime needs PR #1's
`const CBP = {...}` injection to actually receive a payload. On the
`cbpr-06-cbp-runtime` branch in isolation, the engine code is present
but CBP is undefined. We verify the engine SHIPS — full payload
end-to-end is covered when PR #1 and PR #5 + #6 all land on cbpr.
"""
from __future__ import annotations


def _v1_payload():
    return {
        "title": "PR6 integration",
        "subject": "biology",
        "grade": 7,
        "mode": "hard",
        "family": "tabiiy-fanlar",
        "content_json": {
            "meta": {"title": "t", "subject_display": "Biology", "section": "1"},
            "panels": [],
            "flashcards": [],
            "memory_sprint": [],
            "boss_questions": [],
        },
    }


def test_rendered_page_contains_screen_cbp(client):
    resp = client.post("/api/homeworks", json=_v1_payload())
    hw_id = resp.json()["id"]
    page = client.get(f"/h/{hw_id}").text
    assert 'id="screen-cbp"' in page
    assert 'id="screen-unlock"' in page


def test_rendered_page_has_all_engine_functions(client):
    resp = client.post("/api/homeworks", json=_v1_payload())
    hw_id = resp.json()["id"]
    page = client.get(f"/h/{hw_id}").text
    for fn in ("function cbpStart(",
               "function cbpRenderCheckpoint(",
               "function cbpAnswer(",
               "function cbpFinalize("):
        assert fn in page, f"engine function missing in rendered output: {fn}"


def test_rendered_page_has_substage_markers(client):
    resp = client.post("/api/homeworks", json=_v1_payload())
    hw_id = resp.json()["id"]
    page = client.get(f"/h/{hw_id}").text
    for marker in ('data-sub="setup"', 'data-sub="ckp"', 'data-sub="lb"',
                   'data-sub="sim"', 'data-sub="fb"'):
        assert marker in page


def test_rendered_page_has_unlock_screen(client):
    resp = client.post("/api/homeworks", json=_v1_payload())
    hw_id = resp.json()["id"]
    page = client.get(f"/h/{hw_id}").text
    assert 'id="unlock-enter-btn"' in page
