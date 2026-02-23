from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Optional
import uuid

try:
    import tasks_db as _tasks_db
except Exception:
    # tasks_db may not be importable in test environments (no psycopg2); we'll allow tests to monkeypatch server.tasks_db
    _tasks_db = None

tasks_db = _tasks_db


class EscalationRequest(BaseModel):
    booking: dict
    source: Optional[str] = "parking_agent"
    metadata: Optional[dict] = None


class EscalationResponse(BaseModel):
    task_id: str
    status: str


class ResolutionRequest(BaseModel):
    decision: str  # 'confirm' or 'refuse'
    notes: Optional[str] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP CODE ---
    if tasks_db:
        tasks_db.init_db()

    yield

    # --- SHUTDOWN CODE ---
    # cleanup if needed


app = FastAPI(lifespan=lifespan, title="ParkingBot Admin API")

@app.post("/escalate", response_model=EscalationResponse)
def escalate(payload: EscalationRequest):
    task_id = str(uuid.uuid4())
    tasks_db.create_task(task_id, payload.booking, {"source": payload.source, **(payload.metadata or {})})
    return {"task_id": task_id, "status": "pending"}


@app.get("/tasks/{task_id}")
def get_task(task_id: str):
    task = tasks_db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@app.post("/tasks/{task_id}/resolve")
def resolve_task(task_id: str, resolution: ResolutionRequest):
    task = tasks_db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")

    updated = tasks_db.update_task_resolution(task_id, {"decision": resolution.decision, "notes": resolution.notes})
    if not updated:
        raise HTTPException(status_code=500, detail="could not update task")

    return {"task_id": task_id, "status": resolution.decision}


@app.get("/tasks")
def list_tasks(status: str = "pending"):
    """List tasks with given status (default: pending). Returns id and created_at."""
    if not tasks_db:
        return []
    items = tasks_db.list_pending_tasks() if status == "pending" else []
    return items
