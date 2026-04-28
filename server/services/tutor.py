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

from fastapi import HTTPException

from ..config import PROMPTS_DIR
from . import gemini
from . import answer_checker
from .. import db


# Wave F1 — per-(session_id, hw_id) message cap for the live tutor widget.
# Beyond this we hard-cut the chat (cost guard).
SESSION_MESSAGE_CAP: int = 60

# Recent chat-history window injected into each tutor_chat prompt.
TUTOR_CHAT_HISTORY_WINDOW: int = 6

# Recent attempt window pulled from the (read-only) tutor_attempts table.
TUTOR_PRIOR_ATTEMPTS_WINDOW: int = 3

# Allowed boss-persona traits. Anything else from the LLM falls back to default.
ALLOWED_PERSONA_TRAITS: tuple[str, ...] = ("challenger", "mentor", "analyst")

# Max length for the per-question framing wrapper rendered above each boss Q.
BOSS_FRAMING_MAX_CHARS: int = 180

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


def _is_boss(question_id: str, phase: Optional[str]) -> bool:
    """Return True when the current request is a boss-phase interaction.

    Preference order:
      1. Explicit ``phase == "boss"`` field — canonical, preferred.
      2. ``question_id.startswith("boss")`` — legacy fallback kept for
         backward-compatibility with callers that pre-date the ``phase`` field.
         DEPRECATED: pass ``phase="boss"`` explicitly instead.
    """
    if phase is not None:
        return phase == "boss"
    # DEPRECATED fallback: infer from question_id prefix when phase is absent.
    return question_id.startswith("boss")


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
    phase: Optional[str] = None,
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
    # Defensive guard: memory_sprint is a tap-only quiz — never burn Vertex tokens on it.
    # allow_ai_fallback=False on the spec is the primary gate; this is a belt-and-suspenders
    # check for any caller that forgets to set it on the spec.
    if not allow_ai_fallback or phase == "memory_sprint":
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
    # Caller can request 2-axis Anchored Mastery Rubric scoring by setting
    # answer_spec.amr=true (or implicitly via type="semantic" — open-ended
    # responses always benefit from AMR). The prompt has an opt-in section
    # that emits axis_1/axis_2 when amr_mode is true in the input payload.
    amr_requested = bool(answer_spec.get("amr")) or answer_spec.get("type") == "semantic"
    payload = {
        "question": question,
        "student_answer": student_answer,
        "expected_answers": expected_answers,
        "subject": subject,
        "grade": grade,
        "tier": tier,
        "context": context or "",
        "amr_mode": amr_requested,
    }
    schema = {
        "correct": "bool",
        "score": "float between 0 and 1",
        "feedback": "Uzbek string, formal Siz, 1-2 sentences",
        "matched_expected": "string or null",
        "confidence": "float between 0 and 1",
    }
    if amr_requested:
        schema.update({
            "axis_1": "integer 1..4 (Concept Identification)",
            "axis_2": "integer 1..4 (Process Integrity)",
            "axis_1_label": "Mastered|Proficient|Apprentice|Novice",
            "axis_2_label": "Mastered|Proficient|Apprentice|Novice",
        })
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
        if _is_boss(question_id, phase):
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

        # Preserve AMR axes from the AI response on the low-confidence path so
        # the scorecard still gets axis data even when the verdict is unsure.
        for k in ("axis_1", "axis_2", "axis_1_label", "axis_2_label"):
            if k in ai_response:
                res[k] = ai_response[k]

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
    persona_traits: Optional[list[str]] = None,
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

    Wave F3: optional `persona_traits` (e.g. ["challenger", "mentor"]) adapts the boss
    tone. When None or empty, behavior is identical to prior versions (backward-compat).
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
    # Wave F3 — inject persona traits so the prompt can adapt tone.
    # Only include when non-empty to keep the payload identical for callers that
    # don't supply persona_traits (backward-compat guard).
    effective_traits = [
        t for t in (persona_traits or [])
        if isinstance(t, str) and t in ALLOWED_PERSONA_TRAITS
    ]
    if effective_traits:
        payload["persona_traits"] = effective_traits

    # AMR 2-axis grading is REQUIRED for every Final Boss attack — the
    # rubric specifically measures Concept Identification + Process
    # Integrity on multi-step reasoning, which is exactly what Boss
    # Q3-Q5 demand. Always pass amr_mode=true so the prompt emits the
    # extended JSON shape with axis_1/axis_2.
    payload["amr_mode"] = True

    schema = {
        "correct": "bool",
        "damage_dealt": "int (0 or damage_value)",
        "boss_response": "Uzbek string, in-character boss, 1 sentence",
        "hint": "Uzbek string or null (null if attempt 1 or if correct)",
        "score": "float 0-1",
        "axis_1": "integer 1..4 (Concept Identification)",
        "axis_2": "integer 1..4 (Process Integrity)",
        "axis_1_label": "Mastered|Proficient|Apprentice|Novice",
        "axis_2_label": "Mastered|Proficient|Apprentice|Novice",
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


# ---------------------------------------------------------------------------
# Wave F1 — live tutor chat + boss-plan
# ---------------------------------------------------------------------------


# Keys we strip from any question payload before it enters the LLM context for
# practice/boss phases. Bridge B (answer-leak prevention) — see the plan.
_ANSWER_LEAK_KEYS: tuple[str, ...] = (
    "expected",
    "ans",
    "accepted_answers",
    "correct",
)


def _redact_question_for_tutor(question: dict, phase: str) -> dict:
    """Return a deep-ish copy of `question` with answer-bearing keys removed.

    For non-preview phases, `expected`, `ans`, `accepted_answers`, and `correct`
    are stripped at top level AND inside `answer_spec`. Preview phase passes
    through unchanged so the tutor can explain why X is the answer.
    """
    if not isinstance(question, dict):
        return {}
    if phase == "preview":
        # Preview is the only phase where the answer is allowed in context.
        return dict(question)

    # Shallow copy + scrub answer_spec separately so we don't mutate the caller.
    redacted = {k: v for k, v in question.items() if k not in _ANSWER_LEAK_KEYS}
    spec = redacted.get("answer_spec")
    if isinstance(spec, dict):
        redacted["answer_spec"] = {
            k: v for k, v in spec.items() if k not in _ANSWER_LEAK_KEYS
        }
    return redacted


def _format_attempts_for_prompt(attempts: list[dict]) -> str:
    """Render recent attempts as compact bullet lines for the tutor prompt."""
    lines: list[str] = []
    for a in attempts:
        ans = a.get("student_answer", "")
        verdict = a.get("verdict", "")
        feedback = a.get("feedback")
        if feedback:
            lines.append(f'- "{ans}" -> {verdict} (AI: {feedback})')
        else:
            lines.append(f'- "{ans}" -> {verdict}')
    return "\n".join(lines)


def _format_history_for_prompt(turns: list[dict]) -> str:
    """Render recent chat turns as compact lines for the tutor prompt."""
    lines: list[str] = []
    for t in turns:
        role = t.get("role", "")
        content = t.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _build_tutor_chat_prompt(
    *,
    system_prompt: str,
    phase: str,
    subject: str,
    grade: int,
    question_text: str,
    preview_context: Optional[str],
    student_profile: Optional[str],
    persona_traits: Optional[list[str]],
    prior_attempts: list[dict],
    chat_history: list[dict],
    student_message: str,
) -> str:
    """Assemble the full tutor_chat prompt. Optional sections are omitted when
    their input is empty so the prompt stays tight.
    """
    parts: list[str] = [system_prompt, "\n---\n\nINPUT:"]
    parts.append(f"PHASE: {phase}")
    parts.append(f"SUBJECT: {subject}")
    parts.append(f"GRADE: {grade}")
    if question_text:
        parts.append(f"QUESTION_TEXT:\n{question_text}")
    if preview_context:
        parts.append(f"PREVIEW_CONTEXT:\n{preview_context}")
    if student_profile:
        parts.append(f"STUDENT_PROFILE:\n{student_profile}")
    if persona_traits:
        parts.append(f"PERSONA_TRAITS: {', '.join(persona_traits)}")
    if prior_attempts:
        parts.append(
            "STUDENT_PRIOR_ATTEMPTS_ON_THIS_QUESTION:\n"
            + _format_attempts_for_prompt(prior_attempts)
        )
    parts.append(
        "CHAT_HISTORY:\n" + (_format_history_for_prompt(chat_history) or "(none)")
    )
    parts.append(f"STUDENT_MESSAGE:\n{student_message}")
    return "\n\n".join(parts)


async def tutor_chat(
    session_id: str,
    hw_id: str,
    phase: str,
    question_id: Optional[str],
    message: str,
    hw_meta: Optional[dict] = None,
) -> dict:
    """Live tutor chat — persists the user turn, calls the LLM, persists the
    assistant turn, returns ``{"response": str, "message_id": int}``.

    Enforces a per-(session_id, hw_id) cap of ``SESSION_MESSAGE_CAP`` total
    turns. Beyond that, raises ``HTTPException(429)``.

    For non-preview phases, strips all answer-bearing keys from the loaded
    question payload before it enters the LLM context.
    """
    hw_meta = hw_meta or {}

    # Step 1 — persist the user turn first so it's never lost on a downstream
    # error, AND so the cap counts the message we just received.
    user_turn_id = await db.add_tutor_turn(
        session_id=session_id,
        hw_id=hw_id,
        phase=phase,
        question_id=question_id,
        role="user",
        content=message,
    )

    # Step 2 — enforce the per-session cap.
    total = await db.count_session_messages(session_id, hw_id)
    if total > SESSION_MESSAGE_CAP:
        raise HTTPException(
            status_code=429,
            detail={
                "error": (
                    f"Session message cap of {SESSION_MESSAGE_CAP} reached. "
                    "Please start a new session."
                ),
                "code": "TUTOR_SESSION_CAP",
            },
        )

    # Step 3 — chat history (last N turns).
    all_turns = await db.list_tutor_turns(session_id, hw_id, limit=200)
    chat_history = all_turns[-TUTOR_CHAT_HISTORY_WINDOW:]

    # Step 4 — recent attempts (read-only; graceful empty if table missing).
    prior_attempts: list[dict] = []
    if question_id:
        prior_attempts = await db.list_recent_attempts(
            session_id=session_id,
            hw_id=hw_id,
            question_id=question_id,
            limit=TUTOR_PRIOR_ATTEMPTS_WINDOW,
        )

    # Step 5 — build the prompt.
    system_prompt = _load_runtime_prompt("tutor-assistant")

    # Pull the full question dict from the homework's content_json when one was
    # named. Strip answer-bearing keys for non-preview phases.
    question_text = ""
    preview_context = hw_meta.get("preview_context")
    if question_id and isinstance(hw_meta.get("question"), dict):
        redacted = _redact_question_for_tutor(hw_meta["question"], phase)
        # Use the prompt/q text the student sees.
        question_text = (
            redacted.get("q")
            or redacted.get("prompt")
            or redacted.get("question")
            or ""
        )

    full_prompt = _build_tutor_chat_prompt(
        system_prompt=system_prompt,
        phase=phase,
        subject=str(hw_meta.get("subject", "")),
        grade=int(hw_meta.get("grade", 0) or 0),
        question_text=question_text,
        preview_context=preview_context,
        student_profile=hw_meta.get("student_profile"),
        persona_traits=hw_meta.get("persona_traits"),
        prior_attempts=prior_attempts,
        chat_history=chat_history,
        student_message=message,
    )

    # Step 6 — call the LLM. Wrap in a try/except so a backend hiccup surfaces
    # as a friendly 500 instead of an uncaught traceback.
    try:
        response_text = await gemini.generate(full_prompt, model=gemini.FAST_MODEL)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"Tutor backend error: {exc}",
                "code": "TUTOR_BACKEND_ERROR",
            },
        ) from exc

    # Step 7 — persist the assistant turn and return.
    asst_turn_id = await db.add_tutor_turn(
        session_id=session_id,
        hw_id=hw_id,
        phase=phase,
        question_id=question_id,
        role="assistant",
        content=response_text,
    )
    return {"response": response_text, "message_id": asst_turn_id}


def _default_boss_plan(boss_questions: list[dict]) -> dict:
    """Fallback plan when the LLM output is invalid or missing.

    Preserves input order with neutral framing and the safe "mentor" persona.
    """
    ordered: list[dict] = []
    for q in boss_questions:
        qid = q.get("question_id") or q.get("id") or ""
        ordered.append(
            {
                "question_id": qid,
                "framing_text": "O'rgangan bilimingizni amalda qo'llash vaqti keldi.",
            }
        )
    return {"ordered": ordered, "persona_traits": ["mentor"]}


def _validate_boss_plan(plan: dict, boss_questions: list[dict]) -> Optional[dict]:
    """Return a sanitized plan, or None if the response is invalid.

    Validation rules:
      - every input question_id must be covered exactly once
      - persona_traits must be a non-empty subset of ALLOWED_PERSONA_TRAITS
      - framing_text must be a string and is truncated to BOSS_FRAMING_MAX_CHARS
    """
    if not isinstance(plan, dict):
        return None

    raw_ordered = plan.get("ordered")
    if not isinstance(raw_ordered, list) or not raw_ordered:
        return None

    expected_ids = {
        (q.get("question_id") or q.get("id") or "") for q in boss_questions
    }
    expected_ids.discard("")

    seen: set[str] = set()
    cleaned_ordered: list[dict] = []
    for entry in raw_ordered:
        if not isinstance(entry, dict):
            return None
        qid = entry.get("question_id")
        if not isinstance(qid, str) or qid not in expected_ids or qid in seen:
            return None
        seen.add(qid)
        framing = entry.get("framing_text", "")
        if not isinstance(framing, str):
            return None
        if len(framing) > BOSS_FRAMING_MAX_CHARS:
            framing = framing[:BOSS_FRAMING_MAX_CHARS]
        cleaned_ordered.append({"question_id": qid, "framing_text": framing})

    if seen != expected_ids:
        return None

    raw_traits = plan.get("persona_traits")
    if not isinstance(raw_traits, list) or not raw_traits:
        return None
    cleaned_traits = [
        t for t in raw_traits if isinstance(t, str) and t in ALLOWED_PERSONA_TRAITS
    ]
    if not cleaned_traits:
        return None

    return {"ordered": cleaned_ordered, "persona_traits": cleaned_traits}


async def boss_plan(
    session_id: str,
    hw_id: str,
    boss_questions: list[dict],
) -> dict:
    """Build a personalized boss-question plan.

    Returns ``{"ordered": [{question_id, framing_text}], "persona_traits": [...]}``.
    On any LLM failure or invalid response, returns the default-order fallback
    rather than crashing — boss must always be playable.
    """
    if not boss_questions:
        return {"ordered": [], "persona_traits": ["mentor"]}

    student_profile = await db.build_session_profile(session_id, hw_id)

    # Recent attempts across all questions in this session — graceful empty if
    # the producer table doesn't exist yet.
    recent_attempts: list[dict] = []
    for q in boss_questions:
        qid = q.get("question_id") or q.get("id") or ""
        if not qid:
            continue
        rows = await db.list_recent_attempts(session_id, hw_id, qid, limit=2)
        recent_attempts.extend(rows)

    # Normalize the LLM input. Strip any answer-bearing keys from the boss-Q
    # payload — the planner doesn't need the answers.
    sanitized_questions = [_redact_question_for_tutor(q, "boss") for q in boss_questions]

    try:
        system_prompt = _load_runtime_prompt("tutor-boss-plan")
    except FileNotFoundError:
        return _default_boss_plan(boss_questions)

    payload = {
        "BOSS_QUESTIONS": sanitized_questions,
        "STUDENT_PROFILE": student_profile or "(empty)",
        "RECENT_PRACTICE_ATTEMPTS": [
            {
                "question_id": r.get("question_id"),
                "verdict": r.get("verdict"),
                "score": r.get("score"),
                "feedback": r.get("feedback"),
            }
            for r in recent_attempts
        ],
    }
    schema = {
        "ordered": "array of {question_id: string, framing_text: string (<=180 chars)}",
        "persona_traits": "array with at least one of: challenger, mentor, analyst",
    }
    full_prompt = (
        f"{system_prompt}\n\n---\n\nINPUT:\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )

    try:
        ai_response = await gemini.generate_json(
            full_prompt,
            schema_hint=schema,
            model=gemini.PRO_MODEL,
        )
    except Exception as exc:  # noqa: BLE001 — we want every LLM hiccup caught.
        print(f"[boss_plan] LLM failed; using default plan: {exc}", flush=True)
        return _default_boss_plan(boss_questions)

    cleaned = _validate_boss_plan(ai_response, boss_questions)
    if cleaned is None:
        return _default_boss_plan(boss_questions)
    return cleaned


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
    # AMR is always required for Real-Life Q5 and any other open-ended
    # tutor-routed answer. The runtime listener pulls axis_1/axis_2 out
    # of the result for the AMR scorecard; if we don't request them
    # here, the listener falls back to a default of 3/3 which would
    # inflate axis means regardless of answer quality.
    payload = {
        "phase": phase,
        "question": question,
        "student_input": student_input,
        "subject": subject,
        "grade": grade,
        "context": context or "",
        "amr_mode": True,
    }
    schema = {
        "response": "Uzbek string, 2-3 sentences, patient tutor tone",
        "guidance_type": "one of: hint, explanation, encouragement, correction",
        "axis_1": "integer 1..4 (Concept Identification)",
        "axis_2": "integer 1..4 (Process Integrity)",
        "axis_1_label": "Mastered|Proficient|Apprentice|Novice",
        "axis_2_label": "Mastered|Proficient|Apprentice|Novice",
    }
    return await gemini.generate_json(
        f"{prompt}\n\n---\n\nINPUT:\n{json.dumps(payload, ensure_ascii=False, indent=2)}",
        schema_hint=schema,
        model=gemini.FAST_MODEL,
    )
