import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from ..config import StorageConfig
from ..models import StorageObject, StorageResult, StorageStatus
from .base import ProviderCapabilities, StorageProvider

logger = logging.getLogger("palmshed.storage.mock")


class MockStorageProvider(StorageProvider):
    def __init__(self, config: Optional[StorageConfig] = None) -> None:
        self._store: dict[str, tuple[StorageObject, bytes]] = {}
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
        self,
        name: str,
        data: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> StorageResult:
        obj = StorageObject(
            id=str(uuid.uuid4()),
            name=name,
            size=len(data),
            content_type=content_type or "application/octet-stream",
            etag=hashlib.md5(data).hexdigest(),
            metadata=metadata or {},
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc),
            public_url=f"/mock/{name}",
        )
        self._store[name] = (obj, data)
        logger.info("Mock upload: name=%s size=%d", name, len(data))
        return StorageResult(
            status=StorageStatus.UPLOADED,
            object=obj,
            provider="mock",
        )

    def download(self, name: str) -> StorageResult:
        entry = self._store.get(name)
        if not entry:
            return StorageResult(
                status=StorageStatus.NOT_FOUND,
                error=f"Object not found: {name}",
                provider="mock",
            )
        obj, data = entry
        logger.info("Mock download: name=%s", name)
        return StorageResult(
            status=StorageStatus.DOWNLOADED,
            object=obj,
            data=data,
            provider="mock",
        )

    def delete(self, name: str) -> StorageResult:
        entry = self._store.pop(name, None)
        if not entry:
            return StorageResult(
                status=StorageStatus.NOT_FOUND,
                error=f"Object not found: {name}",
                provider="mock",
            )
        logger.info("Mock delete: name=%s", name)
        return StorageResult(
            status=StorageStatus.DELETED,
            object=entry[0],
            provider="mock",
        )

    def exists(self, name: str) -> StorageResult:
        entry = self._store.get(name)
        if not entry:
            return StorageResult(
                status=StorageStatus.NOT_FOUND,
                provider="mock",
            )
        return StorageResult(
            status=StorageStatus.EXISTS,
            object=entry[0],
            provider="mock",
        )

    def metadata(self, name: str) -> StorageResult:
        entry = self._store.get(name)
        if not entry:
            return StorageResult(
                status=StorageStatus.NOT_FOUND,
                error=f"Object not found: {name}",
                provider="mock",
            )
        return StorageResult(
            status=StorageStatus.EXISTS,
            object=entry[0],
            provider="mock",
        )

    def list(self, prefix: str = "") -> StorageResult:
        matching = [
            obj for name, (obj, _) in self._store.items() if name.startswith(prefix)
        ]
        logger.info("Mock list: prefix=%s count=%d", prefix, len(matching))
        import json

        return StorageResult(
            status=StorageStatus.EXISTS,
            data=json.dumps([o.name for o in matching]).encode("utf-8"),
            provider="mock",
        )

    def signed_url(self, name: str, expires_in_seconds: int = 3600) -> StorageResult:
        entry = self._store.get(name)
        if not entry:
            return StorageResult(
                status=StorageStatus.NOT_FOUND,
                error=f"Object not found: {name}",
                provider="mock",
            )
        return StorageResult(
            status=StorageStatus.EXISTS,
            object=entry[0],
            provider="mock",
        )

    def reset(self) -> None:
        self._store.clear()
