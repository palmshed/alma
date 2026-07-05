import logging

from ..models import (
    ChannelCapabilities,
    Notification,
    NotificationResult,
    NotificationStatus,
)
from .base import NotificationChannel

logger = logging.getLogger("palmshed.notifications.mock")


class MockChannel(NotificationChannel):
    def __init__(self, **kwargs) -> None:
        self.sent: list[Notification] = []
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
        self.sent.append(notification)
        logger.info(
            "Mock notify: channel=%s to=%s subject=%s",
            notification.channel,
            notification.recipient,
            notification.subject,
        )
        return NotificationResult(
            notification_id=notification.id,
            channel="mock",
            status=NotificationStatus.SENT,
        )

    def health(self) -> bool:
        return True

    def reset(self) -> None:
        self.sent.clear()
