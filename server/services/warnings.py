"""Warning state machine for the tutor anti-troll system.

Calls flow:
    routes/ai.py → slur_filter.classify(message)
                 → warnings.evaluate(classification, hw_id, session_id)
                 → routes/ai.py acts on outcome (fail short-circuit OR
                   inject context into tutor.tutor_chat())
"""
from __future__ import annotations

from dataclasses import dataclass

from server.services.slur_filter import SlurClassification
from server import db

# Severities that increment the counter immediately (no repetition gate):
HARD_SEVERITIES = frozenset({"profanity_mild", "profanity_strong",
                              "slur_or_hate", "sexual_vulgar"})
# Severities that increment ONLY if repeated 3+ times in last 5 turns:
SOFT_SEVERITIES = frozenset({"insult_mild"})
# Severities that NEVER increment:
SAFE_SEVERITIES = frozenset({"casual_safe", "casual_negative"})

DEDUCTION_AT_LEVEL_7 = 5     # %
DEDUCTION_AT_LEVEL_8 = 10    # %
FAIL_AT_LEVEL = 9


@dataclass(frozen=True)
class WarningOutcome:
    triggered: bool          # True iff this message produced a warning record
    level: int               # post-eval count (0 if not triggered and no priors)
    deduction_pct_this: int  # 0/5/10 — points deducted ON THIS specific event
    cumulative_deduction_pct: int  # total deductions stored for this hw across all events
    is_big_warning: bool     # level == 8
    is_fail: bool            # level >= 9
    severity: str            # echoes classification.severity
    category: str            # echoes classification.category
    lang: str                # echoes classification.lang
    matched_terms: list      # echoes classification.matched_terms
    behavior_summary: str    # from db.summary_for_tutor()


async def evaluate(
    classification: SlurClassification,
    *,
    hw_id: str,
    session_id: str,
) -> WarningOutcome:
    """Decides whether this message triggers a warning + persists if so.

    Always returns an outcome (even for clean messages) so the route layer
    can pass severity + behavior_summary into the prompt context.
    """
    sev = classification.severity
    summary = await db.summary_for_tutor(hw_id)

    # No-op cases: clean message OR safe register
    if classification.is_clean or sev in SAFE_SEVERITIES:
        prior_count = await db.count_warnings_for_hw(hw_id)
        prior_deductions = await db.sum_deductions(hw_id)
        return WarningOutcome(
            triggered=False,
            level=prior_count,
            deduction_pct_this=0,
            cumulative_deduction_pct=prior_deductions,
            is_big_warning=False,
            is_fail=False,
            severity=sev,
            category=classification.category,
            lang=classification.lang,
            matched_terms=list(classification.matched_terms),
            behavior_summary=summary,
        )

    # SOFT_SEVERITIES gate: same category 3+ times in last 5 turns?
    if sev in SOFT_SEVERITIES:
        recent = await db.list_recent_warnings(hw_id, limit=5)
        same_cat_count = sum(
            1 for r in recent if r.get("category") == classification.category
        )
        if same_cat_count < 3:
            # Not yet triggering — still emit varied tease, no record
            prior_count = await db.count_warnings_for_hw(hw_id)
            prior_deductions = await db.sum_deductions(hw_id)
            return WarningOutcome(
                triggered=False,
                level=prior_count,
                deduction_pct_this=0,
                cumulative_deduction_pct=prior_deductions,
                is_big_warning=False,
                is_fail=False,
                severity=sev,
                category=classification.category,
                lang=classification.lang,
                matched_terms=list(classification.matched_terms),
                behavior_summary=summary,
            )
        # Falls through: increment counter

    # Increment path
    prior_count = await db.count_warnings_for_hw(hw_id)
    new_level = prior_count + 1
    deduction_this = 0
    big = False
    fail = False

    if new_level == 7:
        deduction_this = DEDUCTION_AT_LEVEL_7
    elif new_level == 8:
        deduction_this = DEDUCTION_AT_LEVEL_8
        big = True
    elif new_level >= FAIL_AT_LEVEL:
        fail = True

    matched_term = (
        classification.matched_terms[0] if classification.matched_terms else None
    )
    await db.add_warning(
        session_id=session_id,
        hw_id=hw_id,
        severity=sev,
        category=classification.category,
        matched_term=matched_term,
        warning_level=new_level,
        deduction_pct=deduction_this,
        is_big_warning=big,
        is_fail=fail,
    )

    cumulative = await db.sum_deductions(hw_id)

    # Refresh summary AFTER insert so the new event is included
    fresh_summary = await db.summary_for_tutor(hw_id)

    return WarningOutcome(
        triggered=True,
        level=new_level,
        deduction_pct_this=deduction_this,
        cumulative_deduction_pct=cumulative,
        is_big_warning=big,
        is_fail=fail,
        severity=sev,
        category=classification.category,
        lang=classification.lang,
        matched_terms=list(classification.matched_terms),
        behavior_summary=fresh_summary,
    )
