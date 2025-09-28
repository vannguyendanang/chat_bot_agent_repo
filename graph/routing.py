# from langchain.schema import HumanMessage, AIMessage
from langgraph.prebuilt import tools_condition
# from tools.constants import END
from tool_definition.to_bank_account_assistant import ToBankAccountAssistant
from tool_definition.to_get_list_transaction import ToGetListTransaction
from tool_definition.to_dispute_transaction import ToDisputeTransaction
from langgraph.graph import END
from graph.state import State
from typing import Literal, List, Optional
from tool_definition.complete_or_escalate import CompleteOrEscalate
from langchain_core.runnables import RunnableConfig

class Routing:
    def __init__(self, safe_tools: List):
        self.safe_tools = safe_tools
    
    # @staticmethod
    def route_primary_to_sub_assistant(self, state, config: RunnableConfig | None = None):
        """
        Routes the path from primary assistant to sub assistant based on the last message in the state.
        
        Args:
            state (dict): The current state containing messages and other data.
        
        Returns:
            str: The route to take based on the last AIMessage's tool calls.
        """

        # tools_condition: this fuction returns the last message of AIMessage type
        # and checks if it has any tool calls
        route = tools_condition(state)

        if route == END:
            return END

        # state["messages"][-1] will return the last Message object
        tool_calls = state["messages"][-1].tool_calls
        if tool_calls:
            # If the tool name matches ToFlightBookingAssistant, it routes to a node called "enter_update_flight".
            if tool_calls[0]["name"] == ToBankAccountAssistant.__name__:
                return "enter_bank_account"
            elif tool_calls[0]["name"] in (ToGetListTransaction.__name__, ToDisputeTransaction.__name__):
                return "enter_transaction"
            else: 
                return "primary_assistant_tools"
        # If no tool call is found and no valid route exists, raise an error.
        raise ValueError("Invalid route")
        # else:
        #     return "phone_support_route"
    
    # Each delegated workflow can directly respond to the user
    # When the user responds, we want to return to the currently active workflow (e.g., hotel booking, car rental)
    # Input: 
    # state = {
    #     "dialog_state": ["update_flight"],  # user is currently in flight update subgraph
    #     "messages": [...],
    # }
    # Output: "update_flight"
    # @staticmethod
    def route_from_start_to_sub_assistant(self,
        state: State, *args, **kwargs
    ) -> Literal[
        "primary_agent",
        "bank_account_agent",
        "account_transaction_agent"
        # "book_car_rental",
        # "book_hotel",
        # "book_excursion",
    ]:
        
        """If we are in a delegated state, route directly to the appropriate assistant."""
        config: Optional[RunnableConfig] = kwargs.get("config") or (args[0] if args else None)
        dialog_state = state.get("dialog_state")
        # If there's no current dialog state (i.e., no sub-agent is active), default to "primary_assistant".
        if not dialog_state:
            return "primary_agent"
        # Otherwise, return to the last (active) dialog node from the state stack.
        return dialog_state[-1]    
    
    # example input:
    # state = {
    #     "messages": [
    #         # ... previous messages ...,
    #         type("Msg", (), {
    #             "tool_calls": [
    #                 {"name": "search_flights", "id": "tool_call_1", "args": {}},
    #                 {"name": "CompleteOrEscalate", "id": "tool_call_3", "args": {"cancel": True, "reason": "User changed their mind."}}
    #             ]
    #         })()
    #     ]
    # }
    # example output: 
    # "leave_skill"
    # None = None: value may be None, and arg is OPTIONAL
    # For ex: route_from_bank_account_node() --> OK because arg is optional
    # route_from_bank_account_node(None) --> OK because arg's value is optional
    # route_from_bank_account_node(state) --> OK
    # @staticmethod
    def route_from_bank_account_node(self,
        # state: State, safe_tools: List
        state: State, config: RunnableConfig | None = None
    ):
        route = tools_condition(state)
        if route == END:
            return END
        tool_calls = state["messages"][-1].tool_calls
        # Check if any of the tool calls is a CompleteOrEscalate call
        did_cancel = any(tc["name"] == CompleteOrEscalate.__name__ for tc in tool_calls)
        if did_cancel:
            return "leave_skill"
        safe_toolnames = [t.name for t in self.safe_tools]
        # The all() func checks if the "name" field of every tc in the tool_calls list is present 
        # in the safe_toolnames list. If all tool calls are safe, we route to the safe tools node
        if all(tc["name"] in safe_toolnames for tc in tool_calls):
            return "bank_account_safe_tools"
        return "bank_account_sensitive_tools"
    
    def route_from_transaction_node(self, state: State, config: RunnableConfig | None = None):
        route = tools_condition(state)
        if route == END:
            return END
        
        tool_calls = state["messages"][-1].tool_calls
        did_cancel = any(tc["name"] == CompleteOrEscalate.__name__ for tc in tool_calls)
        if did_cancel:
            return "leave_skill"
        safe_toolnames = [t.name for t in self.safe_tools]
        if all(tc["name"] in safe_toolnames for tc in tool_calls):
            return "transaction_safe_tools"
        return "transaction_sensitive_tools"