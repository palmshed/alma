from .config import MailConfig
from .metrics import MailMetrics
from .models import (
    HealthStatus,
    MailMessage,
    MailResult,
    MailStatus,
    MailPriority,
    RetryPolicy,
    ProviderCapabilities,
)
from .service import MailService, MailError, MailValidationError
from .templates import MailTemplate, MailTemplates, TemplateDefinition
from .providers import MailProvider, ProviderRegistry, get_provider
from .queue import MailQueue, get_queue

__all__ = [
    "MailConfig",
    "MailMetrics",
    "MailService",
    "MailMessage",
    "MailResult",
    "MailStatus",
    "MailPriority",
    "MailError",
    "MailValidationError",
    "RetryPolicy",
    "HealthStatus",
    "ProviderCapabilities",
    "MailTemplate",
    "MailTemplates",
    "TemplateDefinition",
    "MailProvider",
    "ProviderRegistry",
    "MailQueue",
    "get_provider",
    "get_queue",
]
