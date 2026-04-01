import time
import hmac
import hashlib
import base64
import httpx
from typing import Dict, Any, Tuple
from app.core.channel.base import BaseAdapter

class FeishuAdapter(BaseAdapter):
    """
    Feishu (Lark) Custom Bot Adapter
    Docs: https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot
    """

    def validate_config(self) -> bool:
        """
        Validate config.
        Feishu requires a webhook_url. Secret is optional but recommended.
        """
        return "webhook_url" in self.config

    def _get_signature(self, secret: str) -> Tuple[str, str]:
        """
        Generate signature for Feishu bot.
        Algorithm:
        1. timestamp = current time in seconds
        2. string_to_sign = "{timestamp}\n{secret}"
        3. sign = Base64(HMAC-SHA256(string_to_sign))
        
        Returns: (timestamp, sign)
        """
        timestamp = str(int(time.time()))
        string_to_sign = '{}\n{}'.format(timestamp, secret)
        hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
        sign = base64.b64encode(hmac_code).decode('utf-8')
        return timestamp, sign

    async def send_text(self, content: str) -> Dict[str, Any]:
        """
        Send plain text message.
        """
        url = self.config.get("webhook_url")
        secret = self.config.get("secret")
        
        payload = {
            "msg_type": "text",
            "content": {
                "text": content
            }
        }
        
        if secret:
            timestamp, sign = self._get_signature(secret)
            payload["timestamp"] = timestamp
            payload["sign"] = sign
            
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload)
            return resp.json()

    async def send_markdown(self, title: str, content: str) -> Dict[str, Any]:
        """
        Send markdown message using Interactive Card.
        Feishu supports markdown via 'interactive' message type.
        """
        url = self.config.get("webhook_url")
        secret = self.config.get("secret")
        
        # Truncate content to avoid exceeding Feishu's limit (approx 30,000 bytes)
        encoded_content = content.encode('utf-8')
        if len(encoded_content) > 28000:
            content = encoded_content[:28000].decode('utf-8', 'ignore') + "\n...(truncated)"
            
        # Construct Interactive Card for Markdown
        card = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": title or "Notification"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": content
                }
            ]
        }
        
        payload = {
            "msg_type": "interactive",
            "card": card
        }
        
        if secret:
            timestamp, sign = self._get_signature(secret)
            payload["timestamp"] = timestamp
            payload["sign"] = sign
            
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload)
            return resp.json()
