"""Unit tier — pure Pydantic validation. No DB, no TestClient, <50ms each.

Asserts the locked-in CBP schema invariants from PR #1 brainstorm:
  - exactly 3 checkpoints
  - canonical kind order [identify, decide, justify]
  - extra="allow" propagation to nested classes
  - retake_variants forward-ref resolves
  - flow_version Literal["v1","v2"] still rejects v3
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from server.schemas.content import (
    CaseBasedPreview,
    Checkpoint,
    ContentJSON,
    FinalSimulation,
    LearningBlock,
)

from factories import valid_cbp_dict, valid_checkpoint


def test_minimal_valid_cbp_accepts_three_canonical_checkpoints():
    cbp = CaseBasedPreview(**valid_cbp_dict())
    assert len(cbp.checkpoints) == 3
    assert [c.kind for c in cbp.checkpoints] == ["identify", "decide", "justify"]


@pytest.mark.parametrize("n", [0, 1, 2, 4, 5])
def test_rejects_wrong_checkpoint_count(n):
    payload = valid_cbp_dict()
    base = payload["checkpoints"]
    if n == 0:
        payload["checkpoints"] = []
    elif n < 3:
        payload["checkpoints"] = base[:n]
    else:
        payload["checkpoints"] = base + [valid_checkpoint("justify")] * (n - 3)
    with pytest.raises(ValidationError):
        CaseBasedPreview(**payload)


def test_rejects_wrong_checkpoint_order():
    payload = valid_cbp_dict()
    payload["checkpoints"] = [
        valid_checkpoint("decide"),
        valid_checkpoint("identify"),
        valid_checkpoint("justify"),
    ]
    with pytest.raises(ValidationError) as exc_info:
        CaseBasedPreview(**payload)
    msg = str(exc_info.value).lower()
    assert "order" in msg or "kind" in msg, f"Validator message should hint at order/kind: {msg}"


def test_extra_allow_propagates_to_cbp_and_nested():
    payload = valid_cbp_dict(author="someone")
    payload["checkpoints"][0]["author_note"] = "added later"
    cbp = CaseBasedPreview(**payload)
    assert cbp.model_extra is not None
    assert cbp.model_extra["author"] == "someone"
    assert cbp.checkpoints[0].model_extra["author_note"] == "added later"


def test_retake_variants_defaults_to_empty_list():
    cbp = CaseBasedPreview(**valid_cbp_dict())
    for cp in cbp.checkpoints:
        assert cp.retake_variants == []


def test_retake_variants_accepts_nested_checkpoints():
    payload = valid_cbp_dict()
    payload["checkpoints"][0]["retake_variants"] = [valid_checkpoint("identify")]
    cbp = CaseBasedPreview(**payload)
    assert len(cbp.checkpoints[0].retake_variants) == 1
    assert cbp.checkpoints[0].retake_variants[0].kind == "identify"


def test_kind_field_is_required():
    payload = valid_cbp_dict()
    del payload["checkpoints"][0]["kind"]
    with pytest.raises(ValidationError):
        CaseBasedPreview(**payload)


def test_kind_rejects_unknown_values():
    payload = valid_cbp_dict()
    payload["checkpoints"][0]["kind"] = "reflect"  # not in Literal
    with pytest.raises(ValidationError):
        CaseBasedPreview(**payload)


def test_final_simulation_text_only_no_svg_field():
    """PR #1 ships text-only `visual_description`; sanitized SVG is deferred
    to PR #6 per risk-auditor blocker #1."""
    fs = FinalSimulation(correct_path="ok", wrong_path="bad")
    assert fs.visual_description is None
    assert "visual_description" in FinalSimulation.model_fields
    assert "visual_svg" not in FinalSimulation.model_fields
    assert "visual_description_or_svg" not in FinalSimulation.model_fields


def test_contentjson_round_trips_cbp_with_flow_version_v2():
    cj = ContentJSON(flow_version="v2", case_based_preview=valid_cbp_dict())
    dumped = cj.model_dump()
    re_imported = ContentJSON(**dumped)
    assert re_imported.flow_version == "v2"
    assert re_imported.case_based_preview is not None
    assert len(re_imported.case_based_preview.checkpoints) == 3


def test_flow_version_v3_rejected_by_existing_literal():
    """Confirms current behavior — Literal["v1","v2"] still rejects "v3".
    If a future PR widens the literal, this test must be updated explicitly."""
    with pytest.raises(ValidationError):
        ContentJSON(flow_version="v3", case_based_preview=valid_cbp_dict())


def test_learning_block_consequence_preview_optional():
    lb_no_cp = LearningBlock(body="just a body")
    assert lb_no_cp.consequence_preview is None
    lb_with_cp = LearningBlock(body="b", consequence_preview="c")
    assert lb_with_cp.consequence_preview == "c"
