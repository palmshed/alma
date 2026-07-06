import os
import sys
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

# --- Architecture boundary tests ---


class TestArchitecture:
    """Enforce service boundaries: auth must not import application modules."""

    FORBIDDEN_MODULES = [
        "flask",
        "django",
        "react",
        "jsx",
        "palmshed_ai",
        "templates",
    ]

    @pytest.mark.parametrize("module", FORBIDDEN_MODULES)
    def test_auth_never_imports_application_modules(self, module):
        for mod in sys.modules:
            if mod.startswith("services.auth"):
                assert module not in mod, f"{mod} imports {module}"

    @pytest.mark.parametrize("module", FORBIDDEN_MODULES)
    def test_providers_never_import_application_code(self, module):
        for mod_name in ("services.auth.providers.mock", "services.auth.providers.jwt"):
            mod = sys.modules.get(mod_name)
            if mod:
                src = mod.__file__ or ""
                with open(src) as f:
                    content = f.read()
                for forbidden in self.FORBIDDEN_MODULES:
                    # Allow self-references and stdlib
                    if forbidden in ("os", "sys"):
                        continue
                    assert forbidden not in content, (
                        f"{mod_name} references {forbidden}"
                    )

    def test_providers_use_base_class(self):
        from services.auth.providers.base import AuthProvider
        from services.auth.providers.mock import MockAuth
        from services.auth.providers.jwt import JWTAuth

        assert issubclass(MockAuth, AuthProvider)
        assert issubclass(JWTAuth, AuthProvider)

    def test_config_is_single_source_of_env(self):
        for mod_name in (
            "services.auth.models",
            "services.auth.service",
            "services.auth.metrics",
            "services.auth.logging",
            "services.auth.providers.base",
            "services.auth.providers.registry",
            "services.auth.providers.mock",
            "services.auth.providers.jwt",
        ):
            mod = sys.modules.get(mod_name)
            if mod and hasattr(mod, "__file__") and mod.__file__:
                src = mod.__file__
                with open(src) as f:
                    content = f.read()
                lines_with_osenv = [
                    (i + 1, line.strip())
                    for i, line in enumerate(content.split("\n"))
                    if "os.environ" in line or "os.getenv" in line
                ]
                assert not lines_with_osenv, (
                    f"{mod_name} reads os.environ at lines: {lines_with_osenv}"
                )

    def test_service_accepts_only_valid_inputs(self):
        from services.auth.service import AuthService

        svc = AuthService()

        with pytest.raises(Exception):
            svc.register(email="", password="pass")

        with pytest.raises(Exception):
            svc.register(email="not-an-email", password="pass")

        with pytest.raises(Exception):
            svc.register(email="a@b.com", password="short")

    def test_health_status_provider_included(self):
        from services.auth.service import AuthService

        svc = AuthService()
        health = svc.health()
        assert health.provider
        assert isinstance(health.config_valid, bool)


# --- Model tests ---


class TestAuthModels:
    def test_user_creation(self):
        from services.auth.models import User

        user = User(id="1", email="test@example.com")
        assert user.id == "1"
        assert user.email == "test@example.com"
        assert user.is_active is True
        assert user.display_name == ""

    def test_user_with_display_name(self):
        from services.auth.models import User

        user = User(id="1", email="test@example.com", display_name="Test User")
        assert user.display_name == "Test User"

    def test_token_pair_creation(self):
        from services.auth.models import TokenPair

        now = datetime.now(timezone.utc)
        tp = TokenPair(
            access_token="access123",
            refresh_token="refresh123",
            expires_at=now,
        )
        assert tp.access_token == "access123"
        assert tp.refresh_token == "refresh123"
        assert tp.token_type == "Bearer"

    def test_auth_result_success(self):
        from services.auth.models import AuthResult, AuthStatus, User

        result = AuthResult(
            status=AuthStatus.SUCCESS,
            user=User(id="1", email="test@example.com"),
            provider="mock",
        )
        assert result.status == AuthStatus.SUCCESS
        assert result.user.email == "test@example.com"
        assert result.error is None

    def test_auth_result_failure(self):
        from services.auth.models import AuthResult, AuthStatus

        result = AuthResult(
            status=AuthStatus.FAILED,
            error="Invalid credentials",
            provider="mock",
        )
        assert result.status == AuthStatus.FAILED
        assert result.error == "Invalid credentials"

    def test_auth_status_values(self):
        from services.auth.models import AuthStatus

        assert AuthStatus.SUCCESS.value == "success"
        assert AuthStatus.FAILED.value == "failed"
        assert AuthStatus.EXPIRED.value == "expired"
        assert AuthStatus.INVALID.value == "invalid"
        assert AuthStatus.LOCKED.value == "locked"

    def test_auth_health_status(self):
        from services.auth.models import AuthHealthStatus

        hs = AuthHealthStatus(provider="mock", config_valid=True)
        assert hs.provider == "mock"
        assert hs.config_valid is True
        assert hs.config_errors == []

    def test_auth_health_status_with_errors(self):
        from services.auth.models import AuthHealthStatus

        hs = AuthHealthStatus(
            provider="jwt", config_valid=False, config_errors=["JWT_SECRET missing"]
        )
        assert hs.config_valid is False
        assert "JWT_SECRET missing" in hs.config_errors


# --- Config tests ---


class TestAuthConfig:
    def test_default_config(self):
        from services.auth.config import AuthConfig

        config = AuthConfig()
        assert config.provider == "mock"
        assert config.jwt_secret == ""
        assert config.jwt_algorithm == "HS256"
        assert config.access_token_expire_minutes == 15
        assert config.refresh_token_expire_days == 7

    def test_config_validation_valid_mock(self):
        from services.auth.config import AuthConfig

        valid, errors = AuthConfig().is_valid()
        assert valid
        assert errors == []

    def test_config_validation_valid_jwt(self):
        from services.auth.config import AuthConfig

        valid, errors = AuthConfig(provider="jwt", jwt_secret="mysecret").is_valid()
        assert valid
        assert errors == []

    def test_config_validation_missing_jwt_secret(self):
        from services.auth.config import AuthConfig

        valid, errors = AuthConfig(provider="jwt").is_valid()
        assert not valid
        assert "JWT_SECRET is required" in errors[0]

    def test_config_validation_invalid_provider(self):
        from services.auth.config import AuthConfig

        valid, errors = AuthConfig(provider="unknown").is_valid()
        assert not valid
        assert "Unknown auth provider" in errors[0]

    def test_from_env_defaults(self):
        from services.auth.config import AuthConfig

        with patch.dict(os.environ, {}, clear=True):
            config = AuthConfig.from_env()
            assert config.provider == "mock"
            assert config.jwt_secret == ""

    def test_from_env_override(self):
        from services.auth.config import AuthConfig

        with patch.dict(
            os.environ,
            {
                "AUTH_PROVIDER": "jwt",
                "JWT_SECRET": "super-secret",
                "JWT_ALGORITHM": "HS384",
                "ACCESS_TOKEN_EXPIRE_MINUTES": "30",
                "REFRESH_TOKEN_EXPIRE_DAYS": "14",
            },
        ):
            config = AuthConfig.from_env()
            assert config.provider == "jwt"
            assert config.jwt_secret == "super-secret"
            assert config.jwt_algorithm == "HS384"
            assert config.access_token_expire_minutes == 30
            assert config.refresh_token_expire_days == 14


# --- Metrics tests ---


class TestAuthMetrics:
    def test_initial_state(self):
        from services.auth.metrics import AuthMetrics

        m = AuthMetrics()
        assert m.registrations == 0
        assert m.logins == 0
        assert m.verifications == 0
        assert m.refreshes == 0
        assert m.failures == 0
        assert m.avg_duration_ms == 0.0

    def test_record_counts(self):
        from services.auth.metrics import AuthMetrics

        m = AuthMetrics()
        m.record_registration()
        m.record_login()
        m.record_verification()
        m.record_refresh()
        m.record_failure()
        assert m.registrations == 1
        assert m.logins == 1
        assert m.verifications == 1
        assert m.refreshes == 1
        assert m.failures == 1

    def test_average_duration(self):
        from services.auth.metrics import AuthMetrics

        m = AuthMetrics()
        m.record_duration(0.1)
        m.record_duration(0.3)
        assert round(m.avg_duration_ms, 1) == 200.0

    def test_snapshot(self):
        from services.auth.metrics import AuthMetrics

        m = AuthMetrics()
        m.record_registration()
        m.record_login()
        snap = m.snapshot()
        assert snap["registrations"] == 1
        assert snap["logins"] == 1
        assert "avg_duration_ms" in snap


# --- Mock provider tests ---


class TestMockAuth:
    def test_create_user_returns_success(self):
        from services.auth.providers.mock import MockAuth

        provider = MockAuth()
        result = provider.create_user("test@example.com", "password123")
        assert result.status.value == "success"
        assert result.user.email == "test@example.com"

    def test_create_user_duplicate(self):
        from services.auth.providers.mock import MockAuth

        provider = MockAuth()
        provider.create_user("dup@example.com", "password123")
        result = provider.create_user("dup@example.com", "password123")
        assert result.status.value == "failed"
        assert "already exists" in result.error

    def test_login_success(self):
        from services.auth.providers.mock import MockAuth

        provider = MockAuth()
        provider.create_user("login@example.com", "mypassword")
        result = provider.authenticate("login@example.com", "mypassword")
        assert result.status.value == "success"
        assert result.token_pair is not None
        assert result.token_pair.access_token
        assert result.token_pair.refresh_token

    def test_login_wrong_password(self):
        from services.auth.providers.mock import MockAuth

        provider = MockAuth()
        provider.create_user("user@example.com", "correct")
        result = provider.authenticate("user@example.com", "wrong")
        assert result.status.value == "failed"

    def test_login_unknown_user(self):
        from services.auth.providers.mock import MockAuth

        provider = MockAuth()
        result = provider.authenticate("nobody@example.com", "password")
        assert result.status.value == "failed"
        assert "Invalid email or password" in result.error

    def test_verify_token_valid(self):
        from services.auth.providers.mock import MockAuth

        provider = MockAuth()
        provider.create_user("verify@example.com", "password")
        login_result = provider.authenticate("verify@example.com", "password")
        token = login_result.token_pair.access_token

        result = provider.verify_token(token)
        assert result.status.value == "success"
        assert result.user.email == "verify@example.com"

    def test_verify_token_invalid(self):
        from services.auth.providers.mock import MockAuth

        provider = MockAuth()
        result = provider.verify_token("invalid-token")
        assert result.status.value == "invalid"

    def test_refresh_token(self):
        from services.auth.providers.mock import MockAuth

        provider = MockAuth()
        provider.create_user("refresh@example.com", "password")
        login_result = provider.authenticate("refresh@example.com", "password")
        old_refresh = login_result.token_pair.refresh_token

        result = provider.refresh_token(old_refresh)
        assert result.status.value == "success"
        assert result.token_pair.access_token != login_result.token_pair.access_token
        assert result.token_pair.refresh_token != old_refresh
        # Old refresh token should be invalidated
        old_result = provider.refresh_token(old_refresh)
        assert old_result.status.value == "invalid"

    def test_revoke_token(self):
        from services.auth.providers.mock import MockAuth

        provider = MockAuth()
        provider.create_user("revoke@example.com", "password")
        login_result = provider.authenticate("revoke@example.com", "password")
        refresh = login_result.token_pair.refresh_token

        provider.revoke_token(refresh)
        result = provider.refresh_token(refresh)
        assert result.status.value == "invalid"

    def test_reset(self):
        from services.auth.providers.mock import MockAuth

        provider = MockAuth()
        provider.create_user("reset@example.com", "password")
        assert len(provider._users) == 1
        provider.reset()
        assert len(provider._users) == 0
        assert len(provider._refresh_tokens) == 0


# --- JWT provider tests ---


class TestJWTAuth:
    def test_create_user_returns_success(self):
        from services.auth.providers.jwt import JWTAuth
        from services.auth.config import AuthConfig

        config = AuthConfig(provider="jwt", jwt_secret="test-secret-key")
        provider = JWTAuth(config)
        result = provider.create_user("test@example.com", "password123")
        assert result.status.value == "success"
        assert result.user.email == "test@example.com"

    def test_create_user_duplicate(self):
        from services.auth.providers.jwt import JWTAuth
        from services.auth.config import AuthConfig

        config = AuthConfig(provider="jwt", jwt_secret="test-secret-key")
        provider = JWTAuth(config)
        provider.create_user("dup@example.com", "password123")
        result = provider.create_user("dup@example.com", "password123")
        assert result.status.value == "failed"

    def test_login_success(self):
        from services.auth.providers.jwt import JWTAuth
        from services.auth.config import AuthConfig

        config = AuthConfig(provider="jwt", jwt_secret="test-secret-key")
        provider = JWTAuth(config)
        provider.create_user("login@example.com", "mypassword")
        result = provider.authenticate("login@example.com", "mypassword")
        assert result.status.value == "success"
        assert result.token_pair is not None

    def test_login_wrong_password(self):
        from services.auth.providers.jwt import JWTAuth
        from services.auth.config import AuthConfig

        config = AuthConfig(provider="jwt", jwt_secret="test-secret-key")
        provider = JWTAuth(config)
        provider.create_user("user@example.com", "correct")
        result = provider.authenticate("user@example.com", "wrong")
        assert result.status.value == "failed"

    def test_verify_token_valid(self):
        from services.auth.providers.jwt import JWTAuth
        from services.auth.config import AuthConfig

        config = AuthConfig(provider="jwt", jwt_secret="test-secret-key")
        provider = JWTAuth(config)
        provider.create_user("verify@example.com", "password")
        login_result = provider.authenticate("verify@example.com", "password")
        token = login_result.token_pair.access_token

        result = provider.verify_token(token)
        assert result.status.value == "success"
        assert result.user.email == "verify@example.com"

    def test_verify_token_tampered(self):
        from services.auth.providers.jwt import JWTAuth
        from services.auth.config import AuthConfig

        config = AuthConfig(provider="jwt", jwt_secret="test-secret-key")
        provider = JWTAuth(config)
        result = provider.verify_token("tampered.token.here")
        assert result.status.value == "invalid"

    def test_verify_token_wrong_secret(self):
        from services.auth.providers.jwt import JWTAuth
        from services.auth.config import AuthConfig

        config1 = AuthConfig(provider="jwt", jwt_secret="secret1")
        config2 = AuthConfig(provider="jwt", jwt_secret="secret2")
        provider1 = JWTAuth(config1)
        provider2 = JWTAuth(config2)

        provider1.create_user("test@example.com", "password")
        login_result = provider1.authenticate("test@example.com", "password")
        token = login_result.token_pair.access_token

        result = provider2.verify_token(token)
        assert result.status.value == "invalid"

    def test_refresh_token(self):
        from services.auth.providers.jwt import JWTAuth
        from services.auth.config import AuthConfig

        config = AuthConfig(provider="jwt", jwt_secret="test-secret-key")
        provider = JWTAuth(config)
        provider.create_user("refresh@example.com", "password")
        login_result = provider.authenticate("refresh@example.com", "password")
        old_refresh = login_result.token_pair.refresh_token

        result = provider.refresh_token(old_refresh)
        assert result.status.value == "success"
        assert result.token_pair is not None

    def test_refresh_token_invalid(self):
        from services.auth.providers.jwt import JWTAuth
        from services.auth.config import AuthConfig

        config = AuthConfig(provider="jwt", jwt_secret="test-secret-key")
        provider = JWTAuth(config)
        result = provider.refresh_token("invalid-refresh-token")
        assert result.status.value == "invalid"

    def test_revoke_token(self):
        from services.auth.providers.jwt import JWTAuth
        from services.auth.config import AuthConfig

        config = AuthConfig(provider="jwt", jwt_secret="test-secret-key")
        provider = JWTAuth(config)
        provider.create_user("revoke@example.com", "password")
        login_result = provider.authenticate("revoke@example.com", "password")
        refresh = login_result.token_pair.refresh_token

        provider.revoke_token(refresh)
        result = provider.refresh_token(refresh)
        assert result.status.value == "invalid"

    def test_jwt_token_has_correct_structure(self):
        from services.auth.providers.jwt import JWTAuth
        from services.auth.config import AuthConfig

        config = AuthConfig(provider="jwt", jwt_secret="test-secret-key")
        provider = JWTAuth(config)
        provider.create_user("struct@example.com", "password")
        result = provider.authenticate("struct@example.com", "password")

        access = result.token_pair.access_token
        parts = access.split(".")
        assert len(parts) == 3

    def test_reset(self):
        from services.auth.providers.jwt import JWTAuth
        from services.auth.config import AuthConfig

        config = AuthConfig(provider="jwt", jwt_secret="test-secret-key")
        provider = JWTAuth(config)
        provider.create_user("reset@example.com", "password")
        assert len(provider._users) == 1
        provider.reset()
        assert len(provider._users) == 0
        assert len(provider._refresh_tokens) == 0


# --- Provider registry tests ---


class TestProviderRegistry:
    def test_register_and_create(self):
        from services.auth.providers.registry import ProviderRegistry
        from services.auth.providers.mock import MockAuth
        from services.auth.config import AuthConfig

        ProviderRegistry.register("test_provider", MockAuth)
        provider = ProviderRegistry.create("test_provider", AuthConfig())
        assert isinstance(provider, MockAuth)

    def test_unknown_provider_raises(self):
        from services.auth.providers.registry import ProviderRegistry
        from services.auth.config import AuthConfig

        with pytest.raises(ValueError, match="Unknown auth provider"):
            ProviderRegistry.create("nonexistent", AuthConfig())

    def test_available_includes_registered(self):
        from services.auth.providers.registry import ProviderRegistry

        available = ProviderRegistry.available()
        assert "mock" in available
        assert "jwt" in available

    def test_get_returns_none_for_unknown(self):
        from services.auth.providers.registry import ProviderRegistry

        assert ProviderRegistry.get("nonexistent") is None

    def test_get_returns_class(self):
        from services.auth.providers.registry import ProviderRegistry
        from services.auth.providers.mock import MockAuth

        cls = ProviderRegistry.get("mock")
        assert cls is MockAuth


# --- Auth service tests ---


class TestAuthService:
    def test_register_success(self):
        from services.auth.service import AuthService

        svc = AuthService()
        result = svc.register("newuser@example.com", "SecurePass123!")
        assert result.status.value == "success"
        assert result.user.email == "newuser@example.com"
        assert result.user.id

    def test_register_duplicate(self):
        from services.auth.service import AuthService

        svc = AuthService()
        svc.register("dup@example.com", "SecurePass123!")
        result = svc.register("dup@example.com", "SecurePass123!")
        assert result.status.value == "failed"

    def test_register_invalid_email(self):
        from services.auth.service import AuthService

        svc = AuthService()
        with pytest.raises(Exception, match="Invalid email"):
            svc.register("not-an-email", "SecurePass123!")

    def test_register_short_password(self):
        from services.auth.service import AuthService

        svc = AuthService()
        with pytest.raises(Exception, match="at least 8"):
            svc.register("user@example.com", "short")

    def test_login_success(self):
        from services.auth.service import AuthService

        svc = AuthService()
        svc.register("login-test@example.com", "SecurePass123!")
        result = svc.login("login-test@example.com", "SecurePass123!")
        assert result.status.value == "success"
        assert result.token_pair is not None
        assert result.token_pair.access_token
        assert result.token_pair.refresh_token

    def test_login_wrong_password(self):
        from services.auth.service import AuthService

        svc = AuthService()
        svc.register("loginfail@example.com", "SecurePass123!")
        result = svc.login("loginfail@example.com", "wrongpassword")
        assert result.status.value == "failed"

    def test_login_nonexistent_user(self):
        from services.auth.service import AuthService

        svc = AuthService()
        result = svc.login("nobody@example.com", "password")
        assert result.status.value == "failed"

    def test_verify_valid_token(self):
        from services.auth.service import AuthService

        svc = AuthService()
        svc.register("verify-me@example.com", "SecurePass123!")
        login_result = svc.login("verify-me@example.com", "SecurePass123!")
        token = login_result.token_pair.access_token

        result = svc.verify(token)
        assert result.status.value == "success"
        assert result.user.email == "verify-me@example.com"

    def test_verify_invalid_token(self):
        from services.auth.service import AuthService

        svc = AuthService()
        result = svc.verify("invalid-token")
        assert result.status.value == "invalid"

    def test_refresh_success(self):
        from services.auth.service import AuthService

        svc = AuthService()
        svc.register("refresh-svc@example.com", "SecurePass123!")
        login_result = svc.login("refresh-svc@example.com", "SecurePass123!")
        old_refresh = login_result.token_pair.refresh_token

        result = svc.refresh(old_refresh)
        assert result.status.value == "success"
        assert result.token_pair.access_token
        assert result.token_pair.refresh_token != old_refresh

    def test_refresh_invalid_token(self):
        from services.auth.service import AuthService

        svc = AuthService()
        result = svc.refresh("invalid-refresh-token")
        assert result.status.value == "invalid"

    def test_logout(self):
        from services.auth.service import AuthService

        svc = AuthService()
        svc.register("logout@example.com", "SecurePass123!")
        login_result = svc.login("logout@example.com", "SecurePass123!")
        refresh = login_result.token_pair.refresh_token

        svc.logout(refresh)
        result = svc.refresh(refresh)
        assert result.status.value == "invalid"

    def test_health(self):
        from services.auth.service import AuthService

        svc = AuthService()
        health = svc.health()
        assert health.provider == "mock"
        assert health.config_valid is True
        assert health.config_errors == []

    def test_metrics_recorded_on_success(self):
        from services.auth.service import AuthService

        svc = AuthService()
        svc.register("metrics@example.com", "SecurePass123!")
        svc.login("metrics@example.com", "SecurePass123!")
        assert svc.metrics.registrations == 1
        assert svc.metrics.logins == 1

    def test_metrics_recorded_on_failure(self):
        from services.auth.service import AuthService

        svc = AuthService()
        svc.login("noone@example.com", "wrongpass")
        assert svc.metrics.failures == 1

    def test_service_works_with_jwt_provider(self):
        from services.auth.service import AuthService
        from services.auth.config import AuthConfig
        from services.auth.providers.jwt import JWTAuth

        config = AuthConfig(provider="jwt", jwt_secret="test-service-secret")
        provider = JWTAuth(config)
        svc = AuthService(config=config, provider=provider)

        reg = svc.register("jwt-svc@example.com", "SecurePass123!")
        assert reg.status.value == "success"

        login = svc.login("jwt-svc@example.com", "SecurePass123!")
        assert login.status.value == "success"

        verify = svc.verify(login.token_pair.access_token)
        assert verify.status.value == "success"

        refresh = svc.refresh(login.token_pair.refresh_token)
        assert refresh.status.value == "success"

    def test_service_validation_empty_email(self):
        from services.auth.service import AuthService

        svc = AuthService()
        with pytest.raises(Exception):
            svc.register("", "SecurePass123!")

    def test_service_validation_empty_password(self):
        from services.auth.service import AuthService

        svc = AuthService()
        with pytest.raises(Exception):
            svc.register("user@example.com", "")
