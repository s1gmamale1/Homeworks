"""
Regression: every `@router.<method>(...)` endpoint declared under `server/routes/`
must have a corresponding `### METHOD /full/path` section header in `docs/API.md`.

Background:
    PR #132 (Sentence Fill backend) added `POST /api/ai/check-answer/finalize`
    but shipped no docs/API.md update. The reviewer's daily PR audit caught the
    drift after the fact. This test fences the same drift class going forward —
    any future PR that adds a new router decorator without a matching doc
    section fails the merge gate at the pytest layer.

Scope:
    - Walks every `*.py` under `server/routes/` (except `__init__.py`).
    - Resolves the full external URL by joining the `app.include_router` prefix
      and the `APIRouter(prefix=...)` value (hardcoded in `_ROUTER_PREFIXES`
      below — small, stable list; touch only when a NEW router file is added,
      which is rare).
    - Extracts every `### METHOD /path` heading from `docs/API.md`.
    - Asserts every routed endpoint has a documented heading.

How to fix a failure:
    Add a `### <METHOD> <path>` section to `docs/API.md` with request/response
    shapes for every endpoint in the test's failure list. Don't suppress the
    test — that defeats the whole point.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ROUTES_DIR = REPO_ROOT / "server" / "routes"
DOCS_API = REPO_ROOT / "docs" / "API.md"

# Full external URL prefix per route file. Combines:
#   - the `app.include_router(<router>, prefix=...)` external prefix in app.py
#   - the `APIRouter(prefix=...)` internal prefix in the route file itself
#
# When a brand-new route file is added under server/routes/, add its mapping
# here; the test will fail with a clear "unknown route file" message until you do.
_ROUTER_PREFIXES: dict[str, str] = {
    "ai.py":            "/api",
    "ai_plan5.py":      "/api",
    "ai_plan8.py":      "/api",
    "equations.py":     "/api",
    "grading.py":       "/api/grading",
    "homework.py":      "/api/homeworks",
    "homework_page.py": "",
    "library.py":       "/api/library",
    "meta.py":          "/api",
    "notebook.py":      "/api/notebook",
    "taskboard.py":     "/api/taskboard",
    "runtime.py":       "/api",
    "reflection.py":    "/api",
    "integrity.py":     "/api",
    "uploads.py":       "/api",
    "applications.py":  "/api/applications",
}

_DECORATOR_RE = re.compile(
    r'@router\.(get|post|put|patch|delete)\(\s*[\'"]([^\'"]*)[\'"]',
    re.MULTILINE,
)
_HEADING_RE = re.compile(
    r'^###\s+(GET|POST|PUT|PATCH|DELETE)\s+(\S+)',
    re.MULTILINE,
)


def _routed_endpoints() -> set[tuple[str, str]]:
    """Walk server/routes/*.py and return every (METHOD, FULL_PATH) pair."""
    routed: set[tuple[str, str]] = set()
    seen_files: list[str] = []
    for py in sorted(ROUTES_DIR.glob("*.py")):
        if py.name == "__init__.py":
            continue
        seen_files.append(py.name)
        prefix = _ROUTER_PREFIXES.get(py.name)
        assert prefix is not None, (
            f"unknown route file {py.name!r} — add a mapping to "
            f"_ROUTER_PREFIXES in {Path(__file__).name} so the audit knows "
            f"the full external URL prefix for this router."
        )
        text = py.read_text(encoding="utf-8")
        for method, path in _DECORATOR_RE.findall(text):
            full = (prefix + path).rstrip("/") or "/"
            routed.add((method.upper(), full))
    assert seen_files, f"no route files found under {ROUTES_DIR}"
    return routed


def _documented_endpoints() -> set[tuple[str, str]]:
    """Parse docs/API.md and return every (METHOD, PATH) declared in `### METHOD /path` headings."""
    text = DOCS_API.read_text(encoding="utf-8")
    return {
        (method.upper(), path.rstrip("/") or "/")
        for method, path in _HEADING_RE.findall(text)
    }


def test_api_md_documents_every_router_endpoint():
    routed = _routed_endpoints()
    documented = _documented_endpoints()

    missing = routed - documented
    assert not missing, (
        "\n\nEndpoints exist in server/routes/* but are NOT documented in docs/API.md.\n"
        "Add a `### METHOD /full/path` section per missing entry with request/response shapes.\n"
        "Do NOT suppress this test — drift between code and docs was the exact bug PR #132\n"
        "introduced (see daily PR audit, 2026-05-02).\n"
        f"Missing ({len(missing)}):\n"
        + "\n".join(f"  - {m:7} {p}" for m, p in sorted(missing))
        + "\n"
    )


_CHECK_ANSWER_PHASES: tuple[str, ...] = (
    "tile-match",
    "real-life-challenge",
    "final-boss",
    "ttt",
    "ttt-session",
    "memory-palace",
)


def test_api_md_documents_check_answer_phases():
    """Sigma drift fence: every `phase=<name>` sub-variant of POST /api/ai/check-answer
    must be documented in docs/API.md as a `*(phase = "...")*` heading marker.

    Background: check-answer sub-phases share a single route decorator, so
    `test_api_md_documents_every_router_endpoint` (which walks decorators) won't
    catch missing per-phase docs. This test fences that gap explicitly.

    Each entry in `_CHECK_ANSWER_PHASES` must appear in a heading that contains
    the literal string  phase = "<name>"  inside the heading line — matching the
    pattern used for tile-match, real-life-challenge, final-boss, ttt, ttt-session.
    """
    text = DOCS_API.read_text(encoding="utf-8")
    missing = []
    for phase in _CHECK_ANSWER_PHASES:
        # Match the heading pattern: phase = `"<name>"`  (backtick-wrapped in MD)
        if f'phase = `"{phase}"`' not in text:
            missing.append(phase)
    assert not missing, (
        "\n\nThe following check-answer phase sub-variants are not documented in "
        "docs/API.md.\nAdd a `### POST /api/ai/check-answer  *(phase = \"<name>\")*` "
        "section for each:\n"
        + "\n".join(f"  - phase={p}" for p in missing)
        + "\n"
    )


def test_api_md_does_not_document_phantom_endpoints():
    """Catch the inverse drift: a docs heading for an endpoint that no longer exists in code."""
    routed = _routed_endpoints()
    documented = _documented_endpoints()

    # Endpoints that appear in docs but have no router decorator. A small allow-list
    # is reserved for non-FastAPI surfaces that legitimately belong in API.md (e.g.,
    # static asset routes, frontend-only contracts). Empty for now — every documented
    # entry currently maps to a real router endpoint.
    allowlist: set[tuple[str, str]] = set()

    stale = (documented - routed) - allowlist
    assert not stale, (
        "\n\ndocs/API.md documents endpoints that no longer exist in server/routes/*.\n"
        "Either restore the route or remove the section.\n"
        f"Stale ({len(stale)}):\n"
        + "\n".join(f"  - {m:7} {p}" for m, p in sorted(stale))
        + "\n"
    )
