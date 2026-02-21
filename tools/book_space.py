from utils.booking_model import BookingInfo
from utils import config
from agents.admin_agent import AdminAgent

# Use AdminAgent synchronous helper for escalation and waiting
_admin_agent = AdminAgent(admin_api_url=config.ADMIN_API_URL)


def book_parking_space(booking_info: BookingInfo):
    """
        Book an appointment with the given booking information. Confirm the given information with the customer before using this tool.
        After giving the start and end time you should select a random spot number that is free based on the SQL table.
        There are a total of 42 parking spots available with spot numbers 1-42.

        Args:
            booking_info (CustomerInfo): booking information to book a parking space.

        Returns:
            dict: A dictionary with the status and message.

        Example:
            book_parking_space(
                booking_info=BookingInfo(
                    name="John Smith"
                    license_plate="ABC123",
                    start_datetime=datetime.datetime(2025, 6, 7, 15, 00, 00),
                    end_datetime=datetime.datetime(2025, 6, 7, 16, 00, 00),
                    spot_number=15
                )
            )
            {
                'status': 'success',
                'message': 'Successfully booked a parking space for {booking_info.name} at {booking_info.start_datetime} for {booking_info.license_plate}'
            }
    """
    if booking_info.check_if_all_fields_present():
        # Notify admin by creating an escalation task in the admin API (demo: unauthenticated)
        payload = {
            "booking": {
                "name": booking_info.name,
                "license_plate": booking_info.license_plate,
                "start_datetime": booking_info.start_datetime.isoformat() if hasattr(booking_info.start_datetime, 'isoformat') else str(booking_info.start_datetime),
                "end_datetime": booking_info.end_datetime.isoformat() if hasattr(booking_info.end_datetime, 'isoformat') else str(booking_info.end_datetime),
                # "spot_number": booking_info.spot_number,
            },
            "source": "book_parking_space_tool",
        }
        try:
            # Create escalation and wait synchronously for admin decision via AdminAgent helper
            # The AdminAgent method will raise TimeoutError on timeout
            print("Booking requires admin confirmation, creating escalation task and waiting for resolution...\n")
            result_task = _admin_agent.create_task_and_wait(payload)

            # At this point, the admin has resolved the task and result_task contains resolution
            res = result_task.get('resolution') or {}
            decision = (res.get('decision') or '').lower()
            notes = res.get('notes')
            if decision in ('confirm', 'confirmed'):
                return {"status": "confirmed", "message": f"Booking confirmed by admin. Notes: {notes or ''}"}
            else:
                return {"status": "refused", "message": f"Booking refused by admin. Notes: {notes or ''}"}
        except TimeoutError:
            return {"status": "failure", "message": "Timeout waiting for admin confirmation"}
        except Exception as e:
            return {"status": "failure", "message": f"Error creating escalation task or waiting for admin: {str(e)}"}
    else:
        return {
            "status": "failure",
            "message": "Error booking parking space: Please confirm all the information is present"
        }