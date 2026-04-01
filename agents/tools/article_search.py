import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from tools.base import Tool
from service_client.backend_client import BackendServiceClient

logger = logging.getLogger(__name__)

class ArticleSearchTool(Tool):
    """
    Article Search Tool for article_agent.
    Supports semantic search, keyword matching, time range filtering, relevance sorting.
    """

    @property
    def name(self) -> str:
        return "article_search"

    @property
    def description(self) -> str:
        return (
            "在系统中检索文章。支持通过 query 进行语义搜索和关键词匹配，"
            "支持时间范围过滤 (start_time, end_time) 和相关性排序。"
            "当需要回答关于某个主题或获取特定时间段的新闻/文章时使用此工具。"
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词或自然语言问题，用于语义搜索和关键词匹配。如果为空，则返回最新文章列表。"
                },
                "limit": {
                    "type": "integer",
                    "description": "返回结果的最大数量，默认为 5，最大 50。",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 50
                },
                "start_time": {
                    "type": "string",
                    "description": "过滤起始时间，ISO 8601 格式 (YYYY-MM-DDTHH:MM:SSZ)。"
                },
                "end_time": {
                    "type": "string",
                    "description": "过滤结束时间，ISO 8601 格式 (YYYY-MM-DDTHH:MM:SSZ)。"
                },
                "feed_id": {
                    "type": "integer",
                    "description": "指定订阅源 ID 进行过滤。"
                },
                "group_id": {
                    "type": "integer",
                    "description": "指定分组 ID 进行过滤。"
                }
            }
        }

    async def execute(self, **kwargs: Any) -> str:
        """
        执行工具逻辑。
        """
        query = kwargs.get("query", "")
        limit = kwargs.get("limit", 5)
        start_time_str = kwargs.get("start_time")
        end_time_str = kwargs.get("end_time")
        feed_id = kwargs.get("feed_id")
        group_id = kwargs.get("group_id")

        client = BackendServiceClient()
        try:
            # Fetch more when time filtering is needed so we can trim after client-side filtering
            fetch_limit = 50 if (start_time_str or end_time_str) else limit

            try:
                articles = await client.get_articles(
                    limit=fetch_limit,
                    feed_id=feed_id,
                    group_id=group_id,
                    q=query if query else None,
                )
            except Exception as e:
                logger.error(f"Articles fetch failed: {e}")
                return json.dumps({"error": f"Fetch failed: {str(e)}"})

            # Client-side time filtering
            if start_time_str or end_time_str:
                filtered = []
                for art in articles:
                    pub_time_str = art.get("published_at")
                    if pub_time_str:
                        try:
                            pub_time = datetime.fromisoformat(pub_time_str.replace("Z", "+00:00"))
                            if start_time_str:
                                start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                                if pub_time < start_time:
                                    continue
                            if end_time_str:
                                end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
                                if pub_time > end_time:
                                    continue
                        except Exception as parse_e:
                            logger.warning(f"Time parse error: {parse_e}")
                    filtered.append(art)
                articles = filtered[:limit]

            summary = f"Found {len(articles)} relevant articles." if query else f"Retrieved {len(articles)} articles."
            return json.dumps({
                "count": len(articles),
                "articles": articles,
                "summary": summary,
            }, ensure_ascii=False)
        finally:
            await client.close()
