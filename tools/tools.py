from tools.sql_db import sql_tools
from tools.vector_db import parking_kb_retrieve
from tools.book_space import book_parking_space

import asyncio


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

mcp_tools = asyncio.run(init_mcp_tools()) # tools provided by MCP server, e.g. write_booking_to_file
tools = [parking_kb_retrieve,
         book_parking_space,
         *sql_tools(),
         *mcp_tools
        ]


