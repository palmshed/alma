import logging
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from ..config import MailConfig
from ..models import MailMessage, MailResult, MailStatus, ProviderCapabilities
from .base import MailProvider

logger = logging.getLogger("palmshed.mail.smtp")


class SMTPProvider(MailProvider):
    def __init__(self, config: MailConfig) -> None:
        self.host = config.smtp_host
        self.port = config.smtp_port
        self.username = config.smtp_username
        self.password = config.smtp_password
        self.use_tls = config.smtp_tls
        self.timeout = config.timeout
        self._capabilities = ProviderCapabilities(
            html=True,
            attachments=True,
            inline_images=False,
            scheduling=False,
        )

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def send(self, message: MailMessage) -> MailResult:
        msg = MIMEMultipart("alternative")
        msg["From"] = message.sender.formatted()
        msg["To"] = message.recipient.formatted()
        msg["Subject"] = message.subject_override or ""

        if message.cc:
            msg["Cc"] = ", ".join(a.formatted() for a in message.cc)

        msg.attach(MIMEText(message.context.get("text_body", ""), "plain"))
        msg.attach(MIMEText(message.context.get("html_body", ""), "html"))

        recipients = [message.recipient.email]
        recipients.extend(a.email for a in message.cc)
        recipients.extend(a.email for a in message.bcc)

        try:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as server:
                if self.use_tls:
                    server.starttls()
                if self.username:
                    server.login(self.username, self.password)
                server.sendmail(message.sender.email, recipients, msg.as_string())
        except Exception as exc:
            logger.exception("SMTP send failed")
            return MailResult(
                mail_id=message.id or "",
                status=MailStatus.FAILED,
                provider="smtp",
                timestamp=datetime.now(timezone.utc),
                retry_count=message.retry_count,
                error=str(exc),
            )

        return MailResult(
            mail_id=message.id or "",
            status=MailStatus.SENT,
            provider="smtp",
            timestamp=datetime.now(timezone.utc),
            retry_count=message.retry_count,
        )
