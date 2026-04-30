"""
Regression guards for the 2026-04-29 sectioned-library work.

The library page used to be a flat grid + 4 dropdowns (subject /
grade / mode / search). The redesign groups by Subject ▸ Grade with
a global language chip strip on top.

Backend contract (`server/routes/library.py`)
-----------------------------------------------
- `/api/library` items expose `language` so the frontend can filter
  client-side and decorate each card.
- `/api/library?language=uz|ru|en` filters server-side.
- Unknown language values are rejected 400 INVALID_LANGUAGE rather
  than silently returning empty.
- `/api/library/facets` includes a `languages` array.

Frontend (`frontend/library.html`, `frontend/js/library.js`,
          `frontend/css/library.css`)
-----------------------------------------------
- The static markup carries the new shell: `#lib-lang-chips`,
  `#lib-sections`, no per-page subject/grade/mode dropdown.
- The JS exposes the subject grouping helpers so a refactor that
  drops them is caught.
- New i18n keys (`library.content_lang_label`, `library.lang_all`,
  `library.section_grade_label`, `library.section_count_*`,
  `library.section_empty`) are present in all three locales.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parent.parent
LIBRARY_HTML = REPO_ROOT / "frontend" / "library.html"
LIBRARY_JS = REPO_ROOT / "frontend" / "js" / "library.js"
LIBRARY_CSS = REPO_ROOT / "frontend" / "css" / "library.css"
I18N_STRINGS = REPO_ROOT / "frontend" / "js" / "i18n" / "strings.js"


# ---------------------------------------------------------------------------
# Fresh DB per test — copied from test_library.py's pattern.
# ---------------------------------------------------------------------------


def _wipe_homeworks() -> None:
    import asyncio
    import aiosqlite
    from server.config import DB_PATH

    async def _do() -> None:
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute("DELETE FROM homework_versions")
            await db.execute("DELETE FROM homeworks")
            await db.commit()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_do())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


@pytest.fixture(autouse=True)
def _clean_db(client):
    _wipe_homeworks()
    yield


def _post_homework(client, subject: str, grade: int, mode: str = "hard") -> str:
    resp = client.post("/api/homeworks", json={
        "title": f"Smoke {subject}-{grade}-{mode}",
        "subject": subject,
        "grade": grade,
        "mode": mode,
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------


def test_library_items_expose_language(client):
    """Each item in the library list must include a `language` field
    so the card decorations and client-side filter have something to
    bind to. Pre-fix the SELECT column list ended at `updated_at` and
    `language` never reached the wire."""
    _post_homework(client, "math-algebra", 8)

    resp = client.get("/api/library")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert items, "expected at least one item"
    assert "language" in items[0], (
        "library items must expose `language` — required for the "
        "sectioned layout's per-card pill and the language filter."
    )
    # Default language is uz (server/db.py:19); persistence of ru/en
    # is owned by the parallel Codex PR and not asserted here.
    assert items[0]["language"] in {"uz", "ru", "en"}, items[0]


def test_library_filters_by_language(client):
    """`?language=uz` must filter server-side."""
    _post_homework(client, "math-algebra", 8)
    _post_homework(client, "biology", 7)

    resp = client.get("/api/library", params={"language": "uz"})
    assert resp.status_code == 200
    data = resp.json()
    # Both rows default to uz, so this filter is the no-op happy
    # path — but the server must still ACCEPT the param. The
    # zero-result case is exercised in the next test.
    assert data["total"] == 2

    # And every item carries language=uz.
    for item in data["items"]:
        assert item["language"] == "uz"


def test_library_unknown_language_400(client):
    """Typos like `?language=engl` must 400 with a clear error code,
    not silently return an empty page."""
    resp = client.get("/api/library", params={"language": "engl"})
    assert resp.status_code == 400
    payload = resp.json()
    assert isinstance(payload.get("detail"), dict)
    assert payload["detail"].get("code") == "INVALID_LANGUAGE"
    # Message must mention the allowed set so the client can self-correct.
    assert "uz" in payload["detail"].get("error", "")


def test_library_filter_yields_zero_for_absent_language(client):
    """`?language=ru` on a uz-only DB returns an empty page with
    total=0, not a 500. (Surfaces the fact that the underlying
    column is queryable even when no rows match.)"""
    _post_homework(client, "math-algebra", 8)
    resp = client.get("/api/library", params={"language": "ru"})
    assert resp.status_code == 200
    data = resp.json()
    assert data == {"items": [], "total": 0}


def test_library_facets_includes_languages(client):
    _post_homework(client, "math-algebra", 8)

    resp = client.get("/api/library/facets")
    assert resp.status_code == 200
    data = resp.json()
    assert "languages" in data
    assert isinstance(data["languages"], list)
    # uz is the default; it must appear once a row exists.
    assert "uz" in data["languages"]


# ---------------------------------------------------------------------------
# Frontend static markup
# ---------------------------------------------------------------------------


def test_library_html_has_new_shell():
    html = LIBRARY_HTML.read_text(encoding="utf-8")
    # The 2026-04-30 Apple-style redesign replaced the <details>
    # `#lib-sections` container with an Apple-grid `#lib-subject-grid`
    # of expandable subject tiles plus a `#lib-stats` strip.
    assert 'id="lib-lang-chips"' in html, "missing language chip group"
    assert 'id="lib-subject-grid"' in html, "missing #lib-subject-grid container"
    assert 'id="lib-stats"' in html, "missing #lib-stats strip"
    assert 'id="lib-stage"' in html, "missing #lib-stage host"
    # The four old per-page dropdowns must be gone — sections own
    # subject/grade now, mode is communicated via the per-card badge.
    forbidden_ids = ('id="lib-subject"', 'id="lib-grade"', 'id="lib-mode"', 'id="lib-sections"')
    for fid in forbidden_ids:
        assert fid not in html, (
            f"library.html still ships {fid} — the Apple-style redesign "
            "moved subject/grade/mode out of the page-level toolbar"
        )


def test_lang_chip_group_has_all_three_languages():
    html = LIBRARY_HTML.read_text(encoding="utf-8")
    # The chip group must offer All + the three supported languages
    # so the layout works for ru/en deployments once Codex's
    # language-persistence PR lands.
    for lang_attr in ('data-lib-lang=""',
                      'data-lib-lang="uz"',
                      'data-lib-lang="ru"',
                      'data-lib-lang="en"'):
        assert lang_attr in html, f"missing chip with {lang_attr}"


# ---------------------------------------------------------------------------
# Frontend JS — keep the subject-grouping helpers in place
# ---------------------------------------------------------------------------


def test_library_js_has_grouping_helpers():
    src = LIBRARY_JS.read_text(encoding="utf-8")
    # 2026-04-30 v2 redesign: <details> sections replaced by in-grid
    # tile expansion. The grouping helper survives; the per-section
    # render path is now `renderTile` + `expandSubject` + `collapseSubject`
    # (the FLIP overlay's `openSubject` / `closePanel` / `getExpandedTarget`
    # were retired when the .subject-panel overlay was deleted).
    for needle in (
        "function groupBySubject",
        "function renderTile",
        "function expandSubject",
        "function collapseSubject",
        "function renderHomeworkCard",
        "function renderStats",
    ):
        assert needle in src, f"library.js missing {needle}"


def test_library_js_persists_state_in_localStorage():
    src = LIBRARY_JS.read_text(encoding="utf-8")
    # Persisted state — language choice + per-subject selected grade —
    # survives reloads. Open-panel state is intentionally NOT persisted
    # (auto-restoring an expanded panel on reload was disruptive).
    # Key bumped to v3 to invalidate the v2 schema (had `openSubjects`).
    assert "nets.library.v3" in src, (
        "library.js must namespace its localStorage key so a future "
        "schema bump can be invalidated cleanly"
    )
    assert "gradeBySubject" in src, (
        "library.js lost the per-subject grade persistence key"
    )
    # The legacy openSubjects key should be gone — the FLIP-panel
    # design doesn't auto-restore an open panel on reload.
    assert "openSubjects" not in src, (
        "library.js still references openSubjects — the FLIP redesign "
        "intentionally drops auto-restore-open behaviour"
    )


def test_library_js_no_longer_uses_pagination_buttons():
    """The pre-fix layout had Prev/Next buttons because a flat grid
    couldn't show 50+ items at once. The sectioned layout fetches
    everything (clamped) and groups, so the pagination DOM refs are
    gone. If a refactor reintroduces them, it should be a deliberate
    decision — surface it."""
    src = LIBRARY_JS.read_text(encoding="utf-8")
    forbidden = ('lib-prev-btn', 'lib-next-btn', 'lib-page-label')
    for f in forbidden:
        assert f not in src, (
            f"library.js still references #{f} — the sectioned "
            "layout shouldn't need page-level pagination"
        )


# ---------------------------------------------------------------------------
# i18n — new keys exist in all three locales
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", [
    "library.content_lang_label",
    "library.lang_all",
    "library.section_grade_label",
    "library.section_grade_all",
    "library.section_empty",
    "library.section_count_one",
    "library.section_count_other",
])
def test_i18n_strings_define_new_keys(key):
    src = I18N_STRINGS.read_text(encoding="utf-8")
    # Each key must appear at least 3 times — once per locale (en/uz/ru).
    occurrences = src.count(f"'{key}'")
    assert occurrences >= 3, (
        f"i18n key '{key}' appears {occurrences}× — must be defined "
        "in all three locales (en, uz, ru)"
    )


# ---------------------------------------------------------------------------
# CSS — section + chip rules survive
# ---------------------------------------------------------------------------


def test_library_css_has_section_and_chip_rules():
    css = LIBRARY_CSS.read_text(encoding="utf-8")
    # 2026-04-30 v2 redesign: replaced the overlay .subject-panel with
    # in-grid expansion (.subject-tile.is-expanded). The chip group +
    # grade chips remain (renamed to .lib-grade-chip in the expanded
    # tile body). The CSS agent owns the file — this guard just pins
    # the surface that library.js binds to.
    needles = (
        ".subject-tile",
        ".subject-tile.is-expanded",
        ".lib-grade-chip",
        ".lib-chip-group",
        ".lib-chip",
        ".homework-card",
    )
    for n in needles:
        assert n in css, f"library.css missing rule for {n}"


# ---------------------------------------------------------------------------
# End-to-end: served library page contains the new shell
# ---------------------------------------------------------------------------


def test_served_library_page_renders_new_shell(client):
    r = client.get("/library.html")
    assert r.status_code == 200
    body = r.text
    assert 'id="lib-lang-chips"' in body
    assert 'id="lib-subject-grid"' in body
    assert 'id="lib-stats"' in body
    assert 'id="lib-stage"' in body
    # Old IDs must be gone from the served HTML too.
    assert 'id="lib-subject"' not in body
    assert 'id="lib-grade"' not in body
    assert 'id="lib-sections"' not in body
