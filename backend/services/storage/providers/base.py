# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from ..models import StorageResult


@dataclass
class ProviderCapabilities:
    public_urls: bool = True
    signed_urls: bool = True
    multipart_upload: bool = True
    versioning: bool = True
    metadata: bool = True
    streaming: bool = True


class StorageProvider(ABC):
    @abstractmethod
    def upload(
        self,
        name: str,
        data: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> StorageResult: ...

    @abstractmethod
    def download(self, name: str) -> StorageResult: ...

    @abstractmethod
    def delete(self, name: str) -> StorageResult: ...

    @abstractmethod
    def exists(self, name: str) -> StorageResult: ...

    @abstractmethod
    def metadata(self, name: str) -> StorageResult: ...

    @abstractmethod
    def list(self, prefix: str = "") -> StorageResult: ...

    @abstractmethod
    def signed_url(
        self, name: str, expires_in_seconds: int = 3600
    ) -> StorageResult: ...

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities: ...
