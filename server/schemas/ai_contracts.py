"""Pydantic contracts for structured AI outputs.

These models define the expected shape of responses from the AI gateway
for each task type. They are used for validation and repair retries.
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field


class TutorResponse(BaseModel):
    reply: str = Field(description="The tutor's response text")
    action: str = Field(
        default="explain",
        description="One of: explain, hint, clarify, encourage, warn, redirect",
    )
    used_screen: bool = Field(default=False)
    used_question: bool = Field(default=False)
    used_performance: bool = Field(default=False)
    detected_need: Optional[str] = Field(
        default=None,
        description="word_definition | concept_explanation | answer_help | unclear_reference",
    )
    misconception_tags: list[str] = Field(default_factory=list)


class AnswerCheckResult(BaseModel):
    score: float = Field(ge=0.0, le=1.0, description="Score between 0.0 and 1.0")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence between 0.0 and 1.0")
    feedback: str = Field(description="Helpful feedback for the student")
    misconception_tags: list[str] = Field(default_factory=list)
    next_hint: Optional[str] = Field(default=None)
    is_correct: Optional[bool] = Field(default=None)


# ---- Plan 7 enriched Boss schemas ------------------------------------------

class BossExpectedAnswer(BaseModel):
    canonical: str
    accepted_variants: list[str] = Field(default_factory=list)
    notes: str = ""


class BossRubric(BaseModel):
    full_credit: list[str] = Field(default_factory=list)
    partial_credit: list[str] = Field(default_factory=list)
    common_mistakes: list[str] = Field(default_factory=list)


class BossQuestionGenerated(BaseModel):
    """Plan 7 strict contract for the Boss Question Generator output.

    Boss-Arena Why→How→What additions (spec §4/§9): the generator emits a
    ``scenario`` plus three reasoning prompts (``why`` / ``how`` / ``what``).
    All four default to "" so legacy single-field generations (which only
    populate ``question_text``) still validate. ``question_text`` stays the
    composite/headline used for anti-repetition + display fallback.
    """

    question_text: str = Field(..., max_length=900)
    # Structured Why→How→What reasoning shape (spec §4/§9). PROMPT text only —
    # safe to send to the client; never carries answer/rubric content.
    scenario: str = ""
    why: str = ""
    how: str = ""
    what: str = ""
    expected_answer: BossExpectedAnswer
    rubric: BossRubric
    target_skill: str
    difficulty: Literal["easy", "medium", "hard"]
    source_phase_ids: list[str] = Field(default_factory=list)
    why_this_question: str = ""


class BossAnswerCheckResult(BaseModel):
    """Plan 7 strict contract for the Boss Answer Checker output.

    NOTE: ``hp_delta`` was removed in Plan 7. The backend owns HP mutations;
    the model only recommends a ``damage_multiplier`` which the backend clamps.
    """

    is_correct: bool
    score: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    feedback: str = Field(
        ...,
        description="1-2 sentence feedback in the student's language",
    )
    misconception_tags: list[str] = Field(default_factory=list)
    damage_multiplier: float = Field(default=1.0, ge=0.0, le=1.5)
    difficulty_recommendation: Literal["increase", "decrease", "stay"] = "stay"
    should_retry_same_skill: bool = False
    # Boss-Arena coverage-based grading (spec §6): per-axis reasoning coverage
    # for the Why→How→What chain, each 0..1. Default empty so legacy single-
    # score generations still validate; calculate_damage falls back to ``score``
    # when coverage is absent.
    coverage: dict[str, float] = Field(default_factory=dict)


class FinalReportResult(BaseModel):
    summary: str
    weak_topics: list[str] = Field(default_factory=list)
    strong_topics: list[str] = Field(default_factory=list)
    recommendation: str
    mastery_score: float = Field(ge=0.0, le=1.0)


class GuardrailResult(BaseModel):
    allowed: bool
    risk: str = Field(default="none", description="none | answer_leak | prompt_injection | off_topic")
    action: str = Field(
        default="continue",
        description="continue | refuse | redirect | ask_clarifying",
    )


class SimulationJudgeResult(BaseModel):
    """Output of an LLM-as-judge over a multi-turn tutor session transcript.

    Used by the SIMULATION_JUDGE task to score offline simulations of tutor
    behaviour (correctness of feedback, age-appropriate tone, no answer
    leakage, etc.).
    """
    overall_score: float = Field(ge=0.0, le=1.0, description="Aggregate quality score 0.0–1.0")
    confidence: float = Field(ge=0.0, le=1.0)
    verdict: str = Field(default="pass", description="pass | fail | needs_review")
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    rubric_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Per-axis 0.0–1.0 scores (correctness, tone, safety, ...)",
    )
    notes: Optional[str] = Field(default=None)
