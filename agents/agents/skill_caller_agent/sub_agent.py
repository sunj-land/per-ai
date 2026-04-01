from typing import Dict, Any, Literal
from core.agent import Agent
from core.state import StandardAgentState
from langgraph.graph import StateGraph, END

class SubAgent(Agent):
    """
    被调用的子 Agent。
    处理具体任务。
    """
    def __init__(self, name="SubAgent"):
        """
        初始化被调用的子 Agent。
        
        :param name: 智能体名称，默认为 "SubAgent"
        """
        # ========== 步骤1：初始化父类 ==========
        super().__init__(name, "Sub Agent for processing specific tasks.")
        
        # 工作流实例: 编译后的状态图对象
        self.workflow = self._build_workflow()

    def _build_workflow(self):
        """
        构建子工作流。
        
        :return: 编译后的 StateGraph 对象
        """
        # ========== 步骤1：创建状态图实例 ==========
        workflow = StateGraph(StandardAgentState)
        
        # ========== 步骤2：添加处理节点 ==========
        workflow.add_node("process_data", self._process_node)
        
        # ========== 步骤3：设置入口点 ==========
        workflow.set_entry_point("process_data")
        
        # ========== 步骤4：设置结束边 ==========
        workflow.add_edge("process_data", END)
        
        return workflow.compile()

    async def _process_node(self, state: StandardAgentState) -> Dict[str, Any]:
        """
        处理数据节点：简单反转字符串作为处理逻辑示例。
        
        :param state: 当前状态
        :return: 处理结果字典
        """
        # 获取任务数据
        task = state.get("task", {})
        # 获取要处理的字符串
        data = task.get("data", "")
        
        # 处理逻辑：字符串反转
        result_str = f"SubAgent processed: {data[::-1]}"
        
        # 构建返回字典
        # processed_data: 处理后的字符串
        result = {"processed_data": result_str}
        
        return {"result": result}

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理子任务的主入口。
        
        :param task: 任务字典，包含数据内容
        :return: 处理结果字典
        """
        # ========== 步骤1：调用工作流执行任务 ==========
        result = await self.workflow.ainvoke({"task": task})
        
        # ========== 步骤2：返回提取出的结果 ==========
        return result.get("result", {})
