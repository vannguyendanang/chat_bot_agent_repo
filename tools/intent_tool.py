from langchain_core.tools import tool
from models.intent_classifier import IntentClassifier

def build_intent_tool(classifier: IntentClassifier):
    # define a tool name
    @tool("classify_intent")
    # define the actual tool function
    def classify_intent(query: str) -> str:
        """Classify user intent for support routing when no tool can answer."""
        pred = classifier.predict(query)
        return pred
    return classify_intent

# ---- Singleton initialization (loaded once per process) ----
_BASE_MODEL = "distilbert-base-uncased"
_ADAPTER_DIR = "models/intent_adapter"  

_classifier = IntentClassifier(base_checkpoint=_BASE_MODEL, adapter_dir=_ADAPTER_DIR)
intent_tool = build_intent_tool(_classifier)