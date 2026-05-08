import asyncio
from pathlib import Path

from server import db as db_mod


ROOT = Path(__file__).resolve().parents[1]


def _run(coro):
    return asyncio.run(coro)


def test_migration_status_and_trigger_persist_normalized_content(client):
    created = _run(
        db_mod.create_homework(
            {
                "title": "Legacy migration smoke",
                "subject": "english",
                "grade": 8,
                "mode": "hard",
                "family": "til-fanlar",
                "status": "draft",
                "content_json": {
                    "quotes": ["Legacy quote"],
                    "reading": {"text": "Legacy passage", "checkpoints": [{"q": "Checkpoint?"}]},
                    "boss": [{"q": "Legacy boss?", "ans": ["yes"]}],
                    "flashcards": [{"term": "Old", "def": "Definition"}],
                },
            }
        )
    )
    hw_id = created["id"]

    status = client.get(f"/api/homeworks/{hw_id}/migration-status")
    assert status.status_code == 200, status.text
    body = status.json()
    assert body["needs_migration"] is True
    assert "gate_quote" in body["added_keys"]
    assert "reading" in body["changed_keys"]

    read = client.get(f"/api/homeworks/{hw_id}")
    assert read.status_code == 200, read.text
    assert read.json()["content_json"]["reading"]["passage"] == "Legacy passage"

    still_raw = client.get(f"/api/homeworks/{hw_id}/migration-status")
    assert still_raw.json()["needs_migration"] is True

    migrated = client.post(f"/api/homeworks/{hw_id}/migrate-content")
    assert migrated.status_code == 200, migrated.text
    payload = migrated.json()
    assert payload["migrated"] is True
    content = payload["homework"]["content_json"]
    assert content["gate_quote"]["mode"] == "custom"
    assert content["reading"]["passage"] == "Legacy passage"
    assert content["boss_questions"][0]["id"] == "bq_0"
    assert content["flashcards"][0]["definition"] == "Definition"

    final_status = client.get(f"/api/homeworks/{hw_id}/migration-status")
    assert final_status.status_code == 200
    assert final_status.json()["needs_migration"] is False


def test_builder_exposes_manual_migration_control():
    builder_html = (ROOT / "frontend" / "builder.html").read_text(encoding="utf-8")
    api_js = (ROOT / "frontend" / "js" / "api.js").read_text(encoding="utf-8")
    builder_js = (ROOT / "frontend" / "js" / "builder.js").read_text(encoding="utf-8")

    assert 'id="migrate-content-btn"' in builder_html
    assert "getHomeworkMigrationStatus" in api_js
    assert "migrateHomeworkContent" in api_js
    assert "checkMigrationStatus();" in builder_js
    assert "Data migrated" in builder_js
