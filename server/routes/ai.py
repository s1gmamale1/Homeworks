"""
AI Runtime Tutor Endpoints.

Called by the homework playback frontend during student sessions.
All stateless. Request/response JSON, no SSE.
"""
import logging
from fastapi import APIRouter, HTTPException, Path as PathParam, Query
from pydantic import BaseModel, Field
from typing import Optional, Any

from ..services import tutor, gemini
from ..services.slur_filter import classify, detect_slurs
from ..services import warnings as warnings_svc
from .. import db

router = APIRouter(tags=["ai-tutor"])

_log = logging.getLogger("nets.sentence_fill")


# --- Request models ---

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
    "consolidation",
    "final-boss",
    "reflection",
})


class TutorChatRequest(BaseModel):
    session_id: str
    hw_id: str
    phase: str
    question_id: Optional[str] = None
    message: str
    screen_context: Optional[str] = None
    student_work_text: Optional[str] = None
    subphase: Optional[str] = None
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


# --- Status ---

@router.get("/ai/status")
async def ai_status() -> dict:
    """Report which AI backend is active plus project/location/model for debugging."""
    pref_list = gemini._preference_list()
    active = gemini._active_backend()

    info: dict[str, Any] = {
        # Legacy fields — kept for backward compat
        "backend": active,
        "model_fast": gemini.FAST_MODEL,
        "model_pro": gemini.PRO_MODEL,
        # Wave F0 additions
        "active_provider": active,
        "preference_list": pref_list,
        "available_providers": gemini.available_providers(),
    }
    if active == "vertex":
        try:
            info["project"] = gemini._resolve_vertex_project(gemini.VERTEX_CREDENTIALS_PATH)
        except Exception:
            info["project"] = None
        info["location"] = gemini.VERTEX_LOCATION
        info["credentials_path"] = gemini.VERTEX_CREDENTIALS_PATH
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
            return await _check_answer_sentence_fill(req)
        except HTTPException:
            raise
        except Exception as e:
            _handle_exc(e)

    try:
        return await tutor.check_answer(
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
        return await tutor.boss_turn(
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
    if isinstance(bq, list):
        return [q for q in bq if isinstance(q, dict)]
    return []


@router.post("/ai/tutor/chat")
async def tutor_chat(req: TutorChatRequest):
    """Live tutor chat — persists turns + invokes the LLM."""
    # Reject malformed session IDs early so they never reach the DB layer.
    tutor._validate_session_id(req.session_id)

    hw = await db.get_homework(req.hw_id)
    hw_meta: dict[str, Any] = {}
    if hw:
        hw_meta["subject"] = hw.get("subject", "")
        hw_meta["grade"] = hw.get("grade", 0)
        content = hw.get("content_json") or {}
        if req.question_id:
            q = _find_question_in_content(content, req.question_id)
            if q is not None:
                hw_meta["question"] = q
    # screen_context is now passed for ALL phases. The server-side sanitizer in
    # tutor.py (_sanitize_screen_context) scrubs answer-bearing DOM attributes
    # so we no longer need to silently drop it outside preview.
    screen_context = req.screen_context[:2000] if req.screen_context else None

    # student_work_text: what the student has typed/selected right now.
    student_work_text = (
        req.student_work_text[:2000] if req.student_work_text else None
    )

    # subphase: validate against the allowlist; drop silently if unknown.
    subphase = req.subphase if req.subphase in SUBPHASE_ALLOWLIST else None

    # --- Warning state machine ---
    # Step 1: classify the incoming message via T1's new classifier.
    classification = classify(req.message)

    # Step 2: evaluate against the warning state machine (persists if triggered).
    try:
        outcome = await warnings_svc.evaluate(
            classification,
            hw_id=req.hw_id,
            session_id=req.session_id,
        )
    except Exception as e:
        # Don't let a DB error in the warning layer block the tutor.
        import logging
        logging.getLogger("nets.tutor").warning("warnings.evaluate failed: %s", e)
        outcome = None

    # Step 3: fail short-circuit — level 9 means homework failed.
    if outcome is not None and outcome.is_fail:
        lang = outcome.lang
        if lang == "ru":
            fail_msg = "Урок завершён. Переходим к финалу."
        elif lang == "en":
            fail_msg = "Homework done. Moving to reflection."
        else:
            fail_msg = "Uy vazifasi tugadi. So'nggi bosqichga o'tamiz."
        return {
            "response": fail_msg,
            "message_id": None,
            "homework_failed": True,
            "warning_level": outcome.level,
            "cumulative_deduction_pct": outcome.cumulative_deduction_pct,
        }

    try:
        # Step 4: build kwargs for tutor_chat from warning outcome.
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

        result = await tutor.tutor_chat(
            session_id=req.session_id,
            hw_id=req.hw_id,
            phase=req.phase,
            question_id=req.question_id,
            message=req.message,
            hw_meta=hw_meta,
            recent_assistant_phrases=req.recent_assistant_phrases or [],
            screen_context=screen_context,
            student_work_text=student_work_text,
            subphase=subphase,
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
        return result
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
        return await tutor.boss_plan(
            session_id=req.session_id,
            hw_id=req.hw_id,
            boss_questions=boss_questions,
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
    return {"turns": turns}
