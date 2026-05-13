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
from difflib import SequenceMatcher
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from . import ai_gateway
from ..config import PROMPTS_DIR
from ..schemas.ai_contracts import BossQuestionGenerated, BossAnswerCheckResult
from .boss_context_builder import _DIFFICULTY_RANK


_log = logging.getLogger("nets.boss_dynamic")


# ---- Prompt versions (Plan 7 §8) ------------------------------------------

PROMPT_VERSION = {
    "boss-question-generator": "v2",
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


# ---- Per-skill difficulty floor (Plan Wave 2) ------------------------------
# 0.40 is a provisional empirical threshold for difflib.SequenceMatcher.ratio()
# matching a generator's `target_skill` to an authored stem's question_text +
# tags. Revisit after 20+ live calls — too low lets unrelated skills inherit
# a stem's floor; too high makes the floor effectively unreachable and the
# pool_max fallback dominates.
_SKILL_MATCH_THRESHOLD = 0.40


def _match_skill_to_stem(
    target_skill: str,
    stems: list[dict],
) -> Optional[dict]:
    """Best-effort fuzzy match of generator's target_skill to an authored stem.

    Compares ``target_skill`` against ``(question_text + tags)`` of each stem
    via ``difflib.SequenceMatcher.ratio()``. Returns the stem with highest
    score when score >= 0.40 (empirical floor; revisit after 20+ live calls).
    Returns None if pool empty, target_skill empty, or no stem clears
    threshold.
    """
    if not target_skill or not stems:
        return None
    target = target_skill.lower().strip()
    if not target:
        return None
    best_score, best_stem = 0.0, None
    for stem in stems:
        haystack = (
            (stem.get("question_text", "") or "")
            + " "
            + (stem.get("tags", "") or "")
        ).lower()
        if not haystack.strip():
            continue
        score = SequenceMatcher(None, target, haystack[:300]).ratio()
        if score > best_score:
            best_score, best_stem = score, stem
    return best_stem if best_score >= _SKILL_MATCH_THRESHOLD else None


def _resolve_skill_floor(
    target_skill: str,
    stems: list[dict],
    pool_max: Optional[str],
) -> Optional[str]:
    """Returns the difficulty floor for the generated question's target_skill.

    Per-stem match → that stem's ``authored_difficulty``. No clear match →
    ``pool_max`` as fallback (per design intent: 'default to pool's maximum
    when target_skill doesn't clearly map to any stem'). Returns ``None`` when
    the pool is empty.
    """
    matched = _match_skill_to_stem(target_skill, stems)
    if matched:
        return matched.get("authored_difficulty")
    return pool_max


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
    stems: Optional[list[dict[str, Any]]] = None,
    pool_max: Optional[str] = None,
    max_question_length: int = 900,
) -> GeneratedBossQuestion:
    """Plan 5 §6 + Plan 7 §10 + Plan Wave 2 backend validation.

    Step 1: Key presence + Pydantic strict contract validation.
    Step 2: Business rules (anti-repetition, length cap).
    Step 3: Per-skill difficulty floor (when stems / pool_max provided).
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

    if parsed.difficulty not in ALLOWED_DIFFICULTIES:
        raise BossQuestionRejected("invalid_difficulty", raw=raw)

    # Anti-repetition: reject when the new question is too similar to any
    # already-asked one. Strict equality (the original implementation) missed
    # near-paraphrases — Kimi could change one number, swap punctuation, or
    # tweak word order and still ship "the same question" from a student's POV.
    # SequenceMatcher.ratio() on whitespace-collapsed lowercase strings gives a
    # 0..1 similarity score; 0.85 is high enough to allow legitimate topical
    # overlap (two different absolute-error problems on different inputs) but
    # low enough to catch paraphrases. BossQuestionRejected triggers the
    # gateway repair retry so Kimi gets one chance to regenerate.
    _DUP_SIMILARITY_THRESHOLD = 0.85
    norm_new = " ".join(question_text.lower().split())
    for prev in asked_questions or []:
        prev_text = " ".join(str(prev.get("question_text") or "").lower().split())
        if not prev_text:
            continue
        if prev_text == norm_new:
            raise BossQuestionRejected("repeats_previous", raw=raw)
        similarity = SequenceMatcher(None, prev_text, norm_new).ratio()
        if similarity >= _DUP_SIMILARITY_THRESHOLD:
            raise BossQuestionRejected(
                f"repeats_previous: similarity={similarity:.2f} >= "
                f"{_DUP_SIMILARITY_THRESHOLD}",
                raw=raw,
            )

    # --- Step 3: Per-skill difficulty floor (Plan Wave 2) ---
    # Each authored stem carries an authored_difficulty. We allow the
    # generated question to drop AT MOST one rank below the matched stem's
    # floor (floor=hard → {medium,hard}; floor=medium → {easy,medium,hard};
    # floor=easy → no extra constraint). When target_skill doesn't clearly
    # match any stem, we fall back to pool_max as the floor.
    floor = _resolve_skill_floor(parsed.target_skill, stems or [], pool_max)
    if floor:
        floor_rank = _DIFFICULTY_RANK[floor]
        gen_rank = _DIFFICULTY_RANK[parsed.difficulty]
        if gen_rank < floor_rank - 1:
            raise BossQuestionRejected(
                f"difficulty_below_skill_floor: target_skill={parsed.target_skill!r} "
                f"matched_stem_floor={floor!r} generated={parsed.difficulty!r}",
                raw=raw,
            )

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

    Plan 5 §6 + Plan 7 §4 + Plan Wave 2 — wired through
    ``ai_gateway.generate_structured()`` for Pydantic validation, repair
    retry, and ai_call_logs telemetry. After the gateway returns we run the
    per-skill difficulty floor check; on persistent floor violation we
    hard-clamp the generated difficulty up to the floor (better UX than
    502-ing the runtime).

    Raises ``BossQuestionRejected`` if neither generation nor clamp can
    salvage the call (empty anchor context, AI unavailable, anti-repetition,
    Pydantic, etc.). Caller should retry once or fall back to a deterministic
    stem.
    """
    # --- Empty-pool guard (Plan Wave 2 §G) ---
    # If we have neither authored stems nor phase summaries, the generator
    # has no anchor context and would hallucinate an off-topic skill. Bail
    # before paying the LLM call.
    stems = list(boss_context.get("authored_question_stems") or [])
    phases = list(boss_context.get("phase_summaries") or [])
    if not stems and not phases:
        raise BossQuestionRejected("no_anchor_context")
    pool_max = boss_context.get("authored_difficulty_floor")

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
    # Convert to dict for business-rule validation (anti-repetition, length,
    # per-skill difficulty floor).
    raw = result.model_dump()
    asked = list(boss_context.get("asked_questions") or [])
    max_qlen = int(
        (boss_context.get("boss_policy") or {}).get("max_question_length") or 900
    )

    try:
        return _validate_generated_question(
            raw,
            asked_questions=asked,
            stems=stems,
            pool_max=pool_max,
            max_question_length=max_qlen,
        )
    except BossQuestionRejected as exc:
        # Hard-clamp on persistent floor violation. The gateway already
        # consumed its one repair retry on Pydantic schema, so the LLM is
        # not getting another shot. Clamping the difficulty up to the floor
        # is preferable to surfacing a 502 to the runtime.
        if (
            exc.reason.startswith("difficulty_below_skill_floor")
            and exc.raw
            and (stems or pool_max)
        ):
            clamped_raw = dict(exc.raw)
            target_skill_str = str(clamped_raw.get("target_skill") or "")
            actual_floor = (
                _resolve_skill_floor(target_skill_str, stems, pool_max) or pool_max
            )
            clamped_raw["difficulty"] = actual_floor
            _log.warning(
                "boss_difficulty_clamped_after_repair_fail: target_skill=%r forced to %r",
                target_skill_str, actual_floor,
            )
            # Re-validate with stems=None / pool_max=None so the floor check
            # is skipped (we just enforced it ourselves). Anti-repetition,
            # length, and Pydantic checks still run.
            return _validate_generated_question(
                clamped_raw,
                asked_questions=asked,
                stems=None,
                pool_max=None,
                max_question_length=max_qlen,
            )
        raise


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
    """
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
