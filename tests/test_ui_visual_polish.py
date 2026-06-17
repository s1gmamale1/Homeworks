from pathlib import Path


ROOT = Path(__file__).parent.parent


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_search_box_uses_visual_icon_and_pill_focus_treatment():
    """Wave V.2 (PR runtime-ux-polish 2026-04-30) replaced the
    `.search-box span::before` implementation with a unified
    .search-box__icon element shared across dashboard / library /
    quote-picker. Re-pin the design so a future revert can't quietly
    bring back the heavier ::before pill."""
    css = _read("frontend/css/app.css")

    # Icon now lives on a real element (.search-box__icon) plus a
    # backwards-compatible aria-hidden <span> selector so older markup
    # still gets styled the same way.
    assert ".search-box .search-box__icon" in css
    assert '.search-box > span[aria-hidden="true"]' in css

    # Focus state: glow ring + accent border via box-shadow.
    assert ".search-box:focus-within" in css
    assert "var(--accent-glow)" in css
    # The border-radius can be either 999px (pill) or 11-12px (rounded
    # rect) — the new compact look uses ~11px. Accept either so the
    # test isn't tied to the exact radius if it's tweaked later.
    assert ("border-radius: 999px" in css) or ("border-radius: 11px" in css) or ("border-radius: 12px" in css)

    # Dark-mode override exists for the search box.
    assert '[data-theme="dark"] .search-box' in css

    # Clear-button affordance — the pill shows the × only when the
    # wrapper picks up .is-filled (toggled by frontend/js/search-box.js).
    assert ".search-box .search-box__clear" in css
    assert ".search-box.is-filled .search-box__clear" in css


def test_library_toolbar_prioritizes_search_column():
    css = _read("frontend/css/library.css")

    # Apple-redesign keeps the same 3-column toolbar grid (lang chips |
    # search | clear button) but the mobile breakpoint moved 640 -> 650
    # to align with the rest of the redesign's responsive cutoffs.
    assert "grid-template-columns: auto minmax(280px, 1fr) auto" in css
    assert ".lib-search" in css
    assert "justify-self: stretch" in css
    assert "@media (max-width: 650px)" in css


def test_tutor_chat_has_polished_panel_and_assistant_identity():
    html = (_read("server/template/js/perfect_homework.js") + "\n" +
            _read("server/template/static/css/perfect_homework.css"))

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
