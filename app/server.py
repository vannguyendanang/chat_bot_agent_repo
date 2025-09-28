from dotenv import load_dotenv
load_dotenv()  # loads .env from the current working directory or parents
# import os
# print("Tracing:", os.getenv("LANGCHAIN_TRACING_V2"))
# print("Project:", os.getenv("LANGCHAIN_PROJECT"))

import logging, sys

APP_LOGGER = "bankbot"  # your app-wide logger namespace

def setup_logging():
    log = logging.getLogger(APP_LOGGER)
    log.setLevel(logging.DEBUG)                 # accept DEBUG on this logger
    if not log.handlers:                        # avoid double handlers on reload
        h = logging.StreamHandler(sys.stdout)   # print to terminal
        h.setLevel(logging.DEBUG)               # don't filter DEBUG
        h.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%H:%M:%S",
        ))
        log.addHandler(h)
        log.propagate = False                   # don't pass to Uvicorn's INFO handler
    return log

app_log = setup_logging()
app_log.info("App logging initialized")

from fastapi import FastAPI
from graph.graph import Graph
from pydantic import BaseModel
from contextlib import asynccontextmanager
from langchain_core.messages import ToolMessage
from app.utility import Utility
from typing import Dict, Any
from fastapi.staticfiles import StaticFiles

# app = FastAPI()
PENDING: dict[str, str] = {}   # session_id -> pending tool_call_id

class SendReq(BaseModel):
    session_id: str
    # account_number: str
    text: str

def _role(m: Any) -> str | None:
    if isinstance(m, dict):
        return m.get("role") or m.get("type")
    return getattr(m, "type", None) or getattr(m, "role", None)

def _content(m: Any) -> str:
    # If the event gave you a dict (can happen with "updates" mode)
    if isinstance(m, dict):
        return str(m.get("content", ""))

    # LangChain message objects (AIMessage, HumanMessage, ToolMessage, etc.)
    c = getattr(m, "content", "")
    if c is None:
        return ""
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

@asynccontextmanager
async def lifespan(app: FastAPI):
# def _startup():
    g = Graph()
    g.build_graph()
    app.state.cg = g.compile_graph()
    # if you hardcode config, you can store it too:
    # app.state.default_config = {
    #     "configurable": {"account_number": "000123456789"}
    # }
    yield
    # optional cleanup on shutdown
    cg = getattr(app.state, "cg", None)
    if cg and hasattr(cg, "aclose"):
        await cg.aclose()
    # close DB pools, etc.

app = FastAPI(lifespan=lifespan)    

def send_turn(question: str, session_id: str, compiled, config) -> Dict[str, Any]:
    """
    - Streams events to terminal (your Utility._print_event still used)
    - Returns the latest assistant text for the UI
    - If there's a pending approval and the user typed yes/no, resume accordingly
    """
    # ---- If we have a pending approval for this session and user typed yes/no
    pending = PENDING.get(session_id)
    if pending:
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

            # 🔽 print the ToolMessage to the terminal right away
            try:
                print(tm.pretty_repr(html=False))     # nicest formatting if available
            except Exception:
                print(f"[tool] id={tm.tool_call_id}\n{tm.content}")
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
        for ev in compiled.stream(None, config, stream_mode="values"):
            Utility._print_event(ev, _printed=set())
            for m in ev.get("messages", []):
                if _role(m) in ("ai", "assistant"):
                    last_ai = _content(m)
        return {"reply": last_ai, "awaiting_approval": False}

    # ---- Normal user turn
    state = {"messages": [("user", question)]}
    last_ai = ""
    _printed: set[str] = set()

    for ev in compiled.stream(state, config, stream_mode="values"):
        # terminal: print everything
        Utility._print_event(ev, _printed)
        # UI: keep the most recent assistant text
        for m in ev.get("messages", []):
            if _role(m) in ("ai", "assistant"):
                last_ai = _content(m)

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

@app.post("/send")
def send(req: SendReq):
    state = {"messages": [("user", req.text)]}
    config = {"configurable": {"thread_id": req.session_id, "account_num": "3423346"},
                "run_name": f"/send {req.session_id}",      # shows as the run title
                "tags": ["ui", "bankbot"],                  # lets you filter/group
                "metadata": {"session_id": req.session_id}, # extra context
             }


    out = send_turn(req.text, req.session_id, app.state.cg, config)
    return out

# Serve / -> ui/index.html and any other static assets in ui/
app.mount("/", StaticFiles(directory="ui", html=True), name="ui")

if __name__ == "__main__":
    import os, uvicorn
    port = int(os.environ.get("PORT", 8080))  # Cloud Run sets $PORT
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")