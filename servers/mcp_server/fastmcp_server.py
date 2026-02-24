import os

from fastmcp import FastMCP

BOOKINGS_FILE_NAME = os.getenv("BOOKINGS_FILE_NAME", "confirmed_bookings.csv")

mcp = FastMCP()

@mcp.tool
def write_booking_to_file(booking_info: dict) -> dict:
    """Write booking info to csv file(append mode), after booking process has finished."""

    with open(BOOKINGS_FILE_NAME, "a") as f:
        f.write(f"{booking_info.get('name')},{booking_info.get('license_plate')},{booking_info.get('start_datetime')},"
                f"{booking_info.get('end_datetime')},{booking_info.get('spot_number')}\n")

    return {"status": "success", "message": "Booking info written to file."}

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
