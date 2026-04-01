import logging
from typing import Any, Dict

from langgraph.graph import END, StateGraph

from core.agent import Agent
from core.state import StandardAgentState
from .prompt import SYSTEM_PROMPT
from .tools import RSSQualityScoringTool

logger = logging.getLogger(__name__)


def build_rss_quality_agent_graph(scoring_tool: RSSQualityScoringTool):
    """
    构建 RSS 文章质量评分工作流（独立函数，可单独测试或复用）。

    :param scoring_tool: RSSQualityScoringTool 实例
    :return: 编译后的 CompiledStateGraph
    """

    async def _score_articles_node(state: StandardAgentState) -> Dict[str, Any]:
        task = state.get("task", {})
        logger.info("RSSQualityAgent received task: %s", task)
        try:
            result = await scoring_tool.execute(task)
            return {"result": result}
        except Exception as exc:
            logger.exception("RSSQualityAgent scoring failed")
            return {"error": str(exc)}

    workflow = StateGraph(StandardAgentState)
    workflow.add_node("score_articles", _score_articles_node)
    workflow.set_entry_point("score_articles")
    workflow.add_edge("score_articles", END)
    return workflow.compile()


class RSSQualityAgent(Agent):
    """RSS 文章质量评分智能体。"""

    def __init__(
        self,
        name: str = "rss_quality_agent",
        description: str = "Batch quality scoring agent for RSS articles",
    ) -> None:
        super().__init__(name=name, description=description)
        self.system_prompt = SYSTEM_PROMPT
        self.scoring_tool = RSSQualityScoringTool()
        self.workflow = build_rss_quality_agent_graph(self.scoring_tool)

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """处理 RSS 文章评分任务。"""
        result = await self.workflow.ainvoke({"task": task})
        if result.get("error"):
            raise ValueError(result["error"])
        return result.get("result", {})
