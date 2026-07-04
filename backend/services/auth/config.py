import os
from dataclasses import dataclass


@dataclass
class AuthConfig:
    provider: str = "mock"
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    @staticmethod
    def from_env() -> "AuthConfig":
        return AuthConfig(
            provider=os.getenv("AUTH_PROVIDER", "mock").lower(),
            jwt_secret=os.getenv("JWT_SECRET", ""),
            jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            access_token_expire_minutes=int(
                os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
            ),
            refresh_token_expire_days=int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")),
        )

    def is_valid(self) -> tuple[bool, list[str]]:
        errors: list[str] = []
        if self.provider not in ("mock", "jwt"):
            errors.append(f"Unknown auth provider: {self.provider}")
        if self.provider == "jwt" and not self.jwt_secret:
            errors.append("JWT_SECRET is required for JWT provider")
        if self.access_token_expire_minutes < 1:
            errors.append("access_token_expire_minutes must be >= 1")
        if self.refresh_token_expire_days < 1:
            errors.append("refresh_token_expire_days must be >= 1")
        return (len(errors) == 0, errors)
