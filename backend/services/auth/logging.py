# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
import logging
from typing import Optional

from .models import AuthResult, AuthStatus

logger = logging.getLogger("palmshed.auth.audit")


class AuthLogger:
    def log_auth_event(
        self,
        event: str,
        email: str,
        result: AuthResult,
        user_id: Optional[str] = None,
    ) -> None:
        entry = {
            "event": event,
            "email": email,
            "user_id": user_id or "",
            "status": result.status.value,
            "provider": result.provider,
        }
        if result.error:
            entry["error"] = result.error
        logger.info("auth_event", extra=entry)

    def log_failure(
        self,
        event: str,
        email: str,
        error: str,
        provider: str = "",
        user_id: Optional[str] = None,
    ) -> None:
        entry = {
            "event": event,
            "email": email,
            "user_id": user_id or "",
            "status": AuthStatus.FAILED.value,
            "provider": provider,
            "error": error,
        }
        logger.info("auth_event", extra=entry)
