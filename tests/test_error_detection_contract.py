"""Error Detection (MARK shape) — schema contract + hydration redaction fence.

The MARK shape shows the student a complete, confident, WRONG artifact and asks
them to tap the segment where it goes wrong. The answer key is a set of SEGMENT
IDS (`faulty_segment_ids`) plus `category` / `fix` / `explanation`.

Two things are guarded here:

1. **The answer key never reaches the browser.** If `faulty_segment_ids`
   survives hydration the game is unplayable — the DOM literally names the
   answer. Treat a failure as a release blocker.
2. **The answer key must point at a segment that exists.** An `ed` item whose
   `faulty_segment_ids` names a missing segment is ungradeable (Jaccard against
   a phantom id can never score 1.0), and it is the bug most worth catching at
   the authoring boundary.

`faulty_segment_ids: []` is LEGAL — it is the deliberate clean artifact, the one
item per set that stops "there is always an error somewhere" from being a free
heuristic. It must never be validated away.
"""
from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from server.schemas.content import ContentJSON
from server.services.runtime_redactor import redact_for_runtime

# Every ⛔ server-only field on the MARK shape.
ED_SERVER_ONLY_KEYS = ["faulty_segment_ids", "category", "fix", "explanation"]

# Unique sentinels planted on each server-only field.
# NB: no sentinel on `category` — its value must be a member of the
# student-visible `categories` list, so planting one there would make the
# sentinel legitimately visible. `category` is covered by key-absence below.
LEAK_TOKENS = ["LEAK_ED_FIX", "LEAK_ED_EXPLANATION"]


def _mark_item(**over) -> dict:
    """The worked example from the design doc: a transposition error whose
    downstream steps stay internally consistent with it."""
    item = {
        "id": "ed_001",
        "artifact": {
            "kind": "worked_solution",
            "segments": [
                {"id": "s1", "text": "2x + 6 = 14", "svg": None},
                {"id": "s2", "text": "2x = 14 + 6", "svg": None},
                {"id": "s3", "text": "2x = 20", "svg": None},
                {"id": "s4", "text": "x = 10", "svg": None},
            ],
        },
        "stages": ["mark", "classify", "correct"],
        "categories": ["sign", "transpose", "arithmetic"],
        "faulty_segment_ids": ["s2"],
        "category": "transpose",
        "fix": "LEAK_ED_FIX",
        "explanation": "LEAK_ED_EXPLANATION",
        "tags": "[Bloom: L3 | PISA: L2]",
        "difficulty": "easy",
    }
    item.update(over)
    return item


def _ed_homework_content() -> dict:
    """A homework carrying the MARK shape, the clean artifact, the LEGACY
    work_blocks shape, and a Mystery Box item whose `category` is display text."""
    return {
        "flow_version": "v2",
        "meta": {"title": "Error Detection fence"},
        "gb_error_detection": [
            _mark_item(),
            # The mandatory clean artifact — no error, nothing to mark.
            _mark_item(
                id="ed_002",
                faulty_segment_ids=[],
                category=None,
                fix=None,
                explanation=None,
            ),
            # Legacy Division-3 shape must keep working on the same key.
            {
                "id": "ed_legacy",
                "instructions": "Find the broken step.",
                "work_blocks": [
                    {"id": "b0", "text": "step zero visible", "is_broken": False},
                    {"id": "b1", "text": "step one visible", "is_broken": True},
                ],
                "correction_answer_spec": {"type": "text_exact", "expected": "LEAK_ED_CORR_SPEC"},
            },
        ],
        # Regression guard: `category` here is STUDENT-VISIBLE display text.
        "gb_mystery_box": [
            {"id": "mb1", "q": "Mystery question visible", "category": "Algebra visible"},
        ],
    }


# ---------------------------------------------------------------------------
# 1. Hydration redaction — the answer key must not survive.
# ---------------------------------------------------------------------------

def test_faulty_segment_ids_does_not_survive_hydration():
    """The one assertion the task asks for: hydrate, then fail if the answer
    key is still there."""
    safe = redact_for_runtime(_ed_homework_content(), hw_id="HW-ED")
    for item in safe["gb_error_detection"]:
        assert "faulty_segment_ids" not in item, (
            f"answer key leaked to the student: {item.get('faulty_segment_ids')!r}"
        )


@pytest.mark.parametrize("key", ED_SERVER_ONLY_KEYS)
def test_ed_server_only_key_stripped(key):
    safe = redact_for_runtime(_ed_homework_content(), hw_id="HW-ED")
    for item in safe["gb_error_detection"]:
        assert key not in item, f"server-only key {key!r} survived hydration"


@pytest.mark.parametrize("token", LEAK_TOKENS)
def test_no_leak_sentinel_anywhere_in_payload(token):
    """Belt and braces: the sentinel must not appear at ANY nesting depth."""
    safe = redact_for_runtime(_ed_homework_content(), hw_id="HW-ED")
    assert token not in json.dumps(safe, ensure_ascii=False)


def test_student_visible_content_survives():
    """The artifact itself, the segment ids and the category CHOICES are what
    the student plays with — stripping them would leave an empty board."""
    safe = redact_for_runtime(_ed_homework_content(), hw_id="HW-ED")
    blob = json.dumps(safe, ensure_ascii=False)
    for text in ("2x + 6 = 14", "2x = 14 + 6", "2x = 20", "x = 10"):
        assert text in blob, f"artifact segment text was stripped: {text!r}"
    item = safe["gb_error_detection"][0]
    assert [s["id"] for s in item["artifact"]["segments"]] == ["s1", "s2", "s3", "s4"]
    assert item["stages"] == ["mark", "classify", "correct"]
    # The closed list is SHOWN to the student; only the answer `category` is not.
    assert item["categories"] == ["sign", "transpose", "arithmetic"]


def test_mystery_box_category_is_not_collateral_damage():
    """`category` is stripped per-game, NOT globally — Mystery Box renders it."""
    safe = redact_for_runtime(_ed_homework_content(), hw_id="HW-ED")
    assert safe["gb_mystery_box"][0]["category"] == "Algebra visible"


def test_redactor_does_not_mutate_input():
    raw = _ed_homework_content()
    redact_for_runtime(raw, hw_id="HW-ED")
    assert raw["gb_error_detection"][0]["faulty_segment_ids"] == ["s2"]
    assert raw["gb_error_detection"][0]["category"] == "transpose"


# ---------------------------------------------------------------------------
# 2. Schema contract — delivery mode.
# ---------------------------------------------------------------------------

def _validate(item: dict):
    return ContentJSON.model_validate({"gb_error_detection": [item]})


def test_valid_mark_item_passes():
    _validate(_mark_item())


def test_clean_artifact_is_legal():
    """`faulty_segment_ids: []` must NOT be validated away."""
    _validate(_mark_item(faulty_segment_ids=[], category=None))


def test_mark_only_item_needs_no_categories():
    _validate(_mark_item(stages=["mark"], categories=None, category=None))


def test_answer_key_pointing_at_missing_segment_is_rejected():
    """The bug most worth catching."""
    with pytest.raises(ValidationError, match="do not exist in artifact.segments"):
        _validate(_mark_item(faulty_segment_ids=["s9"]))


def test_duplicate_segment_ids_rejected():
    with pytest.raises(ValidationError, match="more than once"):
        _validate(_mark_item(artifact={"kind": "equation", "segments": [
            {"id": "s1", "text": "a"}, {"id": "s1", "text": "b"}]}))


def test_empty_segments_rejected():
    with pytest.raises(ValidationError, match="segments must be non-empty"):
        _validate(_mark_item(artifact={"kind": "equation", "segments": []}))


def test_segment_text_over_500_chars_rejected():
    with pytest.raises(ValidationError, match="500 chars"):
        _validate(_mark_item(
            artifact={"kind": "equation", "segments": [{"id": "s1", "text": "x" * 501}]},
            faulty_segment_ids=[], category=None))


def test_stages_must_contain_mark():
    with pytest.raises(ValidationError, match="must contain 'mark'"):
        _validate(_mark_item(stages=["classify"]))


def test_stages_must_be_a_known_subset():
    with pytest.raises(ValidationError, match="unsupported value"):
        _validate(_mark_item(stages=["mark", "guess"]))


def test_classify_requires_categories():
    with pytest.raises(ValidationError, match="categories must be non-empty"):
        _validate(_mark_item(categories=[]))


def test_category_must_be_in_categories():
    with pytest.raises(ValidationError, match="is not in categories"):
        _validate(_mark_item(category="unlisted"))


def test_faulty_item_requires_a_category_when_classifying():
    with pytest.raises(ValidationError, match="category is required"):
        _validate(_mark_item(category=None))


def test_authoring_context_defers_validation():
    """A half-written item must not 400 the builder's autosave."""
    ContentJSON.model_validate(
        {"gb_error_detection": [_mark_item(faulty_segment_ids=["s9"], stages=[])]},
        context={"authoring": True},
    )


def test_legacy_work_blocks_item_still_validates():
    """The MARK validator must not touch the live Division-3 shape."""
    _validate({
        "id": "ed_legacy",
        "instructions": "Find the broken step.",
        "pattern": "math",
        "work_blocks": [
            {"id": "b0", "text": "2x = 10", "is_broken": False},
            {"id": "b1", "text": "x = 10 + 2", "is_broken": True},
        ],
        "correction_answer_spec": {"type": "text_exact", "expected": "x = 5"},
        "hint": "Re-check the operation.",
        "why_prompt": "Explain why the step is wrong.",
    })
