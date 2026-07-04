# Mail Service

A shared mail capability for Palmshed products. Provider-agnostic,
queue-based, and designed for future extraction into a standalone
service.

## Architecture

```
Application
    ↓
MailService.send(template, recipient, context)
    ↓
MailQueue (async delivery with retries)
    ↓
MailProvider (mock / smtp / custom)
    ↓
External provider
```

Dependencies: `MailService` → `MailTemplates` → `MailProvider` → External.

Applications never talk to a provider directly or build HTML/SMTP messages.

## Public API (stable)

| Symbol | Purpose |
|--------|---------|
| `MailService` | Main entry point. Call `send()` to dispatch emails. |
| `MailTemplate` | Enum of known templates (`WELCOME`, `VERIFICATION`, ...). |
| `MailProvider` | Abstract base for provider implementations. |
| `MailResult` | Dataclass returned by every send attempt. |
| `MailConfig` | Centralized configuration from environment variables. |
| `MailMessage` | Internal message dataclass. |
| `MailQueue` | Abstract base for queue implementations. |

These interfaces will not change without a major version bump.

Internal modules (`templates.py`, `queue.py`, `metrics.py`, etc.) may
evolve without notice.

## Quick start

```python
from services.mail import MailService, MailTemplate

svc = MailService()

msg = svc.send(
    template=MailTemplate.WELCOME,
    recipient="user@example.com",
    context={"name": "Niladri", "product": "Alma", "link": "https://..."},
)
```

For synchronous delivery:

```python
from services.mail import MailConfig

config = MailConfig(sync=True)
svc = MailService(config=config)
```

## Configuration

All settings from environment variables (`MailConfig.from_env()`):

```
MAIL_PROVIDER          # "mock" (default), "smtp", or "resend"
MAIL_FROM_EMAIL        # Default: hello@palmshed.dev
MAIL_FROM_NAME         # Default: Palmshed
MAIL_REPLY_TO          # Optional reply-to address
MAIL_SYNC              # "true" for inline sending
MAIL_ASYNC             # "true" for background thread
MAIL_TIMEOUT           # Connection timeout (default: 30)
MAIL_RETRY_MAX         # Max retries (default: 3)
MAIL_RETRY_BASE_DELAY  # Initial retry delay in seconds (default: 1.0)
MAIL_RETRY_MAX_DELAY   # Max retry delay in seconds (default: 60.0)
MAIL_RETRY_BACKOFF     # Backoff factor (default: 2.0)
MAIL_MAX_RECIPIENTS    # Max total recipients (default: 50)
MAIL_MAX_ATTACHMENT_MB # Max attachment size in MB (default: 10)
MAIL_MAX_CONTEXT_BYTES # Max template context size (default: 65536)

# SMTP only:
SMTP_HOST
SMTP_PORT
SMTP_USERNAME
SMTP_PASSWORD
SMTP_TLS

# Resend only:
RESEND_API_KEY
```

Override programmatically:

```python
config = MailConfig(provider="smtp", max_recipients=10)
svc = MailService(config=config)
```

### Versioning policy

Breaking changes require deliberation. The following constitute a
breaking API change:

- Removing or renaming a public symbol (`MailService`, `MailTemplate`, etc.)
- Changing the signature of `MailService.send()`
- Changing the shape of `MailResult` or `MailConfig` fields
- Changing the `MailProvider` ABC (adding required methods)
- Removing a registered `MailTemplate` enum member

The following are **not** breaking:

- Adding new enum members to `MailTemplate`
- Adding optional fields to `MailConfig`
- Adding new methods to `MailProvider` with default implementations
- Adding new providers via `ProviderRegistry`
- Adding new templates or template definitions
- Internal refactoring of `queue.py`, `metrics.py`, `logging.py`
- Adding new environment variables

Deprecation policy:

- Deprecate a feature for one minor cycle before removal
- Log a deprecation warning when the old path is used
- Remove only in a major version bump

## Choosing a provider

| Phase | Provider | Domain required | Notes |
|-------|----------|-----------------|-------|
| Development | `mock` | No | No credentials needed. Captures in memory. |
| Integration testing | `resend` | No | Resend's onboarding domain (`@resend.dev`). Send real emails to your inbox. |
| Production | `resend` | Yes (`palmshed.dev`) | Verified domain with SPF/DKIM/DMARC. |

Moving from integration testing to production requires only
configuration and DNS changes — no application code changes.

## Adding a provider

1. Create a class that extends `MailProvider`.
2. Implement `send(message) -> MailResult` and `capabilities`.
3. Register it via `ProviderRegistry.register("name", MyProvider)`.

```python
from services.mail.providers import MailProvider
from services.mail.models import MailMessage, MailResult, MailStatus, ProviderCapabilities

class MyProvider(MailProvider):
    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(html=True, attachments=True)

    def send(self, message: MailMessage) -> MailResult:
        # ... send via your API ...
        return MailResult(
            mail_id=message.id or "",
            status=MailStatus.SENT,
            provider="myprovider",
        )
```

Set `MAIL_PROVIDER=myprovider` and register before creating `MailService`:

```python
from services.mail.providers.registry import ProviderRegistry

ProviderRegistry.register("myprovider", MyProvider)
```

## Adding a template

1. Create `templates/mail/{name}.html` and `templates/mail/{name}.txt`.
2. Add an enum member to `MailTemplate` in `templates.py`.
3. Add metadata to `_TEMPLATE_METADATA` with required placeholders.

Variables use `${placeholder}` syntax (Python `string.Template`).

Validation runs at startup: files must exist and required placeholders
must appear in the template content.

## Testing

The default provider is `MockProvider`, which captures sent messages
in memory:

```python
svc = MailService()
msg = svc.send(MailTemplate.WELCOME, "test@example.com", context={...})
assert svc.provider.sent[0].template == "welcome"
```

Run the full test suite:

```
python -m pytest backend/tests/test_mail.py -v
```

Integration tests with pytest verify the complete pipeline:
queue → worker → provider → logging → metrics → retries.

Health check for diagnostics:

```python
status = svc.health()
print(status.provider, status.queue_depth, status.templates_valid)
```

Metrics snapshot:

```python
snap = svc.metrics.snapshot()
print(snap["sent"], snap["failed"], snap["avg_duration_ms"])
```

## Lifecycle

```python
# Start
svc = MailService()

# Send (adds to queue, starts background thread)
svc.send(MailTemplate.WELCOME, ...)

# Graceful shutdown — drains queue, waits for in-flight sends
svc.shutdown(timeout=5.0)
```

Call `shutdown()` on application exit to avoid silent message loss.

## Directory structure

```
backend/services/mail/
├── README.md           # This file
├── __init__.py         # Public API exports
├── config.py           # MailConfig (centralized env vars)
├── models.py           # MailMessage, MailResult, Address, HealthStatus, etc.
├── metrics.py          # MailMetrics (queued, sent, failed, retried, duration)
├── service.py          # MailService.send(), health(), shutdown()
├── templates.py        # MailTemplate enum, validation, rendering
├── queue.py            # MailQueue ABC + ThreadMailQueue
├── logging.py          # Audit logging (metadata only)
└── providers/
    ├── __init__.py     # Auto-registers mock, smtp, and resend providers
    ├── base.py         # MailProvider ABC
    ├── registry.py     # ProviderRegistry — register, create, list
    ├── mock.py         # MockProvider (testing)
    ├── smtp.py         # SMTPProvider
    └── resend.py       # ResendProvider (production)
```
