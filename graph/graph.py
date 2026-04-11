from langgraph.graph import StateGraph, END, START
# from langchain.chat_models import ChatOpenAI
# from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable
# from langchain_core.messages import AIMessage, HumanMessage
# from langchain_openai import AzureChatOpenAI
import os
from tools.pdf_tool import PDFTool
from tools.support_phone import SupportPhone
from tools.account_tool import AccountTool
from tools.transaction_tool import TransactionTool
from tools.escalate_to_human import HumanEscalation
from models.assistant import Assistant
from app.utility import Utility
from tool_definition.to_bank_account_update import ToBankAccountUpdate
from tool_definition.to_bank_account_balance import ToBankAccountBalance
from tool_definition.to_get_list_transaction import ToGetListTransaction
from tool_definition.to_dispute_transaction import ToDisputeTransaction
from tool_definition.complete_or_escalate import CompleteOrEscalate
from tool_definition.to_escalate_to_human import ToEscalateToHuman
from tool_definition.to_check_transaction_exist import ToCheckTransactionExist
from models.prompts import Prompts
from graph.routing import Routing 
from graph.state import State
from models.model import Model 
# from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.mysql.pymysql import PyMySQLSaver
import pymysql
from app.constants import Constants
from pathlib import Path

import logging, traceback
# from app.server import APP_LOGGER  # or define a constant in one place
log = logging.getLogger(f"{Constants.APP_LOGGER}.{__name__}")

# from langchain.agents import create_react_agent, AgentExecutor

# from IPython.display import Image, display

class Graph:
    
    def make_conn(self):
        db_user = os.environ["DB_USER"]
        db_pass = os.environ["DB_PASS"]
        db_name = os.environ["DB_NAME"]

        icn = os.environ.get("INSTANCE_CONNECTION_NAME")  # e.g. "triple-router-472320-d0:us-central1:bankbot-mysql"
        if icn:
            # Cloud Run + Cloud SQL unix socket
            unix_socket = f"/cloudsql/{icn}"
            return pymysql.connect(user=db_user, password=db_pass, db=db_name, unix_socket=unix_socket)

        # Fallback for local/dev (TCP)
        db_host = os.environ.get("DB_HOST", "127.0.0.1")
        db_port = int(os.environ.get("DB_PORT", "3306"))
        return pymysql.connect(user=db_user, password=db_pass, db=db_name, host=db_host, port=db_port)

    def __init__(self):
        self.builder = StateGraph(State)
        self.conn = self.make_conn()
        self.checkpointer = PyMySQLSaver(self.conn)  # real saver, not a context manager
        self.checkpointer.setup()  # safe to call each start

    def close(self):
        if self.conn:
            self.conn.close()

    # Keep the state parameter. LangGraph calls each node with (state, config)
    def get_user_info(self, _state: State, config: RunnableConfig) -> dict:
        log.info("Setup user info")
        return {"user_info": Utility.get_user_account_number(config)}

    def chain_prompt_and_tools(self) -> None:
        log.info("Chain the prompt and tools together.")
        """Chain the prompt and tools together."""

        docs_dir = Path(os.getenv("DOCS_DIR", Path(__file__).resolve().parent.parent / "documents"))

        
        filenames = [
        "ALLIANCE Banking Business Process.pdf",
        "ALLIANCE Banking General Info&Policy.pdf",
        "ALLIANCE Technical Issues Solving.pdf",
        ]
        pdf_files = [str(docs_dir / name) for name in filenames]

        # pdf_files = [
        #     "../documents/ALLIANCE Banking Business Process.pdf",
        #     "../documents/ALLIANCE Banking General Info&Policy.pdf",
        #     "../documents/ALLIANCE Technical Issues Solving.pdf"
        # ]
        policy_tool_obj = PDFTool(pdf_files)
        # Load tools
        policy_tool = policy_tool_obj.get_tool()

        phone_support_obj = SupportPhone()
        phone_support_tool = phone_support_obj.get_tool()  

        bank_tool_obj = AccountTool()
        update_bank_account_tool, account_balance_tool = bank_tool_obj.get_tool()
        bank_tool = [update_bank_account_tool, account_balance_tool]

        transaction_obj = TransactionTool()
        escalation_obj = HumanEscalation()
        escalation_to_human_tool = escalation_obj.get_tool()

        list_transaction_tool, check_trans_exist, dispute_transaction_tool = transaction_obj.get_tool()
        transaction_tool = [policy_tool, list_transaction_tool, check_trans_exist, dispute_transaction_tool, escalation_to_human_tool]

        model = Model()
        llm = model.get_llm()

        self.primary_assistant_tool = [policy_tool, phone_support_tool]
            
        # The type "Runnable" suggests that agent is a runnable object that can be invoked with inputs.
        self.primary_agent: Runnable = Prompts.get_primary_prompt() | llm.bind_tools(self.primary_assistant_tool + 
                # each of these classes represents a tool that the primary assistant can use to delegate specific tasks
                # By extending the tool list in this way, the assistant gains the ability to route user requests to the specialized workflow.                                          
                [ToBankAccountBalance, ToBankAccountUpdate, ToGetListTransaction, ToDisputeTransaction, ToEscalateToHuman, ToCheckTransactionExist])

        # set sensitive tools for bank account agent
        self.bank_account_sensitive_tools = [update_bank_account_tool]
        self.bank_account_safe_tools = [account_balance_tool]

        # Chain that connects the prompt and tools with the LLM
        self.bank_account_runnable = Prompts.get_bank_account_prompt() | llm.bind_tools(
            bank_tool + [CompleteOrEscalate]
        )

        self.transaction_sensitive_tools = [dispute_transaction_tool]
        self.transaction_safe_tools = [list_transaction_tool, check_trans_exist, policy_tool, escalation_to_human_tool]
        self.account_transaction_runnable = Prompts.get_transaction_prompt() | llm.bind_tools(
            transaction_tool + [CompleteOrEscalate]
        )

        # --- DEBUG: print transaction prompt ---
        # result = Prompts.get_transaction_prompt().invoke({"messages": [], "user_info": "3423346"})
        # print("=== TRANSACTION PROMPT ===")
        # print(result.messages[0].content)
        # print("==========================\n")
        # --- END DEBUG ---

        self.safe_tools = [account_balance_tool, list_transaction_tool, check_trans_exist, policy_tool, escalation_to_human_tool]


    
    def build_graph(self):
        log.info("Build the graph with nodes and edges.")
        """Build the graph with nodes and edges."""

        # define a list of tools, which ones are safe tools and which ones are sentitive tools and then connect prompt and tools for each agents (primary, account, transaction agent)
        self.chain_prompt_and_tools()

        route = Routing(self.safe_tools)
        # Build graph
        self.builder.add_node("user_info", self.get_user_info)
        self.builder.add_node("primary_agent", Assistant(self.primary_agent))
        self.builder.add_edge(START, "user_info")

        # First, primary agent will generate a tool call including tool name and tool id based on its configured tools
        # Later in during runtime, entry_node(state) runs and returns a ToolMessage(content + tool_call_id) + new dialog_state
        # We will use this node to transfer a ToolMessage and tool_id to the specialized agent
        self.builder.add_node(
            "enter_bank_account",
            # return a func "entry_node" and stored internally to be used later during runtime
            Utility.create_entry_node("Bank Account Assistant", "bank_account_agent"),
        )

        self.builder.add_node(
            "enter_transaction",
            Utility.create_entry_node("Transaction Assistant", "account_transaction_agent")
        )
        # The "bank_account" node is used to handle below tasks:
        # - Handles the conversation with the user about updating bank account or retrieving account balance.
        # - Calls the appropriate tools to search for account information, update bank account as needed.
        # - Decides, based on the user's input and tool results, whether to continue the bank accound mode, escalate back to the main assistant, or finish the workflow.
        self.builder.add_node("bank_account_agent", Assistant(self.bank_account_runnable))

        self.builder.add_node("account_transaction_agent", Assistant(self.account_transaction_runnable))

        # connect from the "enter_bank_account" node to the "bank_account" node
        # "enter_bank_account" node acts as a transition or entry point that prepares the workflow 
        # for the specialized bank assistant. It does 2 things:
        # 1. Adds a system/tool message to the conversation, indicating that control is being handed off to the bank account assistant (without telling the user explicitly).
        # 2. Updates the dialog state to reflect that the workflow is now in the bank account context.
        self.builder.add_edge("enter_bank_account", "bank_account_agent")
        self.builder.add_node(
            "bank_account_sensitive_tools",
            Utility.create_tool_node_with_fallback(self.bank_account_sensitive_tools),
        )
        self.builder.add_node(
            "bank_account_safe_tools",
            Utility.create_tool_node_with_fallback(self.bank_account_safe_tools),
        )

        self.builder.add_edge("enter_transaction", "account_transaction_agent")
        self.builder.add_node(
            "transaction_sensitive_tools", Utility.create_tool_node_with_fallback(self.transaction_sensitive_tools)
        )
        self.builder.add_node(
            "transaction_safe_tools", Utility.create_tool_node_with_fallback(self.transaction_safe_tools)
        )

        # Adds a tool-handling node named "primary_assistant_tools" to run primary assistant tools and fallback 
        # to the primary assistant if the tool fails.
        self.builder.add_node(
            "primary_assistant_tools", Utility.create_tool_node_with_fallback(self.primary_assistant_tool)
        )

        # The assistant can route to one of the delegated assistants,
        # directly use a tool, or directly respond to the user
        # Add Conditional Routing for the primary assistant
        # This is dynamic routing in the graph based on user intent/tool calls.
        self.builder.add_conditional_edges(
            "primary_agent",
            route.route_primary_to_sub_assistant,
            [
                "enter_bank_account",
                "enter_transaction",
                "primary_assistant_tools",
                # "phone_support_route",
                END,
            ],
        )

        # Adds a loop: once tools are used, go back to the primary assistant to continue conversation.
        self.builder.add_edge("primary_assistant_tools", "primary_agent")

        # self.builder.add_edge("phone_support_route", END)

        # Connects "user_info" node to the right workflow dynamically, based on which sub-agent is active.
        # If route_from_start_to_sub_assistant returns "bank_account_agent" then next node will be "bank_account_agent"
        self.builder.add_conditional_edges("user_info", 
                                           route.route_from_start_to_sub_assistant, 
                                           ["primary_agent", "bank_account_agent","account_transaction_agent"]
                                           )



        # back to "bank_account". The assistant can now inform the user of the outcome 
        # (e.g., "Your account has been updated"), ask if further changes are needed
        self.builder.add_edge("bank_account_sensitive_tools", "bank_account_agent")

        # after searching for account balance, the workflow moves back to "bank_account"
        # to present the result to the user.
        self.builder.add_edge("bank_account_safe_tools", "bank_account_agent")

        # After entering the "bank_account" node, the next step is determined by the
        # route_bank_account function, which checks the current state and know which node to go next.
        self.builder.add_conditional_edges(
            "bank_account_agent",
             route.route_from_bank_account_node,
            ["bank_account_safe_tools", "bank_account_sensitive_tools", "leave_skill", END],
        )

        self.builder.add_edge("transaction_sensitive_tools", "account_transaction_agent")
        self.builder.add_edge("transaction_safe_tools", "account_transaction_agent")

        self.builder.add_conditional_edges(
            "account_transaction_agent",
             route.route_from_transaction_node,
            ["transaction_safe_tools", "transaction_sensitive_tools", "leave_skill", END],
        )

        self.builder.add_node("leave_skill", Utility.pop_dialog_state)
        self.builder.add_edge("leave_skill", "primary_agent")

        return self.builder

    def compile_graph(self) -> CompiledStateGraph:
        log.info("Compile graph.")
        # Compile graph
        # memory = MemorySaver()
        # self.checkpointer.setup()
        mygraph = self.builder.compile(
            # checkpointer=memory,
            checkpointer=self.checkpointer,
            # Let the user approve or deny the use of sensitive tools
            interrupt_before=[
                "bank_account_sensitive_tools",
                "transaction_sensitive_tools",
            ],
        )
        
            
        # Get the PNG bytes from the graph
        png_bytes = mygraph.get_graph(xray=True).draw_mermaid_png()

        # # Save to file
        output_path = "graph_visualization.png"
        with open(output_path, "wb") as f:
            f.write(png_bytes)

        print(f"Graph saved to: {output_path}")

        return mygraph
