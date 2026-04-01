import logging
from typing import Dict, Any, List

from langgraph.graph import StateGraph, END

from core.agent import Agent
from core.state import StandardAgentState
from .tools import ShellRiskEngine, ShellExecutionTool

logger = logging.getLogger(__name__)


def build_shell_risk_agent_graph(risk_engine: ShellRiskEngine, execution_tool: ShellExecutionTool):
    """
    构建 Shell 风险评估与执行工作流（独立函数，可单独测试或复用）。

    :param risk_engine: ShellRiskEngine 实例，负责风险评估
    :param execution_tool: ShellExecutionTool 实例，负责实际执行
    :return: 编译后的 CompiledStateGraph
    """

    async def _assess_risk_node(state: StandardAgentState) -> Dict[str, Any]:
        task = state.get("task", {})
        command = task.get("command", "")
        config_override = task.get("risk_config", {})

        logger.info("ShellRiskAgent assessing command: %s with config: %s", command, config_override)

        assessment = risk_engine.assess(command, config_override=config_override)
        is_safe = assessment.get("is_safe", False)
        risk_level = assessment.get("risk_level", "LOW")
        risk_details = assessment.get("risk_details", [])

        assessment_result = {
            "is_safe": is_safe,
            "risk_level": risk_level,
            "risk_details": risk_details,
            "command": command,
        }

        if not is_safe:
            reject_msg = (
                f"拒绝执行该命令。检测到风险等级：{risk_level}。\n"
                f"风险项：{', '.join(risk_details)}"
            )
            return {"result": assessment_result, "error": reject_msg}

        return {"result": assessment_result}

    async def _execute_command_node(state: StandardAgentState) -> Dict[str, Any]:
        command = state.get("result", {}).get("command", "")
        logger.info("ShellRiskAgent executing command: %s", command)
        try:
            exec_result = await execution_tool.execute(command)
            return {"result": {"execution": exec_result}}
        except Exception as e:
            logger.error("Error executing command: %s", e)
            return {"error": f"执行出错: {str(e)}"}

    def _route_after_assessment(state: StandardAgentState) -> str:
        return "execute" if state.get("result", {}).get("is_safe", False) else "reject"

    workflow = StateGraph(StandardAgentState)
    workflow.add_node("assess_risk", _assess_risk_node)
    workflow.add_node("execute_command", _execute_command_node)

    workflow.set_entry_point("assess_risk")
    workflow.add_conditional_edges(
        "assess_risk",
        _route_after_assessment,
        {"execute": "execute_command", "reject": END},
    )
    workflow.add_edge("execute_command", END)

    return workflow.compile()


class ShellRiskAgent(Agent):
    """
    负责接收 Shell 命令，进行风险评估后执行或拒绝的智能体。
    """

    def __init__(
        self,
        name: str = "shell_risk_agent",
        description: str = "A shell execution agent with a multi-dimensional risk assessment engine",
        custom_whitelist: List[str] = None,
        custom_blacklist: List[str] = None,
        custom_sensitive_paths: List[str] = None,
        custom_dangerous_patterns: List[str] = None,
    ):
        super().__init__(name=name, description=description)
        self.risk_engine = ShellRiskEngine(
            custom_whitelist=custom_whitelist,
            custom_blacklist=custom_blacklist,
            custom_sensitive_paths=custom_sensitive_paths,
            custom_dangerous_patterns=custom_dangerous_patterns,
        )
        self.execution_tool = ShellExecutionTool()
        self.workflow = build_shell_risk_agent_graph(self.risk_engine, self.execution_tool)

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        任务数据结构:
        {
            "command": "要执行的 shell 命令",
            "risk_config": {
                "whitelist": [...],
                "blacklist_commands": [...],
                "sensitive_paths": [...],
                "dangerous_patterns": [...]
            }
        }
        """
        initial_state = {"task": task, "task_type": "shell_execution", "result": {}, "error": None}
        result_state = await self.workflow.ainvoke(initial_state)

        if result_state.get("error"):
            return {
                "status": "rejected",
                "message": result_state["error"],
                "risk_assessment": {
                    "level": result_state.get("result", {}).get("risk_level"),
                    "details": result_state.get("result", {}).get("risk_details"),
                },
            }

        return {
            "status": "success",
            "result": result_state.get("result", {}).get("execution", {}),
        }
