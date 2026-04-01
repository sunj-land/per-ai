import httpx
from typing import Dict, Any
from app.core.channel.base import BaseAdapter

class WechatWorkAdapter(BaseAdapter):
    """
    Enterprise WeChat (WeCom) Group Bot Adapter
    Docs: https://developer.work.weixin.qq.com/document/path/91770
    """
    
    def validate_config(self) -> bool:
        """
        Validate if the config is sufficient.
        WeCom Group Bot only requires a webhook_url.
        """
        return "webhook_url" in self.config

    async def send_text(self, content: str) -> Dict[str, Any]:
        """
        Send plain text message.
        """
        url = self.config.get("webhook_url")
        
        payload = {
            "msgtype": "text",
            "text": {
                "content": content
            }
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload)
            return resp.json()

    async def send_markdown(self, title: str, content: str) -> Dict[str, Any]:
        """
        Send markdown message.
        Note: WeCom markdown doesn't support a separate title field, so we prepend it.
        WeCom markdown size limit is 4096 bytes.
        """
        url = self.config.get("webhook_url")
        
        # Prepend title as H1 if provided
        full_content = f"# {title}\n{content}" if title else content
        
        # Truncate to 4096 bytes if necessary to prevent API rejection
        encoded_content = full_content.encode('utf-8')
        if len(encoded_content) > 4000:
            full_content = encoded_content[:4000].decode('utf-8', 'ignore') + "\n...(truncated)"
        
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": full_content
            }
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload)
            return resp.json()
