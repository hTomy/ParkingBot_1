from utils.booking_model import BookingInfo


def book_parking_space(booking_info: BookingInfo):
    """
        Book an appointment with the given booking information. Confirm the given information with the customer before using this tool.
        After giving the start and end time you should select a spot number that is free based on the SQL table.

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
        try:
            return {
                "status": "success",
                "message": f"Successfully booked a parking space for {booking_info.name} at {booking_info.start_datetime}, "
                           f"parking space number: {booking_info.spot_number}. Please wait for confirmation from the admin.",
            }
        except Exception as e:
            return {
                "status": "failure",
                "message": f"Error booking parking space: f{str(e)}"
            }
    else:
        return {
            "status": "failure",
            "message": "Error booking parking space: Please confirm all the information is present"
        }