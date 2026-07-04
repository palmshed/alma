import base64
import http.client
import json
import logging
from datetime import datetime, timezone

from ..config import MailConfig
from ..models import MailMessage, MailResult, MailStatus, ProviderCapabilities
from .base import MailProvider

logger = logging.getLogger("palmshed.mail.resend")

HOST = "api.resend.com"


class ResendProvider(MailProvider):
    def __init__(self, config: MailConfig) -> None:
        self.api_key = config.resend_api_key
        self.timeout = config.timeout
        self._capabilities = ProviderCapabilities(
            html=True,
            attachments=True,
            inline_images=True,
            scheduling=False,
        )

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def send(self, message: MailMessage) -> MailResult:
        body = self._build_payload(message)
        payload = json.dumps(body).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if message.id:
            headers["X-Request-Id"] = message.id

        conn = None
        try:
            conn = http.client.HTTPSConnection(HOST, timeout=self.timeout)
            conn.request("POST", "/emails", body=payload, headers=headers)
            resp = conn.getresponse()
            status = resp.status
            resp_data = resp.read()
        except Exception as exc:
            logger.exception("Resend request error")
            return MailResult(
                mail_id=message.id or "",
                status=MailStatus.FAILED,
                provider="resend",
                timestamp=datetime.now(timezone.utc),
                retry_count=message.retry_count,
                error=str(exc),
            )
        finally:
            if conn:
                conn.close()

        try:
            response_body = json.loads(resp_data)
        except Exception as exc:
            if status != 200:
                return MailResult(
                    mail_id=message.id or "",
                    status=MailStatus.FAILED,
                    provider="resend",
                    timestamp=datetime.now(timezone.utc),
                    retry_count=message.retry_count,
                    error=f"HTTP {status}",
                )
            return MailResult(
                mail_id=message.id or "",
                status=MailStatus.FAILED,
                provider="resend",
                timestamp=datetime.now(timezone.utc),
                retry_count=message.retry_count,
                error=f"Failed to parse response JSON: {exc}",
            )

        if status != 200:
            return MailResult(
                mail_id=message.id or "",
                status=MailStatus.FAILED,
                provider="resend",
                timestamp=datetime.now(timezone.utc),
                retry_count=message.retry_count,
                error=response_body.get(
                    "message", response_body.get("name", f"HTTP {status}")
                ),
            )

        return MailResult(
            mail_id=message.id or "",
            status=MailStatus.SENT,
            provider="resend",
            provider_message_id=response_body.get("id"),
            timestamp=datetime.now(timezone.utc),
            retry_count=message.retry_count,
        )

    def _build_payload(self, message: MailMessage) -> dict:
        body: dict = {
            "from": message.sender.formatted(),
            "to": [message.recipient.email],
            "subject": message.subject_override or "",
        }

        if "html_body" in message.context:
            body["html"] = message.context["html_body"]
        if "text_body" in message.context:
            body["text"] = message.context["text_body"]

        if message.reply_to:
            body["reply_to"] = message.reply_to

        if message.cc:
            body["cc"] = [a.email for a in message.cc]
        if message.bcc:
            body["bcc"] = [a.email for a in message.bcc]

        if message.attachments:
            body["attachments"] = []
            for att in message.attachments:
                body["attachments"].append(
                    {
                        "filename": att.filename,
                        "content": base64.b64encode(att.content).decode(),
                        "content_type": att.mime_type,
                    }
                )

        return body
