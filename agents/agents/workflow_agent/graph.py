from typing import Dict, Any

from langgraph.graph import StateGraph, END

from core.agent import Agent
from core.state import StandardAgentState
from skills.impl.workflow_skills import (
    DependencyManagementSkill,
    ParallelExecutionSkill,
    TaskDecompositionSkill,
)


def build_workflow_agent_graph(skills: dict):
    """
    构建任务编排工作流（独立函数，可单独测试或复用）。
    线性流水线：分解任务 → 分析依赖 → 并行执行。

    :param skills: 技能字典，须包含 TaskDecompositionSkill / DependencyManagementSkill / ParallelExecutionSkill
    :return: 编译后的 CompiledStateGraph
    """

    async def _decompose_node(state: StandardAgentState) -> Dict[str, Any]:
        goal = state["task"].get("goal")
        subtasks_result = skills["TaskDecompositionSkill"].execute({"task_description": goal})
        return {"result": {"subtasks_result": subtasks_result}}

    async def _dependencies_node(state: StandardAgentState) -> Dict[str, Any]:
        subtasks_result = state["result"].get("subtasks_result", {})
        subtasks = subtasks_result.get("subtasks", [])
        deps_result = skills["DependencyManagementSkill"].execute({"tasks": subtasks})
        new_result = state.get("result", {}).copy()
        new_result["deps_result"] = deps_result
        return {"result": new_result}

    async def _execute_node(state: StandardAgentState) -> Dict[str, Any]:
        subtasks_result = state["result"].get("subtasks_result", {})
        subtasks = subtasks_result.get("subtasks", [])
        exec_result = skills["ParallelExecutionSkill"].execute({"tasks": subtasks})
        new_result = state.get("result", {}).copy()
        new_result["exec_result"] = exec_result
        return {"result": new_result}

    workflow = StateGraph(StandardAgentState)
    workflow.add_node("decompose_task", _decompose_node)
    workflow.add_node("analyze_dependencies", _dependencies_node)
    workflow.add_node("execute_parallel", _execute_node)

    workflow.set_entry_point("decompose_task")
    workflow.add_edge("decompose_task", "analyze_dependencies")
    workflow.add_edge("analyze_dependencies", "execute_parallel")
    workflow.add_edge("execute_parallel", END)

    return workflow.compile()


class WorkflowAgent(Agent):
    """
    负责任务编排和工作流管理的智能体。
    用于将复杂任务分解、分析依赖并执行。
    """

    def __init__(self, name: str = "WorkflowAgent"):
        super().__init__(name, "Agent for task orchestration and workflow management.")
        self.register_skill(TaskDecompositionSkill())
        self.register_skill(DependencyManagementSkill())
        self.register_skill(ParallelExecutionSkill())
        self.workflow = build_workflow_agent_graph(self.skills)

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        任务数据结构:
        {
            "goal": "Complex task description",
            "context": {...}
        }
        """
        result = await self.workflow.ainvoke({"task": task})
        if result.get("error"):
            raise ValueError(result["error"])
        final_result = result.get("result", {})
        return {
            "plan": final_result.get("subtasks_result", {}).get("subtasks", []),
            "dependencies": final_result.get("deps_result", {}),
            "execution_results": final_result.get("exec_result", {}),
        }
