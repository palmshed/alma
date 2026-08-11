# Platform Architecture Overview

The application is supported by a platform services layer that owns
cross-product infrastructure. This document explains the architecture
at a high level and points to detailed documents for each component.

---

## Layer Model

```
            ┌──────────────────────────────────┐
            │          Application              │
            │  (Alma, Via, Nuntius, Glimpse)   │
            └────────────┬─────────────────────┘
                         │
                    ┌────▼─────┐
                    │  verify  │  ← one command: platform + application health
                    └────┬─────┘
                         │
            ┌────────────▼──────────────────────┐
            │        PlatformManager             │
            │  (services/platform.py)           │
            │  lazy init · health · shutdown    │
            └──┬────────┬────────┬────────┬─────┘
               │        │        │        │
         ┌─────▼──┐ ┌──▼───┐ ┌──▼────┐ ┌─▼──────────┐
         │  Mail  │ │ Auth │ │Storage│ │Notifications│
         │ Service│ │Service│ │Service│ │  Service    │
         └───┬────┘ └──┬───┘ └──┬────┘ └──────┬──────┘
             │          │        │              │
         Provider   Provider  Provider       Channel
           ABC        ABC       ABC            ABC
       ┌───┼───┐  ┌───┼───┐ ┌──┼───┐    ┌────┼────┐
       │   │   │  │   │   │ │  │   │    │    │    │
     Mock SMTP   Mock JWT  Mock Local  Mock Email Webhook
          Resend                Cloud
             │          │        │              │
             └──────────┴────────┴──────────────┘
                         │
              ┌──────────▼──────────┐
              │    Infrastructure    │
              │  (SMTP, Resend API, │
              │   GCS/S3, HTTP)     │
              └─────────────────────┘
```

---

## How It Works

### PlatformManager

`src/backend/services/platform.py`: the single entry point for all platform
services. Application code never constructs `MailService`, `AuthService`,
etc. directly.

```python
from services import platform

platform.mail.send(template, recipient, context)
platform.auth.login(email, password)
platform.storage.upload(path, data)
platform.notifications.send(recipient, subject, body)

health = platform.health()        # all services in one call
platform.shutdown()               # graceful teardown
```

Services are lazily initialized from environment variables on first
access. `platform.health()` returns status for every service, making
it trivial to expose a single `/api/health` endpoint.

### Platform Services

Each service follows an identical architecture:

- **Config**: `from_env()` reads all settings from environment variables
- **Provider/Channel ABC**: abstract base class for pluggable backends
- **Registry**: provider registration and lookup by name
- **Service**: public API (send, register, upload, health, shutdown)
- **Metrics**: counters, histograms, snapshots
- **Logging**: structured audit trail
- **Verify**: standalone CLI for diagnostics

Provider selection is always configuration-only:
`MAIL_PROVIDER`, `AUTH_PROVIDER`, `STORAGE_PROVIDER`,
`NOTIFICATIONS_DEFAULT_CHANNEL`. No code changes required.

### alma verify

`src/backend/verify.py`: consolidated operational CLI that checks both
platform services (local) and application endpoints (API).

```bash
python -m backend.verify                    # all checks
python -m backend.verify --platform         # platform only
python -m backend.verify --application      # API only
python -m backend.verify --json             # machine-readable
python -m backend.verify --json --output report.json  # write to file
python -m backend.verify mail auth          # specific services
```

The exit code is 0 only when all infrastructure checks pass (quota
issues like image generation rate limits are reported separately and
do not cause a failure). This makes it suitable for CI gating.

---

## Service Reference

| Service | Path | Public API | Providers |
|---------|------|------------|-----------|
| Mail | `src/backend/services/mail/` | `MailService.send()` | Mock, SMTP, Resend |
| Auth | `src/backend/services/auth/` | `register`, `login`, `verify`, `refresh`, `logout` | Mock, JWT |
| Storage | `src/backend/services/storage/` | `upload`, `download`, `delete`, `exists`, `metadata`, `list`, `signed_url` | Mock, Local, Cloud |
| Notifications | `src/backend/services/notifications/` | `NotificationService.send()` | Mock, Email, Webhook |

---

## Decision Records

| Document | Topic |
|----------|-------|
| `docs/architecture/0001-platform-services.md` | Why the platform services layer exists |
| `docs/architecture/0002-mail-service.md` | Mail as a reusable platform capability |
| `docs/architecture/0003-auth-service.md` | Auth as a reusable platform capability |
| `docs/architecture/0003-storage-service.md` | Storage as a reusable platform capability |
| `docs/architecture/0004-notifications-service.md` | Notifications as a reusable platform capability |

---

## Key Properties

- **Product-agnostic**: Zero references to any specific application.
  All four services can be extracted into standalone packages without
  changing consumers.

- **Configuration-driven**: Provider selection, timeouts, limits: all
  from environment variables. No code changes to switch backends.

- **Mock by default**: Every service defaults to an in-memory mock.
  Zero credentials required for local development. Same code path as
  production.

- **Observable by default**: Every service exposes `health()`,
  `metrics.snapshot()`, and structured logging with consistent field
  naming.

- **Tested by architecture**: Every service has architecture boundary
  tests that prevent accidental dependencies on application code or
  other platform modules.

- **One verify command**: `python -m backend.verify` reports platform
  health and application endpoint status together. Designed for both
  human operators and CI.

---

## Versioning

See [docs/versioning.md](versioning.md) for the complete policy on
public API, breaking changes, and deprecation.

Platform services currently share version 0.1.0.

---

## Out of Scope

The platform layer intentionally does not include:

- **Service discovery**: not needed at single-service scale
- **Distributed tracing**: not needed at current scale
- **Persistent queues**: thread-based queue is sufficient for current
  throughput; replace with Redis/Celery if volume grows
- **Circuit breakers**: added when external provider reliability
  becomes a measurable concern

These may be added to individual services as the application scales,
not as a platform-wide requirement.
