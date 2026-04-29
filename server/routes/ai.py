"""
AI Runtime Tutor Endpoints.

Called by the homework playback frontend during student sessions.
All stateless. Request/response JSON, no SSE.
"""
from fastapi import APIRouter, HTTPException, Path as PathParam, Query
from pydantic import BaseModel, Field
from typing import Optional, Any

from ..services import tutor, gemini
from ..services.slur_filter import classify, detect_slurs
from ..services import warnings as warnings_svc
from .. import db

router = APIRouter(tags=["ai-tutor"])


# --- Request models ---

class CheckAnswerRequest(BaseModel):
    question_id: str = ""
    question: str
    student_answer: str
    expected_answers: list[str] = []
    answer_spec: Optional[dict[str, Any]] = None
    allow_ai_fallback: bool = True
    subject: str = "math-algebra"
    grade: int = 8
    tier: str = "MEDIUM"
    context: Optional[str] = None
    phase: Optional[str] = None


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

class TutorChatRequest(BaseModel):
    session_id: str
    hw_id: str
    phase: str
    question_id: Optional[str] = None
    message: str
    screen_context: Optional[str] = None
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


@router.post("/ai/check-answer")
async def check_answer(req: CheckAnswerRequest):
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
    # screen_context is allowed only in PREVIEW phase. In PRACTICE/BOSS the
    # student can put rendered DOM (including the answer) into this field, so
    # we drop it entirely outside preview rather than try to scrub.
    if req.screen_context and req.phase == "preview":
        hw_meta["preview_context"] = req.screen_context[:2000]

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
