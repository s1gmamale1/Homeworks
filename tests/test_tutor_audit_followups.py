"""PR C — frontend + backend audit follow-up regression tests.

Locks the HIGH and MEDIUM findings that PR A and PR B left open:

Frontend (rendered HTML invariants — no Playwright needed):
- FAB carries `aria-expanded="false"` and `aria-controls="nets-tutor-panel"`.
- Cap-warning has `role="alert"` and `aria-live="assertive"`.
- The IIFE installs an `Escape` keydown handler that closes the panel.
- closePanel calls `fab.focus(...)` for keyboard focus return.
- The chat-side theme toggle wires a `storage` event listener so it
  resyncs with the navbar toggle (PR #37) across documents/tabs.
- The send-button counter increments AFTER the apiAvailable() guard,
  not before — failed offline pings no longer burn the cap.

Backend (route + service contract):
- Phase string is allowlist-validated (preview/practice/boss only).
- Chat-history window is fetched via list_tutor_turns(most_recent=True,
  limit=TUTOR_CHAT_HISTORY_WINDOW), not a 200-row scan with [-6:] slice.
- _find_question_in_content recurses into nested dicts/lists.
"""
from __future__ import annotations

import asyncio
from unittest.mock import patch

import aiosqlite
import pytest

from server.config import BASE_DIR
from server.routes.ai import _find_question_in_content


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_template() -> str:
    _html = BASE_DIR / "server" / "template" / "perfect_homework.html"
    _js = BASE_DIR / "server" / "template" / "js" / "perfect_homework.js"
    _css = BASE_DIR / "server" / "template" / "static" / "css" / "perfect_homework.css"
    _tutor = BASE_DIR / "server" / "template" / "static" / "js" / "tutor.js"
    return (_html.read_text(encoding="utf-8") + "\n" +
            _js.read_text(encoding="utf-8") + "\n" +
            _css.read_text(encoding="utf-8") + "\n" +
            _tutor.read_text(encoding="utf-8"))


def _db_path() -> str:
    from server.config import DB_PATH
    return str(DB_PATH)


def _wipe_tutor_tables() -> None:
    async def _do() -> None:
        async with aiosqlite.connect(_db_path()) as conn:
            await conn.execute("DELETE FROM tutor_conversations")
            await conn.commit()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_do())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


@pytest.fixture(autouse=True)
def clean_db():
    _wipe_tutor_tables()
    yield


def _make_homework_with_boss_question(client) -> str:
    create = client.post(
        "/api/homeworks",
        json={
            "title": "Audit followup HW",
            "subject": "math-algebra",
            "grade": 8,
            "mode": "hard",
        },
    )
    assert create.status_code == 200
    hw_id = create.json()["id"]
    content = {
        "boss_questions": [
            {"question_id": "qb-fc", "q": "Solve x", "dmg": 10},
        ]
    }
    client.put(f"/api/homeworks/{hw_id}", json={"content_json": content})
    return hw_id


# ---------------------------------------------------------------------------
# Frontend — rendered HTML & IIFE invariants
# ---------------------------------------------------------------------------


def test_fab_has_aria_expanded_and_controls():
    """Screen readers need both attributes to convey "this button toggles a
    panel and is/isn't currently expanded". Pre-fix the FAB had neither.
    """
    html = _read_template()
    # Find the FAB element line and assert both attrs are present.
    assert 'id="nets-tutor-fab"' in html
    fab_line = next(
        line for line in html.splitlines() if 'id="nets-tutor-fab"' in line
    )
    assert 'aria-expanded="false"' in fab_line, (
        "FAB must carry aria-expanded — initial state is closed"
    )
    assert 'aria-controls="nets-tutor-panel"' in fab_line, (
        "FAB must reference the panel it controls"
    )


def test_cap_warning_has_aria_live():
    """The cap-warning element sits outside #nets-tutor-messages (which is
    the only `role=log` region). Without its own aria-live the AT user is
    never told the session was capped."""
    html = _read_template()
    assert 'id="nets-tutor-cap-warning"' in html
    line = next(
        l for l in html.splitlines() if 'id="nets-tutor-cap-warning"' in l
    )
    assert 'aria-live="assertive"' in line
    assert 'role="alert"' in line


def test_panel_close_returns_focus_to_fab():
    """closePanel must call fab.focus(...) so keyboard users don't lose
    their place in the document when the panel closes via Escape or the
    Close button."""
    html = _read_template()
    # Pull out the closePanel function body.
    start = html.index("function closePanel()")
    end = html.index("}", start)
    body = html[start:end]
    assert "fab.focus" in body, (
        "closePanel must restore keyboard focus to the FAB"
    )


def test_panel_open_close_toggle_aria_expanded():
    html = _read_template()
    open_idx = html.index("function openPanel()")
    close_idx = html.index("function closePanel()", open_idx)
    open_body = html[open_idx:close_idx]
    close_body = html[close_idx:html.index("\n        }", close_idx)]
    assert (
        "fab.setAttribute('aria-expanded', 'true')" in open_body
        or 'fab.setAttribute("aria-expanded", "true")' in open_body
    )
    assert (
        "fab.setAttribute('aria-expanded', 'false')" in close_body
        or 'fab.setAttribute("aria-expanded", "false")' in close_body
    )


def test_escape_key_handler_registered():
    """Pressing Escape while the panel is open must close it. Without this
    the panel is a one-way trip for keyboard-only users (no quick exit)."""
    html = _read_template()
    # Look for a keydown listener that checks for Escape and calls closePanel.
    keydown_idx = html.find("addEventListener('keydown'", html.index("function closePanel"))
    assert keydown_idx != -1, "no keydown handler registered after closePanel"
    handler = html[keydown_idx : keydown_idx + 600]
    assert "Escape" in handler
    assert "closePanel()" in handler


def test_chat_theme_toggle_listens_for_storage_events():
    """The chat IIFE must register a `storage` listener on
    `nets_theme` so the runtime player resyncs when the navbar
    toggle (PR #37) flips the theme in another tab or the parent
    document.

    The 2026-04-29 cleanup removed the chat-side toggle button and
    renamed the setup function from `setupThemeToggle()` (which
    wired BOTH the button click handler AND the storage listener)
    to `applyStoredTheme()` (which only does the read-only mirror).
    The behavioural invariant under test is unchanged: a storage
    listener gated by THEME_KEY must exist."""
    html = _read_template()
    setup_idx = html.index("function applyStoredTheme()")
    setup_end = html.index("applyStoredTheme();", setup_idx)
    body = html[setup_idx:setup_end]
    assert "addEventListener('storage'" in body or 'addEventListener("storage"' in body, (
        "applyStoredTheme must listen for storage events to resync with the navbar"
    )
    assert "THEME_KEY" in body  # gate by key so unrelated storage writes don't apply


def test_message_count_incremented_after_offline_guard():
    """Pre-fix `state.messageCount += 1` ran BEFORE the apiAvailable() check,
    so every failed offline ping burned 1/SESSION_CAP. Post-fix the increment
    must live INSIDE the try block, after the offline early-return."""
    html = _read_template()
    send_idx = html.index("async function sendMessage(text)")
    func_body = html[send_idx : send_idx + 1500]
    # Grab everything up to "if (!apiAvailable())" and assert no increment yet.
    pre_offline = func_body.split("if (!apiAvailable()")[0]
    assert "state.messageCount += 1" not in pre_offline, (
        "messageCount must NOT increment before the apiAvailable() guard"
    )
    # And it must still increment somewhere in the function (post-guard).
    assert func_body.count("state.messageCount += 1") >= 1


# ---------------------------------------------------------------------------
# Backend — phase allowlist
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_phase", ["xyzzy", "", "PREVIEW", "boss-mode", " preview"])
@patch("server.services.ai_orchestrator.generate")
def test_unknown_phase_is_rejected(mock_generate, bad_phase, client):
    mock_generate.return_value = "should not be called"
    hw_id = _make_homework_with_boss_question(client)
    resp = client.post(
        "/api/ai/tutor/chat",
        json={
            "session_id": "sess-phase-validate",
            "hw_id": hw_id,
            "phase": bad_phase,
            "message": "hi",
        },
    )
    # Pydantic catches type mismatches as 422; explicit 400 is for our own
    # allowlist rejection. Either way the request must fail and the LLM
    # must not be called.
    assert resp.status_code in (400, 422)
    if resp.status_code == 400:
        assert resp.json()["detail"]["code"] == "INVALID_PHASE"
    mock_generate.assert_not_called()


@pytest.mark.parametrize("good_phase", ["preview", "practice", "boss"])
@patch("server.services.ai_orchestrator.generate")
def test_known_phases_pass_validation(mock_generate, good_phase, client):
    mock_generate.return_value = "ok"
    hw_id = _make_homework_with_boss_question(client)
    resp = client.post(
        "/api/ai/tutor/chat",
        json={
            "session_id": f"sess-phase-{good_phase}",
            "hw_id": hw_id,
            "phase": good_phase,
            "message": "hi",
        },
    )
    assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# Backend — list_tutor_turns(most_recent=True) shape
# ---------------------------------------------------------------------------


def test_list_tutor_turns_most_recent_returns_last_n_chronologically():
    from server import db

    async def _seed_and_query():
        # Seed 10 turns; assert most_recent=True with limit=3 returns the last
        # 3 (indices 7, 8, 9) in chronological order.
        async with aiosqlite.connect(_db_path()) as conn:
            for i in range(10):
                await conn.execute(
                    "INSERT INTO tutor_conversations "
                    "(session_id, hw_id, phase, role, content, created_at) "
                    "VALUES (?, ?, 'preview', 'user', ?, datetime('now', '+' || ? || ' seconds'))",
                    ("sess-chrono-test", "HW-1", f"turn-{i}", i),
                )
            await conn.commit()

        recent = await db.list_tutor_turns(
            "sess-chrono-test", "HW-1", limit=3, most_recent=True
        )
        return [r["content"] for r in recent]

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        contents = loop.run_until_complete(_seed_and_query())
    finally:
        loop.close()
        asyncio.set_event_loop(None)

    assert contents == ["turn-7", "turn-8", "turn-9"], (
        f"most_recent=True must return the last 3 turns in chronological "
        f"order, got: {contents}"
    )


@patch("server.services.ai_orchestrator.generate")
def test_chat_history_window_uses_most_recent_query_not_slice(mock_generate, client):
    """The chat-history window in tutor_chat must call list_tutor_turns with
    most_recent=True + the small window limit — not pull 200 rows and slice.
    """
    from server.services.tutor import TUTOR_CHAT_HISTORY_WINDOW

    mock_generate.return_value = "ok"
    hw_id = _make_homework_with_boss_question(client)

    with patch("server.db.list_tutor_turns", wraps=__import__("server.db", fromlist=["list_tutor_turns"]).list_tutor_turns) as wrapped:
        client.post(
            "/api/ai/tutor/chat",
            json={
                "session_id": "sess-history-window",
                "hw_id": hw_id,
                "phase": "preview",
                "message": "hi",
            },
        )

    # Find the call from tutor_chat (most_recent=True + the window limit).
    chat_calls = [
        c for c in wrapped.call_args_list
        if c.kwargs.get("most_recent") is True
    ]
    assert chat_calls, (
        "tutor_chat must fetch the recent history window with most_recent=True"
    )
    last = chat_calls[-1]
    assert last.kwargs.get("limit") == TUTOR_CHAT_HISTORY_WINDOW, (
        f"limit should be {TUTOR_CHAT_HISTORY_WINDOW}, got {last.kwargs.get('limit')}"
    )


# ---------------------------------------------------------------------------
# Backend — _find_question_in_content recursion
# ---------------------------------------------------------------------------


def test_find_question_in_top_level_list_still_works():
    content = {
        "boss_questions": [
            {"question_id": "qb1", "q": "ok"},
            {"question_id": "qb2", "q": "still ok"},
        ]
    }
    assert _find_question_in_content(content, "qb2") == {
        "question_id": "qb2",
        "q": "still ok",
    }


def test_find_question_inside_nested_dict_value():
    """Pre-fix the search only walked top-level lists. A reading checkpoint
    inside `reading.checkpoints[]` was invisible — the tutor lost its
    question_text context for that surface."""
    content = {
        "reading": {
            "title": "Reading passage",
            "checkpoints": [
                {"id": "rc1", "prompt": "What is X?"},
                {"id": "rc2", "prompt": "Why Y?"},
            ],
        },
        "consolidation": {
            "problems": [
                {"question_id": "cp1", "q": "Last one"},
            ]
        },
    }
    assert _find_question_in_content(content, "rc2") == {
        "id": "rc2",
        "prompt": "Why Y?",
    }
    assert _find_question_in_content(content, "cp1") == {
        "question_id": "cp1",
        "q": "Last one",
    }


def test_find_question_in_deeply_nested_structure():
    """Recursion must work at arbitrary depth; first match wins."""
    content = {
        "a": {
            "b": {
                "c": [
                    {"id": "deep-target", "q": "found me"},
                    {"id": "deep-other", "q": "not me"},
                ]
            }
        }
    }
    assert _find_question_in_content(content, "deep-target") == {
        "id": "deep-target",
        "q": "found me",
    }


def test_find_question_returns_none_for_unknown_id():
    content = {"boss_questions": [{"question_id": "qb1"}]}
    assert _find_question_in_content(content, "missing") is None
    assert _find_question_in_content(content, "") is None
    assert _find_question_in_content(None, "qb1") is None  # type: ignore[arg-type]
