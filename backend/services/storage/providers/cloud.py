# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
import logging

from ..config import StorageConfig
from ..models import StorageResult, StorageStatus
from .base import ProviderCapabilities, StorageProvider

logger = logging.getLogger("palmshed.storage.cloud")


class CloudStorageProvider(StorageProvider):
    def __init__(self, config: StorageConfig) -> None:
        self._capabilities = ProviderCapabilities(
            public_urls=True,
            signed_urls=True,
            multipart_upload=True,
            versioning=True,
            metadata=True,
            streaming=True,
        )

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def upload(
        self, name: str, data: bytes, content_type=None, metadata=None
    ) -> StorageResult:
        return StorageResult(
            status=StorageStatus.FAILED,
            error="CloudStorageProvider is an interface. Use GCS, S3, R2, or Azure.",
            provider="cloud",
        )

    def download(self, name: str) -> StorageResult:
        return StorageResult(
            status=StorageStatus.FAILED,
            error="CloudStorageProvider is an interface. Use GCS, S3, R2, or Azure.",
            provider="cloud",
        )

    def delete(self, name: str) -> StorageResult:
        return StorageResult(
            status=StorageStatus.FAILED,
            error="CloudStorageProvider is an interface. Use GCS, S3, R2, or Azure.",
            provider="cloud",
        )

    def exists(self, name: str) -> StorageResult:
        return StorageResult(
            status=StorageStatus.FAILED,
            error="CloudStorageProvider is an interface. Use GCS, S3, R2, or Azure.",
            provider="cloud",
        )

    def metadata(self, name: str) -> StorageResult:
        return StorageResult(
            status=StorageStatus.FAILED,
            error="CloudStorageProvider is an interface. Use GCS, S3, R2, or Azure.",
            provider="cloud",
        )

    def list(self, prefix: str = "") -> StorageResult:
        return StorageResult(
            status=StorageStatus.FAILED,
            error="CloudStorageProvider is an interface. Use GCS, S3, R2, or Azure.",
            provider="cloud",
        )

    def signed_url(self, name: str, expires_in_seconds: int = 3600) -> StorageResult:
        return StorageResult(
            status=StorageStatus.FAILED,
            error="CloudStorageProvider is an interface. Use GCS, S3, R2, or Azure.",
            provider="cloud",
        )
