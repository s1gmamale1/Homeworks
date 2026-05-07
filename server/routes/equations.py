"""POST /api/equations/validate — server-side LaTeX validator.

Companion endpoint to the MathLive equation editor (frontend builder UI).
Lets clients (the auto-save path, the AI tutor's grading prep, the future
import tooling) verify that an LaTeX expression is well-formed BEFORE it
hits storage or downstream renderers.

Why server-side: the editor uses MathLive's client-side parser, but the
runtime renders via KaTeX, and AI-tutor pipelines can run server-only.
A single canonical validator avoids drift between those three.

The endpoint is read-only and has no side effects — safe to hit from any
client. No auth required (matches the rest of the read-only meta routes).
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..services.latex_validator import (
    DEFAULT_MAX_LENGTH,
    validate_latex,
)


router = APIRouter(tags=["equations"])


class ValidateRequest(BaseModel):
    """Body for POST /api/equations/validate.

    `extra="allow"` is set so future fields (e.g. `dialect`, `subject`)
    can land without breaking older clients — matches the project's
    Pydantic _Permissive idiom (Invariant 1)."""

    latex: str = Field(..., description="LaTeX expression to validate")
    mode: str = Field(
        default="inline",
        description='"inline" or "display" — affects future per-mode rules; '
                    "currently informational only",
    )
    max_length: Optional[int] = Field(
        default=None,
        description=(
            f"Override the default {DEFAULT_MAX_LENGTH}-char cap. Useful when "
            "validating server-authored content that's known-large."
        ),
    )

    model_config = {"extra": "allow"}


class ValidateResponse(BaseModel):
    """Response for POST /api/equations/validate.

    `valid` is the only field clients MUST inspect. Everything else is
    informational diagnostics — the same shape regardless of whether the
    input parsed cleanly or not, so clients don't have to branch on
    `valid` to read a field.
    """

    valid: bool
    latex: str
    mode: str
    length: int
    macros: list[str] = []
    placeholders: int = 0
    depth: int = 0
    warnings: list[str] = []
    error: Optional[str] = None
    message: Optional[str] = None
    position: Optional[int] = None

    model_config = {"extra": "allow"}


@router.post("/equations/validate", response_model=ValidateResponse)
async def validate_equation(req: ValidateRequest) -> dict[str, Any]:
    """Validate a LaTeX expression. Always returns 200; the `valid` field
    in the response body is the verdict. We deliberately don't return 4xx
    on invalid LaTeX because:
      a) clients want to inspect the diagnostic fields (error code,
         position, warnings) without catching HTTP exceptions, and
      b) input that is *malformed* (e.g. wrong types) is a 4xx (Pydantic
         already handles that), but input that is well-typed yet
         semantically invalid is a normal 200 with valid=false.

    Hard cap at 50_000 chars to protect the validator from
    pathological inputs even when max_length is overridden.
    """
    HARD_CAP = 50_000
    if len(req.latex) > HARD_CAP:
        # This is the only case where we 4xx — a 50KB+ payload is a
        # client misuse, not a regular validation failure.
        raise HTTPException(
            status_code=413,
            detail={
                "error": "payload_too_large",
                "message": f"latex must be <= {HARD_CAP} characters",
            },
        )

    max_len = req.max_length if isinstance(req.max_length, int) and req.max_length > 0 else DEFAULT_MAX_LENGTH
    return validate_latex(req.latex, mode=req.mode, max_length=max_len)
