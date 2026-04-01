import logging
from typing import Dict, Any

from langgraph.graph import StateGraph, END

from core.agent import Agent
from core.state import StandardAgentState
from skills.impl.learning_skills import GoalDecompositionSkill, PlanGenerationSkill

logger = logging.getLogger(__name__)


def build_learning_planner_graph(skills: dict):
    """
    构建学习计划生成工作流（独立函数，可单独测试或复用）。
    线性流水线：目标分解 → 计划生成。

    :param skills: 技能字典，须包含 goal_decomposition / plan_generation
    :return: 编译后的 CompiledStateGraph
    """

    async def _decompose_goal_node(state: StandardAgentState) -> Dict[str, Any]:
        goal_text = state["task"].get("goal_text")
        if not goal_text:
            return {"error": "Missing 'goal_text'"}
        logger.info("Decomposing goal: %s", goal_text)
        goal_info = await skills["goal_decomposition"].execute({"goal_text": goal_text})
        return {"result": {"goal_analysis": goal_info}}

    async def _generate_plan_node(state: StandardAgentState) -> Dict[str, Any]:
        goal_info = state.get("result", {}).get("goal_analysis")
        if not goal_info:
            return {"error": "Goal decomposition failed or missing"}
        logger.info("Generating plan for: %s", goal_info)
        plan_data = await skills["plan_generation"].execute({"goal_info": goal_info})
        return {"result": {"goal_analysis": goal_info, "generated_plan": plan_data}}

    workflow = StateGraph(StandardAgentState)
    workflow.add_node("decompose_goal", _decompose_goal_node)
    workflow.add_node("generate_plan", _generate_plan_node)

    workflow.set_entry_point("decompose_goal")
    workflow.add_edge("decompose_goal", "generate_plan")
    workflow.add_edge("generate_plan", END)

    return workflow.compile()


class LearningPlanningAgent(Agent):
    """
    负责解析用户目标并生成学习计划的主智能体。
    """

    def __init__(self, name: str = "learning_planner"):
        super().__init__(
            name=name,
            description="Analyzes user goals and generates structured learning plans.",
            config={},
        )
        self.register_skill(GoalDecompositionSkill())
        self.register_skill(PlanGenerationSkill())
        self.workflow = build_learning_planner_graph(self.skills)

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        任务数据结构:
        {
            "type": "create_plan",
            "goal_text": "I want to learn Python in 3 months"
        }
        """
        if task.get("type") != "create_plan":
            raise ValueError(f"Unknown task type: {task.get('type')}")
        result = await self.workflow.ainvoke({"task": task})
        if result.get("error"):
            raise ValueError(result["error"])
        return result.get("result", {})
