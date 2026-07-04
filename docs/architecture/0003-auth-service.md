# ADR 0003: Auth Service

## Status

Accepted

## Context

Authentication is a cross-product capability required by every application
built by Palmshed. Rather than implementing auth independently in each
product, we need a reusable, provider-agnostic auth service that can be
shared across products.

Key requirements:

- Provider-agnostic: support multiple auth strategies (JWT, OAuth2, etc.)
- Product-agnostic: zero coupling to any specific application
- Minimal dependencies: core auth works with stdlib only
- Testable: mock provider for development and automated tests

## Decision

Introduce `services.auth` as a new Platform Service following the same
architecture as the mail service (`services.mail`).

### Architecture

```text
services/auth/
├── __init__.py          # Public API re-exports
├── config.py            # AuthConfig from env (single source of truth)
├── models.py            # User, TokenPair, AuthResult, AuthStatus
├── metrics.py           # AuthMetrics (login/register/verify counts)
├── logging.py           # Structured audit logging
├── service.py           # AuthService (single public API)
├── verify.py            # CLI for end-to-end verification
├── README.md            # Versioning policy and usage guide
└── providers/
    ├── __init__.py       # Auto-registration + factory
    ├── base.py           # AuthProvider ABC
    ├── registry.py       # ProviderRegistry (register/create/available)
    ├── mock.py           # MockAuth (in-memory, no dependencies)
    └── jwt.py            # JWTAuth (HMAC-SHA256, stdlib only)
```

### Provider interface

```python
class AuthProvider(ABC):
    def create_user(self, email: str, password: str, **kwargs) -> AuthResult
    def authenticate(self, email: str, password: str) -> AuthResult
    def verify_token(self, token: str) -> AuthResult
    def refresh_token(self, refresh_token: str) -> AuthResult
    def revoke_token(self, refresh_token: str) -> None
```

### AuthService public API

```python
class AuthService:
    def register(self, email: str, password: str, **kwargs) -> AuthResult
    def login(self, email: str, password: str) -> AuthResult
    def verify(self, token: str) -> AuthResult
    def refresh(self, refresh_token: str) -> AuthResult
    def logout(self, refresh_token: str) -> None
    def health(self) -> AuthHealthStatus
```

### Configuration

All environment variables are read exclusively in `AuthConfig.from_env()`:

- `AUTH_PROVIDER` — provider name (default: `mock`)
- `JWT_SECRET` — signing key for JWT tokens
- `JWT_ALGORITHM` — signing algorithm (default: `HS256`)
- `ACCESS_TOKEN_EXPIRE_MINUTES` — access token TTL (default: `15`)
- `REFRESH_TOKEN_EXPIRE_DAYS` — refresh token TTL (default: `7`)

### Mock provider

`MockAuth` stores users and sessions in memory. No credentials or secrets
required. Used by default in development and tests.

### JWT provider

`JWTAuth` implements self-contained JWT tokens using stdlib (`hmac`,
`hashlib`, `base64`, `json`). No external JWT library required. Tokens are
signed with HMAC-SHA256.

### Health integration

The health endpoint instantiates `AuthService` lazily and includes the
provider name and config validity in the health response.

## Consequences

Positive:

- Products can authenticate users without choosing a provider
- Mock provider enables isolated testing
- Consistent architecture across mail and auth services
- Architecture boundary tests enforce product-agnostic constraints

Negative:

- Initial JWT provider uses basic HMAC; advanced features (RS256, JWKs)
  require future enhancement
- No storage persistence in mock provider (in-memory only)

## References

- ADR 0001: Platform Services
- ADR 0002: Mail Service
- `services/mail/` — reference implementation
