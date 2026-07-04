# ADR 0003: Storage Service

## Status

Accepted

## Context

Storage is a cross-product capability required by every application built
by Palmshed. Products need to upload, download, and manage files without
being coupled to a specific storage backend.

Key requirements:

- Provider-agnostic: support multiple storage backends (local, GCS, S3, R2, Azure)
- Product-agnostic: zero coupling to any specific application
- Minimal dependencies: mock and local providers work with stdlib only
- Testable: mock provider for development and automated tests

## Decision

Introduce `services.storage` as a new Platform Service following the same
architecture as `services.mail` and `services.auth`.

### Architecture

```text
services/storage/
├── __init__.py          # Public API re-exports
├── config.py            # StorageConfig from env (single source of truth)
├── models.py            # StorageObject, StorageResult, StorageStatus
├── metrics.py           # StorageMetrics (upload/download/delete counts)
├── logging.py           # Structured audit logging
├── service.py           # StorageService (single public API)
├── verify.py            # CLI for end-to-end verification
├── README.md            # Versioning policy and usage guide
└── providers/
    ├── __init__.py       # Auto-registration + factory
    ├── base.py           # StorageProvider ABC + ProviderCapabilities
    ├── registry.py       # ProviderRegistry (register/create/available)
    ├── mock.py           # MockStorageProvider (in-memory)
    ├── local.py          # LocalStorageProvider (filesystem)
    └── cloud.py          # CloudStorageProvider (interface stub)
```

### Provider interface

```python
class StorageProvider(ABC):
    def upload(self, name, data, content_type=None, metadata=None) -> StorageResult
    def download(self, name) -> StorageResult
    def delete(self, name) -> StorageResult
    def exists(self, name) -> StorageResult
    def metadata(self, name) -> StorageResult
    def list(self, prefix="") -> StorageResult
    def signed_url(self, name, expires_in_seconds=3600) -> StorageResult
```

### ProviderCapabilities

```python
@dataclass
class ProviderCapabilities:
    public_urls: bool = True
    signed_urls: bool = True
    multipart_upload: bool = True
    versioning: bool = True
    metadata: bool = True
    streaming: bool = True
```

### StorageService public API

```python
class StorageService:
    def upload(self, name, data, content_type=None, metadata=None) -> StorageObject
    def download(self, name) -> tuple[StorageObject, bytes]
    def delete(self, name) -> StorageObject
    def exists(self, name) -> bool
    def metadata(self, name) -> StorageObject
    def list(self, prefix="") -> list[str]
    def signed_url(self, name, expires_in_seconds=3600) -> str
    def health(self) -> StorageHealth
```

### Configuration

All environment variables are read exclusively in `StorageConfig.from_env()`:

- `STORAGE_PROVIDER` — provider name (default: `mock`)
- `STORAGE_BUCKET` — logical bucket/container name (default: `alma`)
- `STORAGE_BASE_PATH` — filesystem path for local provider
- `STORAGE_PUBLIC_URL` — public base URL for serving objects
- `MAX_UPLOAD_SIZE_MB` — maximum upload size in MB (default: `50`)

### Providers

**MockStorageProvider** — in-memory store. All capabilities enabled. No
credentials or persistence required. Default for development and tests.

**LocalStorageProvider** — filesystem-backed storage. Supports nested paths,
metadata, and listing. Does not support public URLs or signed URLs.

**CloudStorageProvider** — interface stub. All methods return FAILED with a
message directing implementors to replace with GCS, S3, R2, or Azure.

### Health integration

The health endpoint instantiates `StorageService` lazily and includes the
provider name, bucket, config validity, and liveness check in the response.

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

### Verification CLI

```bash
python -m services.storage.verify
```

Performs: upload, exists check, download + checksum comparison, metadata
fetch, delete, verify deletion, health check. Reports latency per step.

## Consequences

Positive:

- Products can store files without choosing a backend
- Mock provider enables isolated testing
- Cloud provider stub documents the integration contract
- Architecture boundary tests enforce product-agnostic constraints
- Consistent architecture across mail, auth, and storage services

Negative:

- Local provider does not support signed URLs or public serving
- Cloud storage requires a concrete implementation for production use
- No streaming support in initial mock or local providers

## References

- ADR 0001: Platform Services
- ADR 0002: Mail Service
- `services/mail/` — reference implementation
- `services/auth/` — reference implementation
