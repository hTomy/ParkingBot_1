import asyncio
from fastmcp import Client

client = Client("http://localhost:8000/mcp")

async def call_write_booking_tool(booking_info: dict):
    async with client:
        result = await client.call_tool("write_booking_to_file",
                                        booking_info)
        print(result)

asyncio.run(call_write_booking_tool({"booking_info": {"name": "John",
                                                                    "license_plate": "LTP654",
                                                                    "start_datetime": "2024-06-02T10:00:00",
                                                                    "end_datetime": "2024-06-03T12:00:00",
                                                                    "spot_number": "11"}
                                                                }))