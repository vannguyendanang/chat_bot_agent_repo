from dotenv import load_dotenv
load_dotenv()  # loads .env from the current working directory or parents
# import os
# print("Tracing:", os.getenv("LANGCHAIN_TRACING_V2"))
# print("Project:", os.getenv("LANGCHAIN_PROJECT"))
from app.constants import Constants
import logging, sys
from tools.user_login import UserLogin



def setup_logging():
    # Create a logger object named "bankbot"
    log = logging.getLogger(Constants.APP_LOGGER)
    # accept DEBUG on this logger
    # set the log level to DEBUG
    log.setLevel(logging.DEBUG)
    # If this logger currently has no handlers attached to it.                #  
    if not log.handlers:                        # avoid double handlers on reload (e.g., dev server restarts)
        h = logging.StreamHandler(sys.stdout)   # Creates a handler that writes log output to standard output (terminal).
        
        # Print out the DEBUG log level
        h.setLevel(logging.DEBUG)               
        # set log message's format
        # i.e. 12:01:22 INFO [bankbot] App started
        # 11:05:14 INFO [bankbot.graph.graph:get_user_info] Setup user info
        h.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s:%(funcName)s] %(message)s",
            datefmt="%H:%M:%S",
        ))
        log.addHandler(h)
        # just print log message of bankbot logs, not print Uvicorn's log message to avoid duplication
        log.propagate = False                   
    return log


app_log = setup_logging()
app_log.info("App logging initialized")
# print("Handlers:", app_log.handlers)
from fastapi import FastAPI
from graph.graph import Graph
from pydantic import BaseModel
from contextlib import asynccontextmanager
from langchain_core.messages import ToolMessage
from app.utility import Utility
from typing import Dict, Any
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

# Anything defined at the top level of a Python file (outside a function/class) becomes a module-level variable.
# So below variables will not be reseted across different requests
# Create an empty dict named PENDING in which key is session_id and value is tool_call_id
PENDING: dict[str, str] = {}   # session_id -> pending tool_call_id
MsgIdStorage: dict[str, set[str]] = {} # session_id -> list of message ids

class SendReq(BaseModel):
    session_id: str
    account_number: str
    # user message
    text: str

class UserLoginReq(BaseModel):
    account_number: str
    password: str

# the _role func returns either a str or None if no role can be determined
def _role(m: Any) -> str | None:
    # If the message is a dict, read role or type.
    if isinstance(m, dict):
        return m.get("role") or m.get("type")
    # reading attributes on LangChain message objects
    # For ex: m = HumanMessage(content="Update my address") 
    # --> getattr(m, "type", None)  → "human"
    # role can be tool/human/ai
    return getattr(m, "type", None) or getattr(m, "role", None)

def _content(m: Any) -> str:
    # If the event gave you a dict (can happen with "updates" mode)
    if isinstance(m, dict):
        # if m is a dict then return its content or empty
        return str(m.get("content", ""))

    # LangChain message objects (AIMessage, HumanMessage, ToolMessage, etc.)
    c = getattr(m, "content", "")
    if c is None:
        return ""
    # Example of c:
    # c = [
    #     {"type": "text", "text": "I can update your address."},
    #     {"type": "text", "text": "This action requires your approval."}
    # ]
    if isinstance(c, list):
        # Some messages use content blocks (list[dict])
        parts = []
        for blk in c:
            if isinstance(blk, dict):
                parts.append(blk.get("text") or blk.get("content") or "")
            else:
                parts.append(str(blk))
        return "\n".join(p for p in parts if p)
    return str(c)

# Declares a lifespan context manager; FastAPI calls this on startup and shutdown.
@asynccontextmanager
async def lifespan(app: FastAPI):
# def _startup():
    g = Graph()
    g.build_graph()
    # Compiles the graph and stores it on app.state so endpoints can reuse it.
    # cg is an attribute name we create for object app.state
    # app.state is a standard FastAPI place for app-wide shared objects.
    app.state.cg = g.compile_graph()

    # Everything before yield runs on startup.
    # Everything after yield runs on shutdown.
    yield
    # optional cleanup on shutdown
    cg = getattr(app.state, "cg", None)
    # close the compiled graph if it supports async close.
    # Closing this object requires asynchronous operations (cancelling background tasks, flushing async queues,..)
    if cg and hasattr(cg, "aclose"):
        print("Compile graph supports async")
        await cg.aclose()
    else:
        print("Compile graph does not support async")
    # placeholder for other cleanup: close DB pools, etc. if the graph holds them

# Creates the FastAPI app and registers the lifespan handler.
app = FastAPI(lifespan=lifespan)    

# A helper func returns a dict where keys are strings and values can be of any type
def send_turn(question: str, session_id: str, compiled, config) -> Dict[str, Any]:
    """
    - Streams events to terminal (your Utility._print_event still used)
    - Returns the latest assistant text for the UI
    - If there's a pending approval and the user typed yes/no, resume accordingly
    """
    # If we have a pending approval for this session and user typed yes/no
    pending = PENDING.get(session_id)
    if pending:
        # print("Value of PENDING \n", PENDING)
        text = question.strip().lower()
        if text in {"y", "yes"}:
            # approve the tool call
            final = compiled.invoke(None, config)  # resumes the paused run
        else:
            # deny: send a ToolMessage linked to the pending tool_call_id
            tm = ToolMessage(
                tool_call_id=pending,
                content=f"API call denied by user. Reason: '{question}'. Continue the conversation."
            )

            # print the ToolMessage to the terminal right away
            # try:
            #     print("User's denial infor:", tm.pretty_repr(html=False))     # nicest formatting if available
            # except Exception:
            #     print(f"[tool] id={tm.tool_call_id}\n{tm.content}")

            # feed a tool message with denial message back into the graph
            final = compiled.invoke({"messages": [tm]}, config)
            # Satisfy the tool invocation by
            # providing instructions on the requested changes / change of mind
            # It manually constructs a ToolMessage that tells the graph the tool call was denied.
            # tool_call_id identifies the specific tool call to reject.
            # The assistant is instructed to continue the conversation with user's reasoning in mind.
            # result = compiled.invoke(
            #     {
            #         "messages": [
            #             ToolMessage(
            #                 tool_call_id=event["messages"][-1].tool_calls[0]["id"],
            #                 content=f"API call denied by user. Reasoning: '{user_input}'. Continue assisting, accounting for the user's input.",
            #             )
            #         ]
            #     },
            #     config,
            # )            
        # clear the pending flag for this session
        PENDING.pop(session_id, None)

        # collect last assistant message for UI (also print to terminal)
        last_ai = ""
        # stream_mode = "values" means each event will be like below:
        # Event 1:
        # ev["messages"] = [HumanMessage("hi")]
        # Event 2:
        # ev["messages"] = [HumanMessage("hi"), AIMessage("Hello!")]
        # Event 3:
        # ev["messages"] = [HumanMessage("hi"), AIMessage("Hello!"), AIMessage("How can I help?")]
        # get the printed message id, use default value if it is None
        _printed = MsgIdStorage.get(session_id, set())
        for ev in compiled.stream(None, config, stream_mode="values"):
            # Print the last message of ev in terminal
            Utility._print_event(ev, _printed)
            # For each langchain message object like HumanMessage, AIMessage,...
            # Extract the last AI message to return to client
            for m in ev.get("messages", []):
                if _role(m) in ("ai", "assistant"):
                    last_ai = _content(m)
        MsgIdStorage[session_id] = _printed
        return {"reply": last_ai, "awaiting_approval": False}

    # ---- Normal user turn
    state = {"messages": [("user", question)]}
    last_ai = ""
    # _printed: set[str] = set()
    _printed = MsgIdStorage.get(session_id, set())
    count = 0
    for ev in compiled.stream(state, config, stream_mode="values"):
        # Print the last message of ev in terminal
        Utility._print_event(ev, _printed)

        # UI: keep the most recent assistant text
        for m in ev.get("messages", []):
            if _role(m) in ("ai", "assistant"):
                last_ai = _content(m)

        count += 1
    print(f"There are {count} events produced")
    # update the dict MsgIdStorage
    MsgIdStorage[session_id] = _printed
    # After the stream, check if the graph paused for a tool approval
    snap = compiled.get_state(config)
    awaiting = bool(snap.next)        # True => the graph is interrupted (awaiting tool approval)

    # If awaiting approval, remember the tool_call_id so the next user "yes/no" can resume
    if awaiting:
        # Find the last AI message that contains tool_calls
        tool_ai = next(
            (m for m in reversed(snap.values["messages"])
             if hasattr(m, "tool_calls") and m.tool_calls),
            None
        )
        if tool_ai:
            PENDING[session_id] = tool_ai.tool_calls[0]["id"]

    return {"reply": last_ai, "awaiting_approval": awaiting}

# define endpoint "send" which receives JSON from UI and returns JSON back
@app.post("/send")
def send(req: SendReq):
    state = {"messages": [("user", req.text)]}
    config = {"configurable": {"thread_id": req.session_id, "account_num": req.account_number},
                "run_name": f"/send {req.session_id}",      # shows as the run title
                "tags": ["ui", "bankbot"],                  # lets you filter/group
                "metadata": {"session_id": req.session_id}, # extra context
             }
    print("State at send ", state)
    # print("Config at send ", config)

    out = send_turn(req.text, req.session_id, app.state.cg, config)
    return out

# define endpoint "login"
@app.post("/login")
def login(req: UserLoginReq):
    userLogin = UserLogin()
    # print("input acc ", req.account_number)
    # print("input pass ", req.password)
    success = userLogin.check_login(req.account_number, req.password)
    return {"success": success}

# set the redirect from "/" to "/login.html" page
@app.get("/")
def root():
    return RedirectResponse(url="/login.html")

# Serve / -> ui/index.html and any other static assets in ui/
app.mount("/", StaticFiles(directory="ui", html=True), name="ui")

if __name__ == "__main__":
    import os, uvicorn
    port = int(os.environ.get("PORT", 8080))  # Cloud Run sets $PORT
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")