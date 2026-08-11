# SPDX-FileCopyrightText: Copyright (c) 2026 Palmshed
# SPDX-License-Identifier: MIT

"""AI provider registry: mirrors the ImageProviderRegistry pattern."""

from typing import Optional, Type

from .base import AIProvider
from .gemini import GeminiAI
from .openrouter import OpenRouterProvider
from .synthetic import SyntheticProvider

__all__ = [
    "AIProviderRegistry",
    "GeminiAI",
    "OpenRouterProvider",
    "SyntheticProvider",
]


class AIProviderRegistry:
    _providers: dict[str, Type[AIProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_cls: Type[AIProvider]) -> None:
        cls._providers[name] = provider_cls

    @classmethod
    def create(cls, name: str) -> AIProvider:
        provider_cls = cls._providers.get(name)
        if not provider_cls:
            registered = ", ".join(cls.available())
            raise ValueError(f"Unknown AI provider '{name}'. Registered: {registered}")
        return provider_cls()

    @classmethod
    def available(cls) -> list[str]:
        return list(cls._providers.keys())

    @classmethod
    def get(cls, name: str) -> Optional[Type[AIProvider]]:
        return cls._providers.get(name)


AIProviderRegistry.register("gemini", GeminiAI)
AIProviderRegistry.register("openrouter", OpenRouterProvider)
AIProviderRegistry.register("synthetic", SyntheticProvider)
