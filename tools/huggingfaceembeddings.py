# from langchain_huggingface import HuggingFaceEndpointEmbeddings
# import os
from langchain_mistralai import MistralAIEmbeddings
class HuggingFaceEmbeddingsCls:
    # def __init__(self, model_name: str="BAAI/bge-base-en-v1.5"):
    def __init__(self):

        self.embeddings = MistralAIEmbeddings(model="mistral-embed")
    
    def get_embeddings(self):
        return self.embeddings