import logging
from datetime import datetime, timezone
from typing import Optional

from services.mail import MailTemplate
from services.mail.service import MailService

from ..models import (
    ChannelCapabilities,
    Notification,
    NotificationResult,
    NotificationStatus,
)
from .base import NotificationChannel

logger = logging.getLogger("palmshed.notifications.email")


class EmailChannel(NotificationChannel):
    def __init__(self, mail_service: Optional[MailService] = None, **kwargs) -> None:
        self._mail = mail_service or MailService()
        self._capabilities = ChannelCapabilities(
            html=True,
            attachments=True,
            batch=False,
            scheduling=False,
        )

    @property
    def capabilities(self) -> ChannelCapabilities:
        return self._capabilities

    def send(self, notification: Notification) -> NotificationResult:
        try:
            msg = self._mail.send(
                template=MailTemplate.NOTIFICATION,
                recipient=notification.recipient,
                context={
                    "subject": notification.subject,
                    "body": notification.body,
                    "product": notification.metadata.get("product", "Palmshed"),
                },
            )
            return NotificationResult(
                notification_id=notification.id,
                channel="email",
                status=NotificationStatus.SENT,
                provider_message_id=msg.id,
                timestamp=datetime.now(timezone.utc),
            )
        except Exception as exc:
            logger.error("Email notification failed: %s", exc)
            return NotificationResult(
                notification_id=notification.id,
                channel="email",
                status=NotificationStatus.FAILED,
                error=str(exc),
            )

    def health(self) -> bool:
        try:
            self._mail.health()
            return True
        except Exception:
            return False
