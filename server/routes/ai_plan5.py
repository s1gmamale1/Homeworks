"""Plan 5 — Dynamic Boss AI endpoints.

Five new net-new endpoints under ``/ai/boss/*``. The legacy
``/ai/boss-turn`` (defined in ``ai.py``) and the static
``content_json.boss_questions`` flow stay untouched as fallbacks; per
Plan 5 §12, the dynamic path opts in only when the runtime calls these
new endpoints with a ``session_id``.

Hard contracts:

  - Backend owns HP, trials, difficulty (Plan 5 §13 + CLAUDE.md "Backend
    owns state").
  - Generator output is validated server-side before storage; rejected
    questions are not persisted.
  - The frontend never receives ``expected_answer`` / rubric of a generated
    boss question — only ``question_text`` + ``difficulty`` + ``target_skill``.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import db
from ..db import boss_session_repo, boss_repo, session_events_repo, attempts_repo, session_metrics_repo
from ..services import boss_context_builder, boss_dynamic


router = APIRouter(tags=["ai-boss-plan5"])
_log = logging.getLogger("nets.boss_plan5")


# ---- Request / response models -------------------------------------------

class BossStartRequest(BaseModel):
    session_id: str
    homework_id: str
    max_hp: int = Field(default=100, ge=10, le=1000)
    trials_left: int = Field(default=7, ge=1, le=30)
    initial_difficulty: str = "medium"


class BossStartResponse(BaseModel):
    boss_session_id: str
    hp: int
    max_hp: int
    trials_left: int
    current_difficulty: str
    weak_topics: list[str]
    strong_topics: list[str]
    missing_context_flags: list[str]


class BossGenerateQuestionRequest(BaseModel):
    boss_session_id: str
    # `recent_boss_phrases` lets the runtime forward the last few boss-line
    # openings so the generator can vary surface form. Optional.
    recent_boss_phrases: list[str] = []


class BossGenerateQuestionResponse(BaseModel):
    question_id: str
    question_text: str
    target_skill: str
    difficulty: str
    why_this_question: str
    boss_session_id: str


class BossSubmitAnswerRequest(BaseModel):
    boss_session_id: str
    question_id: str
    student_answer: str


class BossSubmitAnswerResponse(BaseModel):
    is_correct: bool
    score: float
    confidence: float
    feedback: str
    damage: int
    hp: int
    trials_left: int
    current_difficulty: str
    boss_status: str  # "active" | "won" | "failed"
    should_retry_same_skill: bool
    misconception_tags: list[str]


class BossStateRequest(BaseModel):
    boss_session_id: str


class BossGiveUpRequest(BaseModel):
    boss_session_id: str


# ---- Helpers --------------------------------------------------------------

def _boss_state_to_response(state: dict[str, Any], extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Project the row to a frontend-safe shape (no answer keys, no rubrics)."""
    out = {
        "boss_session_id": state["id"],
        "session_id": state["session_id"],
        "homework_id": state["homework_id"],
        "status": state["status"],
        "hp": state["hp"],
        "max_hp": state["max_hp"],
        "trials_left": state["trials_left"],
        "current_difficulty": state["current_difficulty"],
        "current_question_id": state.get("current_question_id"),
        "asked_question_ids": state.get("asked_question_ids") or [],
        "weak_topics": state.get("weak_topics") or [],
        "strong_topics": state.get("strong_topics") or [],
    }
    if extra:
        out.update(extra)
    return out


# Boss session staleness (2026-05-13 audit fix).
#
# A boss_sessions row in status='active' is reused by /boss/start to preserve
# state across page refreshes. But "page refresh" was the only intended use
# case — multi-day testing made the same row outlive its useful lifetime,
# depleting trials_left, accumulating asked_question_ids, and trapping the
# next playthrough in a 'failed' state before Q1 even rendered.
#
# 6 hours is conservative: long enough to cover legitimate "student takes
# a break mid-homework," short enough to auto-archive sessions abandoned
# overnight or across days.
_SESSION_STALE_AFTER_SECONDS = 6 * 60 * 60  # 6 hours


def _is_session_fresh(state: dict[str, Any]) -> bool:
    """Return True if the session's updated_at is recent enough to reuse.

    Tolerant of missing/malformed updated_at — treats unparseable as stale
    so we err on the side of spawning fresh sessions over reusing stuck ones.
    """
    raw = state.get("updated_at")
    if not raw:
        return False
    try:
        # SQLite ISO timestamps may or may not carry timezone info; both
        # branches are handled.
        ts = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return False
    age = datetime.now(timezone.utc) - ts
    return age <= timedelta(seconds=_SESSION_STALE_AFTER_SECONDS)


async def _load_asked_questions(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Hydrate the asked queue into question_text+target_skill summaries.

    Used as anti-repetition input to the generator. Strips expected_answer
    and rubric — the generator must not see prior answer keys (Plan 5 §10).
    """
    out: list[dict[str, Any]] = []
    for qid in state.get("asked_question_ids") or []:
        q = await boss_repo.get_generated_boss_question(
            qid, state["session_id"], state["homework_id"],
        )
        if not q:
            continue
        # Re-derive a target_skill rollup from topic_tags (storage uses tags
        # since the storage helper predates Plan 5; the first tag is the
        # generator's target_skill in our writes).
        topic_tags = q.get("topic_tags") or []
        target_skill = topic_tags[0] if topic_tags else ""
        out.append({
            "question_id": qid,
            "question_text": q.get("question_text") or "",
            "target_skill": target_skill,
            "difficulty": q.get("difficulty") or "",
        })
    return out


async def _record_event(
    state: dict[str, Any], event_type: str, payload: dict[str, Any],
) -> None:
    """Best-effort event log. Never raises into the request handler."""
    try:
        await session_events_repo.add_session_event(
            session_id=state["session_id"],
            hw_id=state["homework_id"],
            event_type=event_type,
            payload=payload,
            phase="boss",
        )
    except Exception as exc:
        _log.warning("session_events insert failed (%s): %s", event_type, exc)


def _streaks_from_recent_attempts(attempts: list[dict[str, Any]]) -> boss_dynamic.BossStreaks:
    """Walk the most recent attempts in chronological order and compute the
    current correct/wrong streak. Plan 5 §8 needs both for the difficulty
    decision; if we only tracked one, ties would be ambiguous.
    """
    correct_streak = 0
    wrong_streak = 0
    for a in attempts:  # already chronological per attempts_repo
        if a.get("correct") == 1:
            correct_streak += 1
            wrong_streak = 0
        else:
            wrong_streak += 1
            correct_streak = 0
    return boss_dynamic.BossStreaks(correct_streak=correct_streak, wrong_streak=wrong_streak)


# ---- Endpoints ------------------------------------------------------------

@router.post("/ai/boss/start", response_model=BossStartResponse)
async def boss_start(req: BossStartRequest):
    homework = await db.get_homework(req.homework_id)
    if not homework:
        raise HTTPException(404, detail={"error": f"homework {req.homework_id} not found", "code": "HW_NOT_FOUND"})

    if req.initial_difficulty not in boss_dynamic.ALLOWED_DIFFICULTIES:
        raise HTTPException(400, detail={
            "error": f"initial_difficulty must be one of {list(boss_dynamic.ALLOWED_DIFFICULTIES)}",
            "code": "BOSS_INVALID_DIFFICULTY",
        })

    # Idempotence: if there is already an active boss session for (session, hw),
    # return its state instead of spawning a duplicate. Plan 5 §11 acceptance
    # test 5 (Boss state survives refresh) depends on this.
    #
    # Staleness check (2026-05-13 audit fix): the original idempotence rule
    # assumed a single linear playthrough — refresh mid-session reuses state.
    # But multi-day testing across many runs accumulated trials_left
    # depletion (start with 7, each run consumes one, after 7 runs the next
    # run hits trials=0 immediately and the boss is "failed" before the
    # student even sees Q1). We now treat any session whose updated_at is
    # older than _SESSION_STALE_AFTER_SECONDS as abandoned and fall through
    # to spawning a fresh row.
    existing = await boss_session_repo.get_active_boss_session_for(req.session_id, req.homework_id)
    if existing and _is_session_fresh(existing):
        return BossStartResponse(
            boss_session_id=existing["id"],
            hp=existing["hp"],
            max_hp=existing["max_hp"],
            trials_left=existing["trials_left"],
            current_difficulty=existing["current_difficulty"],
            weak_topics=existing.get("weak_topics") or [],
            strong_topics=existing.get("strong_topics") or [],
            missing_context_flags=[],
        )
    if existing:
        # Stale — mark abandoned so the next get_active query skips it, and
        # fall through to create a fresh session row.
        try:
            await boss_session_repo.update_boss_session(
                existing["id"], status="abandoned",
            )
            _log.info(
                "boss_session_archived_stale id=%s updated_at=%s",
                existing["id"], existing.get("updated_at"),
            )
        except Exception as exc:
            _log.warning("failed to archive stale boss session: %s", exc)

    ctx = await boss_context_builder.build_boss_context(
        req.session_id, req.homework_id,
    )
    # 2026-05-13 design decision: trials_left should match the size of the
    # authored boss_questions[] reference pool. One Kimi-generated question
    # per author-supplied anchor — semantically cleaner than a fixed cap
    # disconnected from the homework's content. The request's trials_left is
    # treated as advisory (frontend default is still 7). Falls back to 5
    # when the homework has no authored boss questions.
    authored_pool_size = len(ctx.authored_question_stems or [])
    _FALLBACK_TRIALS = 5
    effective_trials = authored_pool_size if authored_pool_size > 0 else _FALLBACK_TRIALS
    boss_session_id = f"bs_{uuid.uuid4().hex[:16]}"
    state = await boss_session_repo.create_boss_session(
        boss_session_id,
        req.session_id,
        req.homework_id,
        max_hp=req.max_hp,
        trials_left=effective_trials,
        current_difficulty=req.initial_difficulty,
        weak_topics=ctx.weak_topics,
        strong_topics=ctx.strong_topics,
    )
    await _record_event(state, "boss_started", {
        "boss_session_id": boss_session_id,
        "max_hp": req.max_hp,
        "trials_left": effective_trials,
        "trials_source": "authored_pool_size" if authored_pool_size > 0 else "fallback_default",
        "weak_topics": ctx.weak_topics,
        "strong_topics": ctx.strong_topics,
    })
    try:
        await session_metrics_repo.recompute_session_metrics(
            session_id=req.session_id,
            hw_id=req.homework_id,
        )
    except Exception as exc:
        _log.warning("recompute_session_metrics failed on boss-start: %s", exc)
    return BossStartResponse(
        boss_session_id=boss_session_id,
        hp=state["hp"],
        max_hp=state["max_hp"],
        trials_left=state["trials_left"],
        current_difficulty=state["current_difficulty"],
        weak_topics=state["weak_topics"],
        strong_topics=state["strong_topics"],
        missing_context_flags=ctx.missing_context_flags,
    )


@router.post("/ai/boss/generate-question", response_model=BossGenerateQuestionResponse)
async def boss_generate_question(req: BossGenerateQuestionRequest):
    state = await boss_session_repo.get_boss_session(req.boss_session_id)
    if not state:
        raise HTTPException(404, detail={"error": "boss session not found", "code": "BOSS_NOT_FOUND"})
    if state["status"] != "active":
        raise HTTPException(409, detail={"error": f"boss session is {state['status']}", "code": "BOSS_NOT_ACTIVE"})

    asked = await _load_asked_questions(state)
    ctx = await boss_context_builder.build_boss_context(
        state["session_id"], state["homework_id"],
        asked_questions=asked,
        recent_boss_phrases=req.recent_boss_phrases,
    )

    try:
        generated = await boss_dynamic.generate_boss_question(
            ctx.to_dict(),
            difficulty=state["current_difficulty"],
        )
    except boss_dynamic.BossQuestionRejected as exc:
        _log.warning("boss generation rejected: %s", exc.reason)
        raise HTTPException(502, detail={
            "error": f"boss question generation failed: {exc.reason}",
            "code": "BOSS_GEN_REJECTED",
        })

    question_id = f"gbq_{uuid.uuid4().hex[:16]}"
    # Storage repo predates Plan 5 — it stores topic_tags rather than a
    # dedicated target_skill column. We pack target_skill as the first tag
    # and any source phase ids after it, so _load_asked_questions can recover
    # both. source_phase_ids also rides on source_context for traceability.
    topic_tags = [generated.target_skill] + list(generated.source_phase_ids)
    await boss_repo.create_generated_boss_question(
        question_id=question_id,
        session_id=state["session_id"],
        hw_id=state["homework_id"],
        difficulty=generated.difficulty,
        topic_tags=topic_tags,
        question_text=generated.question_text,
        expected_answer=generated.expected_answer,
        rubric=generated.rubric,
        source_context={
            "boss_session_id": state["id"],
            "why_this_question": generated.why_this_question,
            "source_phase_ids": generated.source_phase_ids,
            "weak_topics_snapshot": ctx.weak_topics,
        },
    )
    await boss_session_repo.append_asked_question(state["id"], question_id)
    await _record_event(state, "boss_question_generated", {
        "question_id": question_id,
        "target_skill": generated.target_skill,
        "difficulty": generated.difficulty,
    })

    return BossGenerateQuestionResponse(
        question_id=question_id,
        question_text=generated.question_text,
        target_skill=generated.target_skill,
        difficulty=generated.difficulty,
        why_this_question=generated.why_this_question,
        boss_session_id=state["id"],
    )


@router.post("/ai/boss/submit-answer", response_model=BossSubmitAnswerResponse)
async def boss_submit_answer(req: BossSubmitAnswerRequest):
    state = await boss_session_repo.get_boss_session(req.boss_session_id)
    if not state:
        raise HTTPException(404, detail={"error": "boss session not found", "code": "BOSS_NOT_FOUND"})
    if state["status"] != "active":
        raise HTTPException(409, detail={"error": f"boss session is {state['status']}", "code": "BOSS_NOT_ACTIVE"})

    q = await boss_repo.get_generated_boss_question(
        req.question_id, state["session_id"], state["homework_id"],
    )
    if not q:
        raise HTTPException(404, detail={
            "error": f"boss question {req.question_id} not found for this session",
            "code": "BOSS_Q_NOT_FOUND",
        })

    verdict = await boss_dynamic.check_boss_answer(
        question_text=q["question_text"],
        expected_answer=q["expected_answer"],
        rubric=q["rubric"],
        student_answer=req.student_answer,
        target_skill=(q.get("topic_tags") or [""])[0],
        difficulty=state["current_difficulty"],
    )

    damage = boss_dynamic.calculate_damage(
        verdict.score, state["current_difficulty"], multiplier=verdict.damage_multiplier,
    )
    new_hp = max(0, state["hp"] - damage)
    new_trials = max(0, state["trials_left"] - 1)

    # Persist this attempt for the metrics + next-difficulty calculation.
    # Bug #7 fix (2026-05-13 audit): attempt_number was hardcoded to 1, so
    # retries on the same question_id produced duplicate rows that inflated
    # _streaks_from_recent_attempts. Query prior attempts for this question
    # and increment.
    import json as _json
    prior_for_q = await attempts_repo.attempts_for_question(
        state["session_id"], state["homework_id"], req.question_id,
    )
    attempt_number = len(prior_for_q) + 1
    attempt_id = await attempts_repo.add_phase_attempt(
        session_id=state["session_id"],
        hw_id=state["homework_id"],
        phase="boss",
        subphase=None,
        question_id=req.question_id,
        attempt_number=attempt_number,
        student_answer=req.student_answer,
        checker_source="boss_judge",
        correct=1 if verdict.is_correct else 0,
        score=verdict.score,
        confidence=verdict.confidence,
        feedback=verdict.feedback_to_student,
        misconception_tags_json=_json.dumps(verdict.misconception_tags or []),
    )
    await boss_repo.mark_boss_question_used(
        req.question_id, state["session_id"], state["homework_id"],
    )

    # Adapt difficulty using all boss attempts so far (chronological).
    all_attempts = await attempts_repo.list_phase_attempts(
        state["session_id"], state["homework_id"], phase="boss", limit=1000,
    )
    streaks = _streaks_from_recent_attempts(all_attempts)
    new_difficulty = boss_dynamic.next_difficulty(
        state["current_difficulty"], verdict.score, streaks,
    )

    # Resolve boss outcome.
    if new_hp <= 0:
        new_status = "won"
    elif new_trials <= 0:
        new_status = "failed"
    else:
        new_status = "active"

    updated = await boss_session_repo.update_boss_session(
        req.boss_session_id,
        hp=new_hp,
        trials_left=new_trials,
        current_difficulty=new_difficulty,
        status=new_status,
    )
    await _record_event(updated or state, "boss_answer_submitted", {
        "question_id": req.question_id,
        "is_correct": verdict.is_correct,
        "score": verdict.score,
        "damage": damage,
        "hp_after": new_hp,
        "trials_left_after": new_trials,
        "next_difficulty": new_difficulty,
        "attempt_id": attempt_id,
        "ai_unavailable": verdict.ai_unavailable,
    })
    if new_status != "active":
        await _record_event(updated or state, "boss_completed", {
            "outcome": new_status,
            "hp_remaining": new_hp,
            "trials_left": new_trials,
        })

    return BossSubmitAnswerResponse(
        is_correct=verdict.is_correct,
        score=verdict.score,
        confidence=verdict.confidence,
        feedback=verdict.feedback_to_student,
        damage=damage,
        hp=new_hp,
        trials_left=new_trials,
        current_difficulty=new_difficulty,
        boss_status=new_status,
        should_retry_same_skill=verdict.should_retry_same_skill,
        misconception_tags=verdict.misconception_tags,
    )


@router.post("/ai/boss/state")
async def boss_state(req: BossStateRequest):
    state = await boss_session_repo.get_boss_session(req.boss_session_id)
    if not state:
        raise HTTPException(404, detail={"error": "boss session not found", "code": "BOSS_NOT_FOUND"})

    current_q_summary: Optional[dict[str, Any]] = None
    qid = state.get("current_question_id")
    if qid:
        q = await boss_repo.get_generated_boss_question(
            qid, state["session_id"], state["homework_id"],
        )
        if q:
            topic_tags = q.get("topic_tags") or []
            current_q_summary = {
                "question_id": qid,
                "question_text": q.get("question_text") or "",
                "difficulty": q.get("difficulty") or state["current_difficulty"],
                "target_skill": topic_tags[0] if topic_tags else "",
            }
    return _boss_state_to_response(state, {"current_question": current_q_summary})


@router.post("/ai/boss/give-up")
async def boss_give_up(req: BossGiveUpRequest):
    state = await boss_session_repo.get_boss_session(req.boss_session_id)
    if not state:
        raise HTTPException(404, detail={"error": "boss session not found", "code": "BOSS_NOT_FOUND"})
    if state["status"] != "active":
        return _boss_state_to_response(state)
    updated = await boss_session_repo.update_boss_session(
        req.boss_session_id, status="abandoned",
    )
    await _record_event(updated or state, "boss_completed", {
        "outcome": "abandoned",
        "hp_remaining": state["hp"],
        "trials_left": state["trials_left"],
    })
    return _boss_state_to_response(updated or state)


__all__ = ["router"]
