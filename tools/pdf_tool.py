# from langchain.document_loaders import PyPDFLoader
from langchain_community.document_loaders import PyPDFLoader
# from langchain.text_splitter import CharacterTextSplitter
# from langchain.vectorstores import FAISS
# from langchain.embeddings import HuggingFaceEmbeddings
from langchain.tools import tool
from typing import List
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from tools.vector_store import VectorStore
from tools.huggingfaceembeddings import HuggingFaceEmbeddingsCls
from tools.retriever import Retriever


class PDFTool:
    def __init__(self, file_paths: List[str]):
        self.file_paths = file_paths

    def load_content(self) -> List[Document]:
        all_docs = []
        for path in self.file_paths:
            try:
                loader = PyPDFLoader(path)
                documents = loader.load()
                all_docs.extend(documents)
            except Exception as e:
                print(f"Error loading PDF content from {path}: {str(e)}")
                continue
        print(f"Loaded {len(all_docs)} documents from {len(self.file_paths)} file paths.")
        return all_docs
        
    # def __init__(self, path="sample.pdf"):
    #     loader = PyPDFLoader(path)
    #     docs = loader.load()
    #     splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    #     chunks = splitter.split_documents(docs)
    #     vectorstore = FAISS.from_documents(chunks, HuggingFaceEmbeddings())
    #     self.retriever = vectorstore.as_retriever()
    def split_documents(self, documents: List[Document], chunk_size: int = 256, chunk_overlap: int = 50) -> List[Document]:
    # def __init__(self, chunk_size: int = 256, chunk_overlap: int = 50):
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
    # def create_chunks(self, documents: List[Document]) -> List[Document]:
        chunks = splitter.split_documents(documents)
        print(f"Created {len(chunks)} chunks from the {len(documents)} documents.")
        return chunks
    
    def get_tool(self):
        # chunker = DocumentChunker()
        
        documents = self.load_content()
        chunker = self.split_documents(documents)
        embeddings = HuggingFaceEmbeddingsCls()
        # vectorstore = None
        # retriever = None
        # chunks = self.chunker.create_chunks(documents)
        vectorstores = VectorStore(embeddings.get_embeddings())
        vectorstore = vectorstores.create_store(chunker)
        retriever_component = Retriever(vectorstore)
        retriever = retriever_component.get_retriever()

        @tool
        def lookup_pdf(query: str) -> str:
            # """Search the PDF for relevant info."""
            """Searches the company knowledge base (PDF documents) for general information and policies.
            Returns text snippets that may be relevant to the query. 
            Use this tool first for any general question.
            IMPORTANT: This tool may not have the answer to very specific or personal problems.
            """            
            results = retriever.invoke(query)

            # print the source and page number of each result for debugging
            # for i, d in enumerate(results):
                # print(i, d.metadata.get("source"), d.metadata.get("page"), len(d.page_content), hash(d.page_content))
            
            return "\n\n".join([doc.page_content for doc in results])

        return lookup_pdf