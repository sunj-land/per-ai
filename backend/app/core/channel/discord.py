import logging
import httpx
import time
from typing import Dict, Any
from app.core.channel.base import BaseAdapter

logger = logging.getLogger(__name__)

DISCORD_API_BASE = "https://discord.com/api/v10"

class DiscordAdapter(BaseAdapter):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.token = self.config.get("token")
        self.channel_id = self.config.get("channel_id")
        self.webhook_url = self.config.get("webhook_url")

    def validate_config(self) -> bool:
        if not self.webhook_url and (not self.token or not self.channel_id):
            logger.error("DiscordAdapter requires either webhook_url or (token + channel_id)")
            return False
        return True

    async def authenticate(self) -> bool:
        return True # Discord uses static token/webhook

    async def send_text(self, content: str) -> Dict[str, Any]:
        return await self._send_message({"content": content})

    async def send_markdown(self, title: str, content: str) -> Dict[str, Any]:
        payload = {
            "embeds": [
                {
                    "title": title,
                    "description": content,
                    "color": 3447003 # Default blue
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
                    return {"status": "success"}

            elif self.token and self.channel_id:
                headers = {"Authorization": f"Bot {self.token}"}
                url = f"{DISCORD_API_BASE}/channels/{self.channel_id}/messages"
                async with httpx.AsyncClient() as client:
                    resp = await client.post(url, json=payload, headers=headers, timeout=10.0)
                    resp.raise_for_status()
                    success = True
                    return resp.json()
            else:
                raise ValueError("Incomplete configuration for sending Discord message")
        except Exception as e:
            logger.error(f"Failed to send Discord message: {e}")
            raise
        finally:
            self.record_metric(success, (time.time() - start_time) * 1000)

    async def receive(self, payload: Dict[str, Any]) -> Any:
        # Example of handling an incoming payload from Discord (if using an interaction endpoint)
        return {"status": "received", "data": payload}
