# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class NotificationStatus(Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DELIVERED = "delivered"
    BOUNCED = "bounced"


class NotificationPriority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


@dataclass
class Notification:
    id: str
    channel: str
    recipient: str
    subject: str
    body: str
    body_html: str = ""
    priority: NotificationPriority = NotificationPriority.NORMAL
    metadata: dict = field(default_factory=dict)
    status: NotificationStatus = NotificationStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sent_at: Optional[datetime] = None
    error: Optional[str] = None


@dataclass
class NotificationResult:
    notification_id: str
    channel: str
    status: NotificationStatus
    provider_message_id: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: Optional[str] = None


@dataclass
class ChannelCapabilities:
    html: bool = False
    attachments: bool = False
    batch: bool = False
    scheduling: bool = False


@dataclass
class NotificationHealth:
    channels: dict[str, str] = field(default_factory=dict)
    enabled: bool = True
