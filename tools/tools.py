from tools.book_space import submit_booking_request

import asyncio
import logging

logger = logging.getLogger(__name__)


async def init_mcp_tools():
    from langchain_mcp_adapters.client import MultiServerMCPClient

    client = MultiServerMCPClient(
        {
            "my_server": {
                "url": "http://localhost:8000/mcp",
                "transport": "http",
            }
        }
    )

    tools = await client.get_tools()

    return tools


def _load_mcp_tools():
    """Load MCP tools, returning empty list on connection failure."""
    try:
        return asyncio.run(init_mcp_tools())
    except Exception as e:
        logger.warning("Could not connect to MCP server, MCP tools unavailable: %s", e)
        return []


def _load_chatbot_tools():
    """Build chatbot tools list, handling import/connection failures gracefully."""
    tools = [submit_booking_request]
    try:
        from tools.vector_db import parking_kb_retrieve
        tools.insert(0, parking_kb_retrieve)
    except Exception as e:
        logger.warning("Could not load parking_kb_retrieve: %s", e)
    try:
        from tools.sql_db import sql_tools
        tools.extend(sql_tools())
    except Exception as e:
        logger.warning("Could not load SQL tools: %s", e)
    return tools


mcp_tools = _load_mcp_tools()

# Tools for the chatbot node (user interaction, RAG, SQL, booking submission)
chatbot_tools = _load_chatbot_tools()

# Tools for the recording node (MCP write_booking_to_file)
recording_tools = list(mcp_tools)

# Combined list (kept for backward compatibility)
tools = chatbot_tools + recording_tools

