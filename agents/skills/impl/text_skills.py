from typing import Any
from core.skill import Skill

class TextClassificationSkill(Skill):
    def __init__(self):
        super().__init__(
            name="TextClassificationSkill",
            description="Classifies text into categories (Dummy Implementation).",
            input_schema={"text": "string"},
            output_schema={"category": "string", "confidence": "float"}
        )

    def execute(self, inputs: Any, **kwargs) -> Any:
        text = inputs.get("text", "")
        # Dummy logic
        if "urgent" in text.lower():
            return {"category": "urgent", "confidence": 0.95}
        return {"category": "general", "confidence": 0.8}

class SentimentAnalysisSkill(Skill):
    def __init__(self):
        super().__init__(
            name="SentimentAnalysisSkill",
            description="Analyzes sentiment of text (Dummy Implementation).",
            input_schema={"text": "string"},
            output_schema={"sentiment": "string", "score": "float"}
        )

    def execute(self, inputs: Any, **kwargs) -> Any:
        text = inputs.get("text", "")
        # Dummy logic
        if "bad" in text.lower() or "sad" in text.lower():
            return {"sentiment": "negative", "score": -0.8}
        if "good" in text.lower() or "happy" in text.lower():
            return {"sentiment": "positive", "score": 0.8}
        return {"sentiment": "neutral", "score": 0.0}

class SummarizationSkill(Skill):
    def __init__(self):
        super().__init__(
            name="SummarizationSkill",
            description="Summarizes text (Dummy Implementation).",
            input_schema={"text": "string"},
            output_schema={"summary": "string"}
        )

    def execute(self, inputs: Any, **kwargs) -> Any:
        text = inputs.get("text", "")
        # Dummy logic: take first 50 chars
        return {"summary": text[:50] + "..." if len(text) > 50 else text}
