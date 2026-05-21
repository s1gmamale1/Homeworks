"""Single source of truth for tutor question-context redaction.

Previously the allow-list + recursive scrub lived in TWO places:
    server/services/tutor.py     (PR #2's CBP-aware version)
    server/services/ai_context.py (older, stale, missing `explanation`
                                   and `flashcard_ref` and the CBP branch)

The live `/api/ai/tutor/chat` route runs through `ai_context.build_tutor_context`,
so PR #2's CBP coupling was dead code on the live path until this module landed
(backend-integration-audit finding #1).

Both modules now import from here. No cycle: `tutor_redaction` has no
intra-services dependencies; `tutor.py` and `ai_context.py` are both downstream.
"""
from __future__ import annotations

from typing import Any


# Keys allowed in question context for non-preview, non-case_based phases.
# Default-deny semantics: any field NOT here is stripped before reaching the LLM.
# When you add a new content field, decide consciously whether it belongs here
# (safe to expose) — fail-closed is the right default.
_TUTOR_CONTEXT_SAFE_KEYS: frozenset[str] = frozenset({
    "id",
    "question_id",
    "q",
    "prompt",
    "question",
    "title",
    "subtitle",
    "text",
    "label",
    "term",
    "term_html",
    "explanation",
    "flashcard_ref",
    "cluster",
    "type",
    "options",
    "fields",
    "front",
    "tier",
    "bloom",
    "pisa",
    "tags",
    "damage",
    "dmg",
})


# CBP-only extension: non-answer-bearing case framing keys that the tutor
# needs to know about during a Case-Based Preview checkpoint. Unioned with
# `_TUTOR_CONTEXT_SAFE_KEYS` ONLY when `phase == "case_based"` so the
# default-deny posture of practice/boss/memory_check is preserved.
#
# Explicitly NOT added (these reveal answers and must remain deny-listed):
#   answer_spec, learning_block_after, consequence_preview, retake_variants,
#   final_simulation, correct_path, wrong_path, feedback_summary,
#   completion_rules, expected, accepted_answers, option_index, correct.
#
# `visual_plan` is intentionally OMITTED from this allow-list —
# layout cues (e.g. which option is highlighted, where the correct
# answer renders on screen) can encode the answer position. Keep it
# in the default-deny set so any author-supplied visual_plan stays
# server-side. (backend-tutor-audit finding #6)
_TUTOR_CONTEXT_CBP_EXTRA_KEYS: frozenset[str] = frozenset({
    "case_setup",          # container
    "metadata",            # container
    "source_extraction",   # container
    "story",               # case_setup.story
    "role",                # case_setup.role
    "task",                # case_setup.task
    "core_concept",        # source_extraction.core_concept
    "main_rule",           # source_extraction.main_rule
    "key_terms",           # source_extraction.key_terms / metadata.key_terms
    "common_mistake",      # source_extraction.common_mistake
    "topic",               # metadata.topic
    "source_concept",      # metadata.source_concept
    "required_skill",      # metadata.required_skill
    "kind",                # Checkpoint.kind (identify|decide|justify)
})


# Phase -> safe-keys table (explicit, exhaustive, easy to extend).
# A future phase rename causes an explicit KeyError-style miss to fall
# through to the strict default rather than silently demoting CBP
# (backend-tutor-audit finding #2).
_PHASE_SAFE_KEYS: dict[str, frozenset[str]] = {
    "case_based": _TUTOR_CONTEXT_SAFE_KEYS | _TUTOR_CONTEXT_CBP_EXTRA_KEYS,
}


def _redact_question_for_tutor(question: dict, phase: str) -> dict:
    """Return a safe copy of `question` for LLM prompt context.

    Preview phase passes through unchanged so the tutor can explain why X is the
    answer. Practice/boss/memory_check phases use an allow-list instead of a
    leak-key deny-list, so newly introduced fields like work/hints/solution_text
    fail closed by default.

    Case-based phase extends the allow-list with CBP framing keys
    (case_setup, metadata, source_extraction + non-answer-bearing inner keys)
    while keeping every answer-bearing key (answer_spec, learning_block_after,
    retake_variants, final_simulation, feedback_summary, completion_rules)
    deny-listed.
    """
    if not isinstance(question, dict):
        return {}
    if phase == "preview":
        # Preview is the only phase where the answer is allowed in context.
        return dict(question)

    safe_keys = _PHASE_SAFE_KEYS.get(phase, _TUTOR_CONTEXT_SAFE_KEYS)

    def scrub(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                k: scrub(v)
                for k, v in value.items()
                if k in safe_keys
            }
        if isinstance(value, list):
            return [scrub(item) for item in value]
        return value

    return scrub(question)
