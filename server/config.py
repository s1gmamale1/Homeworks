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

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

# Vertex AI (preferred) — service account JSON key
VERTEX_CREDENTIALS_PATH: str = os.getenv("VERTEX_CREDENTIALS_PATH", "")
VERTEX_PROJECT: str = os.getenv("VERTEX_PROJECT", "")
VERTEX_LOCATION: str = os.getenv("VERTEX_LOCATION", "us-central1")

# Kimi (Moonshot) — primary AI backend (Wave F0)
KIMI_API_KEY: str = os.getenv("KIMI_API_KEY", "")
KIMI_BASE_URL: str = os.getenv("KIMI_BASE_URL", "https://api.moonshot.ai/v1")
KIMI_MODEL_FAST: str = os.getenv("KIMI_MODEL_FAST", "moonshot-v1-32k")
KIMI_MODEL_PRO: str = os.getenv("KIMI_MODEL_PRO", "moonshot-v1-128k")

# AI backend selection — comma-separated provider preference list
AI_BACKEND_PREFERENCE: str = os.getenv("AI_BACKEND_PREFERENCE", "kimi,vertex,gemini_api")

PORT: int = int(os.getenv("PORT", "8000"))
DEBUG: bool = os.getenv("DEBUG", "true").lower() in ("1", "true", "yes", "on")


def __getattr__(name: str):  # noqa: N807
    """Module-level __getattr__ for backward compat: DB_PATH re-resolves on each access."""
    if name == "DB_PATH":
        return get_db_path()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
