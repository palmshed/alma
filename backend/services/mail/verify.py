import argparse
import sys

from .config import MailConfig
from .templates import MailTemplate
from .service import MailService, MailError


def verify(args: argparse.Namespace) -> int:
    config = MailConfig.from_env()
    provider = config.provider
    template_name = args.template.upper()

    try:
        template = MailTemplate[template_name]
    except KeyError:
        print(f"Unknown template: {template_name}")
        print(f"Available: {', '.join(t.name for t in MailTemplate)}")
        return 1

    valid, errors = config.is_valid()
    if not valid:
        for e in errors:
            print(f"CONFIG ERROR: {e}")
        return 1

    print(f"Provider:     {provider}")
    print(f"From:         {config.from_name} <{config.from_email}>")
    print(f"To:           {args.to}")
    print(f"Template:     {template_name}")
    print(f"Sync mode:    {config.sync}")
    print()

    if provider == "mock":
        print("WARNING: MAIL_PROVIDER=mock — no real email will be sent.")
        print("Set MAIL_PROVIDER=resend and RESEND_API_KEY to test real delivery.")
        print()
        print("Simulating send anyway...")
    elif provider == "resend" and not config.resend_api_key:
        print("ERROR: RESEND_API_KEY is not set.")
        print("Set it in the environment or .env file before verifying.")
        return 1

    try:
        svc = MailService(config=config)
    except Exception as exc:
        print(f"ERROR: Failed to initialize MailService: {exc}")
        return 1

    context = {}
    if args.context:
        for pair in args.context:
            if "=" not in pair:
                print(
                    f"WARNING: ignoring malformed context '{pair}' (expected key=value)"
                )
                continue
            key, value = pair.split("=", 1)
            context[key] = value

    if "name" not in context:
        context["name"] = "Test User"
    if "product" not in context:
        context["product"] = "Alma"
    if "link" not in context:
        context["link"] = "https://palmshed.vercel.app"

    print("Sending...")
    try:
        message = svc.send(
            template=template,
            recipient=args.to,
            context=context,
        )
    except MailError as exc:
        print()
        print(f"FAILED: {exc}")
        return 1
    except Exception as exc:
        print()
        print(f"UNEXPECTED ERROR: {exc}")
        return 1

    print()
    print("--- RESULT ---")
    print(f"Message ID:       {message.id}")
    print(f"Status:           {message.status.value}")
    print(f"Provider:         {provider}")

    if provider == "mock":
        print()
        print("Mock capture (no real send occurred).")
        print("To test real delivery, set:")
        print("  MAIL_PROVIDER=resend")
        print("  RESEND_API_KEY=<your key>")

    if message.status.value == "sent":
        print()
        print("Delivery request succeeded.")
        return 0
    else:
        print()
        print("Delivery request failed.")
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify mail delivery end-to-end",
    )
    parser.add_argument(
        "--to",
        help="Recipient email",
    )
    parser.add_argument(
        "--template",
        default="WELCOME",
        choices=[t.name for t in MailTemplate],
        help="Template to send (default: WELCOME)",
    )
    parser.add_argument(
        "--context",
        action="append",
        help="Context variables as key=value (repeatable)",
    )

    args = parser.parse_args()

    if not args.to:
        parser.print_help()
        print()
        print("ERROR: --to is required (or set MAIL_VERIFY_TO)")
        sys.exit(1)

    sys.exit(verify(args))


if __name__ == "__main__":
    main()
