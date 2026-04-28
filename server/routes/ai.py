"""
AI Runtime Tutor Endpoints.

Called by the homework playback frontend during student sessions.
All stateless. Request/response JSON, no SSE.
"""
from fastapi import APIRouter, HTTPException, Path as PathParam, Query
from pydantic import BaseModel, Field
from typing import Optional, Any

from ..services import tutor, gemini
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
    """Best-effort lookup for a question dict by id across the buckets we know.

    We touch only top-level lists of dicts inside `content_json` (boss_questions,
    gb_adaptive_quiz, memory_sprint, etc). Nothing fancy — the tutor still works
    if we don't find the question; question_text just stays empty.
    """
    if not isinstance(content, dict) or not question_id:
        return None
    for value in content.values():
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and (
                    item.get("question_id") == question_id
                    or item.get("id") == question_id
                ):
                    return item
    return None


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
    if req.screen_context:
        hw_meta["preview_context"] = req.screen_context[:2000]
    try:
        return await tutor.tutor_chat(
            session_id=req.session_id,
            hw_id=req.hw_id,
            phase=req.phase,
            question_id=req.question_id,
            message=req.message,
            hw_meta=hw_meta,
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
    turns = await db.list_tutor_turns(session_id=session_id, hw_id=hw_id, limit=50)
    return {"turns": turns}
