import uuid
from typing import Iterator

from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph, MessagesState
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage
from tools.tools import tools
from utils import config
from prompts import prompts
import asyncio

class ParkingAgent:
    def __init__(self, use_memory_checkpoint: bool = True):
        self.checkpointer = MemorySaver() if use_memory_checkpoint else None

        # Subgraph: LangChain agent (tool loop included)
        self.parking_agent = create_agent(
            model=init_chat_model(config.MODEL),
            tools=tools,
            system_prompt=prompts.PRIMARY_INSTRUCTION,
            checkpointer=self.checkpointer,   # optional; see notes below
            name="parking_agent",             # helps with subgraph scoping/debug
        )

        # Parent graph
        builder = StateGraph(MessagesState)
        builder.add_node("parking_agent", self.parking_agent)
        builder.add_edge(START, "parking_agent")
        builder.add_edge("parking_agent", END)

        self.graph = builder.compile(checkpointer=self.checkpointer) if self.checkpointer else builder.compile()
        self._config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    def invoke_stream(self, message: str) -> Iterator[str]:

        for msg, meta in self.graph.stream(
            {"messages": [HumanMessage(message + " /no_think")]},
            self._config,
            stream_mode="messages",
        ):
            yield msg.content

    def invoke(self, message: str): # TODO convert this to async stream add logging
        out = self.graph.invoke({"messages": [HumanMessage(message)]}, self._config)
        final_ai = next(m for m in reversed(out["messages"]) if isinstance(m, AIMessage))
        return final_ai.content


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
    asyncio.run(debug_run(agent.graph, "what reservations are there for JKL321 licence plate?", agent._config))