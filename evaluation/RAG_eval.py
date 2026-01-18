# from dotenv import load_dotenv
# load_dotenv # loads .env into os.environ

import os
import pandas as pd
from datasets import Dataset, load_dataset
from pathlib import Path
from tools.huggingfaceembeddings import HuggingFaceEmbeddingsCls
from models.model import Model
from ragas import evaluate
import litellm
from ragas.llms import llm_factory
from ragas.embeddings import GoogleEmbeddings
from google import genai
from dotenv import load_dotenv
from tools.pdf_tool import PDFTool
from langchain_core.prompts import ChatPromptTemplate

# print("CWD:", os.getcwd())
# print("__file__:", Path(__file__).resolve())

load_dotenv()

from ragas.metrics import (
    # how many relevant context (relevant with grouth true answer) is retrieved out of total retrieved documents
    # LLMContextPrecisionWithReference,
    context_precision,
    # how much of reference answer is covered/supported by the retrieved contexts
    # LLMContextRecall,
    context_recall,
    # how many claims in the response that are supported by retrieved context out of total claims
    # Faithfulness,
    faithfulness,
    # how relevant a response is to user input
    # generate a set of artificial questions from reponse, then compute cosine similarity between embedding of user input 
    # and embedding of each generated questions and take the mean as the final score
    # AnswerRelevancy
    answer_relevancy
)

# from ragas.metrics.collections import context_precision
INPUT_CSV = "retrieval_layer_tcs.csv"
INPUT_JSONL = "retrieval_layer_tcs.jsonl"
OUTPUT_CSV = "retrieval_layer_test_result.csv"

docs_dir = Path(os.getenv("DOCS_DIR", Path(__file__).resolve().parent.parent / "documents"))

filenames = [
"ALLIANCE Banking Business Process.pdf",
"ALLIANCE Banking General Info&Policy.pdf",
"ALLIANCE Technical Issues Solving.pdf",
]
pdf_files = [str(docs_dir / name) for name in filenames]

policy_tool_obj = PDFTool(pdf_files)

retriever = policy_tool_obj.tool_build()

rag_prompt = ChatPromptTemplate.from_messages([
    ("system", 
     "You are a customer support assistant for ALLIANCE Bank.\n"
     "Your task is to answer user's question based on the provided context.\n"
     "If the context is insufficient, say that you don't know and suggest customer to call customer support phone number"
     "BEGIN_CONTEXT\n{context}\nEND_CONTEXT"),
    ("human", "{question}")
])
model = Model()
llm_rag = model.get_llm()
# compose a chain
chain = rag_prompt | llm_rag
input_df = pd.read_csv(str(docs_dir/INPUT_CSV))
hf_row = []
for _, csv_row in input_df.iterrows():
    question = csv_row["question"]
    lstDocuments = retriever.invoke(question)
    received_context = [doc.page_content for doc in lstDocuments]
    context = "\n".join([doc.page_content for doc in lstDocuments])
    response = chain.invoke({"context": context, "question": question})
    answer = response.content

    hf_row.append(
        {
            "question": question,
            "contexts": received_context,
            "answer": answer,
            "reference": csv_row["ground_truth"]
        }
    )
# input_df.to_json(
#     str(docs_dir/INPUT_JSONL),
#     orient="records",
#     lines=True,
#     force_ascii=False
# )
# convert string list into Python list object
# input_df["contexts"] = input_df["contexts"].apply(eval)
# input_df["ground_truths"] = input_df["ground_truths"].apply(eval)

# convert json dataset to HF dataset and use this file as training set
# dataset = Dataset.from_pandas(input_df)
# dataset = load_dataset("json", data_files=str(docs_dir/INPUT_JSONL))["train"]
dataset = Dataset.from_list(hf_row)

df = dataset.to_pandas()
df.to_csv(str(docs_dir/OUTPUT_CSV))

os.environ["AZURE_API_KEY"] = os.getenv("AZURE_OPENAI_API_KEY")
os.environ["AZURE_API_BASE"] = os.getenv("AZURE_OPENAI_ENDPOINT")
os.environ["AZURE_API_VERSION"] = os.getenv("AZURE_OPENAI_API_VERSION")

# embeddings = HuggingFaceEmbeddings(model="mistral-embed")


client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
# embeddings = GoogleEmbeddings(client=client, model="gemini-embedding-001")
embeddings = HuggingFaceEmbeddingsCls().get_embeddings()

# wrap HF embedding for Ragas compatibility
# embeddings = LangchainEmbeddingsWrapper(hf_embeddings)


llm = llm_factory(
    model=f"azure/{os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME')}",
    provider="litellm",
    client=litellm.completion
)

# initialize metrics with specific models and embeddings
# context_precision = ContextPrecision(llm=llm)
# # context_precision = LLMContextPrecisionWithReference(llm=llm)
# context_recall = ContextRecall(llm=llm)
# faithfulness = Faithfulness(llm=llm)
# answer_relevancy = AnswerRelevancy(llm=llm, embeddings=embeddings)

# metrics_list = [
#     LLMContextPrecisionWithReference(llm=llm),
#     LLMContextRecall(llm=llm),
#     Faithfulness(llm=llm),
#     AnswerRelevancy(llm=llm, embeddings=embeddings)
# ]

metrics_list = [
    context_precision,
    context_recall,
    faithfulness,
    answer_relevancy
]

# print([type(m) for m in metrics_list])
# score_cp = context_precision.score(dataset)
# score_cr = context_recall.score(dataset)
# score_ff = faithfulness.score(dataset)
# score_ar = answer_relevancy.score(dataset)

# print(dataset[0])
# print(type(dataset[0]["contexts"]), type(dataset[0]["reference"]))


results = evaluate(
    dataset,
    metrics=metrics_list,
    llm = llm,
    embeddings=embeddings
)

# print(score_cp, score_cr, score_ff, score_ar)
print(results)

# df = results.to_pandas()



