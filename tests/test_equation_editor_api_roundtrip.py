"""Equation Editor — API round-trip regression.

LaTeX entered via the MathLive editor is persisted as plain `$LaTeX$`
(or `$$LaTeX$$` for display-mode templates) inside `block.text`. This
suite pins that the LaTeX survives byte-for-byte through every API path
the builder uses, plus that it appears in the runtime / iframe-preview
HTML so the runtime KaTeX bootstrap can render it.

Why this matters:
  - Invariant 1 (frozen content_json) — proves no API path normalizes,
    re-encodes, or HTML-escapes math content into a different string.
  - Invariant 4 (tutor answer-leak) — math answers must round-trip
    byte-for-byte so deterministic grading sees the same canonical form
    the student saw.
  - Defends against a regression where someone enables HTML-escape on
    block.text (would mangle `\\frac`, `<`, `&`).
  - Smoke that the new picker scripts ARE served by the static mount —
    a 404 here would silently break the toolbar.
"""

from __future__ import annotations

import pytest


# Each fixture is the LaTeX MathLive emits for a specific picker template.
# We pick one per category to cover the breadth of escaping concerns.
EQUATION_FIXTURES = [
    ("alpha-symbol",         "$\\alpha$"),
    ("less-or-equal",        "$\\leq$"),
    ("fraction",             "$\\frac{a}{b}$"),
    ("sqrt-with-index",      "$\\sqrt[3]{x}$"),
    ("integral-with-limits", "$\\int_{0}^{1} x^2 \\, dx$"),
    ("display-pmatrix",      "$$\\begin{pmatrix} 1 & 0 \\\\ 0 & 1 \\end{pmatrix}$$"),
    ("display-cases",        "$$\\begin{cases} x, & x > 0 \\\\ -x, & x \\le 0 \\end{cases}$$"),
    ("uzbek-mixed",          "Yuza: $S = \\pi r^2$ formula bo'yicha hisoblanadi."),
    ("ampersand-in-math",    "$a = b \\& c$"),
    ("nested-frac",          "$\\frac{1}{1 + \\frac{1}{x}}$"),
]


def _payload_with_equation(latex: str) -> dict:
    return {
        "title": "Equation roundtrip",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
        "family": "aniq-fanlar",
        "content_json": {
            "meta": {"title": "Equation roundtrip", "subject_display": "Algebra"},
            "panels": [
                {
                    "id": 1,
                    "title": "PANEL 1",
                    "pages": [{"blocks": [{"type": "p", "text": latex}]}],
                }
            ],
            "flashcards": [],
            "boss_questions": [],
            "memory_sprint": [],
        },
    }


@pytest.mark.parametrize("label,latex", EQUATION_FIXTURES)
def test_post_then_get_preserves_latex(client, label, latex):
    create = client.post("/api/homeworks", json=_payload_with_equation(latex))
    assert create.status_code == 200, create.text
    hw_id = create.json()["id"]
    fetch = client.get(f"/api/homeworks/{hw_id}")
    text_back = fetch.json()["content_json"]["panels"][0]["pages"][0]["blocks"][0]["text"]
    assert text_back == latex, (
        f"{label}: LaTeX mutated POST→GET\n  sent: {latex!r}\n  back: {text_back!r}"
    )


@pytest.mark.parametrize("label,latex", EQUATION_FIXTURES)
def test_h_route_carries_latex(client, label, latex):
    """The /h/{id} runtime route must include the LaTeX (in either raw
    or JSON-escaped form, depending on injector path) so KaTeX renders it."""
    create = client.post("/api/homeworks", json=_payload_with_equation(latex))
    hw_id = create.json()["id"]
    rendered = client.get(f"/h/{hw_id}").text
    needle_raw = latex
    needle_jsonish = latex.replace("\\", "\\\\")
    assert needle_raw in rendered or needle_jsonish in rendered, (
        f"{label}: LaTeX missing from /h/{{id}} HTML"
    )


@pytest.mark.parametrize("label,latex", EQUATION_FIXTURES)
def test_preview_iframe_carries_latex(client, label, latex):
    create = client.post("/api/homeworks", json=_payload_with_equation(latex))
    hw_id = create.json()["id"]
    rendered = client.get(f"/api/homeworks/{hw_id}/preview").text
    needle_raw = latex
    needle_jsonish = latex.replace("\\", "\\\\")
    assert needle_raw in rendered or needle_jsonish in rendered


@pytest.mark.parametrize("label,latex", EQUATION_FIXTURES)
def test_patch_content_preserves_latex(client, label, latex):
    """The auto-save endpoint that fires on every keystroke must not mutate
    LaTeX. A regression here silently destroys student-authored math."""
    create = client.post("/api/homeworks", json=_payload_with_equation("placeholder"))
    hw_id = create.json()["id"]
    new_content = _payload_with_equation(latex)["content_json"]
    patched = client.patch(
        f"/api/homeworks/{hw_id}/content",
        json={"content_json": new_content},
    )
    assert patched.status_code in (200, 204), patched.text
    fetch = client.get(f"/api/homeworks/{hw_id}")
    text_back = fetch.json()["content_json"]["panels"][0]["pages"][0]["blocks"][0]["text"]
    assert text_back == latex


def test_static_mounts_serve_picker_modules(client):
    """A 404 on any of these silently breaks the toolbar Σ button."""
    for path, needle in [
        ("/js/mathlive-bootstrap.js", "netsMathLive"),
        ("/js/editors/_equation-symbols.js", "EquationSymbols"),
        ("/js/editors/_equation-picker.js", "EquationPicker"),
    ]:
        r = client.get(path)
        assert r.status_code == 200, f"{path} not served"
        assert needle in r.text, f"{path} content missing global '{needle}'"


def test_runtime_loads_katex(client):
    """Sanity: the runtime template loads KaTeX so $LaTeX$ in math blocks
    actually renders. Without this the picker output is invisible at /h/{id}."""
    create = client.post("/api/homeworks", json=_payload_with_equation("$\\pi$"))
    hw_id = create.json()["id"]
    body = client.get(f"/h/{hw_id}").text
    assert "katex" in body.lower(), (
        "/h/{id} doesn't load KaTeX — picker output won't render for students"
    )


def test_builder_loads_mathlive_and_katex(client):
    """The builder page must reference both bootstrap files. A regression
    where one disappears would silently break the WYSIWYG editor."""
    body = client.get("/builder.html").text
    assert "mathlive-bootstrap.js" in body, "MathLive bootstrap not loaded"
    assert "katex-render.js" in body, "KaTeX bootstrap not loaded"
