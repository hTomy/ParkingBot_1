import os
import asyncio
import time
import logging
from typing import Optional

import requests

from utils import config

logger = logging.getLogger(__name__)


class AdminAgent:
    """A wrapper that creates escalation tasks via the admin REST API
    and polls for resolution.
    """

    def __init__(self, admin_api_url: Optional[str] = None):
        self.admin_api_url = admin_api_url or os.getenv("ADMIN_API_URL", "http://127.0.0.1:8001")

    def create_task(self, booking: dict, metadata: dict = None, timeout: float = 10.0) -> dict:
        """Create a task synchronously using requests. Returns the created task response."""
        payload = {"booking": booking, "source": "admin_agent", "metadata": metadata or {}}
        resp = requests.post(f"{self.admin_api_url.rstrip('/')}/escalate", json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    def get_task(self, task_id: str, timeout: float = 10.0) -> Optional[dict]:
        """Retrieve a task by ID. Returns the task dict or None if not found."""
        resp = requests.get(f"{self.admin_api_url.rstrip('/')}/tasks/{task_id}", timeout=timeout)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    async def wait_for_resolution(
        self,
        task_id: str,
        poll_interval: Optional[float] = None,
        poll_timeout: Optional[float] = None,
    ) -> dict:
        """Async-poll GET /tasks/{task_id} until the resolution field is
        populated or timeout is reached.

        Returns the full task dict (including ``resolution``) when resolved.
        Raises ``TimeoutError`` if the admin doesn't respond in time.
        """
        poll_interval = float(poll_interval or config.ADMIN_POLL_INTERVAL)
        poll_timeout = float(poll_timeout or config.ADMIN_POLL_TIMEOUT)
        task_url = f"{self.admin_api_url.rstrip('/')}/tasks/{task_id}"
        start = time.monotonic()

        while True:
            elapsed = time.monotonic() - start
            if elapsed > poll_timeout:
                raise TimeoutError(
                    f"Timeout ({poll_timeout}s) waiting for admin resolution of task {task_id}"
                )
            try:
                resp = requests.get(task_url, timeout=5)
                resp.raise_for_status()
                task = resp.json()
                if task.get("resolution"):
                    logger.info("Admin resolved task %s after %.1fs", task_id, elapsed)
                    return task
            except requests.RequestException as exc:
                logger.debug("Transient error polling task %s: %s", task_id, exc)

            await asyncio.sleep(poll_interval)

    async def create_task_and_wait(
        self,
        booking: dict,
        metadata: dict = None,
        poll_interval: Optional[float] = None,
        poll_timeout: Optional[float] = None,
    ) -> dict:
        """Create an escalation task and asynchronously poll until the
        admin resolves it.  Returns the final task dict with resolution."""
        created = self.create_task(booking, metadata=metadata)
        task_id = created.get("task_id")
        if not task_id:
            raise RuntimeError("No task_id returned from admin API")
        return await self.wait_for_resolution(
            task_id, poll_interval=poll_interval, poll_timeout=poll_timeout
        )

