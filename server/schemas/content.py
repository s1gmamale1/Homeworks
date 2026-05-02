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

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator


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

# Taxonomy enums (forward-compat; runtime engine deferred for Big/Mythical).
BossType = Literal["sub", "big", "mythical"]
BossPisaLevel = Literal["L1", "L2", "L3", "L4", "L5", "L6"]
BossBloomLevel = Literal["apply", "analyze", "evaluate", "create"]
GradeBand = Literal["g1_4", "g5", "g6_8", "g9_11"]


class BossAntiCheatPolicy(BaseModel):
    """Anti-cheat signal fields. Schema-only in v1; runtime telemetry deferred."""
    model_config = ConfigDict(extra="allow")
    paste_detect: bool = False
    response_time_floor_ms: int = 0


class BossMeta(BaseModel):
    """Optional metadata block for the boss phase.

    All fields optional. Lives under content_json.boss_meta — never required.
    Existing homeworks without boss_meta render unchanged.
    """
    model_config = ConfigDict(extra="allow")
    boss_type: BossType = "sub"
    grade_band: Optional[GradeBand] = None
    attempts_max: Optional[int] = None             # None = unlimited (premium sub); 2 = basic sub default; 1 = big/mythical
    anti_cheat: Optional[BossAntiCheatPolicy] = None
    starting_hp_override: Optional[int] = None     # author override for unusual cases

    @model_validator(mode="after")
    def _validate(self) -> "BossMeta":
        if self.attempts_max is not None and self.attempts_max < 1:
            raise ValueError("attempts_max must be >= 1 (use None for unlimited)")
        if self.starting_hp_override is not None and self.starting_hp_override < 10:
            raise ValueError("starting_hp_override must be >= 10")
        if self.boss_type == "mythical" and self.attempts_max not in (None, 1):
            raise ValueError("Mythical boss has fixed attempts_max=1 per spec §3")
        return self


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
    # New optional fields — additive only, existing rows unaffected.
    pisa_level: Optional[BossPisaLevel] = None    # explicit per-q PISA enum (was implicit in tags)
    bloom_level: Optional[BossBloomLevel] = None  # explicit Bloom level (was implicit in tags)
    hint_cost_per_use: Optional[int] = None       # grade-banded default 10; spec §8 override


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
# Tile Match — new structured pair model (replaces raw gb_memory_match tuples).
# --------------------------------------------------------------------------- #

SubjectFamily = Literal[
    "math", "biology", "history", "literature", "physics",
    "chemistry", "language", "geography", "general",
]


class TileMatchPair(BaseModel):
    """gb_tile_match — structured pair for the Tile Match game.

    Each instance represents one left/right concept pair. The injector splits
    these into a side-disjoint flat array so the client never sees both sides
    of a pair in the same JS object (answer-leak prevention).
    """

    model_config = ConfigDict(extra="allow")

    id: str                                                     # stable per-pair id, e.g. "tm_001"
    left: str                                                   # concept side (formula / term / symbol)
    right: str                                                  # definition side (description / example)
    tier: Literal["basic", "premium"] = "basic"
    concept_family: Optional[str] = None                        # branch-complete grouping
    subject_family: Optional[SubjectFamily] = None              # Buzan color hook
    pisa_level: Optional[Literal["L1", "L2", "L3", "L4", "L5", "L6"]] = None
    difficulty: Optional[Literal["easy", "medium", "hard"]] = None
    is_palace_tile: bool = False                                # Memory Palace tile (premium-only)
    explanation: Optional[str] = None                          # premium "why this is wrong" note

    @model_validator(mode="after")
    def _validate_pair(self):
        if not self.left.strip():
            raise ValueError("left must be non-empty")
        if not self.right.strip():
            raise ValueError("right must be non-empty")
        if len(self.left) > 300:
            raise ValueError("left must be ≤ 300 chars")
        if len(self.right) > 300:
            raise ValueError("right must be ≤ 300 chars")
        if self.is_palace_tile and self.tier != "premium":
            raise ValueError("Memory Palace tiles are premium-only (per spec §3)")
        return self


class SentenceFillItem(BaseModel):
    """gb_sentence_fill — cloze passage with per-blank answers + optional word bank."""

    model_config = ConfigDict(extra="allow")
    id: str
    mode: Literal["word_bank", "free_recall"]
    passage: str
    answers: List[str]
    word_bank: Optional[List[str]] = None
    explanations: Optional[List[Optional[str]]] = None
    tags: Optional[str] = None
    pisa_level: Optional[Literal["L1", "L2", "L3", "L4", "L5"]] = None
    difficulty: Optional[Literal["easy", "medium", "hard"]] = None
    subject_hint: Optional[str] = None
    color_hints: Optional[Dict[str, str]] = None
    blank_icons: Optional[List[Optional[str]]] = None
    tier: Literal["basic", "premium"] = "basic"

    @model_validator(mode="after")
    def _validate(self):
        blanks = self.passage.count("___")
        if blanks == 0:
            raise ValueError("passage must contain at least one '___' blank marker")
        if not (1 <= blanks <= 6):
            raise ValueError(f"passage has {blanks} blanks; spec allows 1-6")
        if len(self.answers) != blanks:
            raise ValueError(f"answers length {len(self.answers)} != blanks {blanks}")
        if self.mode == "word_bank":
            if not self.word_bank:
                raise ValueError("word_bank required when mode=='word_bank'")
            if not set(self.answers).issubset(set(self.word_bank)):
                raise ValueError("word_bank must contain every answer")
            if len(self.word_bank) <= len(self.answers):
                raise ValueError("word_bank must include at least one distractor")
        if self.explanations is not None and len(self.explanations) != len(self.answers):
            raise ValueError(f"explanations length {len(self.explanations)} != answers {len(self.answers)}")
        if self.blank_icons is not None and len(self.blank_icons) != len(self.answers):
            raise ValueError(f"blank_icons length {len(self.blank_icons)} != answers {len(self.answers)}")
        return self


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
# Phase 3 (new) — Real-Life Challenge (RLC).                                  #
# Split-and-coexist with legacy `real_life`. New mechanic: 5-step expert      #
# role-play decision case. Legacy `real_life` field is kept unchanged.        #
# --------------------------------------------------------------------------- #

ExpertRole = Literal[
    "fire_inspector", "structural_engineer", "business_consultant",
    "medical_diagnostician", "agronomist", "teacher", "lawyer",
    "city_planner", "epidemiologist", "ethicist", "historian", "general"
]

PisaLevel = Literal["L1", "L2", "L3", "L4", "L5", "L6"]


class RLCDecisionOption(BaseModel):
    """A single MC option on a decision step."""
    model_config = ConfigDict(extra="allow")
    id: str                            # stable per-option id, e.g., "a", "b", "c"
    label: str                         # student-visible text, ≤200 chars
    is_correct: bool = False           # SERVER-ONLY — stripped from injector
    consequence: Optional[str] = None  # SERVER-ONLY — shown only after wrong/correct via endpoint response
    info_cost: Optional[Dict[str, str]] = None  # for info-request steps; {time?, budget?, access?}


class RLCConceptChip(BaseModel):
    """A concept chip for the concept-select step."""
    model_config = ConfigDict(extra="allow")
    id: str
    label: str
    is_correct: bool = False           # SERVER-ONLY


class RLCStep(BaseModel):
    """One of the 5 steps in the case flow."""
    model_config = ConfigDict(extra="allow")
    id: str                                              # "step1" .. "step5"
    kind: Literal["decision", "info_request", "final_decision",
                  "concept_select", "reasoning"]
    title: str                                           # e.g., "1-bosqich. Vaziyatni baholash"
    prompt: str                                          # student-visible (HTML allowed; sanitized)
    options: Optional[List[RLCDecisionOption]] = None    # for decision/info_request/final_decision
    concept_chips: Optional[List[RLCConceptChip]] = None  # for concept_select
    placeholder: Optional[str] = None                   # for reasoning step
    min_chars: Optional[int] = None                     # for reasoning step (default 80)
    acceptable_keywords: Optional[List[str]] = None     # SERVER-ONLY — for reasoning AI grading anchor


class RLCStakeholder(BaseModel):
    """Character in the case (deferred runtime visual; schema-ready)."""
    model_config = ConfigDict(extra="allow")
    id: str
    name: str
    role: str                           # "Bozor sotuvchisi", "Mahalla raisi", etc.
    avatar_emoji: Optional[str] = None  # for v1; image URL fields are future


class RLCConsequence(BaseModel):
    """Post-decision ripple node (deferred runtime visual; schema-ready)."""
    model_config = ConfigDict(extra="allow")
    label: str                         # "Oilani himoya qildi" / "Qo'shni do'konlarga zarar"
    impact: Literal["positive", "negative", "neutral"]
    weight: Optional[int] = None       # 1-5 ripple-distance


class RealLifeChallengeCase(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str                                      # stable case id, e.g., "rlc_001"
    expert_role: ExpertRole
    title: str                                   # case title, ≤200 chars
    intro: str                                   # 1-3 sentence scenario hook
    pisa_level: PisaLevel = "L4"
    tier: Literal["basic", "premium"] = "basic"
    grade_band: Literal["g1_3", "g4_6", "g7_9", "g10_11"] = "g7_9"
    variant: Literal["standard", "creative_thinking"] = "standard"

    # Required: exactly 5 steps in spec order
    steps: List[RLCStep]                         # length == 5

    # Optional: schema-ready forward-compat
    stakeholders: Optional[List[RLCStakeholder]] = None
    consequences: Optional[List[RLCConsequence]] = None
    branch_rules: Optional[List[Dict]] = None              # deferred L5 narrative branching
    apprentice_scaffold_hints: Optional[List[str]] = None  # deferred Apprentice Mode
    memory_palace_location: Optional[str] = None           # deferred Memory Palace

    @model_validator(mode="after")
    def _validate_structure(self):
        if len(self.steps) != 5:
            raise ValueError("RLC case must have exactly 5 steps per spec §1")

        expected_order = ["decision", "info_request", "final_decision",
                          "concept_select", "reasoning"]
        actual_order = [s.kind for s in self.steps]
        if actual_order != expected_order:
            raise ValueError(
                f"RLC step order must be {expected_order}; got {actual_order}"
            )

        # Correctness invariants per step
        decision_steps = [s for s in self.steps if s.kind in
                          ("decision", "info_request", "final_decision")]
        for s in decision_steps:
            if not s.options or len(s.options) < 2:
                raise ValueError(f"Step {s.id} ({s.kind}) must have ≥2 options")
            correct_count = sum(1 for o in s.options if o.is_correct)
            if correct_count != 1:
                raise ValueError(
                    f"Step {s.id} must have exactly 1 correct option "
                    f"(found {correct_count})"
                )

        # Concept select: exactly 1 correct chip
        concept_step = next((s for s in self.steps if s.kind == "concept_select"), None)
        if concept_step:
            if not concept_step.concept_chips or len(concept_step.concept_chips) < 3:
                raise ValueError("concept_select step must have ≥3 chips")
            correct_chips = sum(1 for c in concept_step.concept_chips if c.is_correct)
            if correct_chips != 1:
                raise ValueError(
                    f"concept_select must have exactly 1 correct chip (found {correct_chips})"
                )

        # Reasoning: min_chars sane
        reasoning = next((s for s in self.steps if s.kind == "reasoning"), None)
        if reasoning:
            if reasoning.min_chars is None:
                reasoning.min_chars = 80
            if reasoning.min_chars < 20 or reasoning.min_chars > 1000:
                raise ValueError("reasoning min_chars must be in [20, 1000]")

        # Tier gating
        if self.variant == "creative_thinking" and self.tier != "premium":
            raise ValueError("creative_thinking variant is premium-only per spec §2")
        if self.memory_palace_location is not None and self.tier != "premium":
            raise ValueError("memory_palace_location is premium-only per spec §3")

        return self


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
    # Phase 3 — legacy scenario (untouched; all existing rows use this)
    real_life: Optional[RealLifePhase] = None
    # Phase 3 (new) — Real-Life Challenge (5-step expert role-play decision case)
    real_life_challenge: Optional[RealLifeChallengeCase] = None
    # Phase 4
    reading: Optional[ReadingPhase] = None
    # Phase 5
    boss_questions: Optional[List[BossQuestion]] = None
    boss_meta: Optional[BossMeta] = None
    # Phase 6 — game breaks (each gb_* list lives at top level)
    gb_adaptive_quiz: Optional[List[AdaptiveQuizItem]] = None
    gb_why_chain: Optional[List[WhyChainItem]] = None
    # gb_memory_match is authored as [[term, def], ...] — list of 2-tuples.
    gb_memory_match: Optional[List[List[str]]] = None
    gb_puzzle_lock: Optional[List[PuzzleLockItem]] = None
    gb_mystery_box: Optional[List[MysteryBoxItem]] = None
    gb_ttt: Optional[List[TttItem]] = None
    gb_sentence_fill: Optional[List[SentenceFillItem]] = None
    # Tile Match — new structured pairs (replaces gb_memory_match for new content)
    gb_tile_match: Optional[List[TileMatchPair]] = None

    # Phase 7
    reflection: Optional[ReflectionPhase] = None

    @model_validator(mode="after")
    def _validate_tile_match_collection(self):
        pairs = self.gb_tile_match
        if pairs is None:
            return self
        if not (1 <= len(pairs) <= 8):
            raise ValueError(
                f"gb_tile_match must have 1–8 pairs (got {len(pairs)}); "
                "spec board sizes: G1-2:4, G3-4:5, G5-7:6, G8-11:8"
            )
        ids = [p.id for p in pairs]
        if len(ids) != len(set(ids)):
            raise ValueError("gb_tile_match: all pair id values must be unique")
        lefts = [p.left for p in pairs]
        if len(lefts) != len(set(lefts)):
            raise ValueError("gb_tile_match: all left strings must be unique (distractor rule)")
        rights = [p.right for p in pairs]
        if len(rights) != len(set(rights)):
            raise ValueError("gb_tile_match: all right strings must be unique (distractor rule)")
        palace_count = sum(1 for p in pairs if p.is_palace_tile)
        if palace_count > 1:
            raise ValueError(
                f"gb_tile_match: at most one is_palace_tile=True per board (got {palace_count})"
            )
        return self

    @model_validator(mode="after")
    def _validate_rlc_coexistence(self):
        """Both real_life (legacy) and real_life_challenge (new) may coexist
        on the same row — the runtime decides which to mount based on which
        global is non-null (RLC_CASE vs RL_SCENARIO). No error raised.
        This validator exists as a documented contract checkpoint.
        """
        # real_life_challenge structural validation is handled by
        # RealLifeChallengeCase._validate_structure; nothing to cross-validate here.
        return self

    @model_validator(mode="after")
    def _validate_mythical_boss_hints(self) -> "ContentJSON":
        """Mythical boss spec §11: zero hints per question.

        If boss_meta.boss_type == 'mythical' and any question has non-empty
        hints, raise ValidationError. This prevents accidental hint leakage
        on the highest-difficulty boss type.
        """
        if self.boss_meta is None or self.boss_meta.boss_type != "mythical":
            return self
        questions = self.boss_questions or []
        for q in questions:
            q_dict = q if isinstance(q, dict) else q.model_dump()
            hints = q_dict.get("hints") or []
            if hints:
                raise ValueError(
                    "Mythical boss must have zero hints per spec §11 "
                    "(found non-empty hints on at least one question)"
                )
        return self
