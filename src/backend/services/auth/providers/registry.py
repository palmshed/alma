# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
from typing import Optional

from ..config import AuthConfig
from .base import AuthProvider


class ProviderRegistry:
    _providers: dict[str, type[AuthProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_cls: type[AuthProvider]) -> None:
        cls._providers[name] = provider_cls

    @classmethod
    def create(cls, name: str, config: AuthConfig) -> AuthProvider:
        provider_cls = cls._providers.get(name)
        if not provider_cls:
            registered = ", ".join(cls.available())
            raise ValueError(
                f"Unknown auth provider '{name}'. Registered: {registered}"
            )
        return provider_cls(config)

    @classmethod
    def available(cls) -> list[str]:
        return list(cls._providers.keys())

    @classmethod
    def get(cls, name: str) -> Optional[type[AuthProvider]]:
        return cls._providers.get(name)
