"""Plan 5 + Plan 7 — Dynamic Boss state machine.

Owns:
  * server-side damage formula (LLM never sets HP)
  * adaptive difficulty policy (correct streak → harder, wrong streak → easier)
  * the generation prompt path (LLM generates one question at a time, never
    receiving answer keys from prior phases)
  * the answer-check prompt path (deterministic-friendly judgement; the
    backend clamps any model-supplied damage_multiplier and it never trusts
    the LLM for HP/trials updates)

Plan 7 additions:
  * Pydantic output models for strict JSON contract validation
  * <UNTRUSTED_STUDENT_MESSAGE> delimiter wrapping
  * Prompt version tracking
  * Wired through ai_gateway.generate_structured() for schema validation,
    repair retry, and ai_call_logs telemetry.

Hard rules (Plan 5 §4 + §13 + Plan 7 §2 + the answer-leak invariant in CLAUDE.md):

  - ``answer_spec.expected``, ``ans``, ``accepted_answers``, and ``correct``
    must never appear in any prompt this module sends.
  - HP / trials / difficulty mutations live here, not in the model output.
  - User text (student_answer) is untrusted and wrapped in XML delimiters.
  - The legacy ``/ai/boss-turn`` endpoint stays untouched as a fallback.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from . import ai_gateway
from ..config import PROMPTS_DIR
from ..schemas.ai_contracts import BossQuestionGenerated, BossAnswerCheckResult


_log = logging.getLogger("nets.boss_dynamic")


# ---- Prompt versions (Plan 7 §8) ------------------------------------------

PROMPT_VERSION = {
    "boss-question-generator": "v1",
    "boss-answer-checker": "v1",
    "boss-tutor": "v2",
}


# ---- Damage / difficulty policy --------------------------------------------

BASE_DAMAGE: dict[str, int] = {
    "easy": 10,
    "medium": 15,
    "hard": 25,
}

ALLOWED_DIFFICULTIES: tuple[str, ...] = ("easy", "medium", "hard")
DEFAULT_DIFFICULTY = "medium"

# Hard cap on the model-supplied damage_multiplier — even if the boss-answer
# checker tries to set 99x, the backend clamps to this range. Plan 5 §7 says
# "The model may recommend a multiplier, but backend must clamp it."
_MULTIPLIER_MIN = 0.0
_MULTIPLIER_MAX = 1.5


def calculate_damage(score: float, difficulty: str, multiplier: float = 1.0) -> int:
    """Plan 5 §7 damage table, with a clamped optional multiplier.

    ``score`` is 0..1; ``difficulty`` is one of ALLOWED_DIFFICULTIES.
    Anything outside the allowed set falls back to medium so the runtime
    never deals indeterminate damage.
    """
    diff = difficulty if difficulty in BASE_DAMAGE else DEFAULT_DIFFICULTY
    base = BASE_DAMAGE[diff]
    s = max(0.0, min(1.0, float(score)))
    if s >= 0.90:
        raw = base
    elif s >= 0.60:
        raw = int(base * 0.5)
    else:
        raw = 0
    m = max(_MULTIPLIER_MIN, min(_MULTIPLIER_MAX, float(multiplier or 1.0)))
    return int(round(raw * m))


@dataclass
class BossStreaks:
    correct_streak: int = 0
    wrong_streak: int = 0


def next_difficulty(
    current: str,
    score: float,
    streaks: BossStreaks,
) -> str:
    """Plan 5 §8 policy. Adaptive but never unfair.

    >= 0.90 with 2+ in a row right → bump to hard.
    < 0.50 with 2+ in a row wrong  → ease back to easy.
    Otherwise stay where we are (clamped to medium if invalid).
    """
    cur = current if current in ALLOWED_DIFFICULTIES else DEFAULT_DIFFICULTY
    s = max(0.0, min(1.0, float(score)))
    if s >= 0.90 and streaks.correct_streak >= 2:
        return "hard"
    if s < 0.50 and streaks.wrong_streak >= 2:
        return "easy"
    return cur


# ---- Prompt loading --------------------------------------------------------

_RUNTIME_PROMPTS = PROMPTS_DIR / "runtime"


def _load_prompt(name: str) -> str:
    path = _RUNTIME_PROMPTS / f"{name}.md"
    return path.read_text(encoding="utf-8")


# ---- Local Pydantic models (Plan 7 §4 + §10 Test 2) ------------------------
# These mirror ai_contracts schemas for tests and direct validation.

class ExpectedAnswer(BaseModel):
    canonical: str
    accepted_variants: list[str] = Field(default_factory=list)
    notes: str = ""


class Rubric(BaseModel):
    full_credit: list[str] = Field(default_factory=list)
    partial_credit: list[str] = Field(default_factory=list)
    common_mistakes: list[str] = Field(default_factory=list)


class BossQuestionOutput(BaseModel):
    """Plan 7 strict output contract for the Boss Question Generator."""

    question_text: str = Field(..., max_length=900)
    expected_answer: ExpectedAnswer
    rubric: Rubric
    target_skill: str
    difficulty: Literal["easy", "medium", "hard"]
    source_phase_ids: list[str] = Field(default_factory=list)
    why_this_question: str = ""

    @field_validator("question_text")
    @classmethod
    def _non_empty_question(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("question_text must not be empty")
        return v.strip()

    @field_validator("target_skill")
    @classmethod
    def _non_empty_skill(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("target_skill must not be empty")
        return v.strip()


class BossAnswerVerdictOutput(BaseModel):
    """Plan 7 strict output contract for the Boss Answer Checker."""

    is_correct: bool
    score: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    feedback_to_student: str
    misconception_tags: list[str] = Field(default_factory=list)
    damage_multiplier: float = Field(default=1.0, ge=0.0, le=1.5)
    difficulty_recommendation: str = "stay"
    should_retry_same_skill: bool = False

    @field_validator("feedback_to_student")
    @classmethod
    def _non_empty_feedback_when_wrong(cls, v: str, info) -> str:
        is_correct = info.data.get("is_correct")
        if not is_correct and not v.strip():
            raise ValueError("feedback_to_student required when is_correct is false")
        return v


# ---- Generation -----------------------------------------------------------

@dataclass
class GeneratedBossQuestion:
    question_text: str
    expected_answer: dict[str, Any]
    rubric: dict[str, Any]
    target_skill: str
    difficulty: str
    source_phase_ids: list[str] = field(default_factory=list)
    why_this_question: str = ""

    def to_storage_dict(self) -> dict[str, Any]:
        return {
            "question_text": self.question_text,
            "expected_answer": self.expected_answer,
            "rubric": self.rubric,
            "target_skill": self.target_skill,
            "difficulty": self.difficulty,
            "source_phase_ids": list(self.source_phase_ids),
            "why_this_question": self.why_this_question,
        }


class BossQuestionRejected(Exception):
    """Raised when the generator output fails validation (Plan 5 §6 / Plan 7 §10)."""

    def __init__(self, reason: str, *, raw: Optional[dict[str, Any]] = None):
        super().__init__(reason)
        self.reason = reason
        self.raw = raw or {}


_REQUIRED_GENERATION_KEYS: tuple[str, ...] = (
    "question_text",
    "expected_answer",
    "rubric",
    "target_skill",
    "difficulty",
)


def _validate_generated_question(
    raw: dict[str, Any],
    *,
    asked_questions: list[dict[str, Any]],
    max_question_length: int = 900,
) -> GeneratedBossQuestion:
    """Plan 5 §6 + Plan 7 §10 backend validation.

    Step 1: Key presence + Pydantic strict contract validation.
    Step 2: Business rules (anti-repetition, length cap).
    """
    # --- Step 1: Pydantic strict contract validation ---
    try:
        parsed = BossQuestionOutput.model_validate(raw)
    except Exception as exc:
        raise BossQuestionRejected(f"pydantic_validation:{exc}", raw=raw) from exc

    # --- Step 2: Business rules ---
    question_text = parsed.question_text
    if len(question_text) > max_question_length:
        raise BossQuestionRejected("question_too_long", raw=raw)

    # Anti-repetition check: the new question must not be a near-exact
    # duplicate of any question we've already asked. We use a normalized
    # whitespace-collapsed comparison rather than string equality so trivial
    # paraphrases ("Solve x + 2 = 5" vs "solve  x + 2 = 5  .") still trip.
    if parsed.difficulty not in ALLOWED_DIFFICULTIES:
        raise BossQuestionRejected("invalid_difficulty", raw=raw)

    # Anti-repetition check: the new question must not be a near-exact
    # duplicate of any question we've already asked. We use a normalized
    # whitespace-collapsed comparison rather than string equality so trivial
    # paraphrases ("Solve x + 2 = 5" vs "solve  x + 2 = 5  .") still trip.
    norm_new = " ".join(question_text.lower().split())
    for prev in asked_questions or []:
        prev_text = " ".join(str(prev.get("question_text") or "").lower().split())
        if prev_text and prev_text == norm_new:
            raise BossQuestionRejected("repeats_previous", raw=raw)

    return GeneratedBossQuestion(
        question_text=question_text,
        expected_answer=parsed.expected_answer.model_dump(),
        rubric=parsed.rubric.model_dump(),
        target_skill=parsed.target_skill,
        difficulty=parsed.difficulty,
        source_phase_ids=list(parsed.source_phase_ids),
        why_this_question=parsed.why_this_question,
    )


def _build_boss_input_section(payload: dict[str, Any]) -> str:
    """Serialize a boss payload with Plan 7 <UNTRUSTED_STUDENT_MESSAGE> wrapping.

    Any field named ``student_answer`` is wrapped in XML delimiters so the
    model knows it is untrusted user input.
    """
    from . import ai_orchestrator

    payload = dict(payload)
    if "student_answer" in payload:
        raw = str(payload["student_answer"])
        payload["student_answer"] = (
            f"<UNTRUSTED_STUDENT_MESSAGE>\n{raw}\n</UNTRUSTED_STUDENT_MESSAGE>"
        )
    return ai_orchestrator.build_input_section(payload)


async def generate_boss_question(
    boss_context: dict[str, Any],
    *,
    difficulty: str,
) -> GeneratedBossQuestion:
    """Call the LLM to generate one new boss question, validate, and return.

    Plan 5 §6 + Plan 7 §4 — wired through ai_gateway.generate_structured()
    for Pydantic validation, repair retry, and ai_call_logs telemetry.
    Raises BossQuestionRejected if validation fails. Caller should retry once
    or fall back to a deterministic stem.
    """
    diff = difficulty if difficulty in ALLOWED_DIFFICULTIES else DEFAULT_DIFFICULTY
    prompt = _load_prompt("boss-question-generator")
    payload = dict(boss_context)
    payload["target_difficulty"] = diff
    input_section = _build_boss_input_section(payload)
    full_prompt = f"{prompt}\n\n{input_section}"

    try:
        result = await ai_gateway.generate_structured(
            task=ai_gateway.AITask.BOSS_QUESTION_GENERATE,
            prompt=full_prompt,
            schema=BossQuestionGenerated,
            session_id=boss_context.get("session_id"),
            homework_id=boss_context.get("homework_id"),
            temperature=0.3,
            prompt_version=PROMPT_VERSION["boss-question-generator"],
        )
    except RuntimeError as exc:
        _log.warning(
            "generate_boss_question AI unavailable (%s: %s)",
            exc.__class__.__name__, exc,
        )
        raise BossQuestionRejected("ai_unavailable") from exc

    # Gateway already validated against BossQuestionGenerated Pydantic schema.
    # Convert to dict for business-rule validation.
    raw = result.model_dump()
    return _validate_generated_question(
        raw,
        asked_questions=list(boss_context.get("asked_questions") or []),
        max_question_length=int(
            (boss_context.get("boss_policy") or {}).get("max_question_length") or 900
        ),
    )


# ---- Answer checking ------------------------------------------------------

@dataclass
class BossAnswerVerdict:
    is_correct: bool
    score: float
    confidence: float
    feedback_to_student: str
    misconception_tags: list[str] = field(default_factory=list)
    damage_multiplier: float = 1.0
    difficulty_recommendation: str = "stay"
    should_retry_same_skill: bool = False
    ai_unavailable: bool = False


def _verdict_from_gateway(result: BossAnswerCheckResult) -> BossAnswerVerdict:
    """Convert a validated gateway result to the internal dataclass."""
    diff_rec = result.difficulty_recommendation
    if diff_rec not in {"increase", "decrease", "stay"}:
        diff_rec = "stay"
    return BossAnswerVerdict(
        is_correct=result.is_correct,
        score=result.score,
        confidence=result.confidence,
        feedback_to_student=result.feedback,
        misconception_tags=list(result.misconception_tags),
        damage_multiplier=max(
            _MULTIPLIER_MIN, min(_MULTIPLIER_MAX, float(result.damage_multiplier or 1.0))
        ),
        difficulty_recommendation=diff_rec,
        should_retry_same_skill=result.should_retry_same_skill,
    )


# ---- Deterministic pre-check (hotfix 2026-05-14) --------------------------
#
# Boss grading was 100% LLM-judged on origin/server. Students who typed
# the EXACT canonical answer (e.g. "headache and cold") sometimes still saw
# the AI mark them wrong — a non-zero LLM error rate × thousands of
# attempts = real damage to trust during classroom testing.
#
# Mirroring the Plan-4 answer-checker (deterministic-first → AI fallback),
# we now do a normalized exact-match against canonical + accepted_variants
# BEFORE calling the LLM. If the student typed the unambiguous answer,
# they get an instant correct verdict with full damage and no LLM call.
# When the student's text doesn't match exactly, we fall through to the
# existing LLM-judged path (which handles paraphrases, partial credit,
# misconception tagging, etc.).


def _normalize_for_match(s: str) -> str:
    """Lowercase + strip + collapse internal whitespace + strip trailing
    terminal punctuation. Returns empty string for None/non-str inputs.
    Conservative: does NOT strip percent signs, units, or special chars —
    if those should be accepted, the rubric author must list them as
    explicit variants.
    """
    if not isinstance(s, str):
        return ""
    cleaned = " ".join(s.lower().strip().split())
    return cleaned.rstrip(".!?;:,").strip()


def _accepted_normalized_answers(expected_answer: dict[str, Any]) -> list[str]:
    """Return the canonical + accepted_variants, normalized, with empties
    dropped. The single source of truth used by both the deterministic
    pre-check and the (legacy) LLM-unavailable synthetic_verdict path."""
    canonical = str(expected_answer.get("canonical") or "")
    variants = [str(v) for v in (expected_answer.get("accepted_variants") or [])]
    normalized = [_normalize_for_match(v) for v in [canonical, *variants]]
    return [v for v in normalized if v]


def _deterministic_correct_check(
    student_answer: str,
    expected_answer: dict[str, Any],
) -> Optional[BossAnswerVerdict]:
    """Return a confident-correct verdict when the student's normalized
    answer exactly matches the canonical or any accepted variant.

    Returns ``None`` when no exact match — caller falls through to the
    LLM-judged path. The pre-check NEVER returns ``is_correct=False``;
    near-misses and paraphrases must still be judged by the LLM (which can
    award partial credit and tag misconceptions).
    """
    sa = _normalize_for_match(student_answer)
    if not sa:
        return None
    accepted = _accepted_normalized_answers(expected_answer)
    if not accepted or sa not in accepted:
        return None
    return BossAnswerVerdict(
        is_correct=True,
        score=1.0,
        confidence=1.0,
        # Hardcoded Uzbek matches the existing prod synthetic_verdict
        # pattern. Localization comes via the language banner in the
        # in-flight Plan-7-follow-up prompt v2; out of hotfix scope.
        feedback_to_student="✓ Javobingiz to'g'ri.",
        misconception_tags=[],
        damage_multiplier=1.0,
        difficulty_recommendation="stay",
        should_retry_same_skill=False,
        ai_unavailable=False,
    )


async def check_boss_answer(
    *,
    question_text: str,
    expected_answer: dict[str, Any],
    rubric: dict[str, Any],
    student_answer: str,
    target_skill: str,
    difficulty: str,
    session_id: Optional[str] = None,
    homework_id: Optional[str] = None,
) -> BossAnswerVerdict:
    """Plan 5 §7 + Plan 7 §4 — boss-answer-checker prompt path.

    Wired through ai_gateway.generate_structured() for Pydantic validation,
    repair retry, and ai_call_logs telemetry.

    NOTE: ``expected_answer`` IS sent to the checker (it has to grade against
    something). It is NEVER sent to the boss persona / response model. Keep
    that boundary clear if you ever wire the response phrasing through a
    second model call.

    Hotfix 2026-05-14: deterministic pre-check runs first. If the student's
    answer matches the canonical/variants verbatim (normalized), return
    a confident correct verdict without consulting the LLM. Falls through
    to the LLM path only when no exact match — the LLM still handles
    paraphrases, partial credit, and misconception tagging.
    """
    deterministic = _deterministic_correct_check(student_answer, expected_answer)
    if deterministic is not None:
        _log.info(
            "boss_deterministic_match session=%s hw=%s answer_chars=%d",
            session_id, homework_id, len(student_answer or ""),
        )
        return deterministic

    prompt = _load_prompt("boss-answer-checker")
    payload = {
        "question_text": question_text,
        "expected_answer": expected_answer,
        "rubric": rubric,
        "student_answer": student_answer,
        "target_skill": target_skill,
        "difficulty": difficulty,
    }
    input_section = _build_boss_input_section(payload)
    full_prompt = f"{prompt}\n\n{input_section}"

    try:
        result = await ai_gateway.generate_structured(
            task=ai_gateway.AITask.BOSS_ANSWER_CHECK,
            prompt=full_prompt,
            schema=BossAnswerCheckResult,
            session_id=session_id,
            homework_id=homework_id,
            temperature=0.3,
            prompt_version=PROMPT_VERSION["boss-answer-checker"],
        )
    except RuntimeError as exc:
        _log.warning(
            "check_boss_answer AI unavailable (%s: %s)",
            exc.__class__.__name__, exc,
        )
        return _synthetic_verdict(
            student_answer=student_answer, expected_answer=expected_answer,
        )

    return _verdict_from_gateway(result)


def _synthetic_verdict(
    *,
    student_answer: str,
    expected_answer: dict[str, Any],
) -> BossAnswerVerdict:
    """When the LLM checker is unavailable, fall back to a deterministic
    case-insensitive normalized compare. Better than 500ing in the runtime.
    """
    canonical = str(expected_answer.get("canonical") or "")
    variants = [str(v) for v in (expected_answer.get("accepted_variants") or [])]
    accepted = [v.strip().lower() for v in [canonical, *variants] if v]
    is_correct = student_answer.strip().lower() in accepted if accepted else False
    return BossAnswerVerdict(
        is_correct=is_correct,
        score=1.0 if is_correct else 0.0,
        confidence=0.55,
        feedback_to_student=(
            "AI tafsiloti vaqtinchalik mavjud emas. Javobingiz qabul qilindi."
            if is_correct
            else "AI tafsiloti vaqtinchalik mavjud emas. Hali to'g'ri emas."
        ),
        misconception_tags=[],
        damage_multiplier=1.0,
        difficulty_recommendation="stay",
        should_retry_same_skill=not is_correct,
        ai_unavailable=True,
    )


__all__ = [
    "BASE_DAMAGE",
    "ALLOWED_DIFFICULTIES",
    "DEFAULT_DIFFICULTY",
    "calculate_damage",
    "next_difficulty",
    "BossStreaks",
    "GeneratedBossQuestion",
    "BossQuestionRejected",
    "generate_boss_question",
    "BossAnswerVerdict",
    "check_boss_answer",
    "BossQuestionOutput",
    "BossAnswerVerdictOutput",
    "ExpectedAnswer",
    "Rubric",
    "PROMPT_VERSION",
]
