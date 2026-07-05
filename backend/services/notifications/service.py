import time
import uuid
from typing import Optional

from .channels import NotificationChannel, get_channel
from .config import NotificationConfig
from .logging import NotificationLogger
from .metrics import NotificationMetrics
from .models import (
    Notification,
    NotificationHealth,
    NotificationPriority,
    NotificationResult,
    NotificationStatus,
)


class NotificationError(Exception):
    pass


class NotificationService:
    def __init__(
        self,
        config: Optional[NotificationConfig] = None,
        default_channel: Optional[NotificationChannel] = None,
        mail_service=None,
        logger: Optional[NotificationLogger] = None,
        metrics: Optional[NotificationMetrics] = None,
    ) -> None:
        self.config = config or NotificationConfig.from_env()
        self._mail_service = mail_service
        self._default_channel_instance = default_channel
        self.logger = logger or NotificationLogger()
        self.metrics = metrics or NotificationMetrics()

    def _channel(self, name: str = "") -> NotificationChannel:
        if name:
            return get_channel(
                name, config=self.config, mail_service=self._mail_service
            )
        if self._default_channel_instance:
            return self._default_channel_instance
        return get_channel("", config=self.config, mail_service=self._mail_service)

    def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        channel: str = "",
        body_html: str = "",
        priority: NotificationPriority = NotificationPriority.NORMAL,
        metadata: Optional[dict] = None,
    ) -> NotificationResult:
        if not self.config.enabled:
            self.metrics.record_failed()
            return NotificationResult(
                notification_id="",
                channel=channel or self.config.default_channel,
                status=NotificationStatus.FAILED,
                error="Notifications are disabled",
            )

        notification = Notification(
            id=str(uuid.uuid4()),
            channel=channel or self.config.default_channel,
            recipient=recipient,
            subject=subject,
            body=body,
            body_html=body_html,
            priority=priority,
            metadata=metadata or {},
        )

        t0 = time.monotonic()
        try:
            chan = self._channel(channel)
            result = chan.send(notification)
        except Exception as exc:
            elapsed = time.monotonic() - t0
            self.metrics.record_duration(elapsed)
            self.metrics.record_failed()
            result = NotificationResult(
                notification_id=notification.id,
                channel=notification.channel,
                status=NotificationStatus.FAILED,
                error=str(exc),
            )
            self.logger.log_result(result)
            raise NotificationError(str(exc)) from exc

        elapsed = time.monotonic() - t0
        result.timestamp = result.timestamp
        self.metrics.record_duration(elapsed)

        if result.status == NotificationStatus.FAILED:
            self.metrics.record_failed()
        else:
            self.metrics.record_sent()

        self.logger.log_result(result)
        return result

    def health(self) -> NotificationHealth:
        channels = {}
        for name in ("mock", "email", "webhook"):
            try:
                chan = self._channel(name)
                channels[name] = "ok" if chan.health() else "unhealthy"
            except Exception:
                channels[name] = "unavailable"
        return NotificationHealth(
            channels=channels,
            enabled=self.config.enabled,
        )
