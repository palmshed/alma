from typing import Optional

from ..config import StorageConfig
from .base import ProviderCapabilities, StorageProvider
from .cloud import CloudStorageProvider
from .local import LocalStorageProvider
from .mock import MockStorageProvider
from .registry import ProviderRegistry

ProviderRegistry.register("mock", MockStorageProvider)
ProviderRegistry.register("local", LocalStorageProvider)
ProviderRegistry.register("cloud", CloudStorageProvider)


def get_provider(config: Optional[StorageConfig] = None) -> StorageProvider:
    if config is None:
        config = StorageConfig.from_env()
    return ProviderRegistry.create(config.provider, config)


__all__ = [
    "StorageProvider",
    "MockStorageProvider",
    "LocalStorageProvider",
    "CloudStorageProvider",
    "ProviderRegistry",
    "ProviderCapabilities",
    "get_provider",
]
