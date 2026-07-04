import logging
from datetime import datetime, timezone
from typing import Optional

from ..config import MailConfig
from ..models import MailMessage, MailResult, MailStatus, ProviderCapabilities
from .base import MailProvider

logger = logging.getLogger("palmshed.mail.mock")


class MockProvider(MailProvider):
    def __init__(self, config: Optional[MailConfig] = None) -> None:
        self.sent: list[MailMessage] = []
        self._capabilities = ProviderCapabilities(
            html=True,
            attachments=True,
            inline_images=False,
            scheduling=False,
        )

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def send(self, message: MailMessage) -> MailResult:
        self.sent.append(message)
        logger.info(
            "Mock send: to=%s template=%s",
            message.recipient.email,
            message.template,
        )
        return MailResult(
            mail_id=message.id or "",
            status=MailStatus.SENT,
            provider="mock",
            timestamp=datetime.now(timezone.utc),
            retry_count=message.retry_count,
        )

    def reset(self) -> None:
        self.sent.clear()
