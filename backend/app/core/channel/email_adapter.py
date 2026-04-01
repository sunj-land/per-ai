import logging
import time
import smtplib
from email.message import EmailMessage
from typing import Dict, Any
import asyncio
from app.core.channel.base import BaseAdapter

logger = logging.getLogger(__name__)

class EmailAdapter(BaseAdapter):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.smtp_host = self.config.get("smtp_host")
        self.smtp_port = self.config.get("smtp_port", 587)
        self.smtp_user = self.config.get("smtp_user")
        self.smtp_pass = self.config.get("smtp_pass")
        self.from_address = self.config.get("from_address", self.smtp_user)
        self.to_address = self.config.get("to_address")

    def validate_config(self) -> bool:
        required = [self.smtp_host, self.smtp_user, self.smtp_pass, self.to_address]
        if not all(required):
            logger.error("EmailAdapter requires smtp_host, smtp_user, smtp_pass, and to_address")
            return False
        return True

    async def authenticate(self) -> bool:
        return True

    async def send_text(self, content: str) -> Dict[str, Any]:
        return await self._send_email(subject="Notification", content=content, is_html=False)

    async def send_markdown(self, title: str, content: str) -> Dict[str, Any]:
        # Basic conversion or just sending as text. In a real scenario, use markdown to html converter
        import markdown
        html_content = markdown.markdown(content)
        return await self._send_email(subject=title, content=html_content, is_html=True)

    async def _send_email(self, subject: str, content: str, is_html: bool) -> Dict[str, Any]:
        start_time = time.time()
        success = False
        try:
            msg = EmailMessage()
            msg['Subject'] = subject
            msg['From'] = self.from_address
            msg['To'] = self.to_address
            
            if is_html:
                msg.add_alternative(content, subtype='html')
            else:
                msg.set_content(content)

            await asyncio.to_thread(self._smtp_send, msg)
            success = True
            return {"status": "success"}
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise
        finally:
            self.record_metric(success, (time.time() - start_time) * 1000)

    def _smtp_send(self, msg: EmailMessage) -> None:
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_pass)
            server.send_message(msg)

    async def receive(self, payload: Dict[str, Any]) -> Any:
        # Handling incoming email would typically be done via IMAP or a webhook from SendGrid/Mailgun
        return {"status": "received", "data": payload}
