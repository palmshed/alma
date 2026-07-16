# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
from typing import Optional

from ..config import StorageConfig
from .base import StorageProvider


class ProviderRegistry:
    _providers: dict[str, type[StorageProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_cls: type[StorageProvider]) -> None:
        cls._providers[name] = provider_cls

    @classmethod
    def create(cls, name: str, config: StorageConfig) -> StorageProvider:
        provider_cls = cls._providers.get(name)
        if not provider_cls:
            registered = ", ".join(cls.available())
            raise ValueError(
                f"Unknown storage provider '{name}'. Registered: {registered}"
            )
        return provider_cls(config)

    @classmethod
    def available(cls) -> list[str]:
        return list(cls._providers.keys())

    @classmethod
    def get(cls, name: str) -> Optional[type[StorageProvider]]:
        return cls._providers.get(name)
