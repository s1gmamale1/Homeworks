"""Reflection-analysis schema, hydration redaction, and gate completion flags.

Three contracts, one regression file (BE-Schema lane of the v3 reflection swarm):

1. **Schema** — `ReflectionAnalysis` is additive + permissive: the student-visible
   debrief fields and the server-only grading config both validate, and unknown
   keys are accepted (frozen-additive contract, CONTRACTS.md).
2. **Redaction** — the runtime redactor strips the server-only grading config
   (`analysis_rubric` / `weak_point_keywords` / `strong_point_keywords` /
   `pass_threshold`) from `reflection.analysis` BEFORE hydration, while the
   debrief fields (`narrative` / `weak_points` / `strong_points` / `next_steps`
   / `redo_recommendation`) SURVIVE — they are shown to the student.
3. **Gate** — `compute_gate_state` reports the additive completion flags
   (`practice_arc_completed`, `reflection_required`, `reflection_passed`,
   `all_divisions_complete`) without changing the existing return shape the
   React store consumes.

Style mirrors test_content_json_validation.py + test_runtime_hydration_redaction.py
+ test_v2_gate_flow.py. DB is the temp SQLite the `client` fixture inits; boss
attempts + the reflection mark are seeded through the repos via asyncio.run. No
provider is ever hit.
"""

import asyncio
import json

import pytest

from server.schemas.content import ContentJSON, ReflectionAnalysis, ReflectionPhase
from server.services.runtime_redactor import redact_for_runtime
from server.services.gate_state import compute_gate_state


# --------------------------------------------------------------------------- #
# 1. Schema — additive + permissive holds.
# --------------------------------------------------------------------------- #


def test_reflection_analysis_schema_accepts_extra_and_optional():
    """ReflectionAnalysis: every field optional, unknown keys allowed, and it
    nests under ReflectionPhase + ContentJSON without rejecting anything."""
    # Empty object validates (every field Optional).
    assert ReflectionAnalysis.model_validate({}) is not None

    full = {
        # student-visible debrief
        "narrative": "You moved fast on setup but slipped on the second step.",
        "weak_points": ["sign errors", "skipping the check step"],
        "strong_points": ["clear setup", "good units"],
        "next_steps": ["redo question 3", "review distributing negatives"],
        "redo_recommendation": "retry",
        # server-only grading config
        "analysis_rubric": {"weak": 2, "strong": 1},
        "weak_point_keywords": ["sign", "skip"],
        "strong_point_keywords": ["setup", "units"],
        "pass_threshold": 60,
        # an unknown key — frozen-ADDITIVE contract must accept it
        "future_field": {"anything": [1, 2, 3]},
    }
    model = ReflectionAnalysis.model_validate(full)
    assert model.narrative.startswith("You moved fast")
    assert model.weak_points == ["sign errors", "skipping the check step"]
    assert model.pass_threshold == 60
    # extra="allow" → unknown key survives on the model.
    assert model.model_dump().get("future_field") == {"anything": [1, 2, 3]}

    # Nests under the phase and the top-level blob.
    phase = ReflectionPhase.model_validate({"summary": "Done.", "analysis": full})
    assert phase.analysis is not None and phase.analysis.pass_threshold == 60

    cj = ContentJSON.model_validate({"reflection": {"analysis": full}})
    assert cj.reflection is not None
    assert cj.reflection.analysis is not None
    assert cj.reflection.analysis.weak_point_keywords == ["sign", "skip"]


# --------------------------------------------------------------------------- #
# 2. Redaction — server-only keys stripped, debrief fields survive.
# --------------------------------------------------------------------------- #

_VISIBLE_KEYS = (
    "narrative",
    "weak_points",
    "strong_points",
    "next_steps",
    "redo_recommendation",
)
_SERVER_ONLY_KEYS = (
    "analysis_rubric",
    "weak_point_keywords",
    "strong_point_keywords",
    "pass_threshold",
)


def test_hydration_strips_reflection_analysis_server_only_keys():
    """reflection.analysis: the grading config is stripped, the debrief survives.

    If this fails, the reflection rubric + keyword buckets + pass_threshold ship
    to the browser — a direct grading-anchor leak. Release blocker."""
    raw = {
        "reflection": {
            "summary": "Closing reflection.",
            "analysis": {
                # student-visible — must survive
                "narrative": "VISIBLE_NARRATIVE shown in the debrief.",
                "weak_points": ["VISIBLE_WEAK"],
                "strong_points": ["VISIBLE_STRONG"],
                "next_steps": ["VISIBLE_NEXT"],
                "redo_recommendation": "retry",
                # server-only — must be stripped
                "analysis_rubric": {"weak": "LEAK_RUBRIC"},
                "weak_point_keywords": ["LEAK_WEAK_KW"],
                "strong_point_keywords": ["LEAK_STRONG_KW"],
                "pass_threshold": 70,
            },
        }
    }
    safe = redact_for_runtime(raw, hw_id="HW-REFLECT-1")
    analysis = safe["reflection"]["analysis"]

    # Server-only grading config GONE at this nesting level.
    for k in _SERVER_ONLY_KEYS:
        assert k not in analysis, f"server-only reflection key survived hydration: {k}"

    # Debrief fields SURVIVE verbatim.
    assert analysis.get("narrative") == "VISIBLE_NARRATIVE shown in the debrief."
    assert analysis.get("weak_points") == ["VISIBLE_WEAK"]
    assert analysis.get("strong_points") == ["VISIBLE_STRONG"]
    assert analysis.get("next_steps") == ["VISIBLE_NEXT"]
    assert analysis.get("redo_recommendation") == "retry"

    # No grading-anchor value appears anywhere in the serialized payload.
    blob = json.dumps(safe)
    for tok in ("LEAK_RUBRIC", "LEAK_WEAK_KW", "LEAK_STRONG_KW"):
        assert tok not in blob, f"reflection grading anchor leaked: {tok}"
    # Visible content IS present.
    assert "VISIBLE_NARRATIVE shown in the debrief." in blob

    # Input is never mutated (server still reads the full object to grade).
    assert raw["reflection"]["analysis"]["pass_threshold"] == 70
    assert raw["reflection"]["analysis"]["analysis_rubric"] == {"weak": "LEAK_RUBRIC"}


# --------------------------------------------------------------------------- #
# 3. Gate — additive completion flags (DB-backed, via the temp SQLite).
# --------------------------------------------------------------------------- #


def _run(coro):
    return asyncio.run(coro)


def _make_v2_homework(client, *, with_reflection: bool):
    hw = client.post(
        "/api/homeworks",
        json={"title": "Reflection gate HW", "subject": "math-algebra", "grade": 6, "mode": "hard"},
    ).json()
    hw_id = hw["id"]
    content = {
        "flow_version": "v2",
        "meta": {"title": "Reflection gate HW"},
        "case_based_preview": {
            "checkpoints": [
                {"question": "Q1", "options": ["a", "b"], "answer_spec": {"type": "option_index", "expected": 1, "option_count": 2}},
                {"question": "Q2", "options": ["a", "b"], "answer_spec": {"type": "option_index", "expected": 0, "option_count": 2}},
                {"question": "Q3", "options": ["a", "b"], "answer_spec": {"type": "option_index", "expected": 1, "option_count": 2}},
            ],
        },
        "memory_check": {
            "pass_threshold_pct": 60,
            "items": [
                {"type": "mcq", "prompt": "M1", "options": ["x", "y"], "answer_spec": {"type": "option_index", "expected": 0, "option_count": 2}},
                {"type": "mcq", "prompt": "M2", "options": ["x", "y"], "answer_spec": {"type": "option_index", "expected": 0, "option_count": 2}},
                {"type": "mcq", "prompt": "M3", "options": ["x", "y"], "answer_spec": {"type": "option_index", "expected": 0, "option_count": 2}},
            ],
        },
    }
    if with_reflection:
        content["reflection"] = {"summary": "Wrap up what you learned.", "question": "What clicked?"}
    assert client.put(f"/api/homeworks/{hw_id}", json={"content_json": content}).status_code == 200
    return hw_id


def _pass_cbp_and_mc(client, hw_id, sid):
    for i, a in [(0, "1"), (1, "0"), (2, "1")]:
        client.post("/api/ai/check-answer", json={
            "phase": "case_based_preview", "homework_id": hw_id, "session_id": sid,
            "item_index": i, "student_answer": a,
        })
    for i in range(3):
        client.post("/api/ai/check-answer", json={
            "phase": "memory_check", "homework_id": hw_id, "session_id": sid,
            "item_index": i, "student_answer": "0",
        })


def _seed_boss_win(session_id, hw_id):
    """Persist a boss attempt row with correct=1 — the boss-win signal
    practice_arc_completed derives from (BOSS_PHASES = final-boss | boss)."""
    from server.db import attempts_repo

    async def go():
        await attempts_repo.add_phase_attempt(
            session_id=session_id, hw_id=hw_id,
            phase="boss", subphase=None, question_id="boss-q1",
            checker_source="boss_judge", correct=1, score=1.0, confidence=0.95,
            feedback="won",
        )
    _run(go())


def _seed_reflection_mark(session_id, hw_id, verdict):
    """Persist the reflection mark the engine writes: final_reports.report_json
    with a top-level `verdict`."""
    from server.db import final_report_repo

    async def go():
        await final_report_repo.upsert_final_report(
            session_id, hw_id, {"verdict": verdict, "mark": 88, "narrative": "ok"},
        )
    _run(go())


def test_gate_reports_completion_flags_additive(client):
    """A session with cbp+mc passed + a boss win + a passed reflection mark →
    all_divisions_complete + reflection_passed True; and the inverse (no boss,
    no reflection mark) → both False. Existing keys stay intact (additive)."""
    # ---- Inverse first: fresh-but-passed Learning section, NO boss, NO mark ----
    hw_id = _make_v2_homework(client, with_reflection=True)
    sid_neg = "reflect-gate-neg"
    _pass_cbp_and_mc(client, hw_id, sid_neg)

    gs_neg = _run(compute_gate_state(sid_neg, hw_id))
    # Existing shape preserved.
    assert gs_neg["cbp"]["passed"] is True
    assert gs_neg["mc"]["passed"] is True
    assert gs_neg["practice_arc_unlocked"] is True
    # New additive flags — boss not won, reflection not marked.
    assert gs_neg["reflection_required"] is True       # reflection block authored
    assert gs_neg["practice_arc_completed"] is False   # no boss-win row
    assert gs_neg["reflection_passed"] is False         # no mark persisted
    assert gs_neg["all_divisions_complete"] is False    # boss not completed

    # ---- Positive: same Learning pass + boss win + a PASSED reflection mark ----
    sid_pos = "reflect-gate-pos"
    _pass_cbp_and_mc(client, hw_id, sid_pos)
    _seed_boss_win(sid_pos, hw_id)
    _seed_reflection_mark(sid_pos, hw_id, verdict="passed")

    gs_pos = _run(compute_gate_state(sid_pos, hw_id))
    assert gs_pos["cbp"]["passed"] is True
    assert gs_pos["mc"]["passed"] is True
    assert gs_pos["practice_arc_completed"] is True
    assert gs_pos["reflection_passed"] is True
    assert gs_pos["all_divisions_complete"] is True

    # A non-"passed" verdict must NOT count as passed (defensive parse).
    sid_fail = "reflect-gate-failmark"
    _pass_cbp_and_mc(client, hw_id, sid_fail)
    _seed_boss_win(sid_fail, hw_id)
    _seed_reflection_mark(sid_fail, hw_id, verdict="needs_redo")
    gs_fail = _run(compute_gate_state(sid_fail, hw_id))
    assert gs_fail["practice_arc_completed"] is True
    assert gs_fail["reflection_passed"] is False
    # all_divisions_complete keys off the practice arc, not the reflection mark.
    assert gs_fail["all_divisions_complete"] is True


def test_gate_reflection_required_false_when_no_reflection_block(client):
    """reflection_required mirrors the presence of content_json.reflection —
    a homework without the block reports False (additive, defensive)."""
    hw_id = _make_v2_homework(client, with_reflection=False)
    gs = _run(compute_gate_state("no-reflection-sess", hw_id))
    assert gs["reflection_required"] is False
    # Other additive flags default safely with no session progress.
    assert gs["practice_arc_completed"] is False
    assert gs["reflection_passed"] is False
    assert gs["all_divisions_complete"] is False


def _seed_boss_rows(session_id, hw_id, scores):
    """Persist boss attempts with correct=0 and the given scores (no win row)."""
    from server.db import attempts_repo

    async def go():
        for i, sc in enumerate(scores):
            await attempts_repo.add_phase_attempt(
                session_id=session_id, hw_id=hw_id,
                phase="boss", subphase=None, question_id=f"boss-q{i}",
                checker_source="boss_judge", correct=0, score=sc,
            )
    _run(go())


def test_practice_arc_completed_matches_boss_passed_on_solid_damage(client):
    """A trials-exhausted boss arc with NO correct==1 row but mean score >= 0.6
    (pool-exhausted-with-solid-damage, per the Boss spec) must read as PASSED by
    BOTH the gate's practice_arc_completed AND reflection_engine.boss_passed.
    They previously DIVERGED — the gate used latest-row-correct only, so it read
    such an arc as NOT passed while the verdict read it as PASSED."""
    from server.services import reflection_engine as RE
    hw_id = _make_v2_homework(client, with_reflection=True)

    # Solid damage: mean 0.7 >= 0.6, no correct row.
    sid_solid = "boss-solid-damage"
    _seed_boss_rows(sid_solid, hw_id, [0.7, 0.7, 0.65])
    gs_solid = _run(compute_gate_state(sid_solid, hw_id))
    rows_solid = [{"correct": 0, "score": s} for s in (0.7, 0.7, 0.65)]
    assert gs_solid["practice_arc_completed"] is True
    assert RE.boss_passed(rows_solid) is True            # gate ↔ verdict agree

    # Weak damage: mean ~0.3 < 0.6, no correct row → both NOT passed.
    sid_weak = "boss-weak-damage"
    _seed_boss_rows(sid_weak, hw_id, [0.3, 0.2, 0.4])
    gs_weak = _run(compute_gate_state(sid_weak, hw_id))
    rows_weak = [{"correct": 0, "score": s} for s in (0.3, 0.2, 0.4)]
    assert gs_weak["practice_arc_completed"] is False
    assert RE.boss_passed(rows_weak) is False
