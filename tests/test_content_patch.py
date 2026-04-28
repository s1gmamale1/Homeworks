"""Regression tests for PATCH /api/homeworks/{id}/content.

PR #32 added partial content_json updates via _deep_merge_content. These tests
lock the intended semantics so future editor endpoints cannot accidentally
turn partial updates into destructive overwrites.
"""

from server.routes.homework import _deep_merge_content


def test_deep_merge_preserves_missing_keys():
    base = {
        "meta": {"title": "Old", "section": "Unit 1"},
        "flashcards": [{"term": "A"}],
        "gb_puzzle_lock": [{"content": "old"}],
    }

    merged = _deep_merge_content(base, {"meta": {"section": "Unit 2"}})

    assert merged["meta"] == {"title": "Old", "section": "Unit 2"}
    assert merged["flashcards"] == [{"term": "A"}]
    assert merged["gb_puzzle_lock"] == [{"content": "old"}]


def test_deep_merge_null_sets_null_not_delete():
    merged = _deep_merge_content(
        {"reflection": {"summary": "keep?"}, "meta": {"title": "T"}},
        {"reflection": None},
    )

    assert "reflection" in merged
    assert merged["reflection"] is None
    assert merged["meta"] == {"title": "T"}


def test_deep_merge_recurses_nested_dicts():
    base = {
        "meta": {"title": "Quadratics", "section": "1.1", "cefr_level": ""},
        "reading": {"title": "Read", "checkpoint": {"q": "old", "a": "yes"}},
    }

    merged = _deep_merge_content(
        base,
        {
            "meta": {"section": "1.2"},
            "reading": {"checkpoint": {"q": "new"}},
        },
    )

    assert merged["meta"] == {
        "title": "Quadratics",
        "section": "1.2",
        "cefr_level": "",
    }
    assert merged["reading"]["title"] == "Read"
    assert merged["reading"]["checkpoint"] == {"q": "new", "a": "yes"}


def test_deep_merge_non_dict_overwrites_dict():
    merged = _deep_merge_content(
        {"real_life": {"badge": "Old", "story": "Old story"}},
        {"real_life": "disabled"},
    )

    assert merged["real_life"] == "disabled"


def test_deep_merge_dict_overwrites_non_dict():
    merged = _deep_merge_content(
        {"real_life": "disabled"},
        {"real_life": {"badge": "New"}},
    )

    assert merged["real_life"] == {"badge": "New"}


def test_deep_merge_lists_replace_not_merge():
    merged = _deep_merge_content(
        {"flashcards": [{"term": "old"}, {"term": "stale"}]},
        {"flashcards": [{"term": "new"}]},
    )

    assert merged["flashcards"] == [{"term": "new"}]


def test_patch_content_nonexistent_homework_returns_stable_not_found(client):
    for _ in range(3):
        resp = client.patch(
            "/api/homeworks/HW-DOES-NOT-EXIST/content",
            json={"content_json": {"gb_puzzle_lock": []}},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == {"error": "Not found", "code": "NOT_FOUND"}


def test_patch_content_merges_without_resending_every_phase(client):
    create = client.post(
        "/api/homeworks",
        json={
            "title": "Patch merge smoke",
            "subject": "math-algebra",
            "grade": 8,
            "mode": "hard",
            "content_json": {
                "meta": {"title": "Patch merge smoke", "section": "old"},
                "flashcards": [{"term": "Diskriminant", "def": "D"}],
                "gb_memory_match": [["A", "B"]],
            },
        },
    )
    assert create.status_code == 200, create.text
    hw_id = create.json()["id"]

    patch = client.patch(
        f"/api/homeworks/{hw_id}/content",
        json={
            "content_json": {
                "meta": {"section": "new"},
                "gb_puzzle_lock": [
                    {"content": "Tile A", "q": "Question A", "a": "Answer A"}
                ],
            }
        },
    )
    assert patch.status_code == 200, patch.text
    content = patch.json()["content_json"]

    assert content["meta"]["title"] == "Patch merge smoke"
    assert content["meta"]["section"] == "new"
    assert content["flashcards"] == [{"term": "Diskriminant", "def": "D"}]
    assert content["gb_memory_match"] == [["A", "B"]]
    assert content["gb_puzzle_lock"] == [
        {"content": "Tile A", "q": "Question A", "a": "Answer A"}
    ]
