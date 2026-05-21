"""
AI Tutor Runtime Service.

Stateless tutor endpoints called during student homework playback.
Each function loads its prompt from server/prompts/runtime/{name}.md,
sends to Gemini with request-specific context, returns typed result.
"""
import hashlib
import logging
import re
from typing import Optional, Any
from pathlib import Path
import json

from fastapi import HTTPException

from ..config import PROMPTS_DIR
from . import ai_orchestrator, ai_debug, ai_gateway
from . import answer_checker
from . import ai_context
from .. import db
from ..schemas.ai_contracts import AnswerCheckResult

# Server-side log channel for the tutor — full provider errors land here while
# the client receives a scrubbed friendly message.
_log = logging.getLogger("nets.tutor")

# Minimum entropy + safe charset for session_id. The frontend produces
# UUIDv4 (`crypto.randomUUID()`); test fixtures use shorter slug-style ids.
# Anything ≥8 chars in this charset passes; trivial enumeration vectors
# (single digits, plain words, empty strings) are rejected. Until proper
# auth lands, the only thing protecting one student's history from another
# is the unguessability of this token.
_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,}$")
_SESSION_ID_MIN_LEN = 8


def _validate_session_id(session_id: str) -> str:
    """Reject malformed or trivially-guessable session IDs.

    Returns the value unchanged on success; raises 400 otherwise.
    """
    if (
        not isinstance(session_id, str)
        or len(session_id) < _SESSION_ID_MIN_LEN
        or not _SESSION_ID_RE.match(session_id)
    ):
        raise HTTPException(
            status_code=400,
            detail={
                "error": (
                    "session_id must be at least "
                    f"{_SESSION_ID_MIN_LEN} chars, alphanumeric/-/_"
                ),
                "code": "INVALID_SESSION_ID",
            },
        )
    return session_id


def _fence_untrusted(text: str) -> str:
    """Wrap a chunk of user-controlled text in tags that the system prompt
    instructs the model to treat as data, not instructions.

    Defense-in-depth for prompt injection — the prompt-side rule does the
    actual work, but the fence makes the boundary visible to the model and
    impossible to miss.
    """
    if not isinstance(text, str):
        text = "" if text is None else str(text)
    # Strip any pre-existing fence tags from the input so a student can't
    # forge a closing tag and inject instructions outside the fence.
    cleaned = text.replace("<UNTRUSTED>", "").replace("</UNTRUSTED>", "")
    return f"<UNTRUSTED>{cleaned}</UNTRUSTED>"


def _sanitize_screen_context(text: str, expected_value: str | None = None) -> str:
    """Scrub answer-bearing content from DOM-derived screen context.

    Rules applied in order:
      1. Empty/None input → return "".
      2. Drop entire lines that match HTML answer-marker patterns (data-correct,
         class=correct/is-correct/answer-key, data-expected/answer attributes).
      3. If `expected_value` is non-empty, strip whole-token occurrences of it
         from the remaining text (case-insensitive).
      4. Truncate the result to 2000 chars.
    """
    if not text:
        return ""
    if not isinstance(text, str):
        text = str(text)

    # Pattern that flags lines containing HTML answer markers.
    _ANSWER_MARKER_RE = re.compile(
        r"data-correct\s*=\s*['\"]?true"
        r"|class=['\"][^'\"]*\b(?:correct|is-correct|answer-key)\b"
        r"|data-(?:expected|answer)\s*=\s*",
        re.IGNORECASE,
    )

    lines = text.splitlines()
    clean_lines = [line for line in lines if not _ANSWER_MARKER_RE.search(line)]
    result = "\n".join(clean_lines)

    if expected_value and isinstance(expected_value, str):
        # Strip whole-token occurrences of expected_value (case-insensitive).
        pattern = r"(?<!\w)" + re.escape(expected_value) + r"(?!\w)"
        result = re.sub(pattern, "", result, flags=re.IGNORECASE)

    return result[:2000]


def _strip_fence_tags(reply: str) -> str:
    """Remove <UNTRUSTED> / </UNTRUSTED> tags from the LLM's reply.

    The model occasionally mirrors the fence tags back into its response.
    This function strips them from the *output* so they never reach the UI.
    Excess blank lines produced by the removal are collapsed to at most two.
    """
    if not reply:
        return reply
    stripped = re.sub(r"</?UNTRUSTED>", "", reply)
    # Collapse 3+ consecutive newlines to 2.
    stripped = re.sub(r"\n{3,}", "\n\n", stripped)
    return stripped


def _validate_phase(phase: str) -> str:
    """Reject phases that are not in `ALLOWED_PHASES`.

    Pre-fix the route accepted any string as `phase` — `phase="xyzzy"` would
    bypass the boss-mode check (`phase == "boss"`) silently and the
    `_redact_question_for_tutor` strip pass would still run since "xyzzy"
    isn't "preview". Safe-by-default, but we'd rather hard-reject so callers
    get clear errors and the logic can rely on the field shape.
    """
    if phase not in ALLOWED_PHASES:
        raise HTTPException(
            status_code=400,
            detail={
                "error": (
                    f"phase must be one of {ALLOWED_PHASES!r}, got {phase!r}"
                ),
                "code": "INVALID_PHASE",
            },
        )
    return phase


def _scrub_provider_error(exc: Exception) -> str:
    """Return a client-safe error message; full detail goes to server logs.

    Provider exceptions sometimes embed API-key fragments, GCP project IDs,
    or internal endpoints — never forward those to a browser. We log the
    raw exception so on-call can still diagnose, and we hand the user a
    generic message.
    """
    _log.exception("Tutor LLM call failed: %s", exc)
    return "Tutor backend temporarily unavailable. Please try again."


def _was_correct_normalized(student_answer: str, expected_answers: list[str]) -> bool:
    """Pre-compute correctness server-side for boss-turn so the LLM never sees
    the raw expected_answers list (which would otherwise be a leak surface
    against prompt injection in BOSS).

    Uses normalized whitespace+case comparison — same shape as `_normalize`.
    """
    if not student_answer or not expected_answers:
        return False
    needle = _normalize(student_answer)
    if not needle:
        return False
    for expected in expected_answers:
        if not isinstance(expected, str):
            continue
        if needle == _normalize(expected):
            return True
    return False


# Wave F1 — per-(session_id, hw_id) message cap for the live tutor widget.
# Beyond this we hard-cut the chat (cost guard).
SESSION_MESSAGE_CAP: int = 60

# Wave F: Subjects requiring PRO_MODEL for math hallucination guard.
# Kimi small model invents math facts; use 128k for reasoning-heavy subjects.
# Extensible for future subject→provider routing (math→Kimi-PRO, science→Vertex, etc.)
_PRO_SUBJECTS = frozenset({
    "math-algebra",
    "geometriya-g7-11",
    "physics",
    "kimyo-g7-11",  # chemistry
})

# Recent chat-history window injected into each tutor_chat prompt.
TUTOR_CHAT_HISTORY_WINDOW: int = 6

# Recent attempt window pulled from the (read-only) tutor_attempts table.
TUTOR_PRIOR_ATTEMPTS_WINDOW: int = 3

# Allowed boss-persona traits. Anything else from the LLM falls back to default.
ALLOWED_PERSONA_TRAITS: tuple[str, ...] = ("challenger", "mentor", "analyst")

# Allowed phase strings. Any unknown phase received from the client is rejected
# at the route boundary so the tutor's mode logic only ever sees known values.
ALLOWED_PHASES: tuple[str, ...] = ("preview", "practice", "boss", "case_based", "memory_check")

# Max length for the per-question framing wrapper rendered above each boss Q.
BOSS_FRAMING_MAX_CHARS: int = 180

RUNTIME_PROMPTS = PROMPTS_DIR / "runtime"


def _model_for_subject(subject: str) -> str:
    """Pick the appropriate model tier based on subject difficulty.

    Math and science subjects require deeper reasoning to avoid hallucinations;
    route to PRO_MODEL. Others use FAST_MODEL to minimize latency/cost.
    Extensible for future subject→provider routing.
    """
    if subject in _PRO_SUBJECTS:
        return ai_orchestrator.PRO_MODEL
    return ai_orchestrator.FAST_MODEL


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

    Boss state is determined exclusively by the explicit ``phase`` field. The
    legacy ``question_id.startswith("boss")`` fallback was removed because a
    student could craft `question_id="boss-anything"` to enable boss-mode
    scoring (which awards `correct: True` on low-confidence AI responses)
    and bypass the practice-phase grading path entirely.
    """
    return phase == "boss"


def _semantic_closed_exact_match(
    answer_spec: dict,
    student_answer: str,
    expected_answers: list[str],
) -> dict | None:
    """Accept exact closed-form semantic answers before AI fallback.

    Some closed practice surfaces, especially the legacy Sentence Fill chain,
    use ``type="semantic"`` only to allow fallback for variants. When the
    student types the exact blank value, sending that one-word answer to the
    language rubric can incorrectly reject it as "too brief". Only apply this
    to explicit non-AMR semantic checks so rubric-scored open answers still
    receive AI axes.
    """
    if not isinstance(answer_spec, dict):
        return None
    if answer_spec.get("type") != "semantic" or answer_spec.get("amr") is not False:
        return None

    candidates: list[str] = []
    for value in expected_answers or []:
        if value is not None and str(value).strip():
            candidates.append(str(value))

    expected = answer_spec.get("expected")
    if isinstance(expected, list):
        candidates.extend(str(v) for v in expected if v is not None and str(v).strip())
    elif expected is not None and str(expected).strip():
        candidates.append(str(expected))

    canonical = answer_spec.get("canonical_display")
    if canonical is not None and str(canonical).strip():
        candidates.append(str(canonical))

    seen: set[str] = set()
    for candidate in candidates:
        key = candidate.casefold()
        if key in seen:
            continue
        seen.add(key)
        det = answer_checker.check(
            {
                "type": "text_exact",
                "expected": candidate,
                "canonical_display": candidate,
            },
            student_answer,
        )
        if det.get("verdict") == "correct":
            return det
    return None


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
    semantic_exact = _semantic_closed_exact_match(answer_spec, student_answer, expected_answers)
    if semantic_exact is not None:
        det_result = semantic_exact
    verdict = det_result.get("verdict")
    
    if verdict in ("correct", "incorrect"):
        is_correct = verdict == "correct"
        score = 1.0 if is_correct else 0.0
        feedback = "To'g'ri javob!" if is_correct else "Notog'ri javob."
        res = {
            "correct": is_correct,
            "score": score,
            "feedback": feedback,
            "source": "deterministic",
            "matched_expected": None
        }
        if det_result.get("format_tip"):
            res["format_tip"] = det_result["format_tip"]
        return ai_debug.with_context_debug(
            res,
            {
                "service": "tutor.check_answer",
                "checker_path": "deterministic",
                "provider": None,
                "model": None,
                "answer_spec_type": answer_spec.get("type"),
                "result_action": "accepted" if is_correct else "rejected",
            },
            route="service.check_answer",
        )

    # Step 2: AI Fallback check
    # Defensive guard: memory_sprint is a tap-only quiz — never burn Vertex tokens on it.
    # allow_ai_fallback=False on the spec is the primary gate; this is a belt-and-suspenders
    # check for any caller that forgets to set it on the spec.
    if not allow_ai_fallback or phase == "memory_sprint":
        # If unsure and no AI fallback, just mark incorrect to be safe
        return ai_debug.with_context_debug(
            {
                "correct": False,
                "score": 0.0,
                "feedback": "Notog'ri javob.",
                "source": "deterministic",
                "matched_expected": None,
            },
            {
                "service": "tutor.check_answer",
                "checker_path": "deterministic_no_ai",
                "provider": None,
                "model": None,
                "answer_spec_type": answer_spec.get("type"),
                "result_action": "rejected",
            },
            route="service.check_answer",
        )

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
        return ai_debug.with_context_debug(
            cached,
            {
                "service": "tutor.check_answer",
                "checker_path": "cache",
                "provider": ai_orchestrator._active_backend(),
                "model": ai_orchestrator.FAST_MODEL,
                "answer_spec_type": answer_spec.get("type"),
                "result_action": "cached",
            },
            route="service.check_answer",
        )

    # Log every AI fallback call for rate-limit / abuse triage.
    print(
        f"[ai-fallback] question_id={question_id!r} subject={subject} grade={grade} "
        f"tier={tier} det_verdict={verdict} cache_miss=True",
        flush=True,
    )

    # Language subjects (English / Ona Tili / Rus Tili) use a different rubric
    # (Language Mastery Rubric — Form Accuracy + Communication Effectiveness)
    # because AMR's "name the rule + show steps" anchors don't fit language
    # production. Lookup is in services/language.py.
    from . import language as _lang
    use_language_rubric = _lang.is_language_subject(subject)
    prompt_name = "answer-checker-language" if use_language_rubric else "answer-checker"
    prompt = _load_runtime_prompt(prompt_name)
    # Caller can request 2-axis rubric scoring by setting answer_spec.amr=true
    # (or implicitly via type="semantic" — open-ended responses always benefit
    # from rubric grading). The prompts have opt-in sections that emit
    # axis_1/axis_2 when amr_mode is true in the input payload.
    #
    # An EXPLICIT `amr: false` is honored even when type="semantic" — used by
    # the reading-checkpoint phase on non-language subjects, where we still
    # need semantic meaning-matching but don't want a "name-the-rule" rubric.
    _amr_explicit = answer_spec.get("amr")
    if _amr_explicit is False:
        amr_requested = False
    elif _amr_explicit is True:
        amr_requested = True
    else:
        amr_requested = answer_spec.get("type") == "semantic"
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
        "feedback": "Short string, 1-2 sentences (matches student's language)",
        "matched_expected": "string or null",
        "confidence": "float between 0 and 1",
    }
    if amr_requested:
        if use_language_rubric:
            # LMR v2: meaning-similarity gate decides correct/incorrect; axes
            # evaluate quality of expression (Grammatical Accuracy + Lexical
            # Quality). Task achievement is implicit in the gate, not in axes.
            schema.update({
                "axis_1": "integer 1..4 (Grammatical Accuracy)",
                "axis_2": "integer 1..4 (Lexical Quality)",
                "axis_1_label": "Mastered|Proficient|Apprentice|Novice",
                "axis_2_label": "Mastered|Proficient|Apprentice|Novice",
            })
        else:
            schema.update({
                "axis_1": "integer 1..4 (Concept Identification)",
                "axis_2": "integer 1..4 (Process Integrity)",
                "axis_1_label": "Mastered|Proficient|Apprentice|Novice",
                "axis_2_label": "Mastered|Proficient|Apprentice|Novice",
            })
    # PR 1 — bloat-fix: sanitize+cap before LLM, fall back when unavailable.
    try:
        input_section = ai_orchestrator.build_input_section(payload)
        prompt_size = len(f"{prompt}\n\n{input_section}")
        ai_response = await ai_orchestrator.generate_json(
            f"{prompt}\n\n{input_section}",
            schema_hint=schema,
            model=ai_orchestrator.FAST_MODEL,
        )
    except (ai_orchestrator.PromptTooLargeError, RuntimeError) as exc:
        _log.warning(
            "check_answer AI fallback unavailable (%s: %s); marking unavailable",
            exc.__class__.__name__,
            exc,
        )
        return ai_debug.with_context_debug(
            {
                "correct": False,
                "score": 0.0,
                "feedback": "AI baholash hozir mavjud emas — qayta urinib ko'ring.",
                "source": "ai_unavailable",
                "matched_expected": None,
                "ai_unavailable": True,
            },
            {
                "service": "tutor.check_answer",
                "checker_path": "ai_judge",
                "provider": ai_orchestrator._active_backend(),
                "model": ai_orchestrator.FAST_MODEL,
                "answer_spec_type": answer_spec.get("type"),
                "result_action": "ai_unavailable",
                "ai_unavailable": True,
            },
            route="service.check_answer",
        )

    confidence = float(ai_response.get("confidence", 1.0))
    if confidence >= 0.90:
        ai_response["source"] = "ai"
        await db.set_answer_cache(cache_key, ai_response)
        return ai_debug.with_context_debug(
            ai_response,
            {
                "service": "tutor.check_answer",
                "checker_path": "ai_judge",
                "provider": ai_orchestrator._active_backend(),
                "model": ai_orchestrator.FAST_MODEL,
                "answer_spec_type": answer_spec.get("type"),
                "confidence": confidence,
                "prompt_size": prompt_size,
                "result_action": "accepted",
            },
            route="service.check_answer",
        )
    else:
        # Low confidence
        needs_review = True
        if _is_boss(question_id, phase):
            res = {
                "correct": True,
                "score": 0.7,
                "feedback": ai_response.get("feedback", "Javobingiz tekshirilmoqda..."),
                "source": "ai_unsure",
                "needs_review": True,
                "matched_expected": None
            }
        else:
            res = {
                "correct": False,
                "score": 0.0,
                "feedback": ai_response.get("feedback", "Javobingizni tushunmadim, qayta urinib ko'ring."),
                "source": "ai_unsure",
                "needs_review": True,
                "matched_expected": None
            }

        # Preserve AMR axes from the AI response on the low-confidence path so
        # the scorecard still gets axis data even when the verdict is unsure.
        for k in ("axis_1", "axis_2", "axis_1_label", "axis_2_label"):
            if k in ai_response:
                res[k] = ai_response[k]

        await db.add_to_review_queue(question_id, student_answer, answer_spec, ai_response)
        return ai_debug.with_context_debug(
            res,
            {
                "service": "tutor.check_answer",
                "checker_path": "ai_judge",
                "provider": ai_orchestrator._active_backend(),
                "model": ai_orchestrator.FAST_MODEL,
                "answer_spec_type": answer_spec.get("type"),
                "confidence": confidence,
                "prompt_size": prompt_size,
                "result_action": "review_candidate",
            },
            route="service.check_answer",
        )


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

    Security note: `expected_answers` is NEVER forwarded to the LLM. Correctness
    is computed server-side via `_was_correct_normalized` and the LLM receives
    only `was_correct: bool`. This closes the prompt-injection leak surface
    where a crafted boss-turn message could trick the model into echoing the
    raw expected answers back to the student. AMR axes (concept identification
    + process integrity) are still graded by the LLM since they evaluate the
    student's *reasoning shown*, not the answer value.
    """
    prompt = _load_runtime_prompt("boss-tutor")
    was_correct = _was_correct_normalized(student_answer, expected_answers or [])
    payload = {
        "boss_question": boss_question,
        "student_answer": student_answer,
        "was_correct": was_correct,
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

    # AMR 2-axis grading is REQUIRED for every Final Boss attack — the rubric
    # specifically measures Concept Identification + Process Integrity on
    # multi-step reasoning, which is exactly what Boss Q3-Q5 demand. Always
    # pass amr_mode=true so the prompt emits the extended JSON shape with
    # axis_1/axis_2; the runtime aggregator picks them up from the result.
    payload["amr_mode"] = True

    schema = {
        "correct": "bool — must equal was_correct from input",
        "damage_dealt": "int (damage_value if was_correct else 0)",
        "boss_response": "Uzbek string, in-character boss, 1 sentence",
        "hint": "Uzbek string or null (null if attempt 1 or if was_correct)",
        "score": "float 0-1",
        "axis_1": "integer 1..4 (Concept Identification)",
        "axis_2": "integer 1..4 (Process Integrity)",
        "axis_1_label": "Mastered|Proficient|Apprentice|Novice",
        "axis_2_label": "Mastered|Proficient|Apprentice|Novice",
    }
    # PR 1 — AI grading bloat fix. Sanitize+size-cap the payload before it hits
    # the LLM; on PromptTooLargeError or any provider failure, fall back to a
    # synthetic response keyed off `was_correct` so the runtime sees the right
    # verdict instead of a silent 500.
    try:
        input_section = ai_orchestrator.build_input_section(payload)
        result = await ai_orchestrator.generate_json(
            f"{prompt}\n\n{input_section}",
            schema_hint=schema,
            model=ai_orchestrator.PRO_MODEL,  # boss uses stronger model
        )
    except (ai_orchestrator.PromptTooLargeError, RuntimeError) as exc:
        _log.warning(
            "boss_turn AI call unavailable (%s: %s); returning synthetic verdict",
            exc.__class__.__name__,
            exc,
        )
        return _boss_turn_ai_unavailable(was_correct, damage_value)

    # Authoritative correctness + damage come from the server-side check.
    # Override whatever the model returned to keep scoring deterministic and
    # prevent a prompt-injection from flipping the outcome (in either direction
    # — student-flipping-correct-to-true OR a confused LLM dealing 0 damage on
    # a correct answer). Axes (axis_1/axis_2) are LEFT untouched: those grade
    # the student's process, not the answer value.
    if isinstance(result, dict):
        result["correct"] = was_correct
        result["damage_dealt"] = int(damage_value) if was_correct else 0
    return result


def _boss_turn_ai_unavailable(was_correct: bool, damage_value: int) -> dict:
    """Synthetic boss-turn response when the LLM is unavailable.

    Server-computed `was_correct` (from `_was_correct_normalized`) is the
    authoritative verdict; the runtime's bossHandleResponse already trusts
    `correct` + `damage_dealt` as canonical (Batch A FB-1 fix). Boss line
    surfaces a polite "AI tafsiloti yo'q" note rather than a silent fail.
    Axes are neutralised so the report card still renders meaningfully.
    """
    if was_correct:
        boss_response = "To'g'ri! 🛡️ (AI tafsiloti vaqtinchalik mavjud emas — keyinroq qayta urinib ko'ring.)"
        score = 1.0
        axis = 3
        axis_label = "Proficient"
    else:
        boss_response = "Hali emas. 🌀 (AI tafsiloti vaqtinchalik mavjud emas — qayta urinib ko'ring.)"
        score = 0.0
        axis = 1
        axis_label = "Novice"
    return {
        "correct": was_correct,
        "damage_dealt": int(damage_value) if was_correct else 0,
        "boss_response": boss_response,
        "hint": None,
        "score": score,
        "axis_1": axis,
        "axis_2": axis,
        "axis_1_label": axis_label,
        "axis_2_label": axis_label,
        "ai_unavailable": True,
    }


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
    # PR 1 — bloat-fix: synthesize canned encouragement if LLM unavailable.
    try:
        input_section = ai_orchestrator.build_input_section(payload)
        return await ai_orchestrator.generate_json(
            f"{prompt}\n\n{input_section}",
            schema_hint=schema,
            model=ai_orchestrator.FAST_MODEL,
        )
    except (ai_orchestrator.PromptTooLargeError, RuntimeError) as exc:
        _log.warning(
            "reflection_feedback AI unavailable (%s: %s); returning canned response",
            exc.__class__.__name__,
            exc,
        )
        return {
            "feedback": (
                "Bugungi mashg'ulot uchun rahmat. Sizning urinishingiz qadrli — "
                "har bir mashq bilan miyangiz mustahkamroq bo'ladi."
            ),
            "next_steps": [
                "Asosiy fikrlarni qisqacha o'qib chiqing",
                "Ertaga yana bir mashq bilan davom eting",
            ],
            "encouragement": "Muvaffaqiyat tilaymiz!",
            "ai_unavailable": True,
        }


# ---------------------------------------------------------------------------
# Wave F1 — live tutor chat + boss-plan
# ---------------------------------------------------------------------------


# Keys we allow from question payloads before they enter the LLM context for
# practice/boss phases. Bridge B (answer-leak prevention) fails closed:
# Tutor redaction primitives now live in tutor_redaction.py (the single
# source of truth shared with ai_context.py - see backend-integration-audit
# finding #1). Re-export here so existing imports (from server.services.tutor
# import _redact_question_for_tutor and the frozensets) keep working.
from .tutor_redaction import (  # noqa: E402, F401
    _TUTOR_CONTEXT_SAFE_KEYS,
    _TUTOR_CONTEXT_CBP_EXTRA_KEYS,
    _PHASE_SAFE_KEYS,
    _redact_question_for_tutor,
)


def _format_history_for_prompt(turns: list[dict]) -> str:
    """Render recent chat turns as compact lines for the tutor prompt.

    Each turn's content is fenced as untrusted data because the student-side
    turns are user-controlled and could otherwise re-inject on every request.
    """
    lines: list[str] = []
    for t in turns:
        role = t.get("role", "")
        content = t.get("content", "")
        # Fence both roles uniformly — the model is told to treat anything
        # inside the fence as data, regardless of who "spoke" it.
        lines.append(f"{role}: {_fence_untrusted(content)}")
    return "\n".join(lines)


def _build_tutor_chat_prompt(
    *,
    system_prompt: str,
    phase: str,
    subject: str,
    grade: int,
    question_text: str,
    question_context: Optional[dict],
    screen_context: Optional[str] = None,
    student_attempt: Optional[str] = None,
    subphase: Optional[str] = None,
    student_profile: Optional[str],
    persona_traits: Optional[list[str]],
    chat_history: list[dict],
    student_message: str,
    # Wave J warning fields — optional, defaults preserve backward compat
    severity: str = "casual_safe",
    warning_level: int = 0,
    cumulative_deduction_pct: int = 0,
    is_big_warning: bool = False,
    deduction_pct_this: int = 0,
    behavior_summary: str = "",
    message_lang: str = "uz",
    recent_assistant_phrases: Optional[list[str]] = None,
    # Plan 3 — missing context flags
    missing_context_flags: Optional[list[str]] = None,
    metrics: Optional[dict] = None,
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
    if question_context:
        parts.append(
            "QUESTION_CONTEXT:\n"
            + json.dumps(question_context, ensure_ascii=False, indent=2)
        )
    if subphase:
        parts.append(f"SUBPHASE: {subphase}")
    if student_attempt:
        parts.append(f"STUDENT_ATTEMPT:\n{_fence_untrusted(student_attempt)}")
    if screen_context:
        parts.append(f"SCREEN_CONTEXT:\n{_fence_untrusted(screen_context)}")
    if student_profile:
        parts.append(f"STUDENT_PROFILE:\n{student_profile}")
    if persona_traits:
        parts.append(f"PERSONA_TRAITS: {', '.join(persona_traits)}")
    # Wave J — warning context block (omit when severity is clean and no history)
    if severity not in ("casual_safe",) or warning_level > 0:
        parts.append(
            f"WARNING_CONTEXT:\n"
            f"  severity: {severity}\n"
            f"  warning_level: {warning_level}/9\n"
            f"  cumulative_deduction_pct: {cumulative_deduction_pct}%\n"
            f"  this_event_deduction_pct: {deduction_pct_this}%\n"
            f"  is_big_warning: {is_big_warning}"
        )
    if behavior_summary:
        parts.append(f"BEHAVIOR_HISTORY:\n{behavior_summary}")
    if recent_assistant_phrases:
        parts.append(
            "RECENT_OPENINGS (you said these recently — DO NOT echo):\n"
            + "\n".join(f"  - {p}" for p in recent_assistant_phrases)
        )
    if metrics:
        parts.append(
            "PERFORMANCE:\n"
            + json.dumps(metrics, ensure_ascii=False, indent=2)
        )
    if missing_context_flags:
        parts.append(
            "MISSING_CONTEXT_FLAGS:\n"
            + "\n".join(f"  - {f}" for f in missing_context_flags)
        )
    parts.append(f"MESSAGE_LANG: {message_lang}  # mirror this in your reply")
    parts.append(
        "CHAT_HISTORY:\n" + (_format_history_for_prompt(chat_history) or "(none)")
    )
    parts.append(f"STUDENT_MESSAGE:\n{_fence_untrusted(student_message)}")
    return "\n\n".join(parts)


async def tutor_chat_v2(
    context: ai_context.TutorContextPacket,
    message: str,
    # Wave J warning fields
    severity: str = "casual_safe",
    warning_level: int = 0,
    cumulative_deduction_pct: int = 0,
    is_big_warning: bool = False,
    deduction_pct_this: int = 0,
    behavior_summary: str = "",
    message_lang: str = "uz",
    recent_assistant_phrases: Optional[list[str]] = None,
) -> dict:
    """Live tutor chat v2 — accepts a canonical context packet.

    Persists the user turn, calls the LLM, persists the assistant turn.
    """
    _validate_session_id(context.session_id)
    _validate_phase(context.phase)

    # Step 1 — enforce the per-session cap BEFORE writing the user turn.
    total = await db.count_session_messages(context.session_id, context.hw_id)
    if total >= SESSION_MESSAGE_CAP:
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

    # Step 2 — persist the user turn.
    await db.add_tutor_turn(
        session_id=context.session_id,
        hw_id=context.hw_id,
        phase=context.phase,
        question_id=context.current_question_id,
        role="user",
        content=message,
    )

    # Step 3 — chat history.
    chat_history = await db.list_tutor_turns(
        context.session_id,
        context.hw_id,
        limit=TUTOR_CHAT_HISTORY_WINDOW,
        most_recent=True,
    )

    # Step 4 — build the prompt.
    system_prompt = _load_runtime_prompt("tutor-assistant")

    full_prompt = _build_tutor_chat_prompt(
        system_prompt=system_prompt,
        phase=context.phase,
        subject=context.subject,
        grade=context.grade,
        question_text=context.current_question_text,
        question_context=context.current_question_context,
        screen_context=context.visible_screen_text or None,
        student_attempt=context.student_work_text or None,
        subphase=context.subphase,
        student_profile=None,
        persona_traits=None,
        chat_history=chat_history,
        student_message=message,
        severity=severity,
        warning_level=warning_level,
        cumulative_deduction_pct=cumulative_deduction_pct,
        is_big_warning=is_big_warning,
        deduction_pct_this=deduction_pct_this,
        behavior_summary=behavior_summary,
        message_lang=message_lang,
        recent_assistant_phrases=recent_assistant_phrases,
        missing_context_flags=context.missing_context_flags or None,
        metrics=context.metrics or None,
    )

    # Step 5 — call the LLM through the canonical gateway.
    gateway_task = ai_gateway.AITask.TUTOR_CHAT
    gateway_task_status = ai_gateway.get_status().get("tasks", {}).get(gateway_task.value, {})
    provider = gateway_task_status.get("provider")
    model = gateway_task_status.get("model")

    _PROMPT_SIZE_CAP = 60000
    prompt_cap_exceeded = False
    if len(full_prompt) > _PROMPT_SIZE_CAP:
        prompt_cap_exceeded = True
        _log.warning(
            "tutor.chat prompt %s chars exceeds cap %s; returning canned reply",
            len(full_prompt),
            _PROMPT_SIZE_CAP,
        )
        response_text = (
            "Hozir bu savolga javob bera olmayman — kontekst juda katta. "
            "Iltimos, qisqaroq savol bilan qayta urinib ko'ring."
        )
    else:
        try:
            response_text = await ai_gateway.generate_text(
                task=gateway_task,
                prompt=full_prompt,
                session_id=context.session_id,
                homework_id=context.hw_id,
                prompt_version="tutor-assistant:v2",
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": _scrub_provider_error(exc),
                    "code": "TUTOR_BACKEND_ERROR",
                },
            ) from exc

    # Strip any <UNTRUSTED> fence tags the LLM may have mirrored back.
    response_text = _strip_fence_tags(response_text)

    # Step 6 — persist the assistant turn and return.
    asst_turn_id = await db.add_tutor_turn(
        session_id=context.session_id,
        hw_id=context.hw_id,
        phase=context.phase,
        question_id=context.current_question_id,
        role="assistant",
        content=response_text,
    )
    return ai_debug.with_context_debug(
        {"response": response_text, "message_id": asst_turn_id},
        {
            "service": "tutor.tutor_chat",
            "phase": context.phase,
            "subphase": context.subphase,
            "question_id_present": ai_debug.present(context.current_question_id),
            "question_found": bool(context.current_question_text),
            "question_text_len": ai_debug.text_len(context.current_question_text),
            "screen_context_forwarded_len": ai_debug.text_len(context.visible_screen_text),
            "screen_context_clean_len": ai_debug.text_len(context.visible_screen_text),
            "student_work_text_len": ai_debug.text_len(context.student_work_text),
            "chat_history_count": len(chat_history),
            "provider": provider,
            "model": model,
            "prompt_size": len(full_prompt),
            "prompt_cap": _PROMPT_SIZE_CAP,
            "prompt_cap_exceeded": prompt_cap_exceeded,
            "fallback_status": "prompt_too_large" if prompt_cap_exceeded else "llm_success",
        },
        route="service.tutor_chat",
    )


async def tutor_chat(
    session_id: str,
    hw_id: str,
    phase: str,
    question_id: Optional[str],
    message: str,
    hw_meta: Optional[dict] = None,
    # Wave J warning fields
    severity: str = "casual_safe",
    warning_level: int = 0,
    cumulative_deduction_pct: int = 0,
    is_big_warning: bool = False,
    deduction_pct_this: int = 0,
    behavior_summary: str = "",
    message_lang: str = "uz",
    recent_assistant_phrases: Optional[list[str]] = None,
    # Wave J.2 — new context fields
    screen_context: Optional[str] = None,
    student_work_text: Optional[str] = None,
    subphase: Optional[str] = None,
) -> dict:
    """Legacy wrapper — builds a minimal context packet and delegates to v2."""
    hw_meta = hw_meta or {}

    # Build a minimal context packet from legacy arguments.
    question_dict = hw_meta.get("question") if isinstance(hw_meta.get("question"), dict) else None
    redacted = _redact_question_for_tutor(question_dict, phase) if question_dict else {}
    question_text = (
        redacted.get("q")
        or redacted.get("prompt")
        or redacted.get("question")
        or ""
    )

    expected_value: Optional[str] = None
    if question_dict:
        ans_spec = question_dict.get("answer_spec")
        if isinstance(ans_spec, dict):
            ev = ans_spec.get("expected")
            if isinstance(ev, str):
                expected_value = ev
    screen_clean = _sanitize_screen_context(screen_context, expected_value)

    context = ai_context.TutorContextPacket(
        session_id=session_id,
        hw_id=hw_id,
        phase=phase,
        subphase=subphase,
        current_question_id=question_id,
        subject=str(hw_meta.get("subject", "")),
        grade=int(hw_meta.get("grade", 0) or 0),
        homework_title="",
        current_question_text=question_text,
        current_question_context=redacted if redacted else None,
        visible_screen_text=screen_clean,
        student_work_text=str(student_work_text or ""),
        recent_chat_history=[],
        recent_attempts=[],
        metrics={},
        warnings_summary="",
        missing_context_flags=[],
    )

    return await tutor_chat_v2(
        context=context,
        message=message,
        severity=severity,
        warning_level=warning_level,
        cumulative_deduction_pct=cumulative_deduction_pct,
        is_big_warning=is_big_warning,
        deduction_pct_this=deduction_pct_this,
        behavior_summary=behavior_summary,
        message_lang=message_lang,
        recent_assistant_phrases=recent_assistant_phrases,
    )


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
        return ai_debug.with_context_debug(
            {"ordered": [], "persona_traits": ["mentor"]},
            {
                "service": "tutor.boss_plan",
                "mode": "fixed_boss",
                "boss_questions_count": 0,
                "question_source": "content_json",
                "provider": None,
                "model": None,
                "fallback_status": "empty_boss_pool",
            },
            route="service.boss_plan",
        )

    student_profile = await db.build_session_profile(session_id, hw_id)

    # Normalize the LLM input. Strip any answer-bearing keys from the boss-Q
    # payload — the planner doesn't need the answers.
    sanitized_questions = [_redact_question_for_tutor(q, "boss") for q in boss_questions]

    try:
        system_prompt = _load_runtime_prompt("tutor-boss-plan")
    except FileNotFoundError:
        return ai_debug.with_context_debug(
            _default_boss_plan(boss_questions),
            {
                "service": "tutor.boss_plan",
                "mode": "fixed_boss",
                "boss_questions_count": len(boss_questions),
                "question_source": "content_json",
                "provider": None,
                "model": None,
                "fallback_status": "prompt_missing",
            },
            route="service.boss_plan",
        )

    payload = {
        "BOSS_QUESTIONS": sanitized_questions,
        "STUDENT_PROFILE": student_profile or "(empty)",
    }
    schema = {
        "ordered": "array of {question_id: string, framing_text: string (<=180 chars)}",
        "persona_traits": "array with at least one of: challenger, mentor, analyst",
    }
    # PR 1 — bloat-fix: sanitize+cap. Existing fallback to _default_boss_plan
    # already handles LLM failures; PromptTooLargeError follows the same path.
    try:
        input_section = ai_orchestrator.build_input_section(payload)
        full_prompt = f"{system_prompt}\n\n{input_section}"
        ai_response = await ai_orchestrator.generate_json(
            full_prompt,
            schema_hint=schema,
            model=ai_orchestrator.PRO_MODEL,
        )
    except Exception as exc:  # noqa: BLE001 — we want every LLM hiccup caught.
        print(f"[boss_plan] LLM failed; using default plan: {exc}", flush=True)
        return ai_debug.with_context_debug(
            _default_boss_plan(boss_questions),
            {
                "service": "tutor.boss_plan",
                "mode": "fixed_boss",
                "boss_questions_count": len(boss_questions),
                "question_source": "content_json",
                "provider": ai_orchestrator._active_backend(),
                "model": ai_orchestrator.PRO_MODEL,
                "fallback_status": "llm_unavailable",
                "ai_unavailable": True,
            },
            route="service.boss_plan",
        )

    cleaned = _validate_boss_plan(ai_response, boss_questions)
    if cleaned is None:
        return ai_debug.with_context_debug(
            _default_boss_plan(boss_questions),
            {
                "service": "tutor.boss_plan",
                "mode": "fixed_boss",
                "boss_questions_count": len(boss_questions),
                "question_source": "content_json",
                "provider": ai_orchestrator._active_backend(),
                "model": ai_orchestrator.PRO_MODEL,
                "fallback_status": "invalid_llm_plan",
            },
            route="service.boss_plan",
        )
    return ai_debug.with_context_debug(
        cleaned,
        {
            "service": "tutor.boss_plan",
            "mode": "fixed_boss",
            "boss_questions_count": len(boss_questions),
            "question_source": "content_json",
            "provider": ai_orchestrator._active_backend(),
            "model": ai_orchestrator.PRO_MODEL,
            "prompt_size": len(full_prompt),
            "fallback_status": "llm_success",
        },
        route="service.boss_plan",
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
        # AMR axes on every tutor exchange: when a student types in the chat
        # widget during practice or boss, the runtime aggregator captures
        # axis_1/axis_2 alongside the coaching response so chat attempts
        # also feed the report card.
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
    # PR 1 — bloat-fix: synthesize a polite "try again" if LLM unavailable.
    try:
        input_section = ai_orchestrator.build_input_section(payload)
        return await ai_orchestrator.generate_json(
            f"{prompt}\n\n{input_section}",
            schema_hint=schema,
            model=ai_orchestrator.FAST_MODEL,
        )
    except (ai_orchestrator.PromptTooLargeError, RuntimeError) as exc:
        _log.warning(
            "tutor_help AI unavailable (%s: %s); returning canned response",
            exc.__class__.__name__,
            exc,
        )
        return {
            "response": (
                "Hozir javob bera olmayman — bir oz vaqtdan keyin qayta urinib ko'ring."
            ),
            "guidance_type": "encouragement",
            "axis_1": 1,
            "axis_2": 1,
            "axis_1_label": "Novice",
            "axis_2_label": "Novice",
            "ai_unavailable": True,
        }




async def process_runtime_answer(target: dict, student_answer: str, attempt_number: int = 1) -> dict:
    """
    Grading ladder: Deterministic -> Phase Checker -> AI Judge.
    Returns standard unified contract dict.
    
    Tiered Confidence Policy:
    - confidence >= 0.90: Trust score directly (is_correct = score >= 0.70)
    - confidence >= 0.75: Trust score, flag medium confidence (is_correct = score >= 0.70)
    - confidence >= 0.60: Partial trust, force is_correct=False but keep score
    - confidence < 0.60: Fallback to review queue, score=0
    
    The score >= 0.70 boundary for binary correctness indicates a high
    degree of semantic match without requiring perfection.
    """
    import json
    from . import answer_checker
    from ..db.attempts_repo import add_phase_attempt

    is_correct = False
    score = 0.0
    confidence = 1.0
    feedback = ""
    misconception_tags = []
    next_hint = ""
    grading_method = ""
    requires_review = False

    session_id = target.get("session_id", "")
    if session_id:
        _validate_session_id(session_id)
        
    hw_id = target.get("homework_id", "")
    phase = target.get("phase", "")
    subphase = target.get("subphase", "")
    question_id = target.get("question_id", "")
    item_id = target.get("item_id", "")
    step_id = target.get("step_id", "")
    answer_spec = target.get("answer_spec") or {}
    expected_answers = target.get("expected_answers", [])

    # 1. Deterministic
    det_result = answer_checker.check(answer_spec, student_answer)
    verdict = det_result.get("verdict")
    
    if verdict == "correct":
        is_correct = True
        score = 1.0
        confidence = 1.0
        grading_method = "deterministic"
        feedback = det_result.get("format_tip") or "To'g'ri!"
    elif verdict == "incorrect":
        is_correct = False
        score = 0.0
        confidence = 1.0
        grading_method = "deterministic"
        feedback = det_result.get("reason", "Hali emas, qayta urinib ko'ring.")
    else:
        # 3. AI Judge
        # Route through the gateway for canonical model policy, telemetry, and retries
        # while preserving the tiered confidence policy in this runtime layer.
        grading_method = "ai_judge"
        try:
            # Decide which prompt to use based on target info
            answer_type = target.get("answer_type", "text")
            
            prompt_name = "answer-checker-language"
            if "math" in answer_type or "math" in target.get("subject", "").lower():
                prompt_name = "answer-checker-math"
            if target.get("phase") == "final-boss":
                prompt_name = "answer-checker-boss"
                
            prompt = _load_runtime_prompt(prompt_name)
            
            payload = {
                "question": target.get("question_text", ""),
                "student_answer": student_answer,
                "expected_answers": expected_answers,
                "answer_spec": answer_spec,
            }
            
            input_section = ai_orchestrator.build_input_section(payload)
            ai_response = await ai_gateway.generate_structured(
                task=ai_gateway.AITask.ANSWER_CHECK,
                prompt=f"{prompt}\n\n{input_section}",
                schema=AnswerCheckResult,
                session_id=session_id,
                homework_id=hw_id,
                prompt_version=f"{prompt_name}:runtime",
            )
            ai_res = ai_response.model_dump()
            
            raw_score = float(ai_res.get("score", 0.0))
            raw_confidence = float(ai_res.get("confidence", 1.0))
            raw_feedback = ai_res.get("feedback", "")
            misconception_tags = ai_res.get("misconception_tags", [])
            next_hint = ai_res.get("next_hint", "")
            feedback = raw_feedback
            
            # Tiered Confidence Policy
            if raw_confidence >= 0.90:
                is_correct = raw_score >= 0.70
                score = raw_score
                confidence = raw_confidence
                requires_review = False
            elif raw_confidence >= 0.75:
                is_correct = raw_score >= 0.70
                score = raw_score
                confidence = raw_confidence
                requires_review = False
                misconception_tags.append("medium_confidence")
            elif raw_confidence >= 0.60:
                is_correct = False
                score = raw_score
                confidence = raw_confidence
                requires_review = False
            else:
                is_correct = False
                score = 0.0
                confidence = raw_confidence
                requires_review = True
        except Exception as e:
            _log.error("AI Judge failed: %s", e)
            is_correct = False
            score = 0.0
            confidence = 0.0
            requires_review = True
            grading_method = "error"
            feedback = "Tizim xatosi, iltimos qayta urinib ko'ring."

    normalized_res = {
        "ok": True,
        "grading_method": grading_method,
        "is_correct": is_correct,
        "score": score,
        "confidence": confidence,
        "feedback": feedback,
        "misconception_tags": misconception_tags,
        "next_hint": next_hint,
        "requires_review": requires_review,
        "attempt_number": attempt_number
    }

    # d. (Chunk E) After grading, save the attempt to the DB
    try:
        await add_phase_attempt(
            session_id=session_id,
            hw_id=hw_id,
            phase=phase,
            checker_source=grading_method,
            subphase=subphase,
            question_id=question_id,
            item_id=item_id,
            step_id=step_id,
            attempt_number=attempt_number,
            student_answer=student_answer,
            normalized_answer=None,
            answer_spec_json=json.dumps(answer_spec) if answer_spec else None,
            correct=1 if is_correct else 0,
            score=score,
            confidence=confidence,
            feedback=feedback,
            misconception_tags_json=json.dumps(misconception_tags) if misconception_tags else None,
            time_ms=None
        )
    except Exception as e:
        _log.error("Failed to add phase attempt: %s", e)
        raise

    return normalized_res
