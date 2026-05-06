"""
Taskboard extra-fields tests — status toggle, task_type, subtask counts,
attachment_count, cover_url, and per-user accent color.
"""
import pytest


@pytest.fixture(autouse=True)
def clean_taskboard(client):
    """Archive all existing taskboard rows before each test."""
    users = client.get("/api/taskboard/users").json()
    for u in users:
        client.delete(f"/api/taskboard/users/{u['id']}")
    tasks = client.get("/api/taskboard/tasks").json()
    for t in tasks:
        client.delete(f"/api/taskboard/tasks/{t['id']}")


# ── status toggle ──────────────────────────────────────────────────────────

def test_task_defaults_to_open_status(client):
    r = client.post("/api/taskboard/tasks", json={"title": "fresh"})
    assert r.status_code == 200
    assert r.json()["status"] == "open"


def test_patch_task_status_to_done(client):
    t = client.post("/api/taskboard/tasks", json={"title": "do me"}).json()
    r = client.patch(f"/api/taskboard/tasks/{t['id']}", json={"status": "done"})
    assert r.status_code == 200
    assert r.json()["status"] == "done"


def test_patch_task_status_back_to_open(client):
    t = client.post("/api/taskboard/tasks", json={"title": "toggle"}).json()
    client.patch(f"/api/taskboard/tasks/{t['id']}", json={"status": "done"})
    r = client.patch(f"/api/taskboard/tasks/{t['id']}", json={"status": "open"})
    assert r.status_code == 200
    assert r.json()["status"] == "open"


def test_invalid_status_value_rejected(client):
    t = client.post("/api/taskboard/tasks", json={"title": "x"}).json()
    r = client.patch(f"/api/taskboard/tasks/{t['id']}", json={"status": "invalid"})
    assert r.status_code == 422


# ── task_type ──────────────────────────────────────────────────────────────

def test_task_type_defaults_to_general(client):
    r = client.post("/api/taskboard/tasks", json={"title": "x"})
    assert r.status_code == 200
    assert r.json()["task_type"] == "general"


def test_create_task_with_explicit_type(client):
    r = client.post(
        "/api/taskboard/tasks",
        json={"title": "x", "task_type": "development"},
    )
    assert r.status_code == 200
    assert r.json()["task_type"] == "development"


def test_create_task_rejects_unknown_type(client):
    r = client.post(
        "/api/taskboard/tasks",
        json={"title": "x", "task_type": "made-up"},
    )
    assert r.status_code == 422


def test_patch_task_type(client):
    t = client.post("/api/taskboard/tasks", json={"title": "x"}).json()
    r = client.patch(f"/api/taskboard/tasks/{t['id']}", json={"task_type": "design"})
    assert r.status_code == 200
    assert r.json()["task_type"] == "design"


# ── subtask + attachment counts ────────────────────────────────────────────

def test_subtask_and_attachment_defaults(client):
    body = client.post("/api/taskboard/tasks", json={"title": "x"}).json()
    assert body["subtask_total"] == 0
    assert body["subtask_done"] == 0
    assert body["attachment_count"] == 0


def test_create_with_meta_counts(client):
    r = client.post(
        "/api/taskboard/tasks",
        json={
            "title": "x",
            "subtask_total": 5,
            "subtask_done": 2,
            "attachment_count": 3,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["subtask_total"] == 5
    assert body["subtask_done"] == 2
    assert body["attachment_count"] == 3


def test_patch_subtask_counts(client):
    t = client.post("/api/taskboard/tasks", json={"title": "x"}).json()
    r = client.patch(
        f"/api/taskboard/tasks/{t['id']}",
        json={"subtask_total": 4, "subtask_done": 4},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["subtask_total"] == 4
    assert body["subtask_done"] == 4


def test_negative_counts_rejected(client):
    r = client.post(
        "/api/taskboard/tasks",
        json={"title": "x", "subtask_total": -1},
    )
    assert r.status_code == 422


# ── cover_url ──────────────────────────────────────────────────────────────

def test_cover_url_round_trips(client):
    url = "https://example.com/cover.png"
    r = client.post("/api/taskboard/tasks", json={"title": "x", "cover_url": url})
    assert r.status_code == 200
    assert r.json()["cover_url"] == url


def test_cover_url_can_be_cleared(client):
    t = client.post(
        "/api/taskboard/tasks",
        json={"title": "x", "cover_url": "https://example.com/c.png"},
    ).json()
    r = client.patch(f"/api/taskboard/tasks/{t['id']}", json={"cover_url": None})
    assert r.status_code == 200
    assert r.json()["cover_url"] is None


# ── direct assignment on create ────────────────────────────────────────────

def test_create_task_with_direct_assignee(client):
    user = client.post("/api/taskboard/users", json={"name": "Karim"}).json()
    r = client.post(
        "/api/taskboard/tasks",
        json={"title": "for karim", "assignee_id": user["id"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["assignee_id"] == user["id"]
    assert body["position"] == 0


# ── user color ─────────────────────────────────────────────────────────────

def test_user_color_persists(client):
    r = client.post("/api/taskboard/users", json={"name": "Karim", "color": "#22c55e"})
    assert r.status_code == 200
    assert r.json()["color"] == "#22c55e"


def test_user_color_optional(client):
    r = client.post("/api/taskboard/users", json={"name": "Karim"})
    assert r.status_code == 200
    assert r.json()["color"] is None


def test_patch_user_color(client):
    user = client.post("/api/taskboard/users", json={"name": "Karim"}).json()
    r = client.patch(f"/api/taskboard/users/{user['id']}", json={"color": "#a855f7"})
    assert r.status_code == 200
    assert r.json()["color"] == "#a855f7"


def test_invalid_color_rejected(client):
    r = client.post("/api/taskboard/users", json={"name": "Karim", "color": "red"})
    assert r.status_code == 422
