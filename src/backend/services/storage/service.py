# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
import time
import uuid
from typing import Optional

from .config import StorageConfig
from .logging import StorageLogger
from .metrics import StorageMetrics
from .models import StorageHealth, StorageObject, StorageStatus
from .providers import StorageProvider, get_provider


class StorageError(Exception):
    pass


class StorageValidationError(StorageError):
    pass


class StorageService:
    def __init__(
        self,
        config: Optional[StorageConfig] = None,
        provider: Optional[StorageProvider] = None,
        logger: Optional[StorageLogger] = None,
        metrics: Optional[StorageMetrics] = None,
    ) -> None:
        self.config = config or StorageConfig.from_env()
        self.provider = provider or get_provider(self.config)
        self.logger = logger or StorageLogger()
        self.metrics = metrics or StorageMetrics()

    def upload(
        self,
        name: str,
        data: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> StorageObject:
        self._validate_upload(name, data)

        t0 = time.monotonic()
        result = self.provider.upload(
            name=name,
            data=data,
            content_type=content_type,
            metadata=metadata,
        )
        elapsed = time.monotonic() - t0
        result.duration_ms = elapsed * 1000
        self.metrics.record_duration(elapsed)

        if result.status == StorageStatus.FAILED:
            self.metrics.record_failure()
            self.logger.log_result(result)
            raise StorageError(result.error or "upload failed")

        self.metrics.record_upload()
        self.logger.log_result(result)
        return result.object

    def download(self, name: str) -> tuple[StorageObject, bytes]:
        t0 = time.monotonic()
        result = self.provider.download(name)
        elapsed = time.monotonic() - t0
        result.duration_ms = elapsed * 1000
        self.metrics.record_duration(elapsed)

        if result.status == StorageStatus.NOT_FOUND:
            self.metrics.record_failure()
            raise StorageError(f"Object not found: {name}")

        if result.status == StorageStatus.FAILED:
            self.metrics.record_failure()
            self.logger.log_result(result)
            raise StorageError(result.error or "download failed")

        self.metrics.record_download()
        self.logger.log_result(result)
        return result.object, result.data

    def delete(self, name: str) -> StorageObject:
        t0 = time.monotonic()
        result = self.provider.delete(name)
        elapsed = time.monotonic() - t0
        result.duration_ms = elapsed * 1000
        self.metrics.record_duration(elapsed)

        if result.status == StorageStatus.NOT_FOUND:
            raise StorageError(f"Object not found: {name}")

        if result.status == StorageStatus.FAILED:
            self.metrics.record_failure()
            self.logger.log_result(result)
            raise StorageError(result.error or "delete failed")

        self.metrics.record_delete()
        self.logger.log_result(result)
        return result.object

    def exists(self, name: str) -> bool:
        t0 = time.monotonic()
        result = self.provider.exists(name)
        elapsed = time.monotonic() - t0
        self.metrics.record_duration(elapsed)
        return result.status == StorageStatus.EXISTS

    def metadata(self, name: str) -> StorageObject:
        t0 = time.monotonic()
        result = self.provider.metadata(name)
        elapsed = time.monotonic() - t0
        result.duration_ms = elapsed * 1000
        self.metrics.record_duration(elapsed)

        if result.status == StorageStatus.NOT_FOUND:
            raise StorageError(f"Object not found: {name}")

        if result.status == StorageStatus.FAILED:
            self.metrics.record_failure()
            raise StorageError(result.error or "metadata fetch failed")

        return result.object

    def list(self, prefix: str = "") -> list[str]:
        t0 = time.monotonic()
        result = self.provider.list(prefix)
        elapsed = time.monotonic() - t0
        self.metrics.record_duration(elapsed)

        if result.status == StorageStatus.FAILED:
            self.metrics.record_failure()
            raise StorageError(result.error or "list failed")

        self.metrics.record_list()
        if result.data:
            import json

            return json.loads(result.data.decode("utf-8"))
        return []

    def signed_url(self, name: str, expires_in_seconds: int = 3600) -> str:
        t0 = time.monotonic()
        result = self.provider.signed_url(name, expires_in_seconds)
        elapsed = time.monotonic() - t0
        self.metrics.record_duration(elapsed)

        if result.status == StorageStatus.NOT_FOUND:
            raise StorageError(f"Object not found: {name}")

        if result.status == StorageStatus.FAILED:
            raise StorageError(result.error or "signed URL not available")

        return result.object.public_url or ""

    def health(self) -> StorageHealth:
        valid, errors = self.config.is_valid()
        try:
            test_name = f"__health_check_{uuid.uuid4().hex[:8]}"
            upload_result = self.provider.upload(test_name, b"health")
            if upload_result.status != StorageStatus.UPLOADED:
                raise RuntimeError(upload_result.error or "upload failed")
            delete_result = self.provider.delete(test_name)
            if delete_result.status not in (
                StorageStatus.DELETED,
                StorageStatus.NOT_FOUND,
            ):
                raise RuntimeError(delete_result.error or "delete failed")
            healthy = True
        except Exception:
            healthy = False

        return StorageHealth(
            provider=self.config.provider,
            config_valid=valid,
            config_errors=errors,
            bucket=self.config.bucket,
            healthy=healthy,
        )

    def _validate_upload(self, name: str, data: bytes) -> None:
        if not name:
            raise StorageValidationError("Object name is required")
        if len(data) == 0:
            raise StorageValidationError("Cannot upload empty data")
        if len(data) > self.config.max_upload_size_bytes:
            raise StorageValidationError(
                f"Data too large ({len(data)} bytes); "
                f"max is {self.config.max_upload_size_bytes}"
            )
