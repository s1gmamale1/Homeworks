from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
LIBRARY_JS = (ROOT / "frontend" / "js" / "library.js").read_text(encoding="utf-8")
LIBRARY_HTML = (ROOT / "frontend" / "library.html").read_text(encoding="utf-8")


def test_subject_tile_no_longer_uses_nested_button():
    # The tile must NOT be created as a <button>, since its expanded
    # markup contains nested <button> and <a> elements (invalid HTML).
    assert "createElement(\"div\")" in LIBRARY_JS or \
           "createElement('div')" in LIBRARY_JS, \
        "subject tile must use a neutral <div> (with role=button) instead of <button>"
    assert 'role", "button"' in LIBRARY_JS or "role', 'button'" in LIBRARY_JS, \
        "tile must declare role=button so screen readers treat it as actionable"
    assert 'tabindex", "0"' in LIBRARY_JS or "tabindex', '0'" in LIBRARY_JS, \
        "tile must be keyboard-focusable"


def test_subject_tile_keyboard_activation():
    # A <div role="button"> doesn't get Enter/Space activation for
    # free — must be wired manually.
    assert "keydown" in LIBRARY_JS, \
        "tile keyboard handler missing — Enter/Space won't activate the article"


def test_lib_clear_button_dispatches_input_event():
    # After clearing the input value, the page-level Clear button must
    # dispatch a synthetic input event (or directly remove .is-filled)
    # so the search-box X icon disappears.
    assert "dispatchEvent(new Event(\"input\"" in LIBRARY_JS or \
           "dispatchEvent(new Event('input'" in LIBRARY_JS or \
           "is-filled" in LIBRARY_JS, \
        "lib-clear-btn must dispatch input event or strip .is-filled"


def test_search_input_empty_clears_all_filters():
    # When the search input becomes empty (e.g. via inline X), language
    # and grade filters must reset too — otherwise the page-level Clear
    # button has different semantics from the inline X.
    assert "searchInput.value === \"\"" in LIBRARY_JS or \
           "searchInput.value === ''" in LIBRARY_JS, \
        "library.js search input listener must check for empty value to trigger filter reset"
