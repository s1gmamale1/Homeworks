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

router = APIRouter(prefix="/grading", tags=["grading"])


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

    Pure compute — no DB. The runtime template uses this as a drop-in
    replacement for the old client-side `_amrAggregate` JS function.
    """
    return grading.aggregate(
        req.items,
        warning_deductions=req.warning_deductions,
        homework_failed=req.homework_failed,
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
