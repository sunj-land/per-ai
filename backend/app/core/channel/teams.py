import logging
import httpx
import time
from typing import Dict, Any, Optional
from app.core.channel.base import BaseAdapter

logger = logging.getLogger(__name__)

class TeamsAdapter(BaseAdapter):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.bot_id = self.config.get("bot_id")
        self.bot_password = self.config.get("bot_password")
        self.webhook_url = self.config.get("webhook_url")
        self.tenant_id = self.config.get("tenant_id")
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0

    def validate_config(self) -> bool:
        if not self.bot_id or not self.bot_password:
            # Depending on use case, Teams can also just use a webhook_url
            if not self.webhook_url:
                logger.error("TeamsAdapter requires either bot_id/bot_password or webhook_url")
                return False
        return True

    async def authenticate(self) -> bool:
        if not self.bot_id or not self.bot_password:
            return True # Using incoming webhook

        if self._access_token and time.time() < self._token_expires_at:
            return True

        url = "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.bot_id,
            "client_secret": self.bot_password,
            "scope": "https://api.botframework.com/.default"
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, data=data, timeout=10.0)
                resp.raise_for_status()
                token_data = resp.json()
                self._access_token = token_data.get("access_token")
                expires_in = token_data.get("expires_in", 3599)
                self._token_expires_at = time.time() + expires_in - 300
                logger.info("Teams authentication successful")
                return True
        except Exception as e:
            logger.error(f"Teams authentication failed: {e}")
            return False

    async def send_text(self, content: str) -> Dict[str, Any]:
        return await self._send_message({"type": "message", "text": content})

    async def send_markdown(self, title: str, content: str) -> Dict[str, Any]:
        payload = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.2",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": title,
                                "weight": "Bolder",
                                "size": "Medium"
                            },
                            {
                                "type": "TextBlock",
                                "text": content,
                                "wrap": True
                            }
                        ]
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
                # Send via Incoming Webhook
                async with httpx.AsyncClient() as client:
                    resp = await client.post(self.webhook_url, json=payload, timeout=10.0)
                    resp.raise_for_status()
                    success = True
                    return {"status": "success", "response": resp.text}

            elif self.bot_id and self.bot_password:
                # Send via Bot Framework (requires specific conversation ID, handled by custom logic usually)
                # This is a simplified version; real Teams bot requires conversation ID and service URL
                conversation_id = self.config.get("conversation_id")
                service_url = self.config.get("service_url")
                
                if not conversation_id or not service_url:
                    raise ValueError("Missing conversation_id or service_url for Bot Framework send")

                await self.authenticate()
                headers = {"Authorization": f"Bearer {self._access_token}"}
                url = f"{service_url}/v3/conversations/{conversation_id}/activities"
                
                async with httpx.AsyncClient() as client:
                    resp = await client.post(url, json=payload, headers=headers, timeout=10.0)
                    resp.raise_for_status()
                    success = True
                    return resp.json()
            else:
                raise ValueError("Incomplete configuration for sending Teams message")
        except Exception as e:
            logger.error(f"Failed to send Teams message: {e}")
            raise
        finally:
            self.record_metric(success, (time.time() - start_time) * 1000)

    async def receive(self, payload: Dict[str, Any]) -> Any:
        # Example of handling an incoming webhook payload from Teams
        if payload.get("type") == "message":
            text = payload.get("text", "")
            from_user = payload.get("from", {}).get("id", "unknown")
            return {"status": "received", "text": text, "user": from_user}
        return {"status": "ignored", "reason": "Not a message"}
