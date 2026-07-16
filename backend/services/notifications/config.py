# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
import os
from dataclasses import dataclass


@dataclass
class NotificationConfig:
    enabled: bool = True
    default_channel: str = "mock"
    webhook_url: str = ""
    webhook_timeout: int = 10

    @staticmethod
    def from_env() -> "NotificationConfig":
        return NotificationConfig(
            enabled=os.getenv("NOTIFICATIONS_ENABLED", "true").lower() == "true",
            default_channel=os.getenv("NOTIFICATIONS_DEFAULT_CHANNEL", "mock").lower(),
            webhook_url=os.getenv("NOTIFICATIONS_WEBHOOK_URL", ""),
            webhook_timeout=int(os.getenv("NOTIFICATIONS_WEBHOOK_TIMEOUT", "10")),
        )

    def is_valid(self) -> tuple[bool, list[str]]:
        errors: list[str] = []
        if self.default_channel not in ("mock", "email", "webhook"):
            errors.append(f"Unknown channel: {self.default_channel}")
        if self.default_channel == "webhook" and not self.webhook_url:
            errors.append("NOTIFICATIONS_WEBHOOK_URL is required for webhook channel")
        return (len(errors) == 0, errors)
