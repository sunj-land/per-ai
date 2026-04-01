import json
import logging
import re
from typing import Any, Dict

from langgraph.graph import StateGraph, END

from core.agent import Agent
from core.state import StandardAgentState
from tools.article_search import ArticleSearchTool

logger = logging.getLogger(__name__)


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def build_article_agent_graph(article_search_tool: ArticleSearchTool):
    """
    构建文章搜索工作流（独立函数，可单独测试或复用）。

    :param article_search_tool: ArticleSearchTool 实例
    :return: 编译后的 CompiledStateGraph
    """

    async def _search_article_node(state: StandardAgentState) -> Dict[str, Any]:
        task = state.get("task", {})
        query = task.get("query", "")
        limit = task.get("limit", 5)
        filters = task.get("filters", {})

        logger.info("ArticleQueryAgent searching for: %s (limit=%d, filters=%s)", query, limit, filters)

        try:
            response_str = await article_search_tool.execute(
                query=query,
                limit=limit,
                start_time=filters.get("start_time"),
                end_time=filters.get("end_time"),
                feed_id=filters.get("feed_id"),
                group_id=filters.get("group_id"),
            )
            response_data = json.loads(response_str)
            if "error" in response_data:
                return {"error": response_data["error"]}
            return {"result": response_data}
        except Exception as e:
            logger.error("Error in ArticleQueryAgent: %s", e)
            return {"error": str(e)}

    workflow = StateGraph(StandardAgentState)
    workflow.add_node("search_article", _search_article_node)
    workflow.set_entry_point("search_article")
    workflow.add_edge("search_article", END)
    return workflow.compile()


class ArticleQueryAgent(Agent):
    """
    负责查询本地文章索引的子智能体。
    通过向量搜索技术，根据语义相似度检索相关文章。
    """

    def __init__(
        self,
        name: str = "article_query_agent",
        description: str = "Search articles by semantic similarity",
    ):
        super().__init__(name=name, description=description)
        self.article_search_tool = ArticleSearchTool()
        self.workflow = build_article_agent_graph(self.article_search_tool)

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        任务数据结构:
        {
            "query": "搜索关键字",
            "limit": 5,
            "filters": {"start_time": ..., "end_time": ..., "feed_id": ..., "group_id": ...}
        }
        """
        result = await self.workflow.ainvoke({"task": task})
        if result.get("error"):
            raise ValueError(result["error"])
        raw = result.get("result", {})

        articles = raw.get("articles", [])
        query = task.get("query", "")

        if not articles:
            answer = f"未找到{'与"' + query + '"相关的' if query else ''}文章。"
        else:
            header = f'搜索"{query}"，找到 {len(articles)} 篇相关文章：\n\n' if query else f'最新文章（共 {len(articles)} 篇）：\n\n'
            lines = []
            for i, art in enumerate(articles, 1):
                title = art.get("title", "无标题")
                link = art.get("link", "")
                feed_title = art.get("feed_title", "")
                published_at = art.get("published_at", "")
                author = art.get("author", "")
                summary = _strip_html(art.get("summary", "") or "")

                title_part = f"[{title}]({link})" if link else title
                meta_parts = []
                if feed_title:
                    meta_parts.append(f"📰 {feed_title}")
                if published_at:
                    date_str = published_at[:10] if len(published_at) >= 10 else published_at
                    meta_parts.append(f"📅 {date_str}")
                if author:
                    meta_parts.append(f"✍️ {author}")
                meta_line = " | ".join(meta_parts)

                summary_text = summary[:120].rstrip() + ("…" if len(summary) > 120 else "")

                entry = f"**{i}. {title_part}**"
                if meta_line:
                    entry += f"\n{meta_line}"
                if summary_text:
                    entry += f"\n> {summary_text}"
                lines.append(entry)

            answer = header + "\n\n".join(lines)

        return {"answer": answer, "result": raw}
