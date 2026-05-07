"""Regression tests for the content_json compatibility / normalization layer.

Pins the contract of ``server.services.content_json_compat.normalize_content_json_for_runtime``:

  * Idempotent — running twice yields the same dict as running once.
  * Additive — every key in the input survives unchanged on the output;
    new keys appear alongside the legacy ones.
  * Non-mutating — the caller's input dict is not mutated.
  * Tolerant — malformed / partial / non-dict inputs do not raise.

Each legacy drift case (L1..L9 in the module docstring) gets at least
one dedicated test so a future schema change that breaks the alias path
fails loudly instead of silently dropping a homework section.

Companion to the wiring tests at the bottom of this file, which verify
the normalizer is actually applied on the API GET / preview / shareable
URL routes (i.e., consumers see normalized content_json without callers
having to remember to call the helper themselves).
"""
from __future__ import annotations

import json
import os
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from server.app import app
from server.services.content_json_compat import (
    normalize_content_json_for_runtime,
    normalize_homework_row_for_runtime,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Tolerance — non-dict input never raises.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("garbage", [None, "", 0, 42, [], "hello", [1, 2, 3]])
def test_normalizer_tolerates_non_dict_input(garbage):
    """A row with a corrupted / missing content_json must not 500 the
    server — the normalizer always returns a dict.
    """
    result = normalize_content_json_for_runtime(garbage)
    assert isinstance(result, dict)
    assert result == {} if garbage in (None, "", 0, 42, []) else True


def test_normalizer_does_not_mutate_input():
    """The caller's source dict must remain pristine — FastAPI hands the
    DB row to the response model after the route returns, so any in-place
    mutation would propagate into the wire format.
    """
    src = {
        "quotes": ["Legacy quote"],
        "boss": [{"q": "Legacy boss?"}],
        "reading": {"text": "Legacy passage", "checkpoints": [{"q": "cp1"}]},
        "flashcards": [{"term": "T", "def": "D"}],
    }
    src_snapshot = deepcopy(src)
    _ = normalize_content_json_for_runtime(src)
    assert src == src_snapshot, (
        "normalize_content_json_for_runtime mutated its input; this "
        "leaks normalization side-effects into FastAPI response bodies "
        "and DB rows held in memory after the read."
    )


# ---------------------------------------------------------------------------
# Idempotency — running twice == running once.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "shape",
    [
        # Legacy quotes array
        {"quotes": ["Old quote"], "panels": []},
        # Bare boss key
        {"boss": [{"q": "Q1"}], "panels": []},
        # Reading with text only
        {"reading": {"text": "Old passage"}},
        # All gb_* missing
        {"flashcards": []},
        # Empty
        {},
        # Already modern
        {
            "gate_quote": {"mode": "auto"},
            "boss_questions": [{"id": "bq_0", "prompt": "Q", "q": "Q"}],
            "boss_meta": {"boss_type": "sub"},
            "reading": {"passage": "P", "text": "P"},
        },
    ],
)
def test_normalizer_is_idempotent(shape):
    once = normalize_content_json_for_runtime(shape)
    twice = normalize_content_json_for_runtime(once)
    assert once == twice, (
        "normalize_content_json_for_runtime is not idempotent — running "
        "twice produced a different dict than running once. The compat "
        "layer is called on every read; non-idempotent normalization "
        "would shift the wire format on each request."
    )


# ---------------------------------------------------------------------------
# L1 — quotes array → gate_quote envelope.
# ---------------------------------------------------------------------------


def test_l1_legacy_quotes_array_becomes_custom_envelope():
    """A legacy row with only ``quotes: ["..."]`` should expose a
    ``gate_quote`` envelope whose ``mode == "custom"`` and whose custom
    text is the legacy quote — otherwise the auto-generated default
    envelope shadows the author's intent and the legacy quote disappears
    from the rendered gate.
    """
    src = {"quotes": ["Eski iqtibos matni"]}
    out = normalize_content_json_for_runtime(src)
    # Legacy key stays present.
    assert out["quotes"] == ["Eski iqtibos matni"]
    # New key appears.
    assert isinstance(out["gate_quote"], dict)
    assert out["gate_quote"]["mode"] == "custom"
    assert out["gate_quote"]["custom"]["text"] == "Eski iqtibos matni"


def test_l1_authored_envelope_wins():
    """When the author already shipped a ``gate_quote`` envelope, do not
    overwrite it with the legacy quotes array.
    """
    src = {
        "gate_quote": {"mode": "pinned", "pinned_id": "q_42"},
        "quotes": ["This should NOT win"],
    }
    out = normalize_content_json_for_runtime(src)
    assert out["gate_quote"]["mode"] == "pinned"
    assert out["gate_quote"]["pinned_id"] == "q_42"


def test_l1_empty_envelope_gets_auto_mode():
    """Older builder versions shipped ``{}`` placeholder envelopes —
    the normalizer must populate ``mode`` so downstream lookups succeed.
    """
    src = {"gate_quote": {}}
    out = normalize_content_json_for_runtime(src)
    assert out["gate_quote"]["mode"] == "auto"


def test_l1_no_quotes_at_all_defaults_to_auto():
    """No quotes authored anywhere → default ``mode: "auto"`` so the
    selector can fall back to the global library without raising on a
    missing envelope.
    """
    out = normalize_content_json_for_runtime({})
    assert out["gate_quote"] == {"mode": "auto"}


# ---------------------------------------------------------------------------
# L2 — reading.text → reading.passage.
# ---------------------------------------------------------------------------


def test_l2_reading_text_mirrored_to_passage():
    """The english-g11-b2 fixture (and other pre-passage rows) name the
    reading body ``text``. The injector reads ``passage``. Without
    mirroring, the rendered passage frame is empty.
    """
    src = {"reading": {"text": "Once upon a time, there was a sentence."}}
    out = normalize_content_json_for_runtime(src)
    # Modern key is now populated.
    assert out["reading"]["passage"] == "Once upon a time, there was a sentence."
    # Legacy key stays present.
    assert out["reading"]["text"] == "Once upon a time, there was a sentence."


def test_l2_reading_passage_takes_precedence_when_both_set():
    """When both ``text`` and ``passage`` are populated, ``passage`` wins
    (it is the modern canonical key).
    """
    src = {"reading": {"text": "Legacy", "passage": "Modern"}}
    out = normalize_content_json_for_runtime(src)
    assert out["reading"]["passage"] == "Modern"
    assert out["reading"]["text"] == "Legacy"


def test_l8_reading_checkpoint_q_mirrored_to_prompt():
    src = {"reading": {"checkpoints": [{"q": "What happened next?", "ans": ["A"]}]}}
    out = normalize_content_json_for_runtime(src)
    cp = out["reading"]["checkpoints"][0]
    assert cp["q"] == "What happened next?"   # legacy preserved
    assert cp["prompt"] == "What happened next?"  # modern surfaced
    assert cp["ans"] == ["A"]                  # other fields untouched


# ---------------------------------------------------------------------------
# L3 — bare ``boss`` array → ``boss_questions``.
# ---------------------------------------------------------------------------


def test_l3_bare_boss_array_lifted_to_boss_questions():
    """Some pre-v2 authoring used the bare ``boss`` array. The schema
    pins ``boss_questions``; downstream code reads ``boss_questions``.
    Without the lift, those questions are invisible to the runtime.
    """
    src = {"boss": [{"q": "Find x.", "ans": ["3"]}, {"q": "Then y?", "ans": ["7"]}]}
    out = normalize_content_json_for_runtime(src)
    assert out["boss"] == src["boss"]                  # legacy preserved
    assert isinstance(out["boss_questions"], list)
    assert len(out["boss_questions"]) == 2
    assert out["boss_questions"][0]["q"] == "Find x."
    assert out["boss_questions"][1]["q"] == "Then y?"


def test_l3_does_not_overwrite_existing_boss_questions():
    """If ``boss_questions`` is already present, the legacy ``boss``
    array does NOT replace it (modern takes precedence).
    """
    src = {
        "boss": [{"q": "Legacy"}],
        "boss_questions": [{"q": "Modern"}],
    }
    out = normalize_content_json_for_runtime(src)
    assert len(out["boss_questions"]) == 1
    assert out["boss_questions"][0]["q"] == "Modern"


# ---------------------------------------------------------------------------
# L4 — boss question id stamping (read-side mirror of write-boundary fix).
# ---------------------------------------------------------------------------


def test_l4_boss_questions_get_synthetic_ids_when_missing():
    """Old DB rows stored before id normalization need ids stamped on
    read so the boss-grading endpoint's question lookup succeeds.
    """
    src = {"boss_questions": [{"q": "Q1"}, {"q": "Q2", "id": "author_id"}, {"q": "Q3"}]}
    out = normalize_content_json_for_runtime(src)
    assert out["boss_questions"][0]["id"] == "bq_0"      # synthetic
    assert out["boss_questions"][1]["id"] == "author_id"  # author preserved
    assert out["boss_questions"][2]["id"] == "bq_2"      # synthetic


def test_l4_does_not_overwrite_author_supplied_id():
    src = {"boss_questions": [{"id": "custom-id", "q": "Q"}]}
    out = normalize_content_json_for_runtime(src)
    assert out["boss_questions"][0]["id"] == "custom-id"


# ---------------------------------------------------------------------------
# L5 — boss question ``q`` → ``prompt`` mirror.
# ---------------------------------------------------------------------------


def test_l5_boss_question_q_mirrored_to_prompt():
    """Both keys remain present; downstream prompt-builders read
    ``prompt`` first without alias-walk."""
    src = {"boss_questions": [{"q": "Solve for x."}]}
    out = normalize_content_json_for_runtime(src)
    assert out["boss_questions"][0]["q"] == "Solve for x."
    assert out["boss_questions"][0]["prompt"] == "Solve for x."


def test_l5_existing_prompt_not_clobbered():
    src = {"boss_questions": [{"q": "Legacy", "prompt": "Modern"}]}
    out = normalize_content_json_for_runtime(src)
    assert out["boss_questions"][0]["prompt"] == "Modern"
    assert out["boss_questions"][0]["q"] == "Legacy"


# ---------------------------------------------------------------------------
# L6 — boss_meta default block.
# ---------------------------------------------------------------------------


def test_l6_default_boss_meta_filled_when_missing():
    out = normalize_content_json_for_runtime({})
    assert out["boss_meta"] == {"boss_type": "sub"}


def test_l6_authored_boss_meta_preserved():
    src = {"boss_meta": {"boss_type": "mythical", "starting_hp_override": 200}}
    out = normalize_content_json_for_runtime(src)
    assert out["boss_meta"]["boss_type"] == "mythical"
    assert out["boss_meta"]["starting_hp_override"] == 200


# ---------------------------------------------------------------------------
# L7 — gb_* arrays default to [] when missing.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "key",
    [
        "gb_adaptive_quiz", "gb_why_chain", "gb_memory_match",
        "gb_puzzle_lock", "gb_mystery_box", "gb_ttt",
        "gb_sentence_fill", "gb_tile_match",
    ],
)
def test_l7_missing_gb_arrays_default_to_empty_list(key):
    out = normalize_content_json_for_runtime({})
    assert out[key] == [], (
        f"{key!r} must default to [] so iteration / len() are safe; "
        "the runtime registry skips empty gb_* arrays so this does not "
        "introduce phantom game-break panels."
    )


def test_l7_authored_gb_arrays_preserved():
    src = {"gb_adaptive_quiz": [{"q": "Q1"}, {"q": "Q2"}]}
    out = normalize_content_json_for_runtime(src)
    assert len(out["gb_adaptive_quiz"]) == 2


# ---------------------------------------------------------------------------
# L9 — flashcards ``def`` → ``definition`` mirror.
# ---------------------------------------------------------------------------


def test_l9_flashcard_def_mirrored_to_definition():
    src = {"flashcards": [{"term": "Mitosis", "def": "Cell division."}]}
    out = normalize_content_json_for_runtime(src)
    card = out["flashcards"][0]
    assert card["def"] == "Cell division."          # legacy preserved
    assert card["definition"] == "Cell division."   # modern surfaced


def test_l9_existing_definition_not_clobbered():
    src = {"flashcards": [{"term": "T", "def": "Legacy", "definition": "Modern"}]}
    out = normalize_content_json_for_runtime(src)
    assert out["flashcards"][0]["definition"] == "Modern"


# ---------------------------------------------------------------------------
# Additivity — no key in the input is removed.
# ---------------------------------------------------------------------------


def test_no_input_keys_are_removed():
    """A normalizer that drops keys from the source blob would silently
    corrupt stored homeworks. Every input top-level key must survive on
    the output (the normalizer is purely additive).
    """
    src = {
        "meta": {"title": "T"},
        "quotes": ["Q"],
        "panels": [{"title": "P"}],
        "flashcards": [{"term": "T", "def": "D"}],
        "memory_sprint": [{"prompt": "P", "options": ["A"], "correct": 0}],
        "real_life": {"badge": "B", "story": "S", "q1": {"prompt": "P", "ans": "A"}},
        "boss": [{"q": "Q1"}],
        "boss_questions": [{"q": "Q2"}],
        "boss_meta": {"boss_type": "big"},
        "gb_adaptive_quiz": [],
        "gb_unrecognized_future_key": [{"x": 1}],  # unknown keys must survive
        "reading": {"text": "T", "passage": "P"},
        "consolidation": {"mnemonic": "M"},
        "reflection": {"summary": "S"},
        "gate_quote": {"mode": "pinned", "pinned_id": "q_1"},
    }
    out = normalize_content_json_for_runtime(src)
    for key in src:
        assert key in out, f"normalize_content_json_for_runtime dropped key {key!r}"


# ---------------------------------------------------------------------------
# Real production fixtures load without crashing and pick up modern keys.
# ---------------------------------------------------------------------------


def _load_fixture(name: str) -> dict:
    path = os.path.join(_repo_root(), "fixtures", name)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.parametrize(
    "fixture",
    [
        "math-algebra-g8-hard.json",
        "physics-g9-easy.json",
        "biology-g7-easy.json",
        "english-g11-b2.json",   # has reading.text legacy field
        "history-g8.json",
        "kimyo-g9-hard.json",
    ],
)
def test_real_fixtures_normalize_without_crashing(fixture):
    src = _load_fixture(fixture)
    out = normalize_content_json_for_runtime(src)
    # Every fixture predates gate_quote — the envelope must be present after.
    assert isinstance(out.get("gate_quote"), dict)
    assert out["gate_quote"].get("mode") in ("auto", "custom", "pinned")
    # boss_meta default appears.
    assert isinstance(out.get("boss_meta"), dict)
    # gb_* arrays are non-None even if absent from the source.
    assert isinstance(out.get("gb_adaptive_quiz"), list)
    assert isinstance(out.get("gb_tile_match"), list)


def test_english_g11_legacy_reading_text_now_renders_passage():
    """English G11 fixture has ``reading.text`` (no ``passage``). After
    normalization the modern ``passage`` field MUST be populated so the
    injector renders a non-empty reading panel.
    """
    src = _load_fixture("english-g11-b2.json")
    out = normalize_content_json_for_runtime(src)
    rd = out["reading"]
    assert isinstance(rd, dict)
    assert rd.get("passage")  # non-empty
    assert rd["passage"] == src["reading"]["text"]


# ---------------------------------------------------------------------------
# Wiring tests — normalizer is applied on the API GET / preview / share routes.
# ---------------------------------------------------------------------------


def test_api_get_homework_returns_normalized_content_json(client):
    create = client.post("/api/homeworks", json={
        "title": "Compat smoke",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
    })
    assert create.status_code == 200, create.text
    hw_id = create.json()["id"]
    # PUT (full overwrite, NOT patch — patch deep-merges with the create
    # scaffold's ``gate_quote: {mode: "auto"}`` and would mask the
    # legacy-quotes lift behavior we want to verify here). The PUT body
    # is intentionally minimal + legacy-shaped: bare ``boss`` array, raw
    # ``quotes`` list, no ``boss_meta``, no ``gate_quote``.
    update = client.put(f"/api/homeworks/{hw_id}", json={
        "content_json": {
            "meta": {"title": "Compat smoke"},
            "panels": [],
            "flashcards": [],
            "memory_sprint": [],
            "quotes": ["Legacy quote"],
            "boss": [{"q": "Find x"}],
            "reading": {"text": "Legacy passage"},
        },
    })
    assert update.status_code == 200, update.text

    r = client.get(f"/api/homeworks/{hw_id}")
    assert r.status_code == 200
    cj = r.json()["content_json"]
    # Legacy keys preserved.
    assert cj["quotes"] == ["Legacy quote"]
    assert cj["boss"][0]["q"] == "Find x"
    assert cj["reading"]["text"] == "Legacy passage"
    # Modern aliases / defaults appear.
    assert cj["gate_quote"]["mode"] == "custom"
    assert cj["gate_quote"]["custom"]["text"] == "Legacy quote"
    assert cj["boss_questions"][0]["q"] == "Find x"
    assert cj["boss_questions"][0]["id"]  # stamped
    assert cj["boss_questions"][0]["prompt"] == "Find x"
    assert cj["boss_meta"] == {"boss_type": "sub"}
    assert cj["reading"]["passage"] == "Legacy passage"
    # gb_* arrays defaulted to empty.
    for key in ("gb_adaptive_quiz", "gb_why_chain", "gb_tile_match"):
        assert cj[key] == []


def test_render_homework_sees_normalized_content(client):
    """The /h/{id} shareable URL renders the same template as the
    builder preview. Both go through ``render_homework`` which now runs
    the normalizer first. We check that a row with a legacy
    ``reading.text`` field renders the passage in the HTML — the
    pre-normalizer behavior would leave the passage empty.
    """
    create = client.post("/api/homeworks", json={
        "title": "Legacy reading smoke",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
    })
    assert create.status_code == 200, create.text
    hw_id = create.json()["id"]
    update = client.put(f"/api/homeworks/{hw_id}", json={
        "content_json": {
            "meta": {"title": "Legacy reading smoke"},
            "panels": [], "flashcards": [], "boss_questions": [],
            "memory_sprint": [],
            "reading": {"text": "Marker-passage-text-12345"},
        },
    })
    assert update.status_code == 200, update.text

    r = client.get(f"/h/{hw_id}")
    assert r.status_code == 200
    # The injector serializes the reading object into a JS const named
    # READING — the passage value must appear in the rendered HTML.
    assert "Marker-passage-text-12345" in r.text, (
        "render_homework did not pick up the legacy reading.text field; "
        "either the normalizer is not wired in render_homework or the "
        "injector stopped reading the passage key."
    )


# ---------------------------------------------------------------------------
# Row helper.
# ---------------------------------------------------------------------------


def test_normalize_homework_row_for_runtime_keeps_other_columns():
    row = {
        "id": "HW-1",
        "title": "T",
        "subject": "math-algebra",
        "grade": 8,
        "content_json": {"quotes": ["Q"]},
        "deleted_at": None,
    }
    out = normalize_homework_row_for_runtime(row)
    # Other columns survive unchanged.
    assert out["id"] == "HW-1"
    assert out["title"] == "T"
    assert out["subject"] == "math-algebra"
    assert out["grade"] == 8
    assert out["deleted_at"] is None
    # content_json is normalized.
    assert out["content_json"]["gate_quote"]["mode"] == "custom"


def test_normalize_homework_row_handles_none_content_json():
    row = {"id": "HW-2", "title": "T", "content_json": None}
    out = normalize_homework_row_for_runtime(row)
    assert out["id"] == "HW-2"
    # None content_json is left as None — the row helper only normalizes
    # when there is something to normalize.
    assert out["content_json"] is None
