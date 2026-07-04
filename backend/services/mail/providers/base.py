from abc import ABC, abstractmethod

from ..models import MailMessage, MailResult, ProviderCapabilities


class MailProvider(ABC):
    @abstractmethod
    def send(self, message: MailMessage) -> MailResult:
        ...

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        ...
