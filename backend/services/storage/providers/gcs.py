# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from ..config import StorageConfig
from ..models import StorageObject, StorageResult, StorageStatus
from .base import ProviderCapabilities, StorageProvider

logger = logging.getLogger("palmshed.storage.gcs")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class GCSStorageProvider(StorageProvider):
    def __init__(self, config: StorageConfig) -> None:
        self._bucket_name = config.bucket or "alma"
        self._client: Optional["gcs.Client"] = None
        self._init_error: Optional[str] = None
        self._capabilities = ProviderCapabilities(
            public_urls=True,
            signed_urls=True,
            multipart_upload=False,
            versioning=False,
            metadata=True,
            streaming=False,
        )
        try:
            from google.cloud import storage as gcs
            from google.oauth2.service_account import Credentials

            creds_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
            if creds_json:
                info = json.loads(creds_json)
                credentials = Credentials.from_service_account_info(info)
                self._client = gcs.Client(
                    credentials=credentials, project=info.get("project_id")
                )
            else:
                self._client = gcs.Client()
        except Exception as exc:
            self._init_error = str(exc)
            logger.warning("GCS init deferred — credentials not available yet: %s", exc)

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def _unavailable(self) -> StorageResult:
        msg = self._init_error or "GCS client not initialized"
        return StorageResult(
            status=StorageStatus.FAILED,
            error=f"GCS unavailable: {msg}",
            provider="gcs",
        )

    def _blob(self, name: str):
        return self._client.bucket(self._bucket_name).blob(name)

    def _make_obj(self, name: str, blob) -> StorageObject:
        return StorageObject(
            id=blob.id or str(uuid.uuid4()),
            name=name,
            size=blob.size or 0,
            content_type=blob.content_type or "application/octet-stream",
            etag=blob.etag or hashlib.md5(b"").hexdigest(),
            metadata=dict(blob.metadata or {}),
            created_at=(
                blob.time_created.replace(tzinfo=timezone.utc)
                if blob.time_created
                else _utcnow()
            ),
            modified_at=(
                blob.updated.replace(tzinfo=timezone.utc) if blob.updated else _utcnow()
            ),
            public_url=blob.public_url if hasattr(blob, "public_url") else None,
        )

    def _err(self, name: str, exc: Exception) -> StorageResult:
        logger.error("GCS error for %s: %s", name, exc)
        return StorageResult(
            status=StorageStatus.FAILED,
            error=str(exc),
            provider="gcs",
        )

    def upload(
        self,
        name: str,
        data: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> StorageResult:
        if not self._client:
            return self._unavailable()
        try:
            blob = self._blob(name)
            blob.content_type = content_type or "application/octet-stream"
            if metadata:
                blob.metadata = metadata
            blob.upload(data, content_type=blob.content_type)
            blob.reload()
            logger.info("GCS upload: name=%s size=%d", name, len(data))
            return StorageResult(
                status=StorageStatus.UPLOADED,
                object=self._make_obj(name, blob),
                provider="gcs",
            )
        except Exception as exc:
            return self._err(name, exc)

    def download(self, name: str) -> StorageResult:
        if not self._client:
            return self._unavailable()
        try:
            blob = self._blob(name)
            data = blob.download()
            blob.reload()
            logger.info("GCS download: name=%s", name)
            return StorageResult(
                status=StorageStatus.DOWNLOADED,
                object=self._make_obj(name, blob),
                data=data,
                provider="gcs",
            )
        except Exception as exc:
            if hasattr(exc, "code") and exc.code == 404:
                return StorageResult(
                    status=StorageStatus.NOT_FOUND,
                    error=f"Object not found: {name}",
                    provider="gcs",
                )
            return self._err(name, exc)

    def delete(self, name: str) -> StorageResult:
        if not self._client:
            return self._unavailable()
        try:
            blob = self._blob(name)
            blob.reload()
            obj = self._make_obj(name, blob)
            blob.delete()
            logger.info("GCS delete: name=%s", name)
            return StorageResult(
                status=StorageStatus.DELETED,
                object=obj,
                provider="gcs",
            )
        except Exception as exc:
            if hasattr(exc, "code") and exc.code == 404:
                return StorageResult(
                    status=StorageStatus.NOT_FOUND,
                    error=f"Object not found: {name}",
                    provider="gcs",
                )
            return self._err(name, exc)

    def exists(self, name: str) -> StorageResult:
        if not self._client:
            return self._unavailable()
        try:
            blob = self._blob(name)
            exists = blob.exists()
            if exists:
                blob.reload()
                return StorageResult(
                    status=StorageStatus.EXISTS,
                    object=self._make_obj(name, blob),
                    provider="gcs",
                )
            return StorageResult(
                status=StorageStatus.NOT_FOUND,
                provider="gcs",
            )
        except Exception as exc:
            return self._err(name, exc)

    def metadata(self, name: str) -> StorageResult:
        if not self._client:
            return self._unavailable()
        try:
            blob = self._blob(name)
            blob.reload()
            return StorageResult(
                status=StorageStatus.EXISTS,
                object=self._make_obj(name, blob),
                provider="gcs",
            )
        except Exception as exc:
            if hasattr(exc, "code") and exc.code == 404:
                return StorageResult(
                    status=StorageStatus.NOT_FOUND,
                    error=f"Object not found: {name}",
                    provider="gcs",
                )
            return self._err(name, exc)

    def list(self, prefix: str = "") -> StorageResult:
        if not self._client:
            return self._unavailable()
        try:
            blobs = list(self._client.list_blobs(self._bucket_name, prefix=prefix))
            names = [b.name for b in blobs]
            logger.info("GCS list: prefix=%s count=%d", prefix, len(names))
            return StorageResult(
                status=StorageStatus.EXISTS,
                data=json.dumps(names).encode("utf-8"),
                provider="gcs",
            )
        except Exception as exc:
            return self._err(prefix, exc)

    def signed_url(self, name: str, expires_in_seconds: int = 3600) -> StorageResult:
        if not self._client:
            return self._unavailable()
        try:
            blob = self._blob(name)
            url = blob.generate_signed_url(
                expiration=_utcnow().timestamp() + expires_in_seconds,
                method="GET",
            )
            obj = self._make_obj(name, blob)
            obj.public_url = url
            return StorageResult(
                status=StorageStatus.EXISTS,
                object=obj,
                provider="gcs",
            )
        except Exception as exc:
            if hasattr(exc, "code") and exc.code == 404:
                return StorageResult(
                    status=StorageStatus.NOT_FOUND,
                    error=f"Object not found: {name}",
                    provider="gcs",
                )
            return self._err(name, exc)
