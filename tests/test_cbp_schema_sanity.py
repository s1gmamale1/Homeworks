"""Sanity tier — does the new CBP wiring actually exist?

Pure introspection: no DB, no FastAPI client, no HTML rendering. Confirms
that the keys, classes, constants, and template stub PR #1 promised are
actually in place. Cheap (<0.5s) and catches "shipped the schema but
forgot the injector / template / etc." failure modes.
"""
from __future__ import annotations

import typing
from pathlib import Path


def test_case_based_preview_field_on_contentjson():
    from server.schemas.content import ContentJSON
    assert "case_based_preview" in ContentJSON.model_fields


def test_case_based_preview_field_type():
    from server.schemas.content import CaseBasedPreview, ContentJSON
    fld = ContentJSON.model_fields["case_based_preview"]
    ann = fld.annotation
    # annotation should resolve to Optional[CaseBasedPreview] = Union[CaseBasedPreview, None]
    args = typing.get_args(ann)
    assert CaseBasedPreview in (ann, *args)


def test_flow_version_field_on_contentjson():
    from server.schemas.content import ContentJSON
    assert "flow_version" in ContentJSON.model_fields


def test_cbp_in_object_constants():
    from server.services.injector import _OBJECT_CONSTANTS
    assert ("case_based_preview", "CBP") in _OBJECT_CONSTANTS


def test_template_contains_cbp_stub():
    from server.config import BASE_DIR
    tpl = (BASE_DIR / "server" / "template" / "perfect_homework.html").read_text(encoding="utf-8")
    assert "const CBP = {};" in tpl


def test_template_keeps_existing_mc_stub():
    """Regression fence: PR #1 must not have stomped on the existing
    `const MC = {};` stub from PR #233."""
    from server.config import BASE_DIR
    tpl = (BASE_DIR / "server" / "template" / "perfect_homework.html").read_text(encoding="utf-8")
    assert "const MC = {};" in tpl


def test_decision_process_explanation_field_present():
    """Backend-prompts-audit finding F1: CBP Standard §5 + Infra family
    prompts ALL mandate a Decision Process Explanation (DPE) step between
    Checkpoint 3 and final_simulation. The CaseBasedPreview schema must
    carry a `decision_process_explanation` field so generators can populate
    the three sub-prompts (concept / method / mistake)."""
    from server.schemas.content import CaseBasedPreview, DecisionProcessExplanation
    assert "decision_process_explanation" in CaseBasedPreview.model_fields
    fld = CaseBasedPreview.model_fields["decision_process_explanation"]
    args = typing.get_args(fld.annotation)
    assert DecisionProcessExplanation in (fld.annotation, *args)
    assert "concept" in DecisionProcessExplanation.model_fields
    assert "method" in DecisionProcessExplanation.model_fields
    assert "mistake" in DecisionProcessExplanation.model_fields


def test_checkpoint_kinds_are_locked_literal():
    from server.schemas.content import Checkpoint
    fld = Checkpoint.model_fields["kind"]
    args = typing.get_args(fld.annotation)
    assert set(args) == {"identify", "decide", "justify"}


def test_contentjson_full_round_trip_with_cbp():
    from server.schemas.content import ContentJSON
    from factories import full_content_json_with_cbp

    src = full_content_json_with_cbp()
    cj = ContentJSON(**src)
    dumped = cj.model_dump(exclude_none=True)
    cj2 = ContentJSON(**dumped)
    assert cj2.case_based_preview is not None
    assert len(cj2.case_based_preview.checkpoints) == 3
    assert [c.kind for c in cj2.case_based_preview.checkpoints] == ["identify", "decide", "justify"]
