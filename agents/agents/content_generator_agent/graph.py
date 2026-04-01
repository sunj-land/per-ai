import logging
from typing import Dict, Any, Literal

from langgraph.graph import StateGraph, END

from core.agent import Agent
from core.state import StandardAgentState
from skills.impl.content_skills import (
    ExerciseGenerationSkill,
    SummaryGenerationSkill,
    VideoGenerationSkill,
)

logger = logging.getLogger(__name__)

_CONTENT_TYPE_MAP = {
    "video": "video",
    "exercise": "exercise",
    "quiz": "exercise",
    "summary": "summary",
    "reading": "summary",
}


def build_content_generator_graph(skills: dict):
    """
    构建教育内容生成工作流（独立函数，可单独测试或复用）。

    :param skills: 技能字典，须包含 video_generation / exercise_generation / summary_generation
    :return: 编译后的 CompiledStateGraph
    """

    def _route_task(state: StandardAgentState) -> Literal["video", "exercise", "summary", "unknown"]:
        task = state.get("task", {})
        if task.get("type") != "generate_content":
            return "unknown"
        content_type = task.get("task_type", "summary")
        return _CONTENT_TYPE_MAP.get(content_type, "summary")

    async def _video_gen_node(state: StandardAgentState) -> Dict[str, Any]:
        task_title = state["task"].get("task_title", "Unknown Task")
        result = await skills["video_generation"].execute({"task_title": task_title})
        return {"result": result}

    async def _exercise_gen_node(state: StandardAgentState) -> Dict[str, Any]:
        task_title = state["task"].get("task_title", "Unknown Task")
        result = await skills["exercise_generation"].execute({"task_title": task_title})
        return {"result": result}

    async def _summary_gen_node(state: StandardAgentState) -> Dict[str, Any]:
        task_title = state["task"].get("task_title", "Unknown Task")
        result = await skills["summary_generation"].execute({"task_title": task_title})
        return {"result": result}

    workflow = StateGraph(StandardAgentState)
    workflow.add_node("video_gen", _video_gen_node)
    workflow.add_node("exercise_gen", _exercise_gen_node)
    workflow.add_node("summary_gen", _summary_gen_node)

    workflow.set_conditional_entry_point(
        _route_task,
        {
            "video": "video_gen",
            "exercise": "exercise_gen",
            "summary": "summary_gen",
            "unknown": END,
        },
    )

    workflow.add_edge("video_gen", END)
    workflow.add_edge("exercise_gen", END)
    workflow.add_edge("summary_gen", END)

    return workflow.compile()


class ContentGenerationAgent(Agent):
    """
    负责生成教育内容（如视频、练习题、总结）的智能体。
    """

    def __init__(self, name: str = "content_generator"):
        super().__init__(name=name, description="Generates content for learning tasks.", config={})
        self.register_skill(VideoGenerationSkill())
        self.register_skill(ExerciseGenerationSkill())
        self.register_skill(SummaryGenerationSkill())
        self.workflow = build_content_generator_graph(self.skills)

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        任务数据结构:
        {
            "type": "generate_content",
            "task_type": "video" | "exercise" | "quiz" | "summary" | "reading",
            "task_title": "Understanding Loops"
        }
        """
        result = await self.workflow.ainvoke({"task": task})
        if result.get("result") is None and result.get("error"):
            raise ValueError(result["error"])
        if result.get("result") is None:
            if task.get("type") != "generate_content":
                raise ValueError(f"Unknown task type: {task.get('type')}")
            return {}
        return result.get("result", {})
