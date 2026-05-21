from __future__ import annotations

import pytest
from pydantic import ValidationError

from server.schemas.content import ContentJSON, MemoryCheck


def _valid_item(**overrides):
    item = {
        "type": "mcq",
        "prompt": "Which term means energy release in cells?",
        "options": ["chloroplast", "mitochondria", "vacuole", "ribosome"],
        "answer_spec": {"type": "option_index", "option_index": 1},
        "flashcard_ref": "mitochondria",
        "explanation": "Mitochondria release usable energy.",
    }
    item.update(overrides)
    return item


def test_memory_check_accepts_v1_modes_and_extra_fields():
    content = ContentJSON(
        flow_version="v2",
        flashcards=[{"term": "Mitochondria", "def": "Energy release organelle"}],
        memory_check={
            "pass_threshold_pct": 60,
            "modes_enabled": ["mcq", "fill_blank", "choose_explanation", "true_false"],
            "items": [
                _valid_item(),
                _valid_item(
                    type="fill_blank",
                    prompt="Cells release usable energy in _____.",
                    options=None,
                    answer_spec={
                        "type": "text_exact",
                        "expected": "mitochondria",
                        "accepted_answers": ["Mitochondria"],
                    },
                    source_note="extra fields are preserved",
                ),
                _valid_item(
                    type="choose_explanation",
                    prompt="Why is mitochondria the right answer?",
                    options=[
                        "It stores water.",
                        "It releases energy through cellular respiration.",
                        "It makes sunlight.",
                        "It builds cell walls.",
                    ],
                    answer_spec={"type": "option_index", "option_index": 1},
                ),
                _valid_item(
                    type="true_false",
                    prompt="Mitochondria help release usable energy.",
                    options=["True", "False"],
                    answer_spec={"type": "option_index", "option_index": 0},
                ),
            ],
        },
    )

    assert content.flow_version == "v2"
    assert content.memory_check is not None
    assert content.memory_check.items[1].model_extra["source_note"] == "extra fields are preserved"


def test_memory_check_rejects_deferred_modes_for_v1_runtime():
    with pytest.raises(ValidationError):
        MemoryCheck(items=[_valid_item(type="tile_match")])
