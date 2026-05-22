"""Boss Context Builder (Plan 5 §5).

Builds a compact, deterministic ``BossContext`` that the Boss Question
Generator and the Boss Answer Checker both consume. Pulls from the
homework row, recent ``phase_attempts`` for the session, and any cached
``session_metrics``. Never includes raw transcripts, full ``content_json``
phase trees, or ``answer_spec.expected`` keys — those would either bloat
the prompt or leak answers into a model that must not see them.
"""
from __future__ import annotations

import html as _html_lib
import re
from dataclasses import dataclass, asdict, field
from typing import Optional, Any

from ..db.homework_repo import get_homework
from ..db.attempts_repo import list_phase_attempts
from ..db.session_metrics_repo import get_session_metrics


# Bug A (2026-05-14 audit): authored boss_questions occasionally contain
# inline HTML markup the author used for visual emphasis
# (e.g. "<strong>Translate to English</strong>"). The LLM mirrors those
# tags into generated question_text, and the runtime renders question text
# via textContent (XSS safety) so the markup appears as literal characters
# on the student's screen. Strip server-side at every boundary where
# authored or LLM-generated question_text touches our pipeline.
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html_tags(text: str) -> str:
    """Remove HTML tags and unescape entities from ``text``. Always returns a
    string (empty when input is None/non-str). Does NOT preserve formatting
    — author's <strong>/<em>/<br> intent is dropped so the runtime sees clean
    text. Safe for use on both authored-stem extraction and post-generation
    question_text validation.
    """
    if not isinstance(text, str):
        return ""
    stripped = _HTML_TAG_RE.sub("", text)
    # Unescape after strip so an entity inside a tag attribute doesn't get
    # un-escaped into a stray quote/bracket.
    return _html_lib.unescape(stripped).strip()


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

# English snake_case identifier pattern. Catches things like "sign_error",
# "format_error", "relative_error", "linear_eq" — the style the LLM defaults
# to for "skill tags" because its training corpus is full of code-style
# identifiers. Doesn't fire on legitimate Uzbek skill names ("nisbiy xatolik")
# because those use spaces, not underscores.
#
# 2026-05-14 follow-up to Bug #3: this pattern is NO LONGER used to reject
# output generations (that produced 502s when the LLM persisted). Instead
# it's used as an INPUT filter — we scrub English snake_case from
# weak_topics/strong_topics before feeding them to the LLM, so the model
# can't mirror the English back into target_skill. See
# _scrub_english_snake_case_topics below + the prompt's "skill tag" framing
# is the underlying reason the LLM reaches for snake_case.
_ENGLISH_SNAKE_CASE_RE = re.compile(r"^[a-z]+(_[a-z]+)+$")


def _is_english_snake_case_term(term: str) -> bool:
    """True if ``term`` matches the English snake_case identifier pattern."""
    if not isinstance(term, str):
        return False
    return bool(_ENGLISH_SNAKE_CASE_RE.match(term.strip().lower()))


def _scrub_english_snake_case_topics(
    topics: list[str], language: Optional[str]
) -> list[str]:
    """For uz/ru lessons, drop English snake_case identifiers from a topics
    list before they reach the LLM prompt. Root cause of Bug #3 (2026-05-14):
    the boss-question-generator prompt tells the LLM to "target weak_topics[0]"
    and the LLM mirrors the value verbatim into ``target_skill``. Feeding it
    ``"sign_error"`` guarantees an English skill name in the output. Cleaning
    the INPUT side is the only way to break the echo cycle without rejecting
    valid generations server-side. For English homeworks, snake_case skill
    names are fine and pass through unchanged.
    """
    if language not in ("uz", "uz-cyrl", "ru"):
        return list(topics)
    return [t for t in topics if not _is_english_snake_case_term(t)]


def _detect_language_drift(
    question_text: str,
    target_skill: str,
    expected_language: Optional[str],
) -> Optional[str]:
    """Return a short reason string if the generated text appears to be
    English when the homework language is uz/ru; otherwise None.

    Only checks **English function-word density** across question_text +
    target_skill — threshold of 3+ hits, so a single borrowed word ("error",
    "PISA") doesn't trip the check. Snake_case-only target_skill values
    (e.g. "sign_error") are NOT a rejection signal here — they're scrubbed at
    the input side via :func:`_scrub_english_snake_case_topics` before the
    LLM ever sees them, which prevents the echo loop without producing 502s
    when the LLM persists with English identifiers.
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


# Subject → language inference (Fix B, 2026-05-13). When the homework's
# content_json.language is null, the prompt's output_language directive is
# missing too and Kimi falls back to its training-bias default (usually
# Uzbek for this codebase's data distribution, even on English homeworks).
# This table maps the subject string to a sensible language default.
# Subjects not listed fall through to 'uz' since the platform's primary
# audience is Uzbek students.
_SUBJECT_TO_LANGUAGE: dict[str, str] = {
    "english": "en",
    "russian": "ru",
}


def _infer_language_from_subject(subject: Optional[str]) -> Optional[str]:
    """Map a subject string (e.g. 'english', 'math-algebra', 'kimyo') to a
    language code. Returns None for unknown subjects so the caller can
    decide its own fallback rather than guessing wrong.
    """
    if not subject:
        return None
    return _SUBJECT_TO_LANGUAGE.get(subject.lower().strip())


def _default_policy(language: Optional[str], subject: Optional[str] = None) -> dict[str, Any]:
    # Language-resolution policy (2026-05-13 + 2026-05-20):
    #
    # The DB row's `language` field encodes the AUDIENCE language (the L1
    # of the Uzbek students this platform serves — currently always "uz"
    # on every prod row). It does NOT describe what the boss should
    # output in.
    #
    # The `subject` column is the actual lesson subject. The lesson
    # content (passages, vocabulary, boss questions) is written in the
    # subject's own working language: an English subject's content is in
    # English; a Biology subject taught in Uzbek schools has content in
    # Uzbek; a Russian subject in Russian. The boss should output in the
    # same language the lesson content already uses, so questions and
    # feedback land in the same script the student is reading.
    #
    # The mapping below resolves the subject string to that working
    # language. Subjects not in the map fall through to "uz" (platform
    # default — biology / history / kimyo / physics / geometriya /
    # math-algebra are all delivered in Uzbek on prod).
    #
    # Earlier (2026-05-13) only ran this inference when `language` was
    # falsy. Every real prod row has language="uz" (audience signal), so
    # the inference never fired on English-subject homeworks and Kimi
    # defaulted to Uzbek output. Subject-first inference fixes that.
    subject_language = _infer_language_from_subject(subject)
    if subject_language:
        language = subject_language
    elif not language:
        language = "uz"
    return {
        "target_weak_topics_first": True,
        "avoid_repetition": True,
        "max_question_length": 900,
        "language": language,
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
        # Bug A (2026-05-14): strip HTML from authored question text BEFORE
        # the LLM sees it. Authors sometimes write `<strong>Translate</strong>`
        # for visual emphasis; the LLM mirrors the tags into its output and
        # the runtime renders via textContent → student sees raw markup.
        raw_question_text = str(scrubbed.get("q") or scrubbed.get("prompt") or "")
        stem = {
            "question_text": _truncate(
                _strip_html_tags(raw_question_text),
                _MAX_QUESTION_TEXT_LEN,
            ),
            "tags": str(scrubbed.get("tags") or "")[:200],
            "hint": _truncate(_strip_html_tags(str(scrubbed.get("hint") or "")), 200),
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

    # Bug #3 follow-up (2026-05-14): scrub English snake_case identifiers
    # (e.g. "sign_error", "format_error") from EVERY topics list fed to the
    # LLM on uz/ru lessons. The LLM mirrors weak_topics[0] verbatim into
    # target_skill — feeding it an English token guarantees an English skill
    # tag in the output even with the prompt v4 "use the homework language"
    # banner. Cleaning the input prevents the echo loop without producing
    # 502s when output validation would otherwise have to reject persistent
    # English from the model.
    #
    # Scrubbed at three places: the aggregate weak_topics / strong_topics
    # AND each phase_summary's per-phase weak_topics / strong_topics
    # (the prompt's "Allowed inputs" exposes both).
    _input_language = (
        content_json.get("language") or (hw or {}).get("language") or None
    )
    if not _input_language:
        _input_language = _infer_language_from_subject(
            content_json.get("subject") or (hw or {}).get("subject")
        )
    weak_topics = _scrub_english_snake_case_topics(weak_topics, _input_language)
    strong_topics = _scrub_english_snake_case_topics(strong_topics, _input_language)
    for ps in phase_summaries:
        if isinstance(ps.get("weak_topics"), list):
            ps["weak_topics"] = _scrub_english_snake_case_topics(
                ps["weak_topics"], _input_language
            )
        if isinstance(ps.get("strong_topics"), list):
            ps["strong_topics"] = _scrub_english_snake_case_topics(
                ps["strong_topics"], _input_language
            )

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
    # Reuses the language already inferred above (with subject fallback for
    # null content_json.language).
    expected_language = _input_language
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
        boss_policy=_default_policy(
            language=content_json.get("language") or (hw or {}).get("language"),
            subject=content_json.get("subject") or (hw or {}).get("subject"),
        ),
        missing_context_flags=missing,
        authored_question_stems=stems,
        authored_difficulty_floor=authored_floor,
    )
