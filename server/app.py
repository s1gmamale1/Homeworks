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
from server.routes.ai_plan5 import router as ai_plan5_router
from server.routes.ai_plan8 import router as ai_plan8_router
from server.routes.library import router as library_router
from server.routes.grading import router as grading_router
from server.routes.notebook import router as notebook_router
from server.routes.taskboard import router as taskboard_router
from server.routes.equations import router as equations_router
from server.routes.runtime import router as runtime_router
from server.routes.reflection import router as reflection_router
from server.routes.integrity import router as integrity_router
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
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
        "img-src 'self' data: blob: http: https:; "
        "font-src 'self' data: https://cdn.jsdelivr.net https://fonts.gstatic.com; "
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
app.include_router(ai_plan5_router, prefix="/api")
app.include_router(ai_plan8_router, prefix="/api")
app.include_router(library_router, prefix="/api")
app.include_router(grading_router, prefix="/api")
app.include_router(notebook_router, prefix="/api")
app.include_router(taskboard_router, prefix="/api")
app.include_router(equations_router, prefix="/api")
app.include_router(runtime_router, prefix="/api")
app.include_router(reflection_router, prefix="/api")
app.include_router(integrity_router, prefix="/api")

_FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

# Route → filename map. Single source of truth for the dashboard chrome
# pages. To add a new page, add a row here — the route + cache-bust
# substitution come for free.
_HTML_PAGES: dict[str, str] = {
    "/":              "index.html",
    "/index.html":    "index.html",
    "/builder.html":  "builder.html",
    "/library.html":  "library.html",
    "/landing.html":  "landing.html",
    "/taskboard.html": "taskboard.html",
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

# React SPA (v2 runtime + builder) — built bundle served as static assets.
# Vite content-hashes its own filenames, so this is intentionally OUTSIDE the
# __VERSION__ cache-bust system. Mounted before the "/" catch-all.
_SPA_DIST = os.path.join(_FRONTEND_DIR, "app", "dist")
_SPA_INDEX = os.path.join(_SPA_DIST, "index.html")

# SPA client-route fallback: StaticFiles only serves index.html at the mount
# root, so client-side routes (e.g. /app/builder) 404. Serve the shell for the
# known client routes BEFORE the static mount so the React router takes over.
# (/h/{id} is server-routed in homework_page; this covers the builder route.)
if os.path.isfile(_SPA_INDEX):
    async def _spa_shell():
        with open(_SPA_INDEX, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    for _spa_route in ("/app/builder", "/app/builder/"):
        app.get(_spa_route)(_spa_shell)

if os.path.isdir(_SPA_DIST):
    app.mount("/app", StaticFiles(directory=_SPA_DIST, html=True), name="spa")

# Ensure frontend directory exists before mounting
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
os.makedirs(FRONTEND_DIR, exist_ok=True)

app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
