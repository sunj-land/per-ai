import time
import hmac
import hashlib
import base64
import urllib.parse
import httpx
from typing import Dict, Any
from app.core.channel.base import BaseAdapter

class DingTalkAdapter(BaseAdapter):
    def validate_config(self) -> bool:
        return "webhook_url" in self.config

    def _get_signed_url(self, url: str, secret: str) -> str:
        timestamp = str(round(time.time() * 1000))
        secret_enc = secret.encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, secret)
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code).decode('utf-8'))
        
        separator = "&" if "?" in url else "?"
        return f"{url}{separator}timestamp={timestamp}&sign={sign}"

    async def send_text(self, content: str) -> Dict[str, Any]:
        url = self.config.get("webhook_url")
        secret = self.config.get("secret")
        
        if secret:
            url = self._get_signed_url(url, secret)
            
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
        url = self.config.get("webhook_url")
        secret = self.config.get("secret")
        
        if secret:
            url = self._get_signed_url(url, secret)
            
        # Truncate content to avoid exceeding DingTalk's length limit (approx 20,000 bytes)
        encoded_content = content.encode('utf-8')
        if len(encoded_content) > 18000:
            content = encoded_content[:18000].decode('utf-8', 'ignore') + "\n...(truncated)"
            
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": content
            }
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload)
            return resp.json()
