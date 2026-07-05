# Storage Platform Service

Provider-agnostic storage service for Palmshed products.

## Public API

```python
from services.storage import StorageService, StorageConfig

config = StorageConfig.from_env()
svc = StorageService(config=config)

obj = svc.upload("path/to/file.txt", data, content_type="text/plain")
data = svc.download("path/to/file.txt")
svc.delete("path/to/file.txt")
exists = svc.exists("path/to/file.txt")
meta = svc.metadata("path/to/file.txt")
objects = svc.list(prefix="path/to/")
url = svc.signed_url("path/to/file.txt", expires_in_seconds=3600)
health = svc.health()
```

## Providers

| Provider | Config | Description |
|----------|--------|-------------|
| `mock`   | (default) | In-memory store, no persistence. |
| `local`  | `STORAGE_BASE_PATH` | Local filesystem storage. |
| `cloud`  | — | Interface stub. Replace with GCS, S3, R2, or Azure. |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `STORAGE_PROVIDER` | `mock` | Provider name (`mock`, `local`, `cloud`) |
| `STORAGE_BUCKET` | `alma` | Logical bucket/container name |
| `STORAGE_BASE_PATH` | — | Filesystem path for local provider |
| `STORAGE_PUBLIC_URL` | — | Public base URL for serving objects |
| `MAX_UPLOAD_SIZE_MB` | `50` | Maximum upload size in MB |

## Health

```json
{
  "provider": "mock",
  "config_valid": true,
  "bucket": "alma",
  "healthy": true
}
```

## Verification CLI

```bash
python -m services.storage.verify
```

Uploads, downloads, checksums, deletes, and reports latency for each step.

## Adding a Provider

1. Create `backend/services/storage/providers/gcs.py`
2. Implement `StorageProvider` ABC
3. Register in `providers/__init__.py`
4. Set `STORAGE_PROVIDER=gcs`

No application code changes needed.

## Versioning

See [docs/versioning.md](../../../docs/versioning.md) for the complete
policy. Public API is defined by `__init__.py` exports.
