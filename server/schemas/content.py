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
    use_dynamic_boss: bool = False                 # author opt-in; static boss_questions remain fallback

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
    # Boss-Arena authored Why→How→What shape (spec §4/§9) — all optional, never
    # required. They document the authored question shape; the dynamic boss
    # generator produces the same shape at runtime. extra="allow" already lets
    # unknown keys through; these make the contract explicit for tooling.
    scenario: Optional[str] = None
    why: Optional[str] = None
    how: Optional[str] = None
    what: Optional[str] = None
    expected_concepts: Optional[List[str]] = None  # grading anchor (server-only — see ANSWER_BEARING_KEYS)
    concept_tag: Optional[str] = None
    bloom: Optional[str] = None                    # free-form Bloom label (distinct from the bloom_level enum)
    pisa: Optional[str] = None                     # free-form PISA label (distinct from the pisa_level enum)
    hints: Optional[List[str]] = None              # progressive hints; never reveal the answer
    correct_feedback: Optional[str] = None
    partial_feedback: Optional[str] = None
    wrong_feedback: Optional[str] = None


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
    """gb_ttt — tic-tac-toe quiz with {id, q, correct, distractors[]} (3 distractors).

    `id` is optional (auto-assigned by the injector as "ttt-1", "ttt-2", ... if absent).
    `correct` and `distractors` are server-only — stripped by the injector before the
    wire format is sent to the client (side-disjoint, answer-leak prevention).
    """

    id: Optional[str] = None
    q: Optional[str] = None
    correct: Optional[str] = None
    distractors: Optional[List[str]] = None


class TttConfig(_Permissive):
    """gb_ttt_config — optional XP and session overrides for the TTT game.

    All fields are optional; the injector applies spec defaults when absent:
      session_games=3, xp_correct=50, xp_draw=200, xp_win=300,
      xp_strong_session=100, xp_mercy=10, mercy_chance=0.002.
    """

    session_games: Optional[int] = None       # default 3
    xp_correct: Optional[int] = None          # default 50
    xp_draw: Optional[int] = None             # default 200
    xp_win: Optional[int] = None              # default 300
    xp_strong_session: Optional[int] = None   # default 100
    xp_mercy: Optional[int] = None            # default 10
    mercy_chance: Optional[float] = None      # default 0.002


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


class ReflectionAnalysis(_Permissive):
    """Server-authoritative reflection debrief block (additive — absent on
    legacy homeworks). The reflection engine reads real `phase_attempts` data,
    computes a verdict + mark, and surfaces a debrief.

    Student-visible fields (`narrative`, `weak_points`, `strong_points`,
    `next_steps`, `redo_recommendation`) SURVIVE hydration — they come back in
    the debrief. The grading config (`analysis_rubric`, the keyword buckets,
    `pass_threshold`) is answer-bearing and is stripped by the runtime redactor
    (these keys live in ANSWER_BEARING_KEYS). The server reads the full object
    from the DB row to grade; the browser only ever sees the debrief fields.
    """

    # ---- Student-visible (survive redaction) — these come back in the debrief ----
    narrative: Optional[str] = None
    weak_points: Optional[List[str]] = None
    strong_points: Optional[List[str]] = None
    next_steps: Optional[List[str]] = None
    redo_recommendation: Optional[str] = None

    # ---- Server-only grading config (STRIPPED before hydration) ----
    analysis_rubric: Optional[Dict[str, Any]] = None
    weak_point_keywords: Optional[List[str]] = None
    strong_point_keywords: Optional[List[str]] = None
    pass_threshold: Optional[int] = None


class ReflectionPhase(_Permissive):
    summary: Optional[str] = None
    question: Optional[str] = None
    spaced_rep: Optional[str] = None
    closing: Optional[str] = None
    # Server-authoritative reflection debrief + grading config (additive).
    analysis: Optional[ReflectionAnalysis] = None


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
# Memory Palace — Method-of-Loci game-break mechanic.                         #
#                                                                               #
# NAMESPACE NOTE: `gb_memory_palace` is the standalone Method-of-Loci         #
# mechanic added in this PR. NOT to be confused with:                          #
#   - `RealLifeChallengeCase.memory_palace_location` (sub-field on a different #
#     mechanic — premium RLC location annotation)                               #
#   - `TileMatchPair.is_palace_tile` (premium flag on a different mechanic —   #
#     marks one tile per Tile Match board as a "palace tile" visual bonus)      #
# --------------------------------------------------------------------------- #

MPSubjectFamily = Literal[
    "bio", "chem", "phys", "math", "history", "lang", "art", "universal"
]

PalaceTier = Literal["basic", "premium"]


class MemoryPalaceLocation(_Permissive):
    """A single station inside a Memory Palace route."""

    name: str = ""
    sensory_cue: Optional[str] = None
    icon: Optional[str] = None  # optional emoji


class MemoryPalaceConcept(_Permissive):
    """One concept to be encoded and recalled via the palace route."""

    id: Optional[str] = None             # auto-filled "mp-c{idx+1}" if missing
    term: str = ""
    description: Optional[str] = None
    image_cue: Optional[str] = None      # exaggerated imagery hint


class MemoryPalace(_Permissive):
    """A single palace (route) that students can walk during encoding."""

    key: str = ""
    name: str = ""
    icon: Optional[str] = None
    description: Optional[str] = None
    subject_family: Optional[MPSubjectFamily] = None  # MAY be omitted (defaults handled at builder/runtime layer)
    tier: PalaceTier = "basic"
    locations: List[MemoryPalaceLocation] = Field(default_factory=list)


class MemoryPalaceGame(_Permissive):
    """Top-level container stored in content_json.gb_memory_palace.

    Holds the authored palace routes + concepts for the game-break.
    Validators enforce structural integrity when content is present;
    empty arrays are allowed during builder authoring.
    """

    palaces: List[MemoryPalace] = Field(default_factory=list)
    concepts: List[MemoryPalaceConcept] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_memory_palace_game(self):
        # Palace key uniqueness
        if self.palaces:
            keys = [p.key for p in self.palaces]
            if len(keys) != len(set(keys)):
                raise ValueError("MemoryPalaceGame: all palace key values must be unique")

            # Each palace must have 3–7 locations (accommodates grade overrides 3/5/7)
            for p in self.palaces:
                n = len(p.locations)
                if not (3 <= n <= 7):
                    raise ValueError(
                        f"Palace '{p.key}' has {n} locations; spec allows 3–7 "
                        "(3 for grades 1-4, 5 default, 7 for grades 8-11 premium)"
                    )

        # Concept id auto-fill + uniqueness
        if self.concepts:
            for idx, concept in enumerate(self.concepts):
                if not concept.id:
                    concept.id = f"mp-c{idx + 1}"
            ids = [c.id for c in self.concepts]
            if len(ids) != len(set(ids)):
                raise ValueError(
                    "MemoryPalaceGame: all concept id values must be unique after auto-fill"
                )

        return self


class MemoryPalaceConfig(_Permissive):
    """Authored config overrides for the Memory Palace game-break.

    All fields are optional; server-side defaults fill any omitted keys.
    See _MP_DEFAULTS in server/services/injector.py.
    """

    concept_count: Optional[int] = None             # default 5 server-side
    min_palace_options: Optional[int] = None         # default 4 server-side
    enable_reverse_recall: Optional[bool] = None     # default False; reserved for future
    concept_count_grade_overrides: Optional[Dict[str, int]] = None  # {"low": 3, "high": 7}


# --------------------------------------------------------------------------- #
# v2 flow (flow_version == "v2") — Case-Based Preview + Memory Check.
# All fields optional + extra="allow" so partial/draft authoring validates and
# new fields fail-open at the schema while the runtime redactor fails-closed.
# See docs/HOMEWORK_FLOW_V2_PLAN.md + docs/HOMEWORK_FLOW_V2_REACT_ARCHITECTURE.md.
# --------------------------------------------------------------------------- #


class CaseCheckpoint(_Permissive):
    """One of exactly 3 Case-Based Preview checkpoints (identify/decide/justify).

    answer_spec is the grading contract — stripped server-side before the React
    runtime ever sees it (runtime_redactor). learning_block is the post-submit
    teaching text, returned via the check-answer RESPONSE, not hydration.
    """

    kind: Optional[str] = None  # "identify" | "decide" | "justify"
    question: Optional[str] = None
    options: Optional[List[str]] = None
    answer_spec: Optional[AnswerSpec] = None
    learning_block: Optional[str] = None
    feedback: Optional[str] = None


class DecisionProcessExplanation(_Permissive):
    """Open-ended, AI-graded "Decision Process Explanation" step appended after
    the 3 CBP MCQ checkpoints (additive — absent on legacy/v1 homeworks).

    Student-visible fields (`prompt`, `min_chars`) survive hydration; everything
    else is answer-bearing and is stripped by the runtime redactor (the keyword
    buckets + `rubric` + `pass_score` are in ANSWER_BEARING_KEYS). The server
    reads the full object from the DB row to grade; the browser only ever sees
    `prompt` + `min_chars`.
    """

    # ---- Student-visible (survive redaction) ----
    prompt: Optional[str] = None
    min_chars: Optional[int] = None

    # ---- Answer-bearing (stripped before hydration; server-only grading anchors) ----
    concept_keywords: Optional[List[str]] = None
    method_keywords: Optional[List[str]] = None
    mistake_keywords: Optional[List[str]] = None
    acceptable_keywords: Optional[List[str]] = None
    rubric: Optional[Dict[str, Any]] = None
    pass_score: Optional[int] = None


class CaseBlock(_Permissive):
    """One entry in CaseBasedPreview.blocks[] — a PRESENTATION-ORDER overlay
    that lets authors interleave text pages and checkpoints in the sequence
    they want shown (additive; absent on legacy/v1 CBPs).

    A `blocks[]` entry is a presentation reference ONLY — it never carries
    grading data. `checkpoints[]` stays the canonical checkpoint list; a
    checkpoint block just points at it via `ref` = the index into
    `CaseBasedPreview.checkpoints`. So grading (ai.py
    `_check_answer_case_based_preview`) and gate_state index `checkpoints[ref]`
    unchanged, and redaction needs no new key: text blocks carry no answer
    fields, and a checkpoint block carries only an int `ref` (the answer lives
    in `checkpoints[].answer_spec`, already stripped server-side).
    """

    type: Optional[str] = None            # "text" | "checkpoint"
    # ---- text block (student-visible) ----
    title: Optional[str] = None
    body: Optional[str] = None
    # ---- checkpoint block — presentation-order reference into checkpoints[] ----
    ref: Optional[int] = None             # index into CaseBasedPreview.checkpoints


class CaseBasedPreview(_Permissive):
    """Tile A of the Learning Hub — guided 3-checkpoint real-life learning case."""

    title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    source_extraction: Optional[Dict[str, Any]] = None
    visual_plan: Optional[List[Dict[str, Any]]] = None
    case_setup: Optional[Dict[str, Any]] = None   # {story, role, task}
    checkpoints: Optional[List[CaseCheckpoint]] = None
    # Presentation-order overlay of text pages + checkpoint refs (additive).
    # A PRESENTATION layer only: `checkpoints[]` above stays canonical; a
    # checkpoint block carries `ref` = index into `checkpoints[]`. No grading
    # or redaction change — see CaseBlock docstring.
    blocks: Optional[List[CaseBlock]] = None
    # Open-ended AI-graded reasoning step after the 3 MCQ checkpoints (additive).
    decision_process_explanation: Optional[DecisionProcessExplanation] = None
    final_simulation: Optional[Dict[str, Any]] = None  # {correct_path(redacted), wrong_path}
    feedback_summary: Optional[Dict[str, Any]] = None
    completion_rules: Optional[Dict[str, Any]] = None


class MemoryCheckItem(_Permissive):
    """One Quizlet-style Memory Check item. answer_spec stripped server-side."""

    type: Optional[str] = None  # mcq | fill_blank | choose_explanation | true_false | tile_match | term_definition
    prompt: Optional[str] = None
    options: Optional[List[str]] = None
    answer_spec: Optional[AnswerSpec] = None
    flashcard_ref: Optional[str] = None


class MemoryCheck(_Permissive):
    """Tile B gate — Quizlet-style test after flashcards. Pass ≥ pass_threshold_pct."""

    items: Optional[List[MemoryCheckItem]] = None
    pass_threshold_pct: Optional[int] = None  # default 60 (runtime)
    modes_enabled: Optional[List[str]] = None
    retake_pool_size: Optional[int] = None


# --------------------------------------------------------------------------- #
# Practice Arc games (Ibo PR #248) — Memory Matching, Jigsaw Matching,        #
# Error Detection, Assembly. All `_Permissive` so the redactor can strip      #
# answer_spec / is_correct / acceptable_keywords / is_broken / expected_order #
# at the hydration boundary without schema churn.                             #
# --------------------------------------------------------------------------- #


class MemoryMatchingItem(_Permissive):
    """One memory-matching case per the Infra spec: 3 MCQ checkpoints
    (identify → decide → justify) + Decision-Process-Explanation (DPE) +
    consequence summary. The client renders one item; multiple items per
    homework just means more cases."""

    id: Optional[str] = None
    case_setup: Optional[str] = None
    pairs: Optional[List[Dict[str, Any]]] = None
    checkpoints: Optional[List[Dict[str, Any]]] = None       # each {question, options, correct_index⛔ | answer_spec}
    dpe: Optional[Dict[str, Any]] = None                     # {prompt, acceptable_keywords[]}
    dpe_prompt: Optional[str] = None
    expected_components: Optional[List[str]] = None          # server-only — DPE grading anchor
    consequence: Optional[Dict[str, Any]] = None             # {correct_path, wrong_path}


class JigsawMatchingItem(_Permissive):
    """One jigsaw-matching case per spec: pick two source-supported nodes
    that fit together, identify the relationship type, justify the choice."""

    id: Optional[str] = None
    case_setup: Optional[str] = None
    pieces: Optional[List[Dict[str, Any]]] = None            # {id, label, role}
    checkpoints: Optional[List[Dict[str, Any]]] = None
    dpe: Optional[Dict[str, Any]] = None
    dpe_prompt: Optional[str] = None
    expected_components: Optional[List[str]] = None          # server-only — DPE grading anchor
    consequence: Optional[Dict[str, Any]] = None


class ErrorDetectionItem(_Permissive):
    """One error-detection task per spec: a piece of work containing exactly
    one error. Student finds the broken block, then types the correction.
    Server grades both the spot and the correction text."""

    id: Optional[str] = None
    instructions: Optional[str] = None
    pattern: Optional[str] = None                            # "math" | "grammar" | "science"
    work_blocks: Optional[List[Dict[str, Any]]] = None       # {id, text, is_broken⛔}
    correction_answer_spec: Optional[AnswerSpec] = None      # server-only — AI/deterministic correction
    hint: Optional[str] = None
    why_prompt: Optional[str] = None                         # optional WHY-stage open-ended prompt


class AssemblyItem(_Permissive):
    """Order-the-pieces puzzle. Spec folder for Assembly is empty in the
    Infra zip; this is the minimal contract: ordered list of pieces +
    expected sequence. The student arranges pieces; server verifies order."""

    id: Optional[str] = None
    instructions: Optional[str] = None
    pieces: Optional[List[Dict[str, Any]]] = None            # {id, label}
    expected_order: Optional[List[str]] = None               # server-only — redactor strips


# --------------------------------------------------------------------------- #
# Division-3 Practices — 4 NEW Practice Arc games (per _DIV3_CONTRACT.md).     #
#                                                                               #
# All `_Permissive` (extra="allow"); every field Optional except `id`.         #
# Validators are ADVISORY only — they never raise at the PUT/PATCH boundary    #
# (the boundary must accept partial/draft authoring). Answer-bearing fields    #
# (`correct_index`, `expected_components`, `meter_deltas`, `best_cell_id`,     #
# `answer_case_id`, `breaks_rule`, `final_answer`, `correction_answer_spec`)   #
# are stripped at hydration via ANSWER_BEARING_KEYS — never schema-enforced.   #
# --------------------------------------------------------------------------- #


class SentenceRepairItem(_Permissive):
    """gb_sentence_repair — one broken sentence + 3 MCQ checkpoints
    (which-phrase-breaks-it → best-repair → which-explanation) + an open-ended
    Decision-Process-Explanation (DPE). Each checkpoint is a uniform MCQ
    `{q|question, options, correct_index⛔}`. `expected_components` anchors the
    DPE grading and is server-only."""

    id: Optional[str] = None
    broken_sentence: Optional[str] = None
    checkpoints: Optional[List[Dict[str, Any]]] = None       # each {q|question, options, correct_index⛔}
    dpe_prompt: Optional[str] = None
    expected_components: Optional[List[str]] = None          # server-only — DPE grading anchor

    @model_validator(mode="after")
    def _advise(self) -> "SentenceRepairItem":
        # Advisory only — never raises at the PUT boundary.
        return self


class TttGridItem(_Permissive):
    """gb_ttt_grid — a decision-grid game. A concept-checkpoint MCQ frames the
    rule, the student picks the best cell (`best_cell_id`), then a
    justify-checkpoint MCQ confirms the reasoning, followed by an open-ended
    DPE. Each cell carries `meter_deltas⛔` (per-meter score impact). `meters`
    is the student-visible list of meter names; `meter_deltas` + `best_cell_id`
    are server-only."""

    id: Optional[str] = None
    grid_size: Optional[str] = None                          # "3x3" | "2x2"
    concept_checkpoint: Optional[Dict[str, Any]] = None      # MCQ {q|question, options, correct_index⛔}
    cells: Optional[List[Dict[str, Any]]] = None             # {id, label, type, meter_deltas⛔}
    best_cell_id: Optional[str] = None                       # server-only — winning cell
    justify_checkpoint: Optional[Dict[str, Any]] = None      # MCQ {q|question, options, correct_index⛔}
    dpe_prompt: Optional[str] = None
    meters: Optional[List[str]] = None                       # student-visible meter names

    @model_validator(mode="after")
    def _advise(self) -> "TttGridItem":
        # Advisory only — never raises at the PUT boundary.
        return self


class ProblemTraceItem(_Permissive):
    """gb_problem_trace — a worked problem revealed step-by-step. Each step has
    a `reveal_text` (shown after the student commits) and a `predict` MCQ the
    student answers BEFORE the reveal. `final_answer⛔` is optional and
    server-only."""

    id: Optional[str] = None
    problem: Optional[str] = None
    steps: Optional[List[Dict[str, Any]]] = None             # {id, reveal_text, predict:MCQ{...,correct_index⛔}}
    final_answer: Optional[Union[str, int, float]] = None    # server-only (optional)

    @model_validator(mode="after")
    def _advise(self) -> "ProblemTraceItem":
        # Advisory only — never raises at the PUT boundary.
        return self


class CounterexampleItem(_Permissive):
    """gb_counterexample — a claim + candidate cases; the student picks the case
    that breaks the rule (`answer_case_id`). `breaks_rule` carries the broken
    rule text. An optional explanation MCQ + open-ended DPE follow. Both
    `answer_case_id` and `breaks_rule` are server-only."""

    id: Optional[str] = None
    claim: Optional[str] = None
    prompt: Optional[str] = None
    cases: Optional[List[Dict[str, Any]]] = None             # {id, label}
    answer_case_id: Optional[str] = None                     # server-only — the breaking case
    breaks_rule: Optional[str] = None                        # server-only — which rule it breaks
    explanation_checkpoint: Optional[Dict[str, Any]] = None  # optional MCQ {q|question, options, correct_index⛔}
    dpe_prompt: Optional[str] = None

    @model_validator(mode="after")
    def _advise(self) -> "CounterexampleItem":
        # Advisory only — never raises at the PUT boundary.
        return self


class DependencyChainItem(_Permissive):
    """gb_dependency_chain — TRANSFER / multi-step application. A scenario frames
    a problem; the student SOLVES a sequence of linked sub-questions where each
    answer feeds the next (Q1 → its result carries into Q2 → … → final). Each
    step is a uniform MCQ `{id, prompt, options, correct_index⛔, carry_label?}`.
    Distinct from problem_trace (which REVEALS a given worked solution) — here
    the student computes each linked step themselves. `correct_index` and
    `carry_label` are server-only (carry_label encodes the step's result, e.g.
    "x = 5 →", surfaced by the server ONLY after a correct answer)."""

    id: Optional[str] = None
    scenario: Optional[str] = None
    steps: Optional[List[Dict[str, Any]]] = None             # {id, prompt, options, correct_index⛔, carry_label?⛔}

    @model_validator(mode="after")
    def _advise(self) -> "DependencyChainItem":
        # Advisory only — never raises at the PUT boundary.
        return self


class ConfidenceCheckItem(_Permissive):
    """gb_confidence_check — metacognition. The student answers a uniform MCQ AND
    rates confidence (sure/maybe/guess). The CLIENT derives the calibration
    verdict from {correct, confidence} (e.g. Sure+Correct=Mastered,
    Sure+Wrong=Misconception, Guess+Correct=Lucky). The server only grades the
    MCQ; `correct_index` is server-only."""

    id: Optional[str] = None
    question: Optional[str] = None
    options: Optional[List[str]] = None
    correct_index: Optional[int] = None                      # server-only — index of the right option

    @model_validator(mode="after")
    def _advise(self) -> "ConfidenceCheckItem":
        # Advisory only — never raises at the PUT boundary.
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

    # v2 runtime dispatcher: absent/"v1" -> legacy HTML injector; "v2" -> React SPA.
    flow_version: Optional[str] = None
    # v2 Learning Sections (additive — legacy homeworks omit these).
    case_based_preview: Optional[CaseBasedPreview] = None
    memory_check: Optional[MemoryCheck] = None

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
    gb_ttt_config: Optional[TttConfig] = None
    gb_sentence_fill: Optional[List[SentenceFillItem]] = None
    # Tile Match — new structured pairs (replaces gb_memory_match for new content)
    gb_tile_match: Optional[List[TileMatchPair]] = None
    # Memory Palace — standalone Method-of-Loci game-break mechanic.
    # See MemoryPalaceGame / MemoryPalaceConfig docstrings + NAMESPACE NOTE above.
    gb_memory_palace: Optional[MemoryPalaceGame] = None
    gb_memory_palace_config: Optional[MemoryPalaceConfig] = None
    # Practice Arc games (Ibo PR #248) — answer-bearing fields stripped at
    # hydration (ANSWER_BEARING_KEYS).
    gb_memory_matching: Optional[List[MemoryMatchingItem]] = None
    gb_jigsaw_matching: Optional[List[JigsawMatchingItem]] = None
    gb_error_detection: Optional[List[ErrorDetectionItem]] = None
    gb_assembly: Optional[List[AssemblyItem]] = None
    # Division-3 Practices — 4 NEW games (per _DIV3_CONTRACT.md). Each list is an
    # array of full case items rendered sequentially by the React runtime; all
    # answer-bearing fields are stripped at the hydration boundary.
    gb_sentence_repair: Optional[List[SentenceRepairItem]] = None
    gb_ttt_grid: Optional[List[TttGridItem]] = None
    gb_problem_trace: Optional[List[ProblemTraceItem]] = None
    gb_counterexample: Optional[List[CounterexampleItem]] = None
    # Division-3 Practices — 2 MORE games (Dependency Chain = multi-step transfer;
    # Confidence Calibration = metacognition). Answer-bearing fields (correct_index
    # on both, carry_label on dependency-chain steps) stripped at hydration.
    gb_dependency_chain: Optional[List[DependencyChainItem]] = None
    gb_confidence_check: Optional[List[ConfidenceCheckItem]] = None

    # Phase 7
    reflection: Optional[ReflectionPhase] = None

    @model_validator(mode="after")
    def _validate_tile_match_collection(self):
        pairs = self.gb_tile_match
        if not pairs:
            return self
        if len(pairs) > 8:
            raise ValueError(
                f"gb_tile_match must have 0–8 pairs (got {len(pairs)}); "
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
