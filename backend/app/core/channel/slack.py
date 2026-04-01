import logging
import httpx
import time
from typing import Dict, Any
from app.core.channel.base import BaseAdapter

logger = logging.getLogger(__name__)

SLACK_API_BASE = "https://slack.com/api"

class SlackAdapter(BaseAdapter):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.bot_token = self.config.get("bot_token")
        self.channel_id = self.config.get("channel_id")
        self.webhook_url = self.config.get("webhook_url")

    def validate_config(self) -> bool:
        if not self.webhook_url and (not self.bot_token or not self.channel_id):
            logger.error("SlackAdapter requires either webhook_url or (bot_token + channel_id)")
            return False
        return True

    async def authenticate(self) -> bool:
        return True

    async def send_text(self, content: str) -> Dict[str, Any]:
        return await self._send_message({"text": content})

    async def send_markdown(self, title: str, content: str) -> Dict[str, Any]:
        payload = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": title
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": content
                    }
                }
            ]
        }
        return await self._send_message(payload)

    async def _send_message(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.time()
        success = False
        try:
            if self.webhook_url:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(self.webhook_url, json=payload, timeout=10.0)
                    resp.raise_for_status()
                    success = True
                    return {"status": "success", "response": resp.text}

            elif self.bot_token and self.channel_id:
                headers = {"Authorization": f"Bearer {self.bot_token}"}
                payload["channel"] = self.channel_id
                url = f"{SLACK_API_BASE}/chat.postMessage"
                async with httpx.AsyncClient() as client:
                    resp = await client.post(url, json=payload, headers=headers, timeout=10.0)
                    resp.raise_for_status()
                    data = resp.json()
                    if not data.get("ok"):
                        raise ValueError(f"Slack API error: {data.get('error')}")
                    success = True
                    return data
            else:
                raise ValueError("Incomplete configuration for sending Slack message")
        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}")
            raise
        finally:
            self.record_metric(success, (time.time() - start_time) * 1000)

    async def receive(self, payload: Dict[str, Any]) -> Any:
        # Example of handling an incoming event from Slack Events API
        if "challenge" in payload:
            return {"challenge": payload["challenge"]}
        return {"status": "received", "data": payload}
