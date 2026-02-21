import pytest
from fastapi.testclient import TestClient

# Import the FastAPI app
from admin_api import server

# We'll monkeypatch the tasks_db module to avoid real Postgres in unit tests
class FakeDB:
    def __init__(self):
        self.store = {}

    def init_db(self):
        pass

    def create_task(self, task_id, booking, metadata=None):
        self.store[task_id] = {
            "id": task_id,
            "booking": booking,
            "metadata": metadata or {},
            "status": "pending",
            "resolution": None,
        }

    def get_task(self, task_id):
        return self.store.get(task_id)

    def update_task_resolution(self, task_id, resolution, status="resolved"):
        if task_id not in self.store:
            return False
        self.store[task_id]["resolution"] = resolution
        self.store[task_id]["status"] = status
        return True

    def list_pending_tasks(self):
        return [{"id": k, "created_at": v.get("created_at")} for k, v in self.store.items() if v.get("status") == "pending"]


@pytest.fixture(autouse=True)
def patch_tasks_db(monkeypatch):
    fake = FakeDB()
    monkeypatch.setattr(server, "tasks_db", fake)
    return fake


client = TestClient(server.app)


def test_escalate_and_get_and_resolve():
    booking = {"name": "Test User", "license_plate": "ABC123", "start_datetime": "2026-02-21T09:00:00", "end_datetime": "2026-02-21T10:00:00"}
    r = client.post("/escalate", json={"booking": booking})
    assert r.status_code == 200
    payload = r.json()
    assert "task_id" in payload
    task_id = payload["task_id"]

    # Get task
    r2 = client.get(f"/tasks/{task_id}")
    assert r2.status_code == 200
    task = r2.json()
    assert task["booking"]["name"] == "Test User"

    # Resolve
    r3 = client.post(f"/tasks/{task_id}/resolve", json={"decision": "confirm", "notes": "ok"})
    assert r3.status_code == 200
    res = r3.json()
    assert res["status"] == "confirm"

    # list pending tasks (should be empty now)
    r4 = client.get('/tasks')
    assert r4.status_code == 200
    assert isinstance(r4.json(), list)


def test_get_missing_task():
    r = client.get("/tasks/nonexistent")
    assert r.status_code == 404
