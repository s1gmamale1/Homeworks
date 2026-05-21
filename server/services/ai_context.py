"""
AI Context Builder — single backend authority for what the AI receives.

Produces a canonical TutorContextPacket from session + homework + frontend state.
Every AI call should stop manually assembling random payloads in route handlers.
"""
import logging
import re
from dataclasses import dataclass, field
from typing import Optional, Any

from server.db.homework_repo import get_homework
from server.db.session_repo import get_session
from server.db.attempts_repo import list_phase_attempts
from server.db.session_metrics_repo import get_session_metrics
from server.db.tutor_repo import list_tutor_turns
from server.db import session_events_repo

_log = logging.getLogger("nets.ai_context")

@dataclass
class TutorContextPacket:
    session_id: str
    hw_id: str
    phase: str
    subphase: Optional[str] = None
    current_question_id: Optional[str] = None
    subject: str = ""
    grade: int = 0
    homework_title: str = ""
    homework_summary: str = ""
    current_phase_content: dict = field(default_factory=dict)
    current_question_text: str = ""
    current_question_context: Optional[dict] = None
    visible_screen_text: str = ""
    student_work_text: str = ""
    recent_chat_history: list[dict] = field(default_factory=list)
    recent_attempts: list[dict] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    warnings_summary: str = ""
    missing_context_flags: list[str] = field(default_factory=list)
    context_packet_version: str = "tutor.v2"


def extract_phase_content(content_json: dict, subphase: Optional[str]) -> dict:
    """Extract a relevant subset of phase content to reduce AI context size."""
    if not subphase:
        return {}

    extracted = {}
    if subphase == "preview":
        extracted["preview_data"] = content_json.get("preview", {})
    elif subphase == "memory-sprint":
        extracted["memory_sprint_data"] = content_json.get("memory-sprint", {})
    elif subphase == "sentence-fill":
        extracted["sentence_fill_data"] = content_json.get("sentence-fill", {})
    elif subphase == "tile-match":
        extracted["tile_match_data"] = content_json.get("tile-match", {})
    elif subphase == "real-life-challenge":
        extracted["real_life_challenge_data"] = content_json.get("real-life-challenge", {})
    elif subphase == "final-boss":
        extracted["final_boss_data"] = content_json.get("final-boss", {})
    elif subphase == "reflection":
        extracted["reflection_data"] = content_json.get("reflection", {})
    else:
        extracted["raw_subphase"] = content_json.get(subphase, {})

    return extracted


def summarize_homework_content(content_json: dict) -> dict:
    """Summarize the full homework content_json."""
    return {
        "title": content_json.get("title", ""),
        "subject": content_json.get("subject", ""),
        "grade": content_json.get("grade", 0),
        "summary": content_json.get("summary", ""),
        "phases_available": list(content_json.keys()),
    }


def _find_question_in_content(content: dict, question_id: str) -> Optional[dict]:
    """Best-effort lookup for a question dict by id, walking nested structures."""
    if not isinstance(content, dict) or not question_id:
        return None

    def _walk(node):
        if isinstance(node, dict):
            if node.get("question_id") == question_id or node.get("id") == question_id:
                return node
            for v in node.values():
                hit = _walk(v)
                if hit is not None:
                    return hit
        elif isinstance(node, list):
            for item in node:
                hit = _walk(item)
                if hit is not None:
                    return hit
        return None

    return _walk(content)


# CBP-aware redactor lives in tutor_redaction.py (single source of truth
# shared with services/tutor.py). Backend-integration-audit finding #1:
# this module's previous copy did NOT have the CBP phase branch or the
# _TUTOR_CONTEXT_CBP_EXTRA_KEYS allow-list, so PR #2's CBP coupling was
# dead code on the live tutor route until this import landed.
from .tutor_redaction import _redact_question_for_tutor  # noqa: E402, F401


def sanitize_screen_context_v2(
    text: str, expected_values: list[str] | None = None
) -> dict:
    """Layered sanitizer: scrub answer-bearing markers without deleting whole lines.

    Returns a dict with cleaned text and diagnostics.
    """
    raw = str(text or "")
    cleaned = raw

    # Remove answer-key labels but not whole line
    cleaned = re.sub(
        r"answer\s*key\s*[:=]\s*\S+", "[redacted answer key]", cleaned, flags=re.I
    )
    # Remove data-expected/data-answer HTML attributes
    cleaned = re.sub(
        r"data-(expected|answer)\s*=\s*['\"][^'\"]+['\"]", "", cleaned, flags=re.I
    )
    # Remove class attributes that contain correct/answer-key
    cleaned = re.sub(
        r"class\s*=\s*['\"][^'\"]*\b(?:correct|is-correct|answer-key)\b[^'\"]*['\"]",
        "",
        cleaned,
        flags=re.I,
    )
    # Remove data-correct=true
    cleaned = re.sub(r"data-correct\s*=\s*['\"]?true['\"]?", "", cleaned, flags=re.I)

    for value in expected_values or []:
        if value:
            cleaned = re.sub(re.escape(value), "[redacted]", cleaned, flags=re.I)

    cleaned = re.sub(r"\s+", " ", cleaned).strip()[:1800]

    return {
        "text": cleaned,
        "raw_len": len(raw),
        "clean_len": len(cleaned),
        "redacted": raw != cleaned,
    }


async def build_tutor_context(
    *,
    session_id: str,
    hw_id: str,
    phase: Optional[str] = None,
    subphase: Optional[str] = None,
    question_id: Optional[str] = None,
    screen_context: Optional[str] = None,
    student_work_text: Optional[str] = None,
    ui_state: Optional[dict] = None,
) -> TutorContextPacket:
    """Build a canonical TutorContextPacket from backend state + frontend payload.

    Resolution order:
      1. Load homework by hw_id.
      2. Load session row.
      3. Determine phase: request > session.current_phase > fallback "preview".
      4. Determine question_id: request > session.current_question_id > None.
      5. Find question in content_json.
      6. Build safe question context.
      7. Clean screen context.
      8. Attach recent attempts and metrics.
    """
    flags: list[str] = []

    # 1. Homework
    hw = await get_homework(hw_id) if hw_id else None
    if not hw:
        flags.append("missing_hw")
        return TutorContextPacket(
            session_id=session_id or "",
            hw_id=hw_id or "",
            phase=phase or "preview",
            missing_context_flags=flags,
        )

    content_json = hw.get("content_json") or {}
    subject = content_json.get("subject", hw.get("subject", ""))
    grade = int(content_json.get("grade", hw.get("grade", 0)) or 0)
    homework_title = content_json.get("title", hw.get("title", ""))

    # 2. Session
    session_row = None
    try:
        session_row = await get_session(session_id) if session_id else None
    except Exception as exc:
        _log.warning("build_tutor_context: failed to load session: %s", exc)
        flags.append("missing_session")

    # 3. Phase resolution
    resolved_phase = phase
    if not resolved_phase and session_row:
        resolved_phase = session_row.get("current_phase")
    if not resolved_phase:
        resolved_phase = "preview"

    resolved_subphase = subphase
    if not resolved_subphase and session_row:
        resolved_subphase = session_row.get("current_subphase")

    # 4. Question ID resolution
    resolved_question_id = question_id
    if not resolved_question_id and session_row:
        resolved_question_id = session_row.get("current_question_id")
    if not resolved_question_id:
        flags.append("missing_question_id")

    # 5. Find question
    question_dict = None
    if resolved_question_id:
        question_dict = _find_question_in_content(content_json, resolved_question_id)
        if question_dict is None:
            flags.append("question_not_found")

    # 6. Build safe question context
    current_question_text = ""
    current_question_context: Optional[dict] = None
    expected_values: list[str] = []
    if question_dict:
        redacted = _redact_question_for_tutor(question_dict, resolved_phase)
        current_question_text = (
            redacted.get("q")
            or redacted.get("prompt")
            or redacted.get("question")
            or ""
        )
        current_question_context = redacted
        ans_spec = question_dict.get("answer_spec")
        if isinstance(ans_spec, dict):
            ev = ans_spec.get("expected")
            if isinstance(ev, str):
                expected_values.append(ev)

    # 7. Screen context
    visible_screen_text = ""
    if screen_context:
        sanitized = sanitize_screen_context_v2(screen_context, expected_values)
        visible_screen_text = sanitized["text"]
        sanitized_to_empty = not visible_screen_text
        if sanitized_to_empty:
            flags.append("empty_screen_context")
        # Plan 8 §8 dashboard signal: emit a session event so the regression
        # dashboard can compute screen_context_sanitized_to_empty_rate. Only
        # fired when the request actually carried screen_context (otherwise
        # there's nothing to sanitize and the denominator would be polluted).
        try:
            if session_id and hw_id:
                await session_events_repo.add_session_event(
                    session_id=session_id,
                    hw_id=hw_id,
                    event_type="screen_context_sanitized",
                    payload={
                        "sanitized_to_empty": bool(sanitized_to_empty),
                        "raw_len": int(sanitized.get("raw_len") or 0),
                        "clean_len": int(sanitized.get("clean_len") or 0),
                        "redacted": bool(sanitized.get("redacted") or False),
                    },
                    phase=resolved_phase,
                    subphase=resolved_subphase,
                    question_id=resolved_question_id,
                )
        except Exception as exc:
            _log.warning(
                "build_tutor_context: failed to emit screen_context_sanitized event: %s",
                exc,
            )
    else:
        flags.append("empty_screen_context")

    # 8. Student work
    resolved_student_work = str(student_work_text or "")
    if not resolved_student_work:
        flags.append("empty_student_work")

    # 9. Recent chat history
    recent_chat_history: list[dict] = []
    try:
        if session_id and hw_id:
            recent_chat_history = await list_tutor_turns(
                session_id, hw_id, limit=6, most_recent=True
            )
    except Exception as exc:
        _log.warning("build_tutor_context: failed to load chat history: %s", exc)

    # 10. Recent attempts from phase_attempts repo
    recent_attempts: list[dict] = []
    try:
        if session_id and hw_id:
            recent_attempts = await list_phase_attempts(
                session_id, hw_id, phase=resolved_phase, limit=10
            )
    except Exception as exc:
        _log.warning("build_tutor_context: failed to load attempts: %s", exc)

    # 11. Metrics
    metrics: dict = {}
    try:
        if session_id and hw_id:
            metrics = await get_session_metrics(session_id, hw_id) or {}
    except Exception as exc:
        _log.warning("build_tutor_context: failed to load metrics: %s", exc)

    if not metrics:
        # Fallback: compute lightweight metrics from attempts
        if recent_attempts:
            total = len(recent_attempts)
            correct = sum(1 for a in recent_attempts if a.get("correct") == 1)
            metrics["accuracy"] = round(correct / total, 2) if total else 0.0
            metrics["recent_count"] = total
        else:
            flags.append("empty_metrics")

    # Slice the current phase content
    current_phase_content = extract_phase_content(content_json, resolved_subphase)

    return TutorContextPacket(
        session_id=session_id or "",
        hw_id=hw_id or "",
        phase=resolved_phase,
        subphase=resolved_subphase,
        current_question_id=resolved_question_id,
        subject=subject,
        grade=grade,
        homework_title=homework_title,
        homework_summary=summarize_homework_content(content_json).get("summary", ""),
        current_phase_content=current_phase_content,
        current_question_text=current_question_text,
        current_question_context=current_question_context,
        visible_screen_text=visible_screen_text,
        student_work_text=resolved_student_work,
        recent_chat_history=recent_chat_history,
        recent_attempts=recent_attempts,
        metrics=metrics,
        warnings_summary="",
        missing_context_flags=flags,
    )
