"""Schema tests for the additive CaseBasedPreview.blocks[] presentation overlay.

`blocks[]` lets authors interleave text pages and checkpoints in presentation
order. It is a PRESENTATION layer only: `checkpoints[]` stays the canonical
checkpoint list, and a checkpoint block carries `ref` = the index into
`checkpoints[]`. content_json is FROZEN-ADDITIVE (CONTRACTS.md) — these tests
lock that `blocks` is a new OPTIONAL key that never breaks legacy CBPs and that
the field is permissive (unknown keys allowed, no answer-bearing data required).

Style mirrors tests/test_content_json_validation.py.
"""

from server.schemas.content import (
    CaseBasedPreview,
    CaseBlock,
    ContentJSON,
)


def test_cbp_blocks_field_is_additive_and_permissive():
    """A CBP authored with the new blocks[] overlay validates: a text block
    (title + body) and a checkpoint block (type + ref into checkpoints[])
    parse, unknown extra keys are allowed (_Permissive), and a legacy CBP with
    NO blocks still validates (field is Optional, defaults to None)."""
    cbp = CaseBasedPreview.model_validate(
        {
            "title": "Case",
            "checkpoints": [
                {
                    "question": "Q1",
                    "options": ["a", "b"],
                    "answer_spec": {"type": "option_index", "expected": 1},
                },
            ],
            "blocks": [
                {"type": "text", "title": "Case", "body": "Here is the setup..."},
                {"type": "checkpoint", "ref": 0},
                # Unknown extra key on a block must be tolerated (_Permissive).
                {"type": "text", "body": "Wrap-up", "layout": "wide"},
            ],
        }
    )

    assert cbp.blocks is not None
    assert len(cbp.blocks) == 3

    text_block = cbp.blocks[0]
    assert isinstance(text_block, CaseBlock)
    assert text_block.type == "text"
    assert text_block.title == "Case"
    assert text_block.body == "Here is the setup..."
    # A text block carries no checkpoint reference.
    assert text_block.ref is None

    checkpoint_block = cbp.blocks[1]
    assert checkpoint_block.type == "checkpoint"
    # ref is a PRESENTATION-ORDER index into the canonical checkpoints[].
    assert checkpoint_block.ref == 0
    # checkpoints[] stays canonical and unchanged by the overlay.
    assert cbp.checkpoints is not None
    assert len(cbp.checkpoints) == 1

    # Unknown extra key survived on the third block (_Permissive / extra="allow").
    assert getattr(cbp.blocks[2], "layout", None) == "wide"

    # A legacy CBP with NO blocks still validates; field defaults to None.
    legacy = CaseBasedPreview.model_validate(
        {"checkpoints": [{"question": "Q", "answer_spec": {"type": "option_index", "expected": 0}}]}
    )
    assert legacy.blocks is None

    # Full ContentJSON round-trip with blocks embedded — must not raise.
    ContentJSON.model_validate(
        {
            "case_based_preview": {
                "checkpoints": [
                    {"question": "Q", "answer_spec": {"type": "option_index", "expected": 0}}
                ],
                "blocks": [
                    {"type": "text", "title": "Intro", "body": "..."},
                    {"type": "checkpoint", "ref": 0},
                ],
            }
        }
    )


def test_cbp_blocks_absent_preserves_legacy():
    """A CaseBasedPreview with only checkpoints[] (no blocks) round-trips
    unchanged — the additive field must not alter legacy behavior."""
    payload = {
        "title": "Legacy Case",
        "case_setup": {"story": "...", "role": "...", "task": "..."},
        "checkpoints": [
            {
                "kind": "identify",
                "question": "What applies here?",
                "options": ["x", "y", "z"],
                "answer_spec": {"type": "option_index", "expected": 2},
                "learning_block": "Because...",
            },
            {
                "kind": "decide",
                "question": "What next?",
                "options": ["a", "b"],
                "answer_spec": {"type": "option_index", "expected": 0},
            },
        ],
    }

    cbp = CaseBasedPreview.model_validate(payload)

    # blocks is absent -> None; everything else is preserved.
    assert cbp.blocks is None
    assert cbp.title == "Legacy Case"
    assert cbp.checkpoints is not None
    assert len(cbp.checkpoints) == 2
    assert cbp.checkpoints[0].kind == "identify"
    assert cbp.checkpoints[1].answer_spec is not None

    # Round-trips through ContentJSON without raising or mutating shape.
    ContentJSON.model_validate({"case_based_preview": payload})
