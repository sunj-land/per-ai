from typing import Any
from core.skill import Skill
from .sub_agent import SubAgent

class SubAgentSkill(Skill):
    """
    将 SubAgent 包装为一个 Skill，供主 Agent 调用。
    """
    def __init__(self):
        """
        初始化 SubAgentSkill。
        """
        # ========== 步骤1：初始化父类技能配置 ==========
        super().__init__(
            name="SubAgentSkill",
            description="A skill that delegates tasks to a sub-agent.",
            input_schema={"data": "string"},
            output_schema={"processed_data": "string"}
        )
        # 实例化子 Agent
        self.sub_agent = SubAgent()

    def execute(self, inputs: Any, **kwargs) -> Any:
        """
        执行技能：将数据传递给子 Agent 进行处理。
        注意：此处返回的是一个协程，调用方需要 await。
        
        :param inputs: 输入参数，包含待处理数据
        :param kwargs: 其他可选参数
        :return: 子 Agent 处理任务的协程
        """
        # 获取要处理的数据
        data = inputs.get("data", "")
        
        # 组装传给子 Agent 的任务字典
        # type: 任务类型
        # data: 数据内容
        task = {
            "type": "sub_task",
            "data": data
        }
        
        # 返回处理协程，由外部 await
        return self.sub_agent.process_task(task)
