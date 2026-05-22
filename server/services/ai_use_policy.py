"""AI-use policy table (research §9.3) — what AI is allowed where.

A small, declarative source-of-truth keyed by tutor-phase describing, per phase:
  - ``tutor``        — is the in-app live AI tutor available here?
  - ``external_ai``  — is using an *outside* AI tool (ChatGPT etc.) allowed?
      * ``True``           → fine
      * ``False``          → not appropriate here
      * ``"acknowledged"`` → permitted IF the student acknowledges using it
                             (reflection: thinking-about-the-process is the goal,
                             so an outside tool is allowed when disclosed)
  - ``assessment``   — does work here count as graded assessment?

Per the research's AI-use framing:
  - **preview / practice** — learning surfaces: tutor ON, external OFF, not an
    assessment. The student is meant to explore with the in-app tutor.
  - **practice/case_based** — same learning posture as practice.
  - **boss** — the assessment. Tutor OFF (no help during the test), external OFF,
    this is what counts.
  - **practice/reflection** — metacognitive debrief: tutor ON, external
    ``"acknowledged"`` (disclosing outside-AI use is fine here), not graded.

This module is a pure constant + lookup helper. It is NOT wired into any
request flow yet — the integration agent decides how/where to consult it.
"""
from __future__ import annotations

from typing import Optional


# Safe default for any phase not in the table: lock everything down and treat as
# assessment. Fail-closed — an unknown surface should never silently grant the
# tutor or bless outside-AI use.
SAFE_DEFAULT_POLICY: dict = {
    "tutor": False,
    "external_ai": False,
    "assessment": True,
}


AI_USE_POLICY: dict[str, dict] = {
    # Learning surfaces — explore freely with the in-app tutor; no outside AI;
    # nothing here is graded.
    "preview": {"tutor": True, "external_ai": False, "assessment": False},
    "practice": {"tutor": True, "external_ai": False, "assessment": False},
    "practice/case_based": {"tutor": True, "external_ai": False, "assessment": False},
    # The assessment — tutor off, outside AI off, this is what counts.
    "boss": {"tutor": False, "external_ai": False, "assessment": True},
    # Metacognitive debrief — tutor on, outside-AI use allowed IF acknowledged,
    # not a graded assessment.
    "practice/reflection": {"tutor": True, "external_ai": "acknowledged", "assessment": False},
}


def policy_for(phase: str, subphase: Optional[str] = None) -> dict:
    """Resolve the AI-use policy for a ``phase`` (+ optional ``subphase``).

    Lookup ladder (first hit wins):
      1. ``"{phase}/{subphase}"`` when a subphase is given
      2. ``phase`` alone
      3. ``SAFE_DEFAULT_POLICY`` (fail-closed)

    Returns a *copy* so callers can't mutate the shared table.
    """
    if phase and subphase:
        composite = f"{phase}/{subphase}"
        hit = AI_USE_POLICY.get(composite)
        if hit is not None:
            return dict(hit)
    if phase:
        hit = AI_USE_POLICY.get(phase)
        if hit is not None:
            return dict(hit)
    return dict(SAFE_DEFAULT_POLICY)
