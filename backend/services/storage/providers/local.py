import hashlib
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from ..config import StorageConfig
from ..models import StorageObject, StorageResult, StorageStatus
from .base import ProviderCapabilities, StorageProvider

logger = logging.getLogger("palmshed.storage.local")


class LocalStorageProvider(StorageProvider):
    def __init__(self, config: StorageConfig) -> None:
        self._base_path = config.base_path or "/tmp/palmshed_storage"
        os.makedirs(self._base_path, exist_ok=True)
        self._capabilities = ProviderCapabilities(
            public_urls=False,
            signed_urls=False,
            multipart_upload=False,
            versioning=False,
            metadata=True,
            streaming=False,
        )

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def _path(self, name: str) -> str:
        safe = name.lstrip("/")
        return os.path.normpath(os.path.join(self._base_path, safe))

    def _ensure_safe(self, name: str) -> None:
        full = self._path(name)
        if not full.startswith(os.path.normpath(self._base_path)):
            raise ValueError(f"Path traversal detected: {name}")

    def upload(
        self,
        name: str,
        data: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> StorageResult:
        self._ensure_safe(name)
        path = self._path(name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        now = datetime.now(timezone.utc)
        obj = StorageObject(
            id=str(uuid.uuid4()),
            name=name,
            size=len(data),
            content_type=content_type or "application/octet-stream",
            etag=hashlib.md5(data).hexdigest(),
            metadata=metadata or {},
            created_at=now,
            modified_at=now,
        )
        logger.info("Local upload: name=%s path=%s size=%d", name, path, len(data))
        return StorageResult(
            status=StorageStatus.UPLOADED,
            object=obj,
            provider="local",
        )

    def download(self, name: str) -> StorageResult:
        self._ensure_safe(name)
        path = self._path(name)
        if not os.path.exists(path):
            return StorageResult(
                status=StorageStatus.NOT_FOUND,
                error=f"Object not found: {name}",
                provider="local",
            )
        with open(path, "rb") as f:
            data = f.read()
        stat = os.stat(path)
        obj = StorageObject(
            id=name,
            name=name,
            size=stat.st_size,
            content_type="application/octet-stream",
            etag=hashlib.md5(data).hexdigest(),
            created_at=datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc),
            modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
        )
        logger.info("Local download: name=%s", name)
        return StorageResult(
            status=StorageStatus.DOWNLOADED,
            object=obj,
            data=data,
            provider="local",
        )

    def delete(self, name: str) -> StorageResult:
        self._ensure_safe(name)
        path = self._path(name)
        if not os.path.exists(path):
            return StorageResult(
                status=StorageStatus.NOT_FOUND,
                error=f"Object not found: {name}",
                provider="local",
            )
        size = os.path.getsize(path)
        obj = StorageObject(
            id=name,
            name=name,
            size=size,
        )
        os.remove(path)
        logger.info("Local delete: name=%s", name)
        return StorageResult(
            status=StorageStatus.DELETED,
            object=obj,
            provider="local",
        )

    def exists(self, name: str) -> StorageResult:
        self._ensure_safe(name)
        path = self._path(name)
        if os.path.exists(path):
            return StorageResult(
                status=StorageStatus.EXISTS,
                provider="local",
            )
        return StorageResult(
            status=StorageStatus.NOT_FOUND,
            provider="local",
        )

    def metadata(self, name: str) -> StorageResult:
        self._ensure_safe(name)
        path = self._path(name)
        if not os.path.exists(path):
            return StorageResult(
                status=StorageStatus.NOT_FOUND,
                error=f"Object not found: {name}",
                provider="local",
            )
        data = b""
        if os.path.getsize(path) > 0:
            with open(path, "rb") as f:
                data = f.read(65536)
        stat = os.stat(path)
        obj = StorageObject(
            id=name,
            name=name,
            size=stat.st_size,
            content_type="application/octet-stream",
            etag=hashlib.md5(data).hexdigest(),
            created_at=datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc),
            modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
        )
        return StorageResult(
            status=StorageStatus.EXISTS,
            object=obj,
            provider="local",
        )

    def list(self, prefix: str = "") -> StorageResult:
        base = self._base_path
        if not os.path.exists(base):
            return StorageResult(
                status=StorageStatus.EXISTS,
                data=b"[]",
                provider="local",
            )
        names = []
        for root, _dirs, files in os.walk(base):
            for f in files:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, base)
                if rel.startswith(prefix):
                    names.append(rel)
        logger.info("Local list: prefix=%s count=%d", prefix, len(names))
        import json

        return StorageResult(
            status=StorageStatus.EXISTS,
            data=json.dumps(names).encode("utf-8"),
            provider="local",
        )

    def signed_url(self, name: str, expires_in_seconds: int = 3600) -> StorageResult:
        return StorageResult(
            status=StorageStatus.FAILED,
            error="Local provider does not support signed URLs",
            provider="local",
        )
