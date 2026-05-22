"""Server-authoritative Practice-Arc gate computation.

Extracted from `server/routes/runtime.py` so the React runtime route AND the
grading route (`server/routes/ai.py`, owned by a parallel agent) compute the
unlock the SAME way. The gate is the contract the client renders but can NEVER
flip on its own — only correct, server-graded answers move it.

No-inflation invariant: aggregation keys on the SERVER-DERIVED `subphase`
(`checkpoint_{idx}` / `item_{idx}`, range-validated in ai.py), never on the
CLIENT-supplied `question_id`. Keying on `question_id` let a student resubmit
the same item under different ids and inflate the correct count past the total.
"""

from __future__ import annotations

import math
from typing import Optional

from ..db import get_homework
from ..db.attempts_repo import list_phase_attempts
from .content_json_compat import normalize_content_json_for_runtime

CBP_PHASE = "case_based_preview"
MC_PHASE = "memory_check"
CBP_MIN_CORRECT = 2          # locked rule: ≥2 of 3 checkpoints
DEFAULT_MC_THRESHOLD_PCT = 60
# Boss attempts persist under one of two phase strings depending on which boss
# subsystem graded them: the legacy adaptive boss (ai_plan5.py) writes
# phase="boss"; the v2 React Final Boss adapter (ai.py) uses phase="final-boss".
# We treat EITHER as a boss-arc signal so practice_arc_completed is robust
# across both render paths.
BOSS_PHASES = ("final-boss", "boss")

# Boss "solid damage" floor — MUST match reflection_engine._BOSS_SOLID_DAMAGE_MEAN
# so this gate and the reflection verdict agree on the SAME persisted boss rows.
_BOSS_SOLID_DAMAGE_MEAN = 0.6


async def _practice_arc_completed(session_id: Optional[str], hw_id: str) -> bool:
    """True iff the student PASSED the boss arc for this (session, hw).

    Defensive derivation from persisted `phase_attempts` only (no in-memory
    state, no provider). The boss-pass rule MUST match
    `reflection_engine.boss_passed` so this gate and the verdict never contradict
    each other on the same rows (Boss spec: a win OR pool-exhausted-with-solid-
    damage both count). Previously this used "latest attempt correct" only, which
    could read a trials-exhausted-but-solid arc as NOT passed while the verdict
    read it as PASSED. We now pool ALL boss rows across both phase strings (see
    BOSS_PHASES) — fixing the prior phase-loop bug where the per-phase iteration
    let the last phase's last row override the true cross-phase latest — and
    apply: any correct attempt → pass; else mean score ≥ the solid-damage floor.
    """
    if not session_id:
        return False
    boss_rows: list[dict] = []
    for phase in BOSS_PHASES:
        try:
            boss_rows.extend(await list_phase_attempts(session_id, hw_id, phase=phase, limit=500))
        except Exception:  # noqa: BLE001 — boss arc is best-effort; never break the gate
            pass
    if not boss_rows:
        return False
    if any(r.get("correct") == 1 for r in boss_rows):
        return True
    scores = [float(r.get("score") or 0.0) for r in boss_rows]
    return bool(scores) and (sum(scores) / len(scores)) >= _BOSS_SOLID_DAMAGE_MEAN


async def _reflection_passed(session_id: Optional[str], hw_id: str) -> bool:
    """True iff a persisted reflection mark with verdict=="passed" exists.

    The reflection engine (parallel agent) writes the mark into the
    `final_reports` row's `report_json` with a top-level `verdict`. We read it
    via `final_report_repo.get_final_report`. Import is lazy + guarded so a
    missing/renamed repo never breaks the gate — absent ⇒ False (defensive).
    """
    if not session_id:
        return False
    try:
        from ..db.final_report_repo import get_final_report
        report = await get_final_report(session_id, hw_id)
    except Exception:  # noqa: BLE001 — reflection mark is best-effort; never break the gate
        return False
    if not isinstance(report, dict):
        return False
    return str(report.get("verdict") or "").lower() == "passed"


def latest_correct_by_key(attempts: list[dict]) -> dict[str, bool]:
    """Last attempt wins per SERVER-DERIVED item key (soft-retry).

    Keys on `subphase` only — it is server-derived + range-validated in ai.py
    (`checkpoint_{idx}` / `item_{idx}`). The client-supplied `question_id` is
    deliberately ignored so a student can't inflate the correct count by
    resubmitting the same item under fresh ids.
    """
    latest: dict[str, bool] = {}
    for a in attempts:  # list_phase_attempts returns created_at ASC
        key = a.get("subphase") or a.get("item_id") or str(a.get("id"))
        latest[str(key)] = bool(a.get("correct"))
    return latest


async def compute_gate_state(session_id: Optional[str], hw_id: str) -> dict:
    """Compute the two Learning-Section gates + the combined unlock.

    Returns ``{'cbp': {...}, 'mc': {...}, 'practice_arc_unlocked': bool}`` —
    byte-identical to the legacy inline shape in runtime.py. Without a
    `session_id` we report the structure with zero progress (a fresh student).

    Raises nothing on a missing/trashed homework — the caller decides the HTTP
    behaviour; this returns an all-zero gate for an absent homework.
    """
    hw = await get_homework(hw_id)
    content = normalize_content_json_for_runtime((hw or {}).get("content_json") or {})
    cbp = content.get("case_based_preview") or {}
    mc = content.get("memory_check") or {}
    cbp_total = len(cbp.get("checkpoints") or []) or 3
    mc_items = mc.get("items") or []
    mc_total = len(mc_items)
    mc_threshold = int(mc.get("pass_threshold_pct") or DEFAULT_MC_THRESHOLD_PCT)
    # CBP threshold generalizes: ≥2 OR ≥60% of however many checkpoints exist.
    cbp_threshold = max(CBP_MIN_CORRECT, math.ceil(0.6 * cbp_total))

    # Is the open-ended "Decision Process Explanation" authored on this case?
    # When present, the CBP gate ALSO requires its reasoning attempt to pass.
    reasoning_required = bool(cbp.get("decision_process_explanation"))

    cbp_correct = 0
    mc_correct = 0
    reasoning_passed = False
    if session_id:
        cbp_attempts = await list_phase_attempts(session_id, hw_id, phase=CBP_PHASE, limit=500)
        mc_attempts = await list_phase_attempts(session_id, hw_id, phase=MC_PHASE, limit=500)
        cbp_latest = latest_correct_by_key(cbp_attempts)
        # The open-ended reasoning step persists under subphase="reasoning". It
        # must NOT inflate the MCQ checkpoint count (which is compared against
        # checkpoints_total) — count only the checkpoint_* keys here.
        reasoning_passed = bool(cbp_latest.get("reasoning", False))
        cbp_correct = sum(
            1 for k, v in cbp_latest.items() if v and k != "reasoning"
        )
        mc_correct = sum(1 for v in latest_correct_by_key(mc_attempts).values() if v)

    # Defensive clamp: a server-derived key set can't exceed the authored total,
    # but clamp anyway so a malformed content_json can never report >100%.
    cbp_correct = min(cbp_correct, cbp_total)
    mc_correct = min(mc_correct, mc_total) if mc_total else mc_correct

    mcq_passed = cbp_correct >= cbp_threshold
    # When a reasoning step is authored, the CBP gate requires BOTH the MCQ
    # threshold AND a passing reasoning attempt; otherwise MCQ alone gates.
    cbp_passed = mcq_passed and (reasoning_passed if reasoning_required else True)
    mc_score_pct = round(100 * mc_correct / mc_total) if mc_total else 0
    mc_score_pct = min(mc_score_pct, 100)
    mc_passed = mc_total > 0 and mc_score_pct >= mc_threshold

    # ---- Additive v3 completion flags (do NOT change existing keys). ----
    # The reflection phase is authored / default-on when content_json carries a
    # `reflection` block (closing phase). The reflection engine (parallel agent)
    # persists a server-authoritative mark in `final_reports.report_json` with a
    # top-level `verdict`; "passed" there means the reflection cleared.
    reflection_required = bool(content.get("reflection"))
    practice_arc_completed = await _practice_arc_completed(session_id, hw_id)
    reflection_passed = await _reflection_passed(session_id, hw_id)

    return {
        "cbp": {
            "passed": cbp_passed,
            "checkpoints_correct": cbp_correct,
            "checkpoints_total": cbp_total,
            "threshold": cbp_threshold,
            "reasoning_required": reasoning_required,
            "reasoning_passed": reasoning_passed,
        },
        "mc": {
            "passed": mc_passed,
            "score_pct": mc_score_pct,
            "correct": mc_correct,
            "total": mc_total,
            "threshold_pct": mc_threshold,
        },
        "practice_arc_unlocked": bool(cbp_passed and mc_passed),
        # ---- Additive completion flags (consumed by the v3 reflection flow). ----
        "practice_arc_completed": bool(practice_arc_completed),
        "reflection_required": bool(reflection_required),
        "reflection_passed": bool(reflection_passed),
        "all_divisions_complete": bool(cbp_passed and mc_passed and practice_arc_completed),
    }


async def is_practice_unlocked(session_id: Optional[str], hw_id: str) -> bool:
    gs = await compute_gate_state(session_id, hw_id)
    return bool(gs.get("practice_arc_unlocked"))
