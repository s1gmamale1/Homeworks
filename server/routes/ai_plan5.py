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
    # ADVISORY ONLY (Boss-Arena spec §6). The server derives the real HP from
    # the homework's grade band + boss_meta.starting_hp_override and ignores
    # this value as the source of truth. Field kept for backward-compat with
    # older clients that still send it.
    max_hp: int = Field(default=100, ge=10, le=1000)
    trials_left: int = Field(default=7, ge=1, le=30)
    initial_difficulty: str = "medium"
    # 2026-05-14: explicit-intent flag — when True, /boss/start archives any
    # active row for this (session_id, homework_id) regardless of its age and
    # spawns a fresh session. Frontend should send this when the student
    # clicks an explicit "Restart boss" / "New attempt" action so trials_left
    # is reset cleanly. Default False preserves the legacy resume-on-refresh
    # behavior for the staleness window.
    force_fresh: bool = False


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
    # Boss-Arena Why→How→What (spec §4/§9). PROMPT text — safe to send to the
    # client. NEVER add answer/rubric/expected/coverage-rubric fields here.
    scenario: str = ""
    why: str = ""
    how: str = ""
    what: str = ""
    target_skill: str
    difficulty: str
    why_this_question: str
    boss_session_id: str


class BossSubmitAnswerRequest(BaseModel):
    boss_session_id: str
    question_id: str
    student_answer: str
    # Anti-cheat signal ingestion (ADVISORY — never alters grading/HP/status).
    # Optional; absent = "unknown / not measured" → zero integrity signal.
    client_time_ms: Optional[int] = None
    paste_detected: Optional[bool] = None


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
    # End-of-boss outcome (Bug #5 fix, 2026-05-14). Optional fields populated
    # only on terminal status transitions ('won' / 'failed'). The runtime
    # reads these to render the result card's star count + XP pill; previously
    # the server never sent them and students saw 0 stars / +0 XP even after
    # answering every question correctly.
    outcome: Optional[str] = None       # "expert" | "strong" | "passing" | "hali_emas"
    stars: Optional[int] = None         # 0–3
    outcome_xp: Optional[int] = None    # cumulative XP awarded
    # Per-axis Why→How→What coverage (Boss-Arena spec §4/§9). These are the
    # STUDENT's own per-axis scores for the answer they just submitted — they
    # are NOT answer-bearing (no expected/rubric text), so they're safe to
    # surface to the client to render coverage bars. Populated only when the
    # verdict carries a coverage breakdown; None for legacy/flat verdicts.
    coverage: Optional[dict[str, float]] = None
    # Soft-friction nudge (anti-cheat wiring). Populated for actionable advisory
    # integrity flags such as sudden mastery or an opted-in paste-on-assessment
    # event. It NEVER gates progress. is_correct / score / hp / boss_status are
    # already final and returned alongside. We deliberately do NOT leak
    # reason_code / thresholds to the client (teacher-only intelligence).
    integrity_nudge: Optional[dict] = None


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


# Boss session staleness (2026-05-13 audit fix; 2026-05-14 tightened).
#
# A boss_sessions row in status='active' is reused by /boss/start to preserve
# state across page refreshes. But "page refresh" was the only intended use
# case — same-day testing across hours quietly accumulated trials_left
# depletion. Student starts the boss, gets 2 questions instead of 5, because
# 3 trials were consumed during an earlier abandoned attempt.
#
# 30 minutes is the new threshold: covers legitimate breaks (snack, bathroom,
# answering the door) without spanning multi-hour gaps that the student would
# mentally consider a separate attempt. Pair with the new `force_fresh` flag
# on BossStartRequest — frontend can send it explicitly when the student
# clicks "Restart boss" or after a "Resume / New attempt" dialog.
_SESSION_STALE_AFTER_SECONDS = 30 * 60  # 30 minutes (was 6 hours)


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


# Boss-Arena (spec §6) — "full accuracy" for combo purposes means a correct
# answer that lands in the top accuracy tier (>= 0.85 → 1.0). Lower-scoring
# correct answers count toward correctness but NOT toward a combo.
_FULL_ACCURACY_SCORE = 0.85


def _combo_bonus_for(
    prior_attempts: list[dict[str, Any]], *, hints_used: int,
) -> float:
    """Boss-Arena combo bonus (spec §6).

    Returns ``boss_dynamic.COMBO_BONUS_FACTOR`` (1.2) when the student enters
    this roll on a tail streak of >= ``COMBO_STREAK_THRESHOLD`` consecutive
    full-accuracy correct answers AND has used no hints; otherwise 1.0.

    The streak is computed from the chronological boss attempts recorded
    BEFORE the current submit, walking from the most recent backward — any
    non-full-accuracy attempt breaks it. Hint use (hints_used > 0) suppresses
    the bonus entirely per spec ("reset on any wrong answer OR hint use").
    """
    if hints_used and int(hints_used) > 0:
        return 1.0
    tail_streak = 0
    for a in reversed(prior_attempts or []):  # most-recent first
        is_full = (
            a.get("correct") == 1
            and float(a.get("score") or 0.0) >= _FULL_ACCURACY_SCORE
        )
        if is_full:
            tail_streak += 1
        else:
            break
    if tail_streak >= boss_dynamic.COMBO_STREAK_THRESHOLD:
        return boss_dynamic.COMBO_BONUS_FACTOR
    return 1.0


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
    if existing and not req.force_fresh and _is_session_fresh(existing):
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
        # Stale OR caller explicitly asked for a fresh session — mark
        # abandoned so the next get_active query skips it, and fall through
        # to create a fresh session row.
        reason = "force_fresh" if req.force_fresh else "stale"
        try:
            await boss_session_repo.update_boss_session(
                existing["id"], status="abandoned",
            )
            _log.info(
                "boss_session_archived id=%s reason=%s updated_at=%s",
                existing["id"], reason, existing.get("updated_at"),
            )
        except Exception as exc:
            _log.warning("failed to archive boss session: %s", exc)

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

    # Boss-Arena (spec §6): HP is SERVER-AUTHORITATIVE. Derive it from the
    # homework's grade band + the optional starting_hp_override. `req.max_hp`
    # is now advisory only (the field is kept for backward-compat but is NOT
    # the source of truth) — a client can no longer dictate the boss's HP.
    content_json = (homework or {}).get("content_json") or {}
    boss_meta = content_json.get("boss_meta") or {}
    meta_block = content_json.get("meta") or {}
    grade_band = (
        boss_meta.get("grade_band")
        # fall through to a raw numeric grade if no explicit band
        or content_json.get("grade")
        or meta_block.get("grade")
        or (homework or {}).get("grade")
    )
    hp_override = boss_meta.get("starting_hp_override")
    derived_max_hp = boss_dynamic.starting_hp_for(grade_band, hp_override)

    boss_session_id = f"bs_{uuid.uuid4().hex[:16]}"
    state = await boss_session_repo.create_boss_session(
        boss_session_id,
        req.session_id,
        req.homework_id,
        max_hp=derived_max_hp,
        trials_left=effective_trials,
        current_difficulty=req.initial_difficulty,
        weak_topics=ctx.weak_topics,
        strong_topics=ctx.strong_topics,
    )
    await _record_event(state, "boss_started", {
        "boss_session_id": boss_session_id,
        "max_hp": derived_max_hp,
        "max_hp_source": "starting_hp_override" if hp_override else "grade_band",
        "grade_band": grade_band,
        "client_requested_max_hp": req.max_hp,  # advisory only — not trusted
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
            # Boss-Arena Why→How→What (spec §4/§9) — PROMPT text, persisted so
            # /boss/state can rehydrate the structured shape on resume. These
            # are NOT answer-bearing.
            "scenario": generated.scenario,
            "why": generated.why,
            "how": generated.how,
            "what": generated.what,
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
        scenario=generated.scenario,
        why=generated.why,
        how=generated.how,
        what=generated.what,
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

    # Bug B (2026-05-14): pass the homework's language to the answer-checker
    # so feedback comes back in the student's language (not "typically Uzbek"
    # like the v1 prompt hardcoded) and misconception_tags avoid English
    # snake_case on uz/ru. Falls back to subject-inferred language when
    # content_json.language is null (same logic as boss_context_builder).
    homework = await db.get_homework(state["homework_id"])
    content_json = (homework or {}).get("content_json") or {}
    answer_language = (
        content_json.get("language") or (homework or {}).get("language") or None
    )
    if not answer_language:
        answer_language = boss_context_builder._infer_language_from_subject(
            content_json.get("subject") or (homework or {}).get("subject")
        )

    # Anti-cheat (ADVISORY): snapshot the pre-boss mastery_score BEFORE grading
    # + state update, so the sudden-mastery detector compares the established
    # baseline against the boss's in-progress correct-rate. Best-effort; a miss
    # yields None (= no signal). Also record a paste during this submit.
    pre_boss_mastery: Optional[float] = None
    try:
        from ..services.integrity_wiring import _mastery_score_for_session

        pre_boss_mastery = await _mastery_score_for_session(
            state["session_id"], state["homework_id"]
        )
    except Exception as _pm_exc:
        _log.warning("pre-boss mastery read failed (non-fatal): %s", _pm_exc)
    if req.paste_detected:
        try:
            await session_events_repo.add_session_event(
                session_id=state["session_id"],
                hw_id=state["homework_id"],
                event_type="integrity:paste",
                payload={"phase": "boss", "question_id": req.question_id},
                phase="boss",
                question_id=req.question_id,
            )
        except Exception as _paste_exc:
            _log.warning(
                "integrity:paste session_event failed (non-fatal): %s", _paste_exc
            )

    verdict = await boss_dynamic.check_boss_answer(
        question_text=q["question_text"],
        expected_answer=q["expected_answer"],
        rubric=q["rubric"],
        student_answer=req.student_answer,
        target_skill=(q.get("topic_tags") or [""])[0],
        difficulty=state["current_difficulty"],
        language=answer_language,
        session_id=state["session_id"],
        homework_id=state["homework_id"],
    )

    # Boss-Arena (spec §6): the session's REAL hints_used drives both the
    # damage hint-penalty and the outcome scorer. Legacy rows may store NULL,
    # so coalesce to 0. (A hint-request endpoint is out of scope for this PR;
    # hints_used stays 0 until the frontend wires hint requests — but every
    # consumer now READS the column.)
    hints_used = int(state.get("hints_used") or 0)

    # Combo bonus (spec §6): +20% damage when the student enters this roll on a
    # streak of >= COMBO_STREAK_THRESHOLD consecutive full-accuracy correct
    # answers. The streak resets on any wrong answer OR hint use. We derive it
    # from the boss attempts recorded BEFORE this submit (chronological), so
    # the current answer doesn't count toward its own combo.
    prior_boss_attempts = await attempts_repo.list_phase_attempts(
        state["session_id"], state["homework_id"], phase="boss", limit=1000,
    )
    combo_bonus = _combo_bonus_for(prior_boss_attempts, hints_used=hints_used)

    damage = boss_dynamic.calculate_damage(
        verdict.score,
        state["current_difficulty"],
        multiplier=verdict.damage_multiplier,
        coverage=verdict.coverage or None,
        hints_used=hints_used,
        combo_bonus=combo_bonus,
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

    # Resolve boss arc state-machine status. NOTE (Bug #6, 2026-05-14):
    # `boss_status` is a state-machine label describing how the arc ended —
    # 'won' (HP went to 0), 'failed' (trials ran out before HP did), 'active'
    # (arc still ongoing). It is NOT a value judgment of the student's
    # performance. The runtime never shows this string to the student
    # directly; it only uses it to decide *when* to fire the result card.
    # The student-facing tier ('expert' / 'strong' / 'passing' / 'hali_emas')
    # is computed below by compute_boss_outcome from correctness + HP, so a
    # 'failed' arc with strong performance correctly shows as 'passing' on
    # the result card. The two concepts disagree by design.
    if new_hp <= 0:
        new_status = "won"
    elif new_trials <= 0:
        new_status = "failed"
    else:
        new_status = "active"

    # Bug #5 fix (2026-05-14): compute outcome/stars/XP when the arc ends so
    # the runtime can render the result card with real numbers. Previously
    # these fields were missing → runtime defaulted to 0 stars / +0 XP.
    outcome_payload: dict[str, Any] = {}
    if new_status != "active":
        correct_count = sum(1 for a in all_attempts if a.get("correct") == 1)
        # Include THIS attempt — it's the one that triggered the transition
        # and hasn't been listed by list_phase_attempts above (chronological
        # ordering means the current row may not yet be visible in some
        # backends). Safe to count it from `verdict.is_correct`.
        if all_attempts and all_attempts[-1].get("id") == attempt_id:
            total_attempts = len(all_attempts)
        else:
            total_attempts = len(all_attempts) + 1
            if verdict.is_correct:
                correct_count += 1
        outcome_payload = boss_dynamic.compute_boss_outcome(
            hp=new_hp,
            max_hp=state["max_hp"],
            correct_count=correct_count,
            total_attempts=total_attempts,
            hints_used=hints_used,  # Boss-Arena: real session hints_used (was hardcoded 0)
            status=new_status,
        )

    # Boss-Arena (spec §6): persist the per-session tallies atomically.
    # total_attempts increments every submit; correct_count when is_correct.
    # These columns back compute_boss_outcome on resume + future analytics.
    updated = await boss_session_repo.update_boss_session(
        req.boss_session_id,
        hp=new_hp,
        trials_left=new_trials,
        current_difficulty=new_difficulty,
        status=new_status,
        increment_total_attempts=1,
        increment_correct_count=1 if verdict.is_correct else 0,
    )
    await _record_event(updated or state, "boss_answer_submitted", {
        "question_id": req.question_id,
        "is_correct": verdict.is_correct,
        "score": verdict.score,
        "coverage": verdict.coverage or {},
        "damage": damage,
        "combo_bonus": combo_bonus,
        "hints_used": hints_used,
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

    # Anti-cheat flag engine (ADVISORY — best-effort, post-grading). The boss is
    # an assessment. correct_count / total_attempts come from the updated boss
    # row (post-increment); the correct-rate is correct_count / max(1, total).
    # Enrolls any flags into the review queue and may return a soft-friction
    # nudge. NONE of this changes is_correct / score / hp / boss_status above;
    # a failure is swallowed.
    integrity_nudge = None
    try:
        from ..services.integrity_wiring import evaluate_boss_submit

        row = updated or state
        total_attempts = int(row.get("total_attempts") or 0)
        correct_count = int(row.get("correct_count") or 0)
        grade_for_signal = (
            content_json.get("grade") or (homework or {}).get("grade")
        )
        boss_meta = content_json.get("boss_meta")
        from ..services.integrity_wiring import clamp_client_time_ms

        integrity_nudge = await evaluate_boss_submit(
            session_id=state["session_id"],
            hw_id=state["homework_id"],
            question_id=req.question_id,
            time_ms=clamp_client_time_ms(req.client_time_ms),
            paste_detected=req.paste_detected,
            pre_assessment_mastery=pre_boss_mastery,
            correct_count=correct_count,
            total_attempts=total_attempts,
            grade=grade_for_signal,
            boss_meta=boss_meta,
        )
    except Exception as _integrity_exc:
        _log.warning(
            "boss integrity flag engine failed (non-fatal): %s", _integrity_exc
        )

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
        outcome=outcome_payload.get("outcome"),
        stars=outcome_payload.get("stars"),
        outcome_xp=outcome_payload.get("outcome_xp"),
        coverage=verdict.coverage or None,
        integrity_nudge=integrity_nudge,
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
            # Boss-Arena Why→How→What (spec §4/§9) — surface the structured
            # PROMPT parts on resume too. They live in source_context (free-
            # form JSON), are PROMPT text only, and never carry answers.
            src_ctx = q.get("source_context") or {}
            current_q_summary = {
                "question_id": qid,
                "question_text": q.get("question_text") or "",
                "scenario": src_ctx.get("scenario") or "",
                "why": src_ctx.get("why") or "",
                "how": src_ctx.get("how") or "",
                "what": src_ctx.get("what") or "",
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
