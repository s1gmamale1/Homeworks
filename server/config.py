import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR: Path = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def get_db_path() -> Path:
    """Lazily resolve DB_PATH from env on each call (not frozen at import)."""
    return Path(os.getenv("NETS_DB_PATH", str(BASE_DIR / "nets.db")))


TEMPLATE_PATH: Path = BASE_DIR / "server" / "template" / "perfect_homework.html"
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
