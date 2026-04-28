"""
Wave F4 — deterministic slur-filter tests.

Covers:
  1. _SLURS list is non-empty after module load (sanity)
  2. detect_slurs finds a known slur ("lox") in a message
  3. detect_slurs returns [] for a clean message
  4. detect_slurs respects word boundaries (no false positive inside longer word)
  5. callout_for returns uz / ru / en variants correctly
  6. callout_for returns None for a clean message
  7. POST /api/ai/tutor/chat with a known-slur message — response starts with callout

Run:
    python -m pytest tests/test_slur_filter.py -v
"""

from __future__ import annotations

from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# 1. _SLURS list loads at import
# ---------------------------------------------------------------------------


def test_detect_slurs_loads_list():
    from server.services.slur_filter import _SLURS
    assert len(_SLURS) > 0, "_SLURS should be non-empty after parsing Naughty_words.md"


# ---------------------------------------------------------------------------
# 2. detect_slurs finds a known slur
# ---------------------------------------------------------------------------


def test_detect_slurs_finds_known_slur():
    from server.services.slur_filter import detect_slurs
    # "lox" and "ahmoq" appear explicitly in the word list
    found = detect_slurs("U lox, javobni bilmayapti.")
    assert "lox" in found, f"expected 'lox' in {found}"

    found2 = detect_slurs("Sen ahmoq ekansan!")
    assert "ahmoq" in found2, f"expected 'ahmoq' in {found2}"


# ---------------------------------------------------------------------------
# 3. detect_slurs returns [] for a clean message
# ---------------------------------------------------------------------------


def test_detect_slurs_no_false_positive_on_clean_message():
    from server.services.slur_filter import detect_slurs
    assert detect_slurs("Hello, how are you?") == []
    assert detect_slurs("Iltimos, 5-masalani tushuntirib bering.") == []


# ---------------------------------------------------------------------------
# 4. word-boundary check — partial match must NOT fire
# ---------------------------------------------------------------------------


def test_detect_slurs_word_boundary():
    """'tormoz' is in the list; 'tormozlash' contains it but as a prefix —
    make sure the regex doesn't fire on the embedded occurrence."""
    from server.services.slur_filter import detect_slurs
    # Direct match should fire
    assert "tormoz" in detect_slurs("U tormoz!")
    # As a prefix of a longer word it must NOT fire (word-boundary guard)
    assert detect_slurs("tormozlash jarayoni") == [], (
        "word-boundary failed: 'tormoz' inside 'tormozlash' should not match"
    )


# ---------------------------------------------------------------------------
# 5. callout_for lang variants
# ---------------------------------------------------------------------------


def test_callout_for_uses_lang():
    from server.services.slur_filter import callout_for
    msg = "U lox!"
    uz = callout_for(msg, lang="uz")
    ru = callout_for(msg, lang="ru")
    en = callout_for(msg, lang="en")
    assert uz and "darsdamiz" in uz, f"uz callout unexpected: {uz}"
    assert ru and "уроке" in ru, f"ru callout unexpected: {ru}"
    assert en and "class" in en, f"en callout unexpected: {en}"
    # All three must differ
    assert len({uz, ru, en}) == 3


# ---------------------------------------------------------------------------
# 6. callout_for returns None for clean message
# ---------------------------------------------------------------------------


def test_callout_for_no_slur_returns_none():
    from server.services.slur_filter import callout_for
    assert callout_for("How do I solve this equation?") is None
    assert callout_for("") is None


# ---------------------------------------------------------------------------
# 7. route prepends callout for slur-containing message
# ---------------------------------------------------------------------------


@patch("server.services.gemini.generate")
def test_route_prepends_callout(mock_generate, client):
    """POST /api/ai/tutor/chat with 'U lox!' — mock LLM returns 'X'; assert
    response body starts with the callout prefix."""
    mock_generate.return_value = "X"

    # Create a minimal homework so hw lookup doesn't crash
    create_resp = client.post(
        "/api/homeworks",
        json={
            "title": "Slur filter test HW",
            "subject": "math-algebra",
            "grade": 8,
            "mode": "hard",
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    hw_id = create_resp.json()["id"]

    payload = {
        "session_id": "sess-slur-test",
        "hw_id": hw_id,
        "phase": "preview",
        "message": "U lox, javobni bilmayapti.",
    }
    resp = client.post("/api/ai/tutor/chat", json=payload)
    assert resp.status_code == 200, resp.text
    response_text = resp.json()["response"]
    # Callout must be prepended; "darsdamiz" is the uz-language marker
    assert "darsdamiz" in response_text, (
        f"Expected callout prefix in response, got: {response_text!r}"
    )
    # LLM stub output must still be present
    assert response_text.endswith("X"), (
        f"LLM response 'X' should follow callout, got: {response_text!r}"
    )
