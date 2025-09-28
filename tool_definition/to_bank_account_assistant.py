from pydantic import BaseModel
from pydantic import Field

# Create a Pydantic model named "ToBankAccountAssistant" that inherits from pydantic.BaseModel.
# This tool needs to specify what inputs it accepts and their types. Pydantic handles this.
# If the LLM generates an invalid call like {"location": 123}, Pydantic throws a validation error. 
# Without Pydantic, you’d need to write custom code for every tool to check and clean up inputs.
class ToBankAccountAssistant(BaseModel):
    """A tool to delegate bank account related tasks to a specialized assistant."""

    email: str = Field(description="The new email address that user wants to update.")
    address: str = Field(description="The new address that user wants to update.")
    phone_number: str = Field(description="The new phone number that user wants to update.")

    # define an inner class named "Config" within a Pydantic model.
    # This class sets the "json_schema_extra" dict, which provides an example of how the model should look in JSON format.
    # This example can be used by documentation tools or API generators to illustrate 
    # what a valid input for this model might look like, helping developers and users 
    # understand the expected data structure.
    # If you do not need to customize the model's behavior or schema, you can omit the Config class entirely
    # , and the model will still function correctly.
    # LangChain sends the tool schema to the LLM (Claude, GPT-4, etc.), so it can reason about:
    # - When to call the tool
    # - How to fill out arguments
    # - What the tool is for
    class Config:
        json_schema_extra = {
            "example": {
                "email": "abc@domain.com",
                "address": "123 Main St, City, Country",
                "phone_number": "+1234567890",
            }
        }
