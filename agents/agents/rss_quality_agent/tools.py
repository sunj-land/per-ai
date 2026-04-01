import logging
import os
from typing import Any, Dict

import httpx

logger = logging.getLogger(__name__)


class RSSQualityScoringTool:
    """RSS 文章质量评分工具。"""

    def __init__(self) -> None:
        self.base_url = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8000")
        self.timeout = float(os.getenv("BACKEND_CLIENT_TIMEOUT_SECONDS", "20"))
        self.token = os.getenv("SERVICE_JWT_TOKEN", "change-me")

    async def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """调用后端 RSS 质量评分接口。"""

        self._validate_payload(payload)
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            response = await client.post(
                "/api/v1/agent-center/rss-quality/score",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict) and data.get("code") == 0:
                return data.get("data", {})
            return data

    def _validate_payload(self, payload: Dict[str, Any]) -> None:
        """校验评分任务参数。"""

        if not isinstance(payload, dict):
            raise ValueError("payload must be a dictionary")
        has_feed = payload.get("feed_id") is not None
        article_ids = payload.get("article_ids") or []
        if not has_feed and not article_ids:
            raise ValueError("feed_id or article_ids is required")
        concurrency = int(payload.get("concurrency", 5))
        if concurrency < 1 or concurrency > 20:
            raise ValueError("concurrency must be between 1 and 20")
