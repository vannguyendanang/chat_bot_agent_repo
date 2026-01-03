from typing import Optional, Callable
from langchain_core.messages import ToolMessage, AIMessage, HumanMessage
from langchain_core.runnables import RunnableLambda
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict
from graph.state import State
from langchain_core.runnables import RunnableConfig
import json
from langchain_core.messages import BaseMessage
from models.classifier import Classifier
from tools.support_phone import SupportPhone
class Utility:

    @staticmethod
    def handle_tool_error(payload, config: Optional[RunnableConfig] = None) -> dict:
        """
        Fallback handler for tool failures. `payload` can be either:
        - {"error": Exception, "input": <state>}  (common)
        - {"error": Exception, "inputs": <state>} (some versions)
        - or, in rare cases, just the original state (if no exception_key is used)
        """

        # 1) Unpack the wrapper to get the real state + the exception
        if isinstance(payload, dict) and "error" in payload:
            err = payload.get("error")
            state = payload.get("input") or payload.get("inputs") or {}
        else:
            err = None
            state = payload if isinstance(payload, dict) else {}

        # 2) Find the tool calls from the last AI message (if any)
        messages = state.get("messages") or []
        tool_calls = getattr(messages[-1], "tool_calls", []) if messages else []

        # 3) If we can't find tool_calls, degrade gracefully so the graph continues
        if not tool_calls:
            msg = f"Tool failed: {err!r}" if err else "A tool failed."
            return {"messages": [AIMessage(content=msg)]}

        # 4) For each tool call, return a ToolMessage with the error so the LLM can react
        content = f"Error: {repr(err)}. Please fix your inputs or try a different action."
        out = {
            "messages": [
                ToolMessage(content=content, tool_call_id=tc["id"])
                for tc in tool_calls
            ]
        }

        # Optional: bubble the text of the error into state for later inspection
        # (make `error` optional in your State: class State(TypedDict, total=False): error: str)
        if err is not None:
            out["error"] = str(err)
        return out


    @staticmethod
    def create_tool_node_with_fallback(tools: list) -> dict:
        # initialize ToolNode obj with a list of tools
        # If any tool execution raises an exception, the fallback will be triggered
        # exception_key="error": if an exception occurs, the error obj will be passed to the fallback handler 
        # under the "error" key in the input state
        # [RunnableLambda(handle_tool_error)]: create a runnable obj that wraps the handle_tool_error func
        # This allows the error handler func to be used as a fallback in the tool node pipeline.
        # --> When an error occurs, the sys can call this runnable which will execuate the handle_tool_error
        return ToolNode(tools).with_fallbacks(
            [RunnableLambda(Utility.handle_tool_error)], exception_key="error"
        )
    
    @staticmethod
    # this method runs once, when we build the graph. It's defined to configure a node
    def create_entry_node(assistant_name: str, new_dialog_state: str) -> Callable:
        # This method runs later when the graph is executed to return updates to the state
        # The graph will input state param during runtime
        def entry_node(state: State) -> dict:
            # retrieve the tool_call_id from the most recent tool call in the conversation history.
            # state["messages"] → [HumanMessage, AIMessage, AIMessage, ...]
            # Conversation
            #   └── messages[]
            #         └── last AI message
            #               └── tool_calls[]
            #                     └── tool_call
            #                           ├── id
            #                           ├── name
            #                           ├── args
            #                           └── type
            last_msg = state["messages"][-1]
            tool_call_id = last_msg.tool_calls[0]["id"]
            return {
                "messages": [
                    ToolMessage(
                        content=f"The assistant is now the {assistant_name}. Reflect on the above conversation between the host assistant and the user."
                        f" The user's intent is unsatisfied. Use the provided tools to assist the user. Remember, you are {assistant_name},"
                        " and the update, other action is not complete until after you have successfully invoked the appropriate tool."
                        " If the user changes their mind or needs help for other tasks, call the CompleteOrEscalate function to let the primary host assistant take control."
                        " Do not mention who you are - just act as the proxy for the assistant.",
                        tool_call_id=tool_call_id,
                    )
                ],
                # update the converstation's state to reflect the transition into the specialized assistant's workflow.
                "dialog_state": new_dialog_state,
            }

        return entry_node
    

    @staticmethod
    # This node will be shared for exiting all specialized assistants
    # This function ends or exits a sub-dialogue (or subgraph) in a larger conversational system and return control 
    # to the main assistant.
    # Example output:
    # {
    #     "dialog_state": "pop",
    #     "messages": [
    #         ToolMessage(
    #             content="Resuming dialog with the host assistant. Please reflect on the past conversation and assist the user as needed.",
    #             tool_call_id="tool_call_123"
    #         )
    #     ]
    # }
    def pop_dialog_state(state: State) -> dict:
        """Pop the dialog stack and return to the main assistant.

        This lets the full graph explicitly track the dialog flow and delegate control
        to specific sub-graphs.
        """
        # print("Value in the state \n", state)
        messages = []
        # whether the most recent message in the conversation history includes any tool calls
        # Example the latest tool call:
        # tool_calls=[{'name': 'CompleteOrEscalate', 'args': {'reason': 'The user wants to dispute a transaction, which requires assistance beyond bank account updates or balance inquiries.'}, 'id': 'call_sRN6zfG7MwsnhCCBeOLL4Z41', 'type': 'tool_call'}]
        if state["messages"][-1].tool_calls:
            # Note: Doesn't currently handle the edge case where the llm performs parallel tool calls
            messages.append(
                ToolMessage(
                    content="Resuming dialog with the host assistant. Please reflect on the past conversation and assist the user as needed.",
                    tool_call_id=state["messages"][-1].tool_calls[0]["id"],
                )
            )
        # return dialog_state as "pop" to end the sub-dialogue 
        return {
            "dialog_state": "pop",
            "messages": messages,
        }

    @staticmethod
    def get_user_account_number(config: RunnableConfig) -> str:
        """Function to collect user account number."""
        # Retrieve a dict named "configurable". If "configurable" is not present, it defaults to an empty dict.
        configuration = config.get("configurable", {})
        # Read value of key "passenger_id", if this key is not found or is None, raise ValueError
        acount_num = configuration.get("account_num", None)
        if not acount_num:
            raise ValueError("No account number configured.")
        return acount_num

    @staticmethod
    # Input:
    # event = {
    #     "messages": [
    #         HumanMessage(
    #             content="hi",
    #             ...,
    #             id="d02a1447-b389-4624-a08c-14fe56ec08ca"
    #         ),
    #         AIMessage(
    #             content="Hello! Welcome to ALLIANCE Bank support. How can I assist you today?",
    #             ...,
    #             id="chatcmpl-CntwgVmlOTxZ3WOUJzCZpYPFnBbk4",
    #             response_metadata={...},
    #             usage_metadata={...}
    #         )
    #     ],
    #     "user_info": "3423346",
    #     "dialog_state": []
    # }
    # event["messages"] is a list
    # Each element is a LangChain message object (HumanMessage, AIMessage)

    # Output:
    # ================================== Ai Message ==================================
    # Hello! Welcome to ALLIANCE Bank support. How can I assist you today?

    def _print_event(event: dict, _printed: set, max_length=1500):
        
        # print("Check Pure event before any processing \n", event)
        # get the current state
        current_state = event.get("dialog_state")
        # If the state exists then prints the last entry which is the most recent step or node in the flow.
        # if current_state:
        print("******************")
        print("Current dialog state: ", current_state)
            # print("Currently in dialog state: ", current_state[-1])

        # get the message field from the event.
        messages = event.get("messages")

        # if message is present
        if messages:
            # check if the message is a list, if so, selects the last message in the list
            # if isinstance(message, list):
            #     message = message[-1]
                # print("Message extracted ", message)
            for message in messages:
            # check if the message id already printed by looking it up in the _printed set
                if message.id not in _printed:
                    # If it hasn't, print a pretty HTML representation of the message
                    msg_repr = message.pretty_repr(html=True)
                    # print("Message.id ", message.id)
                    # If the presentation exceeds the specified max length then truncate the output and append an indicator
                    if len(msg_repr) > max_length:
                        msg_repr = msg_repr[:max_length] + " ... (truncated)"
                    # print message id
                    print("ID for below message: ", message.id)
                    # print the formatted message and adds the message ID to the _printed set to avoid printing duplicates in the future.
                    print(msg_repr)
                    _printed.add(message.id)

    @staticmethod
    def print_updates(step):
        # Each `step` is like: {"node_name": {"messages":[...], "error": "...", ...}}
        for node, payload in step.items():
            print(f"\n=== UPDATE from [{node}] ===")
            # show raw (optional)
            # print(json.dumps(payload, indent=2, default=str))

            # errors bubbled by fallbacks / tools
            if isinstance(payload, dict) and "error" in payload:
                print("[ERROR]", payload["error"])

            # messages (AI, Human, ToolMessage, etc.)
            msgs = payload.get("messages", []) if isinstance(payload, dict) else []
            for m in msgs:
                role = getattr(m, "type", type(m).__name__) if isinstance(m, BaseMessage) else "Unknown"
                text = getattr(m, "content", str(m))
                print(f"[{role}] {text}")

    # ---- helpers to inspect messages ----
    # from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
    # @staticmethod
    # def last_human_text(messages):
    #     for m in reversed(messages or []):
    #         if isinstance(m, HumanMessage):
    #             return (m.content or "").strip()
    #     return ""

    # @staticmethod
    # def last_ai_with_tool_calls(messages):
    #     for m in reversed(messages or []):
    #         if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
    #             return m
    #     return None
    
    # @staticmethod
    # def tool_replies_for_last_ai(messages):
    #     """
    #     Returns list of (tool_name, tool_call_id, tool_output_text) for the last AI's tool calls.
    #     """
    #     ai = Utility.last_ai_with_tool_calls(messages)
    #     if not ai:
    #         return []
    #     out = []
    #     tcs = ai.tool_calls or []
    #     for tc in tcs:
    #         tcid = tc.get("id")
    #         name = tc.get("name", "")
    #         # find matching ToolMessage
    #         tm = next(
    #             (m for m in reversed(messages or [])
    #             if isinstance(m, ToolMessage) and getattr(m, "tool_call_id", None) == tcid),
    #             None
    #         )
    #         text = (tm.content or "").strip() if tm else ""
    #         out.append((name, tcid, text))
    #     return out

    # @staticmethod
    # def print_four_things(transcript):
    #     # 1) Last HumanMessage
    #     human = Utility.last_human_text(transcript)
    #     if human:
    #         print("\n=== Last HumanMessage ===")
    #         print(human)

    #     # 2) Last AIMessage that requested tools
    #     ai = Utility.last_ai_with_tool_calls(transcript)
    #     print("\n=== Last AIMessage with tool_calls ===")
    #     if not ai:
    #         print("(none)")
    #     else:
    #         print("content:", ai.content or "")
    #         print("tool_calls:")
    #         for tc in ai.tool_calls or []:
    #             print(f"  - id={tc.get('id')} name={tc.get('name')} args={tc.get('args')}")

    #     # 3) ToolMessage(s) that replied to those tool_calls
    #     print("\n=== ToolMessage replies to last AI's tool_calls ===")
    #     replies = Utility.tool_replies_for_last_ai(transcript)
    #     if not replies:
    #         print("(none)")
    #     else:
    #         for name, tcid, text in replies:
    #             print(f"[{name}] (tool_call_id={tcid})")
    #             print(text[:800] + ("..." if len(text) > 800 else ""))  # trim long text

    #     # 4) (Optional) The original user question at the start of this turn
    #     print("\n=== First Human in this turn (optional) ===")
    #     # If you keep per-turn boundaries, print that; otherwise reuse `human`
    #     print(human or "(none)")
        
    # @staticmethod
    # def print_updates_msg(step, transcript):
    #     # for step in events:
    #     # step is like {"node_name": {"messages":[...], ...}, ...}
    #     for payload in step.values():
    #         if isinstance(payload, dict):
    #             msgs = payload.get("messages", [])
    #             if msgs:
    #                 # mimic add_messages: just append in order
    #                 transcript.extend(msgs)

    #     print("Transcript is now", len(transcript), "messages long.")
    #     print("Transacrip content ")
    #     for m in transcript:
    #         try:
    #             print(m.pretty_repr(html=False))
    #         except Exception:
    #             print(m)
            
    #     # print the four things after each step (or gate it to print only when new ToolMessages appear)
    #     Utility.print_four_things(transcript)

    # @staticmethod
    # def phone_support_route(state: State, config: RunnableConfig | None = None) -> str:
    #     """Route to phone support if the user indicates they want to speak to a human or virtual assistant can not answer user's question."""
    #     user_text = next((m.content for m in reversed(state["messages"]) if m.type=="human"), "")

    #     classifier_llm = Classifier()
    #     cat = classifier_llm.classify_query(user_text) 

    #     supPhone = SupportPhone()
    #     phone_route_tool = supPhone.get_tool()

    #     result = phone_route_tool.invoke({"category": cat})
    #     return {"messages": [AIMessage(content=result)]}

    # def last_human_text(messages):
    #     for m in reversed(messages or []):
    #         if getattr(m, "type", None) == "human":
    #             return (m.content or "").strip()
    #     return ""

    # def last_ai_with_tool_calls(messages):
    #     for m in reversed(messages or []):
    #         if getattr(m, "type", None) == "ai" and getattr(m, "tool_calls", None):
    #             return m
    #     return None

   