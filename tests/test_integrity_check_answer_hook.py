"""G1 — the anti-cheat engine now runs on the /api/ai/check-answer surface.

Before this hook, the integrity engine + signal ingestion + soft-friction
nudge only ran inside ``tutor.process_runtime_answer`` (the tutor runtime) and
the boss path. BUT the v2 React runtime submits CBP checkpoints, CBP reasoning,
Memory Check and the 8 games to ``POST /api/ai/check-answer`` — which dispatches
to dedicated ``_check_answer_<phase>`` handlers that never touch
``process_runtime_answer``. So the engine did NOT run for those phases.

This test pins the coverage fix: a ``case_based_preview_reasoning`` submit on
``/api/ai/check-answer`` that trips ``sudden_mastery`` (low pre-mastery, then a
near-perfect assessment rate over >= 3 items) MUST:
  - enroll a ``kind='integrity'`` review-queue row (reason ``sudden_mastery``),
  - carry an ``integrity_nudge`` on the response,
WHILE the graded ``passed`` / ``score`` fields are byte-identical to the
non-flagged baseline (ADVISORY-only — the flag never alters grading).

The AI grader is mocked RLC-style (``_grade_cbp_reasoning``) so no live provider
is hit; grading is fully deterministic.
"""
from __future__ import annotations

import asyncio
import json
import os
from unittest.mock import patch

import aiosqlite

import server.routes.ai as _ai_routes
from server.db import attempts_repo, session_metrics_repo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


# Keyword buckets: concept="force", method="diagram", mistake="friction".
_DPE = {
    "prompt": "Explain which concept applies, why this method, and the mistake to avoid.",
    "min_chars": 80,
    "concept_keywords": ["force"],
    "method_keywords": ["diagram"],
    "mistake_keywords": ["friction"],
    "pass_score": 60,
}

# A long reasoning text (>= min_chars) that hits all three keyword buckets so
# det_count == 3 → passes the AND-gate when the (mocked) AI score is high.
_LONG_THREE = (
    "The key concept here is force balance, and I would use a free body diagram "
    "to lay out every push and pull acting on the block before solving, while "
    "avoiding the common friction mistake by accounting for it carefully."
)


def _seed_cbp_reasoning_hw(client, *, hint: str) -> str:
    payload = {
        "title": f"Integrity check-answer hook HW ({hint})",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
        "family": "aniq-fanlar",
        "content_json": {
            "meta": {"title": f"Integrity check-answer hook HW ({hint})"},
            "subject": "math-algebra",
            "grade": 8,
            "case_based_preview": {
                "case_setup": {"story": "A block on a ramp", "role": "physicist", "task": "explain"},
                "checkpoints": [],
                "decision_process_explanation": _DPE,
            },
        },
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _seed_low_mastery(session_id: str, hw_id: str) -> None:
    """Seed all-wrong NON-assessment practice attempts → low mastery_score.

    These are phase='practice' (assessment=False under the AI-use policy), so
    they drag the persisted ``mastery_score`` below the sudden-mastery pre-ceiling
    WITHOUT counting toward the assessment correct-rate.
    """

    async def go():
        for i in range(3):
            await attempts_repo.add_phase_attempt(
                session_id=session_id, hw_id=hw_id,
                phase="practice", subphase="sentence-fill",
                question_id=f"prac{i}", checker_source="ai_judge",
                correct=0, score=0.1, confidence=0.9, feedback="not quite",
            )
        await session_metrics_repo.recompute_session_metrics(session_id, hw_id)

    _run(go())


def _integrity_rows(session_id: str):
    db_path = os.environ.get("NETS_DB_PATH")

    async def _do():
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM review_queue WHERE kind = 'integrity' AND session_id = ?",
                (session_id,),
            )
            return [dict(r) for r in await cur.fetchall()]

    return _run(_do())


def _post_reasoning(client, hw_id: str, session_id: str, *, qid: str):
    body = {
        "phase": "case_based_preview_reasoning",
        "homework_id": hw_id,
        "session_id": session_id,
        "question_id": qid,
        "reasoning_text": _LONG_THREE,
    }
    return client.post("/api/ai/check-answer", json=body)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_check_answer_reasoning_sudden_mastery_enrolls_flag_and_nudges(client):
    """A sudden_mastery scenario reached via /api/ai/check-answer (NOT the tutor
    runtime) enrolls an integrity row AND surfaces an integrity_nudge — proving
    the engine now covers the v2 check-answer phases (G1)."""
    hw_id = _seed_cbp_reasoning_hw(client, hint="enroll")
    sess = "ca-hook-enroll-001"
    _seed_low_mastery(sess, hw_id)

    async def _fake_high(*a, **k):
        return (95, "Tushuncha va usulni aniq ko'rsatdingiz.")

    last = None
    with patch.object(_ai_routes, "_grade_cbp_reasoning", new=_fake_high):
        # Three correct reasoning submits → assessment correct-rate 1.0 over 3
        # items; pre-mastery is low → sudden_mastery (strong) fires by the 3rd.
        for i in range(3):
            r = _post_reasoning(client, hw_id, sess, qid=f"cbp_reasoning_{i}")
            assert r.status_code == 200, r.text
            last = r.json()

    # The engine ran on the check-answer surface and enrolled an advisory row.
    rows = _integrity_rows(sess)
    assert rows, "sudden_mastery via /check-answer must enroll a kind='integrity' row"
    reasons = {r["integrity_reason"] for r in rows}
    assert "sudden_mastery" in reasons, reasons
    sm = next(r for r in rows if r["integrity_reason"] == "sudden_mastery")
    assert sm["integrity_severity"] == "strong"
    assert sm["kind"] == "integrity"
    assert sm["student_answer"] == ""  # advisory rows carry no answer

    # The strong flag surfaced the soft-friction nudge on the response.
    assert "integrity_nudge" in last, last
    assert last["integrity_nudge"]["type"] == "explain_reasoning"


def test_check_answer_reasoning_flag_does_not_alter_grade(client):
    """ADVISORY-only proof: the flagged submit's passed/score is identical to a
    clean (non-flagged) baseline submit of the same answer."""
    hw_id = _seed_cbp_reasoning_hw(client, hint="advisory")

    async def _fake_high(*a, **k):
        return (95, "Tushuncha va usulni aniq ko'rsatdingiz.")

    # Baseline: a session that never seeds low mastery → sudden_mastery cannot
    # fire (no pre-mastery <= ceiling), so no flag, no nudge.
    base_sess = "ca-hook-base-001"
    with patch.object(_ai_routes, "_grade_cbp_reasoning", new=_fake_high):
        base = _post_reasoning(client, hw_id, base_sess, qid="cbp_reasoning_b").json()
    assert "integrity_nudge" not in base, base

    # Flagged: low pre-mastery + 3 correct assessment items → sudden_mastery.
    flag_sess = "ca-hook-flag-001"
    _seed_low_mastery(flag_sess, hw_id)
    flagged = None
    with patch.object(_ai_routes, "_grade_cbp_reasoning", new=_fake_high):
        for i in range(3):
            flagged = _post_reasoning(client, hw_id, flag_sess, qid=f"cbp_reasoning_f{i}").json()

    # The flag fired on the flagged session...
    assert "integrity_nudge" in flagged, flagged
    rows = _integrity_rows(flag_sess)
    assert any(r["integrity_reason"] == "sudden_mastery" for r in rows)

    # ...but the GRADE is byte-identical to the unflagged baseline. The signal
    # is teacher intelligence only — it never changes passed/score.
    assert flagged["passed"] == base["passed"] is True
    assert flagged["score"] == base["score"]
