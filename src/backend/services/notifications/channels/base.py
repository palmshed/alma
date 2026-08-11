# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
from abc import ABC, abstractmethod

from ..models import ChannelCapabilities, Notification, NotificationResult


class NotificationChannel(ABC):
    @abstractmethod
    def send(self, notification: Notification) -> NotificationResult: ...

    @property
    @abstractmethod
    def capabilities(self) -> ChannelCapabilities: ...

    @abstractmethod
    def health(self) -> bool: ...
