import uuid

from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph, MessagesState
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage
from tools.tools import tools
from utils import config
from prompts import prompts
import asyncio


class ParkingAgent:
    def __init__(self, use_memory_checkpoint: bool = True):
        self.checkpointer = MemorySaver() if use_memory_checkpoint else None

        self.parking_agent = create_agent(
            model=config.MODEL,
            tools=tools,
            system_prompt=prompts.PRIMARY_INSTRUCTION,
            checkpointer=self.checkpointer,
            name="parking_agent",
        )

        builder = StateGraph(MessagesState)
        builder.add_node("parking_agent", self.parking_agent)
        builder.add_edge(START, "parking_agent")
        builder.add_edge("parking_agent", END)

        self.graph = builder.compile(checkpointer=self.checkpointer) if self.checkpointer else builder.compile()
        self._config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    async def ainvoke(self, message: str):
        out = await self.graph.ainvoke({"messages": [HumanMessage(message)]}, self._config)

        final_ai = next(m for m in reversed(out["messages"]) if isinstance(m, AIMessage))
        return final_ai.content

    async def astream(self, message: str):
        async for msg, meta in self.graph.astream(
            {"messages": [HumanMessage(message)]},
            self._config,
            stream_mode="messages",
        ):
            if isinstance(msg, AIMessage) and msg.content:
                yield msg.content, meta


if __name__ == '__main__':
    #Debug
    async def debug_run(app, text, config):
        async for event in app.astream_events(
                {"messages": [HumanMessage(text)]},
                config=config,
                version="v2",
        ):
            # if event["event"] == "on_tool_start":
            #     print("TOOL:", event.get("name"), "INPUT:", event.get("data", {}).get("input"))
            print(
                event["event"],
                "|",
                event.get("name"),
                "|",
                event.get("data")
            )


    agent = ParkingAgent(use_memory_checkpoint=True)
    asyncio.run(debug_run(agent.graph, "Hello my name is Tamas and I  want to make a reservation. "
                                       "My license plate is RMS456 and time would be 2026-02-24 14:00 - 15:00",
                          agent._config))