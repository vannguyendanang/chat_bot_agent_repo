from typing import List
from langchain_chroma import Chroma
# from langchain.schema import Document
from langchain_core.documents import Document

class VectorStore:
    def __init__(self, embeddings):
        self.embeddings = embeddings
        self.vectorstore = None

    def create_store(self, documents: List[Document]) -> Chroma:
        # extract text and metadata from each document, generate embeddings for the text and store everything in a Chroma object.
        # self.vectorstore = Chroma.from_documents(documents, self.embeddings)
        self.vectorstore = Chroma(
            collection_name="rag_collection",
            embedding_function=self.embeddings,
            persist_directory="./chroma_db"  # specify the directory to store the vector store
        )

        # Index chunks
        _ = self.vectorstore.add_documents(documents=documents)
        print(f"Created vector store with {len(documents)} documents.")

        # store the vectorstore (Vector embeddings, metadata,index structure) in ./chroma_db folder
        # self.vectorstore.persist()

        return self.vectorstore