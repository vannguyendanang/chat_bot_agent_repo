from pydantic import BaseModel
from pydantic import Field

# Create a Pydantic model named "ToBankAccountAssistant" that inherits from pydantic.BaseModel.
# This tool needs to specify what inputs it accepts and their types. Pydantic handles this.
# If the LLM generates an invalid call like {"location": 123}, Pydantic throws a validation error. 
# Without Pydantic, you’d need to write custom code for every tool to check and clean up inputs.
class ToBankAccountBalance(BaseModel):
    """A tool to delegate bank account balance tasks to a specialized assistant."""

