# ADR 0002: Mail as a Platform Service

**Date:** 2026-07-04
**Status:** Accepted

## Context

Alma needed to send transactional and product emails (welcome,
verification, password reset, notifications). The decision was whether
to embed email logic in Alma or build it as shared infrastructure.

Embedding would have been faster initially but would create coupling:
every future Palmshed product would either depend on Alma or
reimplement email from scratch.

## Decision

Build mail as a Platform Service under `backend/services/mail/`.

The service is:

- provider-agnostic (mock, SMTP, future APIs)
- queue-based (async delivery with retries)
- template-driven (HTML + plain text per template)
- configured via `MailConfig` (single source of truth for env vars)
- registered via `ProviderRegistry` (no hardcoded provider selection)

Applications call a single public API:

```python
mail.send(
    template=MailTemplate.WELCOME,
    recipient="user@example.com",
    context={"name": "...", "product": "Alma", "link": "..."},
)
```

## Consequences

- Alma, Via, Nuntius, and future products all use the same service.
- Providers can be swapped without application changes.
- Templates are centralized and version-controlled.
- The module can be extracted into a standalone service without
  changing its public API.
- Adding a new environment does not require embedding email logic
  in that product.
