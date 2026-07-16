# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional
from urllib import request as urlreq
from urllib.error import HTTPError

from ..config import StorageConfig
from ..models import StorageObject, StorageResult, StorageStatus
from .base import ProviderCapabilities, StorageProvider

logger = logging.getLogger("palmshed.storage.vercel_blob")

_API_BASE = "https://vercel.com/api/blob"
_API_VERSION = "12"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_store_id(token: str) -> str:
    parts = token.split("_")
    if len(parts) >= 4:
        raw = parts[3]
        return raw.removeprefix("store_")
    return ""


class VercelBlobStorageProvider(StorageProvider):
    def __init__(self, config: StorageConfig) -> None:
        self._bucket_name = config.bucket or "alma"
        self._url_cache: dict[str, str] = {}
        self._init_error: Optional[str] = None
        self._capabilities = ProviderCapabilities(
            public_urls=True,
            signed_urls=False,
            multipart_upload=False,
            versioning=False,
            metadata=True,
            streaming=False,
        )
        token = os.environ.get("BLOB_READ_WRITE_TOKEN", "")
        if not token:
            self._init_error = "BLOB_READ_WRITE_TOKEN not set"
            logger.warning("Vercel Blob init deferred: %s", self._init_error)
        self._token = token
        self._store_id = _parse_store_id(token) if token else ""

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def _unavailable(self) -> StorageResult:
        msg = self._init_error or "Vercel Blob not initialized"
        return StorageResult(
            status=StorageStatus.FAILED,
            error=f"Vercel Blob unavailable: {msg}",
            provider="vercel_blob",
        )

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "x-vercel-blob-store-id": self._store_id,
            "x-api-version": _API_VERSION,
        }

    def _req(
        self,
        method: str,
        pathname: str,
        data: Optional[bytes] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> tuple[int, bytes, dict[str, str]]:
        if method == "POST" and pathname == "/delete":
            url = f"{_API_BASE}/delete"
        elif method == "POST" and pathname == "/":
            url = f"{_API_BASE}/"
        elif pathname:
            url = f"{_API_BASE}/?pathname={pathname}"
        else:
            url = f"{_API_BASE}/"
        req_headers = self._auth_headers()
        if headers:
            req_headers.update(headers)
        req = urlreq.Request(url, data=data, headers=req_headers, method=method)
        try:
            resp = urlreq.urlopen(req, timeout=30)
            return resp.status, resp.read(), dict(resp.headers)
        except HTTPError as exc:
            body = exc.read()
            return exc.code, body, dict(exc.headers)

    def _make_obj(
        self,
        name: str,
        url: str = "",
        size: int = 0,
        content_type: str = "application/octet-stream",
        etag: Optional[str] = None,
    ) -> StorageObject:
        return StorageObject(
            id=str(uuid.uuid4()),
            name=name,
            size=size,
            content_type=content_type or "application/octet-stream",
            etag=etag or "",
            public_url=url,
            created_at=_utcnow(),
            modified_at=_utcnow(),
        )

    def _err(self, name: str, exc: Exception) -> StorageResult:
        logger.error("Vercel Blob error for %s: %s", name, exc)
        return StorageResult(
            status=StorageStatus.FAILED,
            error=str(exc),
            provider="vercel_blob",
        )

    def upload(
        self,
        name: str,
        data: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> StorageResult:
        if not self._token:
            return self._unavailable()
        try:
            headers = {
                "Content-Type": content_type or "application/octet-stream",
                "x-vercel-blob-access": "private",
                "x-allow-overwrite": "1",
                "x-add-random-suffix": "0",
                "x-cache-control-max-age": "0",
            }
            status, body, resp_headers = self._req("PUT", name, data, headers)
            if status not in (200, 201):
                err = body.decode("utf-8", errors="replace")[:200]
                return StorageResult(
                    status=StorageStatus.FAILED,
                    error=f"Upload failed ({status}): {err}",
                    provider="vercel_blob",
                )
            info = json.loads(body.decode("utf-8"))
            blob_url = info.get("url", "")
            self._url_cache[name] = blob_url
            logger.info("Vercel Blob upload: name=%s size=%d", name, len(data))
            return StorageResult(
                status=StorageStatus.UPLOADED,
                object=self._make_obj(
                    name=name,
                    url=blob_url,
                    size=len(data),
                    content_type=content_type,
                    etag=resp_headers.get("etag", ""),
                ),
                provider="vercel_blob",
            )
        except Exception as exc:
            return self._err(name, exc)

    def _cdn_url(self, name: str) -> str:
        access = "private"
        return f"https://{self._store_id}.{access}.blob.vercel-storage.com/{name}"

    def _cdn_req(self, name: str) -> tuple[int, bytes, dict[str, str]]:
        url = self._cdn_url(name)
        headers = {
            "Authorization": f"Bearer {self._token}",
        }
        req = urlreq.Request(url, headers=headers, method="GET")
        try:
            resp = urlreq.urlopen(req, timeout=30)
            return resp.status, resp.read(), dict(resp.headers)
        except HTTPError as exc:
            body = exc.read()
            return exc.code, body, dict(exc.headers)

    def download(self, name: str) -> StorageResult:
        if not self._token:
            return self._unavailable()
        try:
            status, body, resp_headers = self._cdn_req(name)
            if status == 404:
                return StorageResult(
                    status=StorageStatus.NOT_FOUND,
                    error=f"Object not found: {name}",
                    provider="vercel_blob",
                )
            if status != 200:
                err = body.decode("utf-8", errors="replace")[:200]
                return StorageResult(
                    status=StorageStatus.FAILED,
                    error=f"Download failed ({status}): {err}",
                    provider="vercel_blob",
                )
            logger.info("Vercel Blob download: name=%s size=%d", name, len(body))
            return StorageResult(
                status=StorageStatus.DOWNLOADED,
                object=self._make_obj(
                    name=name,
                    size=len(body),
                    content_type=resp_headers.get("content-type", ""),
                    etag=resp_headers.get("etag", ""),
                ),
                data=body,
                provider="vercel_blob",
            )
        except Exception as exc:
            return self._err(name, exc)

    def delete(self, name: str) -> StorageResult:
        if not self._token:
            return self._unavailable()
        try:
            payload = json.dumps({"urls": [name]}).encode("utf-8")
            status, body, _resp_headers = self._req(
                "POST", "/delete", payload, {"Content-Type": "application/json"}
            )
            if status not in (200, 204):
                err = body.decode("utf-8", errors="replace")[:200]
                if status == 404:
                    return StorageResult(
                        status=StorageStatus.NOT_FOUND,
                        error=f"Object not found: {name}",
                        provider="vercel_blob",
                    )
                return StorageResult(
                    status=StorageStatus.FAILED,
                    error=f"Delete failed ({status}): {err}",
                    provider="vercel_blob",
                )
            self._url_cache.pop(name, None)
            logger.info("Vercel Blob delete: name=%s", name)
            return StorageResult(
                status=StorageStatus.DELETED,
                object=self._make_obj(name=name),
                provider="vercel_blob",
            )
        except Exception as exc:
            return self._err(name, exc)

    def _head(self, name: str) -> Optional[tuple[str, int, str, str]]:
        try:
            url = self._cdn_url(name)
            headers = {"Authorization": f"Bearer {self._token}"}
            req = urlreq.Request(url, headers=headers, method="HEAD")
            resp = urlreq.urlopen(req, timeout=30)
            blob_url = url
            size = int(resp.headers.get("content-length", "0"))
            ct = resp.headers.get("content-type", "application/octet-stream")
            etag = resp.headers.get("etag", "")
            self._url_cache[name] = blob_url
            return blob_url, size, ct, etag
        except HTTPError as exc:
            if exc.code == 404:
                return None
            return None
        except Exception:
            return None

    def exists(self, name: str) -> StorageResult:
        if not self._token:
            return self._unavailable()
        try:
            info = self._head(name)
            if info is None:
                return StorageResult(
                    status=StorageStatus.NOT_FOUND,
                    provider="vercel_blob",
                )
            blob_url, size, ct, etag = info
            return StorageResult(
                status=StorageStatus.EXISTS,
                object=self._make_obj(
                    name=name,
                    url=blob_url,
                    size=size,
                    content_type=ct,
                    etag=etag,
                ),
                provider="vercel_blob",
            )
        except Exception as exc:
            return self._err(name, exc)

    def metadata(self, name: str) -> StorageResult:
        if not self._token:
            return self._unavailable()
        try:
            info = self._head(name)
            if info is None:
                return StorageResult(
                    status=StorageStatus.NOT_FOUND,
                    error=f"Object not found: {name}",
                    provider="vercel_blob",
                )
            blob_url, size, ct, etag = info
            return StorageResult(
                status=StorageStatus.EXISTS,
                object=self._make_obj(
                    name=name,
                    url=blob_url,
                    size=size,
                    content_type=ct,
                    etag=etag,
                ),
                provider="vercel_blob",
            )
        except Exception as exc:
            return self._err(name, exc)

    def list(self, prefix: str = "") -> StorageResult:
        if not self._token:
            return self._unavailable()
        try:
            qs = f"?prefix={prefix}" if prefix else ""
            url = f"{_API_BASE}/{qs}"
            req_headers = self._auth_headers()
            req = urlreq.Request(url, headers=req_headers, method="GET")
            resp = urlreq.urlopen(req, timeout=30)
            body = resp.read()
            data = json.loads(body.decode("utf-8"))
            blobs = data.get("blobs", [])
            names = []
            for b in blobs:
                pathname = b.get("pathname", "")
                blob_url = b.get("url", "")
                if pathname:
                    self._url_cache[pathname] = blob_url
                    names.append(pathname)
            logger.info("Vercel Blob list: prefix=%s count=%d", prefix, len(names))
            return StorageResult(
                status=StorageStatus.EXISTS,
                data=json.dumps(names).encode("utf-8"),
                provider="vercel_blob",
            )
        except HTTPError as exc:
            body = exc.read()
            err = body.decode("utf-8", errors="replace")[:200]
            return StorageResult(
                status=StorageStatus.FAILED,
                error=f"List failed ({exc.code}): {err}",
                provider="vercel_blob",
            )
        except Exception as exc:
            return self._err(prefix, exc)

    def signed_url(self, name: str, expires_in_seconds: int = 3600) -> StorageResult:
        return StorageResult(
            status=StorageStatus.FAILED,
            error="Vercel Blob does not support signed URLs",
            provider="vercel_blob",
        )
