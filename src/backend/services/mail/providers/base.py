# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
from abc import ABC, abstractmethod

from ..models import MailMessage, MailResult, ProviderCapabilities


class MailProvider(ABC):
    @abstractmethod
    def send(self, message: MailMessage) -> MailResult: ...

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities: ...
