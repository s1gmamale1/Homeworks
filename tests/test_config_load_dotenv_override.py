"""Regression — server/config.py must load .env with override=True.

Without override=True, a stale shell-set env var (e.g. an empty-string
`OPENAI_API_KEY=""` left over from an earlier PowerShell session, or a
value that was pasted with surrounding quotes) blocks the real value in
.env from loading. The 2026-05-20 symptom: OpenAIProvider.is_available()
returned False even though the .env file had a valid 164-char key. .env
is the source of truth for this project; the override flag enforces that.
"""
from __future__ import annotations

import re
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "server" / "config.py"


def test_load_dotenv_called_with_override_true():
    body = CONFIG_PATH.read_text(encoding="utf-8")
    # Match any whitespace/comments between the path arg and the override kwarg.
    pattern = re.compile(
        r"load_dotenv\s*\(\s*BASE_DIR\s*/\s*[\"'].env[\"']\s*,\s*override\s*=\s*True\s*\)",
        re.DOTALL,
    )
    assert pattern.search(body), (
        "config.py must call load_dotenv(..., override=True) — without it, "
        "a stale shell env var silently shadows the real value in .env"
    )


def test_load_dotenv_is_not_called_without_override():
    """Reverse guard: no bare load_dotenv(...) call without override.
    Catches the regression where someone removes the explicit param."""
    body = CONFIG_PATH.read_text(encoding="utf-8")
    bare = re.compile(r"load_dotenv\s*\([^)]*\.env[^)]*\)")
    for m in bare.finditer(body):
        assert "override" in m.group(0), (
            f"Found bare load_dotenv without override kwarg: {m.group(0)!r}"
        )
