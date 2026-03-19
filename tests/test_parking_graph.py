"""Tests for the multi-node LangGraph parking pipeline.

These tests mock external dependencies (LLM, admin API, MCP tools) to verify
the graph routing logic:
  chatbot_node  →  admin_approval_node (polls admin API)  →  recording_node  →  chatbot_node

Run with:  pytest tests/test_parking_graph.py -v
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_BOOKING = {
    "name": "Test User",
    "license_plate": "ABC123",
    "start_datetime": "2026-03-20T09:00:00",
    "end_datetime": "2026-03-20T10:00:00",
    "spot_number": "5",
}


# ---------------------------------------------------------------------------
# Unit tests for submit_booking_request tool
# ---------------------------------------------------------------------------

class TestSubmitBookingRequest:
    def test_valid_booking(self):
        from tools.book_space import submit_booking_request
        from utils.booking_model import BookingInfo
        from datetime import datetime

        info = BookingInfo(
            name="Test User",
            license_plate="ABC123",
            start_datetime=datetime(2026, 3, 20, 9, 0),
            end_datetime=datetime(2026, 3, 20, 10, 0),
            spot_number="5",
        )
        result = submit_booking_request(info)
        assert result["status"] == "ready_for_admin"
        assert "booking_info" in result
        assert result["booking_info"]["name"] == "Test User"

    def test_incomplete_booking(self):
        from tools.book_space import submit_booking_request
        from utils.booking_model import BookingInfo
        from datetime import datetime

        # spot_number missing (empty string)
        info = BookingInfo(
            name="Test User",
            license_plate="ABC123",
            start_datetime=datetime(2026, 3, 20, 9, 0),
            end_datetime=datetime(2026, 3, 20, 10, 0),
            spot_number="",
        )
        result = submit_booking_request(info)
        assert result["status"] == "failure"


# ---------------------------------------------------------------------------
# Unit tests for AdminAgent (simplified, no polling)
# ---------------------------------------------------------------------------

class TestAdminAgent:
    def test_create_task(self):
        from agents.admin_agent import AdminAgent
        agent = AdminAgent(admin_api_url="http://fake:8001")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"task_id": "t-123", "status": "pending"}
        mock_resp.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_resp) as mock_post:
            result = agent.create_task({"name": "Test"})
            assert result["task_id"] == "t-123"
            mock_post.assert_called_once()

    def test_get_task(self):
        from agents.admin_agent import AdminAgent
        agent = AdminAgent(admin_api_url="http://fake:8001")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "t-123", "status": "pending", "booking": {}}
        mock_resp.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_resp):
            result = agent.get_task("t-123")
            assert result["id"] == "t-123"

    def test_get_task_not_found(self):
        from agents.admin_agent import AdminAgent
        agent = AdminAgent(admin_api_url="http://fake:8001")

        mock_resp = MagicMock()
        mock_resp.status_code = 404

        with patch("requests.get", return_value=mock_resp):
            result = agent.get_task("nonexistent")
            assert result is None

    @pytest.mark.asyncio
    async def test_wait_for_resolution_success(self):
        """Poll returns resolved task on second attempt."""
        from agents.admin_agent import AdminAgent
        agent = AdminAgent(admin_api_url="http://fake:8001")

        pending_resp = MagicMock()
        pending_resp.status_code = 200
        pending_resp.json.return_value = {"id": "t-1", "resolution": None}
        pending_resp.raise_for_status = MagicMock()

        resolved_resp = MagicMock()
        resolved_resp.status_code = 200
        resolved_resp.json.return_value = {
            "id": "t-1",
            "resolution": {"decision": "confirm", "notes": "ok"},
        }
        resolved_resp.raise_for_status = MagicMock()

        with patch("requests.get", side_effect=[pending_resp, resolved_resp]):
            result = await agent.wait_for_resolution("t-1", poll_interval=0.01, poll_timeout=5)
            assert result["resolution"]["decision"] == "confirm"

    @pytest.mark.asyncio
    async def test_wait_for_resolution_timeout(self):
        """Poll times out if resolution never appears."""
        from agents.admin_agent import AdminAgent
        agent = AdminAgent(admin_api_url="http://fake:8001")

        pending_resp = MagicMock()
        pending_resp.status_code = 200
        pending_resp.json.return_value = {"id": "t-1", "resolution": None}
        pending_resp.raise_for_status = MagicMock()

        with patch("requests.get", return_value=pending_resp):
            with pytest.raises(TimeoutError):
                await agent.wait_for_resolution("t-1", poll_interval=0.01, poll_timeout=0.05)


# ---------------------------------------------------------------------------
# Unit test for _extract_booking_from_messages helper
# ---------------------------------------------------------------------------

class TestExtractBooking:
    def test_extracts_booking(self):
        from agents.parking_agent import _extract_booking_from_messages

        tool_msg = ToolMessage(
            content=json.dumps({
                "status": "ready_for_admin",
                "message": "Booking request submitted.",
                "booking_info": SAMPLE_BOOKING,
            }),
            tool_call_id="tc-1",
        )
        result = _extract_booking_from_messages([HumanMessage("hi"), tool_msg])
        assert result is not None
        assert result["name"] == "Test User"

    def test_no_booking(self):
        from agents.parking_agent import _extract_booking_from_messages

        result = _extract_booking_from_messages([
            HumanMessage("hi"),
            AIMessage(content="Hello!"),
        ])
        assert result is None

    def test_non_booking_tool_message(self):
        from agents.parking_agent import _extract_booking_from_messages

        tool_msg = ToolMessage(
            content=json.dumps({"status": "ok", "data": "some info"}),
            tool_call_id="tc-2",
        )
        result = _extract_booking_from_messages([tool_msg])
        assert result is None


# ---------------------------------------------------------------------------
# Integration tests for the full graph (with mocked LLM & external services)
# ---------------------------------------------------------------------------

class TestParkingGraph:
    """Tests that exercise the full LangGraph pipeline with mocked components."""

    def test_chatbot_no_booking_goes_to_end(self):
        """When the chatbot doesn't trigger a booking, graph should end normally."""
        from agents.parking_agent import ParkingAgent
        state = {"messages": [AIMessage(content="Hello!")], "booking_info": None, "admin_decision": None}
        result = ParkingAgent._route_after_chatbot(state)
        assert result == "__end__"

    def test_route_after_chatbot_with_booking(self):
        """When booking_info is set and no admin decision, route to admin."""
        from agents.parking_agent import ParkingAgent
        state = {
            "messages": [],
            "booking_info": SAMPLE_BOOKING,
            "admin_decision": None,
        }
        result = ParkingAgent._route_after_chatbot(state)
        assert result == "admin_approval_node"

    def test_route_after_chatbot_with_existing_decision(self):
        """When booking_info is set AND admin_decision is already set,
        route to END (don't re-enter admin approval)."""
        from agents.parking_agent import ParkingAgent
        state = {
            "messages": [],
            "booking_info": SAMPLE_BOOKING,
            "admin_decision": "confirmed",
        }
        result = ParkingAgent._route_after_chatbot(state)
        assert result == "__end__"

    def test_route_after_admin_confirm(self):
        """Confirmed decision routes to recording_node."""
        from agents.parking_agent import ParkingAgent
        state = {"admin_decision": "confirmed"}
        result = ParkingAgent._route_after_admin(state)
        assert result == "recording_node"

    def test_route_after_admin_refuse(self):
        """Refused decision routes back to chatbot_node."""
        from agents.parking_agent import ParkingAgent
        state = {"admin_decision": "refused"}
        result = ParkingAgent._route_after_admin(state)
        assert result == "chatbot_node"

    @pytest.mark.asyncio
    async def test_recording_node_calls_write_tool(self):
        """Recording node should invoke write_booking_to_file with booking data."""
        mock_write_tool = MagicMock()
        mock_write_tool.name = "write_booking_to_file"
        mock_write_tool.ainvoke = AsyncMock(return_value={"status": "success", "message": "Written."})

        from agents.parking_agent import ParkingAgent

        # Patch recording_tools where parking_agent reads it
        with patch("agents.parking_agent.recording_tools", [mock_write_tool]):
            agent = ParkingAgent.__new__(ParkingAgent)

            state = {
                "messages": [],
                "booking_info": SAMPLE_BOOKING,
                "admin_decision": "confirmed",
                "admin_notes": "Looks good",
                "task_id": "t-1",
            }

            result = await agent._recording_node(state)

            assert len(result["messages"]) == 1
            content = result["messages"][0].content.lower()
            assert "recorded" in content or "booking" in content
            mock_write_tool.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_recording_node_no_tool_available(self):
        """When write_booking_to_file tool is not found, recording node
        should still return a warning message."""
        from agents.parking_agent import ParkingAgent

        with patch("agents.parking_agent.recording_tools", []):
            agent = ParkingAgent.__new__(ParkingAgent)

            state = {
                "messages": [],
                "booking_info": SAMPLE_BOOKING,
                "admin_decision": "confirmed",
                "admin_notes": "",
                "task_id": "t-1",
            }

            result = await agent._recording_node(state)

            assert len(result["messages"]) == 1
            assert "not available" in result["messages"][0].content.lower() or "warning" in result["messages"][0].content.lower() or "⚠" in result["messages"][0].content

    @pytest.mark.asyncio
    async def test_admin_approval_node_confirm(self):
        """Admin approval node should poll and return confirmed when admin confirms."""
        from agents.parking_agent import ParkingAgent

        agent = ParkingAgent.__new__(ParkingAgent)
        mock_admin = MagicMock()
        mock_admin.create_task.return_value = {"task_id": "t-42", "status": "pending"}
        mock_admin.wait_for_resolution = AsyncMock(return_value={
            "id": "t-42",
            "resolution": {"decision": "confirm", "notes": "Looks good"},
        })
        agent._admin = mock_admin

        state = {
            "messages": [],
            "booking_info": SAMPLE_BOOKING,
            "admin_decision": None,
            "admin_notes": None,
            "task_id": None,
        }

        result = await agent._admin_approval_node(state)

        assert result["admin_decision"] == "confirmed"
        assert result["task_id"] == "t-42"
        assert "confirmed" in result["messages"][0].content.lower()
        mock_admin.create_task.assert_called_once()
        mock_admin.wait_for_resolution.assert_called_once_with("t-42")

    @pytest.mark.asyncio
    async def test_admin_approval_node_refuse(self):
        """Admin approval node should return refused when admin refuses."""
        from agents.parking_agent import ParkingAgent

        agent = ParkingAgent.__new__(ParkingAgent)
        mock_admin = MagicMock()
        mock_admin.create_task.return_value = {"task_id": "t-43", "status": "pending"}
        mock_admin.wait_for_resolution = AsyncMock(return_value={
            "id": "t-43",
            "resolution": {"decision": "refuse", "notes": "Spot taken"},
        })
        agent._admin = mock_admin

        state = {
            "messages": [],
            "booking_info": SAMPLE_BOOKING,
            "admin_decision": None,
            "admin_notes": None,
            "task_id": None,
        }

        result = await agent._admin_approval_node(state)

        assert result["admin_decision"] == "refused"
        assert "refused" in result["messages"][0].content.lower()

    @pytest.mark.asyncio
    async def test_admin_approval_node_timeout(self):
        """Admin approval node should handle timeout gracefully."""
        from agents.parking_agent import ParkingAgent

        agent = ParkingAgent.__new__(ParkingAgent)
        mock_admin = MagicMock()
        mock_admin.create_task.return_value = {"task_id": "t-44", "status": "pending"}
        mock_admin.wait_for_resolution = AsyncMock(side_effect=TimeoutError("timed out"))
        agent._admin = mock_admin

        state = {
            "messages": [],
            "booking_info": SAMPLE_BOOKING,
            "admin_decision": None,
            "admin_notes": None,
            "task_id": None,
        }

        result = await agent._admin_approval_node(state)

        assert result["admin_decision"] == "refused"
        assert "timed out" in result["messages"][0].content.lower()


# ---------------------------------------------------------------------------
# Test the admin server API (already covered in test_admin_api.py but
# included here for completeness of the pipeline test suite)
# ---------------------------------------------------------------------------

class TestAdminServerIntegration:
    """Verify the admin server endpoints work correctly."""

    def test_escalation_flow(self):
        """Test the full escalate → get → resolve flow."""
        from fastapi.testclient import TestClient
        from servers.admin_server import server

        class FakeDB:
            def __init__(self):
                self.store = {}

            def init_db(self):
                pass

            def create_task(self, task_id, booking, metadata=None):
                self.store[task_id] = {
                    "id": task_id, "booking": booking,
                    "metadata": metadata or {}, "status": "pending",
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
                return [{"id": k} for k, v in self.store.items() if v["status"] == "pending"]

        fake = FakeDB()
        original_db = server.tasks_db
        server.tasks_db = fake

        try:
            client = TestClient(server.app)

            # Escalate
            r = client.post("/escalate", json={"booking": SAMPLE_BOOKING})
            assert r.status_code == 200
            task_id = r.json()["task_id"]

            # Get pending
            r2 = client.get(f"/tasks/{task_id}")
            assert r2.status_code == 200
            assert r2.json()["status"] == "pending"

            # Resolve
            r3 = client.post(f"/tasks/{task_id}/resolve",
                             json={"decision": "confirm", "notes": "All good"})
            assert r3.status_code == 200
            assert r3.json()["status"] == "confirm"
        finally:
            server.tasks_db = original_db





