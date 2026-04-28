"""Deterministic slur detection — defense-in-depth alongside the LLM-side rule
in tutor-assistant.md. Loaded from docs/Naughty_words.md at module import.

Why this exists: Kimi FAST_MODEL occasionally misses subtle slurs. This regex
pass catches the deterministic ones; the LLM still handles register + tone."""

from __future__ import annotations
import re
from pathlib import Path
from typing import Optional

from server.config import BASE_DIR

_NAUGHTY_PATH = BASE_DIR / "docs" / "Naughty_words.md"


def _load_slur_list() -> list[str]:
    """Parse Naughty_words.md and return a deduplicated list of slurs.

    The file is markdown — pick out tokens that look like slurs. Use a simple
    heuristic: lines starting with `-`, `*`, or table cells; strip markup;
    only keep words ≥3 chars (filter out single-char punctuation noise)."""
    if not _NAUGHTY_PATH.exists():
        return []
    text = _NAUGHTY_PATH.read_text(encoding="utf-8")
    words: set[str] = set()
    for line in text.splitlines():
        s = line.strip()
        if s.startswith(("-", "*", "|")):
            # Strip leading bullet/table chars + take first column-like token
            cleaned = re.sub(r"^[-*|\s]+", "", s)
            cleaned = re.sub(r"\|.*$", "", cleaned)  # strip table tail
            cleaned = re.sub(r"`+", "", cleaned)      # strip backticks
            cleaned = re.sub(r"\(.*$", "", cleaned)   # strip parenthetical
            for token in re.split(r"[\s,;/]+", cleaned):
                token = token.strip().lower()
                if len(token) >= 3 and re.match(r"^[a-zа-яёa-zëâêîôûş'-]+$", token, re.IGNORECASE):
                    words.add(token)
    return sorted(words)


# Compile once at module load. Word-boundary regex.
_SLURS: list[str] = _load_slur_list()
_PATTERN: Optional[re.Pattern] = (
    re.compile(r"\b(" + "|".join(re.escape(w) for w in _SLURS) + r")\b", re.IGNORECASE)
    if _SLURS else None
)


def detect_slurs(message: str) -> list[str]:
    """Return list of slurs found in `message`. Case-insensitive, word-boundary."""
    if not _PATTERN or not message:
        return []
    return list({m.group(0).lower() for m in _PATTERN.finditer(message)})


def callout_for(message: str, lang: str = "uz") -> Optional[str]:
    """Return a playful callout string if slurs detected, else None.

    Lang preference: 'uz' (default), 'ru', 'en'. Mirrors the tutor's
    register-mirror policy."""
    if not detect_slurs(message):
        return None
    callouts = {
        "uz": "Ey-ey, tilingni yumshat-da, biz darsdamiz \U0001f604.",
        "ru": "Эй-эй, без этих слов, мы же на уроке \U0001f604.",
        "en": "Whoa whoa — language, we're in class \U0001f604.",
    }
    return callouts.get(lang, callouts["uz"])
