import os
import json
import psycopg2
from psycopg2.extras import Json
from datetime import datetime, timezone
from typing import Optional

POSTGRES_CONN = {
    "dbname": os.getenv("POSTGRES_DB", "parking_db"),
    "user": os.getenv("POSTGRES_USER", "user"),
    "password": os.getenv("POSTGRES_PASSWORD", "password"),
    "host": os.getenv("POSTGRES_HOST", os.getenv("POSTGRES_HOST", "postgres")),
    "port": os.getenv("POSTGRES_PORT", os.getenv("POSTGRES_PORT", "5432")),
}

TASKS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS admin_tasks (
    id TEXT PRIMARY KEY,
    booking_json JSONB NOT NULL,
    metadata_json JSONB,
    status TEXT NOT NULL,
    resolution_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);
"""


def _connect():
    return psycopg2.connect(**POSTGRES_CONN)


def init_db():
    conn = _connect()
    cur = conn.cursor()
    cur.execute(TASKS_TABLE_SQL)
    conn.commit()
    cur.close()
    conn.close()


def create_task(task_id: str, booking: dict, metadata: dict = None) -> None:
    conn = _connect()
    cur = conn.cursor()
    now = datetime.now(timezone.utc)
    cur.execute(
        "INSERT INTO admin_tasks (id, booking_json, metadata_json, status, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s)",
        (task_id, Json(booking), Json(metadata or {}), "pending", now, now),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_task(task_id: str) -> Optional[dict]:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT id, booking_json, metadata_json, status, resolution_json, created_at, updated_at FROM admin_tasks WHERE id = %s", (task_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    return {
        "id": row[0],
        "booking": row[1],
        "metadata": row[2] or {},
        "status": row[3],
        "resolution": row[4],
        "created_at": row[5].isoformat() if row[5] else None,
        "updated_at": row[6].isoformat() if row[6] else None,
    }


def update_task_resolution(task_id: str, resolution: dict, status: str = "resolved") -> bool:
    conn = _connect()
    cur = conn.cursor()
    now = datetime.now(timezone.utc)
    cur.execute("UPDATE admin_tasks SET resolution_json = %s, status = %s, updated_at = %s WHERE id = %s", (Json(resolution), status, now, task_id))
    conn.commit()
    changed = cur.rowcount > 0
    cur.close()
    conn.close()
    return changed


def list_pending_tasks() -> list:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT id, created_at FROM admin_tasks WHERE status = %s ORDER BY created_at", ("pending",))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"id": r[0], "created_at": r[1].isoformat() if r[1] else None} for r in rows]
