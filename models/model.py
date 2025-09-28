from langchain_openai import AzureChatOpenAI
import os

class Model:
    """
    Model class handels LLM configurations and provides to create model instances
    """

    def __init__(self):
        
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.azure_deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        self.azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        self.azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")

    def get_llm(self) -> AzureChatOpenAI:
        """
        Get an instance of AzureChatOpenAI with the configured settings.
        """

        return AzureChatOpenAI(
            azure_endpoint=self.azure_endpoint,
            azure_deployment=self.azure_deployment_name,
            openai_api_version=self.azure_api_version
        )