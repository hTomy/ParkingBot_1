import os
from typing import Optional

from utils import config
import requests
import time


class AdminAgent:
    """A minimal wrapper that creates escalation tasks by calling the admin REST API.
    """

    def __init__(self, admin_api_url: Optional[str] = None, model_name: Optional[str] = None):
        self.admin_api_url = admin_api_url or os.getenv("ADMIN_API_URL", "http://127.0.0.1:8001")
        self.model_name = model_name or config.MODEL

    def create_task(self, booking: dict, metadata: dict = None, timeout: float = 10.0) -> dict:
        """Create a task synchronously using requests. Returns the created task response."""
        payload = {"booking": booking, "source": "admin_agent", "metadata": metadata or {}}
        resp = requests.post(f"{self.admin_api_url.rstrip('/')}/escalate", json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    def wait_for_resolution(self, task_id: str, poll_interval: Optional[float] = None, poll_timeout: Optional[float] = None) -> dict:
        """Poll GET /tasks/{task_id} until resolution is present or timeout. Returns the task dict when resolved.

        Raise requests exceptions for persistent HTTP errors.
        """
        poll_interval = float(poll_interval or getattr(config, 'ADMIN_POLL_INTERVAL', 5))
        poll_timeout = float(poll_timeout or getattr(config, 'ADMIN_POLL_TIMEOUT', 600))
        start = time.time()
        task_url = f"{self.admin_api_url.rstrip('/')}/tasks/{task_id}"
        while True:
            if time.time() - start > poll_timeout:
                raise TimeoutError(f"Timeout waiting for admin resolution of task {task_id}")
            try:
                resp = requests.get(task_url, timeout=5)
                resp.raise_for_status()
                task = resp.json()
                if task.get('resolution'):
                    return task
            except requests.RequestException:
                # swallow transient HTTP errors and retry until timeout
                pass
            time.sleep(poll_interval)

    def create_task_and_wait(self, booking: dict, metadata: dict = None, poll_interval: Optional[float] = None, poll_timeout: Optional[float] = None) -> dict:
        """Create an escalation task synchronously and block until admin resolves it.

        Returns the final task dict (with resolution) or raises on timeout/HTTP error.
        """
        created = self.create_task(booking, metadata=metadata)
        task_id = created.get('task_id')
        if not task_id:
            raise RuntimeError('No task_id returned from admin API')
        return self.wait_for_resolution(task_id, poll_interval=poll_interval, poll_timeout=poll_timeout)
