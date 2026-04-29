from pathlib import Path


ROOT = Path(__file__).parent.parent


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_search_box_uses_visual_icon_and_pill_focus_treatment():
    css = _read("frontend/css/app.css")

    assert ".search-box span::before" in css
    assert ".search-box span::after" in css
    assert "border-radius: 999px" in css
    assert "box-shadow: 0 0 0 3px var(--accent-glow), var(--shadow-mid)" in css
    assert "--family-aniq: #0066CC" in css


def test_library_toolbar_prioritizes_search_column():
    css = _read("frontend/css/library.css")

    assert "grid-template-columns: auto minmax(280px, 1fr) auto" in css
    assert ".lib-search" in css
    assert "justify-self: stretch" in css
    assert "@media (max-width: 640px)" in css


def test_tutor_chat_has_polished_panel_and_assistant_identity():
    html = _read("server/template/perfect_homework.html")

    assert "width: 390px" in html
    assert "height: 540px" in html
    assert ".nets-tutor-msg.assistant::before" in html
    assert 'content: "AI"' in html
    assert "padding-left: 42px" in html
    assert "border-radius: 22px" in html
    assert "[data-theme=\"dark\"] .nets-tutor-msg.assistant::before" in html


def test_homework_card_more_actions_button_has_solid_surface():
    css = _read("frontend/css/app.css")

    assert ".card-menu .js-menu-toggle" in css
    assert "background: var(--surface-elevated)" in css
    assert ".card-menu.is-open .js-menu-toggle" in css
    assert "background: var(--accent)" in css
    assert "color: #fff" in css
