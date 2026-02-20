import uuid
from datetime import datetime, timedelta
from typing import Self
from pydantic import Field, BaseModel

class BookingInfo(BaseModel):
    name: str = Field(
        description="Name of the user making the booking",
    )
    license_plate: str = Field(
        description="License plate of the car.",
    )
    start_datetime: datetime = Field(
        description="Date and time of the start of the parking",
    )
    end_datetime: datetime = Field(
        description="Date and time of the end of the parking",
    )
    spot_number: str = Field(
        description="No. of the parking space.",
    )
    @property
    def customer_information(self) -> str:
        return f"Name: {self.name}\nLicence plate: {self.license_plate}\nStart date and time: {self.start_datetime}\nEnd date and time: {self.end_datetime}\nParking space number: {self.spot_number}"

    def check_if_all_fields_present(self) -> bool:
        if self.name and self.license_plate and self.start_datetime and self.end_datetime and self.spot_number:
            return True
        else:
            return False

    def __str__(self):
        return self.customer_information