import os
os.environ["LANGSMITH_TRACING_V2"] = "true"
os.environ["LANGCHAIN_DEBUG"] = "true"          # prints detailed logs
# os.environ["LANGSMITH_API_KEY"] = getpass.getpass()


import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from graph.graph import Graph 
from app.utility import Utility

from langchain_core.messages import ToolMessage
def main():
    thread_id = "test_26"  # Use a fixed thread ID for preserve old messages 
    
    # import logging
    # logging.basicConfig(level=logging.INFO)  # or DEBUG
    from langchain_core.callbacks import BaseCallbackHandler

    # These three methods are called when a tool, chain, or LLM raises an exception.
    # It will only fire if your tools raise (e.g., raise ToolException(...)).
    class PrintErrors(BaseCallbackHandler):
        def on_tool_error(self, error, **kw):
            print("\n[TOOL ERROR]\n", error, "\n")
        def on_chain_error(self, error, **kw):
            print("\n[CHAIN ERROR]\n", error, "\n")
        def on_llm_error(self, error, **kw):
            print("\n[LLM ERROR]\n", error, "\n")

    callbacks = [PrintErrors()]
    config = {
        "configurable": {
            "account_num": "3423346",
            # Checkpoints are accessed by thread_id
            "thread_id": thread_id,
        }, 
        "callbacks": callbacks
    }

    myGraph = Graph()
    myGraph.build_graph()
    myCompiledGraph = myGraph.compile_graph()

    _printed = set()
    # question = "I want to check my transactions from Feb 01 2025 to Apr 30 2025"
    # question = "Yes, please"
    # question = "Yes, just the email"
    # question = "I want to update my bank account information"

    # question = "I want to dispute my transaction"
    # question = "The date time is May 4th 2025 1:00:30 PM, receiver's first name Watson and last name is Castillo. The transfered amount is $345"    
    # question = "I want to dispute my transaction. The date time is May 4th 2025  1:00:30 PM, receiver's first name Watson and last name is Castillo. The transfered amount is $345"
    question = "I want to dispute my transaction. The date time is Mar 27th 2026  09:00:30 AM, receiver's first name Bennet and last name is Sanders. The transfered amount is $611"

    events = myCompiledGraph.stream(
        {"messages": ("user", question)}, config, 
        stream_mode="values"
        # stream_mode="updates"
    )

    # each event represents a step in the conversation flow (like user messages, AI responses, or tool calls)
    for event in events:
        Utility._print_event(event, _printed)
        # Utility.print_updates(event) # Use this for debugging
        # Utility.print_updates_msg(event, transcript)
        
    # get the current state of the conversation
    snapshot = myCompiledGraph.get_state(config)

    while snapshot.next:
    # while snapshot.get("next"):
        # We have an interrupt! The agent is trying to use a tool, and the user can approve or deny it
        # Note: This code is all outside of your graph. Typically, you would stream the output to a UI.
        # Then, you would have the frontend trigger a new run via an API call when the user has provided input.
        try:
            user_input = input(
                "Do you approve of the above actions? Type 'y' to continue;"
                " otherwise, explain your requested changed.\n\n"
            )
        # If input() fails (e.g., non-interactive environment), it defaults to 'y'.
        except:
            user_input = "y"
        
        if user_input.strip() == "y":
            result = myCompiledGraph.invoke(
                None, 
                config
            )

        else:
            # Satisfy the tool invocation by
            # providing instructions on the requested changes / change of mind
            # It manually constructs a ToolMessage that tells the graph the tool call was denied.
            # tool_call_id identifies the specific tool call to reject.
            # The assistant is instructed to continue the conversation with user's reasoning in mind.
            result = myCompiledGraph.invoke(
                {
                    "messages": [
                        ToolMessage(
                            tool_call_id=event["messages"][-1].tool_calls[0]["id"],
                            content=f"API call denied by user. Reasoning: '{user_input}'. Continue assisting, accounting for the user's input.",
                        )
                    ]
                },
                config,
            )
        print()
        print(f"Output of \"Do you approve of the above actions? Type 'y' to continue;\n"
                f" otherwise, explain your requested changed.:\" {user_input}")
        # ✅ Print assistant messages/tool calls from resumed execution
        # We set None bc we are not giving any new user input, we just want to see 
        # the tool result (e.g., the tool output) and the assistant message that 
        # reacts to the tool’s output
        new_events = myCompiledGraph.stream(None, config, stream_mode="values")
        for event in new_events:
            Utility._print_event(event, _printed)

        # If the updated snapshot.next is still a node: loop continues.
        # Else, the graph has reached the END node
        snapshot = myCompiledGraph.get_state(config)
        # snapshot = dict(part_4_graph.get_state(config))
    
    myGraph.close()

if __name__ == "__main__":
    main()