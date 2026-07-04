# Mail System

A shared mail capability for Palmshed products. Provider-agnostic,
queue-based, and designed for future extraction into a standalone
service.

---

## Architecture

```
Application (Alma, Via, Nuntius, ...)
    ↓
MailService.send(template, recipient, context)
    ↓
MailQueue (async delivery)
    ↓
MailProvider (SMTP / Mock / future)
    ↓
External provider
```

Applications never talk directly to an email provider or build
HTML/SMTP messages.

---

## Public API

```python
from services.mail import MailService, MailTemplate

svc = MailService()

svc.send(
    template=MailTemplate.WELCOME,
    recipient="user@example.com",
    context={"name": "Niladri", "product": "Alma", "link": "..."},
)
```

Available templates:

| Enum | Template | Subject |
|------|----------|---------|
| `MailTemplate.WELCOME` | `welcome` | Welcome to ${product} |
| `MailTemplate.VERIFICATION` | `verification` | Verify your email |
| `MailTemplate.PASSWORD_RESET` | `password_reset` | Reset your password |
| `MailTemplate.NOTIFICATION` | `notification` | ${subject} |

---

## Directory structure

```
backend/services/mail/
├── __init__.py         # Public API exports
├── config.py           # MailConfig (all env vars centralized)
├── models.py           # MailMessage, MailResult, Address, etc.
├── service.py          # MailService.send()
├── templates.py        # MailTemplate enum, MailTemplates, validation
├── queue.py            # MailQueue ABC + ThreadMailQueue
├── logging.py          # Audit logging (metadata only)
└── providers/
    ├── __init__.py     # get_provider(config) factory
    ├── base.py         # MailProvider ABC
    ├── smtp.py         # SMTPProvider
    └── mock.py         # MockProvider (testing)

templates/mail/
├── welcome.html / .txt
├── verification.html / .txt
├── password_reset.html / .txt
└── notification.html / .txt
```

---

## Configuration

All settings are read from environment variables via `MailConfig.from_env()`:

```
MAIL_PROVIDER          # "mock" (default), "smtp", or "resend"
MAIL_FROM_EMAIL        # Default: hello@palmshed.dev
MAIL_FROM_NAME         # Default: Palmshed
MAIL_REPLY_TO          # Optional reply-to address
MAIL_SYNC              # "true" to send inline (default: "false")
MAIL_ASYNC             # "true" to use background thread (default: "true")
MAIL_TIMEOUT           # Connection timeout in seconds (default: 30)
MAIL_RETRY_MAX         # Max retry attempts (default: 3)
MAIL_RETRY_BASE_DELAY  # Initial retry delay in seconds (default: 1.0)
MAIL_RETRY_MAX_DELAY   # Max retry delay in seconds (default: 60.0)
MAIL_RETRY_BACKOFF     # Exponential backoff factor (default: 2.0)

# SMTP provider:
SMTP_HOST              # Default: localhost
SMTP_PORT              # Default: 587
SMTP_USERNAME
SMTP_PASSWORD
SMTP_TLS               # "true" (default) or "false"

# Resend provider:
RESEND_API_KEY         # API key from resend.com
```

Override programmatically:

```python
from services.mail import MailConfig

config = MailConfig(provider="smtp", sync=True)
svc = MailService(config=config)
```

---

## Providers

## Available providers

| Provider | ID | When to use |
|----------|-----|-------------|
| Mock | `"mock"` | Development and testing (default) |
| SMTP | `"smtp"` | Self-hosted or legacy mail servers |
| Resend | `"resend"` | Production transactional email (recommended) |

### Mock (default)

Captures messages in memory. No real email is sent. Ideal for tests.

```python
svc = MailService()
msg = svc.send(MailTemplate.WELCOME, "test@example.com", context={...})
assert svc.provider.sent[0].template == "welcome"
```

### SMTP

Connects to any SMTP server using the standard library.

```
MAIL_PROVIDER=smtp
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=...
SMTP_PASSWORD=...
```

### Resend (recommended for production)

Uses the Resend REST API over HTTPS. No SDK required — uses `urllib`.

```
MAIL_PROVIDER=resend
RESEND_API_KEY=re_...
```

Supports HTML, plain text, attachments, inline images, CC, BCC, and
Reply-To. Sender identity and Reply-To are configurable via
`MAIL_FROM_NAME`, `MAIL_FROM_EMAIL`, and `MAIL_REPLY_TO`.

Provider capabilities:

| Field | Mock | SMTP | Resend |
|-------|------|------|--------|
| `html` | ✅ | ✅ | ✅ |
| `attachments` | ✅ | ✅ | ✅ |
| `inline_images` | ❌ | ❌ | ✅ |
| `scheduling` | ❌ | ❌ | ❌ |

## Choosing a provider

- **Local development**: Use `mock` (no credentials needed). Captures messages in memory.
- **Integration testing**: Use `resend` with Resend's testing/onboarding domain to send real emails to your personal inbox. No custom domain required.
- **Production**: Use `resend` with a verified `palmshed.dev` domain. Only configuration changes — no application code changes.

## Adding a provider

1. Create a class that extends `MailProvider`.
2. Implement `send(message) -> MailResult` and `capabilities`.
3. Register via `ProviderRegistry`.

```python
from services.mail.providers import MailProvider
from services.mail.models import MailMessage, MailResult, MailStatus, ProviderCapabilities
from services.mail.providers.registry import ProviderRegistry

class MyProvider(MailProvider):
    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(html=True, attachments=True)

    def send(self, message: MailMessage) -> MailResult:
        return MailResult(
            mail_id=message.id or "",
            status=MailStatus.SENT,
            provider="myprovider",
        )

ProviderRegistry.register("myprovider", MyProvider)
```

Set `MAIL_PROVIDER=myprovider`.

---

## Queue model

Default: `ThreadMailQueue` — an in-process background thread.

```
enqueue(message) → Queue → Worker → Provider
                           └→ Retry on failure
```

The queue supports:

- Configurable retry with exponential backoff
- Retry delay: `min(base * factor^attempt, max_delay)`
- Permanent failure after max retries

Replace the queue for production:

```python
from services.mail.queue import MailQueue

class RedisMailQueue(MailQueue):
    def enqueue(self, message): ...
    def start(self): ...
    def stop(self): ...
```

Pass it to `MailService`:

```python
svc = MailService(queue=RedisMailQueue(worker=...))
```

---

## Templates

Every template must include both HTML and plain-text versions.

Validation runs at startup:

- File existence checked for every registered `MailTemplate`
- Required placeholders verified against template content

Add a template:

1. Create `templates/mail/{name}.html` and `templates/mail/{name}.txt`
2. Add the `MailTemplate` enum member in `templates.py`
3. Add the `TemplateDefinition` with metadata and required placeholders

Template variables use `${placeholder}` syntax (Python `string.Template`).

---

## Branding

All outgoing mail:

- **From:** Palmshed <hello@palmshed.dev>
- **Footer:** "Sent by {product}\nBuilt by Palmshed"

Override sender per message:

```python
from services.mail.models import Address

svc.send(..., sender=Address("custom@palmshed.dev", "Custom"))
```

---

## Testing

Use `MockProvider` which captures sent messages:

```python
from services.mail import MailService, MailTemplate

svc = MailService()
svc.send(MailTemplate.WELCOME, "test@example.com", context={...})

# Assert
mock = svc.provider
assert len(mock.sent) == 1
assert mock.sent[0].template == "welcome"
```

The mock provider is the default when `MAIL_PROVIDER` is unset or `"mock"`.

### End-to-end verification

A CLI tool is available for real delivery verification:

```bash
python -m services.mail.verify --to you@example.com
```

It reads `MAIL_PROVIDER`, `RESEND_API_KEY`, and other config from the
environment. If credentials are present, it sends a real email. If not,
it exits with a clear error message.

```bash
# With mock provider — simulates only
MAIL_PROVIDER=mock python -m services.mail.verify --to you@example.com

# With Resend — sends a real email
MAIL_PROVIDER=resend RESEND_API_KEY=re_... \
  python -m services.mail.verify --to you@example.com

# With custom context
python -m services.mail.verify \
  --to you@example.com \
  --template WELCOME \
  --context name=YourName \
  --context product=Alma
```

Exit code is 0 on success, 1 on failure.

## Development without a custom domain

You can send real emails without owning a custom domain. Resend provides
an onboarding email identity for testing.

### 1. Get a Resend API key

1. Sign up at [resend.com](https://resend.com).
2. Navigate to **API Keys** and create a new key.
3. Copy the key (starts with `re_`).

### 2. Configure environment variables

No domain verification needed. Resend provides a default sender address
during onboarding (e.g., `onboarding@resend.dev`).

```env
MAIL_PROVIDER=resend
RESEND_API_KEY=re_...
MAIL_FROM_NAME=Palmshed
MAIL_FROM_EMAIL=onboarding@resend.dev
MAIL_SYNC=true
```

If deploying on Vercel:
- Add these variables in your Vercel project dashboard under **Settings → Environment Variables**.
- Redeploy for changes to take effect.

### 3. Send a test email

```python
from services.mail import MailService, MailTemplate

svc = MailService()
msg = svc.send(
    MailTemplate.WELCOME,
    "yourname@gmail.com",
    context={
        "name": "Test",
        "product": "Alma",
        "link": "https://palmshed.vercel.app",
    },
)
print(f"Sent: {msg.id}, status: {msg.status}")
```

### 4. Limitations during development

- Emails are sent from Resend's testing domain (`@resend.dev`), not `palmshed.dev`.
- Some recipients may see "via resend.dev" in the from address.
- Delivery rates are suitable for development and testing, not production.
- You can send to your personal email (e.g., Gmail) to verify rendering,
  formatting, and plain-text fallback.

### 5. Migrate to a custom domain later

When you own `palmshed.dev`:

1. Add the domain in Resend dashboard.
2. Configure SPF, DKIM, and DMARC DNS records.
3. Update environment variables:

```env
MAIL_FROM_EMAIL=hello@palmshed.dev
MAIL_FROM_NAME=Palmshed
MAIL_REPLY_TO=support@palmshed.dev
```

4. No code changes required — same `MailService`, same `MailTemplate`,
   same `MailConfig` structure.

---

## Production setup

### 1. Verify your domain

In the Resend dashboard, add your domain (e.g., `palmshed.dev`) and
configure the required DNS records:

| Record | Type | Purpose |
|--------|------|---------|
| SPF | TXT | Authorizes Resend to send on your behalf |
| DKIM | TXT | Cryptographically signs outgoing mail |
| DMARC | TXT | Instructs receivers how to handle unauthenticated mail |

Resend provides the exact values during domain setup.

Example SPF:

```txt
v=spf1 include:spf.resend.com ~all
```

Example DMARC:

```txt
v=DMARC1; p=quarantine; adkim=r; aspf=r; rua=mailto:dmarc@palmshed.dev
```

Allow DNS propagation (a few minutes to 48 hours depending on TTL).

### 2. Configure credentials

```env
MAIL_PROVIDER=resend
RESEND_API_KEY=re_...
MAIL_FROM_NAME=Palmshed
MAIL_FROM_EMAIL=hello@palmshed.dev
MAIL_REPLY_TO=support@palmshed.dev
```

Keep credentials out of source control. Use environment variables or
a secrets manager.

### 3. Verify delivery

Send a test email and verify:

- Subject renders correctly
- HTML and plain-text both present
- From matches `Palmshed <hello@palmshed.dev>`
- Reply-To is set
- DKIM signature passes
- SPF passes
- Lands in inbox (not spam)

### 4. Monitor

Check Resend dashboard for:

- Delivery rates
- Bounce rates
- Spam complaints
- Open and click tracking (if enabled)

---

## Go Live Checklist

### Resend

- [ ] Create a Resend account.
- [ ] Generate a production API key.
- [ ] Confirm the allowed sender address (development or verified domain).

### Vercel

- [ ] Set `MAIL_PROVIDER=resend`
- [ ] Set `RESEND_API_KEY`
- [ ] Set `MAIL_FROM_NAME`
- [ ] Set `MAIL_FROM_EMAIL`
- [ ] Set `MAIL_REPLY_TO` (optional)
- [ ] Set `MAIL_SYNC=true` (or verify the queue worker is running)
- [ ] Redeploy.

### Verification

- [ ] Run `python -m services.mail.verify --to you@example.com` locally.
- [ ] Send a welcome email to a real inbox.
- [ ] Confirm `MailResult.status == SENT`.
- [ ] Record the `provider_message_id`.
- [ ] Verify the message appears in the Resend dashboard.
- [ ] Verify delivery to the inbox (or Spam).
- [ ] Verify HTML and plain-text rendering.
- [ ] Verify audit logs, metrics, and correlation ID.

### Sign-off

- [ ] Record the test date: `__________________`
- [ ] Record the sender address used: `__________________`
- [ ] Record the deployment URL: `__________________`
- [ ] Record the Resend environment (development/production): `__________________`

---

## Troubleshooting

| Symptom | Likely cause |
|---------|-------------|
| No email sent | `MAIL_PROVIDER` is still `"mock"` |
| API key errors | `RESEND_API_KEY` not set or incorrect |
| Authentication failed | SMTP credentials wrong |
| Email goes to spam | Missing or misconfigured SPF/DKIM/DMARC |
| Connection timeout | `MAIL_TIMEOUT` too low or network issue |
| "From" address rejected | Sender domain not verified with provider |
| Queue not processing | `MAIL_ASYNC=false` or worker thread not started |

Enable debug logging:

```python
import logging
logging.getLogger("palmshed.mail").setLevel(logging.DEBUG)
```

---

## Logging

Audit logs contain metadata only — never message bodies:

- mail_id
- recipient
- template
- provider
- status
- timestamp
- retry_count
- error (if failed)

Use `MailLogger.log_result(result)` after every send attempt.

---

## Production test record

Record the successful end-to-end delivery test here.

| Field | Value |
|-------|-------|
| Date | |
| Provider | Resend |
| Sender | `onboarding@resend.dev` |
| Recipient | `dasniladri874@gmail.com` |
| Template | `WELCOME` |
| `provider_message_id` returned | ✅ / ❌ |
| Arrived in inbox | ✅ / ❌ / Spam |
| HTML rendered correctly | ✅ / ❌ |
| Plain text rendered correctly | ✅ / ❌ |
| Migration required | No — custom domain purchase deferred |

### Migration to custom domain

When `palmshed.dev` is purchased and verified in Resend:

```env
MAIL_FROM_EMAIL=hello@palmshed.dev
```

Add SPF, DKIM, DMARC DNS records. No code changes required.

---

## Future extraction

The module is designed to be extracted into a standalone Palmshed
service without changing the public API.

Constraints that enable extraction:

1. `MailConfig` centralizes all environment access
2. `MailQueue` is abstract and replaceable
3. No Alma-specific names anywhere
4. Branding is configurable via `MailConfig`
5. Templates are version-controlled in a standard directory
