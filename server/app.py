from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, HTMLResponse
from contextlib import asynccontextmanager
import os
import base64
import subprocess

from server.routes.meta import router as meta_router
from server.routes.homework import router as hw_router
from server.routes.homework_page import router as homework_page_router
from server.routes.ai import router as ai_router
from server.routes.library import router as library_router
from server.routes.grading import router as grading_router
from server import db
from server.config import BASE_DIR

# Compute git short SHA for cache-busting static assets
def _compute_version() -> str:
    """Return git short SHA or fallback to 'dev' if unavailable."""
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
        ).stdout.strip() or "dev"
    except Exception:
        return "dev"

VERSION = _compute_version()


def _cors_origins() -> list[str]:
    raw = os.environ.get("NETS_CORS_ORIGINS", "")
    if raw.strip():
        return [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]
    return [
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://192.168.1.26:8000",
    ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    try:
        yield
    finally:
        # On graceful shutdown, flush the WAL into the main DB file so nothing
        # sits unreconciled if the host is power-cycled before the next startup.
        try:
            await db.checkpoint()
        except Exception as e:
            # Never let a checkpoint failure block shutdown — just log it.
            import sys
            print(f"[lifespan] checkpoint on shutdown failed: {e}", file=sys.stderr)

app = FastAPI(lifespan=lifespan)

SECURITY_HEADERS: dict[str, str] = {
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data: blob: http: https:; "
        "font-src 'self' data: https://cdn.jsdelivr.net; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'self'"
    ),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    for header, value in SECURITY_HEADERS.items():
        response.headers.setdefault(header, value)
    return response

# 1x1 transparent PNG (minimal favicon to suppress 404 logging)
FAVICON_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)

@app.get("/favicon.ico")
async def get_favicon():
    return Response(content=FAVICON_PNG, media_type="image/x-icon", headers={"Cache-Control": "max-age=31536000"})

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meta_router, prefix="/api")
app.include_router(hw_router, prefix="/api")
app.include_router(homework_page_router)
app.include_router(ai_router, prefix="/api")
app.include_router(library_router, prefix="/api")
app.include_router(grading_router, prefix="/api")

_FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

# Route → filename map. Single source of truth for the dashboard chrome
# pages. To add a new page, add a row here — the route + cache-bust
# substitution come for free.
_HTML_PAGES: dict[str, str] = {
    "/":              "index.html",
    "/index.html":    "index.html",
    "/builder.html":  "builder.html",
    "/library.html":  "library.html",
}

def _render_html_with_version(filename: str) -> str:
    """Read frontend/{filename} and substitute __VERSION__ with git short SHA."""
    html_path = os.path.join(_FRONTEND_DIR, filename)
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read().replace("__VERSION__", VERSION)


def _make_html_handler(filename: str):
    """Closure factory — binds `filename` per route so each registered
    handler reads its own page (avoids the late-binding-in-loop pitfall)."""
    async def _handler():
        return HTMLResponse(_render_html_with_version(filename))
    _handler.__name__ = f"get_{filename.replace('.', '_')}"
    return _handler


for _route, _filename in _HTML_PAGES.items():
    app.get(_route)(_make_html_handler(_filename))

# Runtime static mount — serves /static/runtime/runtime.js from server/template/
# MUST come before the `/` catch-all mount below (FastAPI evaluates mounts in order).
app.mount(
    "/static/runtime",
    StaticFiles(directory=str(BASE_DIR / "server" / "template")),
    name="runtime",
)

# Ensure frontend directory exists before mounting
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
os.makedirs(FRONTEND_DIR, exist_ok=True)

app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
