# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
import time
from typing import Optional

from .config import AuthConfig
from .logging import AuthLogger
from .metrics import AuthMetrics
from .models import AuthHealthStatus, AuthResult, AuthStatus
from .providers import AuthProvider, get_provider


class AuthError(Exception):
    pass


class AuthValidationError(AuthError):
    pass


class AuthService:
    def __init__(
        self,
        config: Optional[AuthConfig] = None,
        provider: Optional[AuthProvider] = None,
        logger: Optional[AuthLogger] = None,
        metrics: Optional[AuthMetrics] = None,
    ) -> None:
        self.config = config or AuthConfig.from_env()
        self.provider = provider or get_provider(self.config)
        self.logger = logger or AuthLogger()
        self.metrics = metrics or AuthMetrics()

    def register(
        self,
        email: str,
        password: str,
        **kwargs,
    ) -> AuthResult:
        self._validate_email(email)
        self._validate_password(password)

        t0 = time.monotonic()
        result = self.provider.create_user(email, password, **kwargs)
        elapsed = time.monotonic() - t0
        self.metrics.record_duration(elapsed)

        self.logger.log_auth_event(
            "register",
            email,
            result,
            user_id=result.user.id if result.user else None,
        )

        if result.status == AuthStatus.SUCCESS:
            self.metrics.record_registration()
        else:
            self.metrics.record_failure()

        return result

    def login(self, email: str, password: str) -> AuthResult:
        self._validate_email(email)
        if not password:
            raise AuthValidationError("Password is required")

        t0 = time.monotonic()
        result = self.provider.authenticate(email, password)
        elapsed = time.monotonic() - t0
        self.metrics.record_duration(elapsed)

        self.logger.log_auth_event(
            "login",
            email,
            result,
            user_id=result.user.id if result.user else None,
        )

        if result.status == AuthStatus.SUCCESS:
            self.metrics.record_login()
        else:
            self.metrics.record_failure()

        return result

    def verify(self, token: str) -> AuthResult:
        if not token:
            raise AuthValidationError("Token is required")

        t0 = time.monotonic()
        result = self.provider.verify_token(token)
        elapsed = time.monotonic() - t0
        self.metrics.record_duration(elapsed)

        if result.status == AuthStatus.SUCCESS:
            self.metrics.record_verification()
        else:
            self.metrics.record_failure()

        return result

    def refresh(self, refresh_token: str) -> AuthResult:
        if not refresh_token:
            raise AuthValidationError("Refresh token is required")

        t0 = time.monotonic()
        result = self.provider.refresh_token(refresh_token)
        elapsed = time.monotonic() - t0
        self.metrics.record_duration(elapsed)

        if result.status == AuthStatus.SUCCESS:
            self.metrics.record_refresh()
        else:
            self.metrics.record_failure()

        return result

    def logout(self, refresh_token: str) -> None:
        if not refresh_token:
            raise AuthValidationError("Refresh token is required")
        self.provider.revoke_token(refresh_token)

    def health(self) -> AuthHealthStatus:
        valid, errors = self.config.is_valid()
        return AuthHealthStatus(
            provider=self.config.provider,
            config_valid=valid,
            config_errors=errors,
        )

    def _validate_email(self, email: str) -> None:
        if not email:
            raise AuthValidationError("Email is required")
        if "@" not in email or "." not in email.split("@")[-1]:
            raise AuthValidationError("Invalid email format")

    def _validate_password(self, password: str) -> None:
        if not password:
            raise AuthValidationError("Password is required")
        if len(password) < 8:
            raise AuthValidationError("Password must be at least 8 characters")
