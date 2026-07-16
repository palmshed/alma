# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
from .config import NotificationConfig
from .metrics import NotificationMetrics
from .models import (
    ChannelCapabilities,
    Notification,
    NotificationHealth,
    NotificationPriority,
    NotificationResult,
    NotificationStatus,
)
from .service import NotificationError, NotificationService
from .channels import (
    ChannelRegistry,
    EmailChannel,
    MockChannel,
    NotificationChannel,
    WebhookChannel,
    get_channel,
)

__all__ = [
    "NotificationConfig",
    "NotificationMetrics",
    "NotificationService",
    "Notification",
    "NotificationResult",
    "NotificationStatus",
    "NotificationPriority",
    "NotificationError",
    "NotificationHealth",
    "ChannelCapabilities",
    "NotificationChannel",
    "MockChannel",
    "EmailChannel",
    "WebhookChannel",
    "ChannelRegistry",
    "get_channel",
]
