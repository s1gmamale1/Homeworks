"""Notebook formula grading — orchestrator for the 4-layer guard pipeline.

Flow: image_bytes -> input validation -> prefilter -> photo store
                  -> vision LLM with grounded prompt
                  -> post-LLM sanity check -> DB row -> NotebookGrade.

Returns a NotebookGrade dataclass that the route layer serializes to JSON.
Owns ALL decisions about hallucination defense — the route just relays.
"""
from __future__ import annotations

import base64
import json
import logging
import re
from dataclasses import asdict, dataclass
from typing import Any, Optional

from server import db
from server.services import gemini, notebook_prefilter, photo_store

log = logging.getLogger(__name__)

# ── Layer 1: input validation ────────────────────────────────────────────────
ACCEPTED_MIMES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_BYTES = 5 * 1024 * 1024   # 5 MB
MIN_FILE_BYTES = 100

# ── Layer 4: post-LLM sanity-check thresholds ────────────────────────────────
MIN_CONFIDENCE_FOR_GRADE = 0.4
MATH_CHAR_REGEX = re.compile(r"[0-9=+\-*/√∫π^()×÷·]", re.UNICODE)
ILLEGIBLE_PATTERNS = re.compile(
    r"(?:i\s+cannot\s+read|illegible|too\s+blurry|cannot\s+make\s+out|unreadable|\[illegible\])",
    re.IGNORECASE,
)

# ── Localized retry messages (Uzbek / Russian / English) ─────────────────────
RETRY_MESSAGES: dict[str, dict[str, str]] = {
    "blank_or_scene": {
        "uz": "Yechimingiz ko'rinmayapti. Iltimos, daftaringizdagi ishingizni yaqindan suratga oling.",
        "ru": "Решение не видно. Сфотографируйте свою работу крупнее.",
        "en": "Couldn't see your work. Please retake the photo closer to your written solution.",
    },
    "skew_too_high": {
        "uz": "Surat juda qiyshiq. Daftarni to'g'ri ushlab qayta urinib ko'ring.",
        "ru": "Фото слишком наклонено. Держите тетрадь ровно и попробуйте снова.",
        "en": "Photo is too tilted. Hold the notebook flat and try again.",
    },
    "scene_detected": {
        "uz": "Surat asosan boshqa narsalardan iborat. Faqat ishingizni suratga oling.",
        "ru": "На фото слишком много постороннего. Сфотографируйте только работу.",
        "en": "Too much of the photo is not your work. Frame just the page.",
    },
    "vision_low_confidence": {
        "uz": "Yozuvni aniq o'qiy olmadik. Iltimos, yorug'roq joyda yaqindan suratga oling.",
        "ru": "Не удалось разобрать почерк. Попробуйте при лучшем освещении и крупнее.",
        "en": "Couldn't read the handwriting clearly. Try better lighting, closer shot.",
    },
    "no_math_symbols": {
        "uz": "Suratda formulalar ko'rinmayapti. Yechimingizni qayta yuklang.",
        "ru": "На фото нет формул. Загрузите работу с решением заново.",
        "en": "Photo doesn't show math work. Please upload your worked solution.",
    },
    "invalid_file": {
        "uz": "Fayl noto'g'ri formatda. JPG, PNG yoki WebP bo'lishi kerak.",
        "ru": "Неверный формат файла. Используйте JPG, PNG или WebP.",
        "en": "Invalid file format. Please use JPG, PNG, or WebP.",
    },
}


@dataclass(frozen=True)
class NotebookGrade:
    rejected: bool
    reason: Optional[str] = None
    photo_id: Optional[str] = None
    transcribed_text: Optional[str] = None
    confidence: Optional[float] = None
    correct: Optional[bool] = None
    score_1_to_4: Optional[int] = None
    axis_1_concept_id: Optional[int] = None
    axis_2_process_integrity: Optional[int] = None
    feedback: Optional[str] = None
    matches_expected: Optional[bool] = None

    def to_response_dict(self, *, lang: str = "uz") -> dict:
        d = asdict(self)
        if self.rejected and self.reason in RETRY_MESSAGES:
            msgs = RETRY_MESSAGES[self.reason]
            d["retry_message_uz"] = msgs["uz"]
            d["retry_message_ru"] = msgs["ru"]
            d["retry_message_en"] = msgs["en"]
        return d


# ── Layer 1 ──────────────────────────────────────────────────────────────────
def _validate_input(image_bytes: bytes, mime: str) -> Optional[NotebookGrade]:
    """Return a rejection NotebookGrade if input fails Layer 1 checks; else None."""
    if not isinstance(mime, str) or mime.lower() not in ACCEPTED_MIMES:
        return NotebookGrade(rejected=True, reason="invalid_file")
    if not isinstance(image_bytes, (bytes, bytearray)):
        return NotebookGrade(rejected=True, reason="invalid_file")
    if len(image_bytes) > MAX_FILE_BYTES:
        return NotebookGrade(rejected=True, reason="invalid_file")
    if len(image_bytes) < MIN_FILE_BYTES:
        return NotebookGrade(rejected=True, reason="invalid_file")

    is_jpg = image_bytes[:3] == b"\xff\xd8\xff"
    is_png = image_bytes[:8] == b"\x89PNG\r\n\x1a\n"
    is_webp = (
        len(image_bytes) >= 12
        and image_bytes[:4] == b"RIFF"
        and image_bytes[8:12] == b"WEBP"
    )
    if not (is_jpg or is_png or is_webp):
        return NotebookGrade(rejected=True, reason="invalid_file")
    return None


def _build_grounded_prompt(
    *, question_text: str, expected: Any, prompt_template: str
) -> str:
    """Inject question + expected into the grader template."""
    if isinstance(expected, list):
        expected_str = ", ".join(str(x) for x in expected) if expected else "(not specified)"
    elif expected is None or expected == "":
        expected_str = "(not specified)"
    else:
        expected_str = str(expected)
    qt = question_text if (question_text and question_text.strip()) else "(not provided)"
    return prompt_template.replace("{question_text}", qt).replace(
        "{expected}", expected_str
    )


# ── Layer 4 ──────────────────────────────────────────────────────────────────
def _post_llm_sanity(grade_json: dict) -> tuple[bool, str]:
    """Return (ok, reason). reason is '' if ok."""
    transcribed_raw = grade_json.get("transcribed_text")
    transcribed = (transcribed_raw or "").strip() if isinstance(transcribed_raw, str) else ""
    try:
        confidence = float(grade_json.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0

    # Empty transcription → low-confidence rejection
    if not transcribed:
        return False, "vision_low_confidence"

    # Hallucination guard: model claims illegible but reports high confidence
    if ILLEGIBLE_PATTERNS.search(transcribed) and confidence > 0.6:
        log.warning(
            "Hallucination guard tripped: illegible-pattern in transcription with confidence=%s",
            confidence,
        )
        return False, "vision_low_confidence"

    # Confidence floor
    if confidence < MIN_CONFIDENCE_FOR_GRADE:
        return False, "vision_low_confidence"

    # Math-content sanity check
    if not MATH_CHAR_REGEX.search(transcribed):
        return False, "no_math_symbols"

    return True, ""


def _strip_markdown_fences(text: str) -> str:
    """Strip ```json ... ``` fences if the model still added them."""
    text = text.strip()
    if not text.startswith("```"):
        return text
    lines = text.split("\n")
    if len(lines) < 2:
        return text
    # Drop opening fence
    lines = lines[1:]
    # Drop closing fence if present
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


async def grade_capture(
    *,
    image_bytes: bytes,
    mime: str,
    session_id: str,
    hw_id: str,
    question_id: str,
    question_text: str,
    expected: Any,
    prompt_template: str,
) -> NotebookGrade:
    """Run the full 4-layer pipeline. Always returns a NotebookGrade — never raises for bad input."""
    # Layer 1 — input validation
    rejection = _validate_input(image_bytes, mime)
    if rejection is not None:
        await _persist_rejection(session_id, hw_id, question_id, rejection)
        return rejection

    # Layer 2 — OpenCV pre-filter
    pf = notebook_prefilter.validate(image_bytes)
    if not pf.ok:
        rg = NotebookGrade(rejected=True, reason=pf.reason or "blank_or_scene")
        await _persist_rejection(session_id, hw_id, question_id, rg)
        return rg

    deskewed = pf.deskewed_bytes or image_bytes

    # Save deskewed bytes to photo store
    try:
        photo_id = photo_store.save(deskewed, hw_id=hw_id)
    except Exception as exc:
        log.warning("photo_store.save failed: %s", exc)
        photo_id = None

    # Layer 3 — vision LLM
    image_b64 = base64.b64encode(deskewed).decode("ascii")
    grounded = _build_grounded_prompt(
        question_text=question_text,
        expected=expected,
        prompt_template=prompt_template,
    )
    try:
        resp = await gemini.generate_vision(
            prompt=grounded,
            image_b64=image_b64,
            mime="image/jpeg",
            json_mode=True,
            temperature=0.1,
        )
        grade_text = (resp.get("text") or "").strip()
        grade_text = _strip_markdown_fences(grade_text)
        grade_json = json.loads(grade_text)
        if not isinstance(grade_json, dict):
            raise ValueError(f"Vision response is not a JSON object: {type(grade_json).__name__}")
    except Exception as exc:
        log.warning("Vision LLM call failed: %s", exc)
        rg = NotebookGrade(
            rejected=True,
            reason="vision_low_confidence",
            photo_id=photo_id,
        )
        await _persist_rejection(session_id, hw_id, question_id, rg)
        return rg

    # Layer 4 — post-LLM sanity
    ok, reject_reason = _post_llm_sanity(grade_json)
    if not ok:
        try:
            conf_val = float(grade_json.get("confidence") or 0.0)
        except (TypeError, ValueError):
            conf_val = 0.0
        rg = NotebookGrade(
            rejected=True,
            reason=reject_reason,
            photo_id=photo_id,
            confidence=conf_val,
            transcribed_text=grade_json.get("transcribed_text"),
        )
        await _persist_rejection(session_id, hw_id, question_id, rg)
        return rg

    # Normalize numeric fields with safe coercion + clamping
    def _clamp_int(v: Any, default: int, lo: int, hi: int) -> int:
        try:
            iv = int(v)
        except (TypeError, ValueError):
            return default
        return max(lo, min(hi, iv))

    def _safe_float(v: Any, default: float = 0.0) -> float:
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    grade = NotebookGrade(
        rejected=False,
        photo_id=photo_id,
        transcribed_text=grade_json.get("transcribed_text"),
        confidence=_safe_float(grade_json.get("confidence")),
        correct=bool(grade_json.get("correct", False)),
        score_1_to_4=_clamp_int(grade_json.get("score_1_to_4"), 1, 1, 4),
        axis_1_concept_id=_clamp_int(grade_json.get("axis_1_concept_id"), 1, 1, 4),
        axis_2_process_integrity=_clamp_int(
            grade_json.get("axis_2_process_integrity"), 1, 1, 4
        ),
        feedback=grade_json.get("feedback") or "",
        matches_expected=bool(grade_json.get("matches_expected", False)),
    )
    await db.add_capture(
        session_id=session_id,
        hw_id=hw_id,
        question_id=question_id,
        photo_id=photo_id,
        status="graded",
        transcribed_text=grade.transcribed_text,
        confidence=grade.confidence,
        score_1_to_4=grade.score_1_to_4,
        axis_1_concept_id=grade.axis_1_concept_id,
        axis_2_process_integrity=grade.axis_2_process_integrity,
        correct=int(bool(grade.correct)),
        feedback=grade.feedback,
        grade_json=json.dumps(grade_json, ensure_ascii=False),
    )
    return grade


async def _persist_rejection(
    session_id: str, hw_id: str, question_id: str, rg: NotebookGrade
) -> None:
    """Persist a rejection row. Swallows DB errors so the route still returns a clean response."""
    try:
        await db.add_capture(
            session_id=session_id,
            hw_id=hw_id,
            question_id=question_id,
            photo_id=rg.photo_id,
            status="rejected",
            rejection_reason=rg.reason,
            confidence=rg.confidence,
            transcribed_text=rg.transcribed_text,
        )
    except Exception as exc:
        log.warning("Failed to persist rejection row: %s", exc)
