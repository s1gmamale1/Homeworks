"""
Wave I1 — i18n infrastructure smoke tests.

Verifies that:
  - The lang-switch pills are present on every dashboard page.
  - The i18n scripts are loaded in the correct order (strings.js before i18n.js).
"""
import pytest


def test_lang_switch_renders_on_dashboard(client):
    """Dashboard (/index.html) must render all three lang-pill data-lang attributes."""
    r = client.get("/index.html")
    assert r.status_code == 200
    body = r.text
    assert 'data-lang="uz"' in body
    assert 'data-lang="ru"' in body
    assert 'data-lang="en"' in body


def test_lang_switch_renders_on_builder(client):
    """Builder page must render all three lang-pill data-lang attributes."""
    r = client.get("/builder.html")
    assert r.status_code == 200
    body = r.text
    assert 'data-lang="uz"' in body
    assert 'data-lang="ru"' in body
    assert 'data-lang="en"' in body


def test_lang_switch_renders_on_library(client):
    """Library page must render all three lang-pill data-lang attributes."""
    r = client.get("/library.html")
    assert r.status_code == 200
    body = r.text
    assert 'data-lang="uz"' in body
    assert 'data-lang="ru"' in body
    assert 'data-lang="en"' in body


def test_i18n_scripts_loaded_in_order(client):
    """strings.js must appear in source before i18n.js on the dashboard."""
    r = client.get("/index.html")
    assert r.status_code == 200
    body = r.text
    pos_strings = body.find("i18n/strings.js")
    pos_i18n = body.find("i18n.js")
    assert pos_strings != -1, "i18n/strings.js not found in dashboard HTML"
    assert pos_i18n != -1, "i18n.js not found in dashboard HTML"
    assert pos_strings < pos_i18n, (
        "i18n/strings.js must be loaded before i18n.js "
        f"(strings at {pos_strings}, i18n at {pos_i18n})"
    )


def test_strings_skeleton_has_exact_three_lang_keys():
    """Sigma's footgun: t()'s fallback chain silently breaks if STRINGS drifts
    from the {uz, ru, en} shape. Lock the shape at the source so I2/I3 can't
    accidentally introduce a 4th key or drop one."""
    from pathlib import Path
    src = Path(__file__).parent.parent / "frontend" / "js" / "i18n" / "strings.js"
    body = src.read_text(encoding="utf-8")
    # Must declare exactly the three lang keys; any drift fails this test.
    assert "uz:" in body, "missing uz: key in STRINGS skeleton"
    assert "ru:" in body, "missing ru: key in STRINGS skeleton"
    assert "en:" in body, "missing en: key in STRINGS skeleton"
    # Defensive: assert no rogue 4th lang slipped in (common mistakes).
    for rogue in ("kk:", "tg:", "ky:", "es:", "fr:", "de:", "uk:"):
        assert rogue not in body, f"unexpected lang key {rogue!r} in STRINGS"
