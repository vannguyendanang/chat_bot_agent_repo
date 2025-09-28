from langchain_chroma import Chroma

class Retriever:
    # limit the number of top k documents to retrieve
    # maximum marginal relevance means that the documents are selected based on their relevance to the query and their diversity
    def __init__(self, vectorstore: Chroma, k: int = 3):
        self.retriever = vectorstore.as_retriever(search_type = "mmr", #maximum marginal relevance
                                                  search_kwargs = {"k": k})    
        
    # def get_relevant_documents(self, query: str) -> List[Document]:
    #     return self.retriever.get_relevant_documents(query)
    def get_retriever(self):
        return self.retriever