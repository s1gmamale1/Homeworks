"""Permanent shareable homework URL — B1.

GET /h/{id}  →  returns the same rendered HTML as /api/homeworks/{id}/preview.
Uses the same render_homework() helper so both routes are byte-equivalent.
If the homework is missing → friendly 404 HTML page (browser-safe).
If the homework is trashed → friendly 409 HTML page.

Also hosts the /api/homeworks/{id}/preview route (used by the builder iframe
for live editing — keeps the no-cache headers and JSON-style errors so the
builder behavior is unchanged).
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from ..db import get_homework
from ..services.injector import inject

router = APIRouter(tags=["homework_page"])

_404_HTML = """<!DOCTYPE html>
<html lang="uz">
<head><meta charset="UTF-8"><title>Topilmadi — NETS</title>
<style>
  body{font-family:system-ui,sans-serif;display:flex;align-items:center;
       justify-content:center;min-height:100vh;margin:0;background:#0f172a;color:#e2e8f0}
  .box{text-align:center;padding:2rem;max-width:420px}
  h1{font-size:2.5rem;margin:0 0 .5rem}
  p{color:#94a3b8;margin:.5rem 0 1.5rem}
  a{color:#60a5fa;text-decoration:none;font-weight:600}
  a:hover{text-decoration:underline}
</style>
</head>
<body>
<div class="box">
  <h1>404</h1>
  <p>Bu topshiriq mavjud emas yoki o'chirib tashlangan.</p>
  <a href="/">&#8592; Asosiy sahifaga qaytish</a>
</div>
</body>
</html>"""

_409_HTML = """<!DOCTYPE html>
<html lang="uz">
<head><meta charset="UTF-8"><title>O'chirilgan — NETS</title>
<style>
  body{font-family:system-ui,sans-serif;display:flex;align-items:center;
       justify-content:center;min-height:100vh;margin:0;background:#0f172a;color:#e2e8f0}
  .box{text-align:center;padding:2rem;max-width:420px}
  h1{font-size:2.5rem;margin:0 0 .5rem}
  p{color:#94a3b8;margin:.5rem 0 1.5rem}
  a{color:#60a5fa;text-decoration:none;font-weight:600}
  a:hover{text-decoration:underline}
</style>
</head>
<body>
<div class="box">
  <h1>409</h1>
  <p>Bu topshiriq o'chirilgan. Tiklanishi kerak.</p>
  <a href="/">&#8592; Asosiy sahifaga qaytish</a>
</div>
</body>
</html>"""


def render_homework(hw: dict) -> str:
    """Shared helper: inject content_json into the template with AI bootstrap.

    Called by both /api/homeworks/{id}/preview and /h/{id}.
    Returns rendered HTML string — byte-equivalent for the same homework record.
    """
    content = hw.get("content_json") or {}
    meta_override = content.get("meta") or {}
    if not meta_override.get("title"):
        meta_override["title"] = hw.get("title", "")
    subject_display = content.get("meta", {}).get("subject_display") or hw.get("subject", "").capitalize()
    grade = hw.get("grade")
    chapter = content.get("meta", {}).get("section")
    summary = f"{subject_display} · {grade}-sinf"
    if chapter:
        summary += f" · {chapter}"

    runtime_ctx = {
        "apiBase": "",  # same-origin
        "subject": hw.get("subject"),
        "grade": grade,
        "homeworkTitle": hw.get("title"),
        "homeworkSummary": summary,
        "hwId": hw.get("id"),
        "lang": (meta_override.get("lang") or content.get("meta", {}).get("lang") or "uz"),
    }
    return inject(content, meta_override, runtime_context=runtime_ctx)


@router.get("/h/{hw_id}", response_class=HTMLResponse)
async def homework_page(hw_id: str):
    """Permanent shareable URL for a finished homework.

    Returns the same rendered HTML as /api/homeworks/{hw_id}/preview.
    Missing homework → friendly 404 HTML. Trashed homework → friendly 409 HTML.
    """
    hw = await get_homework(hw_id)
    if not hw:
        return HTMLResponse(content=_404_HTML, status_code=404)
    if hw.get("deleted_at"):
        return HTMLResponse(content=_409_HTML, status_code=409)
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
