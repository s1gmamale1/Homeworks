"""
Wave F1 — backend tutor tests.

Covers:
  1. preview chat persists user + assistant turns
  2. practice chat does NOT leak the answer (CRITICAL — input prompt redaction)
  3. practice chat: tutor's response is passed through verbatim
  4. boss-plan: valid LLM response covers every question_id once
  5. boss-plan: invalid LLM response triggers default-order fallback
  6. history endpoint returns turns chronologically
  7. cross-session isolation
  8. 60-message cap returns 429 on the 61st chat
  9. tutor sees prior attempts when tutor_attempts table exists
 10. graceful missing-table fallback when tutor_attempts is absent

Run:
    python -m pytest tests/test_tutor_chat.py -v
"""

from __future__ import annotations

import asyncio
import os
import sqlite3
from typing import Any
from unittest.mock import patch

import aiosqlite
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _db_path() -> str:
    from server.config import DB_PATH
    return str(DB_PATH)


def _wipe_tutor_tables() -> None:
    """Reset tutor_conversations + drop any test-created tutor_attempts so each
    test starts with a clean slate."""

    async def _do() -> None:
        async with aiosqlite.connect(_db_path()) as conn:
            await conn.execute("DELETE FROM tutor_conversations")
            try:
                await conn.execute("DROP TABLE IF EXISTS tutor_attempts")
            except Exception:
                pass
            await conn.commit()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_do())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def _create_tutor_attempts_table() -> None:
    """Mirror the contract schema. Used only by tests that simulate the
    grading lane having been merged."""

    async def _do() -> None:
        async with aiosqlite.connect(_db_path()) as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tutor_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    hw_id TEXT NOT NULL,
                    question_id TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    student_answer TEXT NOT NULL,
                    verdict TEXT NOT NULL,
                    score REAL,
                    source TEXT NOT NULL,
                    feedback TEXT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await conn.commit()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_do())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def _insert_tutor_attempt(**fields: Any) -> None:
    async def _do() -> None:
        async with aiosqlite.connect(_db_path()) as conn:
            await conn.execute(
                "INSERT INTO tutor_attempts "
                "(session_id, hw_id, question_id, phase, student_answer, verdict, score, source, feedback) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    fields.get("session_id"),
                    fields.get("hw_id"),
                    fields.get("question_id"),
                    fields.get("phase", "practice"),
                    fields.get("student_answer", ""),
                    fields.get("verdict", "incorrect"),
                    fields.get("score", 0.0),
                    fields.get("source", "ai"),
                    fields.get("feedback"),
                ),
            )
            await conn.commit()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_do())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def _direct_insert_tutor_turn(
    session_id: str,
    hw_id: str,
    phase: str,
    role: str,
    content: str,
    question_id: str | None = None,
) -> None:
    """Insert a tutor_conversations row bypassing the route — useful for
    seeding state without firing AI mocks 60 times."""

    async def _do() -> None:
        async with aiosqlite.connect(_db_path()) as conn:
            await conn.execute(
                "INSERT INTO tutor_conversations "
                "(session_id, hw_id, phase, question_id, role, content, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
                (session_id, hw_id, phase, question_id, role, content),
            )
            await conn.commit()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_do())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def _create_then_set_content(client, content_json: dict) -> str:
    """POST a minimal homework, then PUT the desired content_json. The create
    route doesn't accept a `content_json` field, but the update route does."""
    create_resp = client.post(
        "/api/homeworks",
        json={
            "title": "Tutor F1 test HW",
            "subject": "math-algebra",
            "grade": 8,
            "mode": "hard",
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    hw_id = create_resp.json()["id"]
    put_resp = client.put(f"/api/homeworks/{hw_id}", json={"content_json": content_json})
    assert put_resp.status_code == 200, put_resp.text
    return hw_id


def _make_homework_with_question(client, *, expected: str = "") -> str:
    """Create a homework whose content_json carries one boss question with the
    given `expected` answer. Returns the new hw_id."""
    content = {
        "boss_questions": [
            {
                "question_id": "qb1",
                "q": "Solve: x + 5 = 12",
                "answer_spec": {"type": "numeric", "expected": expected},
                "ans": [expected],
                "accepted_answers": [expected],
                "dmg": 10,
                "tags": "[Bloom: L2]",
            }
        ],
    }
    return _create_then_set_content(client, content)


def _make_homework_with_boss_pool(client, qids: list[str]) -> str:
    """Create a homework with N boss questions identified by `qids`."""
    content = {
        "boss_questions": [
            {
                "question_id": qid,
                "q": f"Question {qid}",
                "answer_spec": {"type": "numeric", "expected": 1},
                "dmg": 10,
            }
            for qid in qids
        ],
    }
    return _create_then_set_content(client, content)


def _select_turns(session_id: str, hw_id: str) -> list[dict]:
    async def _do() -> list[dict]:
        async with aiosqlite.connect(_db_path()) as conn:
            conn.row_factory = aiosqlite.Row
            cur = await conn.execute(
                "SELECT role, content, question_id, phase, created_at "
                "FROM tutor_conversations "
                "WHERE session_id = ? AND hw_id = ? "
                "ORDER BY id ASC",
                (session_id, hw_id),
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_do())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


@pytest.fixture(autouse=True)
def clean_tutor_tables():
    _wipe_tutor_tables()
    yield


# ---------------------------------------------------------------------------
# 1. preview chat persists user + assistant turns
# ---------------------------------------------------------------------------


@patch("server.services.gemini.generate")
def test_preview_chat_persists_turns(mock_generate, client):
    mock_generate.return_value = "Mitoz — bu hujayra bo'linish jarayoni."
    hw_id = _make_homework_with_question(client)
    payload = {
        "session_id": "sess-preview-1",
        "hw_id": hw_id,
        "phase": "preview",
        "message": "Mitoz nima?",
    }
    resp = client.post("/api/ai/tutor/chat", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["response"] == "Mitoz — bu hujayra bo'linish jarayoni."
    assert isinstance(data["message_id"], int) and data["message_id"] > 0

    turns = _select_turns("sess-preview-1", hw_id)
    assert len(turns) == 2
    assert turns[0]["role"] == "user"
    assert turns[0]["content"] == "Mitoz nima?"
    assert turns[1]["role"] == "assistant"
    assert turns[1]["content"] == "Mitoz — bu hujayra bo'linish jarayoni."


# ---------------------------------------------------------------------------
# 2. CRITICAL: practice phase does NOT leak the answer into the LLM prompt
# ---------------------------------------------------------------------------


@patch("server.services.gemini.generate")
def test_practice_no_answer_leak(mock_generate, client):
    """Set expected="MAGIC_TOKEN_42" on the question. Capture the prompt the
    tutor service hands to gemini.generate and assert MAGIC_TOKEN_42 is NOT in it.

    We also stub gemini.generate's return value to contain MAGIC_TOKEN_42 — the
    test must still pass because we only protect *input* (the prompt is the
    safety surface). Output filtering is intentionally out of scope.
    """
    captured: dict[str, str] = {}

    def _fake_generate(prompt: str, *args, **kwargs):
        captured["prompt"] = prompt
        return "Of course the answer is MAGIC_TOKEN_42 [intentional output leak]"

    mock_generate.side_effect = _fake_generate

    hw_id = _make_homework_with_question(client, expected="MAGIC_TOKEN_42")
    payload = {
        "session_id": "sess-leak",
        "hw_id": hw_id,
        "phase": "practice",
        "question_id": "qb1",
        "message": "What's the answer?",
    }
    resp = client.post("/api/ai/tutor/chat", json=payload)
    assert resp.status_code == 200, resp.text

    captured_prompt = captured.get("prompt", "")
    assert captured_prompt, "gemini.generate was never called"
    assert "MAGIC_TOKEN_42" not in captured_prompt, (
        "Answer-leak guard failed: MAGIC_TOKEN_42 ended up in the LLM prompt.\n"
        f"Prompt:\n{captured_prompt[:1000]}"
    )

    # The (deliberately leaky) response is returned untouched — this is the
    # documented behavior. Output filtering is not F1's job.
    assert "MAGIC_TOKEN_42" in resp.json()["response"]


# ---------------------------------------------------------------------------
# 3. practice chat: tutor's response is passed through
# ---------------------------------------------------------------------------


@patch("server.services.gemini.generate")
def test_practice_response_passthrough(mock_generate, client):
    mock_generate.return_value = "Try isolating x first"
    hw_id = _make_homework_with_question(client, expected="7")
    payload = {
        "session_id": "sess-passthrough",
        "hw_id": hw_id,
        "phase": "practice",
        "question_id": "qb1",
        "message": "How do I solve x + 5 = 12?",
    }
    resp = client.post("/api/ai/tutor/chat", json=payload)
    assert resp.status_code == 200, resp.text
    assert resp.json()["response"] == "Try isolating x first"


# ---------------------------------------------------------------------------
# 4. boss-plan basic — valid LLM plan covers every question_id exactly once
# ---------------------------------------------------------------------------


@patch("server.services.gemini.generate_json")
def test_boss_plan_basic(mock_generate_json, client):
    qids = ["qa", "qb", "qc"]
    hw_id = _make_homework_with_boss_pool(client, qids)
    mock_generate_json.return_value = {
        "ordered": [
            {"question_id": "qb", "framing_text": "Warm-up first."},
            {"question_id": "qa", "framing_text": "Now ramp it up."},
            {"question_id": "qc", "framing_text": "Final boss."},
        ],
        "persona_traits": ["challenger"],
    }
    resp = client.post(
        "/api/ai/tutor/boss-plan",
        json={"session_id": "sess-boss-basic", "hw_id": hw_id},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert {entry["question_id"] for entry in data["ordered"]} == set(qids)
    assert len(data["ordered"]) == 3
    assert data["persona_traits"] == ["challenger"]


# ---------------------------------------------------------------------------
# 5. boss-plan fallback — invalid LLM plan triggers default ordering
# ---------------------------------------------------------------------------


@patch("server.services.gemini.generate_json")
def test_boss_plan_invalid_falls_back(mock_generate_json, client):
    qids = ["qx", "qy", "qz"]
    hw_id = _make_homework_with_boss_pool(client, qids)
    # Missing "qz" — should fail validation and trigger default fallback.
    mock_generate_json.return_value = {
        "ordered": [
            {"question_id": "qx", "framing_text": "ok"},
            {"question_id": "qy", "framing_text": "ok"},
        ],
        "persona_traits": ["challenger"],
    }
    resp = client.post(
        "/api/ai/tutor/boss-plan",
        json={"session_id": "sess-boss-invalid", "hw_id": hw_id},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # Default fallback preserves input order + uses "mentor" persona.
    assert [e["question_id"] for e in data["ordered"]] == qids
    assert data["persona_traits"] == ["mentor"]
    for entry in data["ordered"]:
        assert isinstance(entry["framing_text"], str) and entry["framing_text"]


# ---------------------------------------------------------------------------
# 6. history endpoint — chronological turns
# ---------------------------------------------------------------------------


def test_history_returns_chronological_turns(client):
    sess = "sess-history"
    hw_id = "HW-FAKE-1"
    _direct_insert_tutor_turn(sess, hw_id, "preview", "user", "first")
    _direct_insert_tutor_turn(sess, hw_id, "preview", "assistant", "second")
    _direct_insert_tutor_turn(sess, hw_id, "practice", "user", "third")

    resp = client.get("/api/ai/tutor/history", params={"session_id": sess, "hw_id": hw_id})
    assert resp.status_code == 200, resp.text
    turns = resp.json()["turns"]
    assert len(turns) == 3
    assert [t["content"] for t in turns] == ["first", "second", "third"]
    assert [t["role"] for t in turns] == ["user", "assistant", "user"]


# ---------------------------------------------------------------------------
# 7. cross-session isolation
# ---------------------------------------------------------------------------


def test_cross_session_isolation(client):
    hw_id = "HW-FAKE-2"
    _direct_insert_tutor_turn("sess-A", hw_id, "preview", "user", "alice msg")
    _direct_insert_tutor_turn("sess-A", hw_id, "preview", "assistant", "alice reply")

    resp = client.get("/api/ai/tutor/history", params={"session_id": "sess-B", "hw_id": hw_id})
    assert resp.status_code == 200, resp.text
    assert resp.json()["turns"] == []


# ---------------------------------------------------------------------------
# 8. session message cap — 61st POST returns 429
# ---------------------------------------------------------------------------


@patch("server.services.gemini.generate")
def test_session_message_cap_returns_429(mock_generate, client):
    mock_generate.return_value = "ok"
    hw_id = _make_homework_with_question(client)
    sess = "sess-cap"
    # Seed exactly 60 turns directly so we don't have to fire the route 60 times.
    for i in range(60):
        _direct_insert_tutor_turn(sess, hw_id, "preview", "user", f"msg {i}")

    payload = {
        "session_id": sess,
        "hw_id": hw_id,
        "phase": "preview",
        "message": "one over the line",
    }
    resp = client.post("/api/ai/tutor/chat", json=payload)
    assert resp.status_code == 429, resp.text
    detail = resp.json().get("detail", {})
    if isinstance(detail, dict):
        assert detail.get("code") == "TUTOR_SESSION_CAP"


# ---------------------------------------------------------------------------
# 9. tutor sees prior attempts when tutor_attempts exists
# ---------------------------------------------------------------------------


@patch("server.services.gemini.generate")
def test_prior_attempts_reach_prompt(mock_generate, client):
    captured: dict[str, str] = {}

    def _fake_generate(prompt: str, *args, **kwargs):
        captured["prompt"] = prompt
        return "Let's break it down."

    mock_generate.side_effect = _fake_generate

    hw_id = _make_homework_with_question(client, expected="7")
    sess = "sess-attempts"

    _create_tutor_attempts_table()
    _insert_tutor_attempt(
        session_id=sess,
        hw_id=hw_id,
        question_id="qb1",
        phase="practice",
        student_answer="5 km",
        verdict="incorrect",
        source="deterministic",
    )
    _insert_tutor_attempt(
        session_id=sess,
        hw_id=hw_id,
        question_id="qb1",
        phase="practice",
        student_answer="5000",
        verdict="unsure",
        source="ai",
        feedback="missing context",
    )

    payload = {
        "session_id": sess,
        "hw_id": hw_id,
        "phase": "practice",
        "question_id": "qb1",
        "message": "What did I do wrong?",
    }
    resp = client.post("/api/ai/tutor/chat", json=payload)
    assert resp.status_code == 200, resp.text

    prompt = captured.get("prompt", "")
    assert "5 km" in prompt, f"prior attempt #1 missing from prompt:\n{prompt[:600]}"
    assert "5000" in prompt, f"prior attempt #2 missing from prompt:\n{prompt[:600]}"
    # The section is injected as "STUDENT_PRIOR_ATTEMPTS_ON_THIS_QUESTION:\n- ..."
    # — the colon+newline+dash is what distinguishes the *injected* section from
    # the literal {STUDENT_PRIOR_ATTEMPTS_ON_THIS_QUESTION} placeholder reference
    # inside the system prompt MD.
    assert "STUDENT_PRIOR_ATTEMPTS_ON_THIS_QUESTION:\n-" in prompt


# ---------------------------------------------------------------------------
# 10. graceful missing-table fallback
# ---------------------------------------------------------------------------


@patch("server.services.gemini.generate")
def test_missing_tutor_attempts_table_is_graceful(mock_generate, client):
    """Pre-merge with the grading lane: tutor_attempts may not exist yet.
    We must NOT crash; the prompt should simply omit the attempts section."""
    captured: dict[str, str] = {}

    def _fake_generate(prompt: str, *args, **kwargs):
        captured["prompt"] = prompt
        return "Sure, here's how to think about it."

    mock_generate.side_effect = _fake_generate

    # _wipe_tutor_tables already drops tutor_attempts — confirm it's gone.
    conn = sqlite3.connect(_db_path())
    try:
        cur = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='tutor_attempts'"
        )
        assert cur.fetchone() is None, "tutor_attempts must NOT exist for this test"
    finally:
        conn.close()

    hw_id = _make_homework_with_question(client, expected="42")
    payload = {
        "session_id": "sess-missing-table",
        "hw_id": hw_id,
        "phase": "practice",
        "question_id": "qb1",
        "message": "Help?",
    }
    resp = client.post("/api/ai/tutor/chat", json=payload)
    assert resp.status_code == 200, resp.text

    prompt = captured.get("prompt", "")
    # Same convention as test #9: the *injected* section is "...:\n- " — the
    # placeholder-reference inside the system prompt MD is a different shape.
    assert "STUDENT_PRIOR_ATTEMPTS_ON_THIS_QUESTION:\n-" not in prompt, (
        "Attempts section leaked into prompt despite empty attempts list"
    )


# ---------------------------------------------------------------------------
# 11. screen_context reaches the LLM prompt as PREVIEW_CONTEXT
# ---------------------------------------------------------------------------


@patch("server.services.gemini.generate")
def test_tutor_chat_accepts_screen_context(mock_generate, client):
    """screen_context sent from the client must appear in the prompt under
    the PREVIEW_CONTEXT: heading so the tutor can reference on-screen text."""
    captured: dict[str, str] = {}

    def _fake_generate(prompt: str, *args, **kwargs):
        captured["prompt"] = prompt
        return "Here is what the summary panel says."

    mock_generate.side_effect = _fake_generate

    hw_id = _make_homework_with_question(client)
    screen_text = "Photosynthesis converts light energy into chemical energy stored as glucose."
    payload = {
        "session_id": "sess-screen-ctx",
        "hw_id": hw_id,
        "phase": "preview",
        "message": "What is written inside this summary panel?",
        "screen_context": screen_text,
    }
    resp = client.post("/api/ai/tutor/chat", json=payload)
    assert resp.status_code == 200, resp.text

    prompt = captured.get("prompt", "")
    assert "PREVIEW_CONTEXT:" in prompt, "PREVIEW_CONTEXT: section missing from prompt"
    assert screen_text in prompt, "screen_context text not found in prompt"


# ---------------------------------------------------------------------------
# 12. oversized screen_context is truncated to 2000 chars server-side
# ---------------------------------------------------------------------------


@patch("server.services.gemini.generate")
def test_tutor_chat_truncates_long_screen_context(mock_generate, client):
    """A 5000-char screen_context must be capped at 2000 chars in the prompt."""
    captured: dict[str, str] = {}

    def _fake_generate(prompt: str, *args, **kwargs):
        captured["prompt"] = prompt
        return "Got it."

    mock_generate.side_effect = _fake_generate

    hw_id = _make_homework_with_question(client)
    long_context = "A" * 5000
    payload = {
        "session_id": "sess-truncate",
        "hw_id": hw_id,
        "phase": "preview",
        "message": "Summarise the screen.",
        "screen_context": long_context,
    }
    resp = client.post("/api/ai/tutor/chat", json=payload)
    assert resp.status_code == 200, resp.text

    prompt = captured.get("prompt", "")
    assert "PREVIEW_CONTEXT:" in prompt, "PREVIEW_CONTEXT: section missing from prompt"
    # The section injected is "PREVIEW_CONTEXT:\n<context>"; find its content.
    marker = "PREVIEW_CONTEXT:\n"
    idx = prompt.index(marker)
    context_slice = prompt[idx + len(marker):]
    # The slice ends at the next "\n" separator or end of string.
    next_section = context_slice.find("\n")
    injected = context_slice if next_section == -1 else context_slice[:next_section]
    assert len(injected) <= 2000, (
        f"PREVIEW_CONTEXT section is {len(injected)} chars, expected ≤ 2000"
    )


# ---------------------------------------------------------------------------
# 13. Wave K — system prompt locks in the Opus 4.7 tone keywords
# ---------------------------------------------------------------------------


def test_tutor_assistant_prompt_locks_in_tone_rules():
    """The tutor-assistant.md system prompt MUST contain the Wave K tone
    keywords so the live tutor speaks expert-confident + brief + register-
    mirroring instead of formal-professor mode.

    This is a content-lock test: if someone deletes the new tone section in a
    later refactor, this fails loudly so the voice doesn't silently regress.
    """
    from server.config import PROMPTS_DIR

    prompt_path = PROMPTS_DIR / "runtime" / "tutor-assistant.md"
    assert prompt_path.exists(), f"tutor-assistant.md not found at {prompt_path}"
    text = prompt_path.read_text(encoding="utf-8")

    required_markers = [
        "Expert-confident",       # core voice descriptor
        "1-2 sentences",          # brevity rule
        "Mirror",                 # register mirroring (matches both "Mirror" and "Mirrors")
        "tushuntir batafsil",     # explicit "expand" trigger phrase in Uzbek
        "DO / DON",               # tone examples block (DO / DON'T)
        "Slur",                   # slur handling section header
        "naughty",                # tone descriptor for callout style
        "back-prompt",            # soft follow-up rule
        "{PHASE}",                # variable references block present
        "{STUDENT_MESSAGE}",      # variable references block present
    ]
    missing = [m for m in required_markers if m not in text]
    assert not missing, f"Wave K tone markers missing from tutor-assistant.md: {missing}"
