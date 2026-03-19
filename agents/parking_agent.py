import json
import uuid
import logging
from typing import Optional

from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI

from tools.tools import chatbot_tools, recording_tools
from agents.admin_agent import AdminAgent
from utils import config
from prompts import prompts

import asyncio

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Extended state – carries booking & admin decision across nodes
# ---------------------------------------------------------------------------
class ParkingState(MessagesState):
    booking_info: Optional[dict]       # populated when submit_booking_request succeeds
    admin_decision: Optional[str]      # "confirmed" / "refused" after admin node
    admin_notes: Optional[str]         # optional notes from admin
    task_id: Optional[str]             # admin API task id


# ---------------------------------------------------------------------------
# Helper: scan the last tool message for a ready_for_admin signal
# ---------------------------------------------------------------------------
def _extract_booking_from_messages(messages) -> Optional[dict]:
    """Walk messages backwards looking for a ToolMessage whose content
    contains ``"ready_for_admin"`` — this means the chatbot called
    ``submit_booking_request`` and the booking is complete."""
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage):
            try:
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
                data = json.loads(content)
                if isinstance(data, dict) and data.get("status") == "ready_for_admin":
                    return data.get("booking_info")
            except (json.JSONDecodeError, TypeError):
                continue
    return None


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------
class ParkingAgent:
    def __init__(self, use_memory_checkpoint: bool = True):
        self.checkpointer = MemorySaver() if use_memory_checkpoint else None

        llm = ChatOpenAI(model=config.MODEL, temperature=0)
        self._admin = AdminAgent(admin_api_url=config.ADMIN_API_URL)

        # --- Chatbot sub-agent (ReAct agent with tools) ----
        self._chatbot_agent = create_react_agent(
            model=llm,
            tools=chatbot_tools,
            prompt=prompts.PRIMARY_INSTRUCTION,
            name="chatbot_react",
        )

        # --- Build the graph ---
        builder = StateGraph(ParkingState)

        builder.add_node("chatbot_node", self._chatbot_node)
        builder.add_node("admin_approval_node", self._admin_approval_node)
        builder.add_node("recording_node", self._recording_node)

        builder.add_edge(START, "chatbot_node")
        builder.add_conditional_edges(
            "chatbot_node",
            self._route_after_chatbot,
            {"admin_approval_node": "admin_approval_node", END: END},
        )
        builder.add_conditional_edges(
            "admin_approval_node",
            self._route_after_admin,
            {"recording_node": "recording_node", "chatbot_node": "chatbot_node"},
        )
        builder.add_edge("recording_node", "chatbot_node")

        self.graph = builder.compile(checkpointer=self.checkpointer)
        self._config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    # ------------------------------------------------------------------
    # Node: chatbot  (user interaction, RAG, SQL, booking submission)
    # ------------------------------------------------------------------
    async def _chatbot_node(self, state: ParkingState) -> dict:
        """Run the ReAct chatbot agent. After it finishes, inspect tool
        outputs for a booking submission signal."""
        result = await self._chatbot_agent.ainvoke(
            {"messages": state["messages"]},
        )
        new_messages = result["messages"][len(state["messages"]):]

        # Check if the chatbot submitted a booking request
        booking = _extract_booking_from_messages(new_messages)
        if booking:
            return {
                "messages": new_messages,
                "booking_info": booking,
                "admin_decision": None,
                "admin_notes": None,
                "task_id": None,
            }
        return {"messages": new_messages}

    # ------------------------------------------------------------------
    # Node: admin approval  (polls external admin API for resolution)
    # ------------------------------------------------------------------
    async def _admin_approval_node(self, state: ParkingState) -> dict:
        """Create an escalation task on the admin API, then poll
        ``GET /tasks/{task_id}`` until the admin resolves it externally."""
        booking = state.get("booking_info") or {}

        # Create escalation task via admin REST API
        try:
            created = self._admin.create_task(booking, metadata={"source": "langgraph_pipeline"})
            task_id = created.get("task_id", "unknown")
            logger.info("Escalation task created: %s — waiting for admin resolution …", task_id)
        except Exception as e:
            msg = AIMessage(
                content=f"⚠️ Could not reach admin API to create escalation task: {e}"
            )
            return {
                "messages": [msg],
                "admin_decision": "refused",
                "admin_notes": f"admin API error: {e}",
                "task_id": None,
            }

        # Poll the admin API until the resolution field is populated
        try:
            resolved_task = await self._admin.wait_for_resolution(task_id)
        except TimeoutError:
            msg = AIMessage(
                content="⏰ Timed out waiting for admin to resolve the booking request."
            )
            return {
                "messages": [msg],
                "admin_decision": "refused",
                "admin_notes": "timeout",
                "task_id": task_id,
            }
        except Exception as e:
            msg = AIMessage(
                content=f"⚠️ Error while polling admin API: {e}"
            )
            return {
                "messages": [msg],
                "admin_decision": "refused",
                "admin_notes": str(e),
                "task_id": task_id,
            }

        # Parse the resolution from the admin server response
        resolution = resolved_task.get("resolution") or {}
        decision = (resolution.get("decision") or "").lower()
        notes = resolution.get("notes") or ""

        if decision in ("confirm", "confirmed"):
            msg = AIMessage(content=f"✅ Booking has been **confirmed** by the admin. Notes: {notes or 'none'}")
            return {
                "messages": [msg],
                "admin_decision": "confirmed",
                "admin_notes": notes,
                "task_id": task_id,
            }
        else:
            msg = AIMessage(content=f"❌ Booking has been **refused** by the admin. Notes: {notes or 'none'}")
            return {
                "messages": [msg],
                "admin_decision": "refused",
                "admin_notes": notes,
                "task_id": task_id,
            }

    # ------------------------------------------------------------------
    # Node: recording  (persist confirmed booking via MCP tool)
    # ------------------------------------------------------------------
    async def _recording_node(self, state: ParkingState) -> dict:
        """Write the confirmed booking to storage using the MCP
        ``write_booking_to_file`` tool."""
        booking = state.get("booking_info") or {}

        # Find the write_booking_to_file tool from recording_tools
        write_tool = None
        for t in recording_tools:
            if t.name == "write_booking_to_file":
                write_tool = t
                break

        if write_tool is None:
            msg = AIMessage(content="⚠️ Recording tool (write_booking_to_file) not available. Booking was confirmed but could not be saved to file.")
            return {"messages": [msg]}

        try:
            tool_input = {
                "booking_info": {
                    "name": booking.get("name", ""),
                    "license_plate": booking.get("license_plate", ""),
                    "start_datetime": booking.get("start_datetime", ""),
                    "end_datetime": booking.get("end_datetime", ""),
                    "spot_number": booking.get("spot_number", 0),
                }
            }
            result = await write_tool.ainvoke(tool_input)
            msg = AIMessage(
                content=f"📝 Booking recorded successfully. Details:\n"
                        f"  Name: {booking.get('name')}\n"
                        f"  License plate: {booking.get('license_plate')}\n"
                        f"  From: {booking.get('start_datetime')}\n"
                        f"  To: {booking.get('end_datetime')}\n"
                        f"  Spot: {booking.get('spot_number')}\n"
                        f"  Result: {result}"
            )
        except Exception as e:
            msg = AIMessage(content=f"⚠️ Error recording booking: {e}")

        return {"messages": [msg]}

    # ------------------------------------------------------------------
    # Routing functions
    # ------------------------------------------------------------------
    @staticmethod
    def _route_after_chatbot(state: ParkingState) -> str:
        """If booking_info was just populated and no admin decision yet,
        route to admin approval. Otherwise end the turn."""
        if state.get("booking_info") and not state.get("admin_decision"):
            return "admin_approval_node"
        return END

    @staticmethod
    def _route_after_admin(state: ParkingState) -> str:
        """Route to recording if confirmed, back to chatbot if refused."""
        if state.get("admin_decision") == "confirmed":
            return "recording_node"
        return "chatbot_node"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def ainvoke(self, message: str):
        out = await self.graph.ainvoke(
            {"messages": [HumanMessage(message)]}, self._config,
        )
        final_ai = next(
            (m for m in reversed(out["messages"]) if isinstance(m, AIMessage)),
            None,
        )
        return final_ai.content if final_ai else ""

    async def astream(self, message: str):
        async for msg, meta in self.graph.astream(
            {"messages": [HumanMessage(message)]},
            self._config,
            stream_mode="messages",
        ):
            if isinstance(msg, AIMessage) and msg.content:
                yield msg.content, meta



if __name__ == '__main__':
    # Debug
    async def debug_run(app, text, config):
        async for event in app.astream_events(
                {"messages": [HumanMessage(text)]},
                config=config,
                version="v2",
        ):
            print(
                event["event"],
                "|",
                event.get("name"),
                "|",
                event.get("data")
            )

    agent = ParkingAgent(use_memory_checkpoint=True)
    asyncio.run(debug_run(agent.graph, "Hello my name is Tamas and I want to make a reservation. "
                                       "My license plate is RMS456 and time would be 2026-02-24 14:00 - 15:00",
                          agent._config))