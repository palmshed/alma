# Project Philosophy

This document captures the principles that guide how the repository
is structured and maintained. It exists for future contributors who
want to understand *why* things are the way they are.

---

## Principles

### Prefer simple abstractions over generic frameworks

Every abstraction should earn its keep. A `MailProvider` ABC exists
because there are multiple mail backends with real switching
requirements. A generic "ProviderFactory" meta-framework does not
exist because it would add indirection without solving a concrete
problem.

Build for what you have, not for what you imagine you might one day
need.

### Build platform capabilities only after two products need them

The platform services layer exists because future Palmshed products
(Via, Nuntius, Glimpse) would each need mail, auth, storage, and
notifications. Extracting those capabilities once for Alma avoids
rebuilding them three more times.

A capability that only one product will ever use does not belong in
platform services. It belongs in the product.

### Public APIs evolve conservatively

Every symbol listed in a service's `__init__.py` `__all__` is a
commitment. Changing it requires a major version bump, deprecation
warnings, and a migration window.

It is better to leave a symbol internal for an extra release than to
expose it and immediately regret the shape.

### Verification is required before every release

`python -m backend.verify` must pass before any release is cut.
This includes platform health checks plus application endpoint tests.
If CI cannot verify the application in production, the release does
not ship.

### Documentation and tests are part of the implementation

A feature is not complete until it has:

- Tests that cover the public API
- A service README that documents configuration and usage
- Architecture boundary tests that prevent accidental coupling
- A verify CLI entry that operators can run standalone

Documentation is not a separate task. It is the same task.

### Favor the standard library where practical

Mail uses `http.client` instead of `requests`. Auth uses `hmac` +
`hashlib` instead of `PyJWT`. Templates use `string.Template`
instead of Jinja2.

This is not a universal rule — when a dependency dramatically reduces
code or complexity, use it. But default to stdlib first and justify
every external dependency.

### A healthy project says no

The most important architectural skill is knowing when a capability
is not yet needed. The platform will grow. It should grow because
Alma needs it, not because there is another abstract service waiting
to be extracted.

---

## What This Does Not Mean

These principles do not prohibit good engineering. They are not an
excuse to cut corners or defer necessary work. They exist to prevent
the kind of over-engineering that produces elegant infrastructure
and a mediocre product.

The goal is a repository that is easy to understand, easy to change,
and easy to operate — not one that is maximally abstract or
theoretically pure.

---

## Related Documents

- `AGENTS.md` — how to work in this repository
- `docs/architecture.md` — what the platform looks like
- `docs/architecture/*.md` — why specific decisions were made (ADRs)
- `docs/versioning.md` — what counts as a breaking change
- `docs/observability.md` — how services report their state
