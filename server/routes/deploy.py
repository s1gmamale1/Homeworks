"""POST /api/deploy/{id} — one-click deploy a homework into a runnable HTML directory.

Wraps scripts/deploy_homework.py. Returns the absolute output path + suggested URL.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server import db

router = APIRouter()

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEPLOY_SCRIPT = REPO_ROOT / "scripts" / "deploy_homework.py"
DEFAULT_OUT = REPO_ROOT / "dist"


class DeployRequest(BaseModel):
    grading: Optional[dict] = None


@router.post("/deploy/{homework_id}")
async def deploy(homework_id: str, body: DeployRequest):
    record = await db.get_homework(homework_id)
    if not record:
        raise HTTPException(status_code=404, detail="homework not found")

    # Persist the grading config into content_json (idempotent — safe on repeated deploys)
    if body.grading:
        content = record.get("content_json") or {}
        if isinstance(content, dict):
            content["grading"] = body.grading
            await db.update_homework(homework_id, {"content_json": content})

    grading_cfg = (body.grading or {}) if body.grading else {}
    provider = grading_cfg.get("provider", "auto")
    if provider == "auto":
        # When the homework was built on a builder host, default to forwarding
        # grades back to that same builder — single source of truth.
        provider = "builder" if not (os.environ.get("KIMI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")) else \
                   "kimi" if os.environ.get("KIMI_API_KEY") else \
                   "anthropic" if os.environ.get("ANTHROPIC_API_KEY") else "mock"
    port = int(grading_cfg.get("deploy_port", 5060))

    if not DEPLOY_SCRIPT.is_file():
        raise HTTPException(status_code=500, detail=f"deploy script missing at {DEPLOY_SCRIPT}")

    cmd = [
        sys.executable,
        str(DEPLOY_SCRIPT),
        "--db", homework_id,
        "--out", str(DEFAULT_OUT),
        "--port", str(port),
        "--provider", provider,
    ]

    # When provider=builder, propagate the URL + subject + grade
    if provider == "builder":
        builder_url = grading_cfg.get("builder_url") or os.environ.get("BUILDER_URL") or "http://127.0.0.1:8000"
        cmd.extend(["--builder-url", builder_url])
        cmd.extend(["--builder-subject", str(record.get("subject") or "geometriya-g7-11")])
        cmd.extend(["--builder-grade", str(record.get("grade") or 8)])

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(REPO_ROOT),
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        raise HTTPException(status_code=504, detail="deploy timed out after 60s")

    if proc.returncode != 0:
        return {
            "ok": False,
            "error": "deploy script exited with non-zero status",
            "details": (stderr.decode("utf-8", errors="replace") if stderr else "") +
                       "\n--- stdout ---\n" +
                       (stdout.decode("utf-8", errors="replace") if stdout else ""),
            "exit_code": proc.returncode,
        }

    # Parse the script's stdout: it prints "[OK] Deployed: <path>"
    out_text = stdout.decode("utf-8", errors="replace") if stdout else ""
    deployed_path = None
    for line in out_text.splitlines():
        line = line.strip()
        if line.startswith("[OK] Deployed:"):
            deployed_path = line.split(":", 1)[1].strip()
            break

    return {
        "ok": True,
        "homework_id": homework_id,
        "path": deployed_path or str(DEFAULT_OUT),
        "url": f"http://127.0.0.1:{port}/",
        "provider": provider,
        "stdout": out_text[-2000:],
    }
