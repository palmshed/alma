# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
import os
from dataclasses import dataclass, field

from .models import RetryPolicy


@dataclass
class MailConfig:
    provider: str = "mock"
    from_email: str = "hello@palmshed.dev"
    from_name: str = "Palmshed"
    reply_to: str = ""
    sync: bool = False
    async_queue: bool = True
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_tls: bool = True
    timeout: int = 30
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    resend_api_key: str = ""

    max_recipients: int = 50
    max_attachment_size_mb: int = 10
    max_context_size_bytes: int = 65536

    @staticmethod
    def from_env() -> "MailConfig":
        return MailConfig(
            provider=os.getenv("MAIL_PROVIDER", "mock").lower(),
            from_email=os.getenv("MAIL_FROM_EMAIL", "hello@palmshed.dev"),
            from_name=os.getenv("MAIL_FROM_NAME", "Palmshed"),
            reply_to=os.getenv("MAIL_REPLY_TO", ""),
            sync=os.getenv("MAIL_SYNC", "false").lower() == "true",
            async_queue=os.getenv("MAIL_ASYNC", "true").lower() == "true",
            smtp_host=os.getenv("SMTP_HOST", "localhost"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_username=os.getenv("SMTP_USERNAME", ""),
            smtp_password=os.getenv("SMTP_PASSWORD", ""),
            smtp_tls=os.getenv("SMTP_TLS", "true").lower() == "true",
            timeout=int(os.getenv("MAIL_TIMEOUT", "30")),
            retry_policy=RetryPolicy(
                max_retries=int(os.getenv("MAIL_RETRY_MAX", "3")),
                base_delay_seconds=float(os.getenv("MAIL_RETRY_BASE_DELAY", "1.0")),
                max_delay_seconds=float(os.getenv("MAIL_RETRY_MAX_DELAY", "60.0")),
                backoff_factor=float(os.getenv("MAIL_RETRY_BACKOFF", "2.0")),
            ),
            resend_api_key=os.getenv("RESEND_API_KEY", ""),
            max_recipients=int(os.getenv("MAIL_MAX_RECIPIENTS", "50")),
            max_attachment_size_mb=int(os.getenv("MAIL_MAX_ATTACHMENT_MB", "10")),
            max_context_size_bytes=int(os.getenv("MAIL_MAX_CONTEXT_BYTES", "65536")),
        )

    @property
    def max_attachment_size_bytes(self) -> int:
        return self.max_attachment_size_mb * 1024 * 1024

    def is_valid(self) -> tuple[bool, list[str]]:
        errors: list[str] = []
        if self.provider not in ("mock", "smtp", "resend"):
            errors.append(f"Unknown provider: {self.provider}")
        if self.max_recipients < 1:
            errors.append("max_recipients must be >= 1")
        if self.max_attachment_size_mb < 0:
            errors.append("max_attachment_size_mb must be >= 0")
        if self.max_context_size_bytes < 1:
            errors.append("max_context_size_bytes must be >= 1")
        if self.smtp_host and not self.from_email:
            errors.append("from_email is required for SMTP")
        if self.provider == "resend" and not self.resend_api_key:
            errors.append("RESEND_API_KEY is required for Resend provider")
        return (len(errors) == 0, errors)
