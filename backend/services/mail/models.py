# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class MailStatus(Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"


class MailPriority(Enum):
    BULK = "bulk"
    NORMAL = "normal"
    HIGH = "high"


@dataclass
class Attachment:
    filename: str
    content: bytes
    mime_type: str


@dataclass
class Address:
    email: str
    name: Optional[str] = None

    def formatted(self) -> str:
        if self.name:
            return f"{self.name} <{self.email}>"
        return self.email


@dataclass
class MailMessage:
    template: str
    recipient: Address
    context: dict = field(default_factory=dict)
    subject_override: Optional[str] = None
    reply_to: Optional[str] = None
    cc: list[Address] = field(default_factory=list)
    bcc: list[Address] = field(default_factory=list)
    attachments: list[Attachment] = field(default_factory=list)
    priority: MailPriority = MailPriority.NORMAL
    metadata: dict = field(default_factory=dict)

    sender: Address = field(
        default_factory=lambda: Address(
            email="hello@palmshed.dev",
            name="Palmshed",
        )
    )

    id: Optional[str] = None
    status: MailStatus = MailStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = None
    retry_count: int = 0


@dataclass
class MailResult:
    mail_id: str
    status: MailStatus
    provider: str
    provider_message_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    retry_count: int = 0
    error: Optional[str] = None


@dataclass
class ProviderCapabilities:
    html: bool = True
    attachments: bool = True
    inline_images: bool = False
    scheduling: bool = False


@dataclass
class RetryPolicy:
    max_retries: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    backoff_factor: float = 2.0

    def delay_for(self, attempt: int) -> float:
        delay = self.base_delay_seconds * (self.backoff_factor**attempt)
        return min(delay, self.max_delay_seconds)


@dataclass
class HealthStatus:
    provider: str
    provider_capabilities: ProviderCapabilities
    queue_running: bool
    queue_depth: int
    config_valid: bool
    config_errors: list[str]
    templates_valid: bool
    template_count: int
