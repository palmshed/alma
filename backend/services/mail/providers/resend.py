import base64
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone

from ..config import MailConfig
from ..models import MailMessage, MailResult, MailStatus, ProviderCapabilities
from .base import MailProvider

logger = logging.getLogger("palmshed.mail.resend")

BASE_URL = "https://api.resend.com/emails"


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
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if message.id:
            headers["X-Request-Id"] = message.id

        req = urllib.request.Request(
            BASE_URL,
            data=json.dumps(body).encode(),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                response_body = json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            logger.exception("Resend API error (HTTP %d)", exc.code)
            return MailResult(
                mail_id=message.id or "",
                status=MailStatus.FAILED,
                provider="resend",
                timestamp=datetime.now(timezone.utc),
                retry_count=message.retry_count,
                error=self._parse_error(exc),
            )
        except urllib.error.URLError as exc:
            logger.exception("Resend connection error")
            return MailResult(
                mail_id=message.id or "",
                status=MailStatus.FAILED,
                provider="resend",
                timestamp=datetime.now(timezone.utc),
                retry_count=message.retry_count,
                error=str(exc.reason),
            )
        except Exception as exc:
            logger.exception("Resend unexpected error")
            return MailResult(
                mail_id=message.id or "",
                status=MailStatus.FAILED,
                provider="resend",
                timestamp=datetime.now(timezone.utc),
                retry_count=message.retry_count,
                error=str(exc),
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
                body["attachments"].append({
                    "filename": att.filename,
                    "content": base64.b64encode(att.content).decode(),
                    "content_type": att.mime_type,
                })

        return body

    @staticmethod
    def _parse_error(exc: urllib.error.HTTPError) -> str:
        try:
            detail = json.loads(exc.read())
            return detail.get("message", detail.get("name", str(exc.code)))
        except Exception:
            return str(exc.code)
