# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
from __future__ import annotations

import logging
from typing import Optional

from services.auth.config import AuthConfig
from services.auth.service import AuthService
from services.mail.config import MailConfig
from services.mail.service import MailService
from services.notifications.config import NotificationConfig
from services.notifications.service import NotificationService
from services.storage.config import StorageConfig
from services.storage.service import StorageService

logger = logging.getLogger("palmshed.platform")


class PlatformHealth:
    def __init__(self) -> None:
        self.status: str = "ok"
        self.services: dict[str, dict] = {}
        self.errors: list[str] = []

    def to_dict(self) -> dict:
        result: dict = {"status": self.status}
        result.update(self.services)
        if self.errors:
            result["errors"] = self.errors
        return result


class PlatformManager:
    def __init__(self) -> None:
        self._mail: Optional[MailService] = None
        self._auth: Optional[AuthService] = None
        self._storage: Optional[StorageService] = None
        self._notifications: Optional[NotificationService] = None

    @property
    def mail(self) -> MailService:
        if self._mail is None:
            config = MailConfig.from_env()
            self._mail = MailService(config=config)
        return self._mail

    @property
    def auth(self) -> AuthService:
        if self._auth is None:
            config = AuthConfig.from_env()
            self._auth = AuthService(config=config)
        return self._auth

    @property
    def storage(self) -> StorageService:
        if self._storage is None:
            config = StorageConfig.from_env()
            self._storage = StorageService(config=config)
        return self._storage

    @property
    def notifications(self) -> NotificationService:
        if self._notifications is None:
            config = NotificationConfig.from_env()
            self._notifications = NotificationService(
                config=config,
                mail_service=self.mail,
            )
        return self._notifications

    def health(self) -> PlatformHealth:
        health = PlatformHealth()

        for name, svc in [
            ("mail", self._try("mail", lambda: self.mail)),
            ("auth", self._try("auth", lambda: self.auth)),
            ("storage", self._try("storage", lambda: self.storage)),
            ("notifications", self._try("notifications", lambda: self.notifications)),
        ]:
            if svc is not None:
                try:
                    health.services[name] = self._service_health(name, svc)
                except Exception as exc:
                    health.services[name] = {"error": str(exc)}
                    health.errors.append(f"{name}: {exc}")
                    logger.warning("%s health check failed: %s", name, exc)
            else:
                health.services[name] = {"error": "service unavailable"}

        if health.errors:
            health.status = "degraded"

        return health

    def shutdown(self, timeout: float = 5.0) -> None:
        if self._mail is not None:
            try:
                self._mail.shutdown(timeout)
            except Exception as exc:
                logger.warning("Mail shutdown error: %s", exc)

    def _try(self, name: str, fn):
        try:
            return fn()
        except Exception as exc:
            logger.warning("Failed to initialize %s: %s", name, exc)
            return None

    def _service_health(self, name: str, svc) -> dict:
        if name == "mail":
            h = svc.health()
            return {
                "provider": h.provider,
                "config_valid": h.config_valid,
                "queue_running": h.queue_running,
                "queue_depth": h.queue_depth,
                "templates_valid": h.templates_valid,
                "template_count": h.template_count,
            }
        if name == "auth":
            h = svc.health()
            return {
                "provider": h.provider,
                "config_valid": h.config_valid,
            }
        if name == "storage":
            h = svc.health()
            return {
                "provider": h.provider,
                "config_valid": h.config_valid,
                "bucket": h.bucket,
                "healthy": h.healthy,
            }
        if name == "notifications":
            h = svc.health()
            return {
                "enabled": h.enabled,
                "channels": h.channels,
            }
        return {}


platform = PlatformManager()
