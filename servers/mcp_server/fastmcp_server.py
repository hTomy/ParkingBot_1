import os
from pydantic import BaseModel

from fastmcp import FastMCP

BOOKINGS_FILE_NAME = os.getenv("BOOKINGS_FILE_NAME", "confirmed_bookings.csv")

mcp = FastMCP()

class BookingInput(BaseModel):
    name: str
    license_plate: str
    start_datetime: str
    end_datetime: str
    spot_number: int


@mcp.tool
def write_booking_to_file(booking_info: BookingInput) -> dict:
    """
        Write provided booking_info to a csv file.
    """

    with open(BOOKINGS_FILE_NAME, "a") as f:
        f.write(f"{booking_info.name},{booking_info.license_plate},{booking_info.start_datetime},"
                f"{booking_info.end_datetime},{booking_info.spot_number}\n")

    return {"status": "success", "message": "Booking info written to file."}

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
