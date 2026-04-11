from pydantic import BaseModel
from pydantic import Field

class ToCheckTransactionExist(BaseModel):
    """A tool to check if a transaction exist in the system."""

    # account_number: str = Field(description="The account number to which the transaction belongs.")
    transfer_date_time: str = Field(description="The date time of transaction records")
    receiver_firstname: str = Field(description="The first name of receiver")
    receiver_lastname: str = Field(description="The last name of receiver")
    transfer_amount: str = Field(description="The amount has been transfered")
    
    class Config:
        json_schema_extra = {
            "example": {
                # "account_number": "1234567",
                "transfer_date_time": "September 1 2024 15:30:00",
                "receiver_firstname": "Mary",
                "receiver_lastname": "Smith",
                "transfer_amount": "$123"
            }
        }