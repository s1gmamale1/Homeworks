"""
Taskboard users API tests.
"""
import pytest


@pytest.fixture(autouse=True)
def clean_taskboard_users(client):
    """Archive all existing taskboard users before each test to ensure isolation."""
    resp = client.get("/api/taskboard/users")
    for u in resp.json():
        client.delete(f"/api/taskboard/users/{u['id']}")
    # Also archive any stray tasks so they don't interfere
    tasks = client.get("/api/taskboard/tasks").json()
    for t in tasks:
        client.delete(f"/api/taskboard/tasks/{t['id']}")


def test_list_empty_returns_array(client):
    """GET /api/taskboard/users returns [] when no users exist."""
    resp = client.get("/api/taskboard/users")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_user_appends_to_end_position(client):
    """POST creates a user with the next available position."""
    resp = client.post("/api/taskboard/users", json={"name": "Karim"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Karim"
    assert body["position"] == 0


def test_create_two_users_preserves_order(client):
    """Creating two users keeps insertion order in the list."""
    r1 = client.post("/api/taskboard/users", json={"name": "Karim"})
    assert r1.status_code == 200
    r2 = client.post("/api/taskboard/users", json={"name": "Aiden"})
    assert r2.status_code == 200

    resp = client.get("/api/taskboard/users")
    assert resp.status_code == 200
    users = resp.json()
    assert [u["name"] for u in users] == ["Karim", "Aiden"]
    assert [u["position"] for u in users] == [0, 1]


def test_rename_user_via_patch(client):
    """PATCH with name renames the user."""
    create = client.post("/api/taskboard/users", json={"name": "Karim"})
    assert create.status_code == 200
    user_id = create.json()["id"]

    patch = client.patch(f"/api/taskboard/users/{user_id}", json={"name": "Karim Updated"})
    assert patch.status_code == 200
    body = patch.json()
    assert body["name"] == "Karim Updated"
    assert body["position"] == 0


def test_reorder_user_repacks_positions(client):
    """Moving a user to position 0 repacks all positions to 0,1,2."""
    for name in ("Alpha", "Beta", "Gamma"):
        r = client.post("/api/taskboard/users", json={"name": name})
        assert r.status_code == 200

    users = client.get("/api/taskboard/users").json()
    beta_id = users[1]["id"]

    patch = client.patch(f"/api/taskboard/users/{beta_id}", json={"position": 0})
    assert patch.status_code == 200

    users = client.get("/api/taskboard/users").json()
    assert [u["name"] for u in users] == ["Beta", "Alpha", "Gamma"]
    assert [u["position"] for u in users] == [0, 1, 2]


def test_archive_user_unassigns_their_tasks_to_issues(client):
    """Archiving a user sets their tasks' assignee_id to null."""
    user_resp = client.post("/api/taskboard/users", json={"name": "Karim"})
    assert user_resp.status_code == 200
    user_id = user_resp.json()["id"]

    task_resp = client.post("/api/taskboard/tasks", json={"title": "Fix bug"})
    assert task_resp.status_code == 200
    task_id = task_resp.json()["id"]

    # Assign task to user
    patch = client.patch(f"/api/taskboard/tasks/{task_id}", json={"assignee_id": user_id})
    assert patch.status_code == 200
    assert patch.json()["assignee_id"] == user_id

    # Archive user
    archive = client.delete(f"/api/taskboard/users/{user_id}")
    assert archive.status_code == 200

    # Task should be back in Issues
    task = client.get(f"/api/taskboard/tasks?assignee_id=null").json()
    assert any(t["id"] == task_id for t in task)


def test_archived_user_hidden_from_list(client):
    """Archived users do not appear in GET /users."""
    create = client.post("/api/taskboard/users", json={"name": "Karim"})
    assert create.status_code == 200
    user_id = create.json()["id"]

    archive = client.delete(f"/api/taskboard/users/{user_id}")
    assert archive.status_code == 200

    resp = client.get("/api/taskboard/users")
    assert resp.status_code == 200
    assert resp.json() == []
