"""
AI Tutor Runtime Service.

Stateless tutor endpoints called during student homework playback.
Each function loads its prompt from server/prompts/runtime/{name}.md,
sends to Gemini with request-specific context, returns typed result.
"""
import hashlib
import re
from typing import Optional, Any
from pathlib import Path
import json

from ..config import PROMPTS_DIR
from . import gemini
from . import answer_checker
from .. import db

RUNTIME_PROMPTS = PROMPTS_DIR / "runtime"


def _load_runtime_prompt(name: str) -> str:
    path = RUNTIME_PROMPTS / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Runtime prompt missing: {path}")
    return path.read_text(encoding="utf-8")


def _normalize(text: str) -> str:
    if not text:
        return ""
    return re.sub(r'\s+', '', str(text).lower())


async def check_answer(
    question_id: str = "",
    question: str = "",
    student_answer: str = "",
    expected_answers: list[str] = None,
    answer_spec: Optional[dict] = None,
    allow_ai_fallback: bool = True,
    subject: str = "math-algebra",
    grade: int = 8,
    tier: str = "MEDIUM",
    context: Optional[str] = None,
) -> dict:
    """
    Evaluate a student's typed answer semantically.
    """
    if expected_answers is None:
        expected_answers = []
        
    if answer_spec is None:
        # Fallback for old requests
        spec_expected = expected_answers[0] if expected_answers else ""
        answer_spec = {
            "type": "text_fuzzy",
            "expected": spec_expected,
            "canonical_display": spec_expected
        }
        
    # Step 1: Deterministic check
    det_result = answer_checker.check(answer_spec, student_answer)
    verdict = det_result.get("verdict")
    
    if verdict in ("correct", "incorrect"):
        is_correct = verdict == "correct"
        score = 1.0 if is_correct else 0.0
        feedback = "To'g'ri javob!" if is_correct else "Notog'ri javob."
        res = {
            "correct": is_correct,
            "score": score,
            "feedback": feedback,
            "source": "deterministic"
        }
        if det_result.get("format_tip"):
            res["format_tip"] = det_result["format_tip"]
        return res

    # Step 2: AI Fallback check
    if not allow_ai_fallback:
        # If unsure and no AI fallback, just mark incorrect to be safe
        return {
            "correct": False,
            "score": 0.0,
            "feedback": "Notog'ri javob.",
            "source": "deterministic"
        }

    # Cache key includes the answer_spec/expected fingerprint so the same question_id
    # reused across homeworks (e.g. "q1") can't collide on different correct answers.
    spec_fingerprint = json.dumps(
        {"spec": answer_spec, "expected": expected_answers},
        ensure_ascii=False,
        sort_keys=True,
    )
    cache_key_raw = f"{question_id}|{_normalize(student_answer)}|{spec_fingerprint}"
    cache_key = hashlib.sha256(cache_key_raw.encode("utf-8")).hexdigest()

    cached = await db.get_answer_cache(cache_key)
    if cached:
        return cached

    # Log every AI fallback call for rate-limit / abuse triage.
    print(
        f"[ai-fallback] question_id={question_id!r} subject={subject} grade={grade} "
        f"tier={tier} det_verdict={verdict} cache_miss=True",
        flush=True,
    )

    prompt = _load_runtime_prompt("answer-checker")
    payload = {
        "question": question,
        "student_answer": student_answer,
        "expected_answers": expected_answers,
        "subject": subject,
        "grade": grade,
        "tier": tier,
        "context": context or "",
    }
    schema = {
        "correct": "bool",
        "score": "float between 0 and 1",
        "feedback": "Uzbek string, formal Siz, 1-2 sentences",
        "matched_expected": "string or null",
        "confidence": "float between 0 and 1"
    }
    ai_response = await gemini.generate_json(
        f"{prompt}\n\n---\n\nINPUT:\n{json.dumps(payload, ensure_ascii=False, indent=2)}",
        schema_hint=schema,
        model=gemini.FAST_MODEL,
    )
    
    confidence = float(ai_response.get("confidence", 1.0))
    if confidence >= 0.90:
        ai_response["source"] = "ai"
        await db.set_answer_cache(cache_key, ai_response)
        return ai_response
    else:
        # Low confidence
        needs_review = True
        is_boss = question_id.startswith("boss-") or ("phase" in payload and payload.get("phase") == "boss")
        if is_boss:
            res = {
                "correct": True,
                "score": 0.7,
                "feedback": ai_response.get("feedback", "Javobingiz tekshirilmoqda..."),
                "source": "ai_unsure",
                "needs_review": True
            }
        else:
            res = {
                "correct": False,
                "score": 0.0,
                "feedback": ai_response.get("feedback", "Javobingizni tushunmadim, qayta urinib ko'ring."),
                "source": "ai_unsure",
                "needs_review": True
            }
            
        await db.add_to_review_queue(question_id, student_answer, answer_spec, ai_response)
        return res


async def boss_turn(
    boss_question: str,
    student_answer: str,
    expected_answers: list[str],
    damage_value: int,
    hp_remaining: int,
    attempt_number: int,
    subject: str,
    grade: int,
) -> dict:
    """
    Boss combat turn. Evaluates answer, assigns damage, generates in-character boss response.
    Returns: {
        "correct": bool,
        "damage_dealt": int (damage_value if correct, 0 otherwise),
        "boss_response": str (in-character Uzbek taunt or praise, 1 sentence),
        "hint": Optional[str] (if wrong and attempt_number >= 2, provide a hint),
        "score": float
    }
    """
    prompt = _load_runtime_prompt("boss-tutor")
    payload = {
        "boss_question": boss_question,
        "student_answer": student_answer,
        "expected_answers": expected_answers,
        "damage_value": damage_value,
        "hp_remaining": hp_remaining,
        "attempt_number": attempt_number,
        "subject": subject,
        "grade": grade,
    }
    schema = {
        "correct": "bool",
        "damage_dealt": "int (0 or damage_value)",
        "boss_response": "Uzbek string, in-character boss, 1 sentence",
        "hint": "Uzbek string or null (null if attempt 1 or if correct)",
        "score": "float 0-1",
    }
    return await gemini.generate_json(
        f"{prompt}\n\n---\n\nINPUT:\n{json.dumps(payload, ensure_ascii=False, indent=2)}",
        schema_hint=schema,
        model=gemini.PRO_MODEL,  # boss uses stronger model
    )


async def reflection_feedback(
    homework_title: str,
    homework_summary: str,
    student_reflection: str,
    performance: dict,
    subject: str,
    grade: int,
) -> dict:
    """
    Personalized reflection response after student finishes homework.
    Returns: {
        "feedback": str (Uzbek, warm, 3-4 sentences, acknowledges strengths + one growth area),
        "next_steps": list[str] (2-3 concrete actions for next session),
        "encouragement": str (1 sentence),
    }
    """
    prompt = _load_runtime_prompt("reflection-coach")
    payload = {
        "homework_title": homework_title,
        "homework_summary": homework_summary,
        "student_reflection": student_reflection,
        "performance": performance,  # {correct: int, total: int, time_minutes: int, weak_phase: str}
        "subject": subject,
        "grade": grade,
    }
    schema = {
        "feedback": "Uzbek string, 3-4 sentences",
        "next_steps": "array of 2-3 Uzbek strings",
        "encouragement": "Uzbek string, 1 sentence",
    }
    return await gemini.generate_json(
        f"{prompt}\n\n---\n\nINPUT:\n{json.dumps(payload, ensure_ascii=False, indent=2)}",
        schema_hint=schema,
        model=gemini.FAST_MODEL,
    )


async def tutor_help(
    phase: str,
    question: str,
    student_input: str,
    subject: str,
    grade: int,
    context: Optional[str] = None,
) -> dict:
    """
    General tutor assistant. Fallback for open-ended questions or when student asks for help.
    Returns: {
        "response": str (Uzbek, patient tutor tone, 2-3 sentences),
        "guidance_type": "hint" | "explanation" | "encouragement" | "correction",
    }
    """
    prompt = _load_runtime_prompt("tutor-assistant")
    payload = {
        "phase": phase,
        "question": question,
        "student_input": student_input,
        "subject": subject,
        "grade": grade,
        "context": context or "",
    }
    schema = {
        "response": "Uzbek string, 2-3 sentences, patient tutor tone",
        "guidance_type": "one of: hint, explanation, encouragement, correction",
    }
    return await gemini.generate_json(
        f"{prompt}\n\n---\n\nINPUT:\n{json.dumps(payload, ensure_ascii=False, indent=2)}",
        schema_hint=schema,
        model=gemini.FAST_MODEL,
    )
