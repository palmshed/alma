# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
from typing import Optional

from ..config import StorageConfig
from .base import ProviderCapabilities, StorageProvider
from .cloud import CloudStorageProvider
from .gcs import GCSStorageProvider
from .local import LocalStorageProvider
from .mock import MockStorageProvider
from .registry import ProviderRegistry
from .vercel_blob import VercelBlobStorageProvider

ProviderRegistry.register("mock", MockStorageProvider)
ProviderRegistry.register("local", LocalStorageProvider)
ProviderRegistry.register("cloud", CloudStorageProvider)
ProviderRegistry.register("gcs", GCSStorageProvider)
ProviderRegistry.register("vercel_blob", VercelBlobStorageProvider)


def get_provider(config: Optional[StorageConfig] = None) -> StorageProvider:
    if config is None:
        config = StorageConfig.from_env()
    return ProviderRegistry.create(config.provider, config)


__all__ = [
    "StorageProvider",
    "MockStorageProvider",
    "LocalStorageProvider",
    "CloudStorageProvider",
    "GCSStorageProvider",
    "VercelBlobStorageProvider",
    "ProviderRegistry",
    "ProviderCapabilities",
    "get_provider",
]
