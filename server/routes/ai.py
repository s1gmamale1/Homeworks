"""
AI Runtime Tutor Endpoints.

Called by the homework playback frontend during student sessions.
All stateless. Request/response JSON, no SSE.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Any

from ..services import tutor, gemini

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



class BossTurnRequest(BaseModel):
    boss_question: str
    student_answer: str
    expected_answers: list[str] = []
    damage_value: int = Field(default=10, ge=0, le=50)
    hp_remaining: int = Field(default=100, ge=0)
    attempt_number: int = Field(default=1, ge=1)
    subject: str = "math-algebra"
    grade: int = 8


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


# --- Helpers ---

def _handle_exc(e: Exception):
    if isinstance(e, FileNotFoundError):
        raise HTTPException(500, detail={"error": str(e), "code": "PROMPT_MISSING"})
    raise HTTPException(500, detail={"error": str(e), "code": "AI_ERROR"})


# --- Status ---

@router.get("/ai/status")
async def ai_status() -> dict:
    """Report which AI backend is active plus project/location/model for debugging."""
    info: dict[str, Any] = {
        "backend": gemini.ACTIVE_BACKEND,
        "model_fast": gemini.FAST_MODEL,
        "model_pro": gemini.PRO_MODEL,
    }
    if gemini.ACTIVE_BACKEND == "vertex":
        try:
            info["project"] = gemini._resolve_vertex_project(gemini.VERTEX_CREDENTIALS_PATH)
        except Exception:
            info["project"] = None
        info["location"] = gemini.VERTEX_LOCATION
        info["credentials_path"] = gemini.VERTEX_CREDENTIALS_PATH
    return info


# --- Endpoints ---

from fastapi import APIRouter, HTTPException, Path as PathParam

class ReviewDecideRequest(BaseModel):
    correct: bool
    score: float
    feedback: str

@router.get("/review-queue")
async def get_review_queue():
    from .. import db
    return await db.get_review_queue()

@router.post("/review-queue/{id}/decide")
async def decide_review_queue(req: ReviewDecideRequest, id: int = PathParam(...)):
    from .. import db
    success = await db.resolve_review_item(id, req.model_dump())
    if not success:
        raise HTTPException(404, detail="Review item not found or already resolved")
    return {"status": "ok"}

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
