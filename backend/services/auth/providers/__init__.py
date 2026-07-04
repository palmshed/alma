from typing import Optional

from ..config import AuthConfig
from .base import AuthProvider
from .jwt import JWTAuth
from .mock import MockAuth
from .registry import ProviderRegistry

ProviderRegistry.register("mock", MockAuth)
ProviderRegistry.register("jwt", JWTAuth)


def get_provider(config: Optional[AuthConfig] = None) -> AuthProvider:
    if config is None:
        config = AuthConfig.from_env()
    return ProviderRegistry.create(config.provider, config)


__all__ = [
    "AuthProvider",
    "MockAuth",
    "JWTAuth",
    "ProviderRegistry",
    "get_provider",
]
