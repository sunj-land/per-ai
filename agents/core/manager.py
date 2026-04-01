from typing import Dict, List, Optional, Any
from core.agent import Agent
import importlib
import logging

logger = logging.getLogger(__name__)

class AgentManager:
    """
    Agent 管理器类 (单例模式)
    负责管理系统中的所有 Agent 实例，包括注册、获取和列出 Agent。
    """
    _instance = None

    def __new__(cls):
        """
        实现单例模式，确保系统中只有一个 AgentManager 实例。
        如果实例不存在，则创建并初始化默认 Agent。
        """
        if cls._instance is None:
            cls._instance = super(AgentManager, cls).__new__(cls)
            cls._instance.agents: Dict[str, Agent] = {}
            cls._instance._initialize_default_agents()
        return cls._instance

    def _initialize_default_agents(self):
        """
        初始化默认的 Agent 集合。
        注册数据分析、文本处理、图像识别和工作流协调 Agent。
        """
        # 使用延迟加载以避免循环导入和路径问题
        try:
            from agents.data_agent.graph import DataAgent
            from agents.text_agent.graph import TextAgent
            from agents.image_agent.graph import ImageAgent
            from agents.workflow_agent.graph import WorkflowAgent
            from agents.learning_planner_agent.graph import LearningPlanningAgent
            from agents.rss_quality_agent.graph import RSSQualityAgent

            self.register_agent(DataAgent(name="data_analyst"))
            self.register_agent(TextAgent(name="text_processor"))
            self.register_agent(ImageAgent(name="image_recognizer"))
            self.register_agent(WorkflowAgent(name="coordinator"))
            self.register_agent(LearningPlanningAgent(name="learning_planner"))
            self.register_agent(RSSQualityAgent(name="rss_quality_agent"))
        except ImportError as e:
            logger.warning(f"Failed to load default agents: {e}")

    def register_agent(self, agent: Agent):
        """
        注册一个新的 Agent 到管理器中。

        Args:
            agent (Agent): 要注册的 Agent 实例。
        """
        self.agents[agent.name] = agent

    def get_agent(self, name: str) -> Optional[Agent]:
        """
        根据名称获取 Agent 实例。

        Args:
            name (str): Agent 的名称。

        Returns:
            Optional[Agent]: 如果找到则返回 Agent 实例，否则返回 None。
        """
        return self.agents.get(name)

    def list_agents(self) -> List[Dict[str, Any]]:
        """
        获取所有已注册 Agent 的状态列表。

        Returns:
            List[Dict[str, Any]]: 包含所有 Agent 状态信息的列表。
        """
        return [agent.get_status() for agent in self.agents.values()]
