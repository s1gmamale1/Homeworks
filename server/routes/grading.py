"""HTTP surface for the session-grading service.

The runtime template POSTs the full session log here at the end of the
homework; the response is the scorecard payload that the Results screen
renders. The grading rules themselves live in `services/grading.py` —
this module is just the boundary.

Adding a new game / phase to NETS requires NO change here. Update
`PHASE_METHOD` in `services/grading.py` and the rubric automatically
applies to every homework served by the builder.
"""
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from server.services import grading
from server.db import boss_session_repo

router = APIRouter(prefix="/grading", tags=["grading"])

# A final-boss arc that ran out of trials while the boss still held more than
# this fraction of its max HP counts as a failed homework — the student never
# beat the boss. Below the threshold the boss was nearly dead, so the arc reads
# as a near-win and the per-axis tier (compute_boss_outcome) carries the grade
# instead of a blanket fail. Kept here so the policy lives next to its caller.
_BOSS_FAIL_HP_FRACTION = 0.40


async def _boss_session_failed(session_id: str, homework_id: str) -> bool:
    """Server-authoritative check: did the boss arc end in a real failure?

    Returns True only when the latest boss session for this (session, hw) is in
    the terminal ``failed`` state (trials ran out) AND the boss still held more
    than ``_BOSS_FAIL_HP_FRACTION`` of its max HP. The client also sends
    ``homework_failed`` for legacy reasons, but the server must not trust the
    client for a grade-affecting flag — this re-derives it from persisted state.

    Defensive: any lookup error returns False (never block a scorecard on a
    boss-state read failure).
    """
    if not session_id or not homework_id:
        return False
    try:
        sess = await boss_session_repo.get_latest_boss_session_for(
            session_id, homework_id
        )
    except Exception:
        return False
    if not sess or sess.get("status") != "failed":
        return False
    try:
        hp = int(sess.get("hp") or 0)
        max_hp = int(sess.get("max_hp") or 0)
    except (TypeError, ValueError):
        return False
    if max_hp <= 0:
        return False
    return (hp / max_hp) > _BOSS_FAIL_HP_FRACTION


class AggregateRequest(BaseModel):
    items: list[dict[str, Any]]
    # Optional metadata so future Phase-2 persistence can attach the log
    # to a session without breaking the current contract.
    session_id:  str | None = None
    homework_id: str | None = None
    # Wave J — warning deductions from the anti-troll state machine.
    warning_deductions: int = 0
    homework_failed: bool = False
    # Language-rubric routing — when present, language subjects (english,
    # ona-tili, rus-tili) get LMR v2 axis labels (Grammatical Accuracy /
    # Lexical Quality) instead of AMR's (Concept Identification / Process
    # Integrity). The numeric scoring is identical; only the labels differ.
    subject: str | None = None
    # Total expected open-rubric items in the homework (5 Real-Life + 5
    # Boss for Hard mode = 10; reading checkpoints add to this for
    # language subjects). Sent by the runtime so the aggregator can
    # penalise skipped questions instead of inflating the mean over
    # answered ones only. Optional — None preserves legacy behaviour.
    expected_open_count: int | None = None


@router.post("/aggregate")
async def aggregate(req: AggregateRequest) -> dict[str, Any]:
    """Take a session log; return the scorecard payload.

    The runtime template uses this as a drop-in replacement for the old
    client-side `_amrAggregate` JS function. The aggregation itself is pure
    compute, but the route now re-derives ``homework_failed`` from the persisted
    boss-session terminal state so a tampered/forgetful client can't avoid the
    failed-homework penalty — the server is authoritative for this flag.
    """
    # Server-authoritative boss-fail: OR the persisted terminal state into the
    # client-supplied flag. Either source can trip the fail; the server can
    # never UN-fail a client that already reported failure.
    server_boss_failed = await _boss_session_failed(req.session_id, req.homework_id)
    homework_failed = bool(req.homework_failed) or server_boss_failed
    return grading.aggregate(
        req.items,
        warning_deductions=req.warning_deductions,
        homework_failed=homework_failed,
        subject=req.subject,
        expected_open_count=req.expected_open_count,
    )


@router.get("/rubric")
async def rubric() -> dict[str, Any]:
    """Inspect the current rubric. Useful for the dashboard (so a teacher
    can see which phases produce which grade) and for tests."""
    return {
        "phase_method":         grading.PHASE_METHOD,
        "phase_display_order":  grading.PHASE_DISPLAY_ORDER,
        "band_thresholds":      [
            {"axis_avg_floor": floor, "key": k, "name": n}
            for floor, k, n in grading.BAND_THRESHOLDS
        ],
        "finish_threshold_pct": grading.FINISH_THRESHOLD_PCT,
    }
