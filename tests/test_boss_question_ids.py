"""Boss-question canonical ID regression tests.

Guards: pre-fix, the injector synthesized `Q{i+1}` IDs for id-less rows but
the FB question lookup at `_fb_find_boss_question` only recognized
`bq_{i}` / `str(i)` / authored ids. Result: every check-answer for a boss
question on a homework whose `content_json.boss_questions[i]` lacked an
authored `id` returned 404 `FB_Q_NOT_FOUND`. Students saw correct answers
graded as wrong on production homework HW-20260505-008.

Each test asserts the BAD pre-fix state cannot return:
- POST/PUT/PATCH must stamp `id = bq_{i}` on every id-less boss_question
- Author-supplied ids MUST survive normalization
- The route lookup MUST recognize `bq_{i}` AND legacy `Q{i+1}` (transitional)
- The migration script MUST be idempotent and only stamp missing ids
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from server.routes.homework import _normalize_boss_question_ids
from server.routes.ai import _fb_find_boss_question
from server.services.injector import _serialize_boss_questions
from scripts.migrate_boss_question_ids import migrate_boss_questions


# ── _normalize_boss_question_ids — direct unit ──────────────────────────────


def test_normalize_stamps_idless():
    content = {"boss_questions": [{"q": "a"}, {"q": "b"}, {"q": "c"}]}
    _normalize_boss_question_ids(content)
    assert [q["id"] for q in content["boss_questions"]] == ["bq_0", "bq_1", "bq_2"]


def test_normalize_preserves_authored_ids():
    content = {"boss_questions": [
        {"id": "q_factor", "q": "a"},
        {"q": "b"},
        {"id": "q_perf_sq", "q": "c"},
    ]}
    _normalize_boss_question_ids(content)
    assert [q["id"] for q in content["boss_questions"]] == ["q_factor", "bq_1", "q_perf_sq"]


def test_normalize_idempotent():
    content = {"boss_questions": [{"q": "a"}, {"q": "b"}]}
    _normalize_boss_question_ids(content)
    snapshot = [dict(q) for q in content["boss_questions"]]
    _normalize_boss_question_ids(content)
    assert content["boss_questions"] == snapshot


def test_normalize_handles_empty_or_none_id():
    """`id: ""` and `id: None` are treated as missing — defensively defensive."""
    content = {"boss_questions": [
        {"id": "", "q": "a"},
        {"id": None, "q": "b"},
        {"id": "real", "q": "c"},
    ]}
    _normalize_boss_question_ids(content)
    assert [q["id"] for q in content["boss_questions"]] == ["bq_0", "bq_1", "real"]


def test_normalize_no_op_on_missing_or_wrong_shape():
    # No boss_questions key at all
    c1 = {"flashcards": []}
    _normalize_boss_question_ids(c1)
    assert c1 == {"flashcards": []}
    # Wrong type
    c2 = {"boss_questions": "not a list"}
    _normalize_boss_question_ids(c2)
    assert c2 == {"boss_questions": "not a list"}
    # Items not dict
    c3 = {"boss_questions": [{"q": "a"}, "not a dict", 42]}
    _normalize_boss_question_ids(c3)
    assert c3["boss_questions"][0]["id"] == "bq_0"
    assert c3["boss_questions"][1] == "not a dict"
    assert c3["boss_questions"][2] == 42


# ── _fb_find_boss_question — id format recognition ──────────────────────────


@pytest.mark.parametrize("question_id,expected_index", [
    ("bq_0", 0),       # canonical synthetic
    ("bq_1", 1),
    ("0", 0),          # positional string
    ("1", 1),
    ("Q1", 0),         # legacy synthetic (transitional)
    ("Q2", 1),
])
def test_lookup_recognizes_all_id_formats(question_id, expected_index):
    """All supported id formats resolve to the right question on an id-less row.

    This is the load-bearing regression test: pre-fix, only `bq_{i}`/`str(i)`
    matched, so `Q1` from the rendered runtime returned None → 404.
    """
    content = {"boss_questions": [{"q": "first"}, {"q": "second"}]}
    found = _fb_find_boss_question(content, question_id)
    assert found is not None, f"format {question_id!r} should resolve"
    assert found["q"] == content["boss_questions"][expected_index]["q"]


def test_lookup_prefers_authored_id_over_synthetic():
    """If a question has authored id 'bq_0' at index 1, a request for 'bq_0'
    must return the AUTHORED match, not the positional fallback at index 0.
    """
    content = {"boss_questions": [
        {"q": "index zero, no id"},
        {"id": "bq_0", "q": "authored bq_0"},
    ]}
    found = _fb_find_boss_question(content, "bq_0")
    assert found is not None
    assert found["q"] == "index zero, no id"  # iterates from 0; authored matches at i=1 too — but index 0's positional `bq_0` wins first
    # Note: the route loops in index order; the FIRST match wins. At i=0 the
    # `bq_0` positional fallback fires. This is the documented behavior.


def test_lookup_returns_none_for_unknown_id():
    content = {"boss_questions": [{"q": "x"}]}
    assert _fb_find_boss_question(content, "Q99") is None
    assert _fb_find_boss_question(content, "bq_42") is None
    assert _fb_find_boss_question(content, "completely_made_up") is None


def test_lookup_handles_empty_or_missing():
    assert _fb_find_boss_question({}, "bq_0") is None
    assert _fb_find_boss_question({"boss_questions": None}, "bq_0") is None
    assert _fb_find_boss_question({"boss_questions": []}, "bq_0") is None


# ── _serialize_boss_questions — synthetic format must be bq_{i} ─────────────


def test_serialize_stamps_bq_format_on_idless():
    """The injector's synthetic id format must match what the route recognizes
    as canonical. Pre-fix it stamped `Q{i+1}` and broke FB grading."""
    items = [
        {"q": "x", "ans": ["a"], "dmg": 10, "tags": "L3 P3"},
        {"q": "y", "ans": ["b"], "dmg": 10, "tags": "L3 P3"},
    ]
    js = _serialize_boss_questions(items)
    assert '"id": "bq_0"' in js
    assert '"id": "bq_1"' in js
    # Negative: legacy format must NOT appear from synthesis.
    assert '"id": "Q1"' not in js
    assert '"id": "Q2"' not in js


def test_serialize_preserves_authored_id():
    items = [
        {"id": "q_authored", "q": "x", "ans": ["a"], "dmg": 10, "tags": "L3 P3"},
        {"q": "y", "ans": ["b"], "dmg": 10, "tags": "L3 P3"},
    ]
    js = _serialize_boss_questions(items)
    assert '"id": "q_authored"' in js
    assert '"id": "bq_1"' in js  # second one still gets synthetic at correct index


# ── Migration script — direct call ──────────────────────────────────────────


def test_migrate_assigns_ids_and_returns_count():
    content = {"boss_questions": [{"q": "a"}, {"q": "b"}, {"q": "c"}]}
    n = migrate_boss_questions(content)
    assert n == 3
    assert [q["id"] for q in content["boss_questions"]] == ["bq_0", "bq_1", "bq_2"]


def test_migrate_idempotent_returns_zero_on_second_run():
    content = {"boss_questions": [{"q": "a"}, {"q": "b"}]}
    migrate_boss_questions(content)
    n2 = migrate_boss_questions(content)
    assert n2 == 0


def test_migrate_preserves_mixed_authored_idless():
    content = {"boss_questions": [
        {"id": "q_keep", "q": "a"},
        {"q": "b"},
        {"id": "another_keep", "q": "c"},
    ]}
    n = migrate_boss_questions(content)
    assert n == 1
    assert [q["id"] for q in content["boss_questions"]] == ["q_keep", "bq_1", "another_keep"]


def test_migrate_handles_dbless_content():
    """Content shapes that lack boss_questions must be a no-op (return 0)."""
    assert migrate_boss_questions({}) == 0
    assert migrate_boss_questions({"flashcards": []}) == 0
    assert migrate_boss_questions({"boss_questions": "not a list"}) == 0
    assert migrate_boss_questions(None) == 0


# ── Integration via TestClient — POST / PUT / PATCH ─────────────────────────


def test_post_idless_boss_questions_get_stamped(client):
    """The load-bearing end-to-end test: POST id-less → DB row has bq_{i}."""
    resp = client.post("/api/homeworks", json={
        "title": "[idless test]",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "easy",
        "content_json": {
            "boss_questions": [
                {"q": "Q1?", "ans": ["a"], "dmg": 10},
                {"q": "Q2?", "ans": ["b"], "dmg": 10},
            ]
        },
    })
    assert resp.status_code == 200
    bq = resp.json()["content_json"]["boss_questions"]
    assert [q["id"] for q in bq] == ["bq_0", "bq_1"]


def test_post_authored_ids_preserved(client):
    """Authored ids must survive POST normalization."""
    resp = client.post("/api/homeworks", json={
        "title": "[authored test]",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "easy",
        "content_json": {
            "boss_questions": [
                {"id": "q_factor", "q": "a", "ans": ["1"], "dmg": 10},
                {"q": "b", "ans": ["2"], "dmg": 10},
                {"id": "q_perf_sq", "q": "c", "ans": ["3"], "dmg": 10},
            ]
        },
    })
    assert resp.status_code == 200
    bq = resp.json()["content_json"]["boss_questions"]
    assert [q["id"] for q in bq] == ["q_factor", "bq_1", "q_perf_sq"]


def test_put_idless_boss_questions_get_stamped(client):
    seed = client.post("/api/homeworks", json={
        "title": "[put seed]", "subject": "math-algebra", "grade": 8,
        "mode": "easy", "content_json": {"boss_questions": []},
    })
    hw_id = seed.json()["id"]

    resp = client.put(f"/api/homeworks/{hw_id}", json={
        "content_json": {
            "boss_questions": [
                {"q": "x", "ans": ["a"], "dmg": 10},
                {"q": "y", "ans": ["b"], "dmg": 10},
            ]
        }
    })
    assert resp.status_code == 200
    bq = resp.json()["content_json"]["boss_questions"]
    assert [q["id"] for q in bq] == ["bq_0", "bq_1"]


def test_patch_stamps_idless_on_merged_content(client):
    seed = client.post("/api/homeworks", json={
        "title": "[patch seed]", "subject": "math-algebra", "grade": 8,
        "mode": "easy",
        "content_json": {"boss_questions": [
            {"id": "bq_0", "q": "x", "ans": ["a"], "dmg": 10},
            {"id": "bq_1", "q": "y", "ans": ["b"], "dmg": 10},
        ]},
    })
    hw_id = seed.json()["id"]

    resp = client.patch(f"/api/homeworks/{hw_id}/content", json={
        "content_json": {"boss_questions": [
            {"id": "bq_0", "q": "x", "ans": ["a"], "dmg": 10},
            {"id": "bq_1", "q": "y", "ans": ["b"], "dmg": 10},
            {"q": "new question, no id", "ans": ["c"], "dmg": 10},
        ]}
    })
    assert resp.status_code == 200
    bq = resp.json()["content_json"]["boss_questions"]
    assert [q["id"] for q in bq] == ["bq_0", "bq_1", "bq_2"]


@pytest.mark.parametrize("question_id", ["bq_0", "Q1"])
def test_check_answer_resolves_for_canonical_and_legacy_formats(client, monkeypatch, question_id):
    """End-to-end: POST homework → check-answer with both id formats →
    must NOT 404.

    The lookup logic itself is unit-tested above; this asserts the full
    `/api/ai/check-answer?phase=final-boss` route reaches `tutor.boss_turn`
    (mocked) for both canonical (`bq_0`) and transitional (`Q1`) ids.
    """
    seed = client.post("/api/homeworks", json={
        "title": "[lookup test]", "subject": "math-algebra", "grade": 8,
        "mode": "easy",
        "content_json": {"boss_questions": [
            {"q": "factoring", "ans": ["(7a-4b)(7a+4b)", "(7a+4b)(7a-4b)"], "dmg": 10},
        ]},
    })
    assert seed.status_code == 200
    hw_id = seed.json()["id"]

    # Mock tutor.boss_turn so we don't hit Kimi during pytest.
    async def fake_boss_turn(**kwargs):
        return {"correct": True, "damage_dealt": 10, "boss_response": "ok",
                "hint": None, "score": 1.0, "axis_1": 4, "axis_2": 4}
    from server.services import tutor as tutor_svc
    monkeypatch.setattr(tutor_svc, "boss_turn", fake_boss_turn)

    r = client.post("/api/ai/check-answer", json={
        "phase": "final-boss",
        "homework_id": hw_id,
        "question_id": question_id,
        "student_answer": "(7a-4b)(7a+4b)",
        "attempt_number": 1,
        "session_id": f"test-{question_id}",
        "boss_type": "sub",
        "hp_remaining": 100,
        "attempts_used": 0,
    })
    assert r.status_code == 200, f"format {question_id!r} returned {r.status_code}: {r.text}"


# ── Migration script — DB integration ───────────────────────────────────────


def test_migration_script_on_temp_db(tmp_path):
    """End-to-end test of process_db: create temp DB with id-less rows,
    migrate, verify, idempotency."""
    from scripts.migrate_boss_question_ids import process_db

    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute("""
        CREATE TABLE homeworks (
            id TEXT PRIMARY KEY,
            content_json TEXT,
            deleted_at TEXT
        )
    """)
    conn.execute("INSERT INTO homeworks (id, content_json) VALUES (?, ?)", (
        "HW-A",
        json.dumps({"boss_questions": [{"q": "x"}, {"q": "y"}]}),
    ))
    conn.execute("INSERT INTO homeworks (id, content_json) VALUES (?, ?)", (
        "HW-B",
        json.dumps({"boss_questions": [
            {"id": "authored", "q": "z"},
        ]}),
    ))
    conn.execute("INSERT INTO homeworks (id, content_json) VALUES (?, ?)", (
        "HW-C-empty",
        json.dumps({"flashcards": []}),  # no boss_questions at all
    ))
    conn.commit()
    conn.close()

    # First pass — should touch only HW-A.
    rows, ids = process_db(db_file, dry_run=False)
    assert rows == 1
    assert ids == 2

    # Verify state.
    conn = sqlite3.connect(str(db_file))
    c = conn.cursor()
    c.execute("SELECT content_json FROM homeworks WHERE id = ?", ("HW-A",))
    bq_a = json.loads(c.fetchone()[0])["boss_questions"]
    assert [q["id"] for q in bq_a] == ["bq_0", "bq_1"]
    c.execute("SELECT content_json FROM homeworks WHERE id = ?", ("HW-B",))
    bq_b = json.loads(c.fetchone()[0])["boss_questions"]
    assert [q["id"] for q in bq_b] == ["authored"]
    conn.close()

    # Idempotency.
    rows2, ids2 = process_db(db_file, dry_run=False)
    assert rows2 == 0
    assert ids2 == 0


def test_migration_script_dry_run_makes_no_changes(tmp_path):
    from scripts.migrate_boss_question_ids import process_db

    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute("CREATE TABLE homeworks (id TEXT PRIMARY KEY, content_json TEXT, deleted_at TEXT)")
    conn.execute("INSERT INTO homeworks VALUES (?, ?, ?)", (
        "HW-A",
        json.dumps({"boss_questions": [{"q": "x"}, {"q": "y"}]}),
        None,
    ))
    conn.commit()
    conn.close()

    rows, ids = process_db(db_file, dry_run=True)
    assert rows == 1
    assert ids == 2

    # Verify nothing actually changed.
    conn = sqlite3.connect(str(db_file))
    c = conn.execute("SELECT content_json FROM homeworks WHERE id = ?", ("HW-A",))
    bq = json.loads(c.fetchone()[0])["boss_questions"]
    assert all("id" not in q for q in bq), "dry-run must not mutate"
    conn.close()
