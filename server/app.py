from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from contextlib import asynccontextmanager
import os
import base64

from server.routes.meta import router as meta_router
from server.routes.homework import router as hw_router
from server.routes.homework_page import router as homework_page_router
from server.routes.ai import router as ai_router
from server.routes.library import router as library_router
from server import db
from server.config import BASE_DIR

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

# 1x1 transparent PNG (minimal favicon to suppress 404 logging)
FAVICON_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)

@app.get("/favicon.ico")
async def get_favicon():
    return Response(content=FAVICON_PNG, media_type="image/x-icon", headers={"Cache-Control": "max-age=31536000"})

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meta_router, prefix="/api")
app.include_router(hw_router, prefix="/api")
app.include_router(homework_page_router)
app.include_router(ai_router, prefix="/api")
app.include_router(library_router, prefix="/api")

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