"""
Taskboard tasks API tests.
"""
import pytest


@pytest.fixture(autouse=True)
def clean_taskboard_tasks(client):
    """Archive all existing taskboard tasks and users before each test."""
    users = client.get("/api/taskboard/users").json()
    for u in users:
        client.delete(f"/api/taskboard/users/{u['id']}")
    tasks = client.get("/api/taskboard/tasks").json()
    for t in tasks:
        client.delete(f"/api/taskboard/tasks/{t['id']}")


def test_create_task_lands_on_issues_with_null_assignee(client):
    """POST creates a task in Issues (assignee_id=null)."""
    resp = client.post("/api/taskboard/tasks", json={"title": "New task"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "New task"
    assert body["assignee_id"] is None
    assert body["status"] == "open"


def test_create_task_appends_to_end_of_issues(client):
    """Creating two tasks in Issues gives them positions 0 and 1."""
    r1 = client.post("/api/taskboard/tasks", json={"title": "First"})
    assert r1.status_code == 200
    r2 = client.post("/api/taskboard/tasks", json={"title": "Second"})
    assert r2.status_code == 200

    assert r1.json()["position"] == 0
    assert r2.json()["position"] == 1


def test_list_tasks_filter_by_assignee_null(client):
    """GET /tasks?assignee_id=null returns unassigned tasks."""
    client.post("/api/taskboard/tasks", json={"title": "Unassigned"})
    resp = client.get("/api/taskboard/tasks?assignee_id=null")
    assert resp.status_code == 200
    tasks = resp.json()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Unassigned"


def test_list_tasks_filter_by_assignee_id(client):
    """GET /tasks?assignee_id=<id> returns tasks for that user."""
    user_resp = client.post("/api/taskboard/users", json={"name": "Karim"})
    assert user_resp.status_code == 200
    user_id = user_resp.json()["id"]

    client.post("/api/taskboard/tasks", json={"title": "Other"})
    task_resp = client.post("/api/taskboard/tasks", json={"title": "Mine"})
    assert task_resp.status_code == 200
    task_id = task_resp.json()["id"]

    # Assign task to user
    patch = client.patch(f"/api/taskboard/tasks/{task_id}", json={"assignee_id": user_id})
    assert patch.status_code == 200

    resp = client.get(f"/api/taskboard/tasks?assignee_id={user_id}")
    assert resp.status_code == 200
    tasks = resp.json()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Mine"


def test_patch_task_assign_moves_to_user_end(client):
    """PATCH assignee_id moves the task to the user's bucket end."""
    user_resp = client.post("/api/taskboard/users", json={"name": "Karim"})
    assert user_resp.status_code == 200
    user_id = user_resp.json()["id"]

    task_resp = client.post("/api/taskboard/tasks", json={"title": "Move me"})
    assert task_resp.status_code == 200
    task_id = task_resp.json()["id"]

    patch = client.patch(f"/api/taskboard/tasks/{task_id}", json={"assignee_id": user_id})
    assert patch.status_code == 200
    body = patch.json()
    assert body["assignee_id"] == user_id
    assert body["position"] == 0


def test_patch_task_assign_to_null_moves_to_issues(client):
    """PATCH assignee_id=null moves the task back to Issues."""
    user_resp = client.post("/api/taskboard/users", json={"name": "Karim"})
    assert user_resp.status_code == 200
    user_id = user_resp.json()["id"]

    task_resp = client.post("/api/taskboard/tasks", json={"title": "Return me"})
    assert task_resp.status_code == 200
    task_id = task_resp.json()["id"]

    # Assign to user first
    client.patch(f"/api/taskboard/tasks/{task_id}", json={"assignee_id": user_id})

    # Move back to Issues
    patch = client.patch(f"/api/taskboard/tasks/{task_id}", json={"assignee_id": None})
    assert patch.status_code == 200
    body = patch.json()
    assert body["assignee_id"] is None
    # Should be at end of Issues bucket
    issues = client.get("/api/taskboard/tasks?assignee_id=null").json()
    task = next(t for t in issues if t["id"] == task_id)
    assert task["position"] >= 0


def test_patch_task_reorder_within_bucket_repacks(client):
    """PATCH position within the same bucket repacks positions to 0,1,2."""
    tasks = []
    for title in ("A", "B", "C"):
        r = client.post("/api/taskboard/tasks", json={"title": title})
        assert r.status_code == 200
        tasks.append(r.json())

    b_id = tasks[1]["id"]
    patch = client.patch(f"/api/taskboard/tasks/{b_id}", json={"position": 0})
    assert patch.status_code == 200

    resp = client.get("/api/taskboard/tasks?assignee_id=null")
    assert resp.status_code == 200
    listed = resp.json()
    titles = [t["title"] for t in listed]
    assert titles == ["B", "A", "C"]
    assert [t["position"] for t in listed] == [0, 1, 2]


def test_patch_task_cross_bucket_move_with_explicit_position(client):
    """PATCH with assignee_id and position moves to specific slot in new bucket."""
    user_resp = client.post("/api/taskboard/users", json={"name": "Karim"})
    assert user_resp.status_code == 200
    user_id = user_resp.json()["id"]

    # Create two tasks in Issues
    t1 = client.post("/api/taskboard/tasks", json={"title": "First"}).json()
    t2 = client.post("/api/taskboard/tasks", json={"title": "Second"}).json()

    # Move First to user with explicit position 0
    patch = client.patch(f"/api/taskboard/tasks/{t1['id']}", json={"assignee_id": user_id, "position": 0})
    assert patch.status_code == 200
    body = patch.json()
    assert body["assignee_id"] == user_id
    assert body["position"] == 0

    # Move Second to user end
    patch2 = client.patch(f"/api/taskboard/tasks/{t2['id']}", json={"assignee_id": user_id})
    assert patch2.status_code == 200
    assert patch2.json()["position"] == 1


def test_patch_task_omitted_assignee_does_not_change_assignee(client):
    """PATCH that omits assignee_id leaves the existing assignee untouched."""
    user_resp = client.post("/api/taskboard/users", json={"name": "Karim"})
    assert user_resp.status_code == 200
    user_id = user_resp.json()["id"]

    task_resp = client.post("/api/taskboard/tasks", json={"title": "Stable"})
    assert task_resp.status_code == 200
    task_id = task_resp.json()["id"]

    # Assign to user
    client.patch(f"/api/taskboard/tasks/{task_id}", json={"assignee_id": user_id})

    # Patch only title
    patch = client.patch(f"/api/taskboard/tasks/{task_id}", json={"title": "Stable Updated"})
    assert patch.status_code == 200
    body = patch.json()
    assert body["title"] == "Stable Updated"
    assert body["assignee_id"] == user_id


def test_archive_task_hides_from_list(client):
    """Archived tasks are excluded from GET /tasks."""
    task_resp = client.post("/api/taskboard/tasks", json={"title": "Gone"})
    assert task_resp.status_code == 200
    task_id = task_resp.json()["id"]

    archive = client.delete(f"/api/taskboard/tasks/{task_id}")
    assert archive.status_code == 200

    resp = client.get("/api/taskboard/tasks?assignee_id=null")
    assert resp.status_code == 200
    tasks = resp.json()
    assert all(t["id"] != task_id for t in tasks)


def test_archive_does_not_affect_other_tasks_positions(client):
    """Archiving one task leaves remaining tasks with compact positions 0,1."""
    tasks = []
    for title in ("A", "B", "C"):
        r = client.post("/api/taskboard/tasks", json={"title": title})
        assert r.status_code == 200
        tasks.append(r.json())

    b_id = tasks[1]["id"]
    client.delete(f"/api/taskboard/tasks/{b_id}")

    resp = client.get("/api/taskboard/tasks?assignee_id=null")
    assert resp.status_code == 200
    listed = resp.json()
    assert [t["title"] for t in listed] == ["A", "C"]
    assert [t["position"] for t in listed] == [0, 1]
