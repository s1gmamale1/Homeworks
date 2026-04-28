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
  9. screen_context reaches LLM prompt as PREVIEW_CONTEXT
 10. oversized screen_context is truncated to 2000 chars server-side
 11. Wave K — system prompt locks in Opus 4.7 tone keywords
 12. Wave F — math subjects use PRO_MODEL to avoid hallucinations
 13. Wave F — non-math subjects use FAST_MODEL for cost efficiency

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


@patch("server.services.gemini.generate")
def test_practice_no_answer_alias_leak_from_answer_spec(mock_generate, client):
    """Some editor/importer shapes store the answer in `canonical_display`,
    `answer`, or `matched_expected`, not only `expected`. Practice prompts
    must strip those aliases too."""
    captured: dict[str, str] = {}

    def _fake_generate(prompt: str, *args, **kwargs):
        captured["prompt"] = prompt
        return "I can guide the method."

    mock_generate.side_effect = _fake_generate

    content = {
        "boss_questions": [
            {
                "question_id": "qb-alias",
                "q": "Solve the equation.",
                "answer_spec": {
                    "type": "text_fuzzy",
                    "expected": "LEAK_TOKEN_EXPECTED",
                    "canonical_display": "LEAK_TOKEN_CANONICAL",
                    "answer": "LEAK_TOKEN_ANSWER",
                    "matched_expected": "LEAK_TOKEN_MATCHED",
                },
                "answer": "LEAK_TOKEN_TOPLEVEL",
                "a": "LEAK_TOKEN_A",
                "accepted_answers": ["LEAK_TOKEN_ACCEPTED"],
            }
        ],
    }
    hw_id = _create_then_set_content(client, content)

    resp = client.post(
        "/api/ai/tutor/chat",
        json={
            "session_id": "sess-alias-leak",
            "hw_id": hw_id,
            "phase": "practice",
            "question_id": "qb-alias",
            "message": "Help me solve it.",
        },
    )
    assert resp.status_code == 200, resp.text

    prompt = captured.get("prompt", "")
    assert prompt
    for token in (
        "LEAK_TOKEN_EXPECTED",
        "LEAK_TOKEN_CANONICAL",
        "LEAK_TOKEN_ANSWER",
        "LEAK_TOKEN_MATCHED",
        "LEAK_TOKEN_TOPLEVEL",
        "LEAK_TOKEN_A",
        "LEAK_TOKEN_ACCEPTED",
    ):
        assert token not in prompt, f"{token} leaked into prompt:\n{prompt[:1000]}"


@patch("server.services.gemini.generate")
def test_practice_no_nested_answer_leak(mock_generate, client):
    """Redaction should be recursive: answers can appear in nested lists/dicts
    such as options[], fields[], or rubrics from imported content."""
    captured: dict[str, str] = {}

    def _fake_generate(prompt: str, *args, **kwargs):
        captured["prompt"] = prompt
        return "Look at the structure first."

    mock_generate.side_effect = _fake_generate

    content = {
        "gb_adaptive_quiz": [
            {
                "id": "aq-nested",
                "prompt": "Pick the correct option.",
                "options": [
                    {"label": "A", "text": "Wrong"},
                    {"label": "B", "text": "Visible option B", "correct": True},
                ],
                "fields": [
                    {"label": "Step", "acceptable": ["LEAK_TOKEN_FIELD"]},
                ],
                "rubric": {"answer": "LEAK_TOKEN_RUBRIC"},
            }
        ],
    }
    hw_id = _create_then_set_content(client, content)

    resp = client.post(
        "/api/ai/tutor/chat",
        json={
            "session_id": "sess-nested-leak",
            "hw_id": hw_id,
            "phase": "practice",
            "question_id": "aq-nested",
            "message": "Which option is right?",
        },
    )
    assert resp.status_code == 200, resp.text

    prompt = captured.get("prompt", "")
    assert prompt
    assert "QUESTION_CONTEXT:" in prompt
    assert "Pick the correct option." in prompt
    assert "Wrong" in prompt
    assert "Visible option B" in prompt
    assert "Step" in prompt
    for token in ("LEAK_TOKEN_FIELD", "LEAK_TOKEN_RUBRIC"):
        assert token not in prompt, f"{token} leaked into prompt:\n{prompt[:1000]}"
    assert '"correct"' not in prompt
    assert '"acceptable"' not in prompt
    assert '"answer"' not in prompt


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
    _direct_insert_tutor_turn("sess-A-alice", hw_id, "preview", "user", "alice msg")
    _direct_insert_tutor_turn("sess-A-alice", hw_id, "preview", "assistant", "alice reply")

    resp = client.get("/api/ai/tutor/history", params={"session_id": "sess-B-bob", "hw_id": hw_id})
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
# 9. screen_context reaches the LLM prompt as PREVIEW_CONTEXT
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
# 10. oversized screen_context is truncated to 2000 chars server-side
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
# 11. Wave K — system prompt locks in the Opus 4.7 tone keywords
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


# ---------------------------------------------------------------------------
# 12. Wave F: math subjects use PRO_MODEL to avoid hallucinations
# ---------------------------------------------------------------------------


@patch("server.services.gemini.generate")
def test_tutor_chat_uses_pro_model_for_math(mock_generate, client):
    """Math subjects must use PRO_MODEL for deeper reasoning to avoid hallucinations."""
    captured: dict[str, str] = {}

    def _fake_generate(prompt: str, model: str = None, **kwargs):
        captured["model"] = model
        return "Try factoring both sides."

    mock_generate.side_effect = _fake_generate

    # _make_homework_with_question creates with math-algebra by default
    hw_id = _make_homework_with_question(client, expected="7")
    payload = {
        "session_id": "sess-math-pro",
        "hw_id": hw_id,
        "phase": "practice",
        "question_id": "qb1",
        "message": "How do I solve this?",
    }
    resp = client.post("/api/ai/tutor/chat", json=payload)
    assert resp.status_code == 200, resp.text

    model = captured.get("model")
    from server.services import gemini
    assert model == gemini.PRO_MODEL, (
        f"math-algebra should use PRO_MODEL, got {model}"
    )


@patch("server.services.gemini.generate")
def test_tutor_chat_uses_fast_model_for_non_math(mock_generate, client):
    """Non-math subjects like English use FAST_MODEL for cost efficiency."""
    captured: dict[str, str] = {}

    def _fake_generate(prompt: str, model: str = None, **kwargs):
        captured["model"] = model
        return "Good question!"

    mock_generate.side_effect = _fake_generate

    # Create homework with English subject (not math-algebra)
    content = {
        "boss_questions": [
            {
                "question_id": "qb1",
                "q": "What is the meaning of serendipity?",
                "answer_spec": {"type": "text_fuzzy", "expected": "answer"},
                "ans": ["answer"],
                "accepted_answers": ["answer"],
                "dmg": 10,
                "tags": "[Bloom: L1]",
            }
        ],
    }
    create_resp = client.post(
        "/api/homeworks",
        json={
            "title": "English test HW",
            "subject": "english",
            "grade": 8,
            "mode": "hard",
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    hw_id = create_resp.json()["id"]
    put_resp = client.put(f"/api/homeworks/{hw_id}", json={"content_json": content})
    assert put_resp.status_code == 200, put_resp.text

    payload = {
        "session_id": "sess-english-fast",
        "hw_id": hw_id,
        "phase": "practice",
        "question_id": "qb1",
        "message": "What does this mean?",
    }
    resp = client.post("/api/ai/tutor/chat", json=payload)
    assert resp.status_code == 200, resp.text

    model = captured.get("model")
    from server.services import gemini
    assert model == gemini.FAST_MODEL, (
        f"english should use FAST_MODEL, got {model}"
    )
