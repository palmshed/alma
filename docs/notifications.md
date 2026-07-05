# Notifications System

Multi-channel notification delivery for Palmshed products.

---

## Architecture

```
Application
    ↓
NotificationService.send(recipient, subject, body)
    ↓
NotificationChannel (Mock / Email / Webhook / future)
    ↓
Delivery (in-memory / MailService / HTTP POST)
```

---

## Channels

| Channel   | Status | Description |
|-----------|--------|-------------|
| `mock`    | ✓      | In-memory capture, no external delivery |
| `email`   | ✓      | Delivers via MailService (NOTIFICATION template) |
| `webhook` | ✓      | HTTP POST to configurable URL |

### Adding a Channel

1. Create `channels/sms.py`
2. Implement `NotificationChannel` ABC
3. Register in `channels/__init__.py`

No application code changes needed.

---

## Configuration

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `NOTIFICATIONS_ENABLED` | `true` | no | Master toggle |
| `NOTIFICATIONS_DEFAULT_CHANNEL` | `mock` | no | Channel to use when none specified |
| `NOTIFICATIONS_WEBHOOK_URL` | — | for webhook | URL for webhook channel |
| `NOTIFICATIONS_WEBHOOK_TIMEOUT` | `10` | no | Webhook timeout in seconds |

---

## Usage

```python
from services import platform

# Default channel
platform.notifications.send(
    recipient="user@example.com",
    subject="Hello",
    body="Plain text body",
)

# Specific channel
platform.notifications.send(
    recipient="user@example.com",
    subject="Hello",
    body="Plain text body",
    channel="email",
)

# With HTML body
platform.notifications.send(
    recipient="user@example.com",
    subject="Hello",
    body="Plain text",
    body_html="<p>HTML version</p>",
)
```

---

## Health

`GET /api/health` includes notifications status:

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

---

## Verification CLI

```bash
python -m services.notifications.verify --to user@example.com
```

---

## Architecture

See `docs/architecture/0004-notifications-service.md` for the Architecture
Decision Record.
