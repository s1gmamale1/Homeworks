"""
AMR 2-axis grading: schema and payload contract tests.

Locks in the contract that boss_turn and tutor_help:
  - pass amr_mode=True in the payload sent to the LLM
  - declare axis_1, axis_2, axis_1_label, axis_2_label in the schema_hint
  - return those axis fields back through to the caller

Downstream consumers (the runtime aggregator that builds the Stage-9 AMR
scorecard) depend on these keys showing up. If a future refactor drops one
of them, these tests should fail fast.

Run:
    python -m pytest tests/test_tutor_amr.py -v
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch, AsyncMock


def _run(coro):
    """Run an async coroutine in a fresh event loop."""
    return asyncio.new_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# boss_turn — every Final Boss attack must request AMR axes
# ---------------------------------------------------------------------------


@patch("server.services.tutor.gemini.generate_json", new_callable=AsyncMock)
def test_boss_turn_requests_amr_mode(mock_generate_json):
    from server.services import tutor

    mock_generate_json.return_value = {
        "correct": True,
        "damage_dealt": 30,
        "boss_response": "Kuchli zarba!",
        "hint": None,
        "score": 1.0,
        "axis_1": 4,
        "axis_2": 4,
        "axis_1_label": "Mastered",
        "axis_2_label": "Mastered",
    }

    result = _run(tutor.boss_turn(
        boss_question="Aylanadan tashqaridagi P nuqtadan ikkita kesuvchi ...",
        student_answer="∠P = (100° − 40°)/2 = 30°.",
        expected_answers=["30", "30°"],
        damage_value=30,
        hp_remaining=100,
        attempt_number=1,
        subject="geometriya-g7-11",
        grade=8,
    ))

    assert mock_generate_json.await_count == 1
    call = mock_generate_json.await_args_list[0]
    prompt_arg = call.args[0]
    schema = call.kwargs["schema_hint"]

    # The payload (rendered as JSON inside prompt_arg) must carry amr_mode:true.
    assert '"amr_mode": true' in prompt_arg, (
        "boss_turn must inject amr_mode=true so the rubric block in "
        "boss-tutor.md emits axis_1/axis_2."
    )

    # The schema_hint must declare every AMR axis field.
    for key in ("axis_1", "axis_2", "axis_1_label", "axis_2_label"):
        assert key in schema, (
            f"boss_turn schema is missing {key!r} — runtime aggregator "
            f"won't see it on the response."
        )

    # The result is passed through to the caller intact.
    assert result["axis_1"] == 4
    assert result["axis_2"] == 4
    assert result["axis_1_label"] == "Mastered"
    assert result["axis_2_label"] == "Mastered"


# ---------------------------------------------------------------------------
# tutor_help — chat coaching turns must also return AMR axes
# ---------------------------------------------------------------------------


@patch("server.services.tutor.gemini.generate_json", new_callable=AsyncMock)
def test_tutor_help_requests_amr_mode(mock_generate_json):
    from server.services import tutor

    mock_generate_json.return_value = {
        "response": "Pifagor teoremasini eslang.",
        "guidance_type": "hint",
        "axis_1": 2,
        "axis_2": 1,
        "axis_1_label": "Apprentice",
        "axis_2_label": "Novice",
    }

    result = _run(tutor.tutor_help(
        phase="practice",
        question="d = ?",
        student_input="13",
        subject="geometriya-g7-11",
        grade=8,
    ))

    assert mock_generate_json.await_count == 1
    call = mock_generate_json.await_args_list[0]
    prompt_arg = call.args[0]
    schema = call.kwargs["schema_hint"]

    assert '"amr_mode": true' in prompt_arg, (
        "tutor_help must inject amr_mode=true so chat exchanges feed the "
        "report card alongside the coaching text."
    )

    for key in ("axis_1", "axis_2", "axis_1_label", "axis_2_label"):
        assert key in schema, (
            f"tutor_help schema is missing {key!r}."
        )

    # Result should still carry the standard tutor-help fields plus the axes.
    assert result["response"]
    assert result["guidance_type"] == "hint"
    assert result["axis_1"] == 2
    assert result["axis_2"] == 1
