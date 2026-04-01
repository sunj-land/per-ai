from typing import Dict, Any, Literal

from langgraph.graph import StateGraph, END

from core.agent import Agent
from core.state import StandardAgentState
from skills.impl.data_skills import (
    DataCleaningSkill,
    DataVisualizationSkill,
    StatisticalAnalysisSkill,
)


def build_data_agent_graph(skills: dict):
    """
    构建数据处理工作流（独立函数，可单独测试或复用）。

    :param skills: 技能字典，须包含 DataCleaningSkill / StatisticalAnalysisSkill / DataVisualizationSkill
    :return: 编译后的 CompiledStateGraph
    """

    def _route_task(state: StandardAgentState) -> Literal["clean", "analyze", "visualize", "unknown"]:
        task_type = state.get("task", {}).get("type")
        if task_type in ("clean", "analyze", "visualize"):
            return task_type
        return "unknown"

    async def _clean_data_node(state: StandardAgentState) -> Dict[str, Any]:
        data = state["task"].get("data")
        result = skills["DataCleaningSkill"].execute({"data": data})
        return {"result": result}

    async def _analyze_data_node(state: StandardAgentState) -> Dict[str, Any]:
        data = state["task"].get("data")
        result = skills["StatisticalAnalysisSkill"].execute({"data": data})
        return {"result": result}

    async def _visualize_data_node(state: StandardAgentState) -> Dict[str, Any]:
        data = state["task"].get("data")
        result = skills["DataVisualizationSkill"].execute({"data": data})
        return {"result": result}

    workflow = StateGraph(StandardAgentState)
    workflow.add_node("clean_data", _clean_data_node)
    workflow.add_node("analyze_data", _analyze_data_node)
    workflow.add_node("visualize_data", _visualize_data_node)

    workflow.set_conditional_entry_point(
        _route_task,
        {
            "clean": "clean_data",
            "analyze": "analyze_data",
            "visualize": "visualize_data",
            "unknown": END,
        },
    )

    workflow.add_edge("clean_data", END)
    workflow.add_edge("analyze_data", END)
    workflow.add_edge("visualize_data", END)

    return workflow.compile()


class DataAgent(Agent):
    """
    负责数据清洗、分析和可视化的智能体。
    """

    def __init__(self, name: str = "DataAgent"):
        super().__init__(name, "Agent for data cleaning, analysis and visualization.")
        self.register_skill(DataCleaningSkill())
        self.register_skill(StatisticalAnalysisSkill())
        self.register_skill(DataVisualizationSkill())
        self.workflow = build_data_agent_graph(self.skills)

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        任务数据结构:
        {
            "type": "clean" | "analyze" | "visualize",
            "data": ...
        }
        """
        result = await self.workflow.ainvoke({"task": task})
        if result.get("result") is None:
            return {"error": f"Unknown task type: {task.get('type')}"}
        return result.get("result", {})
