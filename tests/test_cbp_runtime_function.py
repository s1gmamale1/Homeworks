"""Function tier — end-to-end engine deliverables in rendered output."""
from __future__ import annotations


def _payload():
    return {
        "title": "PR6 function",
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


def test_rendered_page_carries_full_engine(client):
    """A single GET /h/{id} should expose all the engine pieces: the
    CBP screen, the unlock screen, all 5 substages, the gate logic
    constant, and the Uzbek terminology."""
    resp = client.post("/api/homeworks", json=_payload())
    hw_id = resp.json()["id"]
    page = client.get(f"/h/{hw_id}").text

    # Screens
    assert 'id="screen-cbp"' in page
    assert 'id="screen-unlock"' in page

    # All 5 substages
    for marker in ('data-sub="setup"', 'data-sub="ckp"', 'data-sub="lb"',
                   'data-sub="sim"', 'data-sub="fb"'):
        assert marker in page

    # Engine functions
    for fn in ("cbpStart", "cbpRenderCheckpoint", "cbpAnswer",
               "cbpFinalize", "cbpMaybeOpenUnlockGate"):
        assert "function " + fn + "(" in page

    # Gate threshold
    assert "passed >= 2" in page

    # Uzbek pass/retry labels (Forbid #20)
    assert "Topshirildi" in page
    assert "Qayta urinish kerak" in page


def test_rendered_page_does_not_break_legacy_homework_rendering(client):
    """Legacy homeworks still render through the legacy stage machine.
    PR #6 must not break that."""
    resp = client.post("/api/homeworks", json=_payload())
    hw_id = resp.json()["id"]
    page = client.get(f"/h/{hw_id}").text
    # Legacy setStage and screens are still present
    assert "function setStage(n) {" in page
    assert 'id="screen-1"' in page
    assert 'id="screen-2"' in page


def test_retake_chip_text_renders_in_uzbek_and_english(client):
    """For Flow v2 forbid #19 — the regenerated-variant chip must be
    visible to both sighted and screen-reader users."""
    resp = client.post("/api/homeworks", json=_payload())
    hw_id = resp.json()["id"]
    page = client.get(f"/h/{hw_id}").text
    assert "Qayta ishlangan" in page  # Uzbek
    assert "Regenerated" in page       # English
