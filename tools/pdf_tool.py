# from langchain.document_loaders import PyPDFLoader
from langchain_community.document_loaders import PyPDFLoader
# from langchain.text_splitter import CharacterTextSplitter
# from langchain.vectorstores import FAISS
# from langchain.embeddings import HuggingFaceEmbeddings
from langchain.tools import tool
from typing import List
# from langchain.schema import Document
from langchain_core.documents import Document
# from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_text_splitters import RecursiveCharacterTextSplitter
from tools.vector_store import VectorStore
from tools.huggingfaceembeddings import HuggingFaceEmbeddingsCls
from tools.retriever import Retriever
import logging, traceback
import ftfy
# from app.server import APP_LOGGER

# log = logging.getLogger(f"{APP_LOGGER}.{__name__}")
log = logging.getLogger(__name__)

class PDFTool:
    def __init__(self, file_paths: List[str]):
        self.file_paths = file_paths

    def load_content(self) -> List[Document]:
        all_docs = []
        for path in self.file_paths:
            try:
                loader = PyPDFLoader(path)
                # A PDF file is extracted into multiple document objects. Each object is a page in PDF file
                documents = loader.load()
                # merge these document objects into the main list instead of adding the list as a single element
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

    # chunk size is 256 characters and chunk overlap is 50 characters
    def split_documents(self, documents: List[Document], chunk_size: int = 400, chunk_overlap: int = 50) -> List[Document]:
    # def __init__(self, chunk_size: int = 256, chunk_overlap: int = 50):
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
    # def create_chunks(self, documents: List[Document]) -> List[Document]:
        chunks = splitter.split_documents(documents)
        print(f"Created {len(chunks)} chunks from the {len(documents)} documents.")
        return chunks
    
    def normalize_text(self, text:str) -> str:
        # Fix mojibake (â¢ → •, â → ’, etc.)
        text = ftfy.fix_text(text)
        return text
    
    def tool_build(self):
        documents = self.load_content()
        chunker = self.split_documents(documents)

        for c in chunker:
            c.page_content = self.normalize_text(c.page_content)

        # Initialize embedding model that will convert text to vector
        embeddings = HuggingFaceEmbeddingsCls()
        # vectorstore = None
        # retriever = None
        # chunks = self.chunker.create_chunks(documents)
        # setup vector stores
        vectorstores = VectorStore(embeddings.get_embeddings())
        # index each chunk → create vector embedding for each chunk → save these embeddings into the vector database.
        vectorstore = vectorstores.create_store(chunker)
        retriever_component = Retriever(vectorstore)
        retriever = retriever_component.get_retriever()
        return retriever
    
    def get_tool(self):

        retriever = self.tool_build()

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
            # print("Print out the retrieved context\n")
            log.info("The retrieved context")
            for i, d in enumerate(results):
                # print(i, d.metadata.get("source"), d.metadata.get("page"), len(d.page_content), hash(d.page_content))
                log.info(
                    "chunk=%d source=%s page=%s chars=%d content=%s",
                    i,
                    d.metadata.get("source"),
                    d.metadata.get("page"),
                    len(d.page_content),
                    d.page_content
                )
            
            return "\n\n".join([doc.page_content for doc in results])

        return lookup_pdf