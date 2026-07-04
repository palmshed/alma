# Storage System

A shared storage capability for Palmshed products. Provider-agnostic
and designed for future extraction into a standalone service.

---

## Architecture

```
Application (Alma, Via, Nuntius, ...)
    ↓
StorageService.upload/download/delete/exists/metadata/list/signed_url
    ↓
StorageProvider (Mock / Local / Cloud / GCS / S3 / R2 / Azure)
    ↓
Storage backend
```

Applications never talk directly to a storage backend.

---

## Public API

```python
from services.storage import StorageService, StorageConfig

config = StorageConfig.from_env()
svc = StorageService(config=config)

# Upload
obj = svc.upload("path/to/file.txt", data, content_type="text/plain")

# Download
obj, data = svc.download("path/to/file.txt")

# Delete
obj = svc.delete("path/to/file.txt")

# Check existence
exists = svc.exists("path/to/file.txt")

# Metadata
meta = svc.metadata("path/to/file.txt")

# List
objects = svc.list(prefix="path/to/")

# Signed URL (if supported)
url = svc.signed_url("path/to/file.txt", expires_in_seconds=3600)

# Health
health = svc.health()
```

---

## Providers

### Comparison

| Feature           | Mock | Local | Cloud | GCS | S3 | R2 | Azure |
|-------------------|------|-------|-------|-----|-----|-----|-------|
| Status            | ✓    | ✓     | stub  | —    | —    | —    | —     |
| Public URLs       | ✓    | ✗     | ✓     | —    | —    | —    | —     |
| Signed URLs       | ✓    | ✗     | ✓     | —    | —    | —    | —     |
| Metadata          | ✓    | ✓     | ✓     | —    | —    | —    | —     |
| Multipart upload  | ✓    | ✗     | ✓     | —    | —    | —    | —     |
| Versioning        | ✓    | ✗     | ✓     | —    | —    | —    | —     |
| Streaming         | ✓    | ✗     | ✓     | —    | —    | —    | —     |

### Mock

Default provider. Stores objects in memory. No persistence across restarts.

```
STORAGE_PROVIDER=mock
```

### Local

Stores objects on the local filesystem.

```
STORAGE_PROVIDER=local
STORAGE_BASE_PATH=/var/data/palmshed/storage
```

### Cloud Interface Stub

Placeholder for cloud providers. All operations return `FAILED` until
replaced with a concrete implementation.

```
STORAGE_PROVIDER=cloud
```

### Adding a Provider

1. Create `backend/services/storage/providers/gcs.py`
2. Implement `StorageProvider` ABC
3. Register in `providers/__init__.py`:
   ```python
   ProviderRegistry.register("gcs", GCSStorageProvider)
   ```
4. Set `STORAGE_PROVIDER=gcs`

No application code changes needed.

---

## Configuration

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `STORAGE_PROVIDER` | `mock` | no | Provider name |
| `STORAGE_BUCKET` | `alma` | no | Logical bucket/container name |
| `STORAGE_BASE_PATH` | — | for local | Filesystem path for local provider |
| `STORAGE_PUBLIC_URL` | — | no | Public base URL for serving objects |
| `MAX_UPLOAD_SIZE_MB` | `50` | no | Maximum upload size in MB |

---

## Provider Capabilities

Providers declare their capabilities at startup:

```python
@dataclass
class ProviderCapabilities:
    public_urls: bool     # Objects accessible at public URLs
    signed_urls: bool     # Supports time-limited signed URLs
    multipart_upload: bool  # Supports large file chunked uploads
    versioning: bool      # Supports object versioning
    metadata: bool        # Supports custom object metadata
    streaming: bool       # Supports streaming upload/download
```

Applications can inspect capabilities before calling provider-specific
features.

---

## Health

`GET /api/health` includes storage status:

```json
{
  "storage": {
    "provider": "mock",
    "config_valid": true,
    "bucket": "alma",
    "healthy": true
  }
}
```

Health check performs a write-read-delete cycle to verify the provider
is operational.

---

## Verification CLI

```bash
python -m services.storage.verify
```

Tests all operations end-to-end:

1. Upload a temporary object
2. Verify it exists
3. Download it and compare checksum
4. Fetch metadata
5. Delete it
6. Verify deletion
7. Check health

Reports latency for each step.

---

## Development

```bash
# Default (mock provider, no setup needed)
python -m services.storage.verify

# Local filesystem
STORAGE_PROVIDER=local STORAGE_BASE_PATH=/tmp/palmshed-test \
  python -m services.storage.verify
```

---

## Architecture

See `docs/architecture/0003-storage-service.md` for the Architecture Decision
Record.
