# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
import argparse
import sys
import uuid

from .config import AuthConfig
from .service import AuthService


def verify(args: argparse.Namespace) -> int:
    config = AuthConfig.from_env()
    provider = config.provider

    valid, errors = config.is_valid()
    if not valid:
        for e in errors:
            print(f"CONFIG ERROR: {e}")
        return 1

    print(f"Provider:     {provider}")
    print()

    if provider == "mock":
        print("WARNING: AUTH_PROVIDER=mock — no real authentication.")
        print("Set AUTH_PROVIDER=jwt and JWT_SECRET to test real JWT tokens.")
        print()

    try:
        svc = AuthService(config=config)
    except Exception as exc:
        print(f"ERROR: Failed to initialize AuthService: {exc}")
        return 1

    email = args.email or f"test-{uuid.uuid4().hex[:8]}@example.com"
    password = args.password or "TestPassword123!"

    print("=== Register ===")
    result = svc.register(email=email, password=password)
    if result.status.value != "success":
        print(f"FAILED: {result.error}")
        return 1
    print(f"User ID:  {result.user.id}")
    print(f"Email:    {result.user.email}")
    print()

    print("=== Login ===")
    result = svc.login(email=email, password=password)
    if result.status.value != "success":
        print(f"FAILED: {result.error}")
        return 1
    print(f"Access:   {result.token_pair.access_token[:40]}...")
    print(f"Refresh:  {result.token_pair.refresh_token[:40]}...")
    print(f"Expires:  {result.token_pair.expires_at}")
    access_token = result.token_pair.access_token
    refresh_token = result.token_pair.refresh_token
    print()

    print("=== Verify Access Token ===")
    result = svc.verify(token=access_token)
    if result.status.value != "success":
        print(f"FAILED: {result.error}")
        return 1
    print(f"User:     {result.user.email}")
    print()

    print("=== Refresh Tokens ===")
    result = svc.refresh(refresh_token=refresh_token)
    if result.status.value != "success":
        print(f"FAILED: {result.error}")
        return 1
    print(f"New Access:   {result.token_pair.access_token[:40]}...")
    print(f"New Refresh:  {result.token_pair.refresh_token[:40]}...")
    print()

    print("=== Logout ===")
    svc.logout(refresh_token=result.token_pair.refresh_token)
    print("OK")
    print()

    print("=== Health ===")
    health = svc.health()
    print(f"Provider:     {health.provider}")
    print(f"Config valid: {health.config_valid}")
    print()

    print("All auth checks passed.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify auth service end-to-end",
    )
    parser.add_argument("--email", help="Email to use for verification")
    parser.add_argument("--password", help="Password to use for verification")

    args = parser.parse_args()

    sys.exit(verify(args))


if __name__ == "__main__":
    main()
