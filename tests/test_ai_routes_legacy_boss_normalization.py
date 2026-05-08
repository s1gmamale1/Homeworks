"""Regression tests for legacy ``boss`` → ``boss_questions`` fallback in ai.py.

Pre-fix, the AI route helpers ``_extract_boss_questions`` and
``_fb_find_boss_question`` only read ``content_json["boss_questions"]``.
Legacy homework rows that pre-date the schema migration store the array
under the bare ``boss`` key — those rows hit every AI boss endpoint with
empty arrays / ``FB_Q_NOT_FOUND`` 404s even though the questions exist.

The compat layer at ``server.services.content_json_compat`` already
mirrors ``boss`` → ``boss_questions`` on the GET / render path (PR #202),
but ai.py calls ``db.get_homework`` directly and never runs normalization.
The minimal fix is a fallback inside the two helpers themselves.

These tests pin the new behavior at the helper layer: they operate on
raw dicts (no DB / mock plumbing) so the boss-key bypass is verified
deterministically. Designed to FAIL on commit ``43a25e0`` (the pre-fix
tip of origin/server) and PASS on the fix commit.
"""
from __future__ import annotations

import server.routes.ai as _ai_routes


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _legacy_boss_content() -> dict:
    """A content_json shaped like a pre-v2 row: bare ``boss`` array, no
    ``boss_questions`` key. Authored ids are present so the helpers can
    locate questions deterministically.
    """
    return {
        "meta": {"title": "Legacy boss row"},
        "boss": [
            {
                "id": "bq_legacy_a",
                "q": "Find x.",
                "ans": ["3"],
                "accepted_answers": ["3"],
                "answer_spec": {"kind": "equality", "expected": ["3"]},
            },
            {
                "id": "bq_legacy_b",
                "q": "Then y?",
                "ans": ["7"],
                "accepted_answers": ["7"],
                "answer_spec": {"kind": "equality", "expected": ["7"]},
            },
        ],
    }


def _legacy_boss_no_ids_content() -> dict:
    """Legacy ``boss`` array whose items have no authored ``id``.

    The synthetic ``bq_{i}`` form is what the runtime emits, so the
    helpers must accept that lookup form for legacy rows too.
    """
    return {
        "meta": {"title": "Legacy boss, no ids"},
        "boss": [
            {"q": "Q1", "ans": ["A"]},
            {"q": "Q2", "ans": ["B"]},
        ],
    }


# ---------------------------------------------------------------------------
# _extract_boss_questions — Test 1
# ---------------------------------------------------------------------------


def test_extract_boss_questions_falls_back_to_legacy_boss_key():
    """A homework with ONLY the legacy ``boss`` key (and no
    ``boss_questions`` mirror) must surface its questions through
    ``_extract_boss_questions``. Pre-fix, this returned ``[]`` and the
    boss-plan endpoint shipped an empty plan to the LLM.
    """
    content = _legacy_boss_content()
    out = _ai_routes._extract_boss_questions(content)
    assert isinstance(out, list)
    assert len(out) == 2
    assert out[0]["q"] == "Find x."
    assert out[1]["q"] == "Then y?"


def test_extract_boss_questions_modern_key_takes_precedence():
    """When BOTH keys are present, the modern ``boss_questions`` wins —
    the legacy fallback only triggers when the modern key is missing.
    """
    content = {
        "boss": [{"q": "Legacy"}],
        "boss_questions": [{"q": "Modern"}],
    }
    out = _ai_routes._extract_boss_questions(content)
    assert len(out) == 1
    assert out[0]["q"] == "Modern"


def test_extract_boss_questions_no_boss_keys_returns_empty():
    """A homework with neither key returns an empty list — unchanged
    from the pre-fix behavior.
    """
    assert _ai_routes._extract_boss_questions({}) == []
    assert _ai_routes._extract_boss_questions({"boss": "not a list"}) == []
    assert _ai_routes._extract_boss_questions({"boss_questions": None}) == []


# ---------------------------------------------------------------------------
# _fb_find_boss_question — Test 2
# ---------------------------------------------------------------------------


def test_fb_find_boss_question_finds_by_authored_id_in_legacy_boss():
    """``_fb_find_boss_question`` must locate a question by its authored
    ``id`` even when the array lives under the legacy ``boss`` key.
    Pre-fix this returned ``None`` and the FB check-answer endpoint
    raised ``FB_Q_NOT_FOUND`` on every legacy homework.
    """
    content = _legacy_boss_content()
    q = _ai_routes._fb_find_boss_question(content, "bq_legacy_a")
    assert q is not None
    assert q["q"] == "Find x."
    assert q["ans"] == ["3"]


def test_fb_find_boss_question_finds_by_synthetic_index_in_legacy_boss():
    """Legacy rows whose questions lack an authored ``id`` are looked up
    by the synthetic ``bq_{i}`` form the runtime emits.
    """
    content = _legacy_boss_no_ids_content()
    first = _ai_routes._fb_find_boss_question(content, "bq_0")
    second = _ai_routes._fb_find_boss_question(content, "bq_1")
    assert first is not None and first["q"] == "Q1"
    assert second is not None and second["q"] == "Q2"


def test_fb_find_boss_question_modern_key_takes_precedence():
    """When both keys exist, the lookup hits ``boss_questions`` first;
    the legacy ``boss`` array is only consulted when the modern key is
    missing or non-list.
    """
    content = {
        "boss": [{"id": "x", "q": "Legacy"}],
        "boss_questions": [{"id": "x", "q": "Modern"}],
    }
    q = _ai_routes._fb_find_boss_question(content, "x")
    assert q is not None
    assert q["q"] == "Modern"


def test_fb_find_boss_question_returns_none_when_id_absent():
    """Unknown ids still return ``None`` — fallback only changes which
    array is searched, not the not-found semantics.
    """
    content = _legacy_boss_content()
    assert _ai_routes._fb_find_boss_question(content, "no-such-id") is None
    assert _ai_routes._fb_find_boss_question({}, "anything") is None
    assert _ai_routes._fb_find_boss_question(_legacy_boss_content(), "") is None


# ---------------------------------------------------------------------------
# Test 3 — pre-fix anchor.
# ---------------------------------------------------------------------------


def test_fix_anchor_legacy_boss_key_returns_questions():
    """Anchor test that combines both helpers on a single legacy row.

    This test was designed to FAIL on commit ``43a25e0`` (the pre-fix
    tip of origin/server) and PASS on the fix commit. If you are
    running this on origin/server and it passes, the fallback was
    silently merged via another path — re-audit before deleting.
    """
    content = _legacy_boss_content()

    # Both helpers must agree on the legacy row.
    extracted = _ai_routes._extract_boss_questions(content)
    located = _ai_routes._fb_find_boss_question(content, "bq_legacy_b")

    assert len(extracted) == 2, (
        "_extract_boss_questions returned an empty list for a legacy "
        "row — the boss-plan endpoint would ship an empty plan to the "
        "LLM, defeating Wave F1's per-session boss planning."
    )
    assert located is not None, (
        "_fb_find_boss_question returned None for a legacy row — the "
        "FB check-answer endpoint would raise FB_Q_NOT_FOUND 404 on "
        "every submission against this homework."
    )
    assert located["q"] == "Then y?"
