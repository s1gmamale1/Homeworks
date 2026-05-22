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
from ..services.tutor import _fence_untrusted, _strip_fence_tags
from ..services.slur_filter import classify, detect_slurs
from ..services import warnings as warnings_svc
from ..services.gate_state import is_practice_unlocked
from ..services.tile_match_tokens import (
    resolve_tm_pairs,
    build_token_maps,
    left_token,
    right_token,
)
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
    # Anti-cheat signal ingestion (ADVISORY — never alters grading). Both
    # optional; an absent value is treated as "unknown / not measured" and
    # produces zero integrity signal. `client_time_ms` is clamped server-side
    # before use; `paste_detected` only matters on opt-in assessment phases.
    client_time_ms: Optional[int] = None
    paste_detected: Optional[bool] = None

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

    # Case-Based Preview / Memory Check phase fields.
    # `item_index` is the 0-based index of the checkpoint (case_based_preview)
    # or item (memory_check) within the homework's content_json array.
    # The server resolves the matching answer_spec from content_json — the
    # client NEVER sends the expected answer value.
    item_index: Optional[int] = None

    # Anti-cheat signal ingestion (ADVISORY — never alters grading). Optional;
    # absent = "unknown / not measured" → zero integrity signal. Mirrors the
    # fields on RuntimeAnswerSubmitRequest so the legacy /check-answer surface
    # can carry the same signals.
    client_time_ms: Optional[int] = None
    paste_detected: Optional[bool] = None

    # Soft-friction follow-up (anti-cheat wiring). When the runtime surfaces an
    # `integrity_nudge` (a strong-flag "explain in your own words" prompt), the
    # student's free-text reply is posted back here. A submit that carries a
    # `nudge_response` (or `subphase=="integrity-nudge"`) is recorded as an
    # ADVISORY session event and EARLY-RETURNS `{"advisory": true}` — it is NEVER
    # graded and never produces a score. Mirrors the same contract on the
    # /ai/runtime/submit-answer surface. `subphase` is also threaded into the
    # integrity engine on graded submits (G1).
    subphase: Optional[str] = None
    nudge_response: Optional[str] = None

    # Division-3 Practices phase fields (per _DIV3_CONTRACT.md §"Request
    # contract"). Each new phase reuses `homework_id`/`session_id`/`item_id`
    # plus a subset of these. All Optional so existing callers are unaffected;
    # each handler validates the fields it actually needs.
    #   - uniform MCQ checkpoint: checkpoint_index + selected_index
    #   - error-detection: stage ("spot"|"correction"|"why") + block_id + correction
    #   - assembly: order
    #   - problem-trace: step_index + selected_index
    #   - counterexample: selected_case_id (+ checkpoint_index/selected_index for
    #     the optional explanation MCQ)
    #   - DPE / open-ended: reasoning_text (already defined above)
    #   - escape hatch: payload_json
    checkpoint_index: Optional[int] = None
    selected_index: Optional[int] = None
    stage: Optional[str] = None              # error-detection: "spot" | "correction" | "why"
    block_id: Optional[str] = None           # error-detection: the work-block the student tapped
    correction: Optional[str] = None         # error-detection (correction stage): typed fix
    order: Optional[list[str]] = None        # assembly: the ordered piece ids
    step_index: Optional[int] = None         # problem-trace + dependency-chain: which step's MCQ
    selected_case_id: Optional[str] = None   # counterexample: the case the student picked
    cell_id: Optional[str] = None            # ttt-grid: the cell the student picked
    confidence: Optional[str] = None         # confidence-check: "sure" | "maybe" | "guess"
    payload_json: Optional[dict[str, Any]] = None  # escape hatch — avoid unless needed


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
    # Integrity-resolution fields (anti-cheat wiring, 2026-05-22). Optional so
    # the legacy grading-review decide path is unchanged. The whole request is
    # persisted verbatim into `decision_json`, so a teacher can record how an
    # integrity flag was resolved (e.g. integrity_outcome="cleared" /
    # "confirmed" / "dismissed") without a schema change.
    integrity_reason: Optional[str] = None
    integrity_outcome: Optional[str] = None


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


async def _attach_integrity(
    req: CheckAnswerRequest,
    result: dict[str, Any],
) -> dict[str, Any]:
    """Shared post-grading integrity hook for the /ai/check-answer surface (G1).

    The v2 React runtime submits CBP checkpoints, CBP reasoning, Memory Check
    and the practice-arc games to ``POST /api/ai/check-answer`` — which NEVER
    routes through ``tutor.process_runtime_answer``. So the integrity engine +
    signal ingestion + soft-friction nudge only ran for the tutor runtime + the
    boss before this hook. This wires the SAME engine into the check-answer
    branches by REUSING ``evaluate_runtime_submit`` (no forked flag logic).

    ADVISORY + BEST-EFFORT, exactly like the runtime path:
      - never changes ``correct`` / ``is_correct`` / ``score`` / ``feedback`` /
        ``passed`` — it only *adds* an optional ``integrity_nudge`` key,
      - any failure is swallowed and the graded ``result`` is returned unchanged,
      - ``client_time_ms`` is clamped via ``clamp_client_time_ms`` (H1),
      - it runs AFTER the branch persisted its ``phase_attempt`` row, so the
        assessment correct-rate the engine derives includes THIS submit.

    Covers ``case_based_preview`` / ``case_based_preview_reasoning`` /
    ``memory_check`` (the assessment phases) plus the games (which the engine
    no-ops as non-assessment under the AI-use policy). Returns ``result``.
    """
    if not isinstance(result, dict):
        return result
    try:
        from ..services.integrity_wiring import (
            evaluate_runtime_submit,
            clamp_client_time_ms,
        )

        session_id = req.session_id or "default"
        hw_id = req.homework_id
        if not hw_id:
            return result  # no homework context → nothing to attribute a flag to

        # Resolve the per-homework anti-cheat policy + grade-level from
        # content_json (mirrors the runtime path's boss_meta sourcing).
        boss_meta = None
        hw_grade = None
        try:
            homework = await db.get_homework(hw_id)
            content_json = (homework or {}).get("content_json") or {}
            boss_meta = content_json.get("boss_meta")
            hw_grade = content_json.get("grade") or (homework or {}).get("grade")
        except Exception:
            boss_meta = None
            hw_grade = None

        nudge = await evaluate_runtime_submit(
            session_id=session_id,
            hw_id=hw_id,
            phase=req.phase or "",
            subphase=req.subphase or None,
            question_id=req.question_id or None,
            time_ms=clamp_client_time_ms(req.client_time_ms),
            paste_detected=req.paste_detected,
            grade=hw_grade,
            boss_meta=boss_meta,
        )
        if nudge:
            result["integrity_nudge"] = nudge
    except Exception as _integrity_exc:  # never break grading
        _log.warning(
            "check-answer integrity hook failed (non-fatal): %s", _integrity_exc
        )
    return result


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
async def get_review_queue(kind: Optional[str] = Query(default=None)):
    """List pending review items.

    Without ``?kind=`` this returns every pending row (grading + integrity),
    preserving the legacy behavior. With ``?kind=integrity`` (or
    ``?kind=grading``) the listing is filtered to that lane so a teacher can
    triage ADVISORY integrity flags separately from grading-review items.
    """
    from .. import db
    return await db.get_review_queue(kind=kind)

@router.post("/ai/review-queue/{id}/decide")
async def decide_review_queue(req: ReviewDecideRequest, id: int = PathParam(...)):
    from .. import db

    # M2 — an ADVISORY kind='integrity' row is NOT gradeable. A teacher resolves
    # it by recording an `integrity_outcome` (e.g. "cleared" / "confirmed" /
    # "dismissed"), never a normal {correct, score, feedback} grading verdict.
    # Refuse a grading decision against an integrity row so a flag can never be
    # mistaken for / converted into a grade.
    kind = await db.get_review_item_kind(id)
    if kind == "integrity" and not req.integrity_outcome:
        raise HTTPException(
            400,
            detail={
                "error": (
                    "integrity review rows are advisory — resolve them with an "
                    "integrity_outcome, not a grading decision"
                ),
                "code": "RQ_INTEGRITY_NOT_GRADEABLE",
            },
        )

    # exclude_none keeps the legacy {correct, score, feedback} decision payload
    # byte-identical when the optional integrity-resolution fields are omitted;
    # they only appear in `decision_json` when a teacher actually sets them.
    success = await db.resolve_review_item(id, req.model_dump(exclude_none=True))
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

    # BLOCKER #3 — Practice Arc must be server-enforced before grading.
    # Sentence-Fill is a practice-arc game; refuse to grade for a locked session.
    await _enforce_practice_unlocked(req)

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

    # Persist attempt (best-effort side-effect — never breaks answer-checking).
    # Mirrors the CBP/MC/Phase-2B persisting calls. Only when session_id is
    # present (some preview/anon calls omit it); homework_id is already required
    # above. The Reflection engine reads these rows to extract real performance.
    if req.session_id and req.homework_id:
        import json as _json
        try:
            from ..db.attempts_repo import add_phase_attempt as _add_phase_attempt
            await _add_phase_attempt(
                session_id=req.session_id,
                hw_id=req.homework_id,
                phase="sentence-fill",
                subphase=f"blank_{req.blank_idx}",
                question_id=req.question_id or f"{req.item_id}_{req.blank_idx}",
                item_id=req.item_id,
                attempt_number=attempt_number,
                student_answer=str(student_value),
                answer_spec_json=_json.dumps({"type": "text_fuzzy"}),
                checker_source="phase_adapter:sentence-fill",
                correct=1 if is_correct else 0,
                score=1.0 if is_correct else 0.0,
            )
        except Exception as _e:  # noqa: BLE001 — attempt persistence is best-effort
            _log.warning("SF: failed to persist attempt: %s", _e)

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


async def _enforce_practice_unlocked(req: "CheckAnswerRequest") -> None:
    """Server-side Practice Arc gate (BLOCKER #3 — defense in depth).

    The practice-arc games (tile-match / final-boss / future games) must not
    grade an answer unless the student actually unlocked the arc by completing
    both learning sections. The frontend gate is presentation-only; a tampered
    client can call these endpoints directly after hydrating display content.
    This is the authoritative enforcement.

    Raises HTTPException(403, code="PRACTICE_LOCKED") when the arc is still
    locked for this session+homework. Do NOT call this from the CBP/MC learning
    phases — those ARE the unlock path.
    """
    if not await is_practice_unlocked(req.session_id, req.homework_id):
        raise HTTPException(403, detail={
            "error": "Practice Arc is locked — complete both learning sections first",
            "code": "PRACTICE_LOCKED",
        })


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

    # BLOCKER #3 — Practice Arc must be server-enforced before grading. Tile
    # Match is a practice-arc game; refuse to grade for a locked session.
    await _enforce_practice_unlocked(req)

    hw = await db.get_homework(req.homework_id)
    if hw is None:
        raise HTTPException(404, detail={
            "error": f"homework {req.homework_id} not found",
            "code": "HW_NOT_FOUND",
        })
    content = hw.get("content_json") or {}
    # Opaque-token scheme: `resolve_tm_pairs` gives the canonical, display-only
    # ({left, right}) order used to mint the per-side tokens; the token maps
    # translate the client-supplied opaque left_id/right_id back to a pair
    # INDEX. The pair index is never exposed to the client, so a tampered
    # client can no longer match by submitting `left_id == right_id`.
    #
    # The XP-bonus logic (tier / palace / concept_family / explanation) needs
    # the full authored pair, which the token resolver strips. `_resolve_tm_pairs`
    # preserves those fields in the SAME canonical order (contract: identical
    # ordering), so we index the authored list by the same ordinal.
    pairs = resolve_tm_pairs(content)
    authored_pairs = _resolve_tm_pairs(content)
    if not pairs:
        raise HTTPException(404, detail={
            "error": "tile-match content not found on this homework",
            "code": "TM_NO_CONTENT",
        })
    lid_map, rid_map = build_token_maps(req.homework_id, len(pairs))

    i_left = lid_map.get(req.left_id)
    if i_left is None:
        raise HTTPException(400, detail={
            "error": f"left_id {req.left_id} not found in this tile-match board",
            "code": "TM_BAD_LEFT_ID",
        })
    i_right = rid_map.get(req.right_id)
    if i_right is None:
        raise HTTPException(400, detail={
            "error": f"right_id {req.right_id} not found in this tile-match board",
            "code": "TM_BAD_RIGHT_ID",
        })

    # The matched-pair-id state machine keys off the canonical pair INDEX (the
    # left tile's pair). Indexing is stable across requests and independent of
    # whether the resolver carries an authored `id`. The bonus metadata comes
    # from the authored pair at the same ordinal.
    pair = authored_pairs[i_left] if i_left < len(authored_pairs) else pairs[i_left]
    matched_key = i_left

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
    already_matched = matched_key in state["matched_pair_ids"]

    # Correct when the left tile's pair index equals the right tile's pair
    # index (both resolved from opaque tokens above).
    is_correct = (i_left == i_right) and not already_matched

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
        state["matched_pair_ids"].add(matched_key)
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

        # Branch-complete bonus: this match drains the concept_family. Compute
        # the family's member set by canonical INDEX (matched_pair_ids stores
        # indices) so the comparison is consistent with the new token scheme.
        family = pair.get("concept_family") if isinstance(pair, dict) else None
        if family and family not in state["completed_families"]:
            family_pair_indices = {
                idx for idx, p in enumerate(authored_pairs)
                if isinstance(p, dict) and p.get("concept_family") == family
            }
            if family_pair_indices and family_pair_indices.issubset(state["matched_pair_ids"]):
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
        # Hint = the LEFT-side concept text of the wrongly-picked right tile's
        # TRUE partner (already visible on screen — not a new leak surface).
        right_pair = pairs[i_right]
        hint = (right_pair.get("left", "") if isinstance(right_pair, dict) else "") or None

    xp_total = xp_base + xp_speed + xp_streak + xp_palace + xp_branch

    matched_count = len(state["matched_pair_ids"])
    outcome, completion_bonus = _outcome_for(
        state["wrong_count"],
        matched_count,
        total_pairs,
        state["remaining_seconds"],
    )
    complete = outcome is not None

    # Echo the full set of currently-matched pairs back to the client as per-side
    # tokens (PR #251 backend half). Production sessions never replay tile-match,
    # but after a page reload mid-game the React component remounts with an empty
    # matched-set while the server-side _TM_ATTEMPTS dict still holds the prior
    # session's progress. Without this echo, every click on an already-matched
    # pair returns `correct: false, already_matched=true` and the UI stays stuck
    # at "0/N matched" — the user sees nothing happen. Sending the full token
    # list lets the client re-sync its display state from any response.
    #
    # No-leak: emit ONLY the opaque per-side HMAC tokens (lid/rid), never the
    # pair INDEX or any left/right text. The tokens carry no information beyond
    # what the hydration payload already shipped.
    matched_tokens = [
        {
            "lid": left_token(req.homework_id, idx),
            "rid": right_token(req.homework_id, idx),
        }
        for idx in sorted(state["matched_pair_ids"])
    ]

    # Persist attempt (best-effort side-effect — never breaks answer-checking).
    # Mirrors the CBP/MC persisting calls. `subphase` keys off the SERVER-DERIVED
    # canonical pair index (matched_key) — never the opaque client tokens. Only
    # when session_id is present (homework_id is already required above). The
    # `already_matched` no-op is still persisted as a 0/correct=False attempt so
    # the Reflection engine sees the full interaction stream.
    if req.session_id and req.homework_id:
        import json as _json
        try:
            from ..db.attempts_repo import add_phase_attempt as _add_phase_attempt
            await _add_phase_attempt(
                session_id=req.session_id,
                hw_id=req.homework_id,
                phase="tile-match",
                subphase=f"pair_{matched_key}",
                question_id=req.question_id or f"tile-match_{matched_key}",
                item_id=req.item_id,
                attempt_number=req.attempt_number or 1,
                answer_spec_json=_json.dumps({"type": "tile_match"}),
                checker_source="phase_adapter:tile-match",
                correct=1 if is_correct else 0,
                score=1.0 if is_correct else 0.0,
            )
        except Exception as _e:  # noqa: BLE001 — attempt persistence is best-effort
            _log.warning("TM: failed to persist attempt: %s", _e)

    return {
        "correct": is_correct,
        "already_matched": already_matched,
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
        "matched_tokens": matched_tokens,
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
        # Fence the student's free text — the server-only acceptable_keywords ride
        # in the same prompt, so the student value must be treated strictly as
        # data to grade, never as instructions.
        "student_text": _fence_untrusted(text or ""),
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
    # Defensive: strip any fence tags the model echoed back so a fenced copy of
    # the student's text can't surface in the returned feedback.
    feedback = _strip_fence_tags(str(ai_response.get("feedback") or ""))
    return (score, feedback)


def _score_reasoning_coverage(text: str, dpe: dict) -> int:
    """Deterministic keyword-coverage count for the CBP reasoning step.

    Counts how many of the three answer buckets — concept / method / mistake —
    the student's free text touches (case-insensitive substring presence of ANY
    keyword in the bucket). Returns ``det_count`` in ``0..3``.

    No expected text is ever returned — only the integer count. The keyword
    buckets stay server-only (they live on the DB row, stripped before
    hydration). An empty bucket cannot be "covered" — it contributes 0, so a
    homework that authored no keywords yields det_count==0 (the AI score then
    decides via the combine rule).
    """
    if not isinstance(dpe, dict):
        return 0
    haystack = (text or "").lower()
    if not haystack.strip():
        return 0
    count = 0
    for bucket in ("concept_keywords", "method_keywords", "mistake_keywords"):
        kws = dpe.get(bucket) or []
        if not isinstance(kws, list):
            continue
        for kw in kws:
            if isinstance(kw, str) and kw.strip() and kw.strip().lower() in haystack:
                count += 1
                break  # one hit per bucket is enough
    return count


async def _grade_cbp_reasoning(
    text: str,
    dpe: dict,
    case_setup: Any,
) -> tuple[int, str]:
    """Grade the CBP Decision-Process Explanation via the LLM. Returns (score 0-100, feedback).

    Cloned from ``_grade_rlc_reasoning`` — loads the `cbp-reasoning-checker`
    runtime prompt and calls the SAME ``ai_orchestrator.generate_json`` adapter
    used by ``tutor.check_answer``. Anchors the LLM on the dpe keyword buckets
    (server-only) + the case setup context. The min-char gate is enforced BEFORE
    this is called (cheap reject).

    The keyword buckets ride into the PROMPT INPUT only as grading anchors — the
    prompt instructs the LLM never to echo them — and never appear in the
    response body. Tests mock this function directly (RLC-style), so they never
    hit the live provider. On any AI unavailability we return a neutral score so
    the deterministic fallback in the caller can still decide pass/fail.
    """
    from ..services.tutor import _load_runtime_prompt

    prompt = _load_runtime_prompt("cbp-reasoning-checker")
    # Normalize case_setup to a compact string for the prompt context.
    if isinstance(case_setup, dict):
        case_setup_str = " ".join(
            str(case_setup.get(k) or "")
            for k in ("story", "role", "task")
        ).strip() or str(case_setup)
    else:
        case_setup_str = str(case_setup or "")

    payload = {
        "case_setup": case_setup_str,
        "prompt": dpe.get("prompt", "") if isinstance(dpe, dict) else "",
        # Fence the student's free text — the server-only keyword anchors ride in
        # the same prompt, so the student value must be treated strictly as data
        # to grade, never as instructions. (cbp-reasoning-checker.md already
        # carries the matching "treat as untrusted" rule.)
        "student_text": _fence_untrusted(text or ""),
        # Server-only anchors — never echoed back to client; prompt instructs
        # the LLM to use these as a check, not to quote them.
        "concept_keywords": (dpe.get("concept_keywords") or []) if isinstance(dpe, dict) else [],
        "method_keywords": (dpe.get("method_keywords") or []) if isinstance(dpe, dict) else [],
        "mistake_keywords": (dpe.get("mistake_keywords") or []) if isinstance(dpe, dict) else [],
        "acceptable_keywords": (dpe.get("acceptable_keywords") or []) if isinstance(dpe, dict) else [],
    }
    schema = {
        "score": "integer 0..100",
        "feedback": "1-2 sentence string in the case's language",
    }
    try:
        input_section = ai_orchestrator.build_input_section(payload)
        ai_response = await ai_orchestrator.generate_json(
            f"{prompt}\n\n{input_section}",
            schema_hint=schema,
            model=ai_orchestrator.FAST_MODEL,
        )
    except (ai_orchestrator.PromptTooLargeError, RuntimeError):
        # AI grading unavailable — neutral "needs human review" score; the caller
        # falls back to the deterministic keyword-coverage verdict.
        return (50, "AI baholash hozir mavjud emas — javobingiz keyinroq tekshiriladi.")

    raw_score = ai_response.get("score", 0)
    try:
        score = int(round(float(raw_score)))
    except (TypeError, ValueError):
        score = 0
    score = max(0, min(100, score))
    # Defensive: strip any fence tags the model echoed back so a fenced copy of
    # the student's text can't surface in the returned feedback.
    feedback = _strip_fence_tags(str(ai_response.get("feedback") or ""))
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

    # BLOCKER #3 — Practice Arc must be server-enforced before grading.
    # Real-Life Challenge is a practice-arc game; refuse to grade for a locked session.
    await _enforce_practice_unlocked(req)

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

    # Persist attempt (best-effort side-effect — never breaks answer-checking).
    # RLC is AMR-graded: for reasoning steps `reasoning_score` is 0-100 (AI), so
    # we normalize to a 0-1 `score`; for decision/concept steps score mirrors
    # `is_correct`. `subphase` is the step_id (server-validated above). No
    # misconception tags are computed by the RLC grader, so the field stays None.
    # Only when session_id is present (homework_id is already required above).
    if req.session_id and req.homework_id:
        import json as _json
        if reasoning_score is not None:
            _persist_score = max(0.0, min(1.0, float(reasoning_score) / 100.0))
        else:
            _persist_score = 1.0 if is_correct else 0.0
        _student_answer = (
            req.reasoning_text
            if kind == "reasoning"
            else (req.selected_option_id or req.selected_chip_id)
        )
        try:
            from ..db.attempts_repo import add_phase_attempt as _add_phase_attempt
            await _add_phase_attempt(
                session_id=req.session_id,
                hw_id=req.homework_id,
                phase="real-life-challenge",
                subphase=req.step_id,
                question_id=req.question_id or req.step_id,
                item_id=req.item_id,
                step_id=req.step_id,
                attempt_number=req.attempt_number or 1,
                student_answer=str(_student_answer) if _student_answer is not None else None,
                answer_spec_json=_json.dumps({"type": "rlc", "kind": kind}),
                checker_source="phase_adapter:real-life-challenge",
                correct=1 if is_correct else 0,
                score=_persist_score,
                feedback=reasoning_feedback,
            )
        except Exception as _e:  # noqa: BLE001 — attempt persistence is best-effort
            _log.warning("RLC: failed to persist attempt: %s", _e)

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


# One-time deprecation flag for the legacy boss HP/outcome path. The v2 boss
# (POST /ai/boss/*) is server-authoritative on HP; the legacy turn path only
# mirrors a client-reported HP cursor, which a tampered client could inflate.
# We keep the endpoint working (the v1 template still calls it) but no longer
# let client HP push stars/XP beyond what the boss's own max_hp allows.
_LEGACY_BOSS_HP_WARNED = False


def _legacy_boss_hp_warn_once() -> None:
    """Log the legacy-path deprecation warning at most once per process."""
    global _LEGACY_BOSS_HP_WARNED
    if not _LEGACY_BOSS_HP_WARNED:
        _LEGACY_BOSS_HP_WARNED = True
        _log.warning("legacy boss-turn path is deprecated; v2 uses /ai/boss/*")


def _safe_outcome_hp(client_hp: Optional[int], max_hp: int) -> int:
    """Clamp a client-reported HP cursor into ``[0, max_hp]`` for outcome math.

    Conservative anti-inflation guard (Gap C): the legacy path can only TRUST a
    client HP value up to the boss's own maximum. A forged ``hp_remaining`` above
    ``max_hp`` (or below 0) can no longer inflate the star/XP outcome. This does
    NOT make HP server-authoritative — that's the v2 boss's job — it just stops
    the legacy path's outcome from being driven past its server-known ceiling.
    """
    try:
        hp = int(client_hp or 0)
    except (TypeError, ValueError):
        hp = 0
    ceiling = max(1, int(max_hp or 1))
    return max(0, min(hp, ceiling))


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

    # BLOCKER #3 — Final Boss is a practice-arc game; refuse to grade for a
    # session that has not unlocked the arc (server-side enforcement).
    await _enforce_practice_unlocked(req)

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
        # Gap C: legacy path — do not trust client HP beyond the boss ceiling.
        _legacy_boss_hp_warn_once()
        outcome, stars, outcome_xp = _boss_outcome_for(
            hp_remaining=_safe_outcome_hp(req.hp_remaining, int(max_hp)),
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

    # Persist attempt (best-effort side-effect — never breaks answer-checking).
    # THIS is the path the v2 React `bossTurn()` hits (POST /api/ai/check-answer
    # phase="final-boss"). `score` comes from tutor.boss_turn's 0-1 AMR score;
    # `correct` mirrors the grader verdict. `tutor.boss_turn` does NOT emit
    # misconception tags, so that field stays None. `time_ms` is unavailable —
    # CheckAnswerRequest carries no timing field. `subphase` is the boss
    # question id (server-validated above) or the attempt cursor when the caller
    # submits via the legacy free-form `question` slot. Only when session_id is
    # present (homework_id is already required above).
    if req.session_id and req.homework_id:
        import json as _json
        try:
            _fb_score = boss_response.get("score")
            _fb_score = float(_fb_score) if isinstance(_fb_score, (int, float)) else (
                1.0 if is_correct else 0.0
            )
            from ..db.attempts_repo import add_phase_attempt as _add_phase_attempt
            await _add_phase_attempt(
                session_id=req.session_id,
                hw_id=req.homework_id,
                phase="final-boss",
                subphase=req.question_id or f"attempt_{attempt_number}",
                question_id=req.question_id,
                item_id=req.item_id,
                attempt_number=attempt_number,
                student_answer=str(req.student_answer or ""),
                answer_spec_json=_json.dumps({"type": "boss_amr"}),
                checker_source="phase_adapter:final-boss",
                correct=1 if is_correct else 0,
                score=_fb_score,
                misconception_tags_json=None,
            )
        except Exception as _e:  # noqa: BLE001 — attempt persistence is best-effort
            _log.warning("FB: failed to persist attempt: %s", _e)

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

    # BLOCKER #3 — Practice Arc must be server-enforced before grading.
    # Tic Tac Toe is a practice-arc game; refuse to grade for a locked session.
    await _enforce_practice_unlocked(req)

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
    if not answer_key:
        # React-served (v2) homeworks never pass through the legacy injector
        # render that populates _TTT_ANSWER_KEY, so resolve the key directly
        # from content_json with the same serializer (identical id logic).
        content = hw.get("content_json") or {}
        if content.get("gb_ttt"):
            _wire, answer_key = injector._serialize_ttt(
                content.get("gb_ttt"), content.get("gb_ttt_config") or {}
            )
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

    # Persist attempt (best-effort side-effect — never breaks answer-checking).
    # `subphase` keys off the item_id (server-resolved against the answer key
    # above). `score` mirrors `is_correct`. Only when session_id is present
    # (homework_id is already required above).
    if req.session_id and req.homework_id:
        import json as _json
        try:
            from ..db.attempts_repo import add_phase_attempt as _add_phase_attempt
            await _add_phase_attempt(
                session_id=req.session_id,
                hw_id=req.homework_id,
                phase="ttt",
                subphase=f"pick_{item_id}",
                question_id=req.question_id or item_id,
                item_id=item_id,
                attempt_number=req.attempt_number or 1,
                student_answer=str(picked_norm),
                answer_spec_json=_json.dumps({"type": "ttt"}),
                checker_source="phase_adapter:ttt",
                correct=1 if is_correct else 0,
                score=1.0 if is_correct else 0.0,
            )
        except Exception as _e:  # noqa: BLE001 — attempt persistence is best-effort
            _log.warning("TTT: failed to persist attempt: %s", _e)

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

    # BLOCKER #3 — Practice Arc must be server-enforced before grading.
    # Tic Tac Toe (session tally) is a practice-arc game; refuse for a locked session.
    await _enforce_practice_unlocked(req)

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

    # Persist attempt (best-effort side-effect — never breaks answer-checking).
    # This is the end-of-session TALLY (one row per completed session). `score`
    # is the draw+win mastery ratio (0-1); `correct` is 1 unless the student
    # earned zero non-loss outcomes (duolingo_remediation). `subphase` is the
    # fixed "tally" marker. Only when session_id is present (homework_id is
    # already required above).
    if req.session_id and req.homework_id:
        import json as _json
        _ratio = ((wins + draws) / total_games) if total_games else 0.0
        try:
            from ..db.attempts_repo import add_phase_attempt as _add_phase_attempt
            await _add_phase_attempt(
                session_id=req.session_id,
                hw_id=req.homework_id,
                phase="ttt-session",
                subphase="tally",
                question_id=req.question_id,
                item_id=req.item_id,
                attempt_number=req.attempt_number or 1,
                answer_spec_json=_json.dumps({"type": "ttt_session"}),
                checker_source="phase_adapter:ttt-session",
                correct=0 if duolingo_remediation else 1,
                score=_ratio,
                feedback=mastery_tier,
            )
        except Exception as _e:  # noqa: BLE001 — attempt persistence is best-effort
            _log.warning("TTT-session: failed to persist attempt: %s", _e)

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

    # BLOCKER #3 — Practice Arc must be server-enforced before grading.
    # Memory Palace is a practice-arc game; refuse to grade for a locked session.
    await _enforce_practice_unlocked(req)

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

    # Persist attempt rows (best-effort side-effect — never breaks grading).
    # Memory Palace grades the whole recall set in one POST; persist one row per
    # recall location so the Reflection engine sees per-item memory-palace
    # performance like every other Practice-Arc game (it was previously the only
    # graded game writing NOTHING, so Reflection was blind to it). Only when
    # session_id is present (homework_id is already required above).
    if req.session_id and req.homework_id:
        import json as _json
        for rr in recomputed:
            try:
                from ..db.attempts_repo import add_phase_attempt as _add_phase_attempt
                await _add_phase_attempt(
                    session_id=req.session_id,
                    hw_id=req.homework_id,
                    phase="memory-palace",
                    subphase=f"loc_{rr['location_idx']}",
                    question_id=f"memory-palace_{req.palace_key}_{rr['location_idx']}",
                    attempt_number=req.attempt_number or 1,
                    answer_spec_json=_json.dumps({"type": "memory_palace"}),
                    checker_source="phase_adapter:memory-palace",
                    correct=1 if rr["is_correct"] else 0,
                    score=1.0 if rr["is_correct"] else 0.0,
                    time_ms=int(rr.get("elapsed_ms") or 0),
                )
            except Exception as _e:  # noqa: BLE001 — attempt persistence is best-effort
                _log.warning("MP: failed to persist attempt: %s", _e)

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


async def _check_answer_case_based_preview(req: CheckAnswerRequest) -> dict:
    """Per-checkpoint grading branch for Case-Based Preview (v2 React runtime).

    No-leak invariants:
      - `answer_spec.expected` / `accepted_answers` from content_json are NEVER
        included in the response, even on a wrong answer.
      - `learning_block` (the teaching text) IS returned after submit — this is
        the "feedback from response" pattern, not hydration.
      - On wrong answer, a generic hint is returned, never the expected value.
    """
    if not req.homework_id:
        raise HTTPException(400, detail={
            "error": "homework_id required for phase=case_based_preview",
            "code": "CBP_MISSING_HW",
        })
    if req.item_index is None:
        raise HTTPException(400, detail={
            "error": "item_index required for phase=case_based_preview",
            "code": "CBP_MISSING_ITEM_INDEX",
        })

    hw = await db.get_homework(req.homework_id)
    if hw is None:
        raise HTTPException(404, detail={
            "error": f"homework {req.homework_id} not found",
            "code": "HW_NOT_FOUND",
        })

    content = hw.get("content_json") or {}
    cbp = content.get("case_based_preview")
    if not isinstance(cbp, dict):
        raise HTTPException(404, detail={
            "error": "case_based_preview content not found on this homework",
            "code": "CBP_NO_CONTENT",
        })

    checkpoints = cbp.get("checkpoints") or []
    idx = req.item_index
    if not isinstance(idx, int) or idx < 0 or idx >= len(checkpoints):
        raise HTTPException(400, detail={
            "error": (
                f"item_index {idx} out of range — "
                f"case_based_preview has {len(checkpoints)} checkpoint(s)"
            ),
            "code": "CBP_BAD_INDEX",
        })

    checkpoint = checkpoints[idx]
    if not isinstance(checkpoint, dict):
        raise HTTPException(400, detail={
            "error": f"checkpoint at index {idx} is malformed",
            "code": "CBP_BAD_CHECKPOINT",
        })

    answer_spec = checkpoint.get("answer_spec") or {}
    learning_block: Optional[str] = checkpoint.get("learning_block")
    question_id = req.question_id or f"cbp_{idx}"

    # Grade deterministically using the shared checker.
    from ..services import answer_checker as _answer_checker
    det = _answer_checker.check(answer_spec, req.student_answer or "")
    verdict = det.get("verdict", "incorrect")
    is_correct = verdict == "correct"

    # Build feedback — never include the expected value on wrong answer.
    if is_correct:
        feedback = det.get("format_tip") or "To'g'ri!"
    else:
        # Provide a pedagogical hint without leaking the expected answer.
        feedback = "Qayta urinib ko'ring." if verdict == "unsure" else "Noto'g'ri javob."

    # Persist attempt.
    import json as _json
    session_id = req.session_id or "default"
    try:
        from ..db.attempts_repo import add_phase_attempt as _add_phase_attempt
        await _add_phase_attempt(
            session_id=session_id,
            hw_id=req.homework_id,
            phase="case_based_preview",
            subphase=f"checkpoint_{idx}",
            question_id=question_id,
            item_id=req.item_id,
            attempt_number=req.attempt_number or 1,
            student_answer=str(req.student_answer or ""),
            answer_spec_json=_json.dumps(answer_spec),
            checker_source="phase_adapter:case_based_preview",
            correct=1 if is_correct else 0,
            score=1.0 if is_correct else 0.0,
            feedback=feedback,
        )
    except Exception as _e:  # noqa: BLE001 — attempt persistence is best-effort
        _log.warning("CBP: failed to persist attempt: %s", _e)

    result: dict[str, Any] = {
        "correct": is_correct,
        "feedback": feedback,
    }
    if learning_block is not None:
        result["learning_block"] = learning_block
    return result


async def _check_answer_cbp_reasoning(req: CheckAnswerRequest) -> dict:
    """Open-ended, AI-graded "Decision Process Explanation" branch for CBP.

    Contract (must match the frontend exactly):
      request  POST /api/ai/check-answer
               { homework_id, session_id, phase: "case_based_preview_reasoning",
                 reasoning_text }
      response { passed: bool, score: number(0..100), feedback: str }

    Grading combines a deterministic keyword-coverage count (concept / method /
    mistake buckets → det_count 0..3) with the AI judgment:

        score  = round(0.6 * ai_score + 0.4 * 100 * det_count / 3)
        passed = score >= pass_score(default 60) AND det_count >= 2

    On AI error the AI grader returns a neutral 50, but to avoid a soft
    AI-down pass we fall back to a purely deterministic verdict:
        passed = det_count >= 2.

    No-leak invariants: the response NEVER includes the keyword buckets, the
    rubric, the pass_score, or any expected text — only {passed, score, feedback}.
    """
    if not req.homework_id:
        raise HTTPException(400, detail={
            "error": "homework_id required for phase=case_based_preview_reasoning",
            "code": "CBP_MISSING_HW",
        })

    hw = await db.get_homework(req.homework_id)
    if hw is None:
        raise HTTPException(404, detail={
            "error": f"homework {req.homework_id} not found",
            "code": "HW_NOT_FOUND",
        })

    content = hw.get("content_json") or {}
    cbp = content.get("case_based_preview")
    if not isinstance(cbp, dict):
        raise HTTPException(404, detail={
            "error": "case_based_preview content not found on this homework",
            "code": "CBP_NO_CONTENT",
        })

    dpe = cbp.get("decision_process_explanation")
    if not isinstance(dpe, dict):
        raise HTTPException(404, detail={
            "error": "no decision_process_explanation authored on this case_based_preview",
            "code": "CBP_NO_REASONING",
        })

    text = (req.reasoning_text or "").strip()
    min_chars = int(dpe.get("min_chars") or 80)
    if len(text) < min_chars:
        raise HTTPException(400, detail={
            "error": (
                f"reasoning_text below min_chars={min_chars} "
                f"(got {len(text)} chars)"
            ),
            "code": "CBP_REASONING_TOO_SHORT",
            "min_chars": min_chars,
        })

    # Deterministic keyword coverage (no expected text returned).
    det_count = _score_reasoning_coverage(text, dpe)

    pass_score = int(dpe.get("pass_score") or 60)
    case_setup = cbp.get("case_setup")

    # AI judgment — clone of the RLC reasoning grader path.
    ai_unavailable = False
    try:
        ai_score, feedback = await _grade_cbp_reasoning(text, dpe, case_setup)
    except Exception as _e:  # noqa: BLE001 — never 500 on grader failure
        _log.warning("CBP reasoning: AI grader raised, falling back: %s", _e)
        ai_unavailable = True
        ai_score, feedback = 50, "AI baholash hozir mavjud emas — javobingiz keyinroq tekshiriladi."

    score = int(round(0.6 * ai_score + 0.4 * 100 * det_count / 3))
    score = max(0, min(100, score))

    if ai_unavailable:
        # Pure deterministic fallback — don't let a neutral AI score gate.
        passed = det_count >= 2
    else:
        passed = score >= pass_score and det_count >= 2

    # Persist the attempt under the CBP phase, subphase="reasoning".
    session_id = req.session_id or "default"
    try:
        from ..db.attempts_repo import add_phase_attempt as _add_phase_attempt
        await _add_phase_attempt(
            session_id=session_id,
            hw_id=req.homework_id,
            phase="case_based_preview",
            subphase="reasoning",
            question_id=req.question_id or "cbp_reasoning",
            item_id=req.item_id,
            attempt_number=req.attempt_number or 1,
            student_answer=text,
            checker_source="phase_adapter:case_based_preview_reasoning",
            correct=1 if passed else 0,
            score=score / 100,
            feedback=feedback,
        )
    except Exception as _e:  # noqa: BLE001 — attempt persistence is best-effort
        _log.warning("CBP reasoning: failed to persist attempt: %s", _e)

    # Response carries ONLY the contract fields — no keywords / rubric / expected.
    return {
        "passed": bool(passed),
        "score": int(score),
        "feedback": str(feedback),
    }


async def _check_answer_memory_check(req: CheckAnswerRequest) -> dict:
    """Per-item grading branch for Memory Check (v2 React runtime).

    No-leak invariants:
      - `answer_spec.expected` / `accepted_answers` from content_json are NEVER
        included in the response body.
      - On wrong answer, generic feedback is returned without revealing the
        expected value.
    """
    if not req.homework_id:
        raise HTTPException(400, detail={
            "error": "homework_id required for phase=memory_check",
            "code": "MC_MISSING_HW",
        })
    if req.item_index is None:
        raise HTTPException(400, detail={
            "error": "item_index required for phase=memory_check",
            "code": "MC_MISSING_ITEM_INDEX",
        })

    hw = await db.get_homework(req.homework_id)
    if hw is None:
        raise HTTPException(404, detail={
            "error": f"homework {req.homework_id} not found",
            "code": "HW_NOT_FOUND",
        })

    content = hw.get("content_json") or {}
    mc = content.get("memory_check")
    if not isinstance(mc, dict):
        raise HTTPException(404, detail={
            "error": "memory_check content not found on this homework",
            "code": "MC_NO_CONTENT",
        })

    items = mc.get("items") or []
    idx = req.item_index
    if not isinstance(idx, int) or idx < 0 or idx >= len(items):
        raise HTTPException(400, detail={
            "error": (
                f"item_index {idx} out of range — "
                f"memory_check has {len(items)} item(s)"
            ),
            "code": "MC_BAD_INDEX",
        })

    item = items[idx]
    if not isinstance(item, dict):
        raise HTTPException(400, detail={
            "error": f"item at index {idx} is malformed",
            "code": "MC_BAD_ITEM",
        })

    answer_spec = item.get("answer_spec") or {}
    question_id = req.question_id or f"mc_{idx}"

    # Grade deterministically using the shared checker.
    from ..services import answer_checker as _answer_checker
    det = _answer_checker.check(answer_spec, req.student_answer or "")
    verdict = det.get("verdict", "incorrect")
    is_correct = verdict == "correct"

    # Build feedback — never include the expected value.
    if is_correct:
        feedback = det.get("format_tip") or "To'g'ri!"
    else:
        feedback = "Qayta urinib ko'ring." if verdict == "unsure" else "Noto'g'ri javob."

    # Persist attempt.
    import json as _json
    session_id = req.session_id or "default"
    try:
        from ..db.attempts_repo import add_phase_attempt as _add_phase_attempt
        await _add_phase_attempt(
            session_id=session_id,
            hw_id=req.homework_id,
            phase="memory_check",
            subphase=f"item_{idx}",
            question_id=question_id,
            item_id=req.item_id,
            attempt_number=req.attempt_number or 1,
            student_answer=str(req.student_answer or ""),
            answer_spec_json=_json.dumps(answer_spec),
            checker_source="phase_adapter:memory_check",
            correct=1 if is_correct else 0,
            score=1.0 if is_correct else 0.0,
            feedback=feedback,
        )
    except Exception as _e:  # noqa: BLE001 — attempt persistence is best-effort
        _log.warning("MC: failed to persist attempt: %s", _e)

    return {
        "correct": is_correct,
        "feedback": feedback,
    }


# ---------------------------------------------------------------------------
# Phase 2B games — Adaptive Quiz / Mystery Box / Puzzle Lock check-answer
# branches (v2 React runtime). All three follow the Case-Based Preview
# template: resolve the item by `item_index` from a content_json array, grade
# via the shared deterministic checker, strip the expected value from the
# response, persist a server-derived `subphase`, and return the minimal
# {correct, feedback} contract.
# ---------------------------------------------------------------------------

# Wrong-answer feedback never echoes the expected value (no-leak invariant).
_2B_WRONG_FEEDBACK = "Noto'g'ri javob."
_2B_RETRY_FEEDBACK = "Qayta urinib ko'ring."


def _grade_with_accepted_list(accepted: list[str], student_answer: str) -> tuple[bool, str]:
    """Grade a student answer against an accepted-answer LIST via text_fuzzy.

    The shared answer_checker has no native accepted-list type, so we run one
    `text_fuzzy` check per accepted string and treat the answer as correct if
    ANY matches. Returns ``(is_correct, verdict_of_best)``. The expected values
    are NEVER returned to the caller — only the boolean + verdict label.
    """
    from ..services import answer_checker as _answer_checker

    best_verdict = "incorrect"
    for candidate in accepted:
        det = _answer_checker.check(
            {"type": "text_fuzzy", "expected": str(candidate)}, student_answer
        )
        verdict = det.get("verdict", "incorrect")
        if verdict == "correct":
            return True, "correct"
        if verdict == "unsure":
            best_verdict = "unsure"
    return False, best_verdict


async def _check_answer_phase2b_item(
    req: CheckAnswerRequest,
    *,
    phase: str,
    array_key: str,
    no_content_code: str,
    bad_index_code: str,
    answer_str_fields: tuple[str, ...],
) -> dict:
    """Shared resolver body for the three Phase-2B games.

    Mirrors `_check_answer_case_based_preview` exactly:
      - 400 if no homework_id / item_index None.
      - 404 if homework / array missing.
      - 400 if item_index out of range.
      - `_enforce_practice_unlocked(req)` BEFORE grading (these ARE practice-arc
        games, unlike CBP/MC which are the unlock path).
      - Resolve the item, build / read an answer_spec, grade via the shared
        deterministic checker, and NEVER return the expected value.
    """
    if not req.homework_id:
        raise HTTPException(400, detail={
            "error": f"homework_id required for phase={phase}",
            "code": "HW_REQUIRED",
        })
    if req.item_index is None:
        raise HTTPException(400, detail={
            "error": f"item_index required for phase={phase}",
            "code": "MISSING_ITEM_INDEX",
        })

    # BLOCKER #3 — Practice Arc must be server-enforced before grading.
    await _enforce_practice_unlocked(req)

    hw = await db.get_homework(req.homework_id)
    if hw is None:
        raise HTTPException(404, detail={
            "error": f"homework {req.homework_id} not found",
            "code": "HW_NOT_FOUND",
        })

    content = hw.get("content_json") or {}
    array = content.get(array_key)
    if not isinstance(array, list) or not array:
        raise HTTPException(404, detail={
            "error": f"{array_key} content not found on this homework",
            "code": no_content_code,
        })

    idx = req.item_index
    if not isinstance(idx, int) or isinstance(idx, bool) or idx < 0 or idx >= len(array):
        raise HTTPException(400, detail={
            "error": (
                f"item_index {idx} out of range — "
                f"{array_key} has {len(array)} item(s)"
            ),
            "code": bad_index_code,
        })

    item = array[idx]
    if not isinstance(item, dict):
        raise HTTPException(400, detail={
            "error": f"item at index {idx} is malformed",
            "code": bad_index_code,
        })

    # Resolve the grading rule. Priority: an authored `answer_spec`, else build
    # a text_fuzzy spec on the fly from the game's answer field(s). For
    # adaptive-quiz, an `accepted_answers`/`ans` LIST is supported via the
    # any-match accepted-list helper.
    from ..services import answer_checker as _answer_checker

    answer_spec = item.get("answer_spec")
    student_answer = req.student_answer or ""

    if isinstance(answer_spec, dict) and answer_spec:
        det = _answer_checker.check(answer_spec, student_answer)
        verdict = det.get("verdict", "incorrect")
        is_correct = verdict == "correct"
        format_tip = det.get("format_tip")
        spec_for_persist = answer_spec
    else:
        # Build an accepted list from the game-specific answer fields. The first
        # populated string field (or accepted_answers/ans list) wins.
        accepted: list[str] = []
        raw_accepted = item.get("accepted_answers") or item.get("ans")
        if isinstance(raw_accepted, list):
            accepted = [str(x) for x in raw_accepted if x is not None and str(x) != ""]
        elif isinstance(raw_accepted, str) and raw_accepted:
            accepted = [raw_accepted]
        if not accepted:
            for field in answer_str_fields:
                val = item.get(field)
                if isinstance(val, str) and val:
                    accepted = [val]
                    break
        is_correct, verdict = _grade_with_accepted_list(accepted, student_answer)
        format_tip = None
        # Persist a sanitized spec marker (no expected value) — the real value
        # never leaves the server. We store an opaque type tag for audit only.
        spec_for_persist = {"type": "text_fuzzy"}

    # Feedback — never include the expected value, even on a wrong answer.
    if is_correct:
        feedback = format_tip or "To'g'ri!"
    else:
        feedback = _2B_RETRY_FEEDBACK if verdict == "unsure" else _2B_WRONG_FEEDBACK

    # Persist attempt with a SERVER-DERIVED subphase (range-validated index).
    import json as _json
    session_id = req.session_id or "default"
    question_id = req.question_id or f"{phase}_{idx}"
    try:
        from ..db.attempts_repo import add_phase_attempt as _add_phase_attempt
        await _add_phase_attempt(
            session_id=session_id,
            hw_id=req.homework_id,
            phase=phase,
            subphase=f"item_{idx}",
            question_id=question_id,
            item_id=req.item_id,
            attempt_number=req.attempt_number or 1,
            student_answer=str(student_answer),
            answer_spec_json=_json.dumps(spec_for_persist),
            checker_source=f"phase_adapter:{phase}",
            correct=1 if is_correct else 0,
            score=1.0 if is_correct else 0.0,
            feedback=feedback,
        )
    except Exception as _e:  # noqa: BLE001 — attempt persistence is best-effort
        _log.warning("%s: failed to persist attempt: %s", phase, _e)

    return {
        "correct": is_correct,
        "feedback": feedback,
    }


async def _check_answer_adaptive_quiz(req: CheckAnswerRequest) -> dict:
    """Per-item grading for Adaptive Quiz (phase=adaptive-quiz, v2 runtime).

    Array: ``gb_adaptive_quiz``. Each item carries either an authored
    ``answer_spec`` (used directly) or an ``accepted_answers``/``ans`` list
    graded any-match via text_fuzzy. The expected value is NEVER returned.
    """
    return await _check_answer_phase2b_item(
        req,
        phase="adaptive-quiz",
        array_key="gb_adaptive_quiz",
        no_content_code="AQ_NO_CONTENT",
        bad_index_code="AQ_BAD_INDEX",
        answer_str_fields=("a", "answer"),
    )


async def _check_answer_mystery_box(req: CheckAnswerRequest) -> dict:
    """Per-item grading for Mystery Box (phase=mystery-box, v2 runtime).

    Array: ``gb_mystery_box``. The accepted answer rides on ``a`` (string).
    An on-the-fly ``{type: text_fuzzy}`` spec is built when no authored
    ``answer_spec`` is present. The expected value is NEVER returned.
    """
    return await _check_answer_phase2b_item(
        req,
        phase="mystery-box",
        array_key="gb_mystery_box",
        no_content_code="MB_NO_CONTENT",
        bad_index_code="MB_BAD_INDEX",
        answer_str_fields=("a", "answer"),
    )


async def _check_answer_puzzle_lock(req: CheckAnswerRequest) -> dict:
    """Per-item grading for Puzzle Lock (phase=puzzle-lock, v2 runtime).

    Array: ``gb_puzzle_lock``. The accepted answer rides on ``a`` or
    ``answer`` (string). An on-the-fly ``{type: text_fuzzy}`` spec is built
    when no authored ``answer_spec`` is present. The expected value is
    NEVER returned.
    """
    return await _check_answer_phase2b_item(
        req,
        phase="puzzle-lock",
        array_key="gb_puzzle_lock",
        no_content_code="PL_NO_CONTENT",
        bad_index_code="PL_BAD_INDEX",
        answer_str_fields=("a", "answer"),
    )


# ===========================================================================
# Division-3 Practices — 8 per-phase grading handlers (per _DIV3_CONTRACT.md).
#
# Phases: error-detection, memory-matching, jigsaw-matching, assembly,
#         sentence-repair, ttt-grid, problem-trace, counterexample.
#
# Each handler:
#   1. validate ids (homework_id + item_id) → 400 on missing
#   2. await _enforce_practice_unlocked(req)   (these ARE practice-arc games)
#   3. fetch hw → find item by item_id in content_json.<field>
#   4. grade per contract (MCQ deterministic; assembly order; error-detection
#      spot=is_broken block; DPE/open-ended = the LOCKED pending_ai seam)
#   5. _add_phase_attempt(subphase=...) — best-effort persistence
#   6. student-safe return — NEVER any ⛔ server-only field.
#
# The LOCKED DPE seam shape (do not change):
#   {correct:false, passed:null, score:null, pending_ai:true, feedback:<uz>}
# ===========================================================================

# Locked open-ended seam feedback string (contract §"Response contract").
_DPE_SEAM_FEEDBACK = "Javobingiz AI tomonidan baholanadi — natija tez orada."

# Reusable student-facing feedback (no expected value ever leaked).
_DIV3_CORRECT_FB = "To'g'ri!"
_DIV3_WRONG_FB = "Noto'g'ri javob."

# Error Detection result tiers (contract §"Game complete").
_ED_TIERS = ("Sharp Eye", "Good Detective", "Half-Found", "Hali emas")


def _div3_find_item(content_json: dict, field: str, item_id: str) -> Optional[dict]:
    """Locate a Division-3 practice item by id within content_json.<field>.

    `<field>` is a top-level list (gb_error_detection, gb_sentence_repair, ...).
    Returns the matching dict or None.
    """
    if not isinstance(content_json, dict):
        return None
    items = content_json.get(field)
    if not isinstance(items, list):
        return None
    for item in items:
        if isinstance(item, dict) and item.get("id") == item_id:
            return item
    return None


async def _div3_load_item(req: "CheckAnswerRequest", phase: str, field: str) -> dict:
    """Shared preamble for every Division-3 handler.

    Validates ids → enforces the practice gate → fetches the homework →
    resolves the item. Returns the item dict; raises HTTPException on any
    failure (400 / 403 / 404). The gate runs AFTER id presence but BEFORE
    content resolution, mirroring the existing practice-arc handlers so the
    locked-session tests fire on a bare homework.
    """
    if not req.homework_id or not req.item_id:
        raise HTTPException(400, detail={
            "error": f"homework_id and item_id required for phase={phase}",
            "code": "DIV3_MISSING_IDS",
        })

    # BLOCKER #3 — Practice Arc must be server-enforced before grading.
    await _enforce_practice_unlocked(req)

    hw = await db.get_homework(req.homework_id)
    if hw is None:
        raise HTTPException(404, detail={
            "error": f"homework {req.homework_id} not found",
            "code": "HW_NOT_FOUND",
        })
    content = hw.get("content_json") or {}
    item = _div3_find_item(content, field, req.item_id)
    if item is None:
        raise HTTPException(404, detail={
            "error": f"{phase} item {req.item_id!r} not found in {field}",
            "code": "DIV3_ITEM_NOT_FOUND",
        })
    return item


async def _div3_persist(
    req: "CheckAnswerRequest",
    *,
    phase: str,
    subphase: str,
    student_answer: str,
    correct: Optional[int],
    score: Optional[float],
    feedback: str,
    checker_source: Optional[str] = None,
) -> None:
    """Best-effort attempt persistence (mirrors the CBP/2B handlers)."""
    session_id = req.session_id or "default"
    try:
        from ..db.attempts_repo import add_phase_attempt as _add_phase_attempt
        await _add_phase_attempt(
            session_id=session_id,
            hw_id=req.homework_id,
            phase=phase,
            subphase=subphase,
            question_id=req.question_id or f"{phase}_{req.item_id}",
            item_id=req.item_id,
            attempt_number=req.attempt_number or 1,
            student_answer=student_answer,
            checker_source=checker_source or f"phase_adapter:{phase}",
            correct=correct,
            score=score,
            feedback=feedback,
        )
    except Exception as _e:  # noqa: BLE001 — attempt persistence is best-effort
        _log.warning("%s: failed to persist attempt: %s", phase, _e)


def _div3_dpe_seam() -> dict:
    """The LOCKED open-ended seam response (contract §"Response contract")."""
    return {
        "correct": False,
        "passed": None,
        "score": None,
        "pending_ai": True,
        "feedback": _DPE_SEAM_FEEDBACK,
    }


def _div3_mcq_checkpoint(checkpoint: Any) -> Optional[int]:
    """Read `correct_index` off an authored MCQ checkpoint dict.

    Returns the int index, or None when the checkpoint is malformed (no int
    `correct_index`). Never leaks the value to the client — only used to
    compute the boolean verdict server-side.
    """
    if not isinstance(checkpoint, dict):
        return None
    ci = checkpoint.get("correct_index")
    if isinstance(ci, bool) or not isinstance(ci, int):
        return None
    return ci


def _div3_grade_mcq(
    checkpoint: Any,
    selected_index: Optional[int],
    *,
    is_last: bool,
) -> dict:
    """Deterministic MCQ grade — compares selected_index == correct_index.

    Returns the contract MCQ response `{correct, feedback, advance}`. NEVER
    includes correct_index or any option text. `advance` is True when this was
    the last graded checkpoint before the DPE / next phase.
    """
    correct_index = _div3_mcq_checkpoint(checkpoint)
    if correct_index is None:
        raise HTTPException(400, detail={
            "error": "checkpoint is missing a valid correct_index",
            "code": "DIV3_BAD_CHECKPOINT",
        })
    if not isinstance(selected_index, int) or isinstance(selected_index, bool):
        raise HTTPException(400, detail={
            "error": "selected_index (int) required for an MCQ checkpoint",
            "code": "DIV3_MISSING_SELECTION",
        })
    is_correct = selected_index == correct_index
    return {
        "correct": is_correct,
        "feedback": _DIV3_CORRECT_FB if is_correct else _DIV3_WRONG_FB,
        "advance": bool(is_last),
    }


# ---------------------------------------------------------------------------
# error-detection — phase="error-detection"
# Stages: "spot" (block_id == is_broken block), "correction" (deterministic
# normalize vs correction_answer_spec, else seam), "why" (open-ended seam).
# ---------------------------------------------------------------------------

async def _check_answer_error_detection(req: CheckAnswerRequest) -> dict:
    item = await _div3_load_item(req, "error-detection", "gb_error_detection")
    stage = (req.stage or "spot").strip()

    if stage == "spot":
        if not req.block_id:
            raise HTTPException(400, detail={
                "error": "block_id required for stage=spot",
                "code": "ED_MISSING_BLOCK_ID",
            })
        blocks = item.get("work_blocks") or []
        broken_id = None
        valid_ids = set()
        for b in blocks:
            if not isinstance(b, dict):
                continue
            bid = b.get("id")
            valid_ids.add(bid)
            if b.get("is_broken"):
                broken_id = bid
        if req.block_id not in valid_ids:
            raise HTTPException(400, detail={
                "error": f"block_id {req.block_id!r} not found in work_blocks",
                "code": "ED_BAD_BLOCK_ID",
            })
        is_correct = req.block_id == broken_id
        await _div3_persist(
            req, phase="error-detection", subphase="spot",
            student_answer=str(req.block_id),
            correct=1 if is_correct else 0,
            score=1.0 if is_correct else 0.0,
            feedback=_DIV3_CORRECT_FB if is_correct else _DIV3_WRONG_FB,
        )
        return {
            "correct": is_correct,
            "feedback": _DIV3_CORRECT_FB if is_correct else _DIV3_WRONG_FB,
            # spotting the block is not the last graded step (correction follows).
            "advance": bool(is_correct),
        }

    if stage == "correction":
        student_correction = (req.correction or "").strip()
        spec = item.get("correction_answer_spec")
        # Deterministic-normalize path: only when the spec is a simple exact /
        # fuzzy text spec with an `expected`. Otherwise fall to the AI seam.
        det_verdict: Optional[bool] = None
        if isinstance(spec, dict):
            spec_type = str(spec.get("type") or "")
            if spec_type in ("text_exact", "text_fuzzy") and spec.get("expected") is not None:
                from ..services import answer_checker as _answer_checker
                det = _answer_checker.check(spec, student_correction)
                det_verdict = det.get("verdict") == "correct"
        if det_verdict is not None:
            await _div3_persist(
                req, phase="error-detection", subphase="correction",
                student_answer=student_correction,
                correct=1 if det_verdict else 0,
                score=1.0 if det_verdict else 0.0,
                feedback=_DIV3_CORRECT_FB if det_verdict else _DIV3_WRONG_FB,
            )
            return {
                "correct": det_verdict,
                "feedback": _DIV3_CORRECT_FB if det_verdict else _DIV3_WRONG_FB,
                "advance": bool(det_verdict),
            }
        # AI seam — persist as pending and return the locked seam shape.
        await _div3_persist(
            req, phase="error-detection", subphase="correction",
            student_answer=student_correction, correct=0, score=0.0,
            feedback=_DPE_SEAM_FEEDBACK,
        )
        return _div3_dpe_seam()

    if stage == "why":
        # Open-ended WHY explanation — always the AI seam.
        await _div3_persist(
            req, phase="error-detection", subphase="why",
            student_answer=(req.reasoning_text or "").strip(),
            correct=0, score=0.0, feedback=_DPE_SEAM_FEEDBACK,
        )
        return _div3_dpe_seam()

    raise HTTPException(400, detail={
        "error": f"unknown stage {stage!r} (expected spot|correction|why)",
        "code": "ED_BAD_STAGE",
    })


# ---------------------------------------------------------------------------
# Shared "MCQ checkpoints + DPE" handler — Memory Matching, Jigsaw Matching,
# Sentence Repair all share the exact shape: a `checkpoints` list of uniform
# MCQs (graded by checkpoint_index/selected_index) then an open-ended DPE
# (graded by the seam) signalled by reasoning_text / no checkpoint_index.
# ---------------------------------------------------------------------------

async def _check_answer_checkpoints_then_dpe(
    req: CheckAnswerRequest, *, phase: str, field: str,
) -> dict:
    item = await _div3_load_item(req, phase, field)
    checkpoints = item.get("checkpoints") or []

    # DPE branch: no checkpoint_index supplied → treat as the open-ended step.
    if req.checkpoint_index is None:
        await _div3_persist(
            req, phase=phase, subphase="dpe",
            student_answer=(req.reasoning_text or "").strip(),
            correct=0, score=0.0, feedback=_DPE_SEAM_FEEDBACK,
        )
        return _div3_dpe_seam()

    idx = req.checkpoint_index
    if isinstance(idx, bool) or not isinstance(idx, int) or idx < 0 or idx >= len(checkpoints):
        raise HTTPException(400, detail={
            "error": (
                f"checkpoint_index {idx} out of range — "
                f"{field} item has {len(checkpoints)} checkpoint(s)"
            ),
            "code": "DIV3_BAD_CHECKPOINT_INDEX",
        })

    is_last = idx == len(checkpoints) - 1
    result = _div3_grade_mcq(checkpoints[idx], req.selected_index, is_last=is_last)
    await _div3_persist(
        req, phase=phase, subphase=f"checkpoint_{idx}",
        student_answer=str(req.selected_index),
        correct=1 if result["correct"] else 0,
        score=1.0 if result["correct"] else 0.0,
        feedback=result["feedback"],
    )
    return result


async def _check_answer_memory_matching(req: CheckAnswerRequest) -> dict:
    return await _check_answer_checkpoints_then_dpe(
        req, phase="memory-matching", field="gb_memory_matching"
    )


async def _check_answer_jigsaw_matching(req: CheckAnswerRequest) -> dict:
    return await _check_answer_checkpoints_then_dpe(
        req, phase="jigsaw-matching", field="gb_jigsaw_matching"
    )


async def _check_answer_sentence_repair(req: CheckAnswerRequest) -> dict:
    return await _check_answer_checkpoints_then_dpe(
        req, phase="sentence-repair", field="gb_sentence_repair"
    )


# ---------------------------------------------------------------------------
# assembly — phase="assembly" — order == expected_order (deterministic).
# ---------------------------------------------------------------------------

async def _check_answer_assembly(req: CheckAnswerRequest) -> dict:
    item = await _div3_load_item(req, "assembly", "gb_assembly")
    if req.order is None or not isinstance(req.order, list):
        raise HTTPException(400, detail={
            "error": "order (list of piece ids) required for phase=assembly",
            "code": "ASM_MISSING_ORDER",
        })
    expected = item.get("expected_order") or []
    student_order = [str(x) for x in req.order]
    is_correct = student_order == [str(x) for x in expected]
    await _div3_persist(
        req, phase="assembly", subphase="order",
        student_answer=",".join(student_order),
        correct=1 if is_correct else 0,
        score=1.0 if is_correct else 0.0,
        feedback=_DIV3_CORRECT_FB if is_correct else _DIV3_WRONG_FB,
    )
    # Assembly is single-shot → completing the order completes the game.
    return {
        "correct": is_correct,
        "complete": True,
        "feedback": _DIV3_CORRECT_FB if is_correct else _DIV3_WRONG_FB,
    }


# ---------------------------------------------------------------------------
# ttt-grid — phase="ttt-grid"
# Two MCQs (concept_checkpoint -> checkpoint_index 0, justify_checkpoint -> 1)
# + a cell pick (cell_id == best_cell_id) + an open-ended DPE (seam).
# Dispatch precedence: checkpoint_index (an MCQ) → cell_id (the cell pick) →
# reasoning_text (the DPE seam). Matches the contract's request field names
# exactly (checkpoint_index / selected_index, cell_id, reasoning_text).
# ---------------------------------------------------------------------------

async def _check_answer_ttt_grid(req: CheckAnswerRequest) -> dict:
    item = await _div3_load_item(req, "ttt-grid", "gb_ttt_grid")

    # 1) MCQ checkpoints — concept (index 0) / justify (index 1).
    if req.checkpoint_index is not None:
        idx = req.checkpoint_index
        if idx == 0:
            checkpoint = item.get("concept_checkpoint")
            subphase = "concept"
        elif idx == 1:
            checkpoint = item.get("justify_checkpoint")
            subphase = "justify"
        else:
            raise HTTPException(400, detail={
                "error": "checkpoint_index for ttt-grid must be 0 (concept) or 1 (justify)",
                "code": "TTTG_BAD_CHECKPOINT_INDEX",
            })
        # justify (idx 1) is the last graded checkpoint before the DPE.
        result = _div3_grade_mcq(checkpoint, req.selected_index, is_last=(idx == 1))
        await _div3_persist(
            req, phase="ttt-grid", subphase=subphase,
            student_answer=str(req.selected_index),
            correct=1 if result["correct"] else 0,
            score=1.0 if result["correct"] else 0.0,
            feedback=result["feedback"],
        )
        return result

    # 2) Cell pick — cell_id == best_cell_id (deterministic).
    cell_id = req.cell_id
    if cell_id is not None:
        cells = item.get("cells") or []
        valid_ids = {c.get("id") for c in cells if isinstance(c, dict)}
        if cell_id not in valid_ids:
            raise HTTPException(400, detail={
                "error": f"cell_id {cell_id!r} not found in cells",
                "code": "TTTG_BAD_CELL_ID",
            })
        is_correct = cell_id == item.get("best_cell_id")
        # Post-decision feedback: echo the PICKED cell's meter deltas so the client
        # can animate the State Meters. This is the consequence of the student's own
        # choice (already made) — not a leak of which cell is best.
        picked = next((c for c in cells if isinstance(c, dict) and c.get("id") == cell_id), {})
        meter_deltas = picked.get("meter_deltas") or {}
        await _div3_persist(
            req, phase="ttt-grid", subphase="cell_pick",
            student_answer=str(cell_id),
            correct=1 if is_correct else 0,
            score=1.0 if is_correct else 0.0,
            feedback=_DIV3_CORRECT_FB if is_correct else _DIV3_WRONG_FB,
        )
        return {
            "correct": is_correct,
            "feedback": _DIV3_CORRECT_FB if is_correct else _DIV3_WRONG_FB,
            "advance": bool(is_correct),
            "meters_delta": meter_deltas,
        }

    # 3) DPE — open-ended seam.
    await _div3_persist(
        req, phase="ttt-grid", subphase="dpe",
        student_answer=(req.reasoning_text or "").strip(),
        correct=0, score=0.0, feedback=_DPE_SEAM_FEEDBACK,
    )
    return _div3_dpe_seam()


# ---------------------------------------------------------------------------
# problem-trace — phase="problem-trace"
# Per-step predict MCQ: step_index selects steps[step_index].predict; grade
# selected_index == predict.correct_index.
# ---------------------------------------------------------------------------

async def _check_answer_problem_trace(req: CheckAnswerRequest) -> dict:
    item = await _div3_load_item(req, "problem-trace", "gb_problem_trace")
    steps = item.get("steps") or []

    if req.step_index is None:
        raise HTTPException(400, detail={
            "error": "step_index required for phase=problem-trace",
            "code": "PT_MISSING_STEP_INDEX",
        })
    si = req.step_index
    if isinstance(si, bool) or not isinstance(si, int) or si < 0 or si >= len(steps):
        raise HTTPException(400, detail={
            "error": f"step_index {si} out of range — item has {len(steps)} step(s)",
            "code": "PT_BAD_STEP_INDEX",
        })
    step = steps[si]
    predict = step.get("predict") if isinstance(step, dict) else None
    is_last = si == len(steps) - 1
    result = _div3_grade_mcq(predict, req.selected_index, is_last=is_last)
    await _div3_persist(
        req, phase="problem-trace", subphase=f"step_{si}",
        student_answer=str(req.selected_index),
        correct=1 if result["correct"] else 0,
        score=1.0 if result["correct"] else 0.0,
        feedback=result["feedback"],
    )
    return result


# ---------------------------------------------------------------------------
# counterexample — phase="counterexample"
# Primary pick: selected_case_id == answer_case_id (deterministic).
# Optional explanation MCQ: checkpoint_index/selected_index against
# explanation_checkpoint. Optional DPE: reasoning_text → seam.
# ---------------------------------------------------------------------------

async def _check_answer_counterexample(req: CheckAnswerRequest) -> dict:
    item = await _div3_load_item(req, "counterexample", "gb_counterexample")

    # Optional explanation MCQ.
    if req.checkpoint_index is not None:
        checkpoint = item.get("explanation_checkpoint")
        if not isinstance(checkpoint, dict):
            raise HTTPException(400, detail={
                "error": "no explanation_checkpoint authored on this item",
                "code": "CE_NO_EXPLANATION",
            })
        result = _div3_grade_mcq(checkpoint, req.selected_index, is_last=True)
        await _div3_persist(
            req, phase="counterexample", subphase="explanation",
            student_answer=str(req.selected_index),
            correct=1 if result["correct"] else 0,
            score=1.0 if result["correct"] else 0.0,
            feedback=result["feedback"],
        )
        return result

    # Primary case pick.
    if req.selected_case_id is not None:
        cases = item.get("cases") or []
        valid_ids = {c.get("id") for c in cases if isinstance(c, dict)}
        if req.selected_case_id not in valid_ids:
            raise HTTPException(400, detail={
                "error": f"selected_case_id {req.selected_case_id!r} not found in cases",
                "code": "CE_BAD_CASE_ID",
            })
        is_correct = req.selected_case_id == item.get("answer_case_id")
        await _div3_persist(
            req, phase="counterexample", subphase="case_pick",
            student_answer=str(req.selected_case_id),
            correct=1 if is_correct else 0,
            score=1.0 if is_correct else 0.0,
            feedback=_DIV3_CORRECT_FB if is_correct else _DIV3_WRONG_FB,
        )
        # Whether more steps follow depends on authored content; advance on
        # correct so the client can move to the optional explanation / DPE.
        return {
            "correct": is_correct,
            "feedback": _DIV3_CORRECT_FB if is_correct else _DIV3_WRONG_FB,
            "advance": bool(is_correct),
        }

    # DPE — open-ended seam.
    await _div3_persist(
        req, phase="counterexample", subphase="dpe",
        student_answer=(req.reasoning_text or "").strip(),
        correct=0, score=0.0, feedback=_DPE_SEAM_FEEDBACK,
    )
    return _div3_dpe_seam()


# ---------------------------------------------------------------------------
# dependency-chain — phase="dependency-chain"
# TRANSFER / multi-step application. A scenario frames a problem; the student
# SOLVES a chain of linked MCQ steps. Each step grades selected_index ==
# steps[step_index].correct_index. On a CORRECT answer the server surfaces the
# step's `carry_label` (e.g. "x = 5 →") so the client can feed it into the next
# step's prompt — `carry_label` is server-only (redacted at hydration), so the
# only way the client gets it is by answering correctly. Distinct from
# problem-trace (which reveals a GIVEN worked solution; here the student solves).
# ---------------------------------------------------------------------------

async def _check_answer_dependency_chain(req: CheckAnswerRequest) -> dict:
    item = await _div3_load_item(req, "dependency-chain", "gb_dependency_chain")
    steps = item.get("steps") or []

    if req.step_index is None:
        raise HTTPException(400, detail={
            "error": "step_index required for phase=dependency-chain",
            "code": "DC_MISSING_STEP_INDEX",
        })
    si = req.step_index
    if isinstance(si, bool) or not isinstance(si, int) or si < 0 or si >= len(steps):
        raise HTTPException(400, detail={
            "error": f"step_index {si} out of range — item has {len(steps)} step(s)",
            "code": "DC_BAD_STEP_INDEX",
        })
    step = steps[si]
    is_last = si == len(steps) - 1
    # The step itself IS the MCQ checkpoint ({prompt|q|question, options, correct_index}).
    result = _div3_grade_mcq(step, req.selected_index, is_last=is_last)
    await _div3_persist(
        req, phase="dependency-chain", subphase=f"step_{si}",
        student_answer=str(req.selected_index),
        correct=1 if result["correct"] else 0,
        score=1.0 if result["correct"] else 0.0,
        feedback=result["feedback"],
    )
    # On a correct answer surface the carried result so it can feed the next
    # step. carry_label is server-only — never returned on a wrong answer.
    if result["correct"]:
        carry = step.get("carry_label")
        if isinstance(carry, str) and carry:
            result["carry"] = carry
    return result


# ---------------------------------------------------------------------------
# confidence-check — phase="confidence-check"
# Metacognition. The student answers a uniform MCQ AND rates confidence
# ("sure" | "maybe" | "guess"). The server grades the MCQ only
# (selected_index == correct_index); the calibration verdict (Mastered /
# Misconception / Solid / Lucky / Known-gap) is CLIENT-derived from
# {correct, confidence}. The single item IS the MCQ; advance is always true
# (one question per item). `confidence` is echoed back for symmetry but never
# changes the grade.
# ---------------------------------------------------------------------------

async def _check_answer_confidence_check(req: CheckAnswerRequest) -> dict:
    item = await _div3_load_item(req, "confidence-check", "gb_confidence_check")
    # The item itself is the MCQ ({question|q, options, correct_index}).
    result = _div3_grade_mcq(item, req.selected_index, is_last=True)
    confidence = (req.confidence or "").strip().lower() or None
    await _div3_persist(
        req, phase="confidence-check", subphase="answer",
        student_answer=str(req.selected_index),
        correct=1 if result["correct"] else 0,
        score=1.0 if result["correct"] else 0.0,
        feedback=result["feedback"],
    )
    # Echo confidence so the client can render its locally-derived calibration
    # verdict alongside the server's authoritative correctness.
    if confidence:
        result["confidence"] = confidence
    return result


# Module-level phase → handler map. The route dispatcher iterates this BEFORE
# the tutor fallback; tests reference it to drive each phase generically.
_DIV3_PHASE_HANDLERS = {
    "error-detection": _check_answer_error_detection,
    "memory-matching": _check_answer_memory_matching,
    "jigsaw-matching": _check_answer_jigsaw_matching,
    "assembly": _check_answer_assembly,
    "sentence-repair": _check_answer_sentence_repair,
    "ttt-grid": _check_answer_ttt_grid,
    "problem-trace": _check_answer_problem_trace,
    "counterexample": _check_answer_counterexample,
    "dependency-chain": _check_answer_dependency_chain,
    "confidence-check": _check_answer_confidence_check,
}


@router.post("/ai/runtime/submit-answer")
async def submit_runtime_answer(req: RuntimeAnswerSubmitRequest):
    from ..services.runtime_answer_resolver import resolve_runtime_answer

    if req.session_id:
        tutor._validate_session_id(req.session_id)

    # Soft-friction follow-up (anti-cheat wiring). A submit that carries a
    # `nudge_response` (in client_context, or via subphase=="integrity-nudge")
    # records an ADVISORY session event and is NEVER scored. Best-effort.
    nudge_response = None
    if isinstance(req.client_context, dict):
        nudge_response = req.client_context.get("nudge_response")
    if nudge_response is not None or req.subphase == "integrity-nudge":
        try:
            from ..db import session_events_repo

            await session_events_repo.add_session_event(
                session_id=req.session_id,
                hw_id=req.homework_id,
                event_type="integrity_nudge_response",
                payload={
                    "question_id": req.question_id,
                    "nudge_response": nudge_response,
                },
                phase=req.phase or None,
                subphase=req.subphase or None,
                question_id=req.question_id or None,
            )
        except Exception as _nudge_exc:
            _log.warning(
                "integrity_nudge_response session_event failed (non-fatal): %s",
                _nudge_exc,
            )

    try:
        target = await resolve_runtime_answer(req)
        result = await tutor.process_runtime_answer(
            target=target.model_dump(),
            student_answer=req.student_answer,
            attempt_number=req.attempt_number or 1,
            client_time_ms=req.client_time_ms,
            paste_detected=req.paste_detected,
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
    # C2 — Soft-friction follow-up. A submit carrying a `nudge_response` (or
    # marked subphase=="integrity-nudge") is the student's reply to a
    # strong-flag "explain in your own words" nudge. It is ADVISORY, never a
    # gradeable answer: record a session_events `integrity_nudge_response` event
    # and EARLY-RETURN `{"advisory": true}` BEFORE any grading dispatch below.
    # This must precede every phase branch so a nudge reply never falls through
    # to a real grader (and never produces a score).
    if req.nudge_response is not None or req.subphase == "integrity-nudge":
        try:
            from ..db import session_events_repo

            await session_events_repo.add_session_event(
                session_id=req.session_id or "default",
                hw_id=req.homework_id or "",
                event_type="integrity_nudge_response",
                payload={
                    "question_id": req.question_id or None,
                    "nudge_response": req.nudge_response,
                },
                phase=req.phase or None,
                subphase=req.subphase or None,
                question_id=req.question_id or None,
            )
        except Exception as _nudge_exc:  # never break on the advisory write
            _log.warning(
                "integrity_nudge_response session_event failed (non-fatal): %s",
                _nudge_exc,
            )
        return {"advisory": True}

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

    # Case-Based Preview open-ended reasoning branch (v2 React runtime). The
    # "Decision Process Explanation" step after the 3 MCQ checkpoints — graded
    # by deterministic keyword coverage + AI judgment. Distinct phase string so
    # it never collides with the MCQ checkpoint branch below. Same back-compat
    # gate (require homework_id).
    if req.phase == "case_based_preview_reasoning" and req.homework_id:
        try:
            result = await _check_answer_cbp_reasoning(req)
            result = await _attach_integrity(req, result)
            return _attach_check_answer_debug(
                req, result, checker_path="phase_adapter:case_based_preview_reasoning"
            )
        except HTTPException:
            raise
        except Exception as e:
            _handle_exc(e)

    # Case-Based Preview per-checkpoint grading branch (v2 React runtime).
    # Resolves the checkpoint's answer_spec from content_json server-side;
    # the client NEVER sends the expected answer value.
    if req.phase == "case_based_preview" and req.homework_id:
        try:
            result = await _check_answer_case_based_preview(req)
            result = await _attach_integrity(req, result)
            return _attach_check_answer_debug(
                req, result, checker_path="phase_adapter:case_based_preview"
            )
        except HTTPException:
            raise
        except Exception as e:
            _handle_exc(e)

    # Memory Check per-item grading branch (v2 React runtime).
    # Resolves the item's answer_spec from content_json server-side;
    # the client NEVER sends the expected answer value.
    if req.phase == "memory_check" and req.homework_id:
        try:
            result = await _check_answer_memory_check(req)
            result = await _attach_integrity(req, result)
            return _attach_check_answer_debug(
                req, result, checker_path="phase_adapter:memory_check"
            )
        except HTTPException:
            raise
        except Exception as e:
            _handle_exc(e)

    # Adaptive Quiz per-item grading branch (v2 React runtime, phase 2B).
    # Practice-arc game — server-gated; resolves answer_spec from content_json.
    if req.phase == "adaptive-quiz" and req.homework_id:
        try:
            result = await _check_answer_adaptive_quiz(req)
            result = await _attach_integrity(req, result)
            return _attach_check_answer_debug(
                req, result, checker_path="phase_adapter:adaptive-quiz"
            )
        except HTTPException:
            raise
        except Exception as e:
            _handle_exc(e)

    # Mystery Box per-item grading branch (v2 React runtime, phase 2B).
    # Practice-arc game — server-gated; resolves answer_spec from content_json.
    if req.phase == "mystery-box" and req.homework_id:
        try:
            result = await _check_answer_mystery_box(req)
            result = await _attach_integrity(req, result)
            return _attach_check_answer_debug(
                req, result, checker_path="phase_adapter:mystery-box"
            )
        except HTTPException:
            raise
        except Exception as e:
            _handle_exc(e)

    # Puzzle Lock per-item grading branch (v2 React runtime, phase 2B).
    # Practice-arc game — server-gated; resolves answer_spec from content_json.
    if req.phase == "puzzle-lock" and req.homework_id:
        try:
            result = await _check_answer_puzzle_lock(req)
            result = await _attach_integrity(req, result)
            return _attach_check_answer_debug(
                req, result, checker_path="phase_adapter:puzzle-lock"
            )
        except HTTPException:
            raise
        except Exception as e:
            _handle_exc(e)

    # -----------------------------------------------------------------------
    # Division-3 Practices — 8 new practice-arc games (per _DIV3_CONTRACT.md).
    # All server-gated; each resolves its item from content_json and NEVER
    # returns a ⛔ server-only field. Same back-compat gate (require homework_id)
    # as every branch above, registered BEFORE the tutor fallback.
    # -----------------------------------------------------------------------
    if req.phase in _DIV3_PHASE_HANDLERS and req.homework_id:
        try:
            result = await _DIV3_PHASE_HANDLERS[req.phase](req)
            return _attach_check_answer_debug(
                req, result, checker_path=f"phase_adapter:{req.phase}"
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
            # Gap C: legacy path — do not trust client HP beyond the boss ceiling.
            _legacy_boss_hp_warn_once()
            outcome, stars, outcome_xp = _boss_outcome_for(
                hp_remaining=_safe_outcome_hp(req.hp_remaining, int(max_hp)),
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
