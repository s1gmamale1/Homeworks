from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_library_subject_tile_uses_aria_allowed_host():
    js = _read("frontend/js/library.js")

    assert 'document.createElement("div")' in js
    assert 'document.createElement("article")' not in js
    assert 'tile.setAttribute("role", "button")' in js
    assert 'tile.setAttribute("tabindex", "0")' in js


def test_builder_has_no_nested_aside_landmarks():
    html = _read("frontend/builder.html")

    assert '<aside class="sidebar' not in html
    assert '<aside class="preview-panel' not in html
    assert '<section class="sidebar glass-card" aria-label="Homework phases">' in html
    assert '<section class="preview-panel" id="preview-panel"' in html


def test_dashboard_nav_contrast_tokens_are_darker():
    css = _read("frontend/css/dashboard.css")

    assert "body[data-page=\"dashboard\"] .topbar-nav .btn-ghost" in css
    assert "color: var(--dash-zinc-700);" in css
    assert "[data-theme=\"dark\"] body[data-page=\"dashboard\"] .topbar-nav .btn-ghost" in css
    assert "color: #dbeafe;" in css


def test_library_pills_use_readable_inactive_text():
    css = _read("frontend/css/library.css")

    assert ".lib-chip {" in css
    assert "color: var(--text);" in css
    assert "[data-theme=\"dark\"] .lib-chip" in css
    assert "color: #e5e7eb;" in css
