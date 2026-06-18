"""
Regression test for WCAG 2A select-name violation on dashboard selects.

Axe flagged 3 unlabeled <select> elements on /index.html (PR #106 deploy QA).
The same pattern exists in the create-modal (6 selects total).

Each <select> must have an accessible name via one of:
  - aria-label attribute (preferred, static fallback for pre-JS load)
  - aria-labelledby pointing to an existing element
  - wrapping <label> element with a `for` attribute matching the select's id

This test parses the rendered HTML with regex to detect the violation pattern:
a <select> that lacks all three accessible-name mechanisms.  Using regex rather
than a full DOM parser keeps the dependency footprint zero and is precise enough
for the bounded markup we control (a single well-formed HTML file).
"""
import re
import pytest


# IDs of every <select> that must carry an accessible name on the dashboard.
EXPECTED_SELECT_IDS = [
    "subject-filter",
    "status-filter",
    "mode-filter",
    "homework-subject",
    "homework-grade",
    # NOTE: "homework-mode" (the create-modal Easy/Hard select) was intentionally
    # removed — v2 homeworks don't ask difficulty at create time.
]

# Minimal pattern: <select ... id="X" ... > — captures full attribute string
_SELECT_RE = re.compile(r"<select\b([^>]*)>", re.IGNORECASE)
_ID_RE = re.compile(r'\bid="([^"]+)"')
_ARIA_LABEL_RE = re.compile(r'\baria-label="([^"]+)"')
_ARIA_LABELLEDBY_RE = re.compile(r'\baria-labelledby="([^"]+)"')


def _parse_selects(html: str) -> dict[str, dict]:
    """Return a mapping of select id -> attrs dict for every <select> in html."""
    result = {}
    for m in _SELECT_RE.finditer(html):
        attrs = m.group(1)
        id_m = _ID_RE.search(attrs)
        if not id_m:
            continue
        sel_id = id_m.group(1)
        result[sel_id] = {
            "attrs": attrs,
            "aria_label": _ARIA_LABEL_RE.search(attrs),
            "aria_labelledby": _ARIA_LABELLEDBY_RE.search(attrs),
        }
    return result


@pytest.mark.parametrize("select_id", EXPECTED_SELECT_IDS)
def test_select_has_accessible_name(client, select_id):
    """Every dashboard <select> must carry aria-label or aria-labelledby."""
    r = client.get("/index.html")
    assert r.status_code == 200

    selects = _parse_selects(r.text)
    assert select_id in selects, (
        f"<select id='{select_id}'> not found in / — was it removed or renamed?"
    )

    sel = selects[select_id]
    has_accessible_name = bool(sel["aria_label"] or sel["aria_labelledby"])
    assert has_accessible_name, (
        f"<select id='{select_id}'> has no accessible name.\n"
        f"  Add aria-label=\"...\" and data-i18n-aria-label=\"common.<key>\" to the element.\n"
        f"  Current attrs: {sel['attrs'].strip()}"
    )


def test_all_expected_selects_present(client):
    """Sanity guard: all 6 expected select IDs exist on the page."""
    r = client.get("/index.html")
    assert r.status_code == 200

    selects = _parse_selects(r.text)
    missing = [s for s in EXPECTED_SELECT_IDS if s not in selects]
    assert not missing, (
        f"Expected select IDs missing from /: {missing}\n"
        "Update EXPECTED_SELECT_IDS if the markup changed intentionally."
    )
