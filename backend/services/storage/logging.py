import logging
from typing import Optional

from .models import StorageResult, StorageStatus

logger = logging.getLogger("palmshed.storage.audit")


class StorageLogger:
    def log_result(self, result: StorageResult) -> None:
        entry = {
            "object_id": result.object.id if result.object else "",
            "object_name": result.object.name if result.object else "",
            "provider": result.provider,
            "status": result.status.value,
            "duration_ms": round(result.duration_ms, 2),
        }
        if result.error:
            entry["error"] = result.error
        logger.info("storage_event", extra=entry)

    def log_operation(
        self,
        operation: str,
        name: str,
        provider: str,
        status: StorageStatus,
        error: Optional[str] = None,
    ) -> None:
        entry = {
            "operation": operation,
            "object_name": name,
            "provider": provider,
            "status": status.value,
        }
        if error:
            entry["error"] = error
        logger.info("storage_event", extra=entry)
