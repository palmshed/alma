import json
import time
import uuid
from typing import Optional

from .config import MailConfig
from .logging import MailLogger
from .metrics import MailMetrics
from .models import (
    Address,
    Attachment,
    HealthStatus,
    MailMessage,
    MailResult,
    MailStatus,
)
from .providers import MailProvider, get_provider
from .queue import MailQueue, get_queue
from .templates import (
    MailTemplate,
    MailTemplates,
    registered_templates,
    template_metadata,
)


class MailError(Exception):
    pass


class MailValidationError(MailError):
    pass


class MailService:
    def __init__(
        self,
        config: Optional[MailConfig] = None,
        provider: Optional[MailProvider] = None,
        templates: Optional[MailTemplates] = None,
        queue: Optional[MailQueue] = None,
        logger: Optional[MailLogger] = None,
        metrics: Optional[MailMetrics] = None,
    ) -> None:
        self.config = config or MailConfig.from_env()
        self.provider = provider or get_provider(self.config)
        self.templates = templates or MailTemplates()
        self.queue = queue or get_queue(self.config, worker=self._send)
        self.logger = logger or MailLogger()
        self.metrics = metrics or MailMetrics()

    def send(
        self,
        template: MailTemplate,
        recipient: str,
        context: Optional[dict] = None,
        subject: Optional[str] = None,
        sender: Optional[Address] = None,
        cc: Optional[list[str]] = None,
        bcc: Optional[list[str]] = None,
        attachments: Optional[list[Attachment]] = None,
    ) -> MailMessage:
        ctx = context or {}
        rendered = self.templates.render(template.value, ctx)
        merged = {**ctx, **rendered}

        if not subject:
            meta = template_metadata(template)
            if meta:
                subject = meta.format_subject(ctx)

        cc_list = [Address(a) for a in (cc or [])]
        bcc_list = [Address(a) for a in (bcc or [])]
        attachment_list = attachments or []

        self._validate_recipients(cc_list, bcc_list)
        self._validate_context(ctx)
        self._validate_attachments(attachment_list)

        message = MailMessage(
            id=str(uuid.uuid4()),
            template=template.value,
            recipient=Address(recipient),
            context=merged,
            subject_override=subject,
            reply_to=self.config.reply_to or None,
            sender=sender
            or Address(
                email=self.config.from_email,
                name=self.config.from_name,
            ),
            cc=cc_list,
            bcc=bcc_list,
            attachments=attachment_list,
        )

        self.metrics.record_queued()

        if self.config.sync:
            self._send(message)
        else:
            self.queue.enqueue(message)
            self.queue.start()

        return message

    def health(self) -> HealthStatus:
        config_valid, config_errors = self.config.is_valid()
        try:
            self.templates.validate()
            templates_valid = True
        except Exception:
            templates_valid = False

        return HealthStatus(
            provider=type(self.provider).__name__,
            provider_capabilities=self.provider.capabilities,
            queue_running=self.queue.running,
            queue_depth=self.queue.depth,
            config_valid=config_valid,
            config_errors=config_errors,
            templates_valid=templates_valid,
            template_count=len(registered_templates()),
        )

    def shutdown(self, timeout: float = 5.0) -> None:
        self.queue.drain(timeout)

    def _validate_recipients(self, cc: list[Address], bcc: list[Address]) -> None:
        total = 1 + len(cc) + len(bcc)
        if total > self.config.max_recipients:
            raise MailValidationError(
                f"Too many recipients ({total}); max is {self.config.max_recipients}"
            )

    def _validate_context(self, context: dict) -> None:
        size = len(json.dumps(context))
        if size > self.config.max_context_size_bytes:
            raise MailValidationError(
                f"Context too large ({size} bytes); max is {self.config.max_context_size_bytes}"
            )

    def _validate_attachments(self, attachments: list[Attachment]) -> None:
        caps = self.provider.capabilities
        if attachments and not caps.attachments:
            raise MailValidationError("Provider does not support attachments")

        max_bytes = self.config.max_attachment_size_bytes
        for att in attachments:
            if len(att.content) > max_bytes:
                raise MailValidationError(
                    f"Attachment '{att.filename}' too large "
                    f"({len(att.content)} bytes); max is {max_bytes}"
                )

    def _send(self, message: MailMessage) -> MailResult:
        start = time.monotonic()
        try:
            result = self.provider.send(message)
            elapsed = time.monotonic() - start
            message.status = result.status
            self.metrics.record_duration(elapsed)
            self.logger.log_result(result)
            if result.status == MailStatus.FAILED:
                self.metrics.record_failed()
                raise MailError(result.error or "send failed")
            self.metrics.record_sent()
            return result
        except MailError:
            raise
        except Exception as exc:
            elapsed = time.monotonic() - start
            self.metrics.record_duration(elapsed)
            self.metrics.record_failed()
            message.status = MailStatus.FAILED
            self.logger.log_send(
                mail_id=message.id or "",
                provider=type(self.provider).__name__,
                status=MailStatus.FAILED,
                retry_count=message.retry_count,
                error=str(exc),
            )
            raise MailError(str(exc)) from exc
