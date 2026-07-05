# Versioning Policy

This document defines what constitutes a public API, how breaking
changes are handled, and what versioning expectations consumers
should have for platform services.

---

## Version Scheme

Platform services follow [Semantic Versioning 2.0.0](https://semver.org/):

- **MAJOR** — incompatible API changes
- **MINOR** — backward-compatible additions
- **PATCH** — backward-compatible bug fixes

All four services share the same version number (currently 0.1.0).
Application code depends on `services` as a single unit, so there is
no per-service version pinning.

---

## What Is Public API

Every symbol listed in each service's `__init__.py` `__all__` is
considered part of the public API.

### Mail (`backend/services/mail/`)

`MailConfig`, `MailMetrics`, `MailService`, `MailMessage`, `MailResult`,
`MailStatus`, `MailPriority`, `MailError`, `MailValidationError`,
`RetryPolicy`, `HealthStatus`, `ProviderCapabilities`, `MailTemplate`,
`MailTemplates`, `TemplateDefinition`, `MailProvider`, `ProviderRegistry`,
`MailQueue`, `get_provider`, `get_queue`

### Auth (`backend/services/auth/`)

`AuthConfig`, `AuthMetrics`, `AuthService`, `AuthResult`, `AuthStatus`,
`TokenPair`, `User`, `AuthError`, `AuthValidationError`,
`AuthHealthStatus`, `AuthProvider`, `ProviderRegistry`, `get_provider`

### Storage (`backend/services/storage/`)

`StorageConfig`, `StorageMetrics`, `StorageService`, `StorageObject`,
`StorageResult`, `StorageStatus`, `StorageError`,
`StorageValidationError`, `StorageHealth`, `ProviderCapabilities`,
`StorageProvider`, `ProviderRegistry`, `get_provider`

### Notifications (`backend/services/notifications/`)

`NotificationConfig`, `NotificationMetrics`, `NotificationService`,
`Notification`, `NotificationResult`, `NotificationStatus`,
`NotificationPriority`, `NotificationError`, `NotificationHealth`,
`ChannelCapabilities`, `NotificationChannel`, `MockChannel`,
`EmailChannel`, `WebhookChannel`, `ChannelRegistry`, `get_channel`

Everything else — internal modules, private functions, underscore-prefixed
symbols, test helpers — is not part of the public API and may change
without notice.

---

## What Counts as Breaking

The following changes require a MAJOR version bump:

- Removing or renaming a public symbol
- Changing the signature of a public method
- Changing the shape of a public dataclass or return type
- Adding a required method to an abstract base class
- Removing a registered enum member (e.g., `MailTemplate.WELCOME`)
- Changing the meaning of an existing configuration field

## What Does Not Count as Breaking

The following are backward compatible (MINOR or PATCH):

- Adding new public symbols
- Adding optional parameters to public methods (with defaults)
- Adding new enum members
- Adding optional fields to config dataclasses
- Adding new methods to ABCs with default implementations
- Adding new providers via `ProviderRegistry`
- Adding new templates or template definitions
- Internal refactoring of modules not listed in `__all__`
- Adding new environment variables
- Changing metric names or log messages (consumer-observable but not API)

---

## Deprecation Process

1. **Announce**: Mark the symbol as deprecated in its docstring.
   Log a `DeprecationWarning` when the old path is used at runtime.

2. **Support**: Keep the symbol for one MINOR version cycle after
   deprecation. Consumers have at least one release to migrate.

3. **Remove**: Delete the symbol in the next MAJOR version bump.
   Include the removal in the changelog.

Example:

```python
import warnings

def old_function():
    warnings.warn(
        "old_function is deprecated, use new_function instead",
        DeprecationWarning,
        stacklevel=2,
    )
    # ... implementation ...
```

`DeprecationWarning` is silent by default in Python. Consumers who
want to see them can use `-Wd` or filter explicitly:

```bash
python -Wd -c "from services.mail import old_function"
```

---

## Changelog

Each MAJOR and MINOR release must include a changelog entry describing:

- New public symbols
- Changed behavior
- Deprecated symbols and their replacements
- Removed symbols and migration path

Changelog entries live in each service README under a "Changelog"
section or in the repository-level `CHANGELOG.md`.

---

## Verify CLI Stability

The `backend/verify.py` CLI follows its own stability contract:

- `--json` output format is stable within a MAJOR version
- Human-readable output may change without notice (it is for operators,
  not parsers)
- New flags and sub-commands are backward compatible
- Removing a flag requires a MAJOR version bump
- New keys in JSON output are backward compatible
- Removing a key from JSON output requires a MAJOR version bump
