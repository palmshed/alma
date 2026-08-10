# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT

"""AI provider abstraction and registry."""

from .base import (
    AIProvider,
    AIProviderError,
    CAPABILITY_CHAT,
    CAPABILITY_CODE,
    CAPABILITY_THINKING,
    CAPABILITY_WEB,
    CATEGORY_AUTH,
    CATEGORY_INVALID_REQUEST,
    CATEGORY_NETWORK,
    CATEGORY_QUOTA,
    CATEGORY_SERVER,
    CATEGORY_UNAVAILABLE,
    CATEGORY_UNKNOWN,
    classify_http_status,
    classify_network_error,
    normalize_messages,
)
from .registry import (
    AIProviderRegistry,
    GeminiAI,
    OpenRouterProvider,
    SyntheticProvider,
)

__all__ = [
    "AIProvider",
    "AIProviderError",
    "AIProviderRegistry",
    "CAPABILITY_CHAT",
    "CAPABILITY_CODE",
    "CAPABILITY_THINKING",
    "CAPABILITY_WEB",
    "CATEGORY_AUTH",
    "CATEGORY_INVALID_REQUEST",
    "CATEGORY_NETWORK",
    "CATEGORY_QUOTA",
    "CATEGORY_SERVER",
    "CATEGORY_UNAVAILABLE",
    "CATEGORY_UNKNOWN",
    "GeminiAI",
    "OpenRouterProvider",
    "SyntheticProvider",
    "classify_http_status",
    "classify_network_error",
    "normalize_messages",
]
