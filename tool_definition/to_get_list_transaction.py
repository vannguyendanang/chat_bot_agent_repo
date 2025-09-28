from pydantic import BaseModel
from pydantic import Field

class ToGetListTransaction(BaseModel):
    """A tool to delegate transaction related tasks to a specialized assistant."""

    # account_number: str = Field(description="The account number to which the transaction belongs.")
    start_date: str = Field(description="The start date to search transaction records")
    end_date: str = Field(description="The end date to search transaction records")

    class Config:
        json_schema_extra = {
            "example": {
                # "account_number": "1234567",
                "start_date": "September 1 2024",
                "end_date": "October 1 2024",
            }
        }