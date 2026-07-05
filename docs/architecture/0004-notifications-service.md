# ADR 0004: Notifications Service

## Status

Accepted

## Context

Notifications are a cross-product capability. Products need to send
notifications through multiple channels (email, webhook, future SMS/push)
without being coupled to any specific delivery mechanism.

Key requirements:

- Multi-channel: support email, webhook, and future channels
- Channel-agnostic: the application says "notify" not "send email"
- Reuse Mail: email channel uses the existing MailService
- Product-agnostic: zero coupling to any specific application

## Decision

Introduce `services.notifications` as a Platform Service following the
same architecture as `services.mail`, `services.auth`, and
`services.storage`.

### Architecture

```text
services/notifications/
├── __init__.py          # Public API re-exports
├── config.py            # NotificationConfig from env
├── models.py            # Notification, NotificationResult, NotificationStatus
├── metrics.py           # NotificationMetrics
├── logging.py           # Structured audit logging
├── service.py           # NotificationService (single public API)
├── verify.py            # CLI for end-to-end verification
├── README.md            # Usage guide
└── channels/
    ├── __init__.py       # Auto-registration + factory
    ├── base.py           # NotificationChannel ABC
    ├── registry.py       # ChannelRegistry
    ├── mock.py           # MockChannel (in-memory)
    ├── email.py          # EmailChannel (uses MailService)
    └── webhook.py        # WebhookChannel (HTTP POST)
```

### Channel interface

```python
class NotificationChannel(ABC):
    def send(self, notification: Notification) -> NotificationResult
    def health(self) -> bool

    @property
    def capabilities(self) -> ChannelCapabilities
```

### EmailChannel

Wraps `MailService` to deliver notifications as emails. Uses the
`NOTIFICATION` mail template. Accepts a mail service instance for
dependency injection.

### WebhookChannel

Sends HTTP POST with JSON payload to a configured URL. Used for
integrating with Slack, Discord, custom webhooks, etc.

### PlatformManager integration

```python
platform.notifications.send(
    recipient="user@example.com",
    subject="Hello",
    body="Plain text body",
    channel="email",
)
```

### Health

```json
{
  "notifications": {
    "enabled": true,
    "channels": {
      "mock": "ok",
      "email": "ok",
      "webhook": "unavailable"
    }
  }
}
```

## Consequences

Positive:

- Products can send notifications without choosing a delivery mechanism
- Email channel transparently reuses MailService infrastructure
- Webhook channel enables real-time integrations
- Mock channel enables isolated testing
- Consistent architecture across all platform services

Negative:

- Email channel depends on MailService (not a problem within Palmshed)
- No SMS or push channel in initial implementation
- Webhook channel has no retry or delivery confirmation

## References

- ADR 0001: Platform Services
- ADR 0002: Mail Service
- `services/mail/` — used by EmailChannel
