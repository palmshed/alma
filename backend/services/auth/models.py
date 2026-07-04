from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class AuthStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    EXPIRED = "expired"
    INVALID = "invalid"
    LOCKED = "locked"


@dataclass
class User:
    id: str
    email: str
    display_name: str = ""
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    expires_at: datetime
    token_type: str = "Bearer"


@dataclass
class AuthResult:
    status: AuthStatus
    user: Optional[User] = None
    token_pair: Optional[TokenPair] = None
    error: Optional[str] = None
    provider: str = ""


@dataclass
class AuthHealthStatus:
    provider: str
    config_valid: bool
    config_errors: list[str] = field(default_factory=list)
