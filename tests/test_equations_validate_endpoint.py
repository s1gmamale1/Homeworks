"""POST /api/equations/validate — endpoint regression suite.

Layered tests for the LaTeX validator, both at the service level (pure-
Python `validate_latex`) and at the HTTP boundary (`/api/equations/validate`).

Coverage:
  - Valid expressions across the major template families return valid=true
    with the right macro list and depth metrics
  - Brace / bracket / paren imbalance is caught with position
  - \\begin{X}/\\end{Y} mismatches caught with position
  - Forbidden constructs (script tag, \\input, \\write18, \\href) caught
    with the right error code
  - Length cap honored, override accepted
  - 50KB+ payload rejected with 413
  - Unfilled \\placeholder{} markers surface as warnings, not errors
  - $...$ and $$...$$ delimiters auto-stripped
  - Empty input rejected with error="empty"
  - Non-string `latex` rejected (Pydantic 422 — schema-level)
  - Unknown extra fields are accepted (extra="allow" — Invariant 1 idiom)

Why this layered structure: catching regressions in the validator without
having to spin up the FastAPI client is fast (the service-level tests
run in <50ms each). The HTTP-level tests pin the route contract — error
HTTP status codes, the JSON shape clients depend on.
"""

from __future__ import annotations

import pytest

from server.services.latex_validator import (
    DEFAULT_MAX_LENGTH,
    validate_latex,
)


# ── Service layer: pure-Python validator ────────────────────────────


@pytest.mark.parametrize(
    "latex",
    [
        r"\frac{1}{2}",
        r"\sqrt{x^2 + y^2}",
        r"\int_{0}^{1} x^2 \, dx",
        r"\sum_{i=1}^{n} i^2",
        r"\lim_{x \to \infty} \frac{1}{x}",
        r"\begin{pmatrix} 1 & 0 \\ 0 & 1 \end{pmatrix}",
        r"\begin{cases} x, & x > 0 \\ -x, & x \le 0 \end{cases}",
        r"\alpha + \beta = \gamma",
        r"\overline{AB} \perp \overline{CD}",
        # Plain text mixed with math
        r"S = \pi r^2",
    ],
)
def test_validate_known_good_latex(latex):
    result = validate_latex(latex)
    assert result["valid"] is True, f"unexpected invalid: {result}"
    assert result["error"] is None
    assert result["latex"] == latex
    assert isinstance(result["macros"], list)


def test_validate_strips_outer_dollar_inline():
    result = validate_latex(r"$\alpha$")
    assert result["valid"]
    assert result["latex"] == r"\alpha"


def test_validate_strips_outer_dollar_display():
    result = validate_latex(r"$$\alpha$$")
    assert result["valid"]
    assert result["latex"] == r"\alpha"


def test_validate_does_not_strip_partial_dollar():
    """Only matching $-pairs strip — `$alpha` (one $) keeps it."""
    result = validate_latex(r"$\alpha")
    assert result["valid"]
    assert result["latex"] == r"$\alpha"


# ── Brace / bracket / environment balance ──────────────────────────


def test_unbalanced_open_brace():
    result = validate_latex(r"\frac{1")
    assert not result["valid"]
    assert result["error"] == "unbalanced_braces"
    assert "unclosed" in result["message"]
    assert isinstance(result["position"], int)


def test_unbalanced_close_brace():
    result = validate_latex(r"\frac1}")
    assert not result["valid"]
    assert result["error"] == "unbalanced_braces"
    assert "unmatched" in result["message"]


def test_mismatched_brace_bracket():
    result = validate_latex(r"\frac{1]")
    assert not result["valid"]
    assert result["error"] == "unbalanced_braces"


def test_escaped_braces_dont_count_as_unbalanced():
    """\\{ and \\} are literal characters, not delimiters."""
    result = validate_latex(r"\{ a \}")
    assert result["valid"], result


def test_environment_unmatched_begin():
    result = validate_latex(r"\begin{pmatrix} 1 & 0")
    assert not result["valid"]
    assert result["error"] == "unbalanced_environments"


def test_environment_name_mismatch():
    result = validate_latex(r"\begin{pmatrix} 1 \end{bmatrix}")
    assert not result["valid"]
    assert result["error"] == "unbalanced_environments"
    assert "pmatrix" in result["message"]


def test_environment_proper_nesting_ok():
    """Nested environments must close in reverse order."""
    result = validate_latex(
        r"\begin{aligned} \begin{pmatrix} a \end{pmatrix} \end{aligned}"
    )
    assert result["valid"], result


# ── Forbidden constructs (security) ─────────────────────────────────


@pytest.mark.parametrize(
    "latex,expected_code",
    [
        (r"<script>alert(1)</script>",                "script_tag"),
        (r"<SCRIPT>alert(1)</SCRIPT>",                "script_tag"),
        (r"\input{/etc/passwd}",                      "latex_include"),
        (r"\include{evil}",                           "latex_include"),
        (r"\write18{rm -rf /}",                       "latex_shell_escape"),
        (r"\href{javascript:alert(1)}{click}",        "href_macro"),
    ],
)
def test_forbidden_constructs_are_rejected(latex, expected_code):
    result = validate_latex(latex)
    assert not result["valid"], f"should reject {latex!r}"
    assert result["error"] == expected_code


# ── Length cap ──────────────────────────────────────────────────────


def test_too_long_latex_rejected():
    s = "x" * (DEFAULT_MAX_LENGTH + 1)
    result = validate_latex(s)
    assert not result["valid"]
    assert result["error"] == "too_long"


def test_max_length_override_accepted():
    s = "x" * (DEFAULT_MAX_LENGTH + 1)
    result = validate_latex(s, max_length=DEFAULT_MAX_LENGTH * 5)
    assert result["valid"]


def test_empty_latex_rejected():
    result = validate_latex("")
    assert not result["valid"]
    assert result["error"] == "empty"


def test_whitespace_only_latex_rejected():
    result = validate_latex("   \n\t   ")
    assert not result["valid"]
    assert result["error"] == "empty"


# ── Diagnostics: macros / placeholders / depth ──────────────────────


def test_macros_extracted_dedup_sorted():
    result = validate_latex(r"\frac{\alpha}{\beta} + \alpha")
    assert "frac" in result["macros"]
    assert "alpha" in result["macros"]
    assert "beta" in result["macros"]
    # sorted + dedup — only one alpha entry
    assert result["macros"].count("alpha") == 1
    assert result["macros"] == sorted(result["macros"])


def test_placeholder_count_surfaces_as_warning_not_error():
    result = validate_latex(r"\frac{\placeholder{}}{\placeholder{}}")
    assert result["valid"], "unfilled placeholders should NOT be a hard error"
    assert result["placeholders"] == 2
    assert any("placeholder" in w for w in result["warnings"]), result["warnings"]


def test_brace_depth_calculated():
    result = validate_latex(r"\frac{\sqrt{x}}{y}")
    # \frac{...}{...} = depth 1, \sqrt{...} inside = depth 2
    assert result["depth"] == 2


def test_position_is_zero_based_offset():
    result = validate_latex(r"x + }")
    # The first ill-placed character is the } at offset 4 (in stripped form)
    assert result["position"] == 4


# ── Type errors ─────────────────────────────────────────────────────


def test_non_string_latex_rejected_at_service():
    """Service layer fails closed if a non-str slips through (FastAPI's
    Pydantic schema would already 422, but defense-in-depth)."""
    result = validate_latex(123)  # type: ignore[arg-type]
    assert not result["valid"]
    assert result["error"] == "type_error"


# ── HTTP layer: /api/equations/validate ─────────────────────────────


def test_endpoint_returns_200_on_valid(client):
    r = client.post(
        "/api/equations/validate",
        json={"latex": r"\frac{1}{2}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["valid"] is True
    assert body["error"] is None
    assert "frac" in body["macros"]


def test_endpoint_returns_200_with_valid_false_on_malformed(client):
    """Malformed LaTeX is a regular 200 with valid=false. Clients inspect
    the body, not the HTTP status."""
    r = client.post(
        "/api/equations/validate",
        json={"latex": r"\frac{1"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["valid"] is False
    assert body["error"] == "unbalanced_braces"


def test_endpoint_rejects_50kb_payload_with_413(client):
    """Pathological payloads are 413, not 200 — protects the validator from
    DoS-style inputs."""
    r = client.post(
        "/api/equations/validate",
        json={"latex": "x" * 60_000},
    )
    assert r.status_code == 413, r.text
    body = r.json()
    assert body["detail"]["error"] == "payload_too_large"


def test_endpoint_422_on_missing_latex(client):
    """Pydantic-level — `latex` is required."""
    r = client.post("/api/equations/validate", json={})
    assert r.status_code == 422


def test_endpoint_422_on_non_string_latex(client):
    r = client.post("/api/equations/validate", json={"latex": 123})
    assert r.status_code == 422


def test_endpoint_accepts_extra_fields(client):
    """Pydantic _Permissive idiom — Invariant 1. Unknown fields land
    silently so older clients can talk to newer servers."""
    r = client.post(
        "/api/equations/validate",
        json={"latex": r"\alpha", "future_field": "ignored"},
    )
    assert r.status_code == 200
    assert r.json()["valid"]


def test_endpoint_response_shape_pinned(client):
    """Pin the keys clients depend on. Adding fields is fine; renaming
    or removing breaks consumers."""
    r = client.post(
        "/api/equations/validate",
        json={"latex": r"\sqrt{x}"},
    )
    body = r.json()
    expected_keys = {
        "valid", "latex", "mode", "length", "macros", "placeholders",
        "depth", "warnings", "error", "message", "position",
    }
    missing = expected_keys - set(body.keys())
    assert not missing, f"response missing keys: {missing}"


def test_endpoint_strips_dollar_delimiters(client):
    r = client.post(
        "/api/equations/validate",
        json={"latex": r"$\alpha$"},
    )
    body = r.json()
    assert body["valid"]
    assert body["latex"] == r"\alpha"


def test_endpoint_security_rejects_script_tag(client):
    r = client.post(
        "/api/equations/validate",
        json={"latex": r"<script>alert(1)</script>"},
    )
    body = r.json()
    assert body["valid"] is False
    assert body["error"] == "script_tag"


def test_endpoint_unfilled_placeholders_warn_not_error(client):
    r = client.post(
        "/api/equations/validate",
        json={"latex": r"\frac{\placeholder{}}{\placeholder{}}"},
    )
    body = r.json()
    assert body["valid"] is True
    assert body["placeholders"] == 2
    assert body["warnings"], "expected at least one warning about placeholders"


def test_endpoint_max_length_override_honored(client):
    """A client can opt-in to a larger cap by passing max_length."""
    long_latex = "x" * 3000
    r1 = client.post(
        "/api/equations/validate",
        json={"latex": long_latex},
    )
    assert r1.json()["valid"] is False
    assert r1.json()["error"] == "too_long"

    r2 = client.post(
        "/api/equations/validate",
        json={"latex": long_latex, "max_length": 4000},
    )
    assert r2.json()["valid"] is True
