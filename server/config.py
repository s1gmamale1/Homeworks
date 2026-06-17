import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR: Path = Path(__file__).resolve().parent.parent

# override=True makes .env the source of truth for env vars even when the
# shell already has them set. Without this, a stale `$env:OPENAI_API_KEY=""`
# (empty) or wrongly-quoted value from a previous PowerShell session
# silently blocks the real key in .env from loading — symptom on
# 2026-05-20 was OpenAIProvider.is_available() returning False even with
# a valid key in .env. The shell-shadow class of bugs is harder to debug
# than the rare case of a legitimate shell override, so .env wins by
# default; export a fresh shell var only when intentionally probing.
load_dotenv(BASE_DIR / ".env", override=True)


def get_db_path() -> Path:
    """Lazily resolve DB_PATH from env on each call (not frozen at import)."""
    return Path(os.getenv("NETS_DB_PATH", str(BASE_DIR / "nets.db")))


TEMPLATE_PATH: Path = BASE_DIR / "server" / "template" / "perfect_homework.html"
JS_TEMPLATE_PATH: Path = BASE_DIR / "server" / "template" / "js" / "perfect_homework.js"
PROMPTS_DIR: Path = BASE_DIR / "server" / "prompts"
FIXTURES_DIR: Path = BASE_DIR / "fixtures"
DATA_DIR: Path = BASE_DIR / "server" / "data"

# Kimi (Moonshot) — primary AI backend for general traffic
KIMI_API_KEY: str = os.getenv("KIMI_API_KEY", "")
KIMI_BASE_URL: str = os.getenv("KIMI_BASE_URL", "https://api.moonshot.ai/v1")
KIMI_MODEL_FAST: str = os.getenv("KIMI_MODEL_FAST", "moonshot-v1-32k")
KIMI_MODEL_PRO: str = os.getenv("KIMI_MODEL_PRO", "moonshot-v1-128k")
KIMI_MODEL_VISION: str = os.getenv("KIMI_MODEL_VISION", "kimi-k2.6")

# OpenAI — routed by ai_gateway.TASK_PROVIDER_PREFERENCE to the dynamic boss
# generator + answer-checker only (better Uzbek/Russian than Kimi). Falls
# back to Kimi automatically if OPENAI_API_KEY is unset or the request fails.
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL_FAST: str = os.getenv("OPENAI_MODEL_FAST", "gpt-4o-mini")
OPENAI_MODEL_PRO: str = os.getenv("OPENAI_MODEL_PRO", "gpt-4o-mini")
OPENAI_TIMEOUT: float = float(os.getenv("OPENAI_TIMEOUT", "20"))

# AI backend selection — kept as comma-separated preference list for forward
# compat with future providers; defaults to Kimi as the global primary. Per-task
# overrides live in `ai_gateway.TASK_PROVIDER_PREFERENCE` (e.g. boss → openai).
AI_BACKEND_PREFERENCE: str = os.getenv("AI_BACKEND_PREFERENCE", "kimi")

PORT: int = int(os.getenv("PORT", "8000"))
DEBUG: bool = os.getenv("DEBUG", "true").lower() in ("1", "true", "yes", "on")


def __getattr__(name: str):  # noqa: N807
    """Module-level __getattr__ for backward compat: DB_PATH re-resolves on each access."""
    if name == "DB_PATH":
        return get_db_path()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
