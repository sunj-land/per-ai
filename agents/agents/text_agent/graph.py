from typing import Dict, Any, Literal

from langgraph.graph import StateGraph, END

from core.agent import Agent
from core.state import StandardAgentState
from skills.impl.text_skills import (
    SentimentAnalysisSkill,
    SummarizationSkill,
    TextClassificationSkill,
)


def build_text_agent_graph(skills: dict):
    """
    构建文本处理工作流（独立函数，可单独测试或复用）。

    :param skills: 技能字典，须包含 TextClassificationSkill / SentimentAnalysisSkill / SummarizationSkill
    :return: 编译后的 CompiledStateGraph
    """

    def _route_task(state: StandardAgentState) -> Literal["classify", "sentiment", "summarize", "unknown"]:
        task_type = state.get("task", {}).get("type")
        if task_type in ("classify", "sentiment", "summarize"):
            return task_type
        return "unknown"

    async def _classify_node(state: StandardAgentState) -> Dict[str, Any]:
        text = state["task"].get("text")
        result = skills["TextClassificationSkill"].execute({"text": text})
        return {"result": result}

    async def _sentiment_node(state: StandardAgentState) -> Dict[str, Any]:
        text = state["task"].get("text")
        result = skills["SentimentAnalysisSkill"].execute({"text": text})
        return {"result": result}

    async def _summarize_node(state: StandardAgentState) -> Dict[str, Any]:
        text = state["task"].get("text")
        result = skills["SummarizationSkill"].execute({"text": text})
        return {"result": result}

    workflow = StateGraph(StandardAgentState)
    workflow.add_node("classify_text", _classify_node)
    workflow.add_node("analyze_sentiment", _sentiment_node)
    workflow.add_node("summarize_text", _summarize_node)

    workflow.set_conditional_entry_point(
        _route_task,
        {
            "classify": "classify_text",
            "sentiment": "analyze_sentiment",
            "summarize": "summarize_text",
            "unknown": END,
        },
    )

    workflow.add_edge("classify_text", END)
    workflow.add_edge("analyze_sentiment", END)
    workflow.add_edge("summarize_text", END)

    return workflow.compile()


class TextAgent(Agent):
    """
    负责文本处理的智能体。
    支持文本分类、情感分析和文本总结功能。
    """

    def __init__(self, name: str = "TextAgent"):
        super().__init__(name, "Agent for text classification, sentiment analysis and summarization.")
        self.register_skill(TextClassificationSkill())
        self.register_skill(SentimentAnalysisSkill())
        self.register_skill(SummarizationSkill())
        self.workflow = build_text_agent_graph(self.skills)

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        任务数据结构:
        {
            "type": "classify" | "sentiment" | "summarize",
            "text": "待处理的文本内容"
        }
        """
        result = await self.workflow.ainvoke({"task": task})
        if result.get("result") is None:
            return {"error": f"Unknown task type: {task.get('type')}"}
        return result.get("result", {})
