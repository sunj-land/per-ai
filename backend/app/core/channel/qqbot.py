import httpx
import json
import logging
from typing import Dict, Any, List
from app.core.channel.base import BaseAdapter

logger = logging.getLogger(__name__)

class QQBotAdapter(BaseAdapter):
    """
    Adapter for QQ Official Bot (QQ Open Platform)
    API: https://bot.q.qq.com/wiki/develop/api/
    """

    BASE_URL_SANDBOX = "https://sandbox.api.sgroup.qq.com"
    BASE_URL_PROD = "https://api.sgroup.qq.com"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.app_id = config.get("appId")
        self.client_secret = config.get("secret")
        # "allowFrom" usually contains the OpenIDs that are allowed/targeted
        self.targets: List[str] = config.get("allowFrom", [])
        self.is_sandbox = config.get("sandbox", False)
        self.base_url = self.BASE_URL_SANDBOX if self.is_sandbox else self.BASE_URL_PROD
        self.access_token = None

    def validate_config(self) -> bool:
        return bool(self.app_id and self.client_secret)

    def _clean_urls_and_html(self, text: str, max_length: int = 800) -> str:
        import re
        if not text:
            return text

        # 1. Replace <br> and <p> tags with newlines to preserve paragraph structure
        text = re.sub(r'(?i)<br\s*/?>', '\n', text)
        text = re.sub(r'(?i)</p>', '\n\n', text)
        text = re.sub(r'(?i)</div>', '\n', text)

        # 2. Remove all remaining HTML tags
        cleaned = re.sub(r'<[^>]+>', '', text)

        # 3. Unescape common HTML entities
        cleaned = cleaned.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('&quot;', '"')

        # 4. Strip markdown link syntax [text](url) -> text
        cleaned = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', cleaned)

        # 5. Remove or replace markdown image syntax ![text](url) -> [图片]
        cleaned = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'[图片]', cleaned)

        # 6. Handle literal links
        cleaned = cleaned.replace("http://", "http_//").replace("https://", "https_//")

        # 7. For very strict bots, even domains like www.jiemian.com or img.jiemian.com can be flagged.
        cleaned = re.sub(r'([a-zA-Z0-9][-a-zA-Z0-9]{0,62})\.(com|cn|net|org)', r'\1_\2', cleaned)

        # 8. Clean up excessive newlines and spaces
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        cleaned = cleaned.strip()

        # 9. Truncate if too long
        if len(cleaned) > max_length:
            cleaned = cleaned[:max_length] + "...\n(内容过长，已截断)"

        return cleaned

    async def _get_access_token(self) -> str:
        """Fetch access token from QQ Bot API"""
        url = "https://bots.qq.com/app/getAppAccessToken"
        payload = {
            "appId": self.app_id,
            "clientSecret": self.client_secret
        }

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(url, json=payload, timeout=10.0)
                resp.raise_for_status()
                data = resp.json()
                if "access_token" in data:
                    return data["access_token"]
                else:
                    logger.error(f"Failed to get access token: {data}")
                    raise ValueError(f"Failed to get access token: {data}")
            except Exception as e:
                logger.error(f"Error fetching QQ Bot token: {e}")
                raise

    async def _send_to_openid(self, openid: str, content: str, msg_type: int = 0, markdown: Dict = None) -> Dict[str, Any]:
        """
        Send message to a specific OpenID (Group or User).
        Since we don't know if the OpenID is a Group or C2C user from the ID itself easily,
        we might need to try both or rely on config.
        However, the standard OpenID usually has a prefix or specific length, but it's tricky.

        Common strategy: Try Group first, if fails with specific error, try User?
        Or, just assume Group for now as that's common for bots.
        """
        if not self.access_token:
            self.access_token = await self._get_access_token()

        headers = {
            "Authorization": f"QQBot {self.access_token}",
            "X-Union-Appid": self.app_id
        }

        # For active message (v2), use specific endpoints
        # Try sending to Group (v2/groups/{group_openid}/messages)
        url_group = f"{self.base_url}/v2/groups/{openid}/messages"

        # Note: QQ Open Platform has strict restrictions on URLs in regular text messages.
        # Sending URLs directly in text often triggers "40054010: 不允许发送url" error.
        # To bypass this safely, we will extract the URLs or convert them.
        # However, even markdown might be restricted for some bots unless specifically applied for.
        # For now, we just pass the text as is. If the user hits URL error, they should send markdown.

        is_markdown = False
        if markdown is not None:
             is_markdown = True
        elif msg_type == 2:
             is_markdown = True

        safe_content = self._clean_urls_and_html(content)

        if not is_markdown and ("http://" in content or "https://" in content):
             # Upgrade to markdown dynamically, but still use safe content to avoid rejection
             is_markdown = True
             # If no markdown payload is provided, build a generic one
             if not markdown:
                  markdown = {"content": safe_content}
        elif markdown and "content" in markdown:
             # Ensure markdown content also escapes urls
             md_content = markdown["content"]
             safe_md = self._clean_urls_and_html(md_content)
             markdown["content"] = safe_md

        # Payload for v2 group message
        data = {
            "content": safe_content if not is_markdown else "请查看卡片消息",
            "msg_type": 2 if is_markdown else 0, # 0: Text, 2: Markdown
        }

        if is_markdown and markdown:
             # Ensure markdown also uses safe content if we generated it
             data["markdown"] = markdown

        # We need a unique msg_id for deduplication, but for active push, it might be optional or generated
        # Actually, for passive reply we need msg_id. For active push...
        # Let's try sending to Group first.

        async with httpx.AsyncClient() as client:
            try:
                # 1. Try Group
                resp = await client.post(url_group, json=data, headers=headers, timeout=10.0)
                if resp.status_code == 200:
                    return resp.json()

                logger.warning(f"Failed to send to Group {openid}: {resp.status_code} {resp.text}. Trying User...")

                # 2. Try User (C2C)
                url_user = f"{self.base_url}/v2/users/{openid}/messages"
                resp_user = await client.post(url_user, json=data, headers=headers, timeout=10.0)
                if resp_user.status_code == 200:
                    return resp_user.json()
                else:
                    error_msg = f"Client error '{resp_user.status_code}' for url '{url_user}'\nResponse: {resp_user.text}"
                    logger.error(f"Failed to send to User {openid}: {error_msg}")
                    raise Exception(error_msg)

            except Exception as e:
                logger.error(f"Failed to send QQ message to {openid}: {e}")
                raise

    async def send_text(self, content: str) -> Dict[str, Any]:
        if not self.targets:
            raise ValueError("No targets (allowFrom) configured for QQ Bot")

        results = {}
        success_count = 0
        for target in self.targets:
            try:
                res = await self._send_to_openid(target, content)
                results[target] = res
                if isinstance(res, dict) and res.get("code") and res.get("code") != 0:
                    pass
                else:
                    success_count += 1
            except Exception as e:
                results[target] = {"error": str(e)}

        if success_count == 0 and self.targets:
            raise Exception(f"All QQ Bot targets failed: {json.dumps(results)}")

        return results

    async def receive(self, payload: Dict[str, Any]) -> Any:
        """Handle incoming webhook payload from QQBot"""
        # Extract content
        msg_data = payload.get("d", payload)
        content = msg_data.get("content", "").strip()

        author = msg_data.get("author", {})
        sender_id = author.get("id", "")

        if not content:
            return {"status": "ignored", "reason": "empty content"}

        import re
        content = re.sub(r'<@!\d+>\s*', '', content).strip()

        from app.core.bus import bus
        from app.core.bus.events import InboundMessage

        msg = InboundMessage(
            channel="qqbot",
            sender_id=sender_id,
            chat_id="qqbot-default",
            content=content,
            metadata={"channel_id": self.channel_id}
        )

        await bus.publish_inbound(msg)

        return {"status": "ok", "message": "processing"}

    async def send_markdown(self, title: str, content: str) -> Dict[str, Any]:
        # QQ Bot Markdown format is specific.
        # Simple markdown payload

        # We should use custom markdown template if we have one,
        # but for open platform, generic markdown needs to be enabled for the bot.
        # Also escape URLs here to prevent 40054010 error if not authorized
        safe_content = self._clean_urls_and_html(content)
        markdown_content = f"# {title}\n{safe_content}"

        markdown = {
            "content": markdown_content
        }

        if not self.targets:
             raise ValueError("No targets (allowFrom) configured for QQ Bot")

        results = {}
        success_count = 0
        for target in self.targets:
            try:
                res = await self._send_to_openid(target, "markdown", msg_type=2, markdown=markdown)
                results[target] = res
                if isinstance(res, dict) and res.get("code") and res.get("code") != 0:
                    pass
                else:
                    success_count += 1
            except Exception as e:
                results[target] = {"error": str(e)}

        if success_count == 0 and self.targets:
            raise Exception(f"All QQ Bot targets failed: {json.dumps(results)}")

        return results
