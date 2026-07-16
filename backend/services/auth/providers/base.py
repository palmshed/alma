# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
from abc import ABC, abstractmethod

from ..models import AuthResult


class AuthProvider(ABC):
    @abstractmethod
    def create_user(self, email: str, password: str, **kwargs) -> AuthResult: ...

    @abstractmethod
    def authenticate(self, email: str, password: str) -> AuthResult: ...

    @abstractmethod
    def verify_token(self, token: str) -> AuthResult: ...

    @abstractmethod
    def refresh_token(self, refresh_token: str) -> AuthResult: ...

    @abstractmethod
    def revoke_token(self, refresh_token: str) -> None: ...
