"""
Agent 路由器模块
负责将用户请求路由到合适的子 Agent，包括基于关键词的快速匹配和基于 LLM 的意图推断。
"""
import json
import logging
from typing import Any, Dict, List, Optional

from utils.utils import parse_json_object

logger = logging.getLogger(__name__)


_PURPOSE_AGENT_MAP: Dict[str, str] = {
    "article_search": "article_query_agent",
    "text_summarize": "text_agent",
    "data_analysis": "data_agent",
    "workflow_planning": "workflow_agent",
}

_PURPOSE_KEYWORDS: Dict[str, List[str]] = {
    "article_search": ["文章", "资讯", "新闻", "rss", "feed", "article", "news"],
    "text_summarize": ["总结", "摘要", "概括", "提炼", "summarize", "summary", "tl;dr"],
    "data_analysis": ["数据", "统计", "分析", "图表", "可视化", "csv", "excel", "dataset", "analyze", "analysis"],
    "workflow_planning": ["规划", "计划", "步骤", "分解", "排期", "里程碑", "todo", "roadmap", "workflow"],
}

_PURPOSE_INFER_CONFIDENCE_THRESHOLD = 0.72
_MASTER_AGENT_ALIASES = {"masteragent", "master_agent", "master"}
_PURPOSE_CLASSIFICATION_PROMPT = (
    "你是用途分类器。"
    "请将用户请求分类到以下purpose之一："
    "article_search,text_summarize,data_analysis,workflow_planning,general。"
    "必须仅返回JSON对象，格式为："
    '{"purpose":"general","confidence":0.0}。'
    "confidence取值范围[0,1]。"
)


class AgentRouter:
    """
    Agent 路由器。
    负责判断用户请求应由哪个子 Agent 处理，并提供委托执行能力。

    路由优先级：
      1. 参数中显式指定 agent_name
      2. 参数中显式指定 purpose
      3. 从 query 关键词快速推断 purpose
      4. 调用 LLM 推断 purpose（置信度须超过阈值）
      5. 由 MasterAgent 自身处理
    """

    def __init__(self, llm: Any, model_name: str) -> None:
        self._llm = llm
        self._model_name = model_name
        self._agent_cache: Dict[str, Any] = {}

    # ------------------------------------------------------------------ #
    # Purpose inference                                                     #
    # ------------------------------------------------------------------ #

    def infer_purpose_from_query(self, query: str) -> Optional[str]:
        """通过关键词快速推断 purpose（不调用 LLM）。"""
        normalized = (query or "").strip().lower()
        if not normalized:
            return None
        scores = {
            purpose: sum(1 for kw in kws if kw.lower() in normalized)
            for purpose, kws in _PURPOSE_KEYWORDS.items()
        }
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else None

    async def infer_purpose_with_llm(
        self, query: str, parameters: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """调用 LLM 推断 purpose，返回 {"purpose": ..., "confidence": ...} 或 None。"""
        if not query or len(query.strip()) < 4:
            return None

        requested_model = parameters.get("model_version") if isinstance(parameters, dict) else None
        model = requested_model or self._model_name
        try:
            response = await self._llm.chat_with_retry(
                model=model,
                messages=[
                    {"role": "system", "content": _PURPOSE_CLASSIFICATION_PROMPT},
                    {"role": "user", "content": query},
                ],
                response_format={"type": "json_object"},
                max_tokens=120,
                temperature=0,
            )
            if response.finish_reason == "error" or not response.content:
                return None

            parsed = parse_json_object(response.content)
            purpose = str(parsed.get("purpose", "")).strip().lower()
            if purpose not in _PURPOSE_AGENT_MAP:
                return None

            try:
                confidence = float(parsed.get("confidence", 0))
            except Exception:
                return None

            if confidence < _PURPOSE_INFER_CONFIDENCE_THRESHOLD:
                return None
            return {"purpose": purpose, "confidence": confidence}
        except Exception as exc:
            logger.warning("LLM purpose inference failed: %s", exc)
            return None

    # ------------------------------------------------------------------ #
    # Route resolution                                                      #
    # ------------------------------------------------------------------ #

    def resolve_route_target(
        self, query: str, parameters: Optional[Dict[str, Any]]
    ) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """
        同步路由解析（不调用 LLM）。
        返回 (target_agent, route_source, resolved_purpose)。
        """
        if isinstance(parameters, dict):
            explicit_agent = str(parameters.get("agent_name", "")).strip()
            if explicit_agent and explicit_agent.lower() not in _MASTER_AGENT_ALIASES:
                return explicit_agent, "agent_name", None

            purpose = str(parameters.get("purpose", "")).strip().lower()
            if purpose and purpose in _PURPOSE_AGENT_MAP:
                return _PURPOSE_AGENT_MAP[purpose], "purpose", purpose

        inferred = self.infer_purpose_from_query(query)
        if inferred and inferred in _PURPOSE_AGENT_MAP:
            return _PURPOSE_AGENT_MAP[inferred], "purpose_inferred", inferred

        return None, None, None

    # ------------------------------------------------------------------ #
    # Delegated agent factory                                               #
    # ------------------------------------------------------------------ #

    def get_or_create_agent(self, agent_name: str) -> Optional[Any]:
        """获取或创建（并缓存）委托子 Agent 实例。"""
        key = agent_name.strip().lower()
        if key in self._agent_cache:
            return self._agent_cache[key]

        instance: Optional[Any] = None
        if key == "article_query_agent":
            from agents.article_agent.graph import ArticleQueryAgent
            instance = ArticleQueryAgent()
        elif key == "text_agent":
            from agents.text_agent.graph import TextAgent
            instance = TextAgent(name="text_agent")
        elif key == "data_agent":
            from agents.data_agent.graph import DataAgent
            instance = DataAgent(name="data_agent")
        elif key == "workflow_agent":
            from agents.workflow_agent.graph import WorkflowAgent
            instance = WorkflowAgent(name="workflow_agent")

        if instance is not None:
            self._agent_cache[key] = instance
        return instance

    # ------------------------------------------------------------------ #
    # Task & answer helpers                                                 #
    # ------------------------------------------------------------------ #

    @staticmethod
    def build_task_for_agent(agent_name: str, request: Any) -> Dict[str, Any]:
        """根据目标 Agent 名称构建对应格式的任务字典。"""
        parameters = request.parameters if isinstance(request.parameters, dict) else {}
        key = agent_name.strip().lower()

        if key == "article_query_agent":
            return {"query": request.query, "limit": int(parameters.get("article_limit", 5))}
        if key == "text_agent":
            return {"type": "summarize", "text": request.query}
        if key == "data_agent":
            return {"type": "analyze", "data": {"input_text": request.query}}
        if key == "workflow_agent":
            return {"goal": request.query, "context": parameters.get("workflow_context", {})}
        return {"query": request.query, "input": request.query, "task": request.query}

    @staticmethod
    def extract_answer_from_agent_result(result: Any) -> str:
        """从子 Agent 返回结果中提取文本答案。"""
        if isinstance(result, dict):
            if result.get("answer"):
                return str(result["answer"])
            if result.get("summary"):
                return str(result["summary"])
            if result.get("result") is not None:
                v = result["result"]
                return v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
            return json.dumps(result, ensure_ascii=False)
        return "" if result is None else str(result)
