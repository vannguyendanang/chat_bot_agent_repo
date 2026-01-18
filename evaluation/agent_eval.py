from graph.graph import Graph 
from app.utility import Utility
from langchain_core.messages import ToolMessage
from langchain_core.callbacks import BaseCallbackHandler
from ragas.integrations.langgraph import convert_to_ragas_messages
from ragas.metrics import ToolCallAccuracy, AgentGoalAccuracyWithReference 
from ragas.dataset_schema import MultiTurnSample, EvaluationDataset
from ragas.llms import LangchainLLMWrapper
import ragas.messages as r
from ragas import aevaluate
import os
import pandas as pd
from pathlib import Path
import asyncio
import numpy as np
from models.model import Model
import sys

# check whether the program is running on Windows
if sys.platform.startswith("win"):
    # set how asyncio creates and manges event loops
    # This affects asyncio.run()
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

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


myGraph = Graph()
myGraph.build_graph()
myCompiledGraph = myGraph.compile_graph()


# question = "I want to check my transactions from Feb 01 2025 to Apr 30 2025"
# question = "Yes, please"
# question = "Yes, just the email"
# question = "I want to update my bank account information"

# question = "I want to dispute my transaction"
# question = "The date time is May 4th 2025 1:00:30 PM, receiver's first name Watson and last name is Castillo. The transfered amount is $345"    
# question = "I want to dispute my transaction. The date time is Jun 1st 2025 15:45:30, receiver's first name Brooks and last name is Alvarez. The transfered amount is $120"    

# set data type will give O(1) for checking time, faster than list or tuple O(n)
ROUTING_TOOLS = {"ToGetListTransaction", "ToDisputeTransaction", "ToBankAccountAssistant", "CompleteOrEscalate"}

# remove tool calls and ToolMessage of routing tools from ragas messages
# ragas messages before filtering
    # [HumanMessage(content='My phone needs to be changed to a new one, its numbers are 8286354369', metadata=None, type='human'), 
    # AIMessage(content='', metadata=None, type='ai', tool_calls=[ToolCall(name='ToBankAccountAssistant', args={'email': '', 'address': '', 'phone_number': '8286354369'})]), 
    # ToolMessage(content="The assistant is now the Bank Account Assistant. Reflect on ...the assistant.", metadata=None, type='tool'), 
    # AIMessage(content='', metadata=None, type='ai', tool_calls=[ToolCall(name='update_bank_account', args={'account_number': '3423346', 'phone_number': '8286354369'})]), 
    # ToolMessage(content='Bank account updated to 3423346', metadata=None, type='tool'), 
    # AIMessage(content='Your phone number has been updated to 8286354369 for your bank account. .......hanges, please let me know!', metadata=None, type='ai', tool_calls=[])]
# ragas messages after filtering
    # [HumanMessage(content='My phone needs to be changed to a new one, its numbers are 8286354369', metadata=None, type='human'), 
    # AIMessage(content='', metadata=None, type='ai', tool_calls=[ToolCall(name='update_bank_account', args={'account_number': '3423346', 'phone_number': '8286354369'})]), 
    # ToolMessage(content='Bank account updated to 3423346', metadata=None, type='tool'), 
    # AIMessage(content='Your phone number has been updated to 8286354369 for your bank ... know!', metadata=None, type='ai', tool_calls=[])]
def filter_out_routing_tools_and_tool_message(ragas_messages):
    cleaned = []
    prev = None
    for msg in ragas_messages:
        msg_type = getattr(msg, "type", None)

        # 1) If AIMessage: filter out routing tool calls
        if msg_type == "ai":
            tool_calls = getattr(msg, "tool_calls", None) or []
            if tool_calls:
                kept = [tc for tc in tool_calls if tc.name not in ROUTING_TOOLS]
                msg.tool_calls = kept #if len(kept) > 0 else None
            # else: 
            #     msg.tool_calls = None

            # if prev is not None and getattr(prev, "type", None) == "tool":
            #     msg.tool_calls = None

            # Drop empty AI messages created by filtering
            is_empty_ai = (getattr(msg, "content", "") == "" and not getattr(msg, "tool_calls", None))
            if is_empty_ai:
                prev = msg
                continue

            cleaned.append(msg)
            prev = msg
            continue

        # 2) If ToolMessage: keep only if it immediately follows an AIMessage with tool_calls
        if msg_type == "tool":
            if prev is None:
                continue
            prev_type = getattr(prev, "type", None)
            prev_tool_calls = getattr(prev, "tool_calls", None) or []
            if prev_type != "ai" or len(prev_tool_calls) == 0:
                # orphan tool message -> drop
                continue

            cleaned.append(msg)
            prev = msg
            continue

        # 3) Human or other messages: keep
        cleaned.append(msg)
        prev = msg    
    return cleaned

def constructSamples(question_id, question, tool_name, tool_args_name, tool_args_value, user_goal):

    thread_id = question_id
    config = {
        "configurable": {
            "account_num": "3423346",
            # Checkpoints are accessed by thread_id
            "thread_id": thread_id,
        }, 
        "callbacks": callbacks
    }
    # run the graph
    results = myCompiledGraph.invoke({"messages": ("user", question)}, config)
    
    # get the current state of the conversation
    snapshot = myCompiledGraph.get_state(config)

    while snapshot.next:
    
        results = myCompiledGraph.invoke(
            None, 
            config
        )

        # If the updated snapshot.next is still a node: loop continues.
        # Else, the graph has reached the END node
        snapshot = myCompiledGraph.get_state(config)

    # print("result final ", results["messages"])

    ragas_trace = convert_to_ragas_messages(results["messages"])
    # list of ragas messages
    print("rages trace before filter:")
    print(ragas_trace)
    ragas_trace = filter_out_routing_tools_and_tool_message(ragas_trace)

    print("=============================")
    print("rages trace after filter:")
    print(ragas_trace)
    argDict = dict(zip(tool_args_name, tool_args_value))
    print("arg Dict ", argDict)
    print("tool name ", tool_name)

    multiTurnSample = MultiTurnSample(
        user_input=ragas_trace,
        reference_tool_calls=[
            r.ToolCall(name=tool_name, args=argDict)
        ]
    )

    multiTurnSampleGoal = MultiTurnSample(
        user_input = ragas_trace,
        reference = user_goal
    )
    return multiTurnSample, multiTurnSampleGoal
# define async function
async def agentEval(df):
    arrScore = []
    arrScoreGoal = []
    modelObj = Model()
    llm = modelObj.get_llm()
    scorer = ToolCallAccuracy()
    scorerGoal = AgentGoalAccuracyWithReference()
    evaluator_llm = LangchainLLMWrapper(llm)
    for _, row in df.iterrows():
        sampleElmt, sampleElmtGoal = constructSamples(
            row["id"], 
            row["question"],
            row["expected_tool_call"].strip(), 
            [param.strip() for param in str(row["param_name"]).split(";")],
            [vals.strip() for vals in str(row["param_value"]).split(";")],
            row["user_goal"]
        )

        score = await scorer.multi_turn_ascore(sampleElmt)
        print(f"Tool call accuracy for {row['id']}: {score}")
        arrScore.append(float(score))

        scorerGoal.llm = evaluator_llm
        scoreGoal = await scorerGoal.multi_turn_ascore(sampleElmtGoal)
        print(f"Agent goal accuracy for {row['id']}: {scoreGoal}")
        arrScoreGoal.append(float(scoreGoal))
    # dataset = EvaluationDataset(samples)
    # tool_accuracy_scorer = ToolCallAccuracy()
    # score = await aevaluate(
    #     dataset=dataset,
    #     metrics=[tool_accuracy_scorer]
    # )
    return np.array(arrScore), np.array(arrScoreGoal)

# define async caller
async def main():
    INPUT_CSV = "agent_evaluation_tcs.csv"
    docs_dir = Path(os.getenv("DOCS_DIR", Path(__file__).resolve().parent.parent / "documents"))
    df = pd.read_csv(str(docs_dir/INPUT_CSV))

    try:
        toolCallAcc, agentGoalAccuracy = await agentEval(df)
        print("Tool call accuracy for whole data sample ", toolCallAcc.mean())
        print("Agent goal accuracy for whole data sample ", agentGoalAccuracy.mean())
    finally:
        myGraph.close()

if __name__ == "__main__":
    # run the async caller
    asyncio.run(main())

