import argparse
import sys
import uuid

from .config import NotificationConfig
from .service import NotificationService


def verify(args: argparse.Namespace) -> int:
    config = NotificationConfig.from_env()
    default_channel = config.default_channel

    valid, errors = config.is_valid()
    if not valid:
        for e in errors:
            print(f"CONFIG ERROR: {e}")
        return 1

    print(f"Default channel: {default_channel}")
    print(f"Enabled:         {config.enabled}")
    print()

    if default_channel == "mock":
        print("WARNING: NOTIFICATIONS_DEFAULT_CHANNEL=mock — no real notification.")
        print()

    try:
        svc = NotificationService(config=config)
    except Exception as exc:
        print(f"ERROR: Failed to initialize NotificationService: {exc}")
        return 1

    test_id = uuid.uuid4().hex[:8]
    recipient = args.to or f"test-{test_id}@example.com"
    subject = args.subject or f"Test Notification {test_id}"
    channel = args.channel or ""

    print("=== Send Notification ===")
    try:
        result = svc.send(
            recipient=recipient,
            subject=subject,
            body=f"This is a test notification sent at {test_id}.",
            channel=channel,
        )
    except Exception as exc:
        print(f"FAILED: {exc}")
        return 1

    print(f"Notification ID: {result.notification_id}")
    print(f"Channel:         {result.channel}")
    print(f"Status:          {result.status.value}")
    if result.provider_message_id:
        print(f"Provider ID:     {result.provider_message_id}")
    if result.error:
        print(f"Error:           {result.error}")
    print()

    print("=== Health ===")
    health = svc.health()
    for name, status in health.channels.items():
        print(f"  {name}: {status}")

    if result.status.value == "failed":
        print()
        print("Notification delivery failed.")
        return 1

    print()
    print("All notification checks passed.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify notification delivery",
    )
    parser.add_argument("--to", help="Recipient")
    parser.add_argument("--subject", help="Notification subject")
    parser.add_argument("--channel", help="Channel to use (mock, email, webhook)")

    args = parser.parse_args()

    sys.exit(verify(args))


if __name__ == "__main__":
    main()
