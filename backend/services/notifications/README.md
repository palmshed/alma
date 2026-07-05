# Notifications Platform Service

Multi-channel notification delivery for Palmshed products.

## Channels

| Channel   | Description |
|-----------|-------------|
| `mock`    | In-memory capture (default, no setup) |
| `email`   | Delivers via MailService (requires `services.mail`) |
| `webhook` | HTTP POST to configurable URL |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `NOTIFICATIONS_ENABLED` | `true` | Master toggle |
| `NOTIFICATIONS_DEFAULT_CHANNEL` | `mock` | Channel name |
| `NOTIFICATIONS_WEBHOOK_URL` | — | URL for webhook channel |
| `NOTIFICATIONS_WEBHOOK_TIMEOUT` | `10` | Webhook timeout in seconds |

## Usage

```python
from services.notifications import NotificationService

svc = NotificationService()
result = svc.send(
    recipient="user@example.com",
    subject="Hello",
    body="Plain text body",
    channel="email",
)
```

## Verification

```bash
python -m services.notifications.verify --to user@example.com
```

## Adding a Channel

1. Create `channels/sms.py`
2. Implement `NotificationChannel` ABC
3. Register in `channels/__init__.py`
