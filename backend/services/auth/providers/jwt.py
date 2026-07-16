# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
import base64
import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from ..config import AuthConfig
from ..models import AuthResult, AuthStatus, TokenPair, User
from .base import AuthProvider

logger = logging.getLogger("palmshed.auth.jwt")


def _hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    if salt is None:
        salt = uuid.uuid4().hex[:16]
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return hashlib.sha256(salt.encode() + hashed).hexdigest(), salt


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _base64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def _create_jwt(payload: dict, secret: str, algorithm: str = "HS256") -> str:
    header = {"alg": algorithm, "typ": "JWT"}
    header_b64 = _base64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}"
    if algorithm == "HS256":
        sig = hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    elif algorithm == "HS384":
        sig = hmac.new(secret.encode(), signing_input.encode(), hashlib.sha384).digest()
    elif algorithm == "HS512":
        sig = hmac.new(secret.encode(), signing_input.encode(), hashlib.sha512).digest()
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")
    return f"{signing_input}.{_base64url_encode(sig)}"


def _verify_jwt(token: str, secret: str, algorithm: str = "HS256") -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}"
        if algorithm == "HS256":
            expected = hmac.new(
                secret.encode(), signing_input.encode(), hashlib.sha256
            ).digest()
        elif algorithm == "HS384":
            expected = hmac.new(
                secret.encode(), signing_input.encode(), hashlib.sha384
            ).digest()
        elif algorithm == "HS512":
            expected = hmac.new(
                secret.encode(), signing_input.encode(), hashlib.sha512
            ).digest()
        else:
            return None
        actual = _base64url_decode(sig_b64)
        if not hmac.compare_digest(expected, actual):
            return None
        payload = json.loads(_base64url_decode(payload_b64))
        return payload
    except Exception:
        return None


class JWTAuth(AuthProvider):
    def __init__(self, config: AuthConfig) -> None:
        self._secret = config.jwt_secret
        self._algorithm = config.jwt_algorithm
        self._access_ttl = config.access_token_expire_minutes
        self._refresh_ttl = config.refresh_token_expire_days
        self._users: dict[str, dict] = {}
        self._refresh_tokens: set[str] = set()

    def create_user(self, email: str, password: str, **kwargs) -> AuthResult:
        if email in self._users:
            return AuthResult(
                status=AuthStatus.FAILED,
                error=f"User already exists: {email}",
                provider="jwt",
            )
        password_hash, salt = _hash_password(password)
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            display_name=kwargs.get("display_name", ""),
        )
        self._users[email] = {
            "user": user,
            "password_hash": password_hash,
            "salt": salt,
        }
        logger.info("JWT user created: %s", email)
        return AuthResult(status=AuthStatus.SUCCESS, user=user, provider="jwt")

    def authenticate(self, email: str, password: str) -> AuthResult:
        record = self._users.get(email)
        if not record:
            return AuthResult(
                status=AuthStatus.FAILED,
                error="Invalid email or password",
                provider="jwt",
            )
        password_hash, _ = _hash_password(password, record["salt"])
        if record["password_hash"] != password_hash:
            return AuthResult(
                status=AuthStatus.FAILED,
                error="Invalid email or password",
                provider="jwt",
            )
        user = record["user"]
        if not user.is_active:
            return AuthResult(
                status=AuthStatus.LOCKED,
                error="Account is locked",
                provider="jwt",
            )
        now = datetime.now(timezone.utc)
        access_payload = {
            "sub": user.id,
            "email": user.email,
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=self._access_ttl)).timestamp()),
        }
        refresh_payload = {
            "sub": user.id,
            "email": user.email,
            "type": "refresh",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(days=self._refresh_ttl)).timestamp()),
        }
        access_token = _create_jwt(access_payload, self._secret, self._algorithm)
        refresh_token = _create_jwt(refresh_payload, self._secret, self._algorithm)
        self._refresh_tokens.add(refresh_token)
        expires_at = now + timedelta(minutes=self._access_ttl)
        logger.info("JWT login: %s", email)
        return AuthResult(
            status=AuthStatus.SUCCESS,
            user=user,
            token_pair=TokenPair(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
            ),
            provider="jwt",
        )

    def verify_token(self, token: str) -> AuthResult:
        payload = _verify_jwt(token, self._secret, self._algorithm)
        if payload is None:
            return AuthResult(
                status=AuthStatus.INVALID,
                error="Invalid token signature",
                provider="jwt",
            )
        exp = payload.get("exp", 0)
        now = datetime.now(timezone.utc).timestamp()
        if now > exp:
            return AuthResult(
                status=AuthStatus.EXPIRED,
                error="Token expired",
                provider="jwt",
            )
        email = payload.get("email", "")
        record = self._users.get(email)
        if not record:
            return AuthResult(
                status=AuthStatus.INVALID,
                error="User not found",
                provider="jwt",
            )
        return AuthResult(
            status=AuthStatus.SUCCESS,
            user=record["user"],
            provider="jwt",
        )

    def refresh_token(self, refresh_token_val: str) -> AuthResult:
        if refresh_token_val not in self._refresh_tokens:
            return AuthResult(
                status=AuthStatus.INVALID,
                error="Invalid refresh token",
                provider="jwt",
            )
        payload = _verify_jwt(refresh_token_val, self._secret, self._algorithm)
        if payload is None:
            self._refresh_tokens.discard(refresh_token_val)
            return AuthResult(
                status=AuthStatus.INVALID,
                error="Invalid refresh token signature",
                provider="jwt",
            )
        exp = payload.get("exp", 0)
        now = datetime.now(timezone.utc).timestamp()
        if now > exp:
            self._refresh_tokens.discard(refresh_token_val)
            return AuthResult(
                status=AuthStatus.EXPIRED,
                error="Refresh token expired",
                provider="jwt",
            )
        email = payload.get("email", "")
        record = self._users.get(email)
        if not record:
            return AuthResult(
                status=AuthStatus.INVALID,
                error="User not found",
                provider="jwt",
            )
        user = record["user"]
        new_now = datetime.now(timezone.utc)
        access_payload = {
            "sub": user.id,
            "email": user.email,
            "type": "access",
            "iat": int(new_now.timestamp()),
            "exp": int((new_now + timedelta(minutes=self._access_ttl)).timestamp()),
        }
        new_refresh_payload = {
            "sub": user.id,
            "email": user.email,
            "type": "refresh",
            "iat": int(new_now.timestamp()),
            "exp": int((new_now + timedelta(days=self._refresh_ttl)).timestamp()),
        }
        new_access = _create_jwt(access_payload, self._secret, self._algorithm)
        new_refresh = _create_jwt(new_refresh_payload, self._secret, self._algorithm)
        self._refresh_tokens.discard(refresh_token_val)
        self._refresh_tokens.add(new_refresh)
        expires_at = new_now + timedelta(minutes=self._access_ttl)
        return AuthResult(
            status=AuthStatus.SUCCESS,
            user=user,
            token_pair=TokenPair(
                access_token=new_access,
                refresh_token=new_refresh,
                expires_at=expires_at,
            ),
            provider="jwt",
        )

    def revoke_token(self, refresh_token_val: str) -> None:
        self._refresh_tokens.discard(refresh_token_val)

    def reset(self) -> None:
        self._users.clear()
        self._refresh_tokens.clear()
