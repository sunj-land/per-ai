from typing import Dict, Any, Literal

from langgraph.graph import StateGraph, END

from core.agent import Agent
from core.state import StandardAgentState
from skills.impl.image_skills import (
    FeatureExtractionSkill,
    ImagePreprocessingSkill,
    ObjectDetectionSkill,
)


def build_image_agent_graph(skills: dict):
    """
    构建图像处理工作流（独立函数，可单独测试或复用）。

    :param skills: 技能字典，须包含 ImagePreprocessingSkill / FeatureExtractionSkill / ObjectDetectionSkill
    :return: 编译后的 CompiledStateGraph
    """

    def _route_task(state: StandardAgentState) -> Literal["preprocess", "features", "detect", "unknown"]:
        task_type = state.get("task", {}).get("type")
        if task_type in ("preprocess", "features", "detect"):
            return task_type
        return "unknown"

    async def _preprocess_node(state: StandardAgentState) -> Dict[str, Any]:
        image_path = state["task"].get("image_path")
        result = skills["ImagePreprocessingSkill"].execute({"image_path": image_path})
        return {"result": result}

    async def _extract_features_node(state: StandardAgentState) -> Dict[str, Any]:
        image_path = state["task"].get("image_path")
        result = skills["FeatureExtractionSkill"].execute({"image_path": image_path})
        return {"result": result}

    async def _detect_objects_node(state: StandardAgentState) -> Dict[str, Any]:
        image_path = state["task"].get("image_path")
        result = skills["ObjectDetectionSkill"].execute({"image_path": image_path})
        return {"result": result}

    workflow = StateGraph(StandardAgentState)
    workflow.add_node("preprocess_image", _preprocess_node)
    workflow.add_node("extract_features", _extract_features_node)
    workflow.add_node("detect_objects", _detect_objects_node)

    workflow.set_conditional_entry_point(
        _route_task,
        {
            "preprocess": "preprocess_image",
            "features": "extract_features",
            "detect": "detect_objects",
            "unknown": END,
        },
    )

    workflow.add_edge("preprocess_image", END)
    workflow.add_edge("extract_features", END)
    workflow.add_edge("detect_objects", END)

    return workflow.compile()


class ImageAgent(Agent):
    """
    负责图像处理和识别的智能体。
    支持图像预处理、特征提取和目标检测功能。
    """

    def __init__(self, name: str = "ImageAgent"):
        super().__init__(name, "Agent for image processing and recognition.")
        self.register_skill(ImagePreprocessingSkill())
        self.register_skill(FeatureExtractionSkill())
        self.register_skill(ObjectDetectionSkill())
        self.workflow = build_image_agent_graph(self.skills)

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        任务数据结构:
        {
            "type": "preprocess" | "features" | "detect",
            "image_path": "路径字符串"
        }
        """
        result = await self.workflow.ainvoke({"task": task})
        if result.get("result") is None:
            return {"error": f"Unknown task type: {task.get('type')}"}
        return result.get("result", {})
