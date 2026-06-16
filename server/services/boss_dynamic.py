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
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from . import ai_gateway, ai_orchestrator
from ..config import PROMPTS_DIR
from ..schemas.ai_contracts import BossQuestionGenerated, BossAnswerCheckResult
from .boss_context_builder import (
    _DIFFICULTY_RANK,
    _ENGLISH_INDICATOR_WORDS,  # re-export for back-compat with existing tests
    _detect_language_drift,    # re-export — canonical home is boss_context_builder
    _strip_html_tags,          # Bug A defense-in-depth for generated question_text
)


_log = logging.getLogger("nets.boss_dynamic")


# ---- Prompt versions (Plan 7 §8) ------------------------------------------

PROMPT_VERSION = {
    # boss-question-generator bumped to v7 (grade-appropriate depth guardrail):
    #   v7 — prevents easy/medium grade 6-8 prompts from asking for exact
    #     molecule counts or exhaustive biochemical product lists unless the
    #     authored stems explicitly require that level of detail.
    #   v6 — Boss-Arena Why→How→What rework:
    #   v6 — emits structured scenario + why/how/what reasoning prompts
    #     (spec §4/§9) IN ADDITION to the existing fields. question_text stays
    #     the composite headline used for anti-repetition + display.
    "boss-question-generator": "v7",
    # boss-answer-checker bumped 2026-05-14:
    #   v2 (Bug B) — front-loaded language banner so feedback is written in
    #     the homework's language and misconception_tags avoid English
    #     snake_case on uz/ru lessons.
    #   v3 (Bug C) — added "Semantic equivalence" rule 1a so grammatically
    #     correct variants are accepted even when surface form differs from
    #     the canonical. Protects students from generator-side rubric typos
    #     (e.g. "Does he have to come?" being rejected because the LLM-built
    #     rubric expected literal "has to").
    #   v4 (Boss-Arena) — scores per-axis ``coverage`` (why/how/what, 0..1)
    #     for coverage-based grading (spec §6). Feedback still never reveals
    #     the canonical answer.
    "boss-answer-checker": "v4",
    "boss-tutor": "v2",
}


# ---- Damage / difficulty policy --------------------------------------------

# Boss-Arena spec §6 base damage table (was 10/15/25 before the Why→How→What
# rework). Aligned to the authoring convention (`_dmg_to_difficulty` already
# maps authored dmg 10→easy / 20→medium / 30→hard) so server damage and
# author-supplied damage now agree.
BASE_DAMAGE: dict[str, int] = {
    "easy": 10,    # spec §6
    "medium": 20,  # spec §6
    "hard": 30,    # spec §6
}

ALLOWED_DIFFICULTIES: tuple[str, ...] = ("easy", "medium", "hard")
DEFAULT_DIFFICULTY = "medium"

# Hard cap on the model-supplied damage_multiplier — even if the boss-answer
# checker tries to set 99x, the backend clamps to this range. Plan 5 §7 says
# "The model may recommend a multiplier, but backend must clamp it."
_MULTIPLIER_MIN = 0.0
_MULTIPLIER_MAX = 1.5

# Defensive floors enforced when the LLM verdict has ``is_correct=true``.
# Without these, the model can return is_correct=true + score<0.60 (or
# damage_multiplier<1.0) and the student sees "✓ To'g'ri! −0 HP" because
# calculate_damage's score<0.60 branch returns raw=0. Floor enforced in
# _verdict_from_gateway. See 2026-05-14 audit bug #2.
_CORRECT_SCORE_FLOOR = 0.60       # matches calculate_damage's half-damage threshold
_CORRECT_MULTIPLIER_FLOOR = 1.0   # neutral default; sub-1.0 modifier on a correct answer is nonsensical


# ---- Coverage-based grading helpers (Boss-Arena spec §6) -------------------

_COVERAGE_AXES: tuple[str, ...] = ("why", "how", "what")

# Combo bonus (spec §6): N consecutive full-accuracy correct answers entering
# a roll grant a +20% damage bonus. The threshold + factor live here so the
# route layer and the tests reference one source of truth.
COMBO_STREAK_THRESHOLD = 3
COMBO_BONUS_FACTOR = 1.2


def coverage_mean(coverage: Optional[dict]) -> Optional[float]:
    """Mean of the present why/how/what numeric coverage values.

    Boss-Arena spec §6 grades reasoning coverage across the three axes. Only
    axes actually present (and numeric) count toward the mean, so a verdict
    that scored just {"why": 0.8, "what": 0.6} averages those two. Returns
    None when no usable axis is present (caller falls back to ``score``).
    """
    if not coverage:
        return None
    vals: list[float] = []
    for axis in _COVERAGE_AXES:
        v = coverage.get(axis)
        if isinstance(v, bool):  # guard: bool is an int subclass in Python
            continue
        if isinstance(v, (int, float)):
            vals.append(max(0.0, min(1.0, float(v))))
    if not vals:
        return None
    return sum(vals) / len(vals)


def accuracy_tier(value: float) -> float:
    """Boss-Arena spec §6 accuracy tiers from a 0..1 coverage/score value.

        >= 0.85 -> 1.0
        >= 0.55 -> 0.7
        >= 0.30 -> 0.5
        else    -> 0.0
    """
    v = max(0.0, min(1.0, float(value)))
    if v >= 0.85:
        return 1.0
    if v >= 0.55:
        return 0.7
    if v >= 0.30:
        return 0.5
    return 0.0


def hint_penalty(hints_used: int) -> float:
    """Boss-Arena spec §6 hint multiplier. More hints -> less damage.

        0 hints -> 1.0
        1 hint  -> 0.8
        2 hints -> 0.6
        3+      -> 0.3
    """
    try:
        n = int(hints_used)
    except (TypeError, ValueError):
        n = 0
    return {0: 1.0, 1: 0.8, 2: 0.6}.get(n, 0.3)


def calculate_damage(
    score: float,
    difficulty: str,
    multiplier: float = 1.0,
    *,
    coverage: Optional[dict] = None,
    hints_used: int = 0,
    combo_bonus: float = 1.0,
) -> int:
    """Boss-Arena spec §6 damage: base × accuracy × hint × multiplier × combo.

    ``score`` is 0..1; ``difficulty`` is one of ALLOWED_DIFFICULTIES.
    Anything outside the allowed set falls back to medium so the runtime
    never deals indeterminate damage.

    Accuracy is derived from coverage when present (mean of the why/how/what
    axes), else from the legacy single ``score`` — both run through the spec
    §6 accuracy tiers (``accuracy_tier``). This preserves backward-compat:
    callers passing only (score, difficulty, multiplier) with no coverage get
    the spec-tier behavior off ``score``.

    INVARIANT (spec §6 + this PR's contract): an ``is_correct`` answer always
    deals > 0 damage. A "correct but weak" answer (coverage_mean in
    [0.30, 0.85)) tiers to accuracy >= 0.5, so raw = base * 0.5 > 0. A wrong
    answer (accuracy 0.0) deals 0. The is_correct floors in
    ``_verdict_from_gateway`` keep the input above the 0.30 tier boundary.
    """
    diff = difficulty if difficulty in BASE_DAMAGE else DEFAULT_DIFFICULTY
    base = BASE_DAMAGE[diff]

    accuracy_input = coverage_mean(coverage) if coverage else score
    if accuracy_input is None:  # coverage present but no usable axis
        accuracy_input = score
    accuracy = accuracy_tier(accuracy_input)
    raw = base * accuracy

    m = max(_MULTIPLIER_MIN, min(_MULTIPLIER_MAX, float(multiplier or 1.0)))
    hp = hint_penalty(hints_used)
    cb = max(0.0, float(combo_bonus or 1.0))
    return int(round(raw * m * hp * cb))


# ---- Grade-band starting HP (server-authoritative, Boss-Arena spec) --------
#
# HP is derived server-side from the homework's grade band, not trusted from
# the client. Keys cover the spec's three bands; ``starting_hp_for`` also
# accepts the schema's ``GradeBand`` literals (g1_4 / g5 / g6_8 / g9_11) and a
# raw integer grade, normalizing them to one of these three buckets.
HP_BY_GRADE_BAND: dict[str, int] = {
    "G1-4": 50,
    "G5-8": 100,
    "G9-11": 150,
}
_DEFAULT_STARTING_HP = 100
_MIN_VALID_HP = 10  # mirrors BossMeta.starting_hp_override validator floor


def _normalize_grade_band(grade_band: Optional[Any]) -> Optional[str]:
    """Map any supported grade-band representation to an HP_BY_GRADE_BAND key.

    Accepts:
      * the canonical keys ("G1-4", "G5-8", "G9-11"), case/format tolerant;
      * the schema GradeBand literals ("g1_4", "g5", "g6_8", "g9_11");
      * a raw integer grade (or numeric string) 1..11.
    Returns None when nothing maps (caller falls back to default HP).
    """
    if grade_band is None:
        return None

    # Numeric grade → band.
    try:
        g = int(str(grade_band).strip())
        if 1 <= g <= 4:
            return "G1-4"
        if 5 <= g <= 8:
            return "G5-8"
        if g >= 9:
            return "G9-11"
        return None
    except (TypeError, ValueError):
        pass

    token = str(grade_band).strip().lower().replace(" ", "")
    # Schema GradeBand literals.
    schema_map = {
        "g1_4": "G1-4",
        "g5": "G5-8",
        "g6_8": "G5-8",
        "g9_11": "G9-11",
    }
    if token in schema_map:
        return schema_map[token]
    # Canonical keys, format-tolerant ("g1-4", "g1_4", "g14" all collapse).
    canonical_map = {
        "g1-4": "G1-4", "g1_4": "G1-4",
        "g5-8": "G5-8", "g5_8": "G5-8",
        "g9-11": "G9-11", "g9_11": "G9-11",
    }
    return canonical_map.get(token)


def starting_hp_for(grade_band: Optional[Any], override: Optional[int]) -> int:
    """Server-authoritative starting HP for a boss session.

    Precedence: a valid override (int >= _MIN_VALID_HP) wins; else the band's
    HP; else the default (100). The override floor matches BossMeta's
    ``starting_hp_override`` validator so authoring + runtime agree.
    """
    if override is not None:
        try:
            ov = int(override)
            if ov >= _MIN_VALID_HP:
                return ov
        except (TypeError, ValueError):
            pass
    band_key = _normalize_grade_band(grade_band)
    if band_key is not None:
        return HP_BY_GRADE_BAND[band_key]
    return _DEFAULT_STARTING_HP


# ---- End-of-boss outcome / stars / XP scoring (Bug #5 fix, 2026-05-14) -----
#
# The runtime template expects `outcome` / `stars` / `outcome_xp` on the
# /boss/submit-answer response when the arc is over, and falls back to
# 'passing' / 0 / 0 when missing. Prior to this commit the server never
# emitted them — students saw "+0 XP" and 0 stars even after answering
# every question correctly.

def compute_boss_outcome(
    *,
    hp: int,
    max_hp: int,
    correct_count: int,
    total_attempts: int,
    hints_used: int,
    status: str,
) -> dict[str, Any]:
    """Return ``{outcome, stars, outcome_xp}`` for a terminal boss session.

    ``hp`` is the remaining BOSS HP, not the student's retained HP. Lower is
    better: ``0`` means the boss was defeated. Tier thresholds combine
    correctness with fight progress, so a clean victory earns the visible
    "expert" result instead of being misread as "0 HP retained."

        - 3 stars / expert: won AND correctness >= 0.80
        - 2 stars / strong: won AND correctness >= 0.60
        - 1 star  / passing: won OR correctness >= 0.50
        - 0 stars / hali_emas: failed AND correctness < 0.50

    XP formula: 50 per correct + int(progress_ratio * 100) bonus - 25 per hint.
    Floored at 0 so a wholly empty session never produces negative XP.
    """
    won = (status == "won")
    if total_attempts <= 0:
        return {"outcome": "hali_emas", "stars": 0, "outcome_xp": 0}

    correctness = correct_count / total_attempts
    progress_ratio = ((max_hp - max(0, hp)) / max_hp) if max_hp > 0 else 0.0
    progress_ratio = max(0.0, min(1.0, progress_ratio))

    if won and correctness >= 0.80:
        stars = 3
    elif won and correctness >= 0.60:
        stars = 2
    elif won or correctness >= 0.50:
        stars = 1
    else:
        stars = 0

    outcome = {3: "expert", 2: "strong", 1: "passing", 0: "hali_emas"}[stars]

    xp = 50 * correct_count + int(progress_ratio * 100) - 25 * hints_used
    xp = max(0, xp)

    return {"outcome": outcome, "stars": stars, "outcome_xp": xp}


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
# Bug #8 fix (2026-05-13 audit): the original implementation used only
# SequenceMatcher.ratio() between target_skill (often a short snake_case
# token like "sign_error", ~10 chars) and a 300-char stem haystack. The
# length asymmetry tanked the ratio — 16 of 36 live generations had
# target_skill="sign_error" and none matched any authored Uzbek stem, all
# falling back to pool_max. We now combine token-overlap (Jaccard on
# significant tokens) with SequenceMatcher and take the max. Token-overlap
# is robust to length asymmetry; SequenceMatcher still catches partial
# variations. Threshold 0.40 stays: legitimate matches now score 0.5–1.0.
_SKILL_MATCH_THRESHOLD = 0.40
_SKILL_TOKEN_MIN_LEN = 3  # ignore noise tokens like "a", "of", suffixes


def _tokenize_skill(s: str) -> set[str]:
    """Split a skill string on whitespace, underscore, hyphen; keep tokens
    of length >= _SKILL_TOKEN_MIN_LEN. Lowercased.
    """
    if not s:
        return set()
    return {
        t for t in re.split(r"[\s_\-]+", s.lower().strip())
        if len(t) >= _SKILL_TOKEN_MIN_LEN
    }


def _match_skill_to_stem(
    target_skill: str,
    stems: list[dict],
) -> Optional[dict]:
    """Best-effort fuzzy match of generator's target_skill to an authored stem.

    Hybrid score: max of (token-overlap fraction, SequenceMatcher.ratio).
    Token-overlap counts how many significant tokens from target_skill appear
    in (question_text + tags). Robust to length asymmetry where short
    target tokens get crushed by a long stem haystack. Returns the highest-
    scoring stem when score >= _SKILL_MATCH_THRESHOLD, else None.
    """
    if not target_skill or not stems:
        return None
    target = target_skill.lower().strip()
    if not target:
        return None
    target_tokens = _tokenize_skill(target_skill)
    best_score, best_stem = 0.0, None
    for stem in stems:
        haystack = (
            (stem.get("question_text", "") or "")
            + " "
            + (stem.get("tags", "") or "")
        ).lower()
        if not haystack.strip():
            continue
        # Token-overlap score: fraction of significant target tokens present
        # as substrings of haystack. Substring (not whole-word) keeps Uzbek
        # morphology working — "xatolik" should match "xatoligini".
        if target_tokens:
            hits = sum(1 for t in target_tokens if t in haystack)
            token_score = hits / len(target_tokens)
        else:
            token_score = 0.0
        seq_score = SequenceMatcher(None, target, haystack[:300]).ratio()
        score = max(token_score, seq_score)
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
    """Plan 7 strict output contract for the Boss Question Generator.

    Boss-Arena Why→How→What (spec §4/§9): ``scenario`` + the three reasoning
    prompts (``why`` / ``how`` / ``what``) default to "" so legacy single-
    field generations still validate. ``question_text`` remains the composite
    headline used for anti-repetition + display fallback; when the model
    returns the structured parts but leaves question_text empty, the
    generation path composes one (see ``_compose_question_text``).
    """

    question_text: str = Field(default="", max_length=900)
    scenario: str = ""
    why: str = ""
    how: str = ""
    what: str = ""
    expected_answer: ExpectedAnswer
    rubric: Rubric
    target_skill: str
    difficulty: Literal["easy", "medium", "hard"]
    source_phase_ids: list[str] = Field(default_factory=list)
    why_this_question: str = ""

    @field_validator("question_text")
    @classmethod
    def _strip_question(cls, v: str) -> str:
        # Strip only — emptiness vs. the structured parts is reconciled in the
        # model_validator below (the model may legitimately fill only
        # scenario/why/how/what).
        return (v or "").strip()

    @field_validator("target_skill")
    @classmethod
    def _non_empty_skill(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("target_skill must not be empty")
        return v.strip()

    @model_validator(mode="after")
    def _has_some_question_content(self) -> "BossQuestionOutput":
        # A valid generation must carry SOME question content: either a
        # populated question_text OR at least one of the structured
        # scenario/why/how/what parts. A wholly-empty output is rejected so
        # the Pydantic-level contract still guards against blank questions.
        if self.question_text.strip():
            return self
        if any(p.strip() for p in (self.scenario, self.why, self.how, self.what)):
            return self
        raise ValueError(
            "question_text must not be empty unless scenario/why/how/what "
            "are populated"
        )
        return self


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
    # Boss-Arena Why→How→What structured shape (spec §4/§9). PROMPT text only;
    # safe to surface to the client. Empty strings on legacy single-field gens.
    scenario: str = ""
    why: str = ""
    how: str = ""
    what: str = ""

    def to_storage_dict(self) -> dict[str, Any]:
        return {
            "question_text": self.question_text,
            "scenario": self.scenario,
            "why": self.why,
            "how": self.how,
            "what": self.what,
            "expected_answer": self.expected_answer,
            "rubric": self.rubric,
            "target_skill": self.target_skill,
            "difficulty": self.difficulty,
            "source_phase_ids": list(self.source_phase_ids),
            "why_this_question": self.why_this_question,
        }


def _compose_question_text(
    *, question_text: str, scenario: str, why: str, how: str, what: str,
) -> str:
    """Build a readable composite headline from the structured parts.

    Boss-Arena (spec §4/§9): when the generator returns scenario + the three
    reasoning prompts but leaves question_text blank, we synthesize a single
    display/anti-repetition string. When question_text is already populated we
    keep it verbatim (back-compat with legacy single-field generations).
    """
    qt = (question_text or "").strip()
    if qt:
        return qt
    parts: list[str] = []
    if scenario and scenario.strip():
        parts.append(scenario.strip())
    for prompt in (why, how, what):
        if prompt and prompt.strip():
            parts.append(prompt.strip())
    return "\n\n".join(parts).strip()


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
    expected_language: Optional[str] = None,
) -> GeneratedBossQuestion:
    """Plan 5 §6 + Plan 7 §10 + Plan Wave 2 backend validation.

    Step 1: Key presence + Pydantic strict contract validation.
    Step 2: Business rules (anti-repetition, length cap, language drift).
    Step 3: Per-skill difficulty floor (when stems / pool_max provided).
    """
    # --- Step 1: Pydantic strict contract validation ---
    try:
        parsed = BossQuestionOutput.model_validate(raw)
    except Exception as exc:
        raise BossQuestionRejected(f"pydantic_validation:{exc}", raw=raw) from exc

    # --- Step 2: Business rules ---
    # Bug A (2026-05-14): defense-in-depth strip of any HTML tags the LLM
    # echoed from authored stems (or invented on its own). The runtime
    # renders question_text via textContent (XSS guard), so any `<strong>`
    # / `<em>` etc. would otherwise appear as literal characters. We use
    # the stripped value from here on — length check, anti-repetition, and
    # the returned GeneratedBossQuestion all see clean text. Authored stems
    # are stripped upstream in build_boss_context as well.
    #
    # Boss-Arena Why→How→What (spec §4/§9): the generator may emit a
    # scenario + the three reasoning prompts and leave question_text blank.
    # Strip HTML on each structured part, then compose a readable headline
    # for question_text (anti-repetition + display fallback). When
    # question_text is already populated we keep it verbatim.
    scenario = _strip_html_tags(parsed.scenario)
    why = _strip_html_tags(parsed.why)
    how = _strip_html_tags(parsed.how)
    what = _strip_html_tags(parsed.what)
    question_text = _compose_question_text(
        question_text=_strip_html_tags(parsed.question_text),
        scenario=scenario, why=why, how=how, what=what,
    )
    if not question_text.strip():
        raise BossQuestionRejected("empty_question", raw=raw)
    if len(question_text) > max_question_length:
        raise BossQuestionRejected("question_too_long", raw=raw)

    if parsed.difficulty not in ALLOWED_DIFFICULTIES:
        raise BossQuestionRejected("invalid_difficulty", raw=raw)

    # Language drift (Bug #9 fix). If the homework language is uz/ru and the
    # generated text is English-leaning, reject and let the manual retry path
    # in generate_boss_question fire once with explicit language emphasis.
    drift = _detect_language_drift(
        question_text, parsed.target_skill, expected_language,
    )
    if drift:
        raise BossQuestionRejected(drift, raw=raw)

    # Anti-repetition: the canonical floor is "no byte-identical duplicates"
    # (after whitespace + case normalize) — enforced by the `prev_text ==
    # norm_new` branch below.
    #
    # The fuzzy SequenceMatcher.ratio() check is configurable via
    # _DUP_SIMILARITY_THRESHOLD. We previously held it at 0.85 to catch
    # one-number-swap paraphrases server-side, but in practice on narrow-topic
    # homeworks (e.g. an entire boss focused on fraction division) the LLM
    # legitimately cannot clear 0.85 within the existing 1-shot retry — every
    # candidate scores 0.93+ vs. a prior question and the route 502s. That
    # surfaces in the React arena as the "Try again → Refresh" escalation,
    # which is the safety net working as designed but a poor end-to-end UX
    # for the topic-narrow case.
    #
    # As of 2026-05-21 we delegate variation to the prompt itself (Rule 3 in
    # boss-question-generator.md, v5) and pin the runtime threshold at 1.0:
    # only byte-identical duplicates are rejected post-gateway. The prompt
    # carries explicit variation axes + a self-check directive; if quality
    # regresses we tune the prompt (or temporarily lower this threshold) and
    # measure rather than relying on a hard-coded floor that doesn't know the
    # homework's topic breadth.
    #
    # NOTE (2026-05-13): An earlier comment claimed "BossQuestionRejected
    # triggers the gateway repair retry." That was inaccurate. The gateway's
    # repair retry fires only on json.JSONDecodeError / ValidationError BEFORE
    # this function runs. Anti-repetition rejection happens post-gateway and
    # historically surfaced as an immediate 502. generate_boss_question now
    # implements a single manual retry for the `repeats_previous` case
    # specifically (see line ~490).
    _DUP_SIMILARITY_THRESHOLD = 1.0
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
        scenario=scenario,
        why=why,
        how=how,
        what=what,
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
    # Option C fix (2026-05-13 audit): lift the language directive from the
    # nested boss_policy.language to a top-level output_language key. The
    # prompt's strict-language banner points at this field. Top-level
    # placement makes it the first thing Kimi reads in the input JSON,
    # boosting attention vs. a deeply nested attribute.
    policy_lang = (boss_context.get("boss_policy") or {}).get("language")
    if policy_lang:
        payload["output_language"] = policy_lang

    # Bug #10 fix (2026-05-13 audit): _build_boss_input_section can raise
    # PromptTooLargeError (a RuntimeError subclass from ai_orchestrator) when
    # boss_context exceeds the size cap. Previously this call was outside the
    # try/except below and would surface as an unhandled 500. Translate it
    # to a clean BossQuestionRejected so the route returns 502 with a
    # specific reason rather than crashing.
    try:
        input_section = _build_boss_input_section(payload)
    except ai_orchestrator.PromptTooLargeError as exc:
        _log.warning(
            "generate_boss_question prompt_too_large: size=%d cap=%d",
            exc.size, exc.cap,
        )
        raise BossQuestionRejected(f"prompt_too_large: size={exc.size} cap={exc.cap}") from exc
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
    policy = boss_context.get("boss_policy") or {}
    max_qlen = int(policy.get("max_question_length") or 900)
    expected_language = policy.get("language")

    try:
        return _validate_generated_question(
            raw,
            asked_questions=asked,
            stems=stems,
            pool_max=pool_max,
            max_question_length=max_qlen,
            expected_language=expected_language,
        )
    except BossQuestionRejected as exc:
        # Anti-repetition retry (Plan Wave 2 §3 follow-up, 2026-05-13).
        # The gateway's built-in repair retry doesn't catch BossQuestionRejected
        # because it fires post-gateway. When fuzzy-similarity rejects a
        # near-duplicate we get one explicit retry with an emphatic
        # anti-repetition note injected and temperature bumped for variation.
        # Limited to ONE retry; a second `repeats_previous` propagates as 502.
        if exc.reason.startswith("repeats_previous") and asked:
            _log.warning(
                "boss anti-repetition rejection on attempt 1: %s; retrying once with emphasis",
                exc.reason,
            )
            emphasized_payload = dict(payload)
            emphasized_payload["_anti_repetition_emphasis"] = (
                "CRITICAL — your previous attempt was REJECTED as a near-duplicate of an "
                "already-asked question. You MUST generate a substantively different stem: "
                "different surface form, different numbers, ideally a different target_skill. "
                "Re-read asked_questions[] carefully before generating."
            )
            input_section2 = _build_boss_input_section(emphasized_payload)
            full_prompt2 = f"{prompt}\n\n{input_section2}"
            try:
                result2 = await ai_gateway.generate_structured(
                    task=ai_gateway.AITask.BOSS_QUESTION_GENERATE,
                    prompt=full_prompt2,
                    schema=BossQuestionGenerated,
                    session_id=boss_context.get("session_id"),
                    homework_id=boss_context.get("homework_id"),
                    temperature=0.6,  # bumped from 0.3 for variation
                    prompt_version=PROMPT_VERSION["boss-question-generator"],
                )
            except RuntimeError as exc2:
                _log.warning("boss anti-repetition retry failed: AI unavailable: %s", exc2)
                raise BossQuestionRejected("ai_unavailable_on_retry") from exc2
            raw2 = result2.model_dump()
            # Re-validate (may still reject; propagate that as the final answer).
            return _validate_generated_question(
                raw2,
                asked_questions=asked,
                stems=stems,
                pool_max=pool_max,
                max_question_length=max_qlen,
                expected_language=expected_language,
            )
        # Language-drift retry (Bug #9 fix, 2026-05-13 audit). Same shape as
        # the anti-repetition retry above — one shot with explicit emphasis,
        # second rejection propagates.
        if exc.reason.startswith("language_drift") and expected_language:
            _log.warning(
                "boss language drift rejection on attempt 1: %s; retrying once with emphasis",
                exc.reason,
            )
            lang_payload = dict(payload)
            lang_payload["_language_emphasis"] = (
                f"CRITICAL — your previous attempt was REJECTED for drifting to English. "
                f"This homework is in language={expected_language!r}. Write the entire "
                f"question_text, target_skill, why_this_question, and rubric entries in "
                f"that language. No English snake_case skill names (e.g. 'sign_error') — "
                f"use the homework language's terminology."
            )
            input_section3 = _build_boss_input_section(lang_payload)
            full_prompt3 = f"{prompt}\n\n{input_section3}"
            try:
                result3 = await ai_gateway.generate_structured(
                    task=ai_gateway.AITask.BOSS_QUESTION_GENERATE,
                    prompt=full_prompt3,
                    schema=BossQuestionGenerated,
                    session_id=boss_context.get("session_id"),
                    homework_id=boss_context.get("homework_id"),
                    temperature=0.4,
                    prompt_version=PROMPT_VERSION["boss-question-generator"],
                )
            except RuntimeError as exc3:
                _log.warning("boss language-drift retry failed: AI unavailable: %s", exc3)
                raise BossQuestionRejected("ai_unavailable_on_retry") from exc3
            raw3 = result3.model_dump()
            return _validate_generated_question(
                raw3,
                asked_questions=asked,
                stems=stems,
                pool_max=pool_max,
                max_question_length=max_qlen,
                expected_language=expected_language,
            )
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
    # Boss-Arena coverage-based grading (spec §6): per-axis why/how/what
    # coverage 0..1, threaded into calculate_damage. Empty for legacy/
    # synthetic verdicts (damage then falls back to ``score``).
    coverage: dict[str, float] = field(default_factory=dict)


def _verdict_from_gateway(result: BossAnswerCheckResult) -> BossAnswerVerdict:
    """Convert a validated gateway result to the internal dataclass.

    Defensive floors when ``is_correct=true`` (2026-05-14 audit bug #2):
        - ``score`` floored to ``_CORRECT_SCORE_FLOOR`` (0.60) so
          calculate_damage doesn't return 0 — the damage formula treats
          score < 0.60 as a wrong answer and deals no damage. The LLM
          occasionally returns ``is_correct=true`` with ``score=0.4``
          (e.g. "answer correct but wording imprecise") which manifests
          as "✓ To'g'ri! −0 HP" on the student's screen.
        - ``damage_multiplier`` floored to 1.0 so a correct answer is
          never penalised by a sub-1.0 modifier. The LLM may recommend
          multipliers in [0.0, 1.5]; on ``is_correct=true`` we treat any
          recommendation below 1.0 as semantically inconsistent with the
          binary correctness signal and clamp to the neutral default.

    When ``is_correct=false``, no floors apply — wrong answers legitimately
    have low scores and the route layer correctly skips damage.

    Boss-Arena coverage (spec §6): when the checker returns ``coverage``,
    damage is driven by ``coverage_mean`` rather than ``score``. So the
    is_correct floor must also lift any coverage mean that would fall in the
    zero-damage tier (< 0.30): without this, a correct answer with weak
    coverage would still show "−0 HP", reintroducing the 2026-05-14 bug. We
    floor the coverage mean to ``_CORRECT_SCORE_FLOOR`` by scaling the present
    axes proportionally (preserving their relative shape) when the mean is too
    low. ``score`` is also floored as a defense-in-depth for the no-coverage
    fallback path.
    """
    diff_rec = result.difficulty_recommendation
    if diff_rec not in {"increase", "decrease", "stay"}:
        diff_rec = "stay"

    effective_score = float(result.score)
    effective_multiplier = float(result.damage_multiplier or 1.0)
    # Sanitize coverage to numeric axes only, clamped to 0..1. ``getattr`` keeps
    # us tolerant of legacy / hand-rolled result objects that predate the
    # coverage field (the gateway always supplies it via BossAnswerCheckResult).
    raw_coverage = getattr(result, "coverage", None) or {}
    effective_coverage: dict[str, float] = {}
    for axis in _COVERAGE_AXES:
        v = raw_coverage.get(axis)
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            effective_coverage[axis] = max(0.0, min(1.0, float(v)))

    if result.is_correct:
        if effective_score < _CORRECT_SCORE_FLOOR:
            effective_score = _CORRECT_SCORE_FLOOR
        if effective_multiplier < _CORRECT_MULTIPLIER_FLOOR:
            effective_multiplier = _CORRECT_MULTIPLIER_FLOOR
        # Floor the coverage mean so a correct answer never lands in the
        # zero-damage accuracy tier (< 0.30). Scale present axes up uniformly
        # to lift the mean to _CORRECT_SCORE_FLOOR while keeping their shape.
        cov_mean = coverage_mean(effective_coverage)
        if cov_mean is not None and 0.0 < cov_mean < _CORRECT_SCORE_FLOOR:
            scale = _CORRECT_SCORE_FLOOR / cov_mean
            effective_coverage = {
                k: min(1.0, v * scale) for k, v in effective_coverage.items()
            }
        elif cov_mean is not None and cov_mean == 0.0:
            # All-zero coverage on a "correct" verdict is contradictory; lift
            # every present axis to the floor so damage > 0.
            effective_coverage = {
                k: _CORRECT_SCORE_FLOOR for k in effective_coverage
            }

    return BossAnswerVerdict(
        is_correct=result.is_correct,
        score=effective_score,
        confidence=result.confidence,
        feedback_to_student=result.feedback,
        misconception_tags=list(result.misconception_tags),
        damage_multiplier=max(
            _MULTIPLIER_MIN, min(_MULTIPLIER_MAX, effective_multiplier)
        ),
        difficulty_recommendation=diff_rec,
        should_retry_same_skill=result.should_retry_same_skill,
        coverage=effective_coverage,
    )


async def check_boss_answer(
    *,
    question_text: str,
    expected_answer: dict[str, Any],
    rubric: dict[str, Any],
    student_answer: str,
    target_skill: str,
    difficulty: str,
    language: Optional[str] = None,
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

    The ``language`` kwarg (Bug B, 2026-05-14) drives the prompt v2 language
    banner — the checker emits feedback in the homework's language and
    avoids English snake_case misconception_tags on uz/ru lessons. None is
    permitted for back-compat with callers that haven't been updated; the
    prompt falls back to its own heuristic in that case.
    """
    prompt = _load_prompt("boss-answer-checker")
    payload = {
        "question_text": question_text,
        "expected_answer": expected_answer,
        "rubric": rubric,
        "student_answer": student_answer,
        "target_skill": target_skill,
        "difficulty": difficulty,
        "language": language,
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
    "coverage_mean",
    "accuracy_tier",
    "hint_penalty",
    "HP_BY_GRADE_BAND",
    "starting_hp_for",
    "COMBO_STREAK_THRESHOLD",
    "COMBO_BONUS_FACTOR",
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
