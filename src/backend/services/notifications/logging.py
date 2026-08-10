# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
import logging
from typing import Optional

from .models import NotificationResult, NotificationStatus

logger = logging.getLogger("palmshed.notifications.audit")


class NotificationLogger:
    def log_result(self, result: NotificationResult) -> None:
        entry = {
            "id": result.notification_id,
            "channel": result.channel,
            "status": result.status.value,
            "provider_message_id": result.provider_message_id,
        }
        if result.error:
            entry["error"] = result.error
        logger.info("notification_event", extra=entry)

    def log_send(
        self,
        notification_id: str,
        channel: str,
        status: NotificationStatus,
        error: Optional[str] = None,
    ) -> None:
        entry = {
            "id": notification_id,
            "channel": channel,
            "status": status.value,
        }
        if error:
            entry["error"] = error
        logger.info("notification_event", extra=entry)
