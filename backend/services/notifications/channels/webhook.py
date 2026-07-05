import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

from ..config import NotificationConfig
from ..models import (
    ChannelCapabilities,
    Notification,
    NotificationResult,
    NotificationStatus,
)
from .base import NotificationChannel

logger = logging.getLogger("palmshed.notifications.webhook")


class WebhookChannel(NotificationChannel):
    def __init__(self, config: Optional[NotificationConfig] = None, **kwargs) -> None:
        cfg = config or NotificationConfig.from_env()
        self._webhook_url = cfg.webhook_url
        self._timeout = cfg.webhook_timeout
        self._capabilities = ChannelCapabilities(
            html=False,
            attachments=False,
            batch=False,
            scheduling=False,
        )

    @property
    def capabilities(self) -> ChannelCapabilities:
        return self._capabilities

    def send(self, notification: Notification) -> NotificationResult:
        if not self._webhook_url:
            return NotificationResult(
                notification_id=notification.id,
                channel="webhook",
                status=NotificationStatus.FAILED,
                error="Webhook URL not configured",
            )

        payload = {
            "id": notification.id,
            "channel": notification.channel,
            "recipient": notification.recipient,
            "subject": notification.subject,
            "body": notification.body,
            "body_html": notification.body_html,
            "priority": notification.priority.value,
            "metadata": notification.metadata,
            "timestamp": notification.created_at.isoformat(),
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self._webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=self._timeout)
            logger.info(
                "Webhook sent: id=%s url=%s", notification.id, self._webhook_url
            )
            return NotificationResult(
                notification_id=notification.id,
                channel="webhook",
                status=NotificationStatus.SENT,
                timestamp=datetime.now(timezone.utc),
            )
        except Exception as exc:
            logger.error("Webhook failed: %s", exc)
            return NotificationResult(
                notification_id=notification.id,
                channel="webhook",
                status=NotificationStatus.FAILED,
                error=str(exc),
            )

    def health(self) -> bool:
        return bool(self._webhook_url)
