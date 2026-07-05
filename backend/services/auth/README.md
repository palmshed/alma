# Auth Service

Provider-agnostic authentication for Palmshed products.

## Architecture

```
┌─────────────────┐
│   AuthService    │  ← Public API (single entry point)
│  register()     │
│  login()        │
│  verify()       │
│  refresh()      │
│  logout()       │
│  health()       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  AuthProvider    │  ← ABC (pluggable backend)
│  MockAuth       │  ← In-memory, no credentials
│  JWTAuth        │  ← HMAC-SHA256 JWT (stdlib only)
└─────────────────┘
```

## Quick Start

```python
from services.auth import AuthService

svc = AuthService()

# Register
result = svc.register("user@example.com", "secure-password")
if result.status.value == "success":
    user = result.user

# Login
result = svc.login("user@example.com", "secure-password")
if result.status.value == "success":
    access_token = result.token_pair.access_token
    refresh_token = result.token_pair.refresh_token

# Verify
result = svc.verify(access_token)
if result.status.value == "success":
    print(f"Authenticated: {result.user.email}")

# Refresh
result = svc.refresh(refresh_token)
new_access = result.token_pair.access_token

# Logout
svc.logout(refresh_token)
```

## Configuration

All environment variables are read in `AuthConfig.from_env()`:

| Variable | Default | Description |
|---|---|---|
| `AUTH_PROVIDER` | `mock` | Provider name (`mock`, `jwt`) |
| `JWT_SECRET` | `` | HMAC signing key (required for jwt) |
| `JWT_ALGORITHM` | `HS256` | Signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |

## Providers

### Mock (default)

No credentials required. Suitable for development and tests.

### JWT

Self-contained tokens using stdlib (`hmac`, `hashlib`, `base64`).
Requires `JWT_SECRET` to be set.

```bash
# Generate a secure secret
python3 -c "import secrets; print(secrets.token_hex(32))"
export JWT_SECRET="your-256-bit-secret"
export AUTH_PROVIDER=jwt
```

## Public API

### `AuthService`

| Method | Returns | Description |
|---|---|---|
| `register(email, password)` | `AuthResult` | Create a new user |
| `login(email, password)` | `AuthResult` | Authenticate and get tokens |
| `verify(token)` | `AuthResult` | Validate an access token |
| `refresh(refresh_token)` | `AuthResult` | Get new token pair |
| `logout(refresh_token)` | `None` | Revoke a refresh token |
| `health()` | `AuthHealthStatus` | Provider and config status |

### `AuthResult`

| Field | Type | Description |
|---|---|---|
| `status` | `AuthStatus` | `success`, `failed`, `expired`, `invalid`, `locked` |
| `user` | `User` | Authenticated user (on success) |
| `token_pair` | `TokenPair` | Access + refresh tokens (on login/register/refresh) |
| `error` | `str` | Error message (on failure) |
| `provider` | `str` | Provider name that handled the request |

## Versioning

See [docs/versioning.md](../../../docs/versioning.md) for the complete
policy. Public API is defined by `__init__.py` exports.

## Adding a Provider

1. Create `providers/your_provider.py`
2. Implement the `AuthProvider` ABC
3. Register in `providers/__init__.py`: `ProviderRegistry.register("name", YourProvider)`
4. Add config fields in `AuthConfig` if needed
5. Add validation in `AuthConfig.is_valid()`

## Testing

```bash
# Unit tests
uv run pytest backend/tests/test_auth.py

# End-to-end verification
python -m services.auth.verify
python -m services.auth.verify --email user@example.com --password MyPass123!
```

## Directory Structure

```
services/auth/
├── __init__.py       # Public API re-exports
├── config.py         # AuthConfig from env
├── models.py         # User, TokenPair, AuthResult, AuthStatus
├── service.py        # AuthService (public API)
├── metrics.py        # AuthMetrics
├── logging.py        # Audit logging
├── verify.py         # CLI verification
├── README.md         # This file
└── providers/
    ├── __init__.py   # Auto-registration + factory
    ├── base.py       # AuthProvider ABC
    ├── registry.py   # ProviderRegistry
    ├── mock.py       # MockAuth (in-memory)
    └── jwt.py        # JWTAuth (stdlib only)
```
