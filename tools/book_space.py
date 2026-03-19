from utils.booking_model import BookingInfo


def submit_booking_request(booking_info: BookingInfo) -> dict:
    """
        Submit a parking booking request for admin approval.
        Confirm the given information with the customer before using this tool.
        After giving the start and end time you should select a random spot number that is free based on the SQL table.
        There are a total of 42 parking spots available with spot numbers 1-42.
        Parking spots info can be found in 'parking_bookings' table.

        This tool does NOT finalize the booking. It submits the request for admin review.
        The admin will approve or refuse the booking in a subsequent step.

        Args:
            booking_info (BookingInfo): booking information to submit for approval.

        Returns:
            dict: A dictionary with the status and booking_info.

        Example:
            submit_booking_request(
                booking_info=BookingInfo(
                    name="John Smith",
                    license_plate="ABC123",
                    start_datetime=datetime.datetime(2025, 6, 7, 15, 0, 0),
                    end_datetime=datetime.datetime(2025, 6, 7, 16, 0, 0),
                    spot_number=15
                )
            )
            {
                'status': 'ready_for_admin',
                'message': 'Booking request submitted. Waiting for admin approval.',
                'booking_info': { ... }
            }
    """
    if booking_info.check_if_all_fields_present():
        return {
            "status": "ready_for_admin",
            "message": "Booking request submitted. Waiting for admin approval.",
            "booking_info": booking_info.model_dump(mode="json"),
        }
    else:
        return {
            "status": "failure",
            "message": "Error: Please confirm all the information is present (name, license plate, start time, end time, spot number).",
        }