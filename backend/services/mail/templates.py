import os
import re
from enum import Enum
from functools import cache
from string import Template

from .models import MailPriority


class MailTemplate(str, Enum):
    WELCOME = "welcome"
    VERIFICATION = "verification"
    PASSWORD_RESET = "password_reset"
    NOTIFICATION = "notification"


class TemplateNotFound(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Mail template not found: {name}")


class TemplateValidationError(Exception):
    pass


class TemplateDefinition:
    def __init__(
        self,
        name: str,
        subject: str,
        product: str = "Alma",
        priority: MailPriority = MailPriority.NORMAL,
        required_placeholders: frozenset[str] = frozenset(),
        version: str = "1.0",
        deprecated: bool = False,
        description: str = "",
    ) -> None:
        self.name = name
        self.subject = subject
        self.product = product
        self.priority = priority
        self.required_placeholders = required_placeholders
        self.version = version
        self.deprecated = deprecated
        self.description = description

    def format_subject(self, context: dict) -> str:
        return Template(self.subject).safe_substitute(context)


_TEMPLATE_METADATA: dict[MailTemplate, TemplateDefinition] = {
    MailTemplate.WELCOME: TemplateDefinition(
        name="welcome",
        subject="Welcome to ${product}",
        required_placeholders=frozenset({"name", "product", "link"}),
        description="Sent after a new user signs up.",
    ),
    MailTemplate.VERIFICATION: TemplateDefinition(
        name="verification",
        subject="Verify your email",
        required_placeholders=frozenset({"name", "product", "code", "link", "expires_in"}),
        description="Email verification with a code and link.",
    ),
    MailTemplate.PASSWORD_RESET: TemplateDefinition(
        name="password_reset",
        subject="Reset your password",
        required_placeholders=frozenset({"name", "product", "link", "expires_in"}),
        description="Password reset with expiring link.",
    ),
    MailTemplate.NOTIFICATION: TemplateDefinition(
        name="notification",
        subject="${subject}",
        required_placeholders=frozenset({"subject", "body", "product"}),
        description="General-purpose notification.",
    ),
}


def _extract_placeholders(text: str) -> set[str]:
    return set(re.findall(r"\$\{(\w+)\}", text))


class MailTemplates:
    def __init__(self, directory: str = "") -> None:
        self.directory = directory or os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "templates", "mail"
        )
        self._validate()

    def _validate(self) -> list[str]:
        errors: list[str] = []
        for template in MailTemplate:
            name = template.value
            html_path = os.path.join(self.directory, f"{name}.html")
            txt_path = os.path.join(self.directory, f"{name}.txt")

            if not os.path.exists(html_path):
                errors.append(f"Missing HTML template: {html_path}")
                continue
            if not os.path.exists(txt_path):
                errors.append(f"Missing text template: {txt_path}")
                continue

            meta = template_metadata(template)
            if not meta:
                continue

            with open(html_path) as f:
                html_placeholders = _extract_placeholders(f.read())
            with open(txt_path) as f:
                txt_placeholders = _extract_placeholders(f.read())

            subject_placeholders = _extract_placeholders(meta.subject)
            all_file_placeholders = html_placeholders | txt_placeholders | subject_placeholders
            missing = meta.required_placeholders - all_file_placeholders
            if missing:
                errors.append(
                    f"Template '{name}' missing placeholders: {', '.join(sorted(missing))}"
                )

        if errors:
            raise TemplateValidationError("; ".join(errors))
        return errors

    @cache
    def _load(self, name: str) -> Template:
        path = os.path.join(self.directory, name)
        try:
            with open(path) as f:
                return Template(f.read())
        except FileNotFoundError:
            raise TemplateNotFound(name)

    def render(self, template: str, context: dict) -> dict[str, str]:
        html = self._load(f"{template}.html").safe_substitute(context)
        text = self._load(f"{template}.txt").safe_substitute(context)
        return {"html_body": html, "text_body": text}

    def validate(self) -> list[str]:
        try:
            return self._validate()
        except TemplateValidationError as exc:
            return [str(exc)]


def template_metadata(template: MailTemplate) -> TemplateDefinition | None:
    return _TEMPLATE_METADATA.get(template)


def registered_templates() -> list[MailTemplate]:
    return list(MailTemplate)
