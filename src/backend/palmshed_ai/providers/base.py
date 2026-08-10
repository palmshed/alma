# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT

"""
AI provider abstraction for Alma.

Routes talk to the AI router (``palmshed_ai.router``), never to a concrete
provider.  Each provider (Gemini direct, OpenRouter, synthetic) implements
the interface defined here, so provider logic stays out of the API layer.

Providers raise :class:`AIProviderError` with a classified ``category`` so
failures are observable and correctly reported (quota, auth, unavailable,
server, network) instead of being turned into synthetic successes.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator, List, Optional

# Error categories — deterministic classification for routing and HTTP mapping.
CATEGORY_QUOTA = "quota"
CATEGORY_AUTH = "auth"
CATEGORY_UNAVAILABLE = "unavailable"
CATEGORY_INVALID_REQUEST = "invalid_request"
CATEGORY_SERVER = "server"
CATEGORY_NETWORK = "network"
CATEGORY_UNKNOWN = "unknown"

CATEGORY_LABELS = {
    CATEGORY_QUOTA: "quota",
    CATEGORY_AUTH: "auth",
    CATEGORY_UNAVAILABLE: "unavailable",
    CATEGORY_INVALID_REQUEST: "invalid_request",
    CATEGORY_SERVER: "server",
    CATEGORY_NETWORK: "network",
    CATEGORY_UNKNOWN: "unknown",
}

# Capabilities used by the router to pick a model for a request.
CAPABILITY_CHAT = "chat"
CAPABILITY_THINKING = "thinking"
CAPABILITY_CODE = "code"
CAPABILITY_WEB = "web"


class AIProviderError(Exception):
    """Classified provider failure.

    Carries the failing provider and model so fallback logic and API
    error responses can report exactly what happened.
    """

    def __init__(
        self,
        message: str,
        category: str = CATEGORY_UNKNOWN,
        http_status: Optional[int] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ):
        super().__init__(message)
        self.category = category
        self.http_status = http_status
        self.provider = provider
        self.model = model

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": str(self),
            "category": self.category,
            "http_status": self.http_status,
            "provider": self.provider,
            "model": self.model,
        }

    def http_error_status(self) -> int:
        """HTTP status the API layer should return for this failure."""
        if self.http_status:
            return self.http_status
        mapping = {
            CATEGORY_QUOTA: 429,
            CATEGORY_AUTH: 401,
            CATEGORY_UNAVAILABLE: 503,
            CATEGORY_INVALID_REQUEST: 400,
            CATEGORY_SERVER: 502,
            CATEGORY_NETWORK: 504,
        }
        return mapping.get(self.category, 500)


def classify_http_status(
    status: int,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    message: str = "",
) -> AIProviderError:
    """Build a classified error from an HTTP status code."""
    if status in (429, 402):
        category = CATEGORY_QUOTA
    elif status in (401, 403):
        category = CATEGORY_AUTH
    elif status in (408, 409):
        category = CATEGORY_NETWORK
    elif status == 400:
        category = CATEGORY_INVALID_REQUEST
    elif status == 404:
        category = CATEGORY_INVALID_REQUEST
    elif status == 503:
        category = CATEGORY_UNAVAILABLE
    elif 500 <= status < 600:
        category = CATEGORY_SERVER
    else:
        category = CATEGORY_UNKNOWN
    detail = message or f"provider returned HTTP {status}"
    return AIProviderError(
        detail,
        category=category,
        http_status=status,
        provider=provider,
        model=model,
    )


def classify_network_error(
    exc: Exception,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> AIProviderError:
    """Classify a transport-level failure (connection, timeout, DNS)."""
    detail = str(exc) or exc.__class__.__name__
    return AIProviderError(
        detail,
        category=CATEGORY_NETWORK,
        http_status=None,
        provider=provider,
        model=model,
    )


class AIProvider(ABC):
    """Interface every AI provider implements."""

    #: Canonical name used for routing and configuration (``gemini``,
    #: ``openrouter``, ``synthetic``).
    name: str = "abstract"

    #: Human display name for verification output.
    display_name: str = "Abstract"

    @property
    @abstractmethod
    def has_credentials(self) -> bool:
        """True when real credentials are configured."""

    @property
    def synthetic(self) -> bool:
        """True when the provider synthesizes responses (mock/no key)."""
        return not self.has_credentials

    def describe(self) -> str:
        """Verification label: provider name or ``synthetic/mock``."""
        if self.synthetic:
            return "synthetic/mock"
        return self.display_name

    @abstractmethod
    def model_for(self, capability: str) -> str:
        """Resolve the model name for a capability."""

    @abstractmethod
    def generate_text(self, prompt: str, model: Optional[str] = None) -> str:
        """Generate a plain text response for ``prompt``."""

    @abstractmethod
    def generate_chat(
        self, messages: List[Dict[str, Any]], model: Optional[str] = None
    ) -> str:
        """Generate a response from a conversation message list."""

    @abstractmethod
    def generate_chat_with_thinking(
        self, messages: List[Dict[str, Any]], model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a response plus a thinking summary from a conversation."""

    @abstractmethod
    def generate_text_with_thinking(
        self, prompt: str, model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a response plus a thinking summary from a prompt."""

    @abstractmethod
    def generate_chat_with_url_context(
        self, messages: List[Dict[str, Any]], model: Optional[str] = None
    ) -> str:
        """Generate a response from a conversation with URL context."""

    @abstractmethod
    def generate_text_with_url_context(
        self, prompt: str, model: Optional[str] = None
    ) -> str:
        """Generate a response from a prompt with URL context."""

    @abstractmethod
    def stream_chat(
        self, messages: List[Dict[str, Any]], model: Optional[str] = None
    ) -> Iterator[str]:
        """Stream response deltas for a conversation."""

    def supports_streaming(self) -> bool:
        return True


def normalize_messages(messages: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Normalize conversation messages to ``[{role, content}, ...]``.

    Skips messages without usable text and maps unknown roles to ``user``.
    Role values match each provider's conventions (``user``/``assistant``).
    """
    normalized: List[Dict[str, Any]] = []
    if not messages:
        return normalized
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role", "")
        if role not in ("user", "assistant", "model"):
            continue
        text = (msg.get("content") or "").strip()
        if not text:
            continue
        normalized.append({"role": role, "content": text})
    return normalized


def last_user_query(messages: List[Dict[str, Any]]) -> str:
    """Return the text of the last user message, or ``""``."""
    for msg in reversed(messages):
        if msg.get("role") == "user" and msg.get("content"):
            return msg["content"].strip()
    return ""
