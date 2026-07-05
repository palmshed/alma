# Observability Conventions

This document defines the shared conventions for metrics, logging, and
health reporting across all platform services.

---

## Metrics

### Pattern

Every service defines a dataclass with counter fields, a private
`_durations: list[float]` for timing, an `avg_duration_ms` property,
individual `record_*` methods, and a `snapshot() -> dict` method.

```python
@dataclass
class ServiceNameMetrics:
    operation_a: int = 0
    operation_b: int = 0
    failures: int = 0
    _durations: list[float] = field(default_factory=list, repr=False)

    @property
    def avg_duration_ms(self) -> float:
        if not self._durations:
            return 0.0
        return (sum(self._durations) / len(self._durations)) * 1000

    def record_operation_a(self) -> None:
        self.operation_a += 1

    def record_duration(self, seconds: float) -> None:
        self._durations.append(seconds)

    def snapshot(self) -> dict:
        return {
            "operation_a": self.operation_a,
            "operation_b": self.operation_b,
            "failures": self.failures,
            "avg_duration_ms": round(self.avg_duration_ms, 2),
        }
```

### Conventions

| Rule | Detail |
|------|--------|
| Class name | `<Service>Metrics` |
| Counter names | Plural nouns describing the operation (`uploads`, `logins`) |
| Failure counter | Named `failures` (not `failed`) |
| Timing | `_durations` (private), `avg_duration_ms` (public property) |
| Snapshot | `snapshot() -> dict` returns all counters + `avg_duration_ms` |
| Rounding | `avg_duration_ms` rounded to 2 decimal places |

### Current counters

| Service | Counters |
|---------|----------|
| Mail | `queued`, `sent`, `failed`, `retried`, `avg_duration_ms` |
| Auth | `registrations`, `logins`, `verifications`, `refreshes`, `failures`, `avg_duration_ms` |
| Storage | `uploads`, `downloads`, `deletes`, `lists`, `failures`, `avg_duration_ms` |
| Notifications | `sent`, `failed`, `bounced`, `avg_duration_ms` |

---

## Logging

### Logger names

```
palmshed.{service}.audit
```

Examples: `palmshed.mail.audit`, `palmshed.auth.audit`

### Event keys

Every log call uses the service name as the event key:

| Service | Event key |
|---------|-----------|
| Mail | `mail_event` |
| Auth | `auth_event` |
| Storage | `storage_event` |
| Notifications | `notification_event` |

### Logger class

Each service defines a `<Service>Logger` class with two methods:

- `log_result(result, **context)` — logs the outcome of an operation,
  extracting all available metadata from the result object.
- `log_send(..., **context)` or equivalent — logs a standalone operation
  with explicit parameters when no result object is available.

### Common log fields

Every log entry should include these fields when available:

| Field | Type | When |
|-------|------|------|
| `event` | `str` | Operation name (auth, storage) |
| `service` | `str` | Service name (implied by event key) |
| `status` | `str` | `success`, `failed`, etc. |
| `provider` | `str` | Provider or channel name |
| `duration_ms` | `float` | Operation duration |
| `error` | `str` | Only when status is not success |

Service-specific fields (e.g., `recipient`, `template`, `email`,
`user_id`, `object_name`) are appended as appropriate.

### Conventions

- Use `logger.info(event_key, extra=entry)` — never `logger.warning`
  or `logger.error` for audit events (status is encoded in the entry).
- Conditionally include the `error` key — never set it to an empty string.
- Timestamps are ISO 8601 strings.

---

## Health

### Pattern

Every service exposes a `health() -> HealthStatus` method that returns
a dataclass with service status information.

### Conventions

| Rule | Detail |
|------|--------|
| Return type | Service-specific `HealthStatus` dataclass |
| Config valid | Always include `config_valid: bool` + `config_errors: list[str]` |
| Provider | Always include the active provider name |
| Service-specific | Add fields per service (e.g., `queue_running`, `bucket`) |

### Current health fields

| Service | Health fields |
|---------|---------------|
| Mail | `provider`, `config_valid`, `config_errors`, `queue_running`, `queue_depth`, `templates_valid`, `template_count` |
| Auth | `provider`, `config_valid`, `config_errors` |
| Storage | `provider`, `config_valid`, `config_errors`, `bucket`, `healthy` |
| Notifications | `enabled`, `channels` |

---

## Verify Alignment

The `alma verify` CLI (`backend/verify.py`) reports health in a format
that mirrors each service's health() output.

- Platform checks call `service.health()` directly and map its fields
  into the `details` dict.
- JSON output keys match health status field names.
- Application checks report independent of platform health but use the
  same JSON structure (`name`, `status`, `latency`, `details`, `error`).

When adding a new field to a service's `health()`, add the corresponding
field to the verify CLI's check function for that service.

---

## Changelog

When changing metrics, log fields, or health status fields:

- Log field additions/removals: MINOR version bump (consumer-observable).
- Metric counter additions: no version bump (stateless, no consumer impact).
- Health status field additions: MINOR version bump (consumers may read them).
- Health status field removals: MAJOR version bump.

See [docs/versioning.md](versioning.md) for the full policy.
