"""Pydantic schemas for `content_json` — gates PUT/PATCH at the route boundary.

GPT-5.5 audit (2026-04-29) flagged `content_json` as the largest long-term
safety risk: PUT replaces the whole blob, PATCH deep-merges partial content,
and there is no per-phase validation. A frontend or agent that drops a key
silently corrupts a homework.

Design rule: **be permissive, not strict.** The MVP cannot afford a "schema
rejected the perfectly-valid existing homework" incident. Every model uses
`extra = "allow"` so unknown keys do not break old data. Required fields are
limited to what every existing fixture in `fixtures/` actually has. Field
types are widened (Union[str, int]) wherever production data shows variants.

Phase types covered (matches STATE.md + fixtures):
1. flashcards         — preview phase
2. memory_sprint      — practice phase
3. real_life          — practice phase (scenario + per-question answers)
4. reading            — consolidation phase (passage + checkpoints)
5. boss_questions     — final phase (open-ended + answer_spec)
6. game_breaks        — between-phase mini-games (gb_*)
7. reflection         — closing phase
"""

from typing import Any, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


# --------------------------------------------------------------------------- #
# Permissive base — every nested model accepts unknown keys.
# --------------------------------------------------------------------------- #


class _Permissive(BaseModel):
    """Base model that accepts unknown keys without raising."""

    model_config = ConfigDict(extra="allow")


# --------------------------------------------------------------------------- #
# AnswerSpec — the load-bearing grading contract.
# --------------------------------------------------------------------------- #


class AnswerSpec(_Permissive):
    """Grading contract used by `server/services/answer_checker.py`.

    Variants observed in fixtures:
      - {type: numeric,    expected: int,        tolerance: 0,  ...}
      - {type: text_exact, expected: "B",        allow_ai_fallback: false, ...}
      - {type: text_fuzzy, expected: "qo'sh spiral", allow_ai_fallback: true, ...}
      - {type: option_index, option_index: 2, ...}
      - {type: set_match | semantic_short, ...}

    All fields optional — checker reads `type` first and only requires the
    fields relevant to that type. Refusing a field would lock us out of new
    grading types added later.
    """

    type: Optional[str] = None
    # `expected` is the most variant-shaped field — int, str, list, even dict.
    expected: Optional[Union[str, int, float, bool, List[Any], dict]] = None
    canonical_display: Optional[str] = None
    allow_ai_fallback: Optional[bool] = None
    tolerance: Optional[Union[int, float]] = None
    accepted_answers: Optional[List[str]] = None
    option_index: Optional[int] = None
    correct: Optional[Union[bool, int, str]] = None


# --------------------------------------------------------------------------- #
# Phase 1 — Flashcards (preview).
# --------------------------------------------------------------------------- #


class FlashcardItem(_Permissive):
    """Each fixture uses {term, def, cluster}. NB: key is `def`, not `definition`."""

    term: str
    # Real fixtures use the bare key `def`; we mirror that with a Field alias.
    # Pydantic v2 auto-resolves the alias both ways.
    definition: Optional[str] = Field(default=None, alias="def")
    cluster: Optional[str] = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)


# --------------------------------------------------------------------------- #
# Phase 2 — Memory Sprint (practice, multi-choice).
# --------------------------------------------------------------------------- #


class MemorySprintItem(_Permissive):
    """Question types observed: KO (multi-choice), TF (true/false), YNNG (yes/no/unknown)."""

    type: Optional[str] = None
    prompt: str
    subtitle: Optional[str] = ""
    tags: Optional[str] = ""
    explain: Optional[str] = ""
    options: List[str] = Field(default_factory=list)
    # Index into `options`. Some fixtures may eventually carry a string answer
    # for free-response variants — keep the type widened.
    correct: Optional[Union[int, str]] = None


# --------------------------------------------------------------------------- #
# Phase 3 — Real Life (scenario + per-question answers).
# --------------------------------------------------------------------------- #


class RealLifeField(_Permissive):
    """A single fill-in field inside a real_life q with `fields`."""

    id: Optional[str] = None
    label: Optional[str] = None
    ans: Optional[str] = None


class RealLifeQuestion(_Permissive):
    """Fixtures show 3 shapes:
      - {prompt, ans, fb}                     — single text answer
      - {prompt, fields: [...], fb}           — multiple labeled blanks
      - {prompt, open: true, fb}              — open-ended (graded by AI)
    All combinations exist; we accept all.
    """

    prompt: str
    ans: Optional[str] = None
    fb: Optional[str] = None
    fields: Optional[List[RealLifeField]] = None
    open: Optional[bool] = None


class RealLifePhase(_Permissive):
    """Top-level scenario block. Every q1..qN slot is optional — fixtures
    contain anywhere from 1 to 6+ questions."""

    badge: Optional[str] = None
    story: Optional[str] = None
    q1: Optional[RealLifeQuestion] = None
    q2: Optional[RealLifeQuestion] = None
    q3: Optional[RealLifeQuestion] = None
    q4: Optional[RealLifeQuestion] = None
    q5: Optional[RealLifeQuestion] = None
    q6: Optional[RealLifeQuestion] = None
    endTitle: Optional[str] = None
    endSub: Optional[str] = None


# --------------------------------------------------------------------------- #
# Phase 4 — Reading (consolidation: passage + checkpoint questions).
# --------------------------------------------------------------------------- #


class ReadingCheckpoint(_Permissive):
    # `q` is the canonical key in production fixtures, but synthetic test
    # payloads use `prompt`/other variants. Keep optional so the boundary
    # doesn't reject ambiguous-but-not-broken shapes.
    q: Optional[str] = None
    tags: Optional[str] = None
    ans: Optional[List[str]] = None


class ReadingPhase(_Permissive):
    text: Optional[str] = None
    checkpoints: List[ReadingCheckpoint] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Phase 5 — Boss (final, open-ended w/ answer_spec).
# --------------------------------------------------------------------------- #


class BossQuestion(_Permissive):
    # `q` optional — variants pass `prompt` or carry extra rubric blocks.
    q: Optional[str] = None
    prompt: Optional[str] = None
    tags: Optional[str] = None
    ans: Optional[List[str]] = None
    hint: Optional[str] = None
    dmg: Optional[Union[int, float]] = None
    answer_spec: Optional[AnswerSpec] = None
    accepted_answers: Optional[List[str]] = None


# --------------------------------------------------------------------------- #
# Phase 6 — Game Breaks (between-phase mini-games).
# Each gb_* array is its own list at the top level of content_json.
# --------------------------------------------------------------------------- #


class AdaptiveQuizItem(_Permissive):
    """gb_adaptive_quiz — the same answer_spec contract as boss questions.

    Production fixtures use `q`, but the tutor leak test uses `prompt` with
    nested option/field/rubric blocks. Both must validate."""

    q: Optional[str] = None
    prompt: Optional[str] = None
    tags: Optional[str] = None
    tier: Optional[str] = None  # "EASY" | "MEDIUM" | "HARD"
    ans: Optional[List[str]] = None
    capture: Optional[bool] = None
    answer_spec: Optional[AnswerSpec] = None
    accepted_answers: Optional[List[str]] = None


class WhyChainItem(_Permissive):
    """gb_why_chain — open-ended 'why?' chains with re-prompts."""

    q: str
    inv: Optional[str] = None
    reprompts: Optional[List[str]] = None


class PuzzleLockItem(_Permissive):
    """gb_puzzle_lock — tile + Q&A. Legacy variants use {text, question, answer}
    instead of {content, q, a}, so all six keys are optional."""

    content: Optional[str] = None
    q: Optional[str] = None
    a: Optional[str] = None
    # Legacy aliases observed in test_puzzle_lock_injector.py:
    text: Optional[str] = None
    question: Optional[str] = None
    answer: Optional[str] = None


class MysteryBoxItem(_Permissive):
    """gb_mystery_box — {category, q, a}."""

    category: Optional[str] = None
    q: Optional[str] = None
    a: Optional[str] = None


class TttItem(_Permissive):
    """gb_ttt — tic-tac-toe quiz with {q, correct, distractors[]} (3 distractors)."""

    q: Optional[str] = None
    correct: Optional[str] = None
    distractors: Optional[List[str]] = None


# --------------------------------------------------------------------------- #
# Phase 7 — Reflection (closing).
# --------------------------------------------------------------------------- #


class ReflectionPhase(_Permissive):
    summary: Optional[str] = None
    question: Optional[str] = None
    spaced_rep: Optional[str] = None
    closing: Optional[str] = None


# --------------------------------------------------------------------------- #
# Supporting blocks (panels / meta) — preserved permissively.
# --------------------------------------------------------------------------- #


class PanelBlock(_Permissive):
    type: Optional[str] = None  # h2, p, ul, quote, ...
    text: Optional[str] = None
    items: Optional[List[str]] = None


class PanelPage(_Permissive):
    blocks: Optional[List[PanelBlock]] = None


class Panel(_Permissive):
    id: Optional[Union[int, str]] = None
    title: Optional[str] = None
    pages: Optional[List[PanelPage]] = None


class Meta(_Permissive):
    title: Optional[str] = None
    subject_display: Optional[str] = None
    section: Optional[str] = None
    cefr_level: Optional[str] = None


class GateQuote(_Permissive):
    mode: Optional[str] = None  # "auto" | other


# --------------------------------------------------------------------------- #
# Top-level — every phase optional so partial homeworks still validate.
# --------------------------------------------------------------------------- #


class ContentJSON(_Permissive):
    """Full `content_json` blob. Every phase is optional and `extra='allow'`
    is set on every nested model, so unknown keys propagate untouched. The
    boundary validator only rejects shapes that are *obviously* wrong (e.g.,
    `flashcards` set to a string instead of a list, `meta` set to a list)."""

    meta: Optional[Meta] = None
    quotes: Optional[List[str]] = None
    panels: Optional[List[Panel]] = None
    gate_quote: Optional[GateQuote] = None

    # Final-boss section name. Optional override; when missing the runtime
    # falls back to a subject-aware default (see services/injector.boss_name_for).
    boss_name: Optional[str] = None

    # Phase 1
    flashcards: Optional[List[FlashcardItem]] = None
    # Phase 2
    memory_sprint: Optional[List[MemorySprintItem]] = None
    # Phase 3
    real_life: Optional[RealLifePhase] = None
    # Phase 4
    reading: Optional[ReadingPhase] = None
    # Phase 5
    boss_questions: Optional[List[BossQuestion]] = None
    # Phase 6 — game breaks (each gb_* list lives at top level)
    gb_adaptive_quiz: Optional[List[AdaptiveQuizItem]] = None
    gb_why_chain: Optional[List[WhyChainItem]] = None
    # gb_memory_match is authored as [[term, def], ...] — list of 2-tuples.
    gb_memory_match: Optional[List[List[str]]] = None
    gb_puzzle_lock: Optional[List[PuzzleLockItem]] = None
    gb_mystery_box: Optional[List[MysteryBoxItem]] = None
    gb_ttt: Optional[List[TttItem]] = None
    # Phase 7
    reflection: Optional[ReflectionPhase] = None
