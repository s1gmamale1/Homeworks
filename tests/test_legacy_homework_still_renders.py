"""Backward-compat fence — legacy homeworks (no `flow_version`, no
`case_based_preview`) must still validate and render with the new CBP
wiring present.

This test is the regression fence for the entire v2 arc, not just PR #1.
It must outlive the v2 transition; future PRs that "rename a content_json
key" or "remove a legacy phase" should fail here loudly.

Risk-auditor blocker #3 for PR #1 (moved forward from PR #5).
"""
from __future__ import annotations

from server.schemas.content import ContentJSON
from server.services.injector import inject


def _legacy_content_dict():
    """Minimal legacy content shape — no flow_version, no case_based_preview,
    no memory_check. Closest match to fixtures present in `fixtures/` for
    pre-v2 homeworks."""
    return {
        "meta": {"title": "Legacy HW", "subject_display": "Math", "section": "1"},
        "panels": [],
        "quotes": [],
        # Flat `{term, def}` shape — matches FlashcardItem schema.
        "flashcards": [{"term": "Cell", "def": "Basic unit"}],
        "memory_sprint": [],
        "boss_questions": [],
    }


def test_legacy_contentjson_validates_without_flow_version_or_cbp():
    cj = ContentJSON(**_legacy_content_dict())
    assert cj.flow_version is None
    assert cj.case_based_preview is None


def test_legacy_homework_renders_with_empty_cbp_stub():
    """The CBP stub should be present but with an empty object payload
    when the homework doesn't carry CBP content."""
    html = inject(_legacy_content_dict(), runtime_context={
        "hw_id": "LEGACY-1",
        "subject": "biology",
        "grade": 6,
    })
    # CBP stub must be present (added by PR #1) and remain as `{}` for
    # legacy homeworks that don't supply case_based_preview content.
    assert "const CBP = {}" in html


def test_legacy_homework_preserves_all_sibling_constants():
    html = inject(_legacy_content_dict(), runtime_context={
        "hw_id": "LEGACY-2",
        "subject": "biology",
        "grade": 6,
    })
    # PR #1 must not stomp any sibling JS constant. All five _OBJECT_CONSTANTS
    # entries should appear in the rendered HTML.
    for needle in ["const MC", "const CBP", "const READING", "const CONSOLIDATION", "const REFLECTION"]:
        assert needle in html, f"Missing JS constant: {needle}"


def test_legacy_homework_renders_flashcards_unchanged():
    html = inject(_legacy_content_dict(), runtime_context={
        "hw_id": "LEGACY-3",
        "subject": "biology",
        "grade": 6,
    })
    # The flashcard from the legacy fixture should appear in the array const.
    assert "const FLASHCARDS" in html
    assert "Cell" in html  # the flashcard term
