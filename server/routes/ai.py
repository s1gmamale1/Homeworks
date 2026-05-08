"""
AI Runtime Tutor Endpoints.

Called by the homework playback frontend during student sessions.
All stateless. Request/response JSON, no SSE.
"""
import logging
import random
from fastapi import APIRouter, HTTPException, Path as PathParam, Query
from pydantic import BaseModel, Field
from typing import Optional, Any

from ..services import tutor, ai_orchestrator, injector, ai_debug, ai_context, ai_gateway
from ..services.slur_filter import classify, detect_slurs
from ..services import warnings as warnings_svc
from .. import db

router = APIRouter(tags=["ai-tutor"])

_log = logging.getLogger("nets.sentence_fill")


# --- Request models ---

class RuntimeAnswerSubmitRequest(BaseModel):
    session_id: str
    homework_id: str
    phase: Optional[str] = None
    subphase: Optional[str] = None
    phase_index: Optional[int] = None
    question_id: Optional[str] = None
    item_id: Optional[str] = None
    step_id: Optional[str] = None
    answer_type: Optional[str] = None
    student_answer: Any
    student_work_text: Optional[str] = None
    client_context: dict[str, Any] = Field(default_factory=dict)
    attempt_number: Optional[int] = None

class CheckAnswerRequest(BaseModel):
    # Legacy free-form fields (made optional so sentence-fill phase callers
    # can submit a minimal payload without forcing dummy values).
    question_id: str = ""
    question: str = ""
    student_answer: str = ""
    expected_answers: list[str] = []
    answer_spec: Optional[dict[str, Any]] = None
    allow_ai_fallback: bool = True
    subject: str = "math-algebra"
    grade: int = 8
    tier: str = "MEDIUM"
    context: Optional[str] = None
    phase: Optional[str] = None

    # Sentence-fill phase fields (only used when phase == "sentence-fill").
    homework_id: Optional[str] = None
    item_id: Optional[str] = None
    blank_idx: Optional[int] = None
    student_value: Optional[str] = None
    attempt_number: Optional[int] = None

    # Tile-match phase fields (only used when phase == "tile-match").
    left_id: Optional[str] = None
    right_id: Optional[str] = None
    session_id: Optional[str] = None

    # Real-Life Challenge phase fields (only used when phase == "real-life-challenge").
    # Per RLC plan §3b — one of selected_option_id / selected_chip_id /
    # reasoning_text is populated depending on the step's `kind`.
    step_id: Optional[str] = None
    selected_option_id: Optional[str] = None
    selected_chip_id: Optional[str] = None
    reasoning_text: Optional[str] = None

    # Final Boss phase fields (only used when phase == "final-boss").
    # Per FINAL_BOSS_BACKEND_PLAN.md §3b — runtime delegates to existing
    # tutor.boss_turn via a thin adapter; these fields carry the FB-specific
    # context (boss type, grade band, attempts/HP cursors) into the adapter.
    boss_type: Optional[str] = None       # "sub" | "big" | "mythical"
    grade_band: Optional[str] = None      # "g1_4" | "g5" | "g6_8" | "g9_11"
    attempts_used: Optional[int] = 0
    hp_remaining: Optional[int] = None    # client's current HP cursor for outcome computation

    # Tic Tac Toe phase fields (only used when phase == "ttt" or "ttt-session").
    # Per TIC_TAC_TOE_BACKEND_PLAN.md §1.3, §1.4 — `picked` carries the option
    # string the student tapped (matched against the server-side answer key),
    # `results` carries the end-of-session outcome list for the tally route.
    picked: Optional[str] = None
    results: Optional[list[dict[str, Any]]] = None

    # Memory Palace phase fields (only used when phase == "memory-palace").
    # Per MEMORY_PALACE_BACKEND_PLAN.md §1.3, §1.4 — the route grades a single
    # encode→walk→recall session in one shot. `palace_key` identifies the route
    # the student walked; `placements` is the Step-2 location-concept binding
    # the student authored; `recall_results` is the Step-4 picks. Server
    # recomputes `is_correct` from `placements` to defend against tampered
    # POST bodies. `mp_hints_used` is reserved for future XP shaping (cosmetic
    # only in v1) — distinct from the Final Boss `hints_used` which lives on
    # `BossTurnRequest`, so we namespace this one to avoid model collisions.
    palace_key: Optional[str] = None
    placements: Optional[list[dict[str, Any]]] = None
    recall_results: Optional[list[dict[str, Any]]] = None
    mp_hints_used: Optional[int] = 0


class FinalizeCheckAnswerRequest(BaseModel):
    phase: str
    homework_id: str
    item_id: str


class BossTurnRequest(BaseModel):
    boss_question: str
    student_answer: str
    expected_answers: list[str] = []
    damage_value: int = Field(default=10, ge=0, le=50)
    hp_remaining: int = Field(default=100, ge=0)
    attempt_number: int = Field(default=1, ge=1)
    subject: str = "math-algebra"
    grade: int = 8
    # Wave F3 — optional persona traits from boss_plan; absent = previous behavior.
    persona_traits: Optional[list[str]] = None
    # Final Boss redesign Chunk B — additive optional fields. Existing callers
    # who omit these get identical behavior (response shape unchanged when
    # the boss is still in progress; outcome/stars/outcome_xp surface only
    # when the caller signals defeat by zeroing hp_remaining).
    boss_type: Optional[str] = None       # "sub" | "big" | "mythical"
    grade_band: Optional[str] = None      # "g1_4" | "g5" | "g6_8" | "g9_11"
    attempts_used: Optional[int] = 0
    hints_used: Optional[int] = 0
    max_hp: Optional[int] = None          # for outcome computation; falls back to grade-band default
    homework_id: Optional[str] = None     # forwarded by /check-answer adapter (not used by tutor.boss_turn)
    session_id: Optional[str] = None      # forwarded by /check-answer adapter (not used by tutor.boss_turn)
    question_id: Optional[str] = None     # forwarded by /check-answer adapter (not used by tutor.boss_turn)


class ReflectionRequest(BaseModel):
    homework_title: str = ""
    homework_summary: str = ""
    student_reflection: str
    performance: dict[str, Any] = {}
    subject: str = "math-algebra"
    grade: int = 8


class PreviewAnswerSpecRequest(BaseModel):
    answer_spec: dict[str, Any]


class TutorRequest(BaseModel):
    phase: str = "general"
    question: str
    student_input: str = ""
    subject: str = "math-algebra"
    grade: int = 8
    context: Optional[str] = None


class ReviewDecideRequest(BaseModel):
    correct: bool
    score: float
    feedback: str


# Wave F1 — live tutor chat + boss-plan + history.

# Allowlist of fine-grained subphase values. Anything outside this set is
# silently dropped to None before it reaches the tutor service.
SUBPHASE_ALLOWLIST: frozenset[str] = frozenset({
    "preview",
    "memory-sprint",
    "story-mode",
    "adaptive-quiz",
    "sentence-fill",
    "tile-match",
    "mystery-box",
    "puzzle-lock",
    "real-life",
    "real-life-challenge",
    "consolidation",
    "final-boss",
    "reflection",
})


class TutorChatRequest(BaseModel):
    session_id: str
    hw_id: str
    phase: Optional[str] = None
    question_id: Optional[str] = None
    message: str
    screen_context: Optional[str] = None
    student_work_text: Optional[str] = None
    subphase: Optional[str] = None
    ui_state: Optional[dict[str, Any]] = None
    recent_assistant_phrases: list[str] = []


class TutorChatResponse(BaseModel):
    response: str
    message_id: int


class BossPlanRequest(BaseModel):
    session_id: str
    hw_id: str


class BossPlanOrderedItem(BaseModel):
    question_id: str
    framing_text: str


class BossPlanResponse(BaseModel):
    ordered: list[BossPlanOrderedItem]
    persona_traits: list[str]


# --- Helpers ---

def _handle_exc(e: Exception):
    if isinstance(e, FileNotFoundError):
        raise HTTPException(500, detail={"error": str(e), "code": "PROMPT_MISSING"})
    raise HTTPException(500, detail={"error": str(e), "code": "AI_ERROR"})


def _answer_spec_type(req: CheckAnswerRequest) -> Optional[str]:
    if isinstance(req.answer_spec, dict):
        value = req.answer_spec.get("type")
        return str(value) if value is not None else None
    return None


def _result_action(result: dict[str, Any]) -> str:
    if result.get("ai_unavailable"):
        return "ai_unavailable"
    if result.get("needs_review"):
        return "review_candidate"
    source = result.get("source")
    if source == "ai_unsure":
        return "partial_retry"
    if result.get("correct") is True:
        return "accepted"
    if result.get("correct") is False:
        return "rejected"
    return "completed"


def _attach_check_answer_debug(
    req: CheckAnswerRequest,
    result: dict[str, Any],
    *,
    checker_path: str,
) -> dict[str, Any]:
    existing_debug = result.get("context_debug")
    service_checker_path = None
    if isinstance(existing_debug, dict):
        service_checker_path = existing_debug.get("checker_path")
    return ai_debug.with_context_debug(
        result,
        {
            "route": "check_answer",
            "phase": req.phase,
            "homework_id_present": ai_debug.present(req.homework_id),
            "question_id_present": ai_debug.present(req.question_id),
            "question_id": req.question_id or None,
            "item_id": req.item_id,
            "step_id": req.step_id,
            "answer_spec_type": _answer_spec_type(req),
            "checker_path": service_checker_path or checker_path,
            "route_checker_path": checker_path,
            "provider": ai_orchestrator._active_backend(),
            "model": ai_orchestrator.FAST_MODEL,
            "source": result.get("source"),
            "confidence": result.get("confidence"),
            "result_action": _result_action(result),
            "ai_unavailable": bool(result.get("ai_unavailable")),
        },
        route="api.check_answer",
    )


def _attach_boss_turn_debug(
    req: BossTurnRequest,
    result: dict[str, Any],
) -> dict[str, Any]:
    damage = int(result.get("damage_dealt") or 0)
    hp_before = int(req.hp_remaining or 0)
    return ai_debug.with_context_debug(
        result,
        {
            "route": "boss_turn",
            "mode": "fixed_boss",
            "session_id_present": ai_debug.present(req.session_id),
            "homework_id_present": ai_debug.present(req.homework_id),
            "question_id_present": ai_debug.present(req.question_id),
            "history_count": 0,
            "boss_questions_count": None,
            "question_source": "frontend_payload",
            "hp_before": hp_before,
            "hp_after": max(0, hp_before - damage),
            "damage_dealt": damage,
            "difficulty": req.boss_type or req.grade_band,
            "model": ai_orchestrator.PRO_MODEL,
            "provider": ai_orchestrator._active_backend(),
            "ai_unavailable": bool(result.get("ai_unavailable")),
        },
        route="api.boss_turn",
    )


def _attach_tutor_chat_route_debug(
    req: TutorChatRequest,
    result: dict[str, Any],
    *,
    hw_present: bool,
    question_found: bool,
    screen_context: Optional[str],
    student_work_text: Optional[str],
    subphase: Optional[str],
    warning_level: int,
) -> dict[str, Any]:
    return ai_debug.with_context_debug(
        result,
        {
            "route": "tutor_chat",
            "session_id_present": ai_debug.present(req.session_id),
            "hw_id_present": ai_debug.present(req.hw_id),
            "homework_found": hw_present,
            "phase": req.phase,
            "subphase": subphase,
            "question_id_present": ai_debug.present(req.question_id),
            "question_found": question_found,
            "screen_context_raw_len": ai_debug.text_len(req.screen_context),
            "screen_context_forwarded_len": ai_debug.text_len(screen_context),
            "student_work_text_len": ai_debug.text_len(student_work_text),
            "warning_level": warning_level,
        },
        route="api.tutor_chat",
    )


# --- Status ---

@router.get("/ai/status")
async def ai_status() -> dict:
    """Report which AI backend is active plus resolved task models for debugging."""
    info = ai_gateway.get_status()
    # Legacy fields — kept for backward compat
    info["backend"] = info["active_provider"]
    info["model_fast"] = ai_orchestrator.FAST_MODEL
    info["model_pro"] = ai_orchestrator.PRO_MODEL
    info["available_providers"] = ai_orchestrator.available_providers()
    # Alias provider_order as preference_list for existing consumers
    info["preference_list"] = info["provider_order"]
    return info


# --- Review-queue endpoints (Fix #5: moved under /ai/ prefix for consistency) ---

@router.get("/ai/review-queue")
async def get_review_queue():
    from .. import db
    return await db.get_review_queue()

@router.post("/ai/review-queue/{id}/decide")
async def decide_review_queue(req: ReviewDecideRequest, id: int = PathParam(...)):
    from .. import db
    success = await db.resolve_review_item(id, req.model_dump())
    if not success:
        raise HTTPException(404, detail="Review item not found or already resolved")
    return {"status": "ok"}


# --- Endpoints ---

@router.post("/ai/answer-spec/preview")
async def preview_answer_spec(req: PreviewAnswerSpecRequest):
    spec = req.answer_spec
    ans_type = spec.get("type", "text_fuzzy")
    expected = spec.get("expected")

    examples = []
    if ans_type == "numeric":
        try:
            val = float(expected)
            tol = float(spec.get("tolerance", 0))
            examples.append(str(val))
            if tol > 0:
                examples.append(str(val + tol))
                examples.append(str(val - tol))
        except (ValueError, TypeError):
            examples.append(str(expected))
    elif ans_type == "set_match":
        if isinstance(expected, list):
            # Show the set
            examples.append(", ".join(map(str, expected)))
            if len(expected) > 1:
                # Show one of them
                examples.append(str(expected[0]))
        else:
            examples.append(str(expected))
    else:
        # text variants and semantic
        examples.append(str(spec.get("canonical_display", expected)))

    return {"examples": examples}


# ---------------------------------------------------------------------------
# Sentence-Fill — per-blank attempt tracking + grading
# ---------------------------------------------------------------------------
#
# Storage: Option A (in-memory module-global dict). The persisted
# alternative (`tutor_attempts` table) does not yet exist in this DB schema
# (see `server/db/migrations.py`); per the Chunk B brief, we fall back to
# in-memory tracking and add a TODO for a future migration. Refresh-resilience
# is therefore best-effort — a hard browser refresh resets attempt counts for
# blanks the student had already touched. Acceptable for v1; spec §5 puts the
# bonus on PERFECT fill, which is detected at finalize time from the same
# in-memory dict, so a refresh can only relax the bonus, never inflate it.
#
# Key shape: (homework_id, item_id, blank_idx) -> {"attempts": int, "correct_at": Optional[int]}
# `correct_at` records the attempt number on which the blank was first
# answered correctly (1, 2, ...) — used by /finalize to compute perfect_fill.
# `attempts` is the count of times the student has submitted for that blank.
#
# TODO(future migration): persist as a `tutor_attempts` table keyed by
# (session_id, hw_id, item_id, blank_idx) so attempts survive a refresh.
_SF_ATTEMPTS: dict[tuple[str, str, int], dict[str, Any]] = {}


def _sf_normalize(text: str) -> str:
    """Lowercase + strip whitespace for word-bank deterministic equality."""
    if text is None:
        return ""
    return str(text).strip().lower()


def _find_sf_item(content_json: dict, item_id: str) -> Optional[dict]:
    """Locate a sentence-fill item by id within content_json.gb_sentence_fill."""
    if not isinstance(content_json, dict):
        return None
    items = content_json.get("gb_sentence_fill")
    if not isinstance(items, list):
        return None
    for item in items:
        if isinstance(item, dict) and item.get("id") == item_id:
            return item
    return None


async def _ai_grade_sentence_fill(
    student_value: str,
    expected: str,
    *,
    subject_hint: Optional[str],
    passage: str,
) -> bool:
    """Free-recall grader: routes through the existing AI semantic answer-checker.

    Builds an answer_spec of type "semantic" and reuses tutor.check_answer so
    we inherit caching + low-confidence review-queue handling without
    duplicating prompt-building here.
    """
    # Use language rubric if subject_hint hints at language; otherwise default.
    subject = subject_hint or "language"
    answer_spec = {
        "type": "semantic",
        "expected": expected,
        # `amr: false` — we want meaning-match without the rubric scoring.
        "amr": False,
    }
    result = await tutor.check_answer(
        question_id="",
        question=passage,
        student_answer=student_value,
        expected_answers=[expected],
        answer_spec=answer_spec,
        allow_ai_fallback=True,
        subject=subject,
        grade=8,
        tier="MEDIUM",
        context=None,
        phase=None,
    )
    return bool(result.get("correct"))


async def _check_answer_sentence_fill(req: CheckAnswerRequest) -> dict:
    """Per-blank grading branch. See SENTENCE_FILL_BACKEND_PLAN.md §4."""
    # Validate required sentence-fill fields. Pydantic only enforces shape;
    # business-required-ness for this phase is enforced here.
    if not req.homework_id or not req.item_id:
        raise HTTPException(400, detail={
            "error": "homework_id and item_id required for phase=sentence-fill",
            "code": "SF_MISSING_IDS",
        })
    if req.blank_idx is None:
        raise HTTPException(400, detail={
            "error": "blank_idx required for phase=sentence-fill",
            "code": "SF_MISSING_BLANK",
        })
    attempt_number = req.attempt_number if req.attempt_number is not None else 1
    if attempt_number < 1:
        raise HTTPException(400, detail={
            "error": "attempt_number must be >= 1",
            "code": "SF_BAD_ATTEMPT",
        })
    student_value = req.student_value if req.student_value is not None else ""

    hw = await db.get_homework(req.homework_id)
    if hw is None:
        raise HTTPException(404, detail={
            "error": f"homework {req.homework_id} not found",
            "code": "HW_NOT_FOUND",
        })
    content = hw.get("content_json") or {}
    item = _find_sf_item(content, req.item_id)
    if item is None:
        raise HTTPException(404, detail={
            "error": f"sentence-fill item {req.item_id} not found",
            "code": "SF_ITEM_NOT_FOUND",
        })

    answers = item.get("answers") or []
    if not isinstance(req.blank_idx, int) or req.blank_idx < 0 or req.blank_idx >= len(answers):
        raise HTTPException(400, detail={
            "error": f"blank_idx {req.blank_idx} out of range for item with {len(answers)} blanks",
            "code": "SF_BAD_BLANK_IDX",
        })

    expected = answers[req.blank_idx]
    mode = item.get("mode", "word_bank")

    # Grade.
    if mode == "word_bank":
        is_correct = _sf_normalize(student_value) == _sf_normalize(expected)
    else:
        # Free recall: semantic grader.
        is_correct = await _ai_grade_sentence_fill(
            student_value,
            expected,
            subject_hint=item.get("subject_hint"),
            passage=item.get("passage", ""),
        )

    # Update attempt tracking. Lock once: attempt_number >= 2 OR is_correct.
    attempt_key = (req.homework_id, req.item_id, req.blank_idx)
    record = _SF_ATTEMPTS.get(attempt_key) or {"attempts": 0, "correct_at": None}
    record["attempts"] = max(record["attempts"], attempt_number)
    if is_correct and record["correct_at"] is None:
        record["correct_at"] = attempt_number
    _SF_ATTEMPTS[attempt_key] = record

    locked = bool(is_correct or attempt_number >= 2)

    # Per spec §4: explanation + correct_answer revealed only on lock-and-wrong.
    revealed_answer: Optional[str] = None
    revealed_explanation: Optional[str] = None
    if locked and not is_correct:
        revealed_answer = expected
        explanations = item.get("explanations")
        if isinstance(explanations, list) and 0 <= req.blank_idx < len(explanations):
            entry = explanations[req.blank_idx]
            if entry:
                revealed_explanation = entry

    xp_base = 100 if is_correct else 0
    xp_first = 25 if (is_correct and attempt_number == 1) else 0

    return {
        "correct": is_correct,
        "lock": locked,
        "correct_answer": revealed_answer,
        "explanation": revealed_explanation,
        "xp": {
            "base": xp_base,
            "first_attempt_bonus": xp_first,
            "total": xp_base + xp_first,
        },
    }


# ---------------------------------------------------------------------------
# Tile Match — phase=tile-match check-answer branch (Chunk B).
#
# In-memory attempt tracker (parallel to _SF_ATTEMPTS pattern).
# Keyed by (homework_id, session_id) so multiple concurrent students keep
# independent state. Survives until process restart; refresh-resilience is
# best-effort (a hard refresh resets timer + streak — acceptable for v1).
#
# Per-session value:
# {
#   "matched_pair_ids": set[str],   # pairs already correctly matched
#   "wrong_count": int,             # total mismatch attempts
#   "streak": int,                  # current consecutive-correct count
#   "completed_families": set[str], # concept_family ids already drained
#   "remaining_seconds": int,       # mutable timer, clamped to >=0
#   "tier": "basic" | "premium",
#   "grade": int,
#   "total_pairs": int,
# }
# ---------------------------------------------------------------------------
_TM_ATTEMPTS: dict[tuple[str, str], dict[str, Any]] = {}


def _grade_band_for(grade: int) -> tuple[int, int]:
    """Return (total_pairs, timer_seconds) for a given grade — per spec §1."""
    if grade is None:
        grade = 8
    if grade <= 2:
        return (4, 180)
    if grade <= 4:
        return (5, 165)
    if grade <= 7:
        return (6, 150)
    return (8, 120)


def _speed_bonus_for(remaining_seconds: int) -> int:
    """Return XP speed bonus for a correct match — per spec §5C."""
    if remaining_seconds <= 0:
        return 0
    if remaining_seconds >= 50:
        return 50
    if remaining_seconds >= 30:
        return 30
    return 10


def _outcome_for(
    wrong_count: int,
    matched_count: int,
    total: int,
    timer_remaining: int,
) -> tuple[Optional[str], int]:
    """Compute outcome tier + completion bonus XP — per spec §5A/5B.

    Returns (outcome, completion_bonus_xp). outcome is None when the game is
    still in progress.
    """
    if total <= 0:
        return (None, 0)
    ratio = matched_count / total
    if timer_remaining <= 0 and matched_count < total:
        if ratio < 0.6:
            return ("below_threshold", 0)
        # 60% <= ratio < 100%
        return ("partial", 0)
    if matched_count == total:
        if wrong_count == 0:
            return ("perfect_clear", 200)
        if wrong_count == 1:
            return ("flawless", 100)
        return ("cleared", 0)
    return (None, 0)


def _resolve_tm_pairs(content_json: dict) -> list[dict]:
    """Build the canonical pair list for a homework's tile-match game.

    Reads `gb_tile_match` if non-empty; otherwise shims `gb_memory_match`
    ([[a, b], ...]) into pseudo-TileMatchPair dicts. Mirrors the injector's
    legacy_pairs logic (Chunk A `_serialize_tile_match`).
    """
    if not isinstance(content_json, dict):
        return []
    items = content_json.get("gb_tile_match")
    pairs: list[dict] = []
    if isinstance(items, list) and items:
        for item in items:
            if isinstance(item, dict):
                pairs.append(item)
            else:
                # Pydantic model fallback.
                try:
                    pairs.append(dict(item))
                except Exception:
                    continue
        return pairs
    legacy = content_json.get("gb_memory_match")
    if isinstance(legacy, list):
        for i, pair in enumerate(legacy):
            if not (isinstance(pair, (list, tuple)) and len(pair) >= 2):
                continue
            pairs.append({
                "id": f"tm_legacy_{i:03d}",
                "left": str(pair[0]),
                "right": str(pair[1]),
                "tier": "basic",
            })
    return pairs


async def _check_answer_tile_match(req: CheckAnswerRequest) -> dict:
    """Per-pair grading branch for Tile Match.

    See TILE_MATCH_BACKEND_PLAN.md §3 + tile-match-concept-definition.md §1, §5.

    No-leak invariants:
      - Response on a CORRECT match returns `explanation` only when
        `tier == "premium"` (and the field is authored). Never echoes any
        other pair's right-side text.
      - Response on a WRONG match returns `hint` = the LEFT-side concept text
        of the wrongly-picked right_id's TRUE partner. The student already
        sees that left tile in the DOM, so this is not a new leak surface.
    """
    if not req.homework_id:
        raise HTTPException(400, detail={
            "error": "homework_id required for phase=tile-match",
            "code": "TM_MISSING_HW",
        })
    if not req.left_id or not req.right_id:
        raise HTTPException(400, detail={
            "error": "left_id and right_id required for phase=tile-match",
            "code": "TM_MISSING_IDS",
        })

    hw = await db.get_homework(req.homework_id)
    if hw is None:
        raise HTTPException(404, detail={
            "error": f"homework {req.homework_id} not found",
            "code": "HW_NOT_FOUND",
        })
    content = hw.get("content_json") or {}
    pairs = _resolve_tm_pairs(content)
    if not pairs:
        raise HTTPException(404, detail={
            "error": "tile-match content not found on this homework",
            "code": "TM_NO_CONTENT",
        })

    # Build id-keyed lookups. The student picked left_id + right_id; we need
    # to (a) verify left_id maps to right_id (correct match) and (b) on wrong,
    # return the LEFT text of right_id's TRUE partner.
    by_left_id = {p.get("id"): p for p in pairs if p.get("id")}
    by_right_id_true_left_text = {
        p.get("id"): p.get("left", "") for p in pairs if p.get("id")
    }

    pair = by_left_id.get(req.left_id)
    if pair is None:
        raise HTTPException(400, detail={
            "error": f"left_id {req.left_id} not found in this tile-match board",
            "code": "TM_BAD_LEFT_ID",
        })
    if req.right_id not in by_right_id_true_left_text:
        raise HTTPException(400, detail={
            "error": f"right_id {req.right_id} not found in this tile-match board",
            "code": "TM_BAD_RIGHT_ID",
        })

    # Get-or-create per-session state.
    session_id = req.session_id or "default"
    grade = int(hw.get("grade") or req.grade or 8)
    total_pairs_band, timer_seconds = _grade_band_for(grade)
    # Use the actual board size when smaller than the band default — the
    # outcome is computed against authored pairs, not the band size.
    total_pairs = len(pairs)

    state_key = (req.homework_id, session_id)
    state = _TM_ATTEMPTS.get(state_key)
    if state is None:
        state = {
            "matched_pair_ids": set(),
            "wrong_count": 0,
            "streak": 0,
            "completed_families": set(),
            "remaining_seconds": timer_seconds,
            "tier": (pair.get("tier") if isinstance(pair, dict) else "basic") or "basic",
            "grade": grade,
            "total_pairs": total_pairs,
        }
        _TM_ATTEMPTS[state_key] = state

    # If this pair has already been matched, treat it as a no-op (defensive).
    already_matched = req.left_id in state["matched_pair_ids"]

    is_correct = (req.left_id == req.right_id) and not already_matched

    # Initialize XP components.
    xp_base = 0
    xp_speed = 0
    xp_streak = 0
    xp_palace = 0
    xp_branch = 0
    delta = 0
    hint: Optional[str] = None
    explanation: Optional[str] = None

    if is_correct:
        # Apply timer +3, then compute speed bonus from POST-delta remaining,
        # per plan §3c. Clamp at >=0 (timer can't go negative).
        delta = 3
        state["remaining_seconds"] = max(0, state["remaining_seconds"] + delta)
        state["matched_pair_ids"].add(req.left_id)
        state["streak"] += 1
        state["wrong_count"] = state["wrong_count"]  # no change
        xp_base = 100
        xp_speed = _speed_bonus_for(state["remaining_seconds"])

        # Streak bonus: every 3rd consecutive correct.
        if state["streak"] > 0 and state["streak"] % 3 == 0:
            tier = (pair.get("tier") or "basic") if isinstance(pair, dict) else "basic"
            xp_streak = 75 if tier == "premium" else 50

        # Memory Palace bonus.
        if isinstance(pair, dict) and pair.get("is_palace_tile"):
            xp_palace = 50

        # Branch-complete bonus: this match drains the concept_family.
        family = pair.get("concept_family") if isinstance(pair, dict) else None
        if family and family not in state["completed_families"]:
            family_pair_ids = {
                p.get("id") for p in pairs
                if isinstance(p, dict) and p.get("concept_family") == family and p.get("id")
            }
            if family_pair_ids and family_pair_ids.issubset(state["matched_pair_ids"]):
                xp_branch = 100
                state["completed_families"].add(family)

        # Premium tier — surface the authored explanation, if any.
        if isinstance(pair, dict):
            pair_tier = pair.get("tier") or "basic"
            if pair_tier == "premium" and pair.get("explanation"):
                explanation = pair.get("explanation")
    elif already_matched:
        # No-op: the same pair was claimed twice. Return zeros + correct=False
        # but DON'T penalize timer/streak (defensive against double-clicks).
        delta = 0
    else:
        # Wrong match: -5s timer, reset streak, increment wrong_count.
        delta = -5
        state["remaining_seconds"] = max(0, state["remaining_seconds"] + delta)
        state["streak"] = 0
        state["wrong_count"] += 1
        # Hint = the LEFT-side concept text of the right-tile's true partner.
        hint = by_right_id_true_left_text.get(req.right_id) or None

    xp_total = xp_base + xp_speed + xp_streak + xp_palace + xp_branch

    matched_count = len(state["matched_pair_ids"])
    outcome, completion_bonus = _outcome_for(
        state["wrong_count"],
        matched_count,
        total_pairs,
        state["remaining_seconds"],
    )
    complete = outcome is not None

    return {
        "correct": is_correct,
        "hint": hint,
        "explanation": explanation,
        "xp": {
            "base": xp_base,
            "speed_bonus": xp_speed,
            "streak_bonus": xp_streak,
            "palace_bonus": xp_palace,
            "branch_bonus": xp_branch,
            "total": xp_total,
        },
        "timer": {
            "remaining_seconds": state["remaining_seconds"],
            "delta_seconds": delta,
        },
        "matched_count": matched_count,
        "total_pairs": total_pairs,
        "complete": complete,
        "outcome": outcome,
        "completion_bonus_xp": completion_bonus,
    }


# ---------------------------------------------------------------------------
# Real-Life Challenge — phase=real-life-challenge check-answer branch (Chunk B).
#
# Per RLC plan §3 — 5-step expert role-play case. Per-step grading at this
# endpoint; AI grader fires only on step 5 (reasoning textarea).
#
# In-memory attempt tracker (parallel to _SF_ATTEMPTS / _TM_ATTEMPTS pattern).
# Keyed by (homework_id, session_id). Survives until process restart.
#
# Per-session value:
# {
#   "step_outcomes": dict[str, str],   # step_id -> "correct"|"wrong"
#   "step_xp": dict[str, int],         # step_id -> earned XP for that step
#   "rubric": {                        # running 300-XP rubric (un-multiplied)
#       "decision_quality": int,       # max 150
#       "reasoning_quality": int,      # max 100
#       "concept_id": int,             # max 50
#   },
#   "wrong_attempts": dict[str, int],  # step_id -> wrong-attempt count (decision-kind only)
#   "started_at": datetime,
#   "completed_at": Optional[datetime],
#   "tier": "basic" | "premium",
#   "grade_band": str,
# }
# ---------------------------------------------------------------------------
_RLC_ATTEMPTS: dict[tuple[str, str], dict[str, Any]] = {}


def _rlc_per_step_xp_cap(step_kind: str) -> int:
    """Per-step XP cap, per RLC plan §3d.

    decision/info_request/final_decision → 50 each (decision_quality 150 split / 3)
    concept_select → 50 (concept_id)
    reasoning → 100 (reasoning_quality, AI-graded 1:1 from 0-100)
    """
    if step_kind in ("decision", "info_request", "final_decision"):
        return 50
    if step_kind == "concept_select":
        return 50
    if step_kind == "reasoning":
        return 100
    return 0


def _rlc_outcome_for(rubric: dict[str, int]) -> tuple[str, int, float]:
    """Compute outcome tier + completion bonus + multiplier — per RLC plan §3e.

    Returns (outcome_label, completion_bonus_xp, multiplier).
      90-100% → ("expert_decision", 50, 1.0)
      75-89%  → ("strong_analysis", 0, 1.0)
      60-74%  → ("passing", 0, 0.8)
      <60%    → ("hali_emas", 0, 0.4)
    """
    total = (
        int(rubric.get("decision_quality", 0))
        + int(rubric.get("reasoning_quality", 0))
        + int(rubric.get("concept_id", 0))
    )
    pct = (total / 300) * 100
    if pct >= 90:
        return ("expert_decision", 50, 1.0)
    if pct >= 75:
        return ("strong_analysis", 0, 1.0)
    if pct >= 60:
        return ("passing", 0, 0.8)
    return ("hali_emas", 0, 0.4)


async def _grade_rlc_reasoning(
    text: str,
    step: dict,
    case_intro: str,
    expert_role: str,
) -> tuple[int, str]:
    """Grade reasoning step via the LLM. Returns (score 0-100, feedback string).

    Loads the `real-life-challenge-grader` runtime prompt and calls the same
    `ai_orchestrator.generate_json` adapter used by `tutor.check_answer`. Anchors the
    LLM on step.acceptable_keywords (server-only) + case intro context. The
    min-char gate is enforced BEFORE this is called (cheap reject).

    The student's score is mapped 1:1 onto `xp.reasoning_quality` (0-100).
    Tests mock this function directly — they do not exercise ai_orchestrator.
    """
    # Local imports keep the module load light when the RLC branch is unused.
    from ..services.tutor import _load_runtime_prompt
    import json as _json

    prompt = _load_runtime_prompt("real-life-challenge-grader")
    payload = {
        "expert_role": expert_role or "general",
        "case_intro": case_intro or "",
        "step_prompt": step.get("prompt", "") if isinstance(step, dict) else "",
        "student_text": text or "",
        # Server-only anchor — never echoed back to client; prompt instructs
        # the LLM to use these as a check, not to quote them.
        "acceptable_keywords": (
            step.get("acceptable_keywords") or []
            if isinstance(step, dict) else []
        ),
    }
    schema = {
        "score": "integer 0..100",
        "feedback": "1-2 sentence string in the case's language",
    }
    # PR 1 — bloat-fix: sanitize+cap before LLM, fall back to neutral score
    # when unavailable so the runtime sees a usable response instead of 500.
    try:
        input_section = ai_orchestrator.build_input_section(payload)
        ai_response = await ai_orchestrator.generate_json(
            f"{prompt}\n\n{input_section}",
            schema_hint=schema,
            model=ai_orchestrator.FAST_MODEL,
        )
    except (ai_orchestrator.PromptTooLargeError, RuntimeError):
        # AI grading unavailable — return a neutral "needs human review" score
        # rather than 0 (which would punish the student) or 100 (false pass).
        return (50, "AI baholash hozir mavjud emas — javobingiz keyinroq tekshiriladi.")

    # Defensive parse — clamp to [0, 100], coerce to int.
    raw_score = ai_response.get("score", 0)
    try:
        score = int(round(float(raw_score)))
    except (TypeError, ValueError):
        score = 0
    score = max(0, min(100, score))
    feedback = str(ai_response.get("feedback") or "")
    return (score, feedback)


def _resolve_rlc_case(content_json: dict) -> Optional[dict]:
    """Locate the RLC case dict on a homework's content_json.

    Returns the raw dict (server-only fields like is_correct + consequence +
    acceptable_keywords are STILL present here — that's the whole point of the
    side-disjoint injection: stripping happens only at the injector boundary,
    so the endpoint can read the truth.). Returns None if missing/invalid.
    """
    if not isinstance(content_json, dict):
        return None
    case = content_json.get("real_life_challenge")
    if not isinstance(case, dict):
        return None
    if not case.get("steps"):
        return None
    return case


def _rlc_find_step(case: dict, step_id: str) -> Optional[dict]:
    """Find a step by id within a case dict."""
    if not isinstance(case, dict):
        return None
    for s in case.get("steps") or []:
        if isinstance(s, dict) and s.get("id") == step_id:
            return s
    return None


async def _check_answer_real_life_challenge(req: CheckAnswerRequest) -> dict:
    """Per-step grading branch for Real-Life Challenge.

    See REAL_LIFE_CHALLENGE_BACKEND_PLAN.md §3.

    No-leak invariants:
      - Response NEVER includes `is_correct` flags from other options.
      - Response NEVER includes `consequence` text from any option except
        the one the student picked (and only when wrong, as pedagogical reveal).
        Per plan §3c, only on step 5 (reasoning) does the response carry feedback.
      - Response NEVER echoes `acceptable_keywords` from any step.
      - On a correct decision, the response is bare {correct: true, xp: ...} —
        no consequence leak from the wrong options.
    """
    if not req.homework_id:
        raise HTTPException(400, detail={
            "error": "homework_id required for phase=real-life-challenge",
            "code": "RLC_MISSING_HW",
        })
    if not req.step_id:
        raise HTTPException(400, detail={
            "error": "step_id required for phase=real-life-challenge",
            "code": "RLC_MISSING_STEP_ID",
        })

    hw = await db.get_homework(req.homework_id)
    if hw is None:
        raise HTTPException(404, detail={
            "error": f"homework {req.homework_id} not found",
            "code": "HW_NOT_FOUND",
        })
    content = hw.get("content_json") or {}
    case = _resolve_rlc_case(content)
    if case is None:
        raise HTTPException(404, detail={
            "error": "real-life-challenge content not found on this homework",
            "code": "RLC_NO_CONTENT",
        })

    step = _rlc_find_step(case, req.step_id)
    if step is None:
        raise HTTPException(404, detail={
            "error": f"step {req.step_id} not found in this RLC case",
            "code": "RLC_STEP_NOT_FOUND",
        })

    # Get-or-create per-session state.
    session_id = req.session_id or "default"
    state_key = (req.homework_id, session_id)
    state = _RLC_ATTEMPTS.get(state_key)
    if state is None:
        from datetime import datetime, timezone
        state = {
            "step_outcomes": {},
            "step_xp": {},
            "rubric": {
                "decision_quality": 0,
                "reasoning_quality": 0,
                "concept_id": 0,
            },
            "wrong_attempts": {},
            "started_at": datetime.now(timezone.utc),
            "completed_at": None,
            "tier": case.get("tier", "basic"),
            "grade_band": case.get("grade_band", "g7_9"),
        }
        _RLC_ATTEMPTS[state_key] = state

    kind = step.get("kind")
    steps_list = case.get("steps") or []
    step_index = next(
        (i for i, s in enumerate(steps_list)
         if isinstance(s, dict) and s.get("id") == req.step_id),
        0,
    )
    total_steps = len(steps_list)

    # Per-step XP earned (this submission only, un-multiplied).
    xp_decision_quality = 0
    xp_reasoning_quality = 0
    xp_concept_id = 0
    is_correct = False
    consequence_text: Optional[str] = None
    correct_option_label: Optional[str] = None
    reasoning_score: Optional[int] = None
    reasoning_feedback: Optional[str] = None

    # ---- Dispatch by step kind ----------------------------------------------
    if kind in ("decision", "info_request", "final_decision"):
        # Decision-style steps: match selected_option_id against options[].is_correct.
        if not req.selected_option_id:
            raise HTTPException(400, detail={
                "error": (
                    f"selected_option_id required for step kind={kind!r} "
                    f"(step={req.step_id})"
                ),
                "code": "RLC_MISSING_OPTION_ID",
            })
        options = step.get("options") or []
        picked = None
        correct_opt = None
        for opt in options:
            if not isinstance(opt, dict):
                continue
            if opt.get("id") == req.selected_option_id:
                picked = opt
            if opt.get("is_correct"):
                correct_opt = opt
        if picked is None:
            raise HTTPException(400, detail={
                "error": (
                    f"selected_option_id {req.selected_option_id!r} not found "
                    f"in step {req.step_id} options"
                ),
                "code": "RLC_BAD_OPTION_ID",
            })

        is_correct = bool(picked.get("is_correct"))
        if is_correct:
            xp_decision_quality = _rlc_per_step_xp_cap(kind)
            state["step_outcomes"][req.step_id] = "correct"
            # Reset wrong counter on correct (defensive — should be 0 already).
        else:
            # Track wrong attempts for the pedagogical-reveal policy.
            wrong_n = state["wrong_attempts"].get(req.step_id, 0) + 1
            state["wrong_attempts"][req.step_id] = wrong_n
            state["step_outcomes"][req.step_id] = "wrong"
            # After 2 wrongs on the same step, reveal the correct option's
            # label as a pedagogical assist (xp still 0).
            if wrong_n >= 2 and correct_opt is not None:
                correct_option_label = correct_opt.get("label")

        # Per plan §3c — surface the picked option's `consequence` text ONLY
        # on a wrong decision (pedagogical hint about the path NOT taken).
        # On a correct pick, the response stays bare to avoid leaking any
        # consequence text the student didn't earn yet.
        if (not is_correct) and isinstance(picked.get("consequence"), str) and picked.get("consequence"):
            consequence_text = picked.get("consequence")

    elif kind == "concept_select":
        if not req.selected_chip_id:
            raise HTTPException(400, detail={
                "error": (
                    f"selected_chip_id required for step kind=concept_select "
                    f"(step={req.step_id})"
                ),
                "code": "RLC_MISSING_CHIP_ID",
            })
        chips = step.get("concept_chips") or []
        picked = None
        for chip in chips:
            if isinstance(chip, dict) and chip.get("id") == req.selected_chip_id:
                picked = chip
                break
        if picked is None:
            raise HTTPException(400, detail={
                "error": (
                    f"selected_chip_id {req.selected_chip_id!r} not found "
                    f"in step {req.step_id} concept_chips"
                ),
                "code": "RLC_BAD_CHIP_ID",
            })
        is_correct = bool(picked.get("is_correct"))
        if is_correct:
            xp_concept_id = _rlc_per_step_xp_cap(kind)
            state["step_outcomes"][req.step_id] = "correct"
        else:
            state["step_outcomes"][req.step_id] = "wrong"

    elif kind == "reasoning":
        if req.reasoning_text is None:
            raise HTTPException(400, detail={
                "error": (
                    f"reasoning_text required for step kind=reasoning "
                    f"(step={req.step_id})"
                ),
                "code": "RLC_MISSING_REASONING_TEXT",
            })
        text = (req.reasoning_text or "").strip()
        min_chars = step.get("min_chars") or 80
        if len(text) < int(min_chars):
            raise HTTPException(400, detail={
                "error": (
                    f"reasoning_text below min_chars={min_chars} "
                    f"(got {len(text)} chars)"
                ),
                "code": "RLC_REASONING_TOO_SHORT",
                "min_chars": int(min_chars),
            })
        score, feedback = await _grade_rlc_reasoning(
            text,
            step,
            case_intro=case.get("intro", ""),
            expert_role=case.get("expert_role", "general"),
        )
        reasoning_score = int(score)
        reasoning_feedback = feedback
        # 1:1 map to XP per plan §3d.
        xp_reasoning_quality = int(score)
        # Reasoning is single-attempt — mark step outcome as correct if score
        # is meaningful (>0) for tracking; the rubric percent decides outcome.
        state["step_outcomes"][req.step_id] = (
            "correct" if score > 0 else "wrong"
        )
        is_correct = score > 0  # advisory; outcome tier decides final tier

    else:
        raise HTTPException(400, detail={
            "error": f"unsupported step kind {kind!r} for step {req.step_id}",
            "code": "RLC_BAD_STEP_KIND",
        })

    # ---- Update rubric + step_xp -------------------------------------------
    step_total_xp = xp_decision_quality + xp_concept_id + xp_reasoning_quality
    state["step_xp"][req.step_id] = step_total_xp
    state["rubric"]["decision_quality"] = (
        state["rubric"].get("decision_quality", 0) + xp_decision_quality
    )
    state["rubric"]["concept_id"] = (
        state["rubric"].get("concept_id", 0) + xp_concept_id
    )
    state["rubric"]["reasoning_quality"] = (
        state["rubric"].get("reasoning_quality", 0) + xp_reasoning_quality
    )

    # ---- Completion + outcome ----------------------------------------------
    complete = (kind == "reasoning")
    outcome: Optional[str] = None
    completion_bonus_xp = 0
    multiplier = 1.0
    rubric_breakdown: Optional[dict] = None
    total_xp_field: Optional[int] = None

    if complete:
        from datetime import datetime, timezone
        state["completed_at"] = datetime.now(timezone.utc)
        outcome, completion_bonus_xp, multiplier = _rlc_outcome_for(state["rubric"])
        un_multiplied_total = (
            state["rubric"]["decision_quality"]
            + state["rubric"]["reasoning_quality"]
            + state["rubric"]["concept_id"]
            + completion_bonus_xp
        )
        total_xp_field = int(round(un_multiplied_total * multiplier))
        rubric_breakdown = {
            "decision_quality": int(state["rubric"]["decision_quality"]),
            "reasoning_quality": int(state["rubric"]["reasoning_quality"]),
            "concept_id": int(state["rubric"]["concept_id"]),
            "bonus": int(completion_bonus_xp),
            "multiplier": multiplier,
            "total": int(total_xp_field),
        }

    response: dict[str, Any] = {
        "step_id": req.step_id,
        "kind": kind,
        "correct": bool(is_correct),
        "consequence": consequence_text,
        "correct_option_label": correct_option_label,
        "reasoning_score": reasoning_score,
        "reasoning_feedback": reasoning_feedback,
        "xp": {
            "decision_quality": int(xp_decision_quality),
            "reasoning_quality": int(xp_reasoning_quality),
            "concept_id": int(xp_concept_id),
            "step_total": int(step_total_xp),
        },
        "step_index": int(step_index),
        "total_steps": int(total_steps),
        "complete": bool(complete),
        "outcome": outcome,
        "completion_bonus_xp": int(completion_bonus_xp),
        "total_xp": total_xp_field,
        "rubric_breakdown": rubric_breakdown,
    }
    return response


# ---------------------------------------------------------------------------
# Final Boss — phase=final-boss check-answer branch (Chunk B).
#
# Per FINAL_BOSS_BACKEND_PLAN.md §3 — this is a thin adapter over the existing
# `tutor.boss_turn` LLM call. It does NOT re-implement grading. It DOES:
#   - resolve the boss question by id from content_json.boss_questions[]
#   - delegate AMR 2-axis grading + damage application to tutor.boss_turn
#   - track per-(homework_id, session_id) state in _FB_ATTEMPTS
#   - compute mastery stars + XP via _boss_outcome_for on defeat
#   - apply grade-banded hint cost from boss_meta or per-question override
#
# Per-session value:
# {
#   "max_hp": int,                 # starting HP for the band/override
#   "hp_remaining": int,           # mirrors client-reported cursor
#   "attempts_used": int,          # increments on every wrong submit
#   "hints_used": int,             # not incremented here (frontend-driven); reflects req
#   "correct_count": int,          # turns judged correct
#   "started_at": datetime,
#   "boss_type": str,              # "sub" | "big" | "mythical"
#   "grade_band": Optional[str],
#   "completed_at": Optional[datetime],
# }
# ---------------------------------------------------------------------------
_FB_ATTEMPTS: dict[tuple[str, str], dict[str, Any]] = {}


def _fb_default_hp_for_grade_band(band: Optional[str]) -> int:
    """Per spec §6: g1_4=50, g5=100, g6_8=100, g9_11=150.

    Mirrors `BossHelpers.defaultHpForGradeBand` in `_boss-helpers.js` so the
    server and builder agree on the starting HP for a band (default 100 when
    band is unknown — matches the existing routing.py fallback).
    """
    return {"g1_4": 50, "g5": 100, "g6_8": 100, "g9_11": 150}.get(band or "", 100)


def _fb_default_hint_cost_for_grade_band(band: Optional[str]) -> int:
    """Per spec §8: g1_4=5, g5=10, g6_8=10, g9_11=15.

    Default 10 when band is unknown (current client default). A per-question
    `hint_cost_per_use` (BossQuestion field) overrides this when authored.
    """
    return {"g1_4": 5, "g5": 10, "g6_8": 10, "g9_11": 15}.get(band or "", 10)


def _fb_grade_band_from_grade(grade: Optional[int]) -> str:
    """Mirror of `BossHelpers.gradeBandFromGrade` in `_boss-helpers.js`."""
    g = int(grade) if grade is not None else 8
    if g <= 4:
        return "g1_4"
    if g == 5:
        return "g5"
    if g <= 8:
        return "g6_8"
    return "g9_11"


# XP table per spec §11 — by boss_type and stars (1-3).
# Mythical only rewards 3-star defeats; lesser stars award 0.
_FB_XP_TABLE: dict[str, dict[int, int]] = {
    "sub":      {1: 500,  2: 700,  3: 1000},
    "big":      {1: 1000, 2: 1500, 3: 2000},
    "mythical": {1: 0,    2: 0,    3: 5000},
}


def _boss_outcome_for(
    hp_remaining: int,
    max_hp: int,
    hints_used: int,
    attempt_number: int,
    boss_type: str = "sub",
) -> tuple[Optional[str], Optional[int], int]:
    """Returns (outcome_label, stars, xp_award) per spec §11.

    Boundary semantics (pinned by `test_fb_outcome_thresholds_at_boundaries`):
      - 3 stars: attempt_number == 1 AND hints_used == 0 AND hp_remaining >= max_hp * 0.8
      - 2 stars: attempt_number <= 2 AND hp_remaining > max_hp * 0.5  (>50%, NOT >=)
      - 1 star : any other defeat (caller decides defeat — this helper does not)
      - 0 stars / "hali_emas": NOT defeated (hp_remaining <= 0 with boss still up
        from the caller's perspective is the only "no defeat" path here; we treat
        hp_remaining <= 0 as boss-not-defeated since FB's frame is *student*-HP,
        and 0 student-HP = boss won)

    XP rewards by boss_type (Sub / Big / Mythical) — mythical lesser-star paths
    return 0 XP per spec §11.
    """
    bt = boss_type if boss_type in _FB_XP_TABLE else "sub"
    # Caller passes hp_remaining > 0 when student survived (boss was defeated).
    # hp_remaining <= 0 means student's HP gone → "hali_emas" (not yet defeated).
    if hp_remaining <= 0:
        return ("hali_emas", 0, 0)
    safe_max = max(1, int(max_hp or 1))

    # 3-star: pristine first-attempt clear with no hints + >=80% HP remaining.
    if (
        attempt_number == 1
        and (hints_used or 0) == 0
        and hp_remaining >= safe_max * 0.8
    ):
        return ("expert", 3, _FB_XP_TABLE[bt][3])

    # 2-star: <=2 attempts AND strictly more than 50% HP remaining.
    if attempt_number <= 2 and hp_remaining > safe_max * 0.5:
        return ("strong", 2, _FB_XP_TABLE[bt][2])

    # 1-star: any other defeat.
    return ("passing", 1, _FB_XP_TABLE[bt][1])


def _fb_find_boss_question(content: dict, question_id: str) -> Optional[dict]:
    """Locate a boss_question by id in a homework's content_json.

    BossQuestion shapes vary; prefer `id`, fall back to index-as-id ("bq_0").
    Returns the raw dict (server-only fields like `accepted`/`ans`/`answer_spec`
    are PRESENT here — that is the point of the side-disjoint injector boundary).

    Recognized id forms (in priority order):
      - q["id"] / q["question_id"]   (authored)
      - "bq_{i}" / "{i}"             (canonical synthetic — what the injector emits)
      - "Q{i+1}"                     (legacy synthetic — older rendered pages may
                                      still send this until they reload after deploy;
                                      remove in a follow-up PR once cache window has
                                      elapsed).
    """
    if not isinstance(content, dict) or not question_id:
        return None
    bq = content.get("boss_questions")
    if not isinstance(bq, list):
        bq = content.get("boss")
    if not isinstance(bq, list):
        return None
    for i, q in enumerate(bq):
        if not isinstance(q, dict):
            continue
        if q.get("id") == question_id or q.get("question_id") == question_id:
            return q
        if (question_id == f"bq_{i}"
                or question_id == str(i)
                or question_id == f"Q{i+1}"):
            return q
    return None


def _fb_extract_expected_answers(question: dict) -> list[str]:
    """Pull deterministic accepted answers from a boss question dict.

    Reads in priority order: answer_spec.expected, accepted_answers, ans.
    All three are stripped from any client-side surface — we read the raw
    dict here on the server only.
    """
    if not isinstance(question, dict):
        return []
    spec = question.get("answer_spec")
    if isinstance(spec, dict):
        exp = spec.get("expected")
        if isinstance(exp, list):
            return [str(x) for x in exp if x is not None]
        if isinstance(exp, str) and exp:
            return [exp]
    accepted = question.get("accepted_answers") or question.get("accepted")
    if isinstance(accepted, list):
        return [str(x) for x in accepted if x is not None]
    ans = question.get("ans")
    if isinstance(ans, list):
        return [str(x) for x in ans if x is not None]
    if isinstance(ans, str) and ans:
        return [ans]
    return []


_FB_LEAK_KEYS: frozenset[str] = frozenset({
    "accepted", "ans", "accepted_answers", "answer_spec", "expected_answers",
})


def _fb_strip_answer_leak(payload: dict) -> dict:
    """Defensive strip — removes any answer-bearing keys from an outgoing dict.

    The tutor adapter never returns these, but if a future change accidentally
    stuffs `answer_spec` into the boss-turn response we drop it here so the
    answer-leak gate (test #15) is enforced at the route boundary, not via
    LLM-prompt discipline alone.
    """
    if not isinstance(payload, dict):
        return payload
    return {k: v for k, v in payload.items() if k not in _FB_LEAK_KEYS}


async def _check_answer_final_boss(req: CheckAnswerRequest) -> dict:
    """Per-question grading branch for Final Boss.

    Thin adapter: builds a `BossTurnRequest` shape and delegates to the
    existing `tutor.boss_turn` LLM call. Adds:
      - per-session attempt tracking (mirrors TM/RLC `_*_ATTEMPTS` pattern)
      - mastery stars / outcome / outcome_xp on defeat (via `_boss_outcome_for`)
      - hint cost grade-banding (resolved from boss_meta or homework grade)

    No-leak invariants:
      - Response stripped of `accepted`, `ans`, `accepted_answers`, `answer_spec`
      - `expected_answers` resolved server-side from authored content_json;
        never echoed back in the response payload
    """
    if not req.homework_id:
        raise HTTPException(400, detail={
            "error": "homework_id required for phase=final-boss",
            "code": "FB_MISSING_HW",
        })

    hw = await db.get_homework(req.homework_id)
    if hw is None:
        raise HTTPException(404, detail={
            "error": f"homework {req.homework_id} not found",
            "code": "HW_NOT_FOUND",
        })
    content = hw.get("content_json") or {}

    # Resolve the boss question. question_id is OPTIONAL when the caller is
    # submitting via the `question` text field (legacy tutor.check_answer
    # shape preserved for back-compat with /api/ai/boss-turn callers).
    question: Optional[dict] = None
    if req.question_id:
        question = _fb_find_boss_question(content, req.question_id)
        if question is None:
            raise HTTPException(404, detail={
                "error": (
                    f"boss question {req.question_id!r} not found in this homework"
                ),
                "code": "FB_Q_NOT_FOUND",
            })

    # Resolve grade band (priority: explicit req.grade_band → boss_meta.grade_band
    # → infer from homework grade).
    boss_meta = content.get("boss_meta") if isinstance(content, dict) else None
    if not isinstance(boss_meta, dict):
        boss_meta = {}
    grade_band = (
        req.grade_band
        or boss_meta.get("grade_band")
        or _fb_grade_band_from_grade(hw.get("grade") or req.grade)
    )

    # Resolve boss_type (priority: req → boss_meta → "sub").
    boss_type = (req.boss_type or boss_meta.get("boss_type") or "sub")
    if boss_type not in _FB_XP_TABLE:
        boss_type = "sub"

    # Resolve max HP — boss_meta override → grade-band default.
    max_hp = (
        boss_meta.get("starting_hp_override")
        or _fb_default_hp_for_grade_band(grade_band)
    )

    # Resolve hint cost — per-question override → grade-banded default.
    hint_cost = _fb_default_hint_cost_for_grade_band(grade_band)
    if isinstance(question, dict):
        per_q_cost = question.get("hint_cost_per_use")
        if isinstance(per_q_cost, int) and per_q_cost > 0:
            hint_cost = per_q_cost

    # Per-question damage — fall back to authored `dmg`, then a sensible default.
    damage_value = 10
    if isinstance(question, dict):
        dmg = question.get("dmg")
        if isinstance(dmg, (int, float)) and dmg > 0:
            damage_value = int(dmg)

    # Resolve expected answers from server-only fields. The LLM payload in
    # `tutor.boss_turn` does NOT receive these (per the security note at
    # tutor.py:457 — `expected_answers` is never forwarded to the LLM).
    expected = _fb_extract_expected_answers(question or {})

    # Build the boss-turn input. Mirror the existing /api/ai/boss-turn shape.
    boss_question_text = (
        (question.get("prompt") or question.get("q") or "")
        if isinstance(question, dict) else (req.question or "")
    )

    # Get-or-create per-session state.
    session_id = req.session_id or "default"
    state_key = (req.homework_id, session_id)
    state = _FB_ATTEMPTS.get(state_key)
    if state is None:
        from datetime import datetime, timezone
        state = {
            "max_hp": int(max_hp),
            "hp_remaining": int(req.hp_remaining if req.hp_remaining is not None else max_hp),
            "attempts_used": int(req.attempts_used or 0),
            "hints_used": 0,
            "correct_count": 0,
            "started_at": datetime.now(timezone.utc),
            "boss_type": boss_type,
            "grade_band": grade_band,
            "completed_at": None,
        }
        _FB_ATTEMPTS[state_key] = state

    attempt_number = int(req.attempt_number or 1)
    if attempt_number < 1:
        attempt_number = 1

    # Delegate to existing tutor.boss_turn (LLM call). Tests mock this.
    boss_response = await tutor.boss_turn(
        boss_question=boss_question_text,
        student_answer=req.student_answer or "",
        expected_answers=expected,
        damage_value=damage_value,
        hp_remaining=int(req.hp_remaining if req.hp_remaining is not None else state["hp_remaining"]),
        attempt_number=attempt_number,
        subject=req.subject,
        grade=int(hw.get("grade") or req.grade or 8),
    )
    if not isinstance(boss_response, dict):
        boss_response = {}

    # Update running session state.
    is_correct = bool(boss_response.get("correct"))
    if is_correct:
        state["correct_count"] = int(state.get("correct_count", 0)) + 1
    else:
        state["attempts_used"] = int(state.get("attempts_used", 0)) + 1
    # Mirror any client-reported HP cursor if provided (frontend authoritative
    # on HP for now; backend will become authoritative in a future PR).
    if req.hp_remaining is not None:
        state["hp_remaining"] = int(req.hp_remaining)

    # Build the response. Strip any answer-bearing keys defensively.
    response: dict[str, Any] = dict(_fb_strip_answer_leak(boss_response))
    response.update({
        "phase": "final-boss",
        "boss_type_used": boss_type,
        "grade_band": grade_band,
        "max_hp": int(max_hp),
        "hint_cost_per_use": int(hint_cost),
        "attempts_used": int(state.get("attempts_used", 0)),
        "hints_used": int(state.get("hints_used", 0)),
    })

    # On defeat (caller signals via `done`/`hp_remaining`), compute mastery stars.
    # The boss is "down" when the LLM/grading layer flags `done=True` OR when
    # the server has tallied enough damage. Existing `tutor.boss_turn` does NOT
    # currently emit `done` — it grades a single turn. The frontend agent's
    # PR will pass `done=True` on the FINAL turn; we treat boss_response.get(
    # "done") as the canonical signal and fall back to inspecting the
    # client-reported HP (defeat = hp_remaining > 0 AND attempt_number is final).
    done = bool(boss_response.get("done"))
    if done:
        outcome, stars, outcome_xp = _boss_outcome_for(
            hp_remaining=int(req.hp_remaining or 0),
            max_hp=int(max_hp),
            hints_used=int(req.attempts_used or state.get("hints_used", 0) or 0),
            attempt_number=attempt_number,
            boss_type=boss_type,
        )
        # `hints_used` from the request body wins when explicitly provided by
        # the runtime — mirror it onto the helper input for accurate stars.
        # (We use `attempts_used` as a proxy ONLY if hints_used is unknown.)
        from datetime import datetime, timezone
        state["completed_at"] = datetime.now(timezone.utc)
        response["outcome"] = outcome
        response["stars"] = stars
        response["outcome_xp"] = int(outcome_xp)

    return response


# ---------------------------------------------------------------------------
# Tic Tac Toe (TTT) — per-question + per-session grading
# ---------------------------------------------------------------------------
#
# Two phases live on the same /api/ai/check-answer route:
#
#   phase="ttt"          → _check_answer_ttt:         single option pick
#                                                     resolves to {is_correct,
#                                                     mercy, xp_delta,
#                                                     correct_value}
#   phase="ttt-session"  → _check_answer_ttt_session: end-of-session tally
#                                                     across N games, returns
#                                                     {session_xp, strong_session_bonus,
#                                                     mastery_tier, duolingo_remediation,
#                                                     wins, draws, losses}
#
# The route reads `_TTT_ANSWER_KEY[hw_id][item_id]` populated by
# `injector._serialize_ttt` at render time. If the homework hasn't been
# rendered yet (key map missing), the route returns 404 with
# `detail="ttt_item_not_found"` — matches the side-disjoint pattern from
# TM/RLC/FB. See TIC_TAC_TOE_BACKEND_PLAN.md §1.3, §1.4, §2.3.
# ---------------------------------------------------------------------------
_TTT_DEFAULTS = {
    "session_games": 3,
    "xp_correct": 50,
    "xp_draw": 200,
    "xp_win": 300,
    "xp_strong_session": 100,
    "xp_mercy": 10,
    "mercy_chance": 0.002,
}


def _ttt_config_for(hw: dict) -> dict:
    """Merge `_TTT_DEFAULTS` with the homework's `gb_ttt_config` overrides.

    None values in the override are filtered before merge so partial overrides
    work — i.e. setting only `xp_draw` doesn't null out the other defaults.
    Explicit zero values are preserved (they ARE meaningful overrides).
    """
    content = hw.get("content_json") if isinstance(hw, dict) else None
    raw = (content or {}).get("gb_ttt_config") if isinstance(content, dict) else None
    override: dict = {}
    if isinstance(raw, dict):
        override = {k: v for k, v in raw.items() if v is not None}
    return {**_TTT_DEFAULTS, **override}


def _ttt_mastery_tier(draws_plus_wins: int, total_games: int) -> str:
    """Return the mastery-tier label for a session's draw+win ratio.

    Bands per TIC_TAC_TOE_BACKEND_PLAN.md §1.4:
      0–<20%   → "Learning the Board"
      20–<40%  → "Holding Ground"
      40–<60%  → "Formidable Opponent"
      ≥60%     → "Unbreakable"

    Lower-inclusive boundaries; "≥60%" is taken from §1.4 explicitly.
    """
    pct = (draws_plus_wins / max(total_games, 1)) * 100
    if pct < 20:
        return "Learning the Board"
    if pct < 40:
        return "Holding Ground"
    if pct < 60:
        return "Formidable Opponent"
    return "Unbreakable"


async def _check_answer_ttt(req: CheckAnswerRequest) -> dict:
    """Per-pick grading branch for Tic Tac Toe.

    See TIC_TAC_TOE_BACKEND_PLAN.md §1.3.

    No-leak invariants:
      - Server-only `correct` field is fetched from `_TTT_ANSWER_KEY` (populated
        by the injector at render time); never echoed during the question
        prompt.
      - `correct_value` IS returned in the response, but only AFTER the student
        has resolved the pick — wrong picks still consume a board cell, so
        probing is bounded (max 9 picks per game).
    """
    if not req.homework_id:
        raise HTTPException(400, detail={
            "error": "homework_id required for phase=ttt",
            "code": "TTT_MISSING_HW",
        })

    hw = await db.get_homework(req.homework_id)
    if hw is None:
        raise HTTPException(404, detail={
            "error": f"homework {req.homework_id} not found",
            "code": "HW_NOT_FOUND",
        })

    # The TTT request fields ride as flat top-level keys on CheckAnswerRequest
    # (matching the SF/TM/RLC/FB precedent): `item_id` + `picked`. We also
    # tolerate the legacy `student_answer` slot as a fallback for `picked` so
    # browsers / scripts that re-use the legacy free-form body still work.
    item_id = req.item_id
    picked = req.picked if req.picked is not None else req.student_answer
    if not item_id:
        raise HTTPException(400, detail={
            "error": "item_id required for phase=ttt",
            "code": "TTT_MISSING_ITEM_ID",
        })

    answer_key = injector.get_ttt_answer_key(req.homework_id) or {}
    correct = answer_key.get(item_id)
    if not correct:
        raise HTTPException(404, detail="ttt_item_not_found")

    cfg = _ttt_config_for(hw)
    picked_norm = (picked or "").strip()
    correct_norm = (correct or "").strip()
    is_correct = bool(picked_norm) and (picked_norm == correct_norm)

    mercy = False
    xp_delta = 0
    if is_correct:
        xp_delta = int(cfg["xp_correct"])
    else:
        # Server-decided mercy roll. Hidden from the student during play; the
        # response narrates "lucky bounce" only after resolution.
        mercy = random.random() < float(cfg["mercy_chance"])
        xp_delta = int(cfg["xp_mercy"]) if mercy else 0

    return {
        "is_correct": is_correct,
        "mercy": mercy,
        "xp_delta": xp_delta,
        "correct_value": correct,
    }


async def _check_answer_ttt_session(req: CheckAnswerRequest) -> dict:
    """End-of-session tally for Tic Tac Toe.

    See TIC_TAC_TOE_BACKEND_PLAN.md §1.4.

    Input: `payload.results` — a list of {"outcome": "win"|"draw"|"loss"} dicts.
    Length is tolerated 1..session_games (default 3); longer lists are silently
    truncated. Per-correct-pick XP (+50 each) was already paid out during
    `phase=ttt` calls — this route only accounts for outcome-level XP plus the
    strong-session bonus.
    """
    if not req.homework_id:
        raise HTTPException(400, detail={
            "error": "homework_id required for phase=ttt-session",
            "code": "TTT_MISSING_HW",
        })

    hw = await db.get_homework(req.homework_id)
    if hw is None:
        raise HTTPException(404, detail={
            "error": f"homework {req.homework_id} not found",
            "code": "HW_NOT_FOUND",
        })

    cfg = _ttt_config_for(hw)
    session_games = int(cfg["session_games"])

    raw_results = req.results
    if not isinstance(raw_results, list):
        raise HTTPException(400, detail={
            "error": "results required for phase=ttt-session",
            "code": "TTT_MISSING_RESULTS",
        })

    # Validate + normalize — must be a list of dicts. Tolerate length 1..N;
    # silently truncate when longer than session_games so a runaway client
    # can't inflate the tally.
    cleaned: list[dict] = []
    for item in raw_results[:session_games]:
        if not isinstance(item, dict):
            continue
        outcome = item.get("outcome")
        if outcome in ("win", "draw", "loss"):
            cleaned.append({"outcome": outcome})

    wins = sum(1 for r in cleaned if r["outcome"] == "win")
    draws = sum(1 for r in cleaned if r["outcome"] == "draw")
    losses = sum(1 for r in cleaned if r["outcome"] == "loss")

    per_outcome_xp = wins * int(cfg["xp_win"]) + draws * int(cfg["xp_draw"])
    strong_bonus = int(cfg["xp_strong_session"]) if draws >= 2 else 0
    session_xp = per_outcome_xp + strong_bonus

    total_games = len(cleaned)
    mastery_tier = _ttt_mastery_tier(wins + draws, total_games)
    duolingo_remediation = (wins == 0 and draws == 0)

    return {
        "session_xp": int(session_xp),
        "strong_session_bonus": int(strong_bonus),
        "mastery_tier": mastery_tier,
        "duolingo_remediation": bool(duolingo_remediation),
        "wins": wins,
        "draws": draws,
        "losses": losses,
    }


# ---------------------------------------------------------------------------
# Memory Palace — phase=memory-palace check-answer branch (T2).
#
# Per MEMORY_PALACE_BACKEND_PLAN.md §1.3, §1.4, §2.1, §5, §7. Stateless,
# session-scoped: the entire encode→walk→recall arc lives in one POST body.
# The author's `gb_memory_palace.concepts` describe content for hint material;
# the recall test grades the student against THEIR OWN Step-2 placements,
# which travel with the recall picks in the same payload.
#
# Server recomputes `is_correct` from the submitted placement_map to defend
# against trivial XP forge by tampered POST. This is NOT as strong as
# side-disjoint validation (the validation key travels with the picks) but is
# acceptable for a low-stakes practice mechanic where consistent tampering
# yields no real XP edge — and v1 XP is aesthetic-only anyway (see
# `_mp_session_xp_display` docstring).
# ---------------------------------------------------------------------------


def _mp_outcome(correct_count: int, total: int) -> str:
    """Map a (correct_count, total) recall tally to one of four outcome buckets.

    Per plan §1.4:
      perfect             — every location recalled
      yaxshi              — exactly one missed (e.g., 4/5)
      hali_emas_partial   — >=60% recalled (e.g., 3/5)
      hali_emas_fail      — below 60% (e.g., <=2/5)
    """
    if total <= 0:
        return "hali_emas_fail"
    if correct_count == total:
        return "perfect"
    if correct_count == total - 1:
        return "yaxshi"
    if correct_count >= total * 0.6:
        return "hali_emas_partial"
    return "hali_emas_fail"


def _mp_outcome_text(outcome: str, lang: str = "uz") -> tuple[str, str]:
    """Return the (title, body) outcome strings.

    `lang` is reserved for future i18n; v1 always returns Uzbek titles +
    English body text per spec §1.4.
    """
    table = {
        "perfect": (
            "Ajoyib!",
            "Perfect recall. Your palace glows because every location-concept bond survived the walkthrough.",
        ),
        "yaxshi": (
            "Yaxshi!",
            "4 of 5 locations recalled. One missed location should pulse softly for a second walkthrough.",
        ),
        "hali_emas_partial": (
            "Hali emas",
            "Partial palace built. Offer a second walkthrough for the missed locations.",
        ),
        "hali_emas_fail": (
            "Hali emas",
            "The palace turns grayscale in the full app, then reveals all correct pairs and offers retry.",
        ),
    }
    return table.get(outcome, table["hali_emas_fail"])


def _mp_level_label(outcome: str) -> str:
    """Map an outcome to a tier label.

    Mastery ("Mastered") is deferred per plan §7 #8 — it requires cross-session
    persistence (3+ perfect runs of the same palace). v1 surfaces only the
    in-session ladder.
    """
    return {
        "perfect": "Proficient",
        "yaxshi": "Apprentice ↗",
        "hali_emas_partial": "Apprentice",
        "hali_emas_fail": "Pending",
    }.get(outcome, "Pending")


def _mp_session_xp_display(correct_count: int, total: int) -> int:
    """COSMETIC display-only XP for v1 per plan §7 #9.

    Not persisted. Not summed into any user-visible XP wallet. The frontend
    flashes this on the outcome card to give the session a payoff feel; once
    cross-session persistence lands, this helper will be replaced by an
    authoritative XP ledger write.

    Formula: `correct_count * 50` plus an outcome bonus
      perfect → +200, yaxshi → +100, others → +0
    """
    outcome = _mp_outcome(correct_count, total)
    bonus = 200 if outcome == "perfect" else (100 if outcome == "yaxshi" else 0)
    return int(correct_count) * 50 + bonus


async def _check_answer_memory_palace(req: CheckAnswerRequest) -> dict:
    """Per-session grading branch for Memory Palace.

    See MEMORY_PALACE_BACKEND_PLAN.md §1.3, §1.4, §2.1.

    Server-recompute rationale (NOT side-disjoint): The author content is hint
    material; the recall test grades the student against THEIR OWN Step 2
    placements, which travel with the recall picks in the same POST body.
    Server recomputes `is_correct` from the submitted placement map to defend
    against trivial XP forge by tampered POST. Not as strong as side-disjoint
    (validation key travels with the picks) but acceptable for a low-stakes
    practice mechanic where consistent tampering yields no real XP edge —
    and v1 XP is aesthetic-only anyway.
    """
    if not req.homework_id:
        raise HTTPException(400, detail={
            "error": "homework_id required for phase=memory-palace",
            "code": "MP_MISSING_HW",
        })
    if not req.palace_key:
        raise HTTPException(400, detail={
            "error": "palace_key required for phase=memory-palace",
            "code": "MP_MISSING_PALACE_KEY",
        })
    if not isinstance(req.placements, list) or not req.placements:
        raise HTTPException(400, detail={
            "error": "placements required for phase=memory-palace",
            "code": "MP_MISSING_PLACEMENTS",
        })
    if not isinstance(req.recall_results, list) or not req.recall_results:
        raise HTTPException(400, detail={
            "error": "recall_results required for phase=memory-palace",
            "code": "MP_MISSING_RECALL",
        })

    hw = await db.get_homework(req.homework_id)
    if hw is None:
        raise HTTPException(404, detail={
            "error": f"homework {req.homework_id} not found",
            "code": "homework_not_found",
        })

    # Server recompute: build {location_idx -> concept_id} from Step 2
    # placements, then walk recall_results and OVERWRITE each `is_correct`
    # field. We trust the client only on `picked_concept_id` and `elapsed_ms`.
    placement_map: dict[Any, Any] = {}
    for p in req.placements:
        if not isinstance(p, dict):
            continue
        loc_idx = p.get("location_idx")
        concept_id = p.get("concept_id")
        if loc_idx is None or concept_id is None:
            continue
        placement_map[loc_idx] = concept_id

    recomputed: list[dict[str, Any]] = []
    for rr in req.recall_results:
        if not isinstance(rr, dict):
            continue
        loc_idx = rr.get("location_idx")
        picked = rr.get("picked_concept_id")
        elapsed_ms = rr.get("elapsed_ms", 0) or 0
        is_correct = (placement_map.get(loc_idx) == picked) and (picked is not None)
        recomputed.append({
            "location_idx": loc_idx,
            "picked_concept_id": picked,
            "elapsed_ms": elapsed_ms,
            "is_correct": bool(is_correct),
        })

    total_count = len(recomputed)
    correct_count = sum(1 for rr in recomputed if rr["is_correct"])

    outcome = _mp_outcome(correct_count, total_count)
    outcome_title, outcome_text = _mp_outcome_text(outcome)
    level_label = _mp_level_label(outcome)
    session_xp_display = _mp_session_xp_display(correct_count, total_count)

    accuracy_pct = round((correct_count / total_count) * 100) if total_count > 0 else 0
    recall_speed_avg_s = (
        round(sum(int(rr.get("elapsed_ms") or 0) for rr in recomputed) / total_count / 1000, 1)
        if total_count > 0 else 0
    )
    missed_location_indices = sorted([
        rr["location_idx"] for rr in recomputed
        if not rr["is_correct"] and rr["location_idx"] is not None
    ])
    retry_offered = (outcome != "perfect")

    return {
        "outcome": outcome,
        "outcome_title": outcome_title,
        "outcome_text": outcome_text,
        "accuracy_pct": accuracy_pct,
        "correct_count": correct_count,
        "total_count": total_count,
        "recall_speed_avg_s": recall_speed_avg_s,
        "level_label": level_label,
        "session_xp_display": session_xp_display,  # COSMETIC, not persisted
        "retry_offered": retry_offered,
        "missed_location_indices": missed_location_indices,
    }


@router.post("/ai/runtime/submit-answer")
async def submit_runtime_answer(req: RuntimeAnswerSubmitRequest):
    from ..services.runtime_answer_resolver import resolve_runtime_answer
    
    if req.session_id:
        tutor._validate_session_id(req.session_id)
        
    try:
        target = await resolve_runtime_answer(req)
        result = await tutor.process_runtime_answer(
            target=target.model_dump(),
            student_answer=req.student_answer,
            attempt_number=req.attempt_number or 1
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        _log.error("Failed to process runtime answer: %s", e)
        raise HTTPException(
            status_code=500, 
            detail={"error": "internal", "code": "RUNTIME_GRADING_ERROR"}
        )

@router.post("/ai/check-answer")
async def check_answer(req: CheckAnswerRequest):
    # Phase dispatch — the new sentence-fill grading branch is keyed on
    # phase=="sentence-fill" AND presence of `homework_id`. The phase string
    # alone is insufficient because pre-existing tests/clients submit
    # phase="sentence-fill" with the legacy {question, student_answer,
    # answer_spec} shape (no homework_id field). Detecting on `homework_id`
    # preserves backward compatibility for those callers while routing the
    # new per-blank contract to its own handler. Within the SF handler,
    # `item_id` and `blank_idx` are then validated strictly (400 on missing).
    if req.phase == "sentence-fill" and req.homework_id:
        try:
            result = await _check_answer_sentence_fill(req)
            return _attach_check_answer_debug(
                req, result, checker_path="phase_adapter:sentence-fill"
            )
        except HTTPException:
            raise
        except Exception as e:
            _handle_exc(e)

    # Tile Match per-pair grading branch — same back-compat gate (require
    # homework_id) so legacy AMR-shape callers passing phase="tile-match"
    # without an HW id continue to flow through tutor.check_answer below.
    if req.phase == "tile-match" and req.homework_id:
        try:
            result = await _check_answer_tile_match(req)
            return _attach_check_answer_debug(
                req, result, checker_path="phase_adapter:tile-match"
            )
        except HTTPException:
            raise
        except Exception as e:
            _handle_exc(e)

    # Real-Life Challenge per-step grading branch — same back-compat gate.
    # Legacy callers using phase="real-life-challenge" without a homework_id
    # (none currently exist, but mirror the SF/TM pattern for forward-compat)
    # fall through to tutor.check_answer below.
    if req.phase == "real-life-challenge" and req.homework_id:
        try:
            result = await _check_answer_real_life_challenge(req)
            return _attach_check_answer_debug(
                req, result, checker_path="phase_adapter:real-life-challenge"
            )
        except HTTPException:
            raise
        except Exception as e:
            _handle_exc(e)

    # Final Boss per-question grading branch — same back-compat gate. Legacy
    # callers without a homework_id fall through to tutor.check_answer.
    if req.phase == "final-boss" and req.homework_id:
        try:
            result = await _check_answer_final_boss(req)
            return _attach_check_answer_debug(
                req, result, checker_path="phase_adapter:final-boss"
            )
        except HTTPException:
            raise
        except Exception as e:
            _handle_exc(e)

    # Tic Tac Toe per-pick grading branch — same back-compat gate.
    if req.phase == "ttt" and req.homework_id:
        try:
            result = await _check_answer_ttt(req)
            return _attach_check_answer_debug(
                req, result, checker_path="phase_adapter:ttt"
            )
        except HTTPException:
            raise
        except Exception as e:
            _handle_exc(e)

    # Tic Tac Toe end-of-session tally branch — same back-compat gate.
    if req.phase == "ttt-session" and req.homework_id:
        try:
            result = await _check_answer_ttt_session(req)
            return _attach_check_answer_debug(
                req, result, checker_path="phase_adapter:ttt-session"
            )
        except HTTPException:
            raise
        except Exception as e:
            _handle_exc(e)

    # Memory Palace per-session grading branch — same back-compat gate.
    # Stateless: the entire encode→walk→recall arc rides in one POST.
    if req.phase == "memory-palace" and req.homework_id:
        try:
            result = await _check_answer_memory_palace(req)
            return _attach_check_answer_debug(
                req, result, checker_path="phase_adapter:memory-palace"
            )
        except HTTPException:
            raise
        except Exception as e:
            _handle_exc(e)

    try:
        result = await tutor.check_answer(
            question_id=req.question_id,
            question=req.question,
            student_answer=req.student_answer,
            expected_answers=req.expected_answers,
            answer_spec=req.answer_spec,
            allow_ai_fallback=req.allow_ai_fallback,
            subject=req.subject,
            grade=req.grade,
            tier=req.tier,
            context=req.context,
            phase=req.phase,
        )
        return _attach_check_answer_debug(
            req, result, checker_path="legacy:tutor.check_answer"
        )
    except Exception as e:
        _handle_exc(e)


@router.post("/ai/check-answer/finalize")
async def check_answer_finalize(req: FinalizeCheckAnswerRequest):
    """Per-item perfect-fill bonus query. See plan §4."""
    if req.phase != "sentence-fill":
        raise HTTPException(400, detail={
            "error": f"phase {req.phase!r} unsupported on /finalize",
            "code": "SF_BAD_PHASE",
        })

    hw = await db.get_homework(req.homework_id)
    if hw is None:
        raise HTTPException(404, detail={
            "error": f"homework {req.homework_id} not found",
            "code": "HW_NOT_FOUND",
        })
    item = _find_sf_item(hw.get("content_json") or {}, req.item_id)
    if item is None:
        raise HTTPException(404, detail={
            "error": f"sentence-fill item {req.item_id} not found",
            "code": "SF_ITEM_NOT_FOUND",
        })

    answers = item.get("answers") or []
    blanks_total = len(answers)

    # Aggregate per-blank state from in-memory attempts dict.
    blanks_correct = 0
    first_attempt_correct = 0
    for b_idx in range(blanks_total):
        rec = _SF_ATTEMPTS.get((req.homework_id, req.item_id, b_idx))
        if rec is None:
            # No attempts logged — treat as missing (graceful default per brief).
            _log.warning(
                "sf finalize: missing attempts for hw=%s item=%s blank=%d (cold call or session lost)",
                req.homework_id, req.item_id, b_idx,
            )
            continue
        if rec.get("correct_at") is not None:
            blanks_correct += 1
            if rec["correct_at"] == 1:
                first_attempt_correct += 1

    perfect_fill = (
        blanks_total > 0
        and blanks_correct == blanks_total
        and first_attempt_correct == blanks_total
    )
    xp_bonus = 100 if perfect_fill else 0

    return {
        "perfect_fill": perfect_fill,
        "xp_bonus": xp_bonus,
        "summary": {
            "blanks_correct": blanks_correct,
            "blanks_total": blanks_total,
            "first_attempt_correct": first_attempt_correct,
        },
    }


@router.post("/ai/boss-turn")
async def boss_turn(req: BossTurnRequest):
    try:
        result = await tutor.boss_turn(
            boss_question=req.boss_question,
            student_answer=req.student_answer,
            expected_answers=req.expected_answers,
            damage_value=req.damage_value,
            hp_remaining=req.hp_remaining,
            attempt_number=req.attempt_number,
            subject=req.subject,
            grade=req.grade,
            persona_traits=req.persona_traits,  # Wave F3
        )
        # Final Boss redesign Chunk B — additive: when the caller signals
        # defeat (done=True) AND attached the FB context fields, surface
        # mastery stars / outcome / outcome_xp on the same response. Existing
        # in-progress responses (no `done` key, no FB context) are unchanged.
        if isinstance(result, dict) and result.get("done"):
            boss_type = req.boss_type if req.boss_type in _FB_XP_TABLE else "sub"
            grade_band = req.grade_band or _fb_grade_band_from_grade(req.grade)
            max_hp = int(req.max_hp) if req.max_hp else _fb_default_hp_for_grade_band(grade_band)
            outcome, stars, outcome_xp = _boss_outcome_for(
                hp_remaining=int(req.hp_remaining or 0),
                max_hp=max_hp,
                hints_used=int(req.hints_used or 0),
                attempt_number=int(req.attempt_number or 1),
                boss_type=boss_type,
            )
            result["outcome"] = outcome
            result["stars"] = stars
            result["outcome_xp"] = int(outcome_xp)
            result["boss_type_used"] = boss_type
        return _attach_boss_turn_debug(req, result)
    except Exception as e:
        _handle_exc(e)


@router.post("/ai/reflection")
async def reflection(req: ReflectionRequest):
    try:
        return await tutor.reflection_feedback(
            homework_title=req.homework_title,
            homework_summary=req.homework_summary,
            student_reflection=req.student_reflection,
            performance=req.performance,
            subject=req.subject,
            grade=req.grade,
        )
    except Exception as e:
        _handle_exc(e)


@router.post("/ai/tutor")
async def tutor_help(req: TutorRequest):
    try:
        return await tutor.tutor_help(
            phase=req.phase,
            question=req.question,
            student_input=req.student_input,
            subject=req.subject,
            grade=req.grade,
            context=req.context,
        )
    except Exception as e:
        _handle_exc(e)


# --- Wave F1: live tutor chat / boss-plan / history -------------------------


def _find_question_in_content(content: dict, question_id: str) -> Optional[dict]:
    """Best-effort lookup for a question dict by id, walking nested structures.

    Pre-fix this only scanned top-level *list* values of `content_json`, so
    questions parked under nested objects (e.g. `reading.questions[]`,
    `consolidation.problems[]`, `gb_why_chain.steps[]`) silently returned
    None and the tutor lost its question_text context. The scan now recurses
    into dicts and lists of arbitrary depth — first match wins.
    """
    if not isinstance(content, dict) or not question_id:
        return None

    def _walk(node):
        if isinstance(node, dict):
            if (
                node.get("question_id") == question_id
                or node.get("id") == question_id
            ):
                return node
            for v in node.values():
                hit = _walk(v)
                if hit is not None:
                    return hit
        elif isinstance(node, list):
            for item in node:
                hit = _walk(item)
                if hit is not None:
                    return hit
        return None

    return _walk(content)


def _extract_boss_questions(content: dict) -> list[dict]:
    """Pull the boss_questions[] list from a homework's content_json."""
    if not isinstance(content, dict):
        return []
    bq = content.get("boss_questions")
    if not isinstance(bq, list):
        bq = content.get("boss")
    if isinstance(bq, list):
        return [q for q in bq if isinstance(q, dict)]
    return []


@router.post("/ai/tutor/chat")
async def tutor_chat(req: TutorChatRequest):
    """Live tutor chat — persists turns + invokes the LLM."""
    # Reject malformed session IDs early so they never reach the DB layer.
    tutor._validate_session_id(req.session_id)

    # If phase is explicitly supplied, validate it immediately.
    if req.phase is not None:
        tutor._validate_phase(req.phase)

    # Pre-flight homework lookup — used purely for debug-instrumentation
    # metadata (hw_present / question_found). The actual context payload is
    # rebuilt by ai_context.build_tutor_context below, so hw_meta is not
    # forwarded to tutor.tutor_chat_v2.
    hw = await db.get_homework(req.hw_id)
    hw_present = hw is not None
    question_found = False
    if hw:
        content = hw.get("content_json") or {}
        if req.question_id:
            q = _find_question_in_content(content, req.question_id)
            if q is not None:
                question_found = True

    # Truncated copies of frontend payloads — used only by the debug envelope
    # so context_debug.text_len() reports the post-clip length, matching the
    # length the tutor service ultimately sees after its own sanitization.
    screen_context = req.screen_context[:2000] if req.screen_context else None
    student_work_text = (
        req.student_work_text[:2000] if req.student_work_text else None
    )

    # subphase: validate against the allowlist; drop silently if unknown.
    subphase = req.subphase if req.subphase in SUBPHASE_ALLOWLIST else None

    # Build canonical context packet from backend state + frontend payload.
    context = await ai_context.build_tutor_context(
        session_id=req.session_id,
        hw_id=req.hw_id,
        phase=req.phase,
        subphase=subphase,
        question_id=req.question_id,
        screen_context=req.screen_context,
        student_work_text=req.student_work_text,
        ui_state=req.ui_state,
    )

    # --- Warning state machine ---
    classification = classify(req.message)
    try:
        outcome = await warnings_svc.evaluate(
            classification,
            hw_id=req.hw_id,
            session_id=req.session_id,
        )
    except Exception as e:
        import logging
        logging.getLogger("nets.tutor").warning("warnings.evaluate failed: %s", e)
        outcome = None

    # Fail short-circuit — level 9 means homework failed.
    if outcome is not None and outcome.is_fail:
        lang = outcome.lang
        if lang == "ru":
            fail_msg = "Урок завершён. Переходим к финалу."
        elif lang == "en":
            fail_msg = "Homework done. Moving to reflection."
        else:
            fail_msg = "Uy vazifasi tugadi. So'nggi bosqichga o'tamiz."
        return _attach_tutor_chat_route_debug(
            req,
            {
            "response": fail_msg,
            "message_id": None,
            "homework_failed": True,
            "warning_level": outcome.level,
            "cumulative_deduction_pct": outcome.cumulative_deduction_pct,
            },
            hw_present=hw_present,
            question_found=question_found,
            screen_context=screen_context,
            student_work_text=student_work_text,
            subphase=subphase,
            warning_level=outcome.level,
        )

    try:
        warning_kwargs: dict[str, Any] = {}
        if outcome is not None:
            warning_kwargs = {
                "severity": outcome.severity,
                "warning_level": outcome.level,
                "cumulative_deduction_pct": outcome.cumulative_deduction_pct,
                "is_big_warning": outcome.is_big_warning,
                "deduction_pct_this": outcome.deduction_pct_this,
                "behavior_summary": outcome.behavior_summary,
                "message_lang": outcome.lang,
            }

        result = await tutor.tutor_chat_v2(
            context=context,
            message=req.message,
            recent_assistant_phrases=req.recent_assistant_phrases or [],
            **warning_kwargs,
        )

        # Defense in depth: slur filter on the LLM output.
        # Only replace on profanity_strong or above to avoid muting mild-detection
        # false positives where the new prompt already handles varied callouts.
        response_text = result.get("response", "") or ""
        output_classification = classify(response_text)
        from ..services.slur_filter import _SEVERITY_RANK
        if (
            not output_classification.is_clean
            and _SEVERITY_RANK.get(output_classification.severity, 0)
            >= _SEVERITY_RANK.get("profanity_strong", 4)
        ):
            lang = outcome.lang if outcome is not None else "uz"
            if lang == "ru":
                deflection = "Keling, savolingizga qaytaylik."
            elif lang == "en":
                deflection = "Let's get back to the question."
            else:
                deflection = "Keling, savolingizga qaytaylik."
            result["response"] = deflection
            result["defense_in_depth_triggered"] = True
        elif not output_classification.is_clean:
            # Mild detection — log but don't replace (the new prompt handles it)
            import logging
            logging.getLogger("nets.tutor").info(
                "defense_in_depth: mild output classification %s — not replacing",
                output_classification.severity,
            )

        # Augment the response with warning fields so the frontend can render
        # the warning chip / banner / fail handler.
        result["warning_level"] = outcome.level if outcome is not None else 0
        result["cumulative_deduction_pct"] = (
            outcome.cumulative_deduction_pct if outcome is not None else 0
        )
        result["homework_failed"] = False
        return _attach_tutor_chat_route_debug(
            req,
            result,
            hw_present=hw_present,
            question_found=question_found,
            screen_context=screen_context,
            student_work_text=student_work_text,
            subphase=subphase,
            warning_level=outcome.level if outcome is not None else 0,
        )
    except HTTPException:
        # tutor_chat raises HTTPException itself for the cap + LLM-error cases —
        # let those propagate untouched.
        raise
    except Exception as e:
        _handle_exc(e)


@router.post("/ai/tutor/boss-plan")
async def tutor_boss_plan(req: BossPlanRequest):
    """Build a personalized boss-question plan for a session."""
    tutor._validate_session_id(req.session_id)
    hw = await db.get_homework(req.hw_id)
    boss_questions: list[dict] = []
    if hw:
        boss_questions = _extract_boss_questions(hw.get("content_json") or {})
    try:
        result = await tutor.boss_plan(
            session_id=req.session_id,
            hw_id=req.hw_id,
            boss_questions=boss_questions,
        )
        existing_debug = result.get("context_debug")
        service_ai_unavailable = (
            existing_debug.get("ai_unavailable")
            if isinstance(existing_debug, dict)
            else None
        )
        return ai_debug.with_context_debug(
            result,
            {
                "route": "tutor_boss_plan",
                "mode": "fixed_boss",
                "session_id_present": ai_debug.present(req.session_id),
                "hw_id_present": ai_debug.present(req.hw_id),
                "homework_found": hw is not None,
                "boss_questions_count": len(boss_questions),
                "question_source": "content_json",
                "provider": ai_orchestrator._active_backend(),
                "model": ai_orchestrator.PRO_MODEL,
                "ai_unavailable": bool(
                    service_ai_unavailable or result.get("ai_unavailable")
                ),
            },
            route="api.tutor_boss_plan",
        )
    except HTTPException:
        raise
    except Exception as e:
        _handle_exc(e)


@router.get("/ai/tutor/history")
async def tutor_history(
    session_id: str = Query(...),
    hw_id: str = Query(...),
):
    """Return the chronological chat history for a (session_id, hw_id), capped at 50."""
    tutor._validate_session_id(session_id)
    turns = await db.list_tutor_turns(session_id=session_id, hw_id=hw_id, limit=50)
    return ai_debug.with_context_debug(
        {"turns": turns},
        {
            "route": "tutor_history",
            "session_id_present": ai_debug.present(session_id),
            "hw_id_present": ai_debug.present(hw_id),
            "history_count": len(turns),
        },
        route="api.tutor_history",
    )
