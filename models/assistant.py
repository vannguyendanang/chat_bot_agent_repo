from langchain_core.runnables import Runnable
# from langchain_core.messages import State, AIMessage
from graph.state import State

class Assistant:
    def __init__(self, runnable: Runnable):
        self.runnable = runnable

    def __call__(self, state: State):
        while True:
            result = self.runnable.invoke(state)
            if not result.tool_calls and (not result.content or 
                isinstance(result.content, list) and not result.content[0].get("text")):
                messages = state["messages"] + [("user", "Respond with a real output.")]

                # Create a new state object based on the existing state and the new values for the key "messages"
                state = {**state, "messages": messages}
            else:
                break

        # Return a dictionary with the updated messages
        # For ex: {"messages": AIMessage(content="Hello")}
        return {"messages": result}

        
