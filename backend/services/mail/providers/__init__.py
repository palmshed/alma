# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
from typing import Optional

from ..config import MailConfig
from .base import MailProvider
from .mock import MockProvider
from .registry import ProviderRegistry
from .resend import ResendProvider
from .smtp import SMTPProvider

ProviderRegistry.register("mock", MockProvider)
ProviderRegistry.register("smtp", SMTPProvider)
ProviderRegistry.register("resend", ResendProvider)


def get_provider(config: Optional[MailConfig] = None) -> MailProvider:
    if config is None:
        config = MailConfig.from_env()
    return ProviderRegistry.create(config.provider, config)


__all__ = [
    "MailProvider",
    "SMTPProvider",
    "MockProvider",
    "ResendProvider",
    "ProviderRegistry",
    "get_provider",
]
