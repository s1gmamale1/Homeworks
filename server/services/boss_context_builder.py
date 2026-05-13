"""Boss Context Builder (Plan 5 §5).

Builds a compact, deterministic ``BossContext`` that the Boss Question
Generator and the Boss Answer Checker both consume. Pulls from the
homework row, recent ``phase_attempts`` for the session, and any cached
``session_metrics``. Never includes raw transcripts, full ``content_json``
phase trees, or ``answer_spec.expected`` keys — those would either bloat
the prompt or leak answers into a model that must not see them.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict, field
from typing import Optional, Any

from ..db.homework_repo import get_homework
from ..db.attempts_repo import list_phase_attempts
from ..db.session_metrics_repo import get_session_metrics


# Fields the LLM must never see, anywhere in the boss context.
_ANSWER_LEAK_KEYS: tuple[str, ...] = (
    "expected",
    "expected_answer",
    "ans",
    "answers",
    "accepted_answers",
    "correct",
    "canonical",
    "answer_spec",
)

# Field-length caps inside the boss prompt. The orchestrator's
# ``build_input_section`` enforces a top-level cap; these inner caps keep
# any single phase summary or topic list from dominating the budget.
_MAX_PHASE_SUMMARIES = 8
_MAX_TOPICS = 12
_MAX_ASKED_QUESTIONS_IN_CTX = 10
_MAX_QUESTION_TEXT_LEN = 600
_MAX_AUTHORED_STEMS_IN_CTX = 10

# Discrete difficulty buckets — used here for authored_difficulty inference,
# imported by boss_dynamic.py for the per-skill difficulty floor clamp.
_DIFFICULTY_RANK = {"easy": 0, "medium": 1, "hard": 2}


# ---- Language-drift detection (Bug #9 fix, 2026-05-13 audit) ---------------
# Originally lived in boss_dynamic; moved here so build_boss_context can also
# use it to filter asked_questions before sending to Kimi (Option B fix,
# 2026-05-13). Re-exported from boss_dynamic for backward compatibility.
#
# Detection is conservative: counts English function-word tokens that have no
# Uzbek/Russian cognates. A threshold of 3+ hits means single borrowed words
# ("error", "PISA", "Bloom") don't trip the check.
_ENGLISH_INDICATOR_WORDS = frozenset({
    "the", "is", "of", "and", "in", "to", "a", "for", "with", "as",
    "that", "this", "are", "was", "were", "be", "been", "by", "on",
    "at", "an", "or", "but", "not", "what", "which", "who", "how",
    "if", "then", "than", "from",
})


def _detect_language_drift(
    question_text: str,
    target_skill: str,
    expected_language: Optional[str],
) -> Optional[str]:
    """Return a short reason string if the generated text appears to be
    English when the homework language is uz/ru; otherwise None.
    """
    if expected_language not in ("uz", "uz-cyrl", "ru"):
        return None
    combined = f"{question_text} {target_skill}".lower()
    tokens = re.findall(r"\b[a-z]+\b", combined)
    if not tokens:
        return None
    english_hits = sum(1 for t in tokens if t in _ENGLISH_INDICATOR_WORDS)
    if english_hits >= 3:
        return (
            f"language_drift: expected={expected_language!r}, "
            f"detected English ({english_hits} indicator words)"
        )
    return None


@dataclass
class BossContext:
    session_id: str
    homework_id: str
    homework_title: str
    subject: str
    grade: int
    phase_summaries: list[dict[str, Any]] = field(default_factory=list)
    overall_metrics: dict[str, Any] = field(default_factory=dict)
    weak_topics: list[str] = field(default_factory=list)
    strong_topics: list[str] = field(default_factory=list)
    asked_questions: list[dict[str, Any]] = field(default_factory=list)
    recent_boss_phrases: list[str] = field(default_factory=list)
    boss_policy: dict[str, Any] = field(default_factory=dict)
    missing_context_flags: list[str] = field(default_factory=list)
    authored_question_stems: list[dict[str, Any]] = field(default_factory=list)
    authored_difficulty_floor: Optional[str] = None  # "easy" | "medium" | "hard"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _scrub_dict(node: Any) -> Any:
    """Recursively drop any answer-leak key from a nested structure."""
    if isinstance(node, dict):
        return {
            k: _scrub_dict(v)
            for k, v in node.items()
            if k not in _ANSWER_LEAK_KEYS
        }
    if isinstance(node, list):
        return [_scrub_dict(item) for item in node]
    return node


def _truncate(text: str, limit: int) -> str:
    if not isinstance(text, str):
        return ""
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _dmg_to_difficulty(dmg: Any) -> str:
    """Map authored damage value to difficulty bucket. 10→easy, 20→medium, 30→hard.
    Default medium when missing/unknown so absent dmg doesn't accidentally
    floor-anchor at 'easy' which would let the LLM drop arbitrarily low."""
    try:
        d = int(dmg)
    except (TypeError, ValueError):
        return "medium"
    if d <= 10:
        return "easy"
    if d >= 30:
        return "hard"
    return "medium"


def _pool_max_difficulty(stems: list[dict]) -> Optional[str]:
    """Return the pool's hardest authored difficulty — fallback floor when
    target_skill matches no stem. None when pool is empty."""
    if not stems:
        return None
    ranks = [_DIFFICULTY_RANK[s.get("authored_difficulty", "medium")] for s in stems]
    return ["easy", "medium", "hard"][max(ranks)]


def _phase_summary_from_attempts(attempts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group attempts by phase/subphase and emit per-phase scoring rollups.

    Deterministic. Topic extraction comes from misconception_tags_json when
    present — otherwise the phase contributes only score/attempt counts. We
    deliberately do not invoke an LLM here; this is the cheap pre-prompt
    step that makes the generator prompt small.
    """
    if not attempts:
        return []

    by_phase: dict[str, dict[str, Any]] = {}
    for a in attempts:
        phase = a.get("phase") or "unknown"
        bucket = by_phase.setdefault(
            phase,
            {
                "phase": phase,
                "attempts": 0,
                "correct": 0,
                "scores": [],
                "weak_topics": set(),
                "strong_topics": set(),
            },
        )
        bucket["attempts"] += 1
        if a.get("correct") == 1:
            bucket["correct"] += 1
        score = a.get("score")
        if isinstance(score, (int, float)):
            bucket["scores"].append(float(score))

        # misconception_tags_json is stored as JSON-encoded list[str]
        import json as _json
        tags_raw = a.get("misconception_tags_json")
        try:
            tags = _json.loads(tags_raw) if isinstance(tags_raw, str) else (tags_raw or [])
        except Exception:
            tags = []
        if isinstance(tags, list):
            for tag in tags:
                if isinstance(tag, str) and tag:
                    if a.get("correct") == 1:
                        bucket["strong_topics"].add(tag)
                    else:
                        bucket["weak_topics"].add(tag)

    summaries: list[dict[str, Any]] = []
    for bucket in by_phase.values():
        attempts_n = bucket["attempts"]
        if not attempts_n:
            continue
        avg_score = sum(bucket["scores"]) / len(bucket["scores"]) if bucket["scores"] else 0.0
        summaries.append({
            "phase": bucket["phase"],
            "attempts": attempts_n,
            "correct": bucket["correct"],
            "score": round(avg_score, 3),
            "accuracy": round(bucket["correct"] / attempts_n, 3),
            "weak_topics": sorted(bucket["weak_topics"])[:_MAX_TOPICS],
            "strong_topics": sorted(bucket["strong_topics"])[:_MAX_TOPICS],
        })
    summaries.sort(key=lambda s: s["score"])
    return summaries[:_MAX_PHASE_SUMMARIES]


def _aggregate_topics(summaries: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    weak: dict[str, int] = {}
    strong: dict[str, int] = {}
    for s in summaries:
        for t in s.get("weak_topics") or []:
            weak[t] = weak.get(t, 0) + 1
        for t in s.get("strong_topics") or []:
            strong[t] = strong.get(t, 0) + 1
    weak_sorted = sorted(weak.items(), key=lambda kv: -kv[1])
    strong_sorted = sorted(strong.items(), key=lambda kv: -kv[1])
    return [t for t, _ in weak_sorted[:_MAX_TOPICS]], [t for t, _ in strong_sorted[:_MAX_TOPICS]]


def _default_policy(language: Optional[str]) -> dict[str, Any]:
    return {
        "target_weak_topics_first": True,
        "avoid_repetition": True,
        "max_question_length": 900,
        "language": language or "uzbek_or_student_language",
    }


async def build_boss_context(
    session_id: str,
    homework_id: str,
    *,
    asked_questions: Optional[list[dict[str, Any]]] = None,
    recent_boss_phrases: Optional[list[str]] = None,
) -> BossContext:
    """Build a BossContext from session metrics + recent phase attempts.

    Tolerant of missing pieces — sets ``missing_context_flags`` instead of
    raising, so the boss can still function on a fresh session that has no
    metrics yet (Plan 5 acceptance test 1).
    """
    missing: list[str] = []

    hw = await get_homework(homework_id) if homework_id else None
    if not hw:
        missing.append("missing_homework")
    content_json = (hw or {}).get("content_json") or {}

    raw_qs = content_json.get("boss_questions") or []
    stems: list[dict] = []
    for q in raw_qs[:_MAX_AUTHORED_STEMS_IN_CTX]:
        if not isinstance(q, dict):
            continue
        scrubbed = _scrub_dict(q)  # strips expected/ans/accepted_answers/answer_spec
        stem = {
            "question_text": _truncate(
                str(scrubbed.get("q") or scrubbed.get("prompt") or ""),
                _MAX_QUESTION_TEXT_LEN,
            ),
            "tags": str(scrubbed.get("tags") or "")[:200],
            "hint": _truncate(str(scrubbed.get("hint") or ""), 200),
            "authored_difficulty": _dmg_to_difficulty(scrubbed.get("dmg")),
        }
        if stem["question_text"]:
            stems.append(stem)
    authored_floor = _pool_max_difficulty(stems)

    attempts = []
    if session_id and homework_id:
        try:
            attempts = await list_phase_attempts(session_id, homework_id, limit=200)
        except Exception:
            attempts = []
    if not attempts:
        missing.append("no_attempts")

    phase_summaries = _phase_summary_from_attempts(attempts)
    weak_topics, strong_topics = _aggregate_topics(phase_summaries)

    metrics: dict[str, Any] = {}
    if session_id and homework_id:
        try:
            metrics = await get_session_metrics(session_id, homework_id) or {}
        except Exception:
            metrics = {}
    if not metrics:
        missing.append("empty_metrics")

    # Compress asked_questions for the generator (cap count + text length;
    # scrub any leaked answer keys).
    #
    # Option B fix (2026-05-13 audit): for uz/ru homeworks, drop any prior
    # generations whose text looks English BEFORE applying the chronological
    # [-N:] slice. Past buggy generations would otherwise feed back into the
    # in-context-learning signal and pull subsequent generations toward
    # English even with the v3+ language directive. The drift detector is
    # the same one used for live output validation.
    expected_language = (
        content_json.get("language") or (hw or {}).get("language") or None
    )
    candidate_qs: list[dict[str, Any]] = []
    for q in (asked_questions or []):
        if not isinstance(q, dict):
            continue
        if expected_language and _detect_language_drift(
            str(q.get("question_text") or ""),
            str(q.get("target_skill") or ""),
            expected_language,
        ):
            continue  # drop language-drifted prior generation from context
        candidate_qs.append(q)
    asked_clean: list[dict[str, Any]] = []
    for q in candidate_qs[-_MAX_ASKED_QUESTIONS_IN_CTX:]:
        scrubbed = _scrub_dict(q)
        if "question_text" in scrubbed:
            scrubbed["question_text"] = _truncate(
                str(scrubbed.get("question_text") or ""), _MAX_QUESTION_TEXT_LEN
            )
        asked_clean.append(scrubbed)

    return BossContext(
        session_id=session_id,
        homework_id=homework_id,
        homework_title=str(content_json.get("title") or (hw or {}).get("title") or ""),
        subject=str(content_json.get("subject") or (hw or {}).get("subject") or ""),
        grade=int(content_json.get("grade") or (hw or {}).get("grade") or 0),
        phase_summaries=phase_summaries,
        overall_metrics=metrics,
        weak_topics=weak_topics,
        strong_topics=strong_topics,
        asked_questions=asked_clean,
        recent_boss_phrases=list(recent_boss_phrases or [])[:5],
        boss_policy=_default_policy(content_json.get("language") or (hw or {}).get("language")),
        missing_context_flags=missing,
        authored_question_stems=stems,
        authored_difficulty_floor=authored_floor,
    )
