from typing import Dict, Any

from langgraph.graph import StateGraph, END

from core.agent import Agent
from core.state import StandardAgentState
from .skills import SubAgentSkill


def build_skill_caller_graph(skills: dict):
    """
    构建子 Agent 委派工作流（独立函数，可单独测试或复用）。

    :param skills: 技能字典，须包含 SubAgentSkill
    :return: 编译后的 CompiledStateGraph
    """

    async def _delegate_node(state: StandardAgentState) -> Dict[str, Any]:
        data = state.get("task", {}).get("data", "")
        skill_result = await skills["SubAgentSkill"].execute({"data": data})
        return {"result": {"original": data, "sub_agent_result": skill_result.get("processed_data", "")}}

    workflow = StateGraph(StandardAgentState)
    workflow.add_node("delegate_task", _delegate_node)
    workflow.set_entry_point("delegate_task")
    workflow.add_edge("delegate_task", END)
    return workflow.compile()


class SkillCallerAgent(Agent):
    """
    演示如何通过 Skill 机制调用子 Agent 的主 Agent。
    """

    def __init__(self, name: str = "SkillCallerAgent"):
        super().__init__(name, "Main Agent that calls a sub-agent via skill.")
        self.register_skill(SubAgentSkill())
        self.workflow = build_skill_caller_graph(self.skills)

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        result = await self.workflow.ainvoke({"task": task})
        return result.get("result", {})
