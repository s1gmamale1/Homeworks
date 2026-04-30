import asyncio
import copy
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts import migrate_content_json as mig
from server import db


BASE_CONTENT = {
    "flashcards": [{"term": "force", "def": "push or pull"}],
    "boss_questions": [
        {"q": "What is force?", "ans": ["push or pull"]},
        {"q": "What is mass?", "ans": ["matter"], "dmg": 7},
    ],
}


def run(coro):
    return asyncio.run(coro)


async def _seed(tmp_path: Path, rows: list[dict] | None = None) -> list[dict]:
    db_path = tmp_path / "test_nets.db"
    with patch("server.db.get_db_path", return_value=db_path):
        await db.init_db()
        created = []
        for index, content in enumerate(rows or [BASE_CONTENT]):
            created.append(
                await db.create_homework(
                    {
                        "title": f"HW {index}",
                        "subject": "physics",
                        "grade": 9,
                        "mode": "easy",
                        "family": "aniq-fanlar",
                        "content_json": copy.deepcopy(content),
                    }
                )
            )
    return created


def _args(transform, **overrides):
    values = {
        "transform": transform,
        "apply": False,
        "limit": None,
        "ids": None,
        "report": None,
        "db": None,
        "verbose": False,
    }
    values.update(overrides)
    return type("Args", (), values)()


def test_noop_transform_skips_unchanged_test_db(tmp_path):
    rows = run(_seed(tmp_path, [BASE_CONTENT, {"flashcards": []}]))

    with patch("server.db.get_db_path", return_value=tmp_path / "test_nets.db"):
        report = run(mig.run_migration(_args("noop")))

    assert report["summary"]["total"] == len(rows)
    assert report["summary"]["transformed"] == 0
    assert report["summary"]["skipped_unchanged"] == len(rows)


def test_add_default_dmg_to_boss_transforms_missing_dmg_only(tmp_path):
    run(_seed(tmp_path, [BASE_CONTENT, {"boss_questions": [{"q": "ok", "dmg": 1}]}]))

    with patch("server.db.get_db_path", return_value=tmp_path / "test_nets.db"):
        report = run(mig.run_migration(_args("add_default_dmg_to_boss")))

    assert report["summary"]["transformed"] == 1
    assert report["summary"]["skipped_unchanged"] == 1
    transformed = [row for row in report["rows"] if row["status"] == "transformed"]
    assert transformed[0]["diff_keys"] == ["boss_questions"]


def test_invalid_transform_flags_validation_and_continues(tmp_path):
    run(_seed(tmp_path, [BASE_CONTENT, {"flashcards": []}]))

    @mig.register_transform("test_invalid_boss_questions")
    def invalid(content, row):
        if row["title"] == "HW 0":
            content["boss_questions"] = "not a list"
        return content

    with patch("server.db.get_db_path", return_value=tmp_path / "test_nets.db"):
        report = run(mig.run_migration(_args("test_invalid_boss_questions")))

    assert report["summary"]["skipped_validation_failure"] == 1
    assert report["summary"]["skipped_unchanged"] == 1


def test_raising_transform_flags_error_and_continues(tmp_path):
    run(_seed(tmp_path, [BASE_CONTENT, {"flashcards": []}]))

    @mig.register_transform("test_raise_once")
    def raise_once(content, row):
        if row["title"] == "HW 0":
            raise RuntimeError("boom")
        return None

    with patch("server.db.get_db_path", return_value=tmp_path / "test_nets.db"):
        report = run(mig.run_migration(_args("test_raise_once")))

    assert report["summary"]["skipped_transform_error"] == 1
    assert report["summary"]["skipped_unchanged"] == 1


def test_dry_run_never_writes(tmp_path):
    rows = run(_seed(tmp_path, [BASE_CONTENT]))
    hw_id = rows[0]["id"]

    with patch("server.db.get_db_path", return_value=tmp_path / "test_nets.db"):
        before = run(db.get_homework(hw_id))["content_json"]
        report = run(mig.run_migration(_args("add_default_dmg_to_boss")))
        after = run(db.get_homework(hw_id))["content_json"]

    assert report["summary"]["transformed"] == 1
    assert before == after


def test_ids_filter_scopes_processing(tmp_path):
    rows = run(_seed(tmp_path, [BASE_CONTENT, BASE_CONTENT]))
    target_id = rows[0]["id"]

    with patch("server.db.get_db_path", return_value=tmp_path / "test_nets.db"):
        report = run(mig.run_migration(_args("add_default_dmg_to_boss", ids=target_id)))

    assert report["summary"]["total"] == 1
    assert report["rows"][0]["hw_id"] == target_id
