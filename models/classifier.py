from models.model import Model
from app.constants import Constants
from models.prompts import Prompts
from langchain_core.output_parsers import StrOutputParser

class Classifier:
    def __init__(self):
        model = Model()
        self.llm = model.get_llm()

    def classify_query(self, question: str) -> str:

        # Without StrOutputParser: result = AIMessage(content='card_issues', ...)
        # With StrOutputParser: result = 'card_issues'
        # StrOutputParser() just extracts the text content so you can work with a plain str
        classifier_chain = Prompts.get_classifier_prompt() | self.llm | StrOutputParser()

        label = classifier_chain.invoke({"question": question}).strip().lower()
        return label if label in Constants.CATEGORIES else "general_issues"