import logging
from typing import Optional

from .models import MailResult, MailStatus

logger = logging.getLogger("palmshed.mail.audit")


class MailLogger:
    def log_result(self, result: MailResult) -> None:
        entry = {
            "id": result.mail_id,
            "recipient": None,
            "template": None,
            "provider": result.provider,
            "status": result.status.value,
            "sent_at": result.timestamp.isoformat(),
            "retry_count": result.retry_count,
            "provider_message_id": result.provider_message_id,
        }
        if result.error:
            entry["error"] = result.error
        logger.info("mail_event", extra=entry)

    def log_send(
        self,
        mail_id: str,
        provider: str,
        status: MailStatus,
        retry_count: int = 0,
        error: Optional[str] = None,
    ) -> None:
        entry = {
            "id": mail_id,
            "recipient": None,
            "template": None,
            "provider": provider,
            "status": status.value,
            "sent_at": None,
            "retry_count": retry_count,
        }
        if error:
            entry["error"] = error
        logger.info("mail_event", extra=entry)
