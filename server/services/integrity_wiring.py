"""Integration glue between the live submit paths and the integrity engine.

This module is the ONE place that threads the *foundations* (the pure
``integrity_signals`` flag engine + the ``ai_use_policy`` table) into the
runtime submit flow. Everything here is BEST-EFFORT and ADVISORY:

  - Nothing in this module ever changes ``score`` / ``is_correct`` /
    ``confidence`` / ``hp`` / ``boss_status`` or blocks progress. The caller
    has already produced the final grade before invoking us.
  - Every public coroutine swallows its own exceptions and logs — a DB hiccup
    or a malformed homework can NEVER break grading.
  - The server stays authoritative; flags are conservative + opt-in (the policy
    + thresholds live in the foundations modules, which we only *consume*).

The two entry points (one per submit surface) build an
``IntegritySignalInput``, run ``compute_flags``, enroll any flags into the
review queue as ADVISORY ``kind='integrity'`` rows, and return an optional
soft-friction nudge (only when a ``strong`` flag fired).
"""
from __future__ import annotations

import logging
from typing import Optional

from .. import db
from .integrity_signals import (
    IntegritySignalInput,
    SEVERITY_STRONG,
    compute_flags,
    policy_from_boss_meta,
)
from . import ai_use_policy

_log = logging.getLogger("nets.integrity")


# Upper bound for a single response time: 24h in ms. A measured time outside
# (0, _MAX_TIME_MS) is treated as garbage (clock skew / tampered client) and
# discarded → no signal, never suspicious.
_MAX_TIME_MS = 86_400_000


def clamp_client_time_ms(value) -> Optional[int]:
    """Server-side clamp for a client-reported response time.

    Accept only a real ``int`` strictly inside ``(0, 86_400_000)``. Anything
    else (None, bool, float, str, negative, zero, absurd) collapses to ``None``
    — i.e. "unknown / not measured", which every detector treats as no-signal.

    ``bool`` is explicitly rejected even though ``True``/``False`` are ints in
    Python — a stray boolean must not masquerade as a 1ms response.
    """
    if isinstance(value, bool):
        return None
    if not isinstance(value, int):
        return None
    if 0 < value < _MAX_TIME_MS:
        return value
    return None


def _nudge_for_flags(flags) -> Optional[dict]:
    """Build the soft-friction nudge iff a ``strong`` flag fired.

    Only the (single) strong detector — ``sudden_mastery`` — surfaces a nudge.
    The nudge is a gentle pedagogical "explain in your own words" prompt; it
    NEVER carries the reason_code or thresholds (teacher-only intelligence) and
    NEVER gates progress.
    """
    if any(getattr(f, "severity", None) == SEVERITY_STRONG for f in flags):
        return {
            "type": "explain_reasoning",
            "message": (
                "Zo'r ish! Bu savolni o'z so'zlaring bilan qanday "
                "yechganingni qisqacha tushuntirib bera olasanmi?"
            ),
        }
    return None


async def _assessment_rate_for_session(
    session_id: str, hw_id: str
) -> tuple[Optional[float], int]:
    """Derive (correct_rate, item_count) over the session's ASSESSMENT attempts.

    Walks ``phase_attempts`` for the session and keeps only rows whose
    phase/subphase resolve to ``assessment=True`` in the AI-use policy table.
    Returns ``(None, 0)`` when there are no assessment attempts (so the
    sudden-mastery detector — which needs both a rate and a min item count —
    cleanly no-ops). Best-effort: a query failure returns ``(None, 0)``.
    """
    try:
        from ..db.attempts_repo import list_phase_attempts

        attempts = await list_phase_attempts(session_id, hw_id, limit=1000)
    except Exception as exc:  # pragma: no cover - defensive
        _log.warning("list_phase_attempts failed (integrity, non-fatal): %s", exc)
        return None, 0

    total = 0
    correct = 0
    for a in attempts:
        phase = a.get("phase") or ""
        subphase = a.get("subphase") or None
        try:
            is_assessment = bool(ai_use_policy.policy_for(phase, subphase).get("assessment"))
        except Exception:
            is_assessment = False
        if not is_assessment:
            continue
        total += 1
        if a.get("correct") == 1:
            correct += 1
    if total == 0:
        return None, 0
    return (correct / total), total


async def _mastery_score_for_session(session_id: str, hw_id: str) -> Optional[float]:
    """Read the persisted mastery_score from session_metrics (or None)."""
    try:
        from ..db.session_metrics_repo import get_session_metrics

        metrics = await get_session_metrics(session_id, hw_id)
    except Exception as exc:  # pragma: no cover - defensive
        _log.warning("get_session_metrics failed (integrity, non-fatal): %s", exc)
        return None
    if not isinstance(metrics, dict):
        return None
    val = metrics.get("mastery_score")
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        return float(val)
    return None


async def evaluate_runtime_submit(
    *,
    session_id: str,
    hw_id: str,
    phase: str,
    subphase: Optional[str],
    question_id: Optional[str],
    time_ms: Optional[int],
    paste_detected: Optional[bool],
    grade: Optional[int],
    boss_meta: Optional[dict],
) -> Optional[dict]:
    """Run the flag engine for one runtime (process_runtime_answer) submit.

    Enrolls any advisory flags into the review queue and returns an optional
    soft-friction nudge. Fully best-effort: any failure returns ``None`` and
    the caller proceeds with the normal graded response unchanged.
    """
    try:
        try:
            is_assessment = bool(ai_use_policy.policy_for(phase, subphase).get("assessment"))
        except Exception:
            is_assessment = False

        pre_mastery = await _mastery_score_for_session(session_id, hw_id)
        correct_rate, item_count = await _assessment_rate_for_session(session_id, hw_id)

        inp = IntegritySignalInput(
            phase=phase or "",
            subphase=subphase,
            is_assessment=is_assessment,
            time_ms=time_ms,
            paste_detected=bool(paste_detected),
            pre_assessment_mastery=pre_mastery,
            assessment_correct_rate=correct_rate,
            assessment_item_count=item_count,
            grade=grade,
        )
        policy = policy_from_boss_meta(boss_meta)
        flags = compute_flags(inp, policy)

        for flag in flags:
            try:
                await db.add_integrity_flag(session_id, hw_id, question_id, flag)
            except Exception as exc:
                _log.warning("add_integrity_flag failed (non-fatal): %s", exc)

        return _nudge_for_flags(flags)
    except Exception as exc:  # pragma: no cover - top-level guard
        _log.warning("evaluate_runtime_submit failed (non-fatal): %s", exc)
        return None


async def evaluate_boss_submit(
    *,
    session_id: str,
    hw_id: str,
    question_id: Optional[str],
    time_ms: Optional[int],
    paste_detected: Optional[bool],
    pre_assessment_mastery: Optional[float],
    correct_count: int,
    total_attempts: int,
    grade: Optional[int],
    boss_meta: Optional[dict],
) -> Optional[dict]:
    """Run the flag engine for one boss submit (ai_plan5 boss_submit_answer).

    The boss is always an assessment. ``correct_count`` / ``total_attempts``
    come from the boss_session row (post-update); the correct-rate is
    ``correct_count / max(1, total_attempts)``. Best-effort throughout.
    """
    try:
        item_count = int(total_attempts or 0)
        rate = (int(correct_count or 0) / max(1, item_count)) if item_count > 0 else None

        inp = IntegritySignalInput(
            phase="boss",
            subphase=None,
            is_assessment=True,
            time_ms=time_ms,
            paste_detected=bool(paste_detected),
            pre_assessment_mastery=pre_assessment_mastery,
            assessment_correct_rate=rate,
            assessment_item_count=item_count,
            grade=grade,
        )
        policy = policy_from_boss_meta(boss_meta)
        flags = compute_flags(inp, policy)

        for flag in flags:
            try:
                await db.add_integrity_flag(session_id, hw_id, question_id, flag)
            except Exception as exc:
                _log.warning("add_integrity_flag failed (non-fatal): %s", exc)

        return _nudge_for_flags(flags)
    except Exception as exc:  # pragma: no cover - top-level guard
        _log.warning("evaluate_boss_submit failed (non-fatal): %s", exc)
        return None
