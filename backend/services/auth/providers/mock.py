import hashlib
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from ..config import AuthConfig
from ..models import AuthResult, AuthStatus, TokenPair, User
from .base import AuthProvider

logger = logging.getLogger("palmshed.auth.mock")


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


class MockAuth(AuthProvider):
    def __init__(self, config: Optional[AuthConfig] = None) -> None:
        self._users: dict[str, dict] = {}
        self._refresh_tokens: dict[str, dict] = {}

    def create_user(self, email: str, password: str, **kwargs) -> AuthResult:
        if email in self._users:
            return AuthResult(
                status=AuthStatus.FAILED,
                error=f"User already exists: {email}",
                provider="mock",
            )
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            display_name=kwargs.get("display_name", ""),
        )
        self._users[email] = {
            "user": user,
            "password_hash": _hash_password(password),
        }
        logger.info("Mock user created: %s", email)
        return AuthResult(status=AuthStatus.SUCCESS, user=user, provider="mock")

    def authenticate(self, email: str, password: str) -> AuthResult:
        record = self._users.get(email)
        if not record:
            return AuthResult(
                status=AuthStatus.FAILED,
                error="Invalid email or password",
                provider="mock",
            )
        if record["password_hash"] != _hash_password(password):
            return AuthResult(
                status=AuthStatus.FAILED,
                error="Invalid email or password",
                provider="mock",
            )
        user = record["user"]
        if not user.is_active:
            return AuthResult(
                status=AuthStatus.LOCKED,
                error="Account is locked",
                provider="mock",
            )
        access_token = str(uuid.uuid4())
        refresh_token = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        self._refresh_tokens[refresh_token] = {
            "user_id": user.id,
            "access_token": access_token,
            "expires_at": expires_at,
        }
        token_pair = TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
        )
        logger.info("Mock login: %s", email)
        return AuthResult(
            status=AuthStatus.SUCCESS,
            user=user,
            token_pair=token_pair,
            provider="mock",
        )

    def verify_token(self, token: str) -> AuthResult:
        for rt, session in self._refresh_tokens.items():
            if session["access_token"] == token:
                if datetime.now(timezone.utc) > session["expires_at"]:
                    return AuthResult(
                        status=AuthStatus.EXPIRED,
                        error="Token expired",
                        provider="mock",
                    )
                email = self._find_email_by_user_id(session["user_id"])
                if not email:
                    return AuthResult(
                        status=AuthStatus.INVALID,
                        error="User not found",
                        provider="mock",
                    )
                return AuthResult(
                    status=AuthStatus.SUCCESS,
                    user=self._users[email]["user"],
                    provider="mock",
                )
        return AuthResult(
            status=AuthStatus.INVALID,
            error="Invalid token",
            provider="mock",
        )

    def refresh_token(self, refresh_token: str) -> AuthResult:
        session = self._refresh_tokens.get(refresh_token)
        if not session:
            return AuthResult(
                status=AuthStatus.INVALID,
                error="Invalid refresh token",
                provider="mock",
            )
        email = self._find_email_by_user_id(session["user_id"])
        if not email:
            return AuthResult(
                status=AuthStatus.INVALID,
                error="User not found",
                provider="mock",
            )
        new_access_token = str(uuid.uuid4())
        new_refresh_token = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        del self._refresh_tokens[refresh_token]
        self._refresh_tokens[new_refresh_token] = {
            "user_id": session["user_id"],
            "access_token": new_access_token,
            "expires_at": expires_at,
        }
        return AuthResult(
            status=AuthStatus.SUCCESS,
            user=self._users[email]["user"],
            token_pair=TokenPair(
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                expires_at=expires_at,
            ),
            provider="mock",
        )

    def revoke_token(self, refresh_token: str) -> None:
        self._refresh_tokens.pop(refresh_token, None)

    def _find_email_by_user_id(self, user_id: str) -> Optional[str]:
        for email, record in self._users.items():
            if record["user"].id == user_id:
                return email
        return None

    def reset(self) -> None:
        self._users.clear()
        self._refresh_tokens.clear()
