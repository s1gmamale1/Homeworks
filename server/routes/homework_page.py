"""Permanent shareable homework URL — B1.

GET /h/{id}  →  returns the same rendered HTML as /api/homeworks/{id}/preview.
Uses the same render_homework() helper so both routes are byte-equivalent.
If the homework is missing → friendly 404 HTML page (browser-safe).
If the homework is trashed → friendly 409 HTML page.

Also hosts the /api/homeworks/{id}/preview route (used by the builder iframe
for live editing — keeps the no-cache headers and JSON-style errors so the
builder behavior is unchanged).
"""

import html as _html
import json as _json
import os as _os

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

from ..db import get_homework
from ..services.content_json_compat import normalize_content_json_for_runtime
from ..services.injector import inject

router = APIRouter(tags=["homework_page"])

# React SPA built bundle (Vite). The dist/index.html already references the
# content-hashed assets under /app/; we inject NETS_CTX + OG tags into its head.
_SPA_DIST_INDEX = _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.dirname(__file__))),
    "frontend", "app", "dist", "index.html",
)


def _render_spa_shell(hw: dict) -> str:
    """v2 runtime: serve the React SPA shell with boot context + OG tags.

    Reads the Vite-built dist/index.html (hashed asset refs intact) and injects:
      - window.NETS_CTX (hw_id, flow_version, title) for client boot
      - Open Graph / Twitter meta so Telegram/social share cards render
        (the SPA is client-rendered, so crawlers need server-emitted OG).
    """
    content = hw.get("content_json") or {}
    meta = content.get("meta") or {}
    title = meta.get("title") or hw.get("title") or "NETS Homework"
    subject = meta.get("subject_display") or (hw.get("subject") or "").capitalize()
    grade = hw.get("grade")
    desc_bits = [b for b in [subject, f"{grade}-sinf" if grade else None] if b]
    description = " · ".join(desc_bits) or "Interactive homework on NETS."

    with open(_SPA_DIST_INDEX, "r", encoding="utf-8") as f:
        shell = f.read()

    ctx = {
        "hw_id": hw.get("id"),
        "flow_version": content.get("flow_version"),
        "title": title,
    }
    t = _html.escape(title)
    d = _html.escape(description)
    head_inject = (
        f'<title>{t} · NETS</title>'
        f'<meta name="description" content="{d}">'
        f'<meta property="og:title" content="{t}">'
        f'<meta property="og:description" content="{d}">'
        f'<meta property="og:type" content="website">'
        f'<meta name="twitter:card" content="summary">'
        f'<script>window.NETS_CTX = {_json.dumps(ctx)};</script>'
    )
    # Inject right after <head ...> opening tag (before Vite's own tags).
    lower = shell.lower()
    idx = lower.find("<head>")
    if idx != -1:
        cut = idx + len("<head>")
        return shell[:cut] + head_inject + shell[cut:]
    return shell.replace("</head>", head_inject + "</head>", 1)

# Wave I3 — friendly 404/409 pages are now lang-aware. Tuple format:
# (h1, body, link). Title is derived from the lang too. 'uz' is the default
# fallback for unknown languages so existing links keep working.
_FRIENDLY_BODIES: dict[str, dict[int, tuple[str, str, str, str]]] = {
    "uz": {
        404: (
            "Topilmadi — NETS",
            "404",
            "Bu topshiriq mavjud emas yoki o'chirib tashlangan.",
            "← Asosiy sahifaga qaytish",
        ),
        409: (
            "O'chirilgan — NETS",
            "409",
            "Bu topshiriq o'chirilgan. Tiklanishi kerak.",
            "← Asosiy sahifaga qaytish",
        ),
    },
    "ru": {
        404: (
            "Не найдено — NETS",
            "404",
            "Это задание не существует или было удалено.",
            "← Вернуться на главную",
        ),
        409: (
            "Удалено — NETS",
            "409",
            "Это задание удалено. Его нужно восстановить.",
            "← Вернуться на главную",
        ),
    },
    "en": {
        404: (
            "Not found — NETS",
            "404",
            "This homework does not exist or has been deleted.",
            "← Back to dashboard",
        ),
        409: (
            "Deleted — NETS",
            "409",
            "This homework has been deleted. It needs to be restored.",
            "← Back to dashboard",
        ),
    },
}


def _friendly_page(code: int, lang: str = "uz") -> str:
    """Return a lang-aware friendly HTML page for 404/409.

    Defaults to 'uz' if the requested lang isn't in the dict — defensive against
    garbage `?lang=` query params and unexpected DB values.
    """
    if lang not in _FRIENDLY_BODIES:
        lang = "uz"
    title, h1, body, link = _FRIENDLY_BODIES[lang][code]
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head><meta charset="UTF-8"><title>{title}</title>
<style>
  body{{font-family:system-ui,sans-serif;display:flex;align-items:center;
       justify-content:center;min-height:100vh;margin:0;background:#0f172a;color:#e2e8f0}}
  .box{{text-align:center;padding:2rem;max-width:420px}}
  h1{{font-size:2.5rem;margin:0 0 .5rem}}
  p{{color:#94a3b8;margin:.5rem 0 1.5rem}}
  a{{color:#60a5fa;text-decoration:none;font-weight:600}}
  a:hover{{text-decoration:underline}}
</style>
</head>
<body>
<div class="box">
  <h1>{h1}</h1>
  <p>{body}</p>
  <a href="/">{link}</a>
</div>
</body>
</html>"""


def render_homework(hw: dict) -> str:
    """Shared helper: inject content_json into the template with AI bootstrap.

    Called by both /api/homeworks/{id}/preview and /h/{id}.
    Returns rendered HTML string — byte-equivalent for the same homework record.
    """
    # Normalize legacy aliases (gate_quote envelope / boss → boss_questions /
    # reading.text → reading.passage / boss-question ids / etc) before the
    # injector sees the blob. The DB row is left untouched — this is purely
    # in-memory, additive, idempotent.
    content = normalize_content_json_for_runtime(hw.get("content_json") or {})
    meta_override = content.get("meta") or {}
    if not meta_override.get("title"):
        meta_override["title"] = hw.get("title", "")
    subject_display = content.get("meta", {}).get("subject_display") or hw.get("subject", "").capitalize()
    grade = hw.get("grade")
    chapter = content.get("meta", {}).get("section")
    summary = f"{subject_display} · {grade}-sinf"
    if chapter:
        summary += f" · {chapter}"

    # Wave I3 — lang resolution falls through three sources (in order):
    #   1. meta.lang (per-homework runtime override authored in the builder)
    #   2. hw.language (DB column — Wave I default per homework)
    #   3. 'uz' (legacy default)
    runtime_ctx = {
        "apiBase": "",  # same-origin
        "subject": hw.get("subject"),
        "grade": grade,
        "homeworkTitle": hw.get("title"),
        "homeworkSummary": summary,
        "hwId": hw.get("id"),
        "lang": (
            meta_override.get("lang")
            or content.get("meta", {}).get("lang")
            or hw.get("language")
            or "uz"
        ),
    }
    return inject(content, meta_override, runtime_context=runtime_ctx)


@router.get("/h/{hw_id}", response_class=HTMLResponse)
async def homework_page(hw_id: str, lang: str | None = Query(default=None)):
    """Permanent shareable URL for a finished homework.

    Returns the same rendered HTML as /api/homeworks/{hw_id}/preview.
    Missing homework → friendly 404 HTML (lang-aware via `?lang=` query).
    Trashed homework → friendly 409 HTML (lang-aware via the homework's own
    DB language column).
    """
    hw = await get_homework(hw_id)
    if not hw:
        # No homework → no DB lang available. Use the query param if provided,
        # else default 'uz'. Garbage values fall back to 'uz' inside _friendly_page.
        return HTMLResponse(
            content=_friendly_page(404, lang or "uz"), status_code=404
        )
    if hw.get("deleted_at"):
        # Trashed homework — we DO know the language from the DB row.
        return HTMLResponse(
            content=_friendly_page(409, hw.get("language") or "uz"),
            status_code=409,
        )
    # v2 fork: flow_version == "v2" → React SPA shell (if the bundle is built).
    # Everything else → the legacy injector path, byte-for-byte unchanged.
    content = hw.get("content_json") or {}
    if content.get("flow_version") == "v2" and _os.path.isfile(_SPA_DIST_INDEX):
        # The SPA shell references content-hashed bundles + carries the CSP that
        # the page locks in at load — must not be cached, or a rebuild/CSP change
        # leaves students pinned to a stale bundle and the old policy.
        return HTMLResponse(
            content=_render_spa_shell(hw),
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )
    html = render_homework(hw)
    return HTMLResponse(
        content=html,
        headers={
            "Cache-Control": "public, max-age=300",
        },
    )


@router.get("/api/homeworks/{hw_id}/preview", response_class=HTMLResponse)
async def preview(hw_id: str):
    """Live preview URL used by the builder iframe.

    Same rendered HTML body as /h/{id} (shared render_homework helper) but
    returns JSON-style HTTPException errors and no-cache headers so the
    builder's live-editing flow stays unchanged.
    """
    hw = await get_homework(hw_id)
    if not hw:
        raise HTTPException(
            status_code=404,
            detail={"error": "Homework not found", "code": "NOT_FOUND"},
        )
    if hw.get("deleted_at"):
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Cannot render a trashed homework. Restore it first.",
                "code": "TRASHED",
            },
        )
    html = render_homework(hw)
    return HTMLResponse(
        content=html,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        },
    )
