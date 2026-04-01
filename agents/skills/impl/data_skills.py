from typing import Any
from core.skill import Skill
import pandas as pd

class DataCleaningSkill(Skill):
    def __init__(self):
        super().__init__(
            name="DataCleaningSkill",
            description="Cleans data by handling missing values and duplicates.",
            input_schema={"data": "list/dict/csv_path"},
            output_schema={"cleaned_data": "list/dict"}
        )

    def execute(self, inputs: Any, **kwargs) -> Any:
        data = inputs.get("data")
        if isinstance(data, str) and data.endswith(".csv"):
            df = pd.read_csv(data)
        elif isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            df = pd.DataFrame([data])
        else:
            return {"error": "Unsupported data format"}
        
        # Simple cleaning: drop duplicates, fill na
        df.drop_duplicates(inplace=True)
        df.fillna(0, inplace=True)
        
        return {"cleaned_data": df.to_dict(orient="records")}

class StatisticalAnalysisSkill(Skill):
    def __init__(self):
        super().__init__(
            name="StatisticalAnalysisSkill",
            description="Performs basic statistical analysis.",
            input_schema={"data": "list/dict"},
            output_schema={"stats": "dict"}
        )

    def execute(self, inputs: Any, **kwargs) -> Any:
        data = inputs.get("data")
        df = pd.DataFrame(data)
        desc = df.describe().to_dict()
        return {"stats": desc}

class DataVisualizationSkill(Skill):
    def __init__(self):
        super().__init__(
            name="DataVisualizationSkill",
            description="Generates basic visualization data (e.g. for charts).",
            input_schema={"data": "list/dict"},
            output_schema={"chart_data": "dict"}
        )

    def execute(self, inputs: Any, **kwargs) -> Any:
        # For now, just return data formatted for a simple chart
        data = inputs.get("data")
        df = pd.DataFrame(data)
        # Assume numerical columns are values, categorical are labels
        # Simplified logic
        return {"chart_data": {
            "columns": df.columns.tolist(),
            "rows": df.to_dict(orient="records")
        }}
