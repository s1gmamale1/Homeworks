"""Server-authoritative Reflection / finalization pipeline.

This is the background engine behind the flowchart's final "Reflection" node.
After all three divisions complete, finalizing a homework runs:

  1. EXTRACT  — pull the real per-attempt rows from ``phase_attempts`` and
                group them by division (CBP / Memory Check / Practice+Boss).
  2. ANALYZE  — recompute the proven session metrics (weak/strong topics,
                mastery, boss-readiness) + build the grading scorecard via the
                ONE source of truth ``services.grading.aggregate``, and count
                mistake-repairs (wrong early → right in the Boss).
  3. AI       — turn the aggregates + the student's reflection answers into a
                warm Uzbek debrief narrative. AI writes PROSE ONLY; it never
                decides the verdict. On any AI unavailability a deterministic
                neutral debrief is returned with ``ai_unavailable: True``.
  4. MARK     — compute the DETERMINISTIC verdict (passed / needs_retry),
                persist the full debrief to ``final_reports`` with a top-level
                ``verdict`` key (the gate agent reads ``report_json.verdict``),
                and write the session-level mark (status / overall_score /
                ended_at / performance_summary_json).
  5. REDO     — flip needs_retry → active and clear Division-3 progress so the
                runtime re-presents the Practice Arc with a reshuffle.

Everything reuses existing infra — nothing here re-implements grading, metrics,
or persistence. Pure orchestration over the repos + ``grading.aggregate``.

No-leak invariant: the returned debrief NEVER carries answer-bearing data
(expected answers, accepted lists, rubric text, keyword anchors). The
weak/strong keyword anchors ride into the AI PROMPT only and are dropped from
the response.
"""
from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Optional

from ..db.attempts_repo import list_phase_attempts
from ..db.connection import connect
from ..db.final_report_repo import get_final_report, upsert_final_report
from ..db.session_metrics_repo import recompute_session_metrics
from ..services import ai_orchestrator
from ..services import grading
from ..services.gate_state import compute_gate_state

_log = logging.getLogger(__name__)


# ── Division grouping (phase strings — fixed contract) ──────────────────────

CBP_PHASE = "case_based_preview"
MC_PHASE = "memory_check"

# Division 3 = Practice Arc games + the Final Boss. These are the phase strings
# a Division-3 attempt is recorded under.
PRACTICE_PHASES: frozenset[str] = frozenset({
    "tile-match",
    "sentence-fill",
    "real-life-challenge",
    "ttt",
    "ttt-session",
    "adaptive-quiz",
    "mystery-box",
    "puzzle-lock",
    "memory-palace",
    "final-boss",
    "boss",
})

# The Boss can persist under two phase strings: "final-boss" (the legacy
# check-answer path) and "boss" (the dynamic /ai/boss/* rebuild, PR #252/#253).
# Both map to the Division-3 boss bucket so the verdict + debrief see boss data
# regardless of which path graded the turn.
BOSS_PHASE = "final-boss"
BOSS_PHASES: frozenset[str] = frozenset({"final-boss", "boss"})

# Boss "solid damage" floor: when there is no outright boss win row, the boss is
# treated as passed only if the boss attempts collectively show real progress
# (mean score over boss attempts ≥ this). Pool-exhausted-with-solid-damage path.
_BOSS_SOLID_DAMAGE_MEAN = 0.6

# Divisions that, when present, gate the verdict. CBP + MC must pass; the
# Practice Arc unlock already depends on them via compute_gate_state.
FINISH_THRESHOLD_PCT = grading.FINISH_THRESHOLD_PCT  # 60

VERDICT_PASSED = "passed"
VERDICT_NEEDS_RETRY = "needs_retry"

# Uzbek formal verdict labels (NEVER "Not Completed").
_VERDICT_LABELS = {
    VERDICT_PASSED: "Tabriklaymiz, vazifa topshirildi",
    VERDICT_NEEDS_RETRY: "Qayta urinish kerak",
}

# Division display labels (Uzbek).
_DIVISION_LABELS = {
    "cbp": "Vaziyatli kirish",
    "mc": "Xotira sinovi",
    "practice": "Amaliyot maydoni",
    "boss": "Yakuniy jang",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _division_for_phase(phase: Optional[str]) -> Optional[str]:
    """Map a phase_attempts.phase string to a division key, or None if unknown."""
    if phase == CBP_PHASE:
        return "cbp"
    if phase == MC_PHASE:
        return "mc"
    if phase in BOSS_PHASES:
        return "boss"
    if phase in PRACTICE_PHASES:
        return "practice"
    return None


# ── 1. EXTRACT ──────────────────────────────────────────────────────────────

def group_attempts_by_division(attempts: list[dict]) -> dict[str, list[dict]]:
    """Group raw phase_attempts rows into the four division buckets.

    Returns ``{"cbp": [...], "mc": [...], "practice": [...], "boss": [...]}``.
    The Final Boss is split out of Practice into its own ``boss`` bucket so the
    deterministic verdict can reason about it independently, while still being a
    Division-3 phase for the grading scorecard.

    Unknown phases (e.g. ungraded previews) are dropped — they never count.
    """
    buckets: dict[str, list[dict]] = {"cbp": [], "mc": [], "practice": [], "boss": []}
    for a in attempts:
        div = _division_for_phase(a.get("phase"))
        if div is None:
            continue
        buckets[div].append(a)
    return buckets


def _correct_total(rows: list[dict]) -> tuple[int, int]:
    """(correct_count, total) for a bucket of attempt rows.

    Counts each row once; ``correct == 1`` is a hit. Soft-retry resolution
    (last attempt wins per item) is the gate's job; for the division scorecard
    we report raw attempt accuracy, which is what the grading aggregate uses.
    """
    total = len(rows)
    correct = sum(1 for r in rows if r.get("correct") == 1)
    return correct, total


# ── 2. ANALYZE ──────────────────────────────────────────────────────────────

# The v2 runtime persists newer phase strings than grading.aggregate's v1-era
# PHASE_METHOD/PHASE_DISPLAY_ORDER table, so several Division-3 attempts were
# being SILENTLY DROPPED from overall_pct: real-life-challenge (the key AMR
# reasoning signal), the dynamic boss ("boss"), and the v2-only Game-Break games.
# Map each v2 phase to the canonical grading key so it counts. We alias here
# (not in grading.py) so the shared v1 scorecard is untouched — and finalize()
# reads ONLY `overall_pct` + `band` from the scorecard (never its per-phase
# rows), so routing the v2-only games onto a counted closed key affects the
# donut total only; the student-facing per-division breakdown comes from
# divisions[] (the real per-phase buckets), never from this alias.
_GRADING_PHASE_ALIAS: dict[str, str] = {
    "real-life-challenge": "real-life",   # v2 string for the AMR real-life phase
    "boss": "final-boss",                 # dynamic /ai/boss/* boss → AMR boss row
    "mystery-box": "adaptive-quiz",       # v2-only closed Game-Break → counted closed
    "puzzle-lock": "adaptive-quiz",
    "ttt": "adaptive-quiz",
    "memory-palace": "adaptive-quiz",
    # tile-match / sentence-fill / adaptive-quiz already match grading keys.
    # ttt-session (the redundant tally) is intentionally NOT aliased so it stays
    # uncounted and never double-counts the per-pick "ttt" rows.
}


def _grading_items_from_attempts(attempts: list[dict]) -> list[dict]:
    """Build the ``grading.aggregate`` items list from extracted attempt rows.

    Each item is ``{phase, correct, score, axis_1, axis_2}`` — exactly the shape
    ``grading.aggregate`` coerces. Runtime phase strings are normalized to the
    grading table's canonical keys via ``_GRADING_PHASE_ALIAS`` so every graded
    Division-3 attempt contributes to overall_pct. Phases the aggregate still
    doesn't know about contribute nothing (it skips them); the deterministic
    verdict below uses the division buckets, not the scorecard rows, for pass/fail.
    """
    items: list[dict] = []
    for a in attempts:
        phase = a.get("phase")
        div = _division_for_phase(phase)
        if div is None:
            continue
        items.append({
            "phase": _GRADING_PHASE_ALIAS.get(phase, phase),
            "correct": a.get("correct") == 1,
            "score": a.get("score"),
            "axis_1": a.get("axis_1"),
            "axis_2": a.get("axis_2"),
        })
    return items


def count_mistake_repairs(buckets: dict[str, list[dict]]) -> int:
    """Count concepts the student got WRONG early then RIGHT in the Boss.

    "Early" = any CBP / Memory Check / Practice attempt that was incorrect on a
    concept (keyed by question_id / item_id), "right in the Boss" = a correct
    final-boss attempt touching the same concept key. This is the strongest
    learning signal (per the Boss spec), so we surface the count.

    Concept keys are matched on question_id (falling back to item_id). When the
    boss questions are dynamically generated (no shared id with practice), we
    also credit a repair when the boss attempt's misconception tags overlap a
    concept the student missed earlier — a best-effort signal that degrades to 0
    rather than over-counting.
    """
    early_wrong_keys: set[str] = set()
    early_wrong_tags: set[str] = set()
    for div in ("cbp", "mc", "practice"):
        for r in buckets.get(div, []):
            if r.get("correct") == 0:
                key = r.get("question_id") or r.get("item_id")
                if key:
                    early_wrong_keys.add(str(key))
                for t in _tags_of(r):
                    early_wrong_tags.add(t)

    if not early_wrong_keys and not early_wrong_tags:
        return 0

    repaired_keys: set[str] = set()
    repaired_tags: set[str] = set()
    for r in buckets.get("boss", []):
        if r.get("correct") != 1:
            continue
        key = r.get("question_id") or r.get("item_id")
        if key and str(key) in early_wrong_keys:
            repaired_keys.add(str(key))
        for t in _tags_of(r):
            if t in early_wrong_tags:
                repaired_tags.add(t)

    return len(repaired_keys) + len(repaired_tags)


def _tags_of(row: dict) -> list[str]:
    """Parse misconception_tags_json off an attempt row into a list of strings."""
    import json as _json

    raw = row.get("misconception_tags_json")
    if not raw:
        return []
    try:
        tags = _json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        return []
    if isinstance(tags, list):
        return [str(t) for t in tags if t]
    return []


# ── 3. AI narrative ─────────────────────────────────────────────────────────

# Deterministic neutral debrief prose (used when the AI backend is unavailable).
_FALLBACK_NARRATIVE = (
    "Bugungi mashg'ulotni yakunlaganingiz uchun rahmat. Har bir bo'lim "
    "ustida ishlaganingiz ko'rinib turibdi — natijalaringizni quyida ko'rishingiz mumkin."
)
_FALLBACK_NEXT_STEPS = [
    "Eng past natija ko'rsatgan bo'limni qayta ko'rib chiqing",
    "Asosiy tushunchalarni mustahkamlab, yana bir bor urinib ko'ring",
]
_FALLBACK_ENCOURAGEMENT = "Davom eting — har bir urinish sizni kuchliroq qiladi!"


async def _ai_narrative(
    *,
    overall_pct: int,
    band: dict,
    divisions: list[dict],
    mistake_repairs: int,
    reflection_answers: list[str],
    weak_topics: list[str],
    strong_topics: list[str],
) -> tuple[dict, bool]:
    """Generate the prose half of the debrief. Returns (prose_dict, ai_unavailable).

    The prose_dict has keys: narrative, weak_points, strong_points, next_steps,
    redo_recommendation. The weak/strong topic anchors ride into the PROMPT only
    (marked DO-NOT-echo); they never appear in the returned dict.

    On PromptTooLargeError / RuntimeError (no provider, bad JSON) we return a
    deterministic neutral debrief grounded in the real aggregates and signal
    ai_unavailable=True so the caller can flag it in the response + report.
    """
    from ..services.tutor import _load_runtime_prompt

    prompt = _load_runtime_prompt("reflection-analysis")
    payload = {
        "overall_pct": overall_pct,
        "band": band,
        "divisions": divisions,
        "mistake_repairs": mistake_repairs,
        # Untrusted student free-text — the prompt instructs the LLM to treat it
        # as data, never as instructions.
        "reflection_answers": [str(a) for a in (reflection_answers or [])],
        # Server-only grounding anchors — the prompt instructs the LLM to NEVER
        # echo these verbatim. They never make it into the returned dict.
        "weak_point_keywords": list(weak_topics or []),
        "strong_point_keywords": list(strong_topics or []),
    }
    schema = {
        "narrative": "Uzbek string, 2-4 sentences",
        "weak_points": "array of short Uzbek strings",
        "strong_points": "array of short Uzbek strings",
        "next_steps": "array of 2-3 actionable Uzbek strings",
        "redo_recommendation": "phase string or 'none'",
    }
    try:
        input_section = ai_orchestrator.build_input_section(payload)
        ai = await ai_orchestrator.generate_json(
            f"{prompt}\n\n{input_section}",
            schema_hint=schema,
            model=ai_orchestrator.FAST_MODEL,
        )
    except (ai_orchestrator.PromptTooLargeError, RuntimeError) as exc:
        _log.warning(
            "reflection narrative AI unavailable (%s: %s); using neutral debrief",
            exc.__class__.__name__,
            exc,
        )
        # Deterministic fallback grounded in the real division data.
        weak_div = _weakest_division(divisions)
        return (
            {
                "narrative": _FALLBACK_NARRATIVE,
                "weak_points": [weak_div["label"]] if weak_div else [],
                "strong_points": [d["label"] for d in divisions if d.get("status") == "passed"][:2],
                "next_steps": list(_FALLBACK_NEXT_STEPS),
                "redo_recommendation": "none",
            },
            True,
        )

    # Sanitize the AI prose into the exact shape we expose. Drop any extraneous
    # keys the model may have hallucinated (defence-in-depth against leak).
    return (
        {
            "narrative": str(ai.get("narrative") or _FALLBACK_NARRATIVE),
            "weak_points": _str_list(ai.get("weak_points")),
            "strong_points": _str_list(ai.get("strong_points")),
            "next_steps": _str_list(ai.get("next_steps")) or list(_FALLBACK_NEXT_STEPS),
            "redo_recommendation": str(ai.get("redo_recommendation") or "none"),
        },
        False,
    )


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(v) for v in value if isinstance(v, str) and v.strip()]


def _weakest_division(divisions: list[dict]) -> Optional[dict]:
    """Return the division with the lowest pct among those that aren't passed."""
    candidates = [d for d in divisions if d.get("status") != "passed"]
    pool = candidates or divisions
    if not pool:
        return None
    return min(pool, key=lambda d: d.get("pct", 0))


# ── Verdict (DETERMINISTIC — AI never decides this) ─────────────────────────

def boss_passed(boss_rows: list[dict]) -> bool:
    """A final-boss attempt indicates a win OR pool exhausted with solid damage.

    - Any ``correct == 1`` boss attempt → win → passed.
    - Else, if boss attempts exist and their mean score clears the solid-damage
      floor → pool-exhausted-with-solid-damage → passed.
    - No boss attempts at all → not passed (boss not reached/completed).
    """
    if not boss_rows:
        return False
    if any(r.get("correct") == 1 for r in boss_rows):
        return True
    scores = [float(r.get("score") or 0.0) for r in boss_rows]
    if not scores:
        return False
    return (sum(scores) / len(scores)) >= _BOSS_SOLID_DAMAGE_MEAN


def compute_verdict(
    *,
    overall_pct: int,
    boss_rows: list[dict],
    cbp_passed: bool,
    mc_passed: bool,
) -> str:
    """The deterministic mark. AI never touches this.

    ``passed`` iff overall_pct >= FINISH_THRESHOLD_PCT (60) AND the boss passed
    AND the CBP + Memory Check gates passed. Otherwise ``needs_retry``.
    """
    if (
        overall_pct >= FINISH_THRESHOLD_PCT
        and boss_passed(boss_rows)
        and cbp_passed
        and mc_passed
    ):
        return VERDICT_PASSED
    return VERDICT_NEEDS_RETRY


def _division_status(div_key: str, pct: float, total: int, *, gate_passed: Optional[bool], boss_ok: Optional[bool]) -> str:
    """Per-division status for the debrief divisions[] list."""
    if total == 0:
        return "incomplete"
    if div_key in ("cbp", "mc"):
        return "passed" if gate_passed else "needs_retry"
    if div_key == "boss":
        return "passed" if boss_ok else "needs_retry"
    # practice
    return "passed" if pct >= FINISH_THRESHOLD_PCT else "needs_retry"


def _build_divisions(
    buckets: dict[str, list[dict]],
    *,
    gate: dict,
    boss_ok: bool,
) -> list[dict]:
    """Build the divisions[] list for the debrief response."""
    out: list[dict] = []
    cbp_gate = bool((gate.get("cbp") or {}).get("passed"))
    mc_gate = bool((gate.get("mc") or {}).get("passed"))
    gate_for = {"cbp": cbp_gate, "mc": mc_gate}
    for key in ("cbp", "mc", "practice", "boss"):
        rows = buckets.get(key, [])
        correct, total = _correct_total(rows)
        pct = round(100.0 * correct / total, 1) if total else 0.0
        out.append({
            "key": key,
            "label": _DIVISION_LABELS[key],
            "pct": pct,
            "correct": correct,
            "total": total,
            "status": _division_status(
                key, pct, total,
                gate_passed=gate_for.get(key),
                boss_ok=boss_ok,
            ),
        })
    return out


# ── 4. MARK + persistence ───────────────────────────────────────────────────

async def _write_session_mark(
    session_id: str,
    *,
    verdict: str,
    overall_pct: int,
    performance_summary: dict,
) -> None:
    """Persist the session-level mark onto the existing sessions columns.

    Reuses status / overall_score / ended_at / performance_summary_json (all
    pre-existing). status='completed' on pass, 'needs_retry' on fail.
    """
    import json as _json

    status = "completed" if verdict == VERDICT_PASSED else "needs_retry"
    db = await connect()
    try:
        await db.execute(
            """
            UPDATE sessions
               SET status = ?,
                   overall_score = ?,
                   ended_at = ?,
                   performance_summary_json = ?,
                   updated_at = ?
             WHERE id = ?
            """,
            (
                status,
                float(overall_pct),
                _utc_now_iso(),
                _json.dumps(performance_summary, ensure_ascii=False),
                _utc_now_iso(),
                session_id,
            ),
        )
        await db.commit()
    finally:
        await db.close()


# ── Public pipeline ─────────────────────────────────────────────────────────

async def finalize(
    session_id: str,
    hw_id: str,
    reflection_answers: Optional[list[str]] = None,
) -> dict:
    """Run the full finalization pipeline and return the rich debrief.

    Idempotent-ish: re-finalizing recomputes from the current attempts and
    overwrites the persisted report + session mark.

    Persists:
      • final_reports.report_json — the full debrief with a TOP-LEVEL ``verdict``
        key (the gate agent reads ``report_json.verdict``).
      • sessions.status / overall_score / ended_at / performance_summary_json.

    Returns the EXACT finalize response shape the FE depends on (see module doc
    + the route). Never includes answer-bearing data.
    """
    reflection_answers = reflection_answers or []

    # ── 1. EXTRACT ──
    attempts = await list_phase_attempts(session_id, hw_id, limit=1000)
    buckets = group_attempts_by_division(attempts)

    # ── 2. ANALYZE ──
    # Proven session metrics (weak/strong topics, mastery, boss readiness).
    metrics = await recompute_session_metrics(session_id, hw_id)
    weak_topics = list(metrics.get("weak_topics") or [])
    strong_topics = list(metrics.get("strong_topics") or [])

    # The proven scorecard — single source of truth for overall_pct + band.
    scorecard = grading.aggregate(_grading_items_from_attempts(attempts))
    overall_pct = int(scorecard.get("overall_pct") or 0)
    band = scorecard.get("band") or {"key": "novice", "name": "Novice"}

    mistake_repairs = count_mistake_repairs(buckets)

    # Gate state (CBP + MC pass) — server-authoritative, reused.
    gate = await compute_gate_state(session_id, hw_id)
    cbp_pass = bool((gate.get("cbp") or {}).get("passed"))
    mc_pass = bool((gate.get("mc") or {}).get("passed"))
    boss_ok = boss_passed(buckets.get("boss", []))

    divisions = _build_divisions(buckets, gate=gate, boss_ok=boss_ok)

    # ── 3. AI narrative (prose only; never decides the verdict) ──
    prose, ai_unavailable = await _ai_narrative(
        overall_pct=overall_pct,
        band=band,
        divisions=divisions,
        mistake_repairs=mistake_repairs,
        reflection_answers=reflection_answers,
        weak_topics=weak_topics,
        strong_topics=strong_topics,
    )

    # ── 4. MARK (deterministic verdict) ──
    verdict = compute_verdict(
        overall_pct=overall_pct,
        boss_rows=buckets.get("boss", []),
        cbp_passed=cbp_pass,
        mc_passed=mc_pass,
    )

    encouragement = (
        "Ajoyib ish! Siz bu vazifani muvaffaqiyatli yakunladingiz."
        if verdict == VERDICT_PASSED
        else _FALLBACK_ENCOURAGEMENT
    )

    debrief = {
        "verdict": verdict,
        "verdict_label": _VERDICT_LABELS[verdict],
        "overall_pct": overall_pct,
        "band": {"key": band.get("key", ""), "name": band.get("name", "")},
        "divisions": divisions,
        "weak_points": prose.get("weak_points", []),
        "strong_points": prose.get("strong_points", []),
        "next_steps": prose.get("next_steps", []),
        "narrative": prose.get("narrative", ""),
        "encouragement": encouragement,
        "redo_recommendation": (
            prose.get("redo_recommendation", "none")
            if verdict == VERDICT_NEEDS_RETRY
            else "none"
        ),
        "mistake_repairs": mistake_repairs,
        "ai_unavailable": ai_unavailable,
    }

    # ── Persist ──
    # The final_reports.report_json IS the debrief (verdict at top level so the
    # gate agent can read report_json.verdict directly).
    await upsert_final_report(session_id, hw_id, debrief)

    performance_summary = {
        "overall_pct": overall_pct,
        "band": debrief["band"],
        "divisions": divisions,
        "mistake_repairs": mistake_repairs,
        "verdict": verdict,
        "finalized_at": _utc_now_iso(),
    }
    await _write_session_mark(
        session_id,
        verdict=verdict,
        overall_pct=overall_pct,
        performance_summary=performance_summary,
    )

    return debrief


async def get_debrief(session_id: str, hw_id: str) -> Optional[dict]:
    """Return the persisted debrief (from final_reports), or None if absent.

    The stored report carries created_at / updated_at appended by the repo. We
    return it as-is — it already has the top-level ``verdict`` and never contains
    answer-bearing data (it was built that way at finalize time).
    """
    return await get_final_report(session_id, hw_id)


async def redo(session_id: str, hw_id: str) -> dict:
    """Re-route a needs_retry session back into the Practice Arc.

    Flips status needs_retry → active and CLEARS Division-3 progress so the
    runtime re-presents the Practice Arc with a reshuffle. Returns
    ``{"ok": True, "reshuffled": True, "cleared": <n>}``.

    Tradeoff (documented): we DELETE the Division-3 phase_attempts rows for this
    session rather than mark them ``superseded``. The phase_attempts table has no
    ``superseded`` column; adding one would be a schema migration for a
    history-preservation nicety that nothing currently reads. The CBP + MC
    attempts are preserved untouched, so the Practice-Arc gate
    (``compute_gate_state``, which reads ONLY CBP/MC) stays unlocked across the
    redo — the student does not re-do the learning sections, only the Practice
    Arc + Boss. We do NOT regenerate questions (out of scope); the runtime
    reshuffles the existing pool client-side.
    """
    # Flip the session back to active (only meaningful when it was needs_retry,
    # but we set it unconditionally so a redo always reopens the arc).
    db = await connect()
    try:
        await db.execute(
            """
            UPDATE sessions
               SET status = 'active',
                   updated_at = ?
             WHERE id = ?
            """,
            (_utc_now_iso(), session_id),
        )
        # Clear Division-3 progress (Practice Arc games + Final Boss) for this
        # session so the gate/runtime treat it as un-played. CBP + MC rows stay.
        placeholders = ",".join("?" for _ in PRACTICE_PHASES)
        params = [session_id, hw_id, *sorted(PRACTICE_PHASES)]
        cursor = await db.execute(
            f"""
            DELETE FROM phase_attempts
             WHERE session_id = ?
               AND hw_id = ?
               AND phase IN ({placeholders})
            """,
            params,
        )
        cleared = cursor.rowcount
        await db.commit()
    finally:
        await db.close()

    return {"ok": True, "reshuffled": True, "cleared": int(cleared or 0)}
