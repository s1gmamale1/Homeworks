"""Academic-integrity signal engine (foundations — NOT yet wired).

Per ``docs/NETS_Academic_Integrity_AntiCheat_Research.md``: integrity signals
are **teacher intelligence**, never an auto grade-penalty or hard block. This
module is a *pure* flag engine — it reads nothing, writes nothing, calls no DB,
no LLM, no clock. It maps a single ``IntegritySignalInput`` + an
``AntiCheatPolicy`` to a list of advisory ``IntegrityFlag``s.

Design invariants (the research's FAIRNESS-FIRST rule):
  - Every detector is CONSERVATIVE and OPT-IN. A slow, careful, non-native
    English speaker must never be flagged. When in doubt, emit nothing.
  - Signals are ADVISORY. Nothing here touches score / is_correct / XP. The
    integration agent decides how (and whether) a flag surfaces to a teacher.
  - The thresholds live as module DEFAULT constants so a future authoring layer
    can tune them per-homework via the policy without editing the rules.

A second agent threads these into the submit flow; this module ships standalone
and fully unit-tested.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# --- Severity vocabulary -----------------------------------------------------
# Kept as a tuple (not an Enum) so the dataclass stays a plain value object and
# the integration agent can map these to whatever review-queue severity it uses.
SEVERITY_LOW = "low"
SEVERITY_MEDIUM = "medium"
SEVERITY_STRONG = "strong"
_VALID_SEVERITIES = (SEVERITY_LOW, SEVERITY_MEDIUM, SEVERITY_STRONG)


# --- DEFAULT thresholds ------------------------------------------------------
# These are the *engine* defaults. The per-homework policy overrides the floors
# that need tuning (response-time floor, paste, sudden-mastery toggle). The
# sudden-mastery numeric bounds below are deliberately wide so the flag only
# fires on a stark before/after gap, never on a student who was simply ready.
DEFAULT_SUDDEN_MASTERY_PRE_CEILING = 0.40   # pre-assessment mastery must be <= this
DEFAULT_SUDDEN_MASTERY_POST_FLOOR = 0.90    # assessment correct-rate must be >= this
DEFAULT_SUDDEN_MASTERY_MIN_ITEMS = 3        # need enough items for the rate to mean anything


@dataclass(frozen=True)
class IntegrityFlag:
    """One advisory integrity signal. Never an input to grading.

    ``reason_code`` is a stable machine key (e.g. ``"too_fast"``); ``severity``
    is one of ``{"low","medium","strong"}``; ``detail`` carries the
    human-readable evidence the teacher sees (thresholds + the observed value).
    """

    reason_code: str
    severity: str
    detail: dict


@dataclass(frozen=True)
class IntegritySignalInput:
    """A single gradeable interaction's integrity-relevant facts.

    Every field the integration layer can cheaply observe. ``None`` means
    "unknown / not measured" — and every detector treats unknown as
    *no-signal*, never as suspicious.
    """

    phase: str
    subphase: Optional[str]
    is_assessment: bool
    time_ms: Optional[int]
    paste_detected: bool
    pre_assessment_mastery: Optional[float]
    assessment_correct_rate: Optional[float]
    assessment_item_count: int
    grade: Optional[int]


@dataclass(frozen=True)
class AntiCheatPolicy:
    """Per-homework integrity policy. Conservative + opt-in by construction.

    ``paste_detect`` and the ``response_time_floor_ms`` are OFF by default
    (False / 0) so a homework that never opts in produces ZERO flags. Only
    ``sudden_mastery_enabled`` defaults on, because that detector is already
    bounded by a stark before/after gap and a minimum item count.
    """

    paste_detect: bool = False
    response_time_floor_ms: int = 0          # 0 = disabled (opt-in)
    sudden_mastery_enabled: bool = True


def policy_from_boss_meta(boss_meta: Optional[dict]) -> AntiCheatPolicy:
    """Build an ``AntiCheatPolicy`` from a homework's ``boss_meta.anti_cheat``.

    Fail-safe: any missing / malformed input collapses to the conservative
    defaults (paste OFF, time-floor OFF, sudden-mastery ON). Unknown keys are
    ignored. Negative / non-int time floors clamp to 0 (disabled).
    """
    if not isinstance(boss_meta, dict):
        return AntiCheatPolicy()

    raw = boss_meta.get("anti_cheat")
    if not isinstance(raw, dict):
        return AntiCheatPolicy()

    paste = bool(raw.get("paste_detect", False))

    floor_raw = raw.get("response_time_floor_ms", 0)
    try:
        floor = int(floor_raw)
    except (TypeError, ValueError):
        floor = 0
    if floor < 0:
        floor = 0

    # sudden_mastery defaults ON; only an explicit False disables it.
    sudden = raw.get("sudden_mastery_enabled", True)
    sudden_enabled = bool(sudden) if sudden is not None else True

    return AntiCheatPolicy(
        paste_detect=paste,
        response_time_floor_ms=floor,
        sudden_mastery_enabled=sudden_enabled,
    )


def _flag_too_fast(
    inp: IntegritySignalInput, policy: AntiCheatPolicy
) -> Optional[IntegrityFlag]:
    """LOW: a measured response time below an opt-in floor.

    Only fires when the floor is explicitly enabled (> 0) AND we actually
    measured a time. A missing time is never suspicious.
    """
    floor = policy.response_time_floor_ms
    if floor <= 0:
        return None
    if inp.time_ms is None:
        return None
    if inp.time_ms < floor:
        return IntegrityFlag(
            reason_code="too_fast",
            severity=SEVERITY_LOW,
            detail={"time_ms": inp.time_ms, "floor_ms": floor},
        )
    return None


def _flag_paste_on_assessment(
    inp: IntegritySignalInput, policy: AntiCheatPolicy
) -> Optional[IntegrityFlag]:
    """MEDIUM: a paste during an assessment phase, when paste-detect is opted in.

    Pasting outside an assessment (e.g. into a practice scratchpad) is never
    flagged — copying a worked example to study is legitimate.
    """
    if not policy.paste_detect:
        return None
    if not inp.is_assessment:
        return None
    if not inp.paste_detected:
        return None
    return IntegrityFlag(
        reason_code="paste_on_assessment",
        severity=SEVERITY_MEDIUM,
        detail={"phase": inp.phase, "subphase": inp.subphase},
    )


def _flag_sudden_mastery(
    inp: IntegritySignalInput, policy: AntiCheatPolicy
) -> Optional[IntegrityFlag]:
    """STRONG: a stark low-then-near-perfect jump across the assessment boundary.

    Fires only when ALL hold:
      - the detector is enabled, and
      - pre-assessment mastery is known and <= the (low) ceiling, and
      - assessment correct-rate is known and >= the (high) floor, and
      - there were enough items for the rate to be meaningful.

    A student who was genuinely ready (moderate pre-mastery) or who only
    answered 1-2 items cannot trip this.
    """
    if not policy.sudden_mastery_enabled:
        return None
    pre = inp.pre_assessment_mastery
    post = inp.assessment_correct_rate
    if pre is None or post is None:
        return None
    if inp.assessment_item_count < DEFAULT_SUDDEN_MASTERY_MIN_ITEMS:
        return None
    if pre <= DEFAULT_SUDDEN_MASTERY_PRE_CEILING and post >= DEFAULT_SUDDEN_MASTERY_POST_FLOOR:
        return IntegrityFlag(
            reason_code="sudden_mastery",
            severity=SEVERITY_STRONG,
            detail={
                "pre_assessment_mastery": pre,
                "assessment_correct_rate": post,
                "assessment_item_count": inp.assessment_item_count,
                "pre_ceiling": DEFAULT_SUDDEN_MASTERY_PRE_CEILING,
                "post_floor": DEFAULT_SUDDEN_MASTERY_POST_FLOOR,
            },
        )
    return None


def _flag_sophistication_jump(
    inp: IntegritySignalInput, policy: AntiCheatPolicy
) -> Optional[IntegrityFlag]:
    """STUB (v1 → always None).

    The research §intent is to flag a sudden leap in *linguistic / reasoning
    sophistication* relative to a student's established baseline (e.g. a B1
    writer suddenly producing C2 prose). That requires a per-student style
    baseline we do not yet collect, and a non-native-speaker population makes a
    naive version dangerously unfair. Documented + reserved; emits nothing.
    """
    return None


# Detector registry — order is the order flags appear in the returned list.
_DETECTORS = (
    _flag_too_fast,
    _flag_paste_on_assessment,
    _flag_sudden_mastery,
    _flag_sophistication_jump,
)


def compute_flags(
    inp: IntegritySignalInput, policy: AntiCheatPolicy
) -> list[IntegrityFlag]:
    """Run every detector and return the list of advisory flags (possibly empty).

    Pure: deterministic, no I/O, no side effects. A fully-default policy on a
    non-assessment interaction returns ``[]``.
    """
    flags: list[IntegrityFlag] = []
    for detector in _DETECTORS:
        flag = detector(inp, policy)
        if flag is not None:
            # Defensive: never emit an out-of-vocabulary severity.
            if flag.severity in _VALID_SEVERITIES:
                flags.append(flag)
    return flags
