from typing import TypedDict, Annotated, Literal, Optional
from langgraph.graph.message import add_messages, AnyMessage
# from utility import Utility


# If right = "book_hotel" → push to stack
# If right = "pop" → remove last task
# If right = None → leave unchanged
# Example input:
# left: ["assistant"], right: ["book_hotel" 
# --> output: ["assistant", "book_hotel"]
# Example input:
# left: ["assistant", "book_hotel"], right: "pop"
# --> output: ["assistant"]
# @staticmethod
def update_dialog_stack(left: list[str], right: Optional[str]) -> list[str]:
    """Push or pop the state."""
    if right is None:
        return left
    if right == "pop":
        # return elements from the begining up to, but not including, the last element
        return left[:-1]
    return left + [right]

class State(TypedDict):
       
    # Annotated[<actual_type>, <metadata_or_rule>]
    messages: Annotated[list[AnyMessage], add_messages]
    user_info: str
    # dialog_state is a list of strings AND each string must be node name
    # Whenever this field is updated by a node, use update_dialog_stack to handle how it should change
    dialog_state: Annotated[
        list[
            Literal[
                "primary_agent",
                "bank_account_agent",
                "account_transaction_agent"
                # "pop" 
            ]
        ],
        # LangGraph will call this function with suitable input params based on 
        # the field's annotation to update the dialog_state field
        # Utility.update_dialog_stack,
        update_dialog_stack,
    ]
    error: str

