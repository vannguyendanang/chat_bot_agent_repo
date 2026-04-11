from app.constants import Constants
import logging, traceback
from langchain.tools import tool

log = logging.getLogger(f"{Constants.APP_LOGGER}.{__name__}")

class HumanEscalation:
    def get_tool(self) -> str:
        @tool
        def escalate_to_human(reason: str, transactionId: str):
            """
                A tool to escalate the question to a human instead of being solved by an agent
            """
            log.info(f"{transactionId} needs to be reviewed for a dispute transaction with reason {reason}")
            return "A live agent will verify your request within 24 hours."
        return escalate_to_human