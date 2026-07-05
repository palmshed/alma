from typing import Optional

from ..config import NotificationConfig
from .base import NotificationChannel
from .email import EmailChannel
from .mock import MockChannel
from .registry import ChannelRegistry
from .webhook import WebhookChannel

ChannelRegistry.register("mock", MockChannel)
ChannelRegistry.register("email", EmailChannel)
ChannelRegistry.register("webhook", WebhookChannel)


def get_channel(
    name: str = "",
    config: Optional[NotificationConfig] = None,
    mail_service=None,
) -> NotificationChannel:
    cfg = config or NotificationConfig.from_env()
    channel_name = name or cfg.default_channel
    kwargs = {}
    if channel_name == "email":
        kwargs["mail_service"] = mail_service
    if channel_name == "webhook":
        kwargs["config"] = cfg
    return ChannelRegistry.create(channel_name, **kwargs)


__all__ = [
    "NotificationChannel",
    "MockChannel",
    "EmailChannel",
    "WebhookChannel",
    "ChannelRegistry",
    "get_channel",
]
