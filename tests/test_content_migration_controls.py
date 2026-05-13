import asyncio
import base64
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


def test_migration_preserves_generated_image_urls_and_extracts_structured_data_uri(client):
    tiny_png = base64.b64encode(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
        b"\x00\x00\x00\x1f\x15\xc4\x89"
    ).decode("ascii")
    data_uri = f"data:image/png;base64,{tiny_png}"
    old_lan_url = "http://192.168.1.87:8000/generated/good-authored-diagram.png"
    created = _run(
        db_mod.create_homework(
            {
                "title": "Legacy media migration",
                "subject": "math-algebra",
                "grade": 8,
                "mode": "hard",
                "family": "aniq-fanlar",
                "status": "draft",
                "content_json": {
                    "meta": {"title": "Legacy media migration"},
                    "panels": [
                        {
                            "pages": [
                                {
                                    "blocks": [
                                        {"type": "quote", "text": f'<img src="{old_lan_url}" alt="diagram">'},
                                        {"type": "image", "src": data_uri, "alt": "authored upload"},
                                    ]
                                }
                            ]
                        }
                    ],
                },
            }
        )
    )
    hw_id = created["id"]

    status = client.get(f"/api/homeworks/{hw_id}/migration-status")
    assert status.status_code == 200, status.text
    assert status.json()["needs_migration"] is True

    migrated = client.post(f"/api/homeworks/{hw_id}/migrate-content")
    assert migrated.status_code == 200, migrated.text
    content = migrated.json()["homework"]["content_json"]
    blocks = content["panels"][0]["pages"][0]["blocks"]
    lifted_img = blocks[0]
    extracted_img = blocks[1]

    assert lifted_img == {
        "type": "image",
        "src": "/generated/good-authored-diagram.png",
        "alt": "diagram",
    }
    assert extracted_img["type"] == "image"
    assert extracted_img["alt"] == "authored upload"
    assert extracted_img["src"].startswith(f"/generated/{hw_id}__media_")
    assert not extracted_img["src"].startswith("data:image")
    written = ROOT / "frontend" / extracted_img["src"].lstrip("/")
    try:
        assert written.exists()
    finally:
        written.unlink(missing_ok=True)


def test_migration_preserves_generic_svg_artwork_for_manual_cleanup(client):
    generic_svg = """
    <svg xmlns="http://www.w3.org/2000/svg" width="1200" height="720">
      <text>Homework diagram</text>
      <text>Formula diagram</text>
    </svg>
    """
    created = _run(
        db_mod.create_homework(
            {
                "title": "Generic SVG preservation",
                "subject": "math-algebra",
                "grade": 8,
                "mode": "hard",
                "family": "aniq-fanlar",
                "status": "draft",
                "content_json": {
                    "meta": {"title": "Generic SVG preservation"},
                    "panels": [
                        {
                            "pages": [
                                {
                                    "blocks": [
                                        {"type": "svg", "html": generic_svg},
                                    ]
                                }
                            ]
                        }
                    ],
                },
            }
        )
    )
    hw_id = created["id"]

    status = client.get(f"/api/homeworks/{hw_id}/migration-status")
    assert status.status_code == 200, status.text
    assert status.json()["media"]["generic_svgs_rewritten"] == 0

    migrated = client.post(f"/api/homeworks/{hw_id}/migrate-content")
    assert migrated.status_code == 200, migrated.text
    content_json = migrated.json()["homework"]["content_json"]
    html = content_json["panels"][0]["pages"][0]["blocks"][0]["html"]
    assert "Homework diagram" in html
    assert "Formula diagram" in html
