"""Pydantic validation tests for content_json at the PUT+PATCH boundary.

GPT-5.5 audit (2026-04-29) flagged content_json as the largest long-term
safety risk — a dropped key today silently corrupts a homework with no error.
These tests lock the boundary contract: every existing fixture in fixtures/
must pass validation, obviously-wrong shapes must fail, and the route layer
must surface a 400 INVALID_CONTENT on bad PUT/PATCH bodies.
"""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from server.schemas.content import (
    AdaptiveQuizItem,
    AnswerSpec,
    BossQuestion,
    ContentJSON,
    FlashcardItem,
    MemorySprintItem,
    MysteryBoxItem,
    PuzzleLockItem,
    ReadingPhase,
    RealLifePhase,
    ReflectionPhase,
    TttItem,
    WhyChainItem,
)


FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


# --------------------------------------------------------------------------- #
# 1. Every existing production fixture validates.
# --------------------------------------------------------------------------- #


HOMEWORK_FIXTURES = sorted(
    p for p in FIXTURES_DIR.glob("*.json") if p.name != "tutor-tests.json"
)


@pytest.mark.parametrize("fixture_path", HOMEWORK_FIXTURES, ids=lambda p: p.name)
def test_existing_fixture_validates(fixture_path: Path):
    """Schema must accept every homework currently in fixtures/. If this
    fails, the schema is stricter than production data — loosen it."""
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    ContentJSON.model_validate(data)


# --------------------------------------------------------------------------- #
# 2. Per-phase: valid sample + invalid sample, for all 7 phase types.
# --------------------------------------------------------------------------- #


# ---- Phase 1: flashcards -------------------------------------------------- #


def test_flashcards_valid_with_def_alias():
    """Production fixtures use the bare key `def`, not `definition`."""
    item = FlashcardItem.model_validate({"term": "DNK", "def": "Irsiy material"})
    assert item.term == "DNK"
    assert item.definition == "Irsiy material"


def test_flashcards_missing_term_rejected():
    with pytest.raises(ValidationError):
        FlashcardItem.model_validate({"def": "no term here"})


# ---- Phase 2: memory_sprint ---------------------------------------------- #


def test_memory_sprint_valid_multi_choice():
    item = MemorySprintItem.model_validate(
        {
            "type": "KO",
            "prompt": "Which is correct?",
            "options": ["A", "B", "C", "D"],
            "correct": 1,
        }
    )
    assert item.correct == 1
    assert len(item.options) == 4


def test_memory_sprint_missing_prompt_rejected():
    with pytest.raises(ValidationError):
        MemorySprintItem.model_validate({"options": ["A", "B"], "correct": 0})


# ---- Phase 3: real_life --------------------------------------------------- #


def test_real_life_valid_with_mixed_question_shapes():
    """Real-life questions in production come in 3 shapes simultaneously:
    {prompt, ans, fb}, {prompt, fields, fb}, {prompt, open, fb}."""
    phase = RealLifePhase.model_validate(
        {
            "badge": "VAZIFA · X",
            "story": "scenario...",
            "q1": {"prompt": "Q1?", "ans": "A1", "fb": "good"},
            "q2": {
                "prompt": "Q2?",
                "fields": [{"id": "a", "label": "a=", "ans": "5"}],
                "fb": "yes",
            },
            "q3": {"prompt": "Q3?", "open": True, "fb": "open response"},
        }
    )
    assert phase.q1.ans == "A1"
    assert phase.q2.fields[0].ans == "5"
    assert phase.q3.open is True


def test_real_life_question_missing_prompt_rejected():
    with pytest.raises(ValidationError):
        RealLifePhase.model_validate({"q1": {"ans": "no prompt"}})


# ---- Phase 4: reading ----------------------------------------------------- #


def test_reading_valid_with_checkpoints():
    phase = ReadingPhase.model_validate(
        {
            "text": "Long passage about AI...",
            "checkpoints": [
                {"q": "Main topic?", "tags": "[Bloom: L2]", "ans": ["AI debate"]}
            ],
        }
    )
    assert phase.checkpoints[0].q == "Main topic?"


def test_reading_phase_must_have_list_for_checkpoints():
    """checkpoints must be a list of objects, not a string."""
    with pytest.raises(ValidationError):
        ReadingPhase.model_validate({"checkpoints": "not a list"})


# ---- Phase 5: boss_questions --------------------------------------------- #


def test_boss_question_valid_with_answer_spec():
    item = BossQuestion.model_validate(
        {
            "q": "x² - 9x + 20 = 0 ildizlar yig'indisi?",
            "tags": "[Bloom: L2]",
            "ans": ["9"],
            "hint": "Viyet teoremasi",
            "dmg": 10,
            "answer_spec": {
                "type": "numeric",
                "expected": 9,
                "canonical_display": "9",
                "allow_ai_fallback": False,
                "tolerance": 0,
            },
            "accepted_answers": ["9"],
        }
    )
    assert item.answer_spec.type == "numeric"
    assert item.answer_spec.expected == 9


def test_boss_question_with_wrong_dmg_type_rejected():
    """`dmg` must be a number, not a list. Type coercion catches obviously
    wrong shapes even when `q`/`prompt` keys are flexible."""
    with pytest.raises(ValidationError):
        BossQuestion.model_validate({"q": "Q?", "ans": ["X"], "dmg": ["not", "a", "number"]})


# ---- Phase 6: game_breaks ------------------------------------------------ #


def test_adaptive_quiz_item_valid():
    item = AdaptiveQuizItem.model_validate(
        {
            "q": "What is 7+8?",
            "tier": "EASY",
            "ans": ["15"],
            "answer_spec": {"type": "numeric", "expected": 15, "tolerance": 0},
            "accepted_answers": ["15"],
        }
    )
    assert item.tier == "EASY"


def test_why_chain_valid():
    item = WhyChainItem.model_validate(
        {
            "q": "Why is Vieta's theorem useful?",
            "inv": "without solving",
            "reprompts": ["Think about sum of roots", "Hint two"],
        }
    )
    assert len(item.reprompts) == 2


def test_puzzle_lock_accepts_legacy_aliases():
    """Production tests show both {content,q,a} and legacy {text,question,answer}."""
    new_shape = PuzzleLockItem.model_validate(
        {"content": "<b>3x</b>", "q": "x = ?", "a": "3"}
    )
    legacy = PuzzleLockItem.model_validate(
        {"text": "legacy tile", "question": "legacy q", "answer": "legacy a"}
    )
    assert new_shape.q == "x = ?"
    assert legacy.question == "legacy q"


def test_mystery_box_valid():
    item = MysteryBoxItem.model_validate(
        {"category": "Algebra", "q": "Solve 3x+5=14", "a": "3"}
    )
    assert item.category == "Algebra"


def test_ttt_valid_with_three_distractors():
    item = TttItem.model_validate(
        {"q": "What is 7 x 8?", "correct": "56", "distractors": ["54", "48", "63"]}
    )
    assert len(item.distractors) == 3


def test_game_breaks_arrays_must_be_lists_not_strings():
    """Top-level shape check — gb_* must be lists if present."""
    with pytest.raises(ValidationError):
        ContentJSON.model_validate({"gb_adaptive_quiz": "not a list"})


# ---- Phase 7: reflection -------------------------------------------------- #


def test_reflection_valid_full_shape():
    phase = ReflectionPhase.model_validate(
        {
            "summary": "Today we learned...",
            "question": "What was hardest?",
            "spaced_rep": "Tomorrow review...",
            "closing": "Good job!",
        }
    )
    assert phase.summary.startswith("Today")


def test_reflection_rejects_non_dict():
    with pytest.raises(ValidationError):
        ContentJSON.model_validate({"reflection": "should be an object"})


# --------------------------------------------------------------------------- #
# 3. AnswerSpec — the load-bearing grading contract.
# --------------------------------------------------------------------------- #


def test_answer_spec_accepts_all_known_types():
    """answer_checker.py dispatches on `type`. Schema must accept every variant
    currently used so the boundary doesn't lock out grading types."""
    for spec in [
        {"type": "numeric", "expected": 7, "tolerance": 0.5},
        {"type": "text_exact", "expected": "B", "allow_ai_fallback": False},
        {"type": "text_fuzzy", "expected": "for", "allow_ai_fallback": True},
        {"type": "set_match", "expected": ["A", "B"]},
        {"type": "option_index", "option_index": 2},
    ]:
        AnswerSpec.model_validate(spec)


# --------------------------------------------------------------------------- #
# 4. Top-level — partial homeworks still validate; obvious shape errors fail.
# --------------------------------------------------------------------------- #


def test_top_level_empty_dict_validates():
    """Every phase optional → an empty content_json is a valid (empty) homework."""
    ContentJSON.model_validate({})


def test_top_level_unknown_keys_allowed():
    """`extra='allow'` so frontend additions don't break old homeworks."""
    ContentJSON.model_validate({"future_phase_we_havent_modeled": [1, 2, 3]})


def test_top_level_flashcards_must_be_list_not_string():
    with pytest.raises(ValidationError):
        ContentJSON.model_validate({"flashcards": "not a list"})


def test_top_level_meta_must_be_object_not_list():
    with pytest.raises(ValidationError):
        ContentJSON.model_validate({"meta": ["not", "an", "object"]})


# --------------------------------------------------------------------------- #
# 5. Integration — PUT + PATCH route boundary.
# --------------------------------------------------------------------------- #


def _create_minimal_homework(client) -> str:
    resp = client.post(
        "/api/homeworks",
        json={
            "title": "Validation smoke",
            "subject": "math-algebra",
            "grade": 8,
            "mode": "hard",
            "content_json": {
                "meta": {"title": "Validation smoke", "section": "1"},
                "flashcards": [{"term": "T", "def": "D"}],
            },
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def test_put_with_valid_content_json_returns_200(client):
    hw_id = _create_minimal_homework(client)
    resp = client.put(
        f"/api/homeworks/{hw_id}",
        json={
            "content_json": {
                "meta": {"title": "Updated", "section": "2"},
                "flashcards": [{"term": "T2", "def": "D2"}],
                "boss_questions": [
                    {
                        "q": "Test?",
                        "ans": ["yes"],
                        "answer_spec": {"type": "text_fuzzy", "expected": "yes"},
                    }
                ],
            }
        },
    )
    assert resp.status_code == 200, resp.text


def test_put_with_invalid_content_json_returns_400_invalid_content(client):
    hw_id = _create_minimal_homework(client)
    resp = client.put(
        f"/api/homeworks/{hw_id}",
        # flashcards must be a list, not a string
        json={"content_json": {"flashcards": "this is not a list"}},
    )
    assert resp.status_code == 400, resp.text
    detail = resp.json()["detail"]
    assert detail["code"] == "INVALID_CONTENT"
    assert "details" in detail


def test_put_with_model_validator_error_returns_serializable_400(client):
    """Model-level ValueError ctx must not turn validation failures into 500s."""
    hw_id = _create_minimal_homework(client)
    resp = client.put(
        f"/api/homeworks/{hw_id}",
        json={
            "content_json": {
                "gb_tile_match": [
                    {"id": "tm_001", "left": "dup", "right": "one"},
                    {"id": "tm_002", "left": "dup", "right": "two"},
                ]
            }
        },
    )
    assert resp.status_code == 400, resp.text
    detail = resp.json()["detail"]
    assert detail["code"] == "INVALID_CONTENT"
    assert "ctx" not in detail["details"][0]
    assert "left strings must be unique" in detail["details"][0]["msg"]


def test_put_accepts_empty_tile_match_from_compat_read_path(client):
    """GET normalization can surface gb_tile_match=[]; builder PUT must accept it."""
    hw_id = _create_minimal_homework(client)
    resp = client.put(
        f"/api/homeworks/{hw_id}",
        json={
            "content_json": {
                "meta": {"title": "Updated", "section": "2"},
                "flashcards": [{"term": "T2", "def": "D2"}],
                "gb_tile_match": [],
            }
        },
    )
    assert resp.status_code == 200, resp.text


def test_patch_with_invalid_merged_content_returns_400(client):
    """PATCH must validate the *merged* result. A patch that replaces a
    well-typed array with a non-array must be rejected."""
    hw_id = _create_minimal_homework(client)
    resp = client.patch(
        f"/api/homeworks/{hw_id}/content",
        json={"content_json": {"flashcards": "not a list"}},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "INVALID_CONTENT"


def test_patch_with_valid_partial_content_returns_200(client):
    hw_id = _create_minimal_homework(client)
    resp = client.patch(
        f"/api/homeworks/{hw_id}/content",
        json={
            "content_json": {
                "reflection": {"summary": "S", "closing": "C"},
            }
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["content_json"]["reflection"]["summary"] == "S"
    # Existing flashcards must still be there (partial merge).
    assert body["content_json"]["flashcards"] == [{"term": "T", "def": "D"}]
