from pydantic import BaseModel


# This is a Pydantic model used as a tool to signal that a specialized assistant
# has either completed its task or needs to escalate back to main assistant.
# This class has 2 fields: cancel and reason.
# The language model (LLM) or agent could, in principle, decide to call the tool
# with cancel=False if it determines escalation is needed (for example, if the user asks for something outside the sub-assistant's scope).
# Example the message that sub agent generates this tool definition (when user changes their mind)
# AIMessage(content='', additional_kwargs={'tool_calls': [{'id': 'call_sRN6zfG7MwsnhCCBeOLL4Z41', 'function': {'arguments': 
# '{"reason":"The user wants to dispute a transaction, which requires assistance beyond bank account updates or balance inquiries."}', 'name': 'CompleteOrEscalate'}, 'type': 'function'}]
class CompleteOrEscalate(BaseModel):
    """A tool to mark the current task as completed and/or to escalate control of the dialog to the main assistant,
    who can re-route the dialog based on the user's needs."""

    cancel: bool = True
    reason: str

    # class Config is used to provide extra configuration by adding examples to the generated documentation
    class Config:
        json_schema_extra = {
            # user canceled the task so we need to exit this sub-agent
            "example": {
                "cancel": True,
                "reason": "User changed their mind about the current task.",
            },
            # the task has been finished so we need to exit this sub-agent
            "example 2": {
                "cancel": True,
                "reason": "I have fully completed the task.",
            },
            # the task is not finished yet, so we need to escalate the dialog to the main assistant
            "example 3": {
                "cancel": False,
                "reason": "I need to search the user's emails or calendar for more information.",
            },
        }