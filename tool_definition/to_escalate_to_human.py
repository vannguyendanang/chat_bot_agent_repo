from pydantic import BaseModel
from pydantic import Field

class ToEscalateToHuman(BaseModel):
    """A tool to escalate the question to a human instead of being solved by an agent"""

    # account_number: str = Field(description="The account number to which the transaction belongs.")
    reason: str = Field(description="The reason for the escalation")
    transaction_id: str = Field(description="The transaction that is being escalated")
    
    class Config:
        json_schema_extra = {
            "example": {
                # "account_number": "1234567",
                "reason": "unauthorized",
                "transaction_id": "123xyz",
            }
        }